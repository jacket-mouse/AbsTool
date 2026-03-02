package cn.edu.sdu.software.engine

import cn.edu.sdu.software.model.ScriptConfig
import cn.edu.sdu.software.service.ActionMappingService
import org.springframework.stereotype.Service

@Service
class PythonScriptGenerator(
    private val actionMappingService: ActionMappingService
) {

    /**
     * 核心入口：将配置对象转换为 Python 代码字符串
     */
    fun generate(config: ScriptConfig): String {
        return generateInternal(config, false)
    }

    /**
     * 为调试模式生成具备断点交互能力的 Python 代码字符串
     */
    fun generateDebug(config: ScriptConfig): String {
        return generateInternal(config, true)
    }

    private val objectMapper = com.fasterxml.jackson.databind.ObjectMapper()

    private fun generateInternal(config: ScriptConfig, isDebug: Boolean): String {
        if (isDebug) {
            // 调试模式下为保证逐行注入特性，暂且依然采用原来的生成树
            val parser = AbsScriptParser()
            val astSequenceNode = parser.parse(config)
            val pythonVisitor = PythonAstVisitor(actionMappingService, true)
            astSequenceNode.accept(pythonVisitor)
            return pythonVisitor.getResult()
        }

        // 生产模式 - 基于状态机的执行引擎翻译
        val nodeMap = config.nodes.associateBy { it.id }
        val adjList = mutableMapOf<String, String?>()
        val inDegree = mutableMapOf<String, Int>()

        config.nodes.forEach {
            inDegree[it.id ?: ""] = 0
            adjList[it.id ?: ""] = null
        }

        config.connections.forEach { conn ->
            if (nodeMap.containsKey(conn.from) && nodeMap.containsKey(conn.to)) {
                adjList[conn.from] = conn.to
                val toId = conn.to
                inDegree[toId] = (inDegree[toId] ?: 0) + 1
            }
        }

        val roots = inDegree.filter { it.value == 0 }.keys
        val startNodeId = roots.firstOrNull() ?: if (config.nodes.isNotEmpty()) config.nodes[0].id else ""

        val flowGraph = mutableMapOf<String, MutableMap<String, Any?>>()
        val dummyVisitor = PythonAstVisitor(actionMappingService, false)

        config.nodes.forEach { node ->
            val id = node.id ?: return@forEach
            val map = mutableMapOf<String, Any?>()
            map["type"] = node.type
            map["next"] = adjList[id]

            // 将所有属性存入 map
            map.putAll(node.properties)

            // 先翻译成原子 Python 代码 (例如 device.click(x, y))
            val actionAstNode = ActionAstNode(id, node.type ?: "", node.title ?: "", node.properties as Map<String, Any>)
            val codeStr = dummyVisitor.getCodeSnippet(actionAstNode)
            map["code"] = codeStr

            flowGraph[id] = map
        }

        val flowGraphJson = objectMapper.writeValueAsString(flowGraph)

        val template = """
            # 自动生成的Android行为模拟脚本 (State Machine 核心引擎驱动)
            from uiautomator2 import connect
            import time
            import json
            import traceback

            def run_script():
                # 1. 连接设备
                print("正在连接设备...")
                try:
                    device = connect()
                    print(json.dumps({"type": "init", "status": "success", "serial": device.serial}), flush=True)
                except Exception as e:
                    print(json.dumps({"type": "init", "status": "error", "error": str(e)}), flush=True)
                    exit(1)

                # 2. 注入从 JSON 解析来的图结构数据
                flow_graph = $flowGraphJson
                
                # 3. 初始化状态机和安全锁
                current_node_id = "$startNodeId"
                jump_counters = {}
                max_total_steps = 1000
                step_count = 0

                print("脚本状态机开始执行...")
                # 4. 状态机主循环 (核心路由)
                while current_node_id and step_count < max_total_steps:
                    step_count += 1
                    node_data = flow_graph.get(current_node_id)
                    
                    if not node_data:
                        print(f"节点 {current_node_id} 不存在，流程终止。")
                        break
                        
                    action_type = node_data.get("type")
                    next_node = node_data.get("next")
                    
                    # 跳转节点路由逻辑
                    if action_type == "jump":
                        target = node_data.get("targetNodeId")
                        max_r = int(node_data.get("maxRetries", 1)) if node_data.get("maxRetries") else 1
                        
                        jump_counters[current_node_id] = jump_counters.get(current_node_id, 0) + 1
                        if jump_counters[current_node_id] <= max_r:
                            print(f"执行跳转 ({jump_counters[current_node_id]}/{max_r}) -> 返回节点: {target}")
                            current_node_id = target
                        else:
                            print(f"跳转节点已达到最大重试次数 {max_r}，跳出循环执行下一步。")
                            current_node_id = next_node
                        continue
                        
                    # 普通动作执行
                    code_str = node_data.get("code")
                    if code_str:
                        try:
                            # 动态挂载原生物理按键方法执行
                            exec(code_str, globals(), locals())
                            print(f"节点{current_node_id}({action_type}) 执行成功")
                        except Exception as e:
                            print(f"节点{current_node_id}({action_type}) 执行失败: {e}")
                            traceback.print_exc()
                            raise e

                    current_node_id = next_node

                if step_count >= max_total_steps:
                    print("警告：触发全局状态机执行安全锁 (单次任务上限1000步)，强制停止以保护设备！")
                else:
                    print("所有节点执行完毕！")

            if __name__ == "__main__":
                run_script()
        """.trimIndent()

        return template
    }
}