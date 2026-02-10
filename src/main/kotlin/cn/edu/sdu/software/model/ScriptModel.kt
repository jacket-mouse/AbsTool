package cn.edu.sdu.software.model

// 1. 顶层配置对象 (对应整个 JSON)
data class ScriptConfig(
    var nodes: List<ScriptNode> = ArrayList(),
    var connections: List<Connection> = ArrayList()
)

// 2. 节点对象
data class ScriptNode(
    var id: String = "",
    var type: String? = null,
    var title: String? = null,
    var desc: String? = null,
    var loc: String? = null,
    // 动态属性，对应前端的 properties
    var properties: Map<String, Any?> = HashMap()
)

// 3. 连接关系
data class Connection(
    var from: String = "",
    var to: String = "",
    var fromPort: String? = null,
    var toPort: String? = null
)