package cn.edu.sdu.software.engine

import cn.edu.sdu.software.service.ActionMappingService

class PythonAstVisitor(
    private val mappingService: ActionMappingService? = null,
    private val isDebug: Boolean = false
) : AstVisitor {

    private val sb = StringBuilder()
    
    // 模板头部：初始化代码
    private val scriptHeader = """
        # 自动生成的Android行为模拟脚本（适配UiAutomator2）
        from uiautomator2 import connect
        import time
        import json

        # 设备初始化
        try:
            device = connect() # 默认连接当前连入电脑的设备
            print(json.dumps({"type": "init", "status": "success", "serial": device.serial}), flush=True)
        except Exception as e:
            print(json.dumps({"type": "init", "status": "error", "error": str(e)}), flush=True)
            exit(1)
    """.trimIndent()

    // 模板尾部：清理代码
    private val scriptFooter = """
        # 脚本执行完成
        print("所有节点执行完毕")
    """.trimIndent()

    private val debugHeader = """
        def execute_debug_node(node_id, action_name, code_str):
            import json, sys, traceback
            while True:
                print(json.dumps({"type": "break", "nodeId": node_id, "action": action_name, "code": code_str}), flush=True)
                line = sys.stdin.readline()
                if not line: sys.exit(0)
                try:
                    cmd = json.loads(line)
                    if cmd.get('action') == 'stop':
                        sys.exit(0)
                    elif cmd.get('action') == 'run':
                        if 'overrideCode' in cmd: code_str = cmd['overrideCode']
                        exec(code_str, globals())
                        print(json.dumps({"type": "log", "nodeId": node_id, "status": "success", "message": f"Execute [{action_name}] success"}), flush=True)
                        break
                except Exception as e:
                    import traceback
                    print(json.dumps({"type": "log", "nodeId": node_id, "status": "error", "message": f"Execute failed: {str(e)}\n{traceback.format_exc()}"}), flush=True)
    """.trimIndent()

    init {
        sb.append(scriptHeader)
        sb.append("\n\n")
        if (isDebug) {
            sb.append(debugHeader)
            sb.append("\n\n")
        }
    }

    override fun visit(node: SequenceAstNode) {
        node.children.forEach { child ->
            child.accept(this)
        }
        sb.append(scriptFooter)
        sb.append("\n")
    }

    override fun visit(node: ActionAstNode) {
        // 尝试从数据库获取扩展映射
        val extendedMapping = mappingService?.getMapping(node.type, "Python")
        val codeLine = if (!extendedMapping.isNullOrBlank()) {
            buildFromTemplate(extendedMapping, node.properties)
        } else {
            // 代码内置基础映射
            getBuiltInActionCode(node)
        }
        
        if (isDebug) {
            val escapedCode = codeLine.replace("\\", "\\\\").replace("\"", "\\\"").replace("\n", "\\n")
            sb.append("execute_debug_node(\"${node.id}\", \"${node.type}\", \"\"\"$codeLine\"\"\")\n")
        } else {
            val indentedCode = codeLine.replace("\n", "\n    ")
            sb.append("# 节点：${node.id} (${node.type})\n")
            sb.append("try:\n")
            sb.append("    $indentedCode\n")
            sb.append("    print(\"节点${node.id}执行成功\")\n")
            sb.append("except Exception as e:\n")
            sb.append("    print(f\"节点${node.id}执行失败: {str(e)}\")\n")
            sb.append("    raise\n\n")
        }
    }

    fun getCodeSnippet(node: ActionAstNode): String {
        val extendedMapping = mappingService?.getMapping(node.type, "Python")
        return if (!extendedMapping.isNullOrBlank()) {
            buildFromTemplate(extendedMapping, node.properties)
        } else {
            getBuiltInActionCode(node)
        }
    }

    fun getBuiltInActionCode(node: ActionAstNode): String {
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
                val steps = props["steps"]?.toString()?.toDouble() ?: 50.0
                "device.swipe($sx, $sy, $ex, $ey, duration=${steps * 0.005})"
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
            "unlock" -> {
                val unlockType = props["unlockType"] as? String ?: "密码"
                if (unlockType == "手势") {
                    val gestureList = props["gesture"] as? List<*> ?: emptyList<Any>()
                    val patternStr = gestureList.joinToString(",")
                    """
                    # 手势解锁
                    device.screen_on()
                    device.swipe_ext("up", scale=0.8) # 向上滑动调出密码框
                    time.sleep(1)

                    # 尝试动态获取手势控件边界
                    pattern_view = device(classNameMatches="(?i).*LockPatternView.*")
                    if pattern_view.exists:
                        bounds = pattern_view.info['bounds']
                        left, top, right, bottom = bounds['left'], bounds['top'], bounds['right'], bounds['bottom']
                        w = right - left
                        h = bottom - top
                        # 计算 3x3 宫格的中心点 (分六份，取奇数1,3,5)
                        x_c = [left + w/6, left + w/2, left + w*5/6]
                        y_c = [top + h/6, top + h/2, top + h*5/6]
                    else:
                        # 找不到控件则Fallback：基于屏幕比例猜测
                        width = device.info['displayWidth']
                        height = device.info['displayHeight']
                        x_c = [width*0.2, width*0.5, width*0.8]
                        y_c = [height*0.55, height*0.7, height*0.85]
                    
                    pattern = [$patternStr]
                    points = []
                    for idx in pattern:
                        row = int(idx) // 3
                        col = int(idx) % 3
                        points.append((x_c[col], y_c[row]))
                        
                    if points:
                        device.swipe_points(points, 0.05)
                    """.trimIndent()
                } else {
                    val password = props["password"] as? String ?: ""
                    """
                    # 密码解锁
                    device.screen_on()
                    device.swipe_ext("up", scale=0.8)
                    time.sleep(1)
                    
                    pwd = "$password"
                    for char in pwd:
                        # 优先尝试在屏幕上寻找对应数字的九宫格/安全按键 
                        btn = device(text=char)
                        if not btn.exists:
                            btn = device(description=char)
                        
                        if btn.exists:
                            btn.click()
                        elif char.isdigit():
                            # 降级：发送Android底层系统按键事件指令 (KEYCODE_0为7)
                            device.press(int(char) + 7)
                        time.sleep(0.2)
                        
                    time.sleep(0.5)
                    # 处理可能存在的独立确认按钮（部分系统密码输满即解锁，部分有独立的"确认"或"完成"按钮）
                    enter_btn = device(textMatches="(?i)(确认|确定|完成|done|enter)")
                    if not enter_btn.exists:
                        enter_btn = device(descriptionMatches="(?i)(确认|确定|完成|done|enter)")
                        
                    if enter_btn.exists:
                        enter_btn.click()
                    else:
                        device.press("enter")
                    """.trimIndent()
                }
            }
            "jump" -> {
                val targetId = props["targetNodeId"] as? String ?: "未知"
                "# 逻辑控制流：将跳转流向节点 ID -> $targetId"
            }
            else -> "# 未知节点类型: ${node.type}"
        }
    }

    /**
     * 极简模板渲染器: 取出数据库模板 ${x}, 然后用 node.properties 替换
     */
    fun buildFromTemplate(template: String, props: Map<String, Any>): String {
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
