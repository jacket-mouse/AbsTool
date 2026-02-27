package cn.edu.sdu.software.engine

import cn.edu.sdu.software.service.ActionMappingService

class PythonAstVisitor(
    private val mappingService: ActionMappingService? = null
) : AstVisitor {

    private val sb = StringBuilder()
    
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

    init {
        sb.append(scriptHeader)
        sb.append("\\n")
    }

    override fun visit(node: SequenceAstNode) {
        node.children.forEach { child ->
            child.accept(this)
        }
        sb.append(scriptFooter)
    }

    override fun visit(node: ActionAstNode) {
        sb.append("        # 节点：${node.id} (${node.type})\n")
        sb.append("        try:\n")
        
        // 尝试从数据库获取扩展映射
        val extendedMapping = mappingService?.getMapping(node.type, "Python")
        val codeLine = if (!extendedMapping.isNullOrBlank()) {
            buildFromTemplate(extendedMapping, node.properties)
        } else {
            // 代码内置基础映射
            getBuiltInActionCode(node)
        }
        
        sb.append("            $codeLine\n")
        sb.append("            print(\"节点${node.id}执行成功\")\n")
        sb.append("        except Exception as e:\n")
        sb.append("            print(f\"节点${node.id}执行失败: {str(e)}\")\n")
        sb.append("            raise\n\n")
    }

    private fun getBuiltInActionCode(node: ActionAstNode): String {
        val props = node.properties
        return when (node.type) {
            "click" -> {
                val targetType = props["targetType"] as? String
                val elementId = props["elementId"] as? String
                if (targetType == "元素 ID" && !elementId.isNullOrEmpty()) {
                    "device(resourceId=\"$elementId\").click()"
                } else {
                    val x = props["x"] ?: 0
                    val y = props["y"] ?: 0
                    "device.click($x, $y)"
                }
            }
            "longPress" -> {
                val targetType = props["targetType"] as? String
                val elementId = props["elementId"] as? String
                val duration = props["duration"] ?: 1000
                if (targetType == "元素 ID" && !elementId.isNullOrEmpty()) {
                    "device(resourceId=\"$elementId\").long_click(duration=${duration.toString().toDouble() / 1000})"
                } else {
                    val x = props["x"] ?: 0
                    val y = props["y"] ?: 0
                    "device.long_click($x, $y, ${duration.toString().toDouble() / 1000})"
                }
            }
            "swipe" -> {
                val sx = props["startX"] ?: 0
                val sy = props["startY"] ?: 0
                val ex = props["endX"] ?: 100
                val ey = props["endY"] ?: 100
                val steps = props["steps"] ?: 50
                "device.swipe($sx, $sy, $ex, $ey, $steps)"
            }
            "input" -> {
                val text = props["text"] as? String ?: ""
                val elementId = props["elementId"] as? String
                if (!elementId.isNullOrEmpty()) {
                    "device(resourceId=\"$elementId\").set_text(\"$text\")"
                } else {
                    "# [Error] input操作需要元素ID绑定"
                }
            }
            "wait" -> {
                val duration = props["duration"] ?: 1000
                "time.sleep(${duration.toString().toLong() / 1000.0})"
            }
            "openApp" -> {
                val pkg = props["packageName"] as? String ?: ""
                "device.app_start(\"$pkg\")"
            }
            "closeApp" -> {
                val pkg = props["packageName"] as? String ?: ""
                "device.app_stop(\"$pkg\")"
            }
            "home" -> "device.press(\"home\")"
            "back" -> "device.press(\"back\")"
            else -> "# 未知节点类型: ${node.type}"
        }
    }

    /**
     * 极简模板渲染器: 取出数据库模板 ${x}, 然后用 node.properties 替换
     */
    private fun buildFromTemplate(template: String, props: Map<String, Any>): String {
        var str = template
        props.forEach { (key, value) ->
            str = str.replace("\${$key}", value.toString())
        }
        return str
    }

    fun getResult(): String {
        return sb.toString()
    }
}
