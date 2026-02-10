package cn.edu.sdu.software.engine

import cn.edu.sdu.software.model.*
import org.springframework.stereotype.Service

@Service
class PythonScriptGenerator {

    // 模板头部：初始化代码
    private val scriptHeader = """
        # 自动生成的Android行为模拟脚本（适配UiAutomator2）
        from uiautomator2 import connect
        import time

        # 设备初始化
        try:
            device = connect("127.0.0.1:5555") # 默认连接本地
            device.wait_for_idle(timeout=10)
            print("设备连接成功")
        except Exception as e:
            print(f"设备连接失败: {e}")
            exit(1)
            
    """.trimIndent()

    // 模板尾部：清理代码
    private val scriptFooter = """
        # 脚本执行完成
        print("所有节点执行完毕")
    """.trimIndent()

    /**
     * 核心入口：将配置对象转换为 Python 代码字符串
     */
    fun generate(config: ScriptConfig): String {
        val sb = StringBuilder()
        sb.append(scriptHeader)
        sb.append("\n")

        // 1. 流程排序 (简单实现：根据 connections 确定执行顺序)
        // 实际生产中这里需要拓扑排序，这里简化为按列表顺序或简单链表查找
        val sortedNodes = sortNodes(config.nodes, config.connections)

        // 2. 遍历节点生成指令
        sortedNodes.forEach { node ->
            val codeBlock = mapNodeToCode(node)
            sb.append(codeBlock)
            sb.append("\n")
        }

        sb.append(scriptFooter)
        return sb.toString()
    }

    /**
     * 指令映射逻辑 (对应 3.3.1 指令映射表)
     */
    private fun mapNodeToCode(node: ScriptNode): String {
        return """
        # 节点：${node.id} (${node.type})
        try:
            ${getActionCode(node)}
            print("节点${node.id}执行成功")
        except Exception as e:
            print(f"节点${node.id}执行失败: {str(e)}")
            raise

        """.trimIndent()
    }

    private fun getActionCode(node: ScriptNode): String {
        val props = node.properties
        return when (node.type) {
            "click" -> {
                val elementId = props["elementId"] as? String
                if (!elementId.isNullOrEmpty()) {
                    "device(resourceId=\"$elementId\").click()"
                } else {
                    val x = props["x"]
                    val y = props["y"]
                    "device.click($x, $y)"
                }
            }
            "longpress" -> {
                val x = props["x"]
                val y = props["y"]
                val duration = props["duration"] ?: 1000
                "device.long_click($x, $y, ${duration.toString().toDouble()/1000})"
            }
            "swipe" -> {
                val sx = props["startX"]
                val sy = props["startY"]
                val ex = props["endX"]
                val ey = props["endY"]
                "device.swipe($sx, $sy, $ex, $ey)"
            }
            "input" -> {
                val text = props["text"] as? String ?: ""
                val elementId = props["elementId"] as? String
                if (!elementId.isNullOrEmpty()) {
                    "device(resourceId=\"$elementId\").set_text(\"$text\")"
                } else {
                    "# 缺少元素ID，无法输入"
                }
            }
            "wait" -> {
                val duration = props["duration"] ?: 1000
                "time.sleep(${duration.toString().toLong()/1000.0})"
            }
            "openApp" -> {
                val pkg = props["packageName"] as? String
                "device.app_start(\"$pkg\")"
            }
            "closeApp" -> {
                val pkg = props["packageName"] as? String
                "device.app_stop(\"$pkg\")"
            }
            "home" -> "device.press(\"home\")"
            "back" -> "device.press(\"back\")"
            else -> "# 未知节点类型: ${node.type}"
        }
    }

    /**
     * 简单的排序逻辑：寻找 Start 节点并根据 Connection 排序
     * (为了简化演示，这里直接返回 nodes，实际需要根据 connections 连线逻辑重排)
     */
    private fun sortNodes(nodes: List<ScriptNode>, connections: List<Connection>): List<ScriptNode> {
        // TODO: 实现真正的拓扑排序
        // 这里暂时假设 JSON 里的 nodes 顺序就是执行顺序
        return nodes
    }
}