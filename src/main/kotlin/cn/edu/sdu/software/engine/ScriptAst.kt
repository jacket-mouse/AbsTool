package cn.edu.sdu.software.engine

import cn.edu.sdu.software.model.ScriptConfig
import cn.edu.sdu.software.model.ScriptNode

// 抽象语法树基础节点
abstract class AstNode {
    abstract fun accept(visitor: AstVisitor)
}

// 具体操作节点
class ActionAstNode(
    val id: String,
    val type: String,
    val title: String,
    val properties: Map<String, Any>
) : AstNode() {
    override fun accept(visitor: AstVisitor) {
        visitor.visit(this)
    }
}

// 根节点/序列节点 (组合模式)
class SequenceAstNode : AstNode() {
    val children = mutableListOf<AstNode>()
    override fun accept(visitor: AstVisitor) {
        visitor.visit(this)
    }
}

// 访问者接口：分离数据结构和具体操作逻辑(如生成 Python/XML)
interface AstVisitor {
    fun visit(node: SequenceAstNode)
    fun visit(node: ActionAstNode)
}

/**
 * 语法解析器：将 JSON 格式的散乱配置 (节点数组+连线数组) 构建为有序的抽象语法树 (AST)
 * 同时在构建时校验其合法性 (缺失参数、孤立节点闭环检测等)
 */
class AbsScriptParser {

    fun parse(config: ScriptConfig): SequenceAstNode {
        // 1. 数据预处理，构造节点图表映射
        val nodeMap = config.nodes.associateBy { it.id }
        // adj 为出度边
        val adjList = mutableMapOf<String, MutableList<String>>()
        // inDegree 用于找起始节点
        val inDegree = mutableMapOf<String, Int>()

        config.nodes.forEach {
            adjList[it.id] = mutableListOf()
            inDegree[it.id] = 0
        }

        config.connections.forEach { conn ->
            val from = conn.from
            val to = conn.to
            if (nodeMap.containsKey(from) && nodeMap.containsKey(to)) {
                adjList[from]?.add(to)
                inDegree[to] = inDegree.getOrDefault(to, 0) + 1
            }
        }

        // 2. 校验：必填参数校验
        config.nodes.forEach { node ->
            validateNodeProperties(node)
        }

        // 3. 寻找入口点 (入度为0的节点)
        val roots = inDegree.filter { it.value == 0 }.keys
        if (roots.isEmpty() && config.nodes.isNotEmpty()) {
            throw IllegalArgumentException("配置非法: 流程存在闭环无法找到起点(无入度为0的起始节点)")
        }

        // 4. 将流程关系通过拓扑排序构建串行 Sequence (目前以单分支直线逻辑构建，可扩展到树型分支)
        val sequenceNode = SequenceAstNode()
        val visited = mutableSetOf<String>()
        val queue = ArrayDeque<String>()
        queue.addAll(roots)

        while (queue.isNotEmpty()) {
            val currId = queue.removeFirst()
            if (visited.contains(currId)) {
                // 如果在后续队列再次遇到说明是图中某个复杂的反向环，目前当普通节点忽略或是通过校验限制
                continue
            }
            visited.add(currId)
            val n = nodeMap[currId] ?: continue
            
            // 构建具体操作的抽象语法树节点 ActionAstNode
            val actionAstNode = ActionAstNode(
                id = n.id ?: "",
                type = n.type ?: "",
                title = n.title ?: "",
                properties = n.properties.filterValues { it != null } as Map<String, Any>
            )
            sequenceNode.children.add(actionAstNode)

            // BFS 向下推进
            adjList[currId]?.forEach { nextNodeValue ->
                if (!visited.contains(nextNodeValue) && !queue.contains(nextNodeValue)) {
                    queue.addLast(nextNodeValue)
                }
            }
        }

        // 强行判断是否所有节点都被覆盖到了
        if (visited.size < config.nodes.size) {
            throw IllegalArgumentException("配置非法: 流程图中存在孤立节点或无法到达的死循环区域。")
        }

        return sequenceNode
    }

    private fun validateNodeProperties(node: ScriptNode) {
        val props = node.properties
        when (node.type) {
            "click", "longpress" -> {
                val elementId = props["elementId"] as? String
                val targetType = props["targetType"] as? String
                if (targetType == "元素 ID" && elementId.isNullOrBlank()) {
                    throw IllegalArgumentException("节点 ${node.title}(${node.id}) 缺少必填参数: 元素 ID")
                } else if (targetType == "坐标" && props["x"] == null) {
                    throw IllegalArgumentException("节点 ${node.title}(${node.id}) 缺少必填参数: 坐标(X,Y)")
                }
            }
            "input" -> {
                if ((props["text"] as? String).isNullOrBlank() || (props["elementId"] as? String).isNullOrBlank()) {
                    throw IllegalArgumentException("节点 ${node.title}(${node.id}) 缺少必填参数: text或elementId")
                }
            }
            "swipe" -> {
                if (props["startX"] == null || props["startY"] == null || props["endX"] == null || props["endY"] == null) {
                    throw IllegalArgumentException("节点 ${node.title}(${node.id}) 滑动参数不全")
                }
            }
            "wait" -> {
                if (props["duration"] == null && props["waitMode"] == null) {
                    throw IllegalArgumentException("节点 ${node.title}(${node.id}) 缺少等待时长")
                }
            }
            // 可以继续补充其他类型...
        }
    }
}
