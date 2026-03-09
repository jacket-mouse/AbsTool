package cn.edu.sdu.software.engine;

import cn.edu.sdu.software.model.Connection;
import cn.edu.sdu.software.model.ScriptConfig;
import cn.edu.sdu.software.model.ScriptNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.springframework.stereotype.Service;

import java.util.HashMap;
import java.util.Map;

@Service
public class PythonScriptGenerator {

    private final ObjectMapper objectMapper = new ObjectMapper();

    public String generate(ScriptConfig config) throws Exception {
        return generateInternal(config, false);
    }

    public String generateDebug(ScriptConfig config) throws Exception {
        return generateInternal(config, true);
    }

    private String generateInternal(ScriptConfig config, boolean isDebug) throws Exception {
        Map<String, ScriptNode> nodeMap = new HashMap<>();
        Map<String, Object> nextMap = new HashMap<>();
        Map<String, Integer> inDegree = new HashMap<>();
        Map<String, String> nodeGroupMap = new HashMap<>();  // childId -> groupNodeId
        if (config.getNodes() != null) {
            for (ScriptNode node : config.getNodes()) {
                nodeMap.put(node.getId(), node);
                inDegree.put(node.getId(), 0);
                if (node.getGroupKey() != null && !node.getGroupKey().isEmpty()) {
                    nodeGroupMap.put(node.getId(), node.getGroupKey());
                }
            }
        }

        if (config.getConnections() != null) {
            for (Connection conn : config.getConnections()) {
                if (nodeMap.containsKey(conn.getFrom()) && nodeMap.containsKey(conn.getTo())) {
                    if (conn.getFromPort() != null && !conn.getFromPort().isEmpty()) {
                        nextMap.compute(conn.getFrom(), (k, v) -> {
                            Map<String, String> m;
                            if (v instanceof Map) {
                                m = (Map<String, String>) v;
                            } else {
                                m = new HashMap<>();
                                if (v instanceof String) {
                                    m.put("default", (String) v);
                                }
                            }
                            m.put(conn.getFromPort(), conn.getTo());
                            return m;
                        });
                    } else {
                        nextMap.put(conn.getFrom(), conn.getTo());
                    }
                    inDegree.put(conn.getTo(), inDegree.getOrDefault(conn.getTo(), 0) + 1);
                }
            }
        }

        // Build children sub-graphs for loop group nodes
        // Key: loopNodeId -> {"nodes": {childId: childData}, "connections": [{from,to,fromPort}], "startNodeId": firstChildId}
        Map<String, Map<String, Object>> loopChildrenMap = new HashMap<>();
        if (config.getNodes() != null) {
            for (ScriptNode node : config.getNodes()) {
                if (node.isGroup() && "loop".equals(node.getType())) {
                    Map<String, Object> childGraph = new HashMap<>();
                    Map<String, Map<String, Object>> childNodes = new HashMap<>();
                    Map<String, Integer> childInDegree = new HashMap<>();

                    // Collect child nodes
                    for (ScriptNode child : config.getNodes()) {
                        if (node.getId().equals(child.getGroupKey())) {
                            Map<String, Object> childData = new HashMap<>();
                            childData.put("type", child.getType());
                            childData.put("next", nextMap.get(child.getId()));
                            if (child.getProperties() != null) {
                                Map<String, Object> childProps = new HashMap<>(child.getProperties());
                                childProps.remove("loc"); childProps.remove("category"); childProps.remove("key");
                                childData.putAll(childProps);
                            }
                            childNodes.put(child.getId(), childData);
                            childInDegree.put(child.getId(), 0);
                        }
                    }

                    // Count in-degrees within children (for identifying start node)
                    if (config.getConnections() != null) {
                        for (Connection conn : config.getConnections()) {
                            if (childNodes.containsKey(conn.getTo()) && childNodes.containsKey(conn.getFrom())) {
                                childInDegree.put(conn.getTo(), childInDegree.getOrDefault(conn.getTo(), 0) + 1);
                            }
                        }
                    }

                    String childStart = "";
                    for (Map.Entry<String, Integer> e : childInDegree.entrySet()) {
                        if (e.getValue() == 0) { childStart = e.getKey(); break; }
                    }
                    if (childStart.isEmpty() && !childNodes.isEmpty()) {
                        childStart = childNodes.keySet().iterator().next();
                    }

                    childGraph.put("nodes", childNodes);
                    childGraph.put("startNodeId", childStart);
                    loopChildrenMap.put(node.getId(), childGraph);
                }
            }
        }

        String startNodeId = "";
        for (Map.Entry<String, Integer> entry : inDegree.entrySet()) {
            // Skip child nodes of groups from outer graph start detection
            if (nodeGroupMap.containsKey(entry.getKey())) continue;
            if (entry.getValue() == 0) {
                startNodeId = entry.getKey();
                break;
            }
        }
        if (startNodeId.isEmpty() && config.getNodes() != null && !config.getNodes().isEmpty()) {
            startNodeId = config.getNodes().get(0).getId();
        }

        Map<String, Map<String, Object>> flowGraph = new HashMap<>();
        if (config.getNodes() != null) {
            for (ScriptNode node : config.getNodes()) {
                // Skip child nodes of groups - they are embedded inside their group
                if (nodeGroupMap.containsKey(node.getId())) continue;

                Map<String, Object> map = new HashMap<>();
                map.put("type", node.getType());
                map.put("next", nextMap.get(node.getId()));

                if (node.getProperties() != null) {
                    Map<String, Object> props = new HashMap<>(node.getProperties());
                    props.remove("loc");
                    props.remove("category");
                    props.remove("key");
                    map.putAll(props);
                }

                // For loop group nodes, embed children graph
                if (node.isGroup() && "loop".equals(node.getType()) && loopChildrenMap.containsKey(node.getId())) {
                    map.put("children", loopChildrenMap.get(node.getId()));
                }

                flowGraph.put(node.getId(), map);
            }
        }

        // 把图转成可以直接嵌入 Python 脚本里的 JSON 字符串
        String flowGraphJson = objectMapper.writeValueAsString(flowGraph);

        // 3. 最终生成组装的 Python 脚本模板
        String template = String.format("""
                # 自动生成的Android行为模拟脚本 (State Machine 核心引擎驱动)
                import uiautomator2 as u2
                import time
                import random
                import json
                import traceback
                import sys
                import threading
                import os
                
                # --- 1. 定义各个具体动作的执行函数 (Handlers) ---
                # 点击
                def handle_click(device, node):
                    target_type = node.get("targetType", "")
                    element_id = node.get("elementId", "")
                    if target_type == "元素 ID" and element_id:
                        device(resourceId=element_id).click()
                    else:
                        x = node.get("x", 0)
                        y = node.get("y", 0)
                        device.click(int(x), int(y))
                
                # 长按
                def handle_long_press(device, node):
                    target_type = node.get("targetType", "")
                    element_id = node.get("elementId", "")
                    # 兼容前端传 int 或 string 的情况
                    try:
                        dur_sec = float(node.get("duration", 1000)) / 1000.0
                    except (ValueError, TypeError):
                        dur_sec = 1.0
                
                    if target_type == "元素 ID" and element_id:
                        elem = device(resourceId=element_id)
                        # 优化 1：显式等待。最多等 5 秒，如果元素出现了才操作，大大降低崩溃率
                        if elem.wait(timeout=5.0):
                            elem.long_click(duration=dur_sec)
                        else:
                            # 配合我们之前的状态机设计，抛出异常让上层捕获并发送 error 给前端
                            raise Exception(f"长按失败：5秒内未找到元素 ID [{element_id}]")
                    elif target_type == "坐标":
                        x = node.get("x", 0)
                        y = node.get("y", 0)
                        # 优化 2：坐标归一化处理
                        # 假设前端 Vue 画布的基准分辨率是 1080 x 1920 (你需要根据实际情况修改这两个值)
                        canvas_width = 1080.0
                        canvas_height = 1920.0
                        # 获取当前连入手机的真实物理分辨率
                        real_width = device.info['displayWidth']
                        real_height = device.info['displayHeight']
                        # 动态换算真实坐标
                        # 如果你前端传的已经是 0~1 的百分比了，那直接 x * real_width 即可
                        real_x = int((float(x) / canvas_width) * real_width)
                        real_y = int((float(y) / canvas_height) * real_height)
                        # 确保坐标没有越界
                        real_x = max(0, min(real_x, real_width - 1))
                        real_y = max(0, min(real_y, real_height - 1))
                        print(real_x, real_y);
                
                        device.long_click(real_x, real_y, duration=dur_sec)
                    else:
                        raise Exception("长按节点配置错误：未知的目标类型或缺少参数")
                
                # 滑动
                def handle_swipe(device, node):
                    sx = node.get("startX", 0)
                    sy = node.get("startY", 0)
                    ex = node.get("endX", 0)
                    ey = node.get("endY", 0)
                
                    steps_str = node.get("steps", 50)
                    try:
                        dur = float(steps_str) * 0.005
                    except:
                        dur = 0.25
                
                    device.swipe_ext("up", scale=0.8) # 暂时 fallback 简易滑动
                    device.swipe(int(sx), int(sy), int(ex), int(ey), duration=dur)
                
                # 输入
                def handle_input(device, node):
                    text = str(node.get("text", ""))
                    element_id = node.get("elementId", "")
                    if element_id:
                        device(resourceId=element_id).set_text(text)
                    else:
                        print(json.dumps({"type": "log", "message": "[Error] input操作需要元素ID绑定"}, ensure_ascii=False), flush=True)
                
                # 等待
                def handle_wait(device, node):
                    duration_str = node.get("duration", "1000")
                    try:
                        dur_sec = float(duration_str) / 1000.0
                    except:
                        dur_sec = 1.0
                    time.sleep(dur_sec + random.uniform(0, 0.3))
                
                # 打开 APP
                def handle_open_app(device, node):
                    pkg = node.get("packageName", "")
                    if pkg:
                        device.app_start(pkg)
                
                # 关闭 APP
                def handle_close_app(device, node):
                    pkg = node.get("packageName", "")
                    if pkg:
                        device.app_stop(pkg)

                # 切换前台
                def handle_foreground(device, node):
                    pkg = node.get("packageName", "")
                    if pkg:
                        device.app_start(pkg, stop=False)
                        print(json.dumps({"type": "log", "message": f"系统提示件: 切换包名 {pkg} 至前台操作完毕"}, ensure_ascii=False), flush=True)
                        
                # 获取获取 APP 当前状态
                def handle_app_state(device, node):
                    pkg = node.get("packageName", "")
                    if pkg:
                        current = device.app_current()
                        if current.get("package") == pkg:
                            state = "前台"
                        else:
                            try:
                                pid = device.shell(["pidof", pkg]).output.strip()
                                state = "后台运行中" if pid else "未运行"
                            except Exception:
                                state = "未知或后台"
                        print(json.dumps({"type": "log", "message": f"检测到应用 [{pkg}] 当前状态: {state}"}, ensure_ascii=False), flush=True)
                
                # 返回主页
                def handle_home(device, node):
                    device.press("home")
                
                # 返回上一级
                def handle_back(device, node):
                    device.press("back")
                
                # 解锁屏幕(todo: 手势解锁
                def handle_unlock(device, node):
                    unlock_type = node.get("unlockType", "密码")
                    device.screen_on()
                    device.swipe_ext("up", scale=0.8)
                    time.sleep(1)
                
                    if unlock_type == "手势":
                        gesture = node.get("gesture", [])
                        if not isinstance(gesture, list):
                            try:
                                # If gesture is e.g. "0,1,2"
                                gesture = [int(i.strip()) for i in str(gesture).split(",") if i.strip().isdigit()]
                            except:
                                gesture = []
                
                        pattern_view = device(classNameMatches="(?i).*LockPatternView.*")
                        if pattern_view.exists:
                            bounds = pattern_view.info['bounds']
                            left, top, right, bottom = bounds['left'], bounds['top'], bounds['right'], bounds['bottom']
                            w = right - left
                            h = bottom - top
                            x_c = [left + w/6, left + w/2, left + w*5/6]
                            y_c = [top + h/6, top + h/2, top + h*5/6]
                        else:
                            width = device.info['displayWidth']
                            height = device.info['displayHeight']
                            x_c = [width*0.2, width*0.5, width*0.8]
                            y_c = [height*0.55, height*0.7, height*0.85]
                
                        points = []
                        for idx in gesture:
                            try:
                                idx_int = int(idx)
                                row = idx_int // 3
                                col = idx_int %% 3
                                points.append((x_c[col], y_c[row]))
                            except:
                                pass
                
                        if points:
                            device.swipe_points(points, 0.05)
                    else:
                        pwd = str(node.get("password", ""))
                        for char in pwd:
                            btn = device(text=char)
                            if not btn.exists: btn = device(description=char)
                            if btn.exists:
                                btn.click()
                            elif char.isdigit():
                                device.press(int(char) + 7)
                            time.sleep(0.2)
                        time.sleep(0.5)
                        enter_btn = device(textMatches="(?i)(确认|确定|完成|done|enter)")
                        if not enter_btn.exists: enter_btn = device(descriptionMatches="(?i)(确认|确定|完成|done|enter)")
                        if enter_btn.exists:
                            enter_btn.click()
                        else:
                            device.press("enter")
                # 屏幕亮度（todo: 屏幕亮度需要适配优化
                def handle_brightness(device, node):
                    brightness_raw = node.get("brightness", 50)
                    try:
                        val = float(brightness_raw)
                        val = max(0.0, min(100.0, val)) # 钳制在 0-100 之间
                    except (ValueError, TypeError):
                        val = 50.0  # 兜底安全值
                    # 强制关闭自动亮度
                    device.shell(["settings", "put", "system", "screen_brightness_mode", "0"])
                    # 将 0-100 转换为 0.0-1.0 的浮点数
                    float_val = val / 100.0
                    # 尝试使用现代 Android (9.0+) 的 cmd display 命令
                    # 该命令会自动处理非线性映射，完全对齐系统 UI 的亮度条
                    output, exit_code = device.shell(["cmd", "display", "set-brightness", str(float_val)])
                    # 如果 exit_code 不是 0，说明手机系统太老不支持此命令，自动降级到旧版 255 方案
                    if exit_code != 0:
                        v_255 = int(val * 255 / 100)
                        device.shell(["settings", "put", "system", "screen_brightness", str(v_255)])
                

                
                # 模拟通知
                def handle_notification(device, node):
                    title = str(node.get("notifTitle", "系统通知"))
                    content = str(node.get("notifContent", ""))
                    try:
                        res = device.shell(["cmd", "notification", "post", "-t", title, "mock_tag", content])
                        if hasattr(res, 'exit_code') and res.exit_code != 0:
                            device.toast.show(f"{title}: {content}")
                    except:
                        device.toast.show(f"{title}: {content}")
                
                # 切换网络
                def handle_network(device, node):
                    network_type = node.get("networkType", "")
                    if network_type == "WiFi":
                        device.shell(["cmd", "connectivity", "airplane-mode", "disable"])
                        device.shell(["settings", "put", "global", "airplane_mode_on", "0"])
                        device.shell(["am", "broadcast", "-a", "android.intent.action.AIRPLANE_MODE", "--ez", "state", "false"])
                        device.shell(["svc", "wifi", "enable"])
                        device.shell(["svc", "data", "disable"])
                    elif network_type == "移动数据":
                        device.shell(["cmd", "connectivity", "airplane-mode", "disable"])
                        device.shell(["settings", "put", "global", "airplane_mode_on", "0"])
                        device.shell(["am", "broadcast", "-a", "android.intent.action.AIRPLANE_MODE", "--ez", "state", "false"])
                        device.shell(["svc", "wifi", "disable"])
                        device.shell(["svc", "data", "enable"])
                    elif network_type == "飞行模式":
                        device.shell(["cmd", "connectivity", "airplane-mode", "enable"])
                        device.shell(["settings", "put", "global", "airplane_mode_on", "1"])
                        device.shell(["am", "broadcast", "-a", "android.intent.action.AIRPLANE_MODE", "--ez", "state", "true"])

                # 分支判断
                def handle_decision(device, node):
                    condition = str(node.get("condition", "")).strip()
                    if not condition:
                        return "R"
                    try:
                        import sys
                        local_ctx = {"device": device}
                        result = eval(condition, {"__builtins__": __builtins__}, local_ctx)
                        if result:
                            print(json.dumps({"type": "log", "message": f"条件检测 '{condition}' 解析为 True"}, ensure_ascii=False), flush=True)
                            return "B"
                        else:
                            print(json.dumps({"type": "log", "message": f"条件 '{condition}' 不满足 [False 分支]"}, ensure_ascii=False), flush=True)
                            return "R"
                    except Exception as e:
                        print(json.dumps({"type": "error", "message": f"条件检测抛出异常 '{condition}': {e}，默认走 False"}, ensure_ascii=False), flush=True)
                        return "R"

                # 循环执行 (计数循环 / 条件循环)
                def handle_loop(device, node, dispatcher):
                    loop_type = node.get("loopType", "计数循环")
                    children_graph = node.get("children", {})
                    child_nodes = children_graph.get("nodes", {})
                    child_start = children_graph.get("startNodeId", "")

                    if not child_nodes or not child_start:
                        print(json.dumps({"type": "log", "message": "循环节点无子节点，跳过"}, ensure_ascii=False), flush=True)
                        return

                    def run_iteration():
                        # 运行一次循环体内部的子状态机
                        cur = child_start
                        steps = 0
                        while cur and steps < 500:
                            steps += 1
                            child_data = child_nodes.get(cur)
                            if not child_data:
                                break
                            child_type = child_data.get("type", "unknown")
                            child_next = child_data.get("next")
                            print(json.dumps({"type": "log", "message": f"[循环体] 执行: {child_type} (节点 {cur})"}, ensure_ascii=False), flush=True)
                            handler = dispatcher.get(child_type)
                            branch = None
                            if handler and child_type != "loop":
                                try:
                                    branch = handler(device, child_data)
                                except Exception as e:
                                    print(json.dumps({"type": "error", "message": f"[循环体] 节点 {cur} 执行出错: {e}"}, ensure_ascii=False), flush=True)
                                    raise
                            if isinstance(child_next, dict):
                                branch_key = str(branch) if branch else "B"
                                cur = child_next.get(branch_key) or child_next.get("default")
                            else:
                                cur = child_next

                    if loop_type == "计数循环":
                        try:
                            n = int(node.get("iterations", 1))
                        except (ValueError, TypeError):
                            n = 1
                        print(json.dumps({"type": "log", "message": f"开始计数循环，共 {n} 次"}, ensure_ascii=False), flush=True)
                        for i in range(n):
                            print(json.dumps({"type": "log", "message": f"循环第 {i+1}/{n} 次"}, ensure_ascii=False), flush=True)
                            run_iteration()
                        print(json.dumps({"type": "log", "message": f"计数循环完成，共执行 {n} 次"}, ensure_ascii=False), flush=True)

                    elif loop_type == "条件循环":
                        condition = str(node.get("condition", "")).strip()
                        max_iters = 200
                        iteration = 0
                        print(json.dumps({"type": "log", "message": f"开始条件循环，条件: {condition}"}, ensure_ascii=False), flush=True)
                        while iteration < max_iters:
                            # 先检查条件
                            try:
                                local_ctx = {"device": device}
                                should_continue = eval(condition, {"__builtins__": __builtins__}, local_ctx)
                            except Exception as ce:
                                print(json.dumps({"type": "error", "message": f"条件循环条件求值失败: {ce}"}, ensure_ascii=False), flush=True)
                                break
                            if not should_continue:
                                print(json.dumps({"type": "log", "message": f"条件循环退出：条件 '{condition}' 不满足"}, ensure_ascii=False), flush=True)
                                break
                            iteration += 1
                            print(json.dumps({"type": "log", "message": f"条件循环第 {iteration} 次迭代"}, ensure_ascii=False), flush=True)
                            run_iteration()
                        if iteration >= max_iters:
                            print(json.dumps({"type": "log", "message": f"条件循环达到安全上限 {max_iters} 次，强制退出"}, ensure_ascii=False), flush=True)

                # --- 2. 注册动作字典 (路由表) ---
                ACTION_DISPATCHER = {
                    "click": handle_click,
                    "longPress": handle_long_press,
                    "swipe": handle_swipe,
                    "input": handle_input,
                    "wait": handle_wait,
                    "openApp": handle_open_app,
                    "closeApp": handle_close_app,
                    "foreground": handle_foreground,
                    "appState": handle_app_state,
                    "home": handle_home,
                    "back": handle_back,
                    "unlock": handle_unlock,
                    "brightness": handle_brightness,
                    "notification": handle_notification,
                    "network": handle_network,
                    "decision": handle_decision,
                    "loop": lambda device, node: handle_loop(device, node, ACTION_DISPATCHER)
                }
                
                def run_script():
                    # 1. 连接设备
                    print(json.dumps({"type": "log", "message": "正在连接设备..."}, ensure_ascii=False), flush=True)
                    try:
                        device = u2.connect()
                        print(json.dumps({"type": "init", "status": "success", "serial": device.serial}, ensure_ascii=False), flush=True)
                    except Exception as e:
                        print(json.dumps({"type": "init", "status": "error", "error": str(e)}, ensure_ascii=False), flush=True)
                        sys.exit(1)
                
                    # 给 Python 补充定义 JSON 常用常量字面量，防止作为字典抛出 NameError
                    null = None
                    true = True
                    false = False
                
                    # 2. 注入从前台配置精简与转译处理后的图节点 (作为引擎食粮)
                    flow_graph = %s
                
                    # 3. 初始化状态机和安全互斥锁
                    current_node_id = "%s"
                    jump_counters = {}
                    max_total_steps = 1000
                    step_count = 0
                
                    print(json.dumps({"type": "log", "message": "脚本状态机开始执行..."}, ensure_ascii=False), flush=True)
                
                    # --- 调试引擎配置 ---
                    is_debug_mode = %s
                    debug_lock = threading.Event()
                    
                    # 初始状态
                    if is_debug_mode:
                        debug_lock.clear()
                    else:
                        debug_lock.set()
                        
                    engine_running = True
                    
                    # 监听线程：死循环读取 stdin 解码前端发来的 JSON 指令
                    def debug_listener():
                        nonlocal is_debug_mode, engine_running
                        while engine_running:
                            line = sys.stdin.readline()
                            if not line:
                                break
                            try:
                                cmd = json.loads(line)
                                cmd_action = cmd.get("action")
                                
                                if cmd_action == "stop":
                                    engine_running = False
                                    debug_lock.set()  # 解锁主线程让其退出
                                    os._exit(0)
                                elif cmd_action == "pause":
                                    is_debug_mode = True
                                    # 通知并不直接挂起当前正在执行的动作，而是让下一次循环前置断点生效
                                elif cmd_action == "run":
                                    is_debug_mode = False
                                    debug_lock.set()
                                elif cmd_action == "step":
                                    is_debug_mode = True
                                    # 如果有覆盖运行代码参数则执行
                                    override_code = cmd.get("overrideCode")
                                    if override_code:
                                        try:
                                            exec(override_code, globals(), globals())
                                        except Exception as dev_err:
                                            print(json.dumps({"type": "log", "status": "error", "message": f"执行覆盖代码失败: {dev_err}"}, ensure_ascii=False), flush=True)
                                    debug_lock.set()  # 放行当前步，主线程走到下一轮又会被 clear 阻塞
                                elif cmd_action == "update_node":
                                    node_id = cmd.get("nodeId")
                                    node_data = cmd.get("nodeData")
                                    if node_id and node_data and isinstance(node_data, dict):
                                        if str(node_id) in flow_graph:
                                            flow_graph[str(node_id)].update(node_data)
                                            print(json.dumps({"type": "log", "message": f"[Debug] 成功热更新节点 {node_id} 参数"}, ensure_ascii=False), flush=True)
                            except Exception:
                                pass
                
                    listener_thread = threading.Thread(target=debug_listener, daemon=True)
                    listener_thread.start()
                
                    # 4. 状态机主循环 (核心路由)
                    while current_node_id and step_count < max_total_steps and engine_running:
                        step_count += 1
                        node_data = flow_graph.get(current_node_id)
                
                        if not node_data:
                            print(json.dumps({"type": "error", "message": f"节点 {current_node_id} 不存在，流程异常终止！"}, ensure_ascii=False), flush=True)
                            break
                
                        action_type = node_data.get("type", "unknown")
                        next_node = node_data.get("next")
                
                        # 将正在执行的节点传给前端
                        print(json.dumps({"type": "running_node", "nodeId": current_node_id, "action": action_type}, ensure_ascii=False), flush=True)
                
                        if is_debug_mode:
                            # 立即挂起锁：使主线程在此中断
                            debug_lock.clear()
                            details = {k: v for k, v in node_data.items() if k not in ["next", "type"]}
                            if details:
                                print(json.dumps({"type": "log", "message": f"[Debug] 断点：即将执行 {action_type}，参数: {details}"}, ensure_ascii=False), flush=True)
                            
                            # 向前端发送断点触发生效的信标
                            print(json.dumps({"type": "break", "nodeId": current_node_id, "action": action_type}, ensure_ascii=False), flush=True)
                            
                            # 主线程物理阻塞，等待 listener_thread 放行 (收到 step/run)
                            debug_lock.wait()
                            
                        if not engine_running:
                            break
                
                        # --- 行为解析区 ---
                        if action_type == "jump":
                            target = node_data.get("targetNodeId")
                            max_r_str = node_data.get("maxRetries", 1)
                            try:
                                max_r = int(max_r_str)
                            except:
                                max_r = 1
                
                            # 计数器检测避免死循环
                            jump_counters[current_node_id] = jump_counters.get(current_node_id, 0) + 1
                            if jump_counters[current_node_id] <= max_r:
                                print(json.dumps({"type": "log", "message": f"执行跳转 ({jump_counters[current_node_id]}/{max_r}) -> 跳转至节点: {target}"}, ensure_ascii=False), flush=True)
                                current_node_id = target
                            else:
                                print(json.dumps({"type": "log", "message": f"跳转节点达到最大重试次数 {max_r}，继续往下走。"}, ensure_ascii=False), flush=True)
                                current_node_id = next_node
                
                            time.sleep(0.1)
                            continue
                
                        handler_func = ACTION_DISPATCHER.get(action_type)
                        result = None
                        if handler_func:
                            try:
                                result = handler_func(device, node_data)
                                print(json.dumps({"type": "log", "message": f"节点 {current_node_id}({action_type}) 执行成功"}, ensure_ascii=False), flush=True)
                            except Exception as e:
                                print(json.dumps({"type": "error", "nodeId": current_node_id, "message": f"执行失败: {e}"}, ensure_ascii=False), flush=True)
                                traceback.print_exc()
                                raise e
                        elif action_type != "unknown":
                            print(json.dumps({"type": "log", "message": f"未知的动作类型: {action_type}"}, ensure_ascii=False), flush=True)
                
                        # 执行推进向下一步
                        if isinstance(next_node, dict):
                            # 分支节点：拥有多个分支走向，提取 handler_func 回传的标量
                            branch_key = str(result) if result else "B"
                            current_node_id = next_node.get(branch_key)
                            if not current_node_id:
                                current_node_id = next_node.get("default")
                        else:
                            current_node_id = next_node
                
                    if step_count >= max_total_steps:
                        print(json.dumps({"type": "error", "message": "警告：触发全局安全锁 (上限1000步)，强制停止以保护设备！"}, ensure_ascii=False), flush=True)
                    elif current_node_id is None:
                        print(json.dumps({"type": "log", "message": "所有节点执行完毕！"}, ensure_ascii=False), flush=True)
                
                if __name__ == "__main__":
                    run_script()
                """, flowGraphJson, startNodeId, isDebug ? "True" : "False");

        return template;
    }
}
