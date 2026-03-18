# ============================================================
# 自动生成的 Android 行为模拟脚本 (State Machine 核心引擎驱动)
# 关键配置区域（由生成器自动填充，请勿手动修改标注行）
# ============================================================
import re

import uiautomator2 as u2
import time
import random
import json
import traceback
import sys
import threading
import os

# JSON 兼容
null = None
true = True
false = False



# --- 关键配置（由生成器填充）---
_FLOW_GRAPH_ = {} # __FLOW_GRAPH__
_START_NODE_ID_ = ""  # __START_NODE__
_IS_DEBUG_MODE_ = True  # __IS_DEBUG__
debug_lock = threading.Event()
engine_running = True
runtime_state = {}


# --- 1. 定义各个具体动作的执行函数 (Handlers) ---
def handle_click(device, node_data):
    props = node_data.get("properties", {})

    target_type = props.get("targetType", "")
    xpath_val = props.get("elementId", "")

    if target_type in ["XPath", "元素 ID"]:
        if not xpath_val:
            raise Exception(f"点击失败：目标类型为 {target_type}，但未提供定位参数")

        # 使用 uiautomator2 的 xpath 选择器
        elem_selector = device.xpath(xpath_val)

        if elem_selector.wait(5.0):
            # 普通点击不需要计算中心点，uiautomator2 的 xpath 对象直接支持 .click()
            elem_selector.click()
        else:
            raise Exception(f"点击失败：5秒内未找到目标 [{xpath_val}]")

    elif target_type == "坐标":
        x = props.get("x", 0)
        y = props.get("y", 0)

        device.click(x, y)

    else:
        raise Exception(f"点击节点配置错误：未知的目标类型 [{target_type}]")

# 长按
def handle_long_press(device, node_data):
    props = node_data.get("properties", {})

    target_type = props.get("targetType", "")
    xpath_val = props.get("elementId", "")

    try:
        dur_sec = float(props.get("duration", 1000)) / 1000.0
    except (ValueError, TypeError):
        dur_sec = 1.0

    if target_type == "元素 ID" and xpath_val:
        if not xpath_val:
            raise Exception("长按失败：目标类型为 XPath，但未提供 xpath 参数")

        # 使用 uiautomator2 的 xpath 选择器
        elem_selector = device.xpath(xpath_val)

        # wait(5.0) 如果找到元素会返回真实的 element 对象，找不到返回 None
        if elem_selector.wait(5.0):
            # 获取元素的中心点坐标，转化为物理坐标点击（完美兼容自定义 duration）
            center_x, center_y = elem_selector.get().center()
            device.long_click(center_x, center_y, duration=dur_sec)
        else:
            raise Exception(f"长按失败：5秒内未找到 XPath [{xpath_val}]")

    elif target_type == "坐标":
        x = props.get("x", 0)
        y = props.get("y", 0)
        device.long_click(x, y, duration=dur_sec)
    else:
        raise Exception("长按节点配置错误：未知的目标类型或缺少参数")

# 滑动
def handle_swipe(device, node):
    node = node.get("properties", {})
    sx = node.get("startX", 0)
    sy = node.get("startY", 0)
    ex = node.get("endX", 0)
    ey = node.get("endY", 0)
    steps_str = node.get("steps", 50)
    try:
        dur = float(steps_str) * 0.005
    except Exception:
        dur = 0.25
    device.swipe_ext("up", scale=0.8)
    device.swipe(int(sx), int(sy), int(ex), int(ey), duration=dur)

# 输入
def handle_input(device, node_data):
    props = node_data.get("properties", {})

    text = str(props.get("text", ""))
    xpath_val = props.get("xpath", props.get("elementId", ""))

    if xpath_val:
        # 使用 uiautomator2 的 xpath 选择器
        elem_selector = device.xpath(xpath_val)

        # wait(5.0) 寻找输入框，最多等 5 秒
        if elem_selector.wait(5.0):
            # uiautomator2 的 xpath 选择器直接支持 set_text 方法
            elem_selector.set_text(text)
        else:
            raise Exception(f"输入失败：5秒内未找到输入框 [{xpath_val}]")
    else:
        raise Exception("输入失败：未提供 XPath 定位参数")

# 等待
def handle_wait(device, node):
    props = node.get("properties", {})
    duration_str = props.get("duration", "1000")
    dur_sec = float(duration_str) / 1000.0
    print(json.dumps({"type": "log", "message": f"等待{duration_str}ms"}, ensure_ascii=False), flush=True)
    time.sleep(dur_sec + random.uniform(0, 0.3))

# 打开 app
def handle_open_app(device, node):
    props = node.get("properties", {})
    pkg = props.get("packageName", props.get("packagename", ""))

    if pkg:
        # uiautomator2 原生方法，直接拉起对应包名的 App
        device.app_start(pkg)
    else:
        # 🌟 细节 2：如果没有包名，绝不默默跳过，直接抛异常给前端
        raise Exception("打开应用失败：未提供包名 (packageName) 参数")

# 关闭 APP
def handle_close_app(device, node):
    props = node.get("properties", {})
    pkg = props.get("packageName", props.get("packagename", ""))
    if pkg:
        device.app_stop(pkg)

# 切换前台
def handle_foreground(device, node):
    props = node.get("properties", {})
    pkg = props.get("packageName", props.get("packagename", ""))
    if pkg:
        device.app_start(pkg, stop=False)
        print(json.dumps({"type": "log", "message": f"系统提示件: 切换包名 {pkg} 至前台操作完毕"}, ensure_ascii=False), flush=True)

# 获取 APP 当前状态
def handle_app_state(device, node):
    props = node.get("properties", {})
    pkg = props.get("packageName", props.get("packagename", ""))
    if not pkg:
        return "R3"
    current = device.app_current()
    if current.get("package") == pkg:
        state = "前台"
        port = "R1"
    else:
        try:
            pid = device.shell(["pidof", pkg]).output.strip()
            if pid:
                state = "后台运行中"
                port = "R2"
            else:
                state = "未运行"
                port = "R3"
        except Exception:
            state = "未知或后台"
            port = "R3"
    print(json.dumps({"type": "log", "message": f"检测到应用 [{pkg}] 当前状态: {state}"}, ensure_ascii=False), flush=True)
    return port

# 解锁屏幕
def handle_unlock(device, node):
    device.screen_on()
    device.swipe_ext("up", scale=0.8)
    time.sleep(1)
    pwd = str(node.get("properties", "").get("password", ""))
    for char in pwd:
        btn = device(text=char)
        if not btn.exists:
            btn = device(description=char)
        if btn.exists:
            btn.click()
        elif char.isdigit():
            device.press(int(char) + 7)
        time.sleep(0.2)
    time.sleep(0.5)
    enter_btn = device(textMatches="(?i)(确认|确定|完成|done|enter)")
    if not enter_btn.exists:
        enter_btn = device(descriptionMatches="(?i)(确认|确定|完成|done|enter)")
    if enter_btn.exists:
        enter_btn.click()
    else:
        device.press("enter")

# 屏幕亮度
def handle_brightness(device, node_data):
    props = node_data.get("properties", {})
    brightness_raw = props.get("brightness", 50)

    try:
        val = float(brightness_raw)
        val = max(0.0, min(100.0, val))  # 限制在 0-100 之间
    except (ValueError, TypeError):
        val = 50.0

    # 计算不同安卓版本所需的亮度值格式
    float_val = val / 100.0  # 用于较新系统的 0.0 - 1.0 格式
    int_val = int(val * 255 / 100)  # 传统数据库 0 - 255 格式

    try:
        # 1. 强制关闭自动亮度 (如果不关，修改会在一秒后被传感器覆盖回去)
        device.shell("settings put system screen_brightness_mode 0")
        # 2. 写入传统整型配置 (修改系统设置数据库，绝大部分国产机型靠这个生效)
        device.shell(f"settings put system screen_brightness {int_val}")
        # 3. 写入新版浮点型配置 (修改 Android 11+ 的数据库)
        device.shell(f"settings put system screen_brightness_float {float_val}")
        # 🌟 修复 2：绝不能把 int_val (如 127) 传给 cmd display！
        # 只用 float_val 去通知系统立刻刷新亮度，避免触发 >1.0 拉满的 Bug
        device.shell(f"cmd display set-brightness {float_val}")

    except Exception as e:
        # 亮度调节不应该阻断主流程，使用软隔离
        print(json.dumps({"type": "log", "message": f"⚠️ 屏幕亮度调节部分受限: {e}"}, ensure_ascii=False), flush=True)

# 模拟通知
def handle_notification(device, node):
    props = node.get("properties", {})
    title = str(props.get("notifTitle", "系统通知"))
    content = str(props.get("notifContent", ""))
    try:
        res = device.shell(["cmd", "notification", "post", "-t", title, "mock_tag", content])
        if hasattr(res, 'exit_code') and res.exit_code != 0:
            device.toast.show(f"{title}: {content}")
    except Exception:
        device.toast.show(f"{title}: {content}")

# 切换网络
def handle_network(device, node):
    props = node.get("properties", {})
    network_type = props.get("networkType", "")
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
# B true R false
def handle_decision(device, node):
    props = node.get("properties", {})
    detection_type = props.get("detectionType", "")
    if detection_type == "应用状态":
        app_package = props.get("appPackageName", "")
        app_running_state = props.get("appRunningState", "")
        if not app_package:
            print(json.dumps({"type": "log", "message": f"不存在的包名"},ensure_ascii=False), flush=True)
            return "R"
        current = device.app_current()
        if app_running_state == "前台运行":
            if current and current.get("package") == app_package:
                print(json.dumps({"type": "log", "message": f"{app_package}在前台运行"}, ensure_ascii=False), flush=True)
                return "B"
            else:
                print(json.dumps({"type": "log", "message": f"{app_package}不在前台运行"}, ensure_ascii=False),
                      flush=True)
                return "R"

        else:
            pid_info = device.shell(f"pidof {app_package}").output.strip()
            if pid_info and app_running_state == "后台运行":
                print(json.dumps({"type": "log", "message": f"{app_package}在后台运行"}, ensure_ascii=False),
                      flush=True)
                return "B"
            elif not pid_info and app_running_state == "未运行":
                print(json.dumps({"type": "log", "message": f"{app_package}未运行"}, ensure_ascii=False),
                      flush=True)
                return "B"
            elif pid_info and app_running_state == "未运行":
                print(json.dumps({"type": "log", "message": f"{app_package}在后台运行"}, ensure_ascii=False),
                      flush=True)
                return "R"
            else:
                print(json.dumps({"type": "log", "message": f"{app_package}未运行"}, ensure_ascii=False))
                return "R"

    elif detection_type == "设备状态":
        device_state_type = props.get("deviceStateType", "")
        if device_state_type == "网络类型":
            target_networks = props.get("networkTypes", "")  # 假设前端传来 ["WiFi", "数据网络"]

            # 获取 WiFi IP (如果有 IP 说明连了 WiFi)
            wlan_ip = device.wlan_ip
            has_wifi = bool(wlan_ip)

            # 简单粗暴的探针逻辑：
            if "WiFi" == target_networks:
                if has_wifi:
                    print(json.dumps({"type": "log", "message": "WiFi 模式"}, ensure_ascii=False), flush=True)
                    return "B"
                else:
                    return "R"
            elif "数据网络" == target_networks:
                if not has_wifi:
                    # 如果没连 WiFi，但能 ping 通百度，粗略认为是数据网络
                    ping_res = device.shell("ping -c 1 -w 2 223.5.5.5").exit_code
                    if ping_res == 0:
                        print(json.dumps({"type": "log", "message": "数据模式"}, ensure_ascii=False), flush=True)
                        return "B"
                    else:
                        return "R"
                else:
                    return "R"
            elif "飞行模式" == target_networks:
                if has_wifi:
                    return "R"
                else:
                    ping_res = device.shell("ping -c 1 -w 2 223.5.5.5").exit_code
                    if ping_res == 0:
                        return "R"
                    else:
                        return "B"

        elif device_state_type == "电池电量":
            battery_op = props.get("batteryOp", ">")
            battery_val = props.get("batteryValue")

            if battery_val is not None:
                battery_val = float(battery_val)
                # 调用安卓底层电池接口
                battery_info = device.shell("dumpsys battery").output
                match = re.search(r"level:\s*(\d+)", battery_info)

                if match:
                    current_level = float(match.group(1))
                    # 数学逻辑映射
                    if battery_op == ">" and current_level > battery_val:
                        return "B"
                    elif battery_op == "<" and current_level < battery_val:
                        return "B"
                    elif battery_op == "==" and current_level == battery_val:
                        return "B"
                    elif battery_op == ">=" and current_level >= battery_val:
                        return "B"
                    elif battery_op == "<=" and current_level <= battery_val:
                        return "B"
            return "R"
        elif device_state_type == "屏幕开启":
            target_screen = props.get("screenOn", "开启")  # "开启" 或 "关闭"
            # uiautomator2 原生自带了极速的屏幕状态探针
            is_screen_on = device.info.get("screenOn", False)

            if target_screen == "开启" and is_screen_on:
                return "B"
            elif target_screen == "关闭" and not is_screen_on:
                return "B"
            return "R"
        elif device_state_type == "正在充电":
            target_charging = props.get("charging", "是")  # "是" 或 "否"
            battery_info = device.shell("dumpsys battery").output

            # 在 dumpsys battery 中，status: 2 代表正在充电，5 代表充满依然插着电
            is_charging = "status: 2" in battery_info or "status: 5" in battery_info or "AC powered: true" in battery_info or "USB powered: true" in battery_info

            if target_charging == "是" and is_charging:
                return "B"
            elif target_charging == "否" and not is_charging:
                return "B"
            return "R"
    elif detection_type == "元素存在性":
        xpath = props.get("xpath", "")
        if xpath:
            # 不要用瞬间检测，给 UI 渲染留 2 秒的缓冲时间
            # wait(2.0) 如果在 2 秒内找到了元素，会返回 Element 对象 (隐式转换为 True)
            # 如果 2 秒后还没找到，返回 None (隐式转换为 False)
            if device.xpath(xpath).wait(2.0):
                return "B"
        else:
            print(json.dumps({"type": "log", "message": "分支判断警告: 元素存在性检测未提供 xpath 参数"},
                             ensure_ascii=False), flush=True)

# 计数循环执行器 (Stateful)
def handle_loop(device, node, current_node_id):
    global runtime_state

    try:
        max_iter = int(node.get("properties").get("iterations", 1))
    except (ValueError, TypeError):
        max_iter = 1

    # 获取当前循环记忆，没有则默认 0
    current_count = runtime_state.get(current_node_id, 0)

    if current_count < max_iter:
        runtime_state[current_node_id] = current_count + 1
        print(
            json.dumps({"type": "log", "message": f"↻ 循环进度: {current_count + 1} / {max_iter}"}, ensure_ascii=False),
            flush=True)
        return "Body"  # 告诉主引擎顺着 LoopBody 端口走
    else:
        # 循环结束，清空记忆（为了将来可能再次进入该循环）
        runtime_state[current_node_id] = 0
        print(json.dumps({"type": "log", "message": f"✓ 循环完成，跳出"}, ensure_ascii=False), flush=True)
        return "R"  # 告诉主引擎顺着 Completed 端口走


# --- 2. 注册动作字典 ---
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
    "unlock": handle_unlock,
    "brightness": handle_brightness,
    "notification": handle_notification,
    "network": handle_network,
    "decision": handle_decision,
    "loop": handle_loop,
}

def run_script():
    global is_debug_mode, debug_lock, engine_running
    # 设备连接 输出信息至 stdout
    print(json.dumps({"type": "log", "message": "正在连接设备..."}, ensure_ascii=False), flush=True)
    try:
        device = u2.connect()
        print(json.dumps({"type": "init", "status": "success", "serial": device.serial}, ensure_ascii=False), flush=True)
    except Exception as e:
        print(json.dumps({"type": "init", "status": "error", "error": str(e)}, ensure_ascii=False), flush=True)
        sys.exit(1)



    # 使用配置区的关键变量
    flow_graph = _FLOW_GRAPH_
    current_node_id = _START_NODE_ID_
    jump_counters = {}
    runtime_state.clear() # 初始化
    max_total_steps = 50000
    step_count = 0

    print(json.dumps({"type": "log", "message": "脚本状态机开始执行..."}, ensure_ascii=False), flush=True)

    is_debug_mode = _IS_DEBUG_MODE_ # True 则可以一个个执行

    if is_debug_mode:
        debug_lock.clear() # 线程阻塞信号，之后若遇到 wait 则阻塞
    else:
        debug_lock.set() # 线程通过状态，之后若遇到 wait 直接通过

    def debug_listener():
        # is_debug_mode 决定下一个节点执行完之后要不要暂停
        # debug_lock 决定当前线程现在能不能继续走 如果上一次没有暂停(is_debug_mode = False) 这一个就没用
        """
            命令      is_debug_mode    debug_lock    效果
            ────────  ─────────────    ──────────    ──────────────────────
            stop      False            set()         进程直接退出
            pause     True             不动          当前节点跑完，下个节点暂停
            run       False            set()         立即解除阻塞 + 后续不再暂停
            step      True             set()         立即解除阻塞 + 下个节点还暂停
        """
        global is_debug_mode, debug_lock, engine_running
        while engine_running:
            line = sys.stdin.readline()
            if not line:
                break # 线程停止运行
            try:
                cmd = json.loads(line)
                cmd_action = cmd.get("action")
                override_code = cmd.get("overrideCode")
                if override_code:
                    try:
                        new_node_data = json.loads(override_code)
                        # 更新当前在主循环里正在处理的 node_data（因为它们是指向同一个字典的引用，或者你可以使用 global 更新 _FLOW_GRAPH_）
                        _FLOW_GRAPH_[current_node_id].update(new_node_data)
                        print(json.dumps({"type": "log", "message": f"✨ 成功应用临时覆盖参数！"}, ensure_ascii=False),
                              flush=True)
                    except Exception as e:
                        print(json.dumps({"type": "error", "message": f"应用覆盖参数失败: {e}"}, ensure_ascii=False),
                              flush=True)
                        
                if cmd_action == "stop":
                    engine_running = False # 该线程停止运行
                    debug_lock.set()
                    os._exit(0)
                elif cmd_action == "pause":
                    is_debug_mode = True
                    # 不写 debug_lock 默认阻塞
                elif cmd_action == "run":
                    is_debug_mode = False
                    debug_lock.set()
                elif cmd_action == "step":
                    is_debug_mode = True
                    debug_lock.set()

            except Exception:
                pass

    # 启动了一个后台线程 读取标准输入（前端）
    # 该线程只会执行 debug_listener 一个函数
    # daemon = True 主线程结束监听线程也结束
    listener_thread = threading.Thread(target=debug_listener, daemon=True)
    listener_thread.start()
    call_stack = []

    while current_node_id and step_count < max_total_steps and engine_running:
        step_count += 1
        node_data = flow_graph.get(current_node_id)

        if not node_data:
            print(json.dumps({"type": "error", "message": f"节点 {current_node_id} 不存在，流程异常终止！"}, ensure_ascii=False), flush=True)
            break

        action_type = node_data.get("type", "unknown")
        next_node = node_data.get("next")

        print(json.dumps({"type": "running_node", "nodeId": current_node_id, "action": action_type}, ensure_ascii=False), flush=True)

        if is_debug_mode:
            debug_lock.clear() # 阻塞

            print(json.dumps({
                "type": "break",
                "nodeId": current_node_id,
                "action": action_type,
                # 把当前节点的原始数据发给前端，前端调试台的输入框里会显示它
                "code": json.dumps(node_data, ensure_ascii=False)
            }, ensure_ascii=False), flush=True)

            # 除了 next 和 type 的其他属性都存到 details 里
            details = {k: v for k, v in node_data.items() if k not in ["next", "type"]}
            if details:
                print(json.dumps({"type": "log", "message": f"[Debug] 断点：即将执行 {action_type}，参数: {details}"}, ensure_ascii=False), flush=True)
            debug_lock.wait()

        if not engine_running:
            break

        if action_type == "jump":
            target = node_data.properties.get("targetNodeId")
            max_r = int(node_data.properties.get("maxRetries", 1)) # 可动态设置最大跳转次数
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
                if action_type == "loop":
                    result = handler_func(device, node_data, current_node_id)
                else:
                    result = handler_func(device, node_data)
                    print(json.dumps({"type": "log", "message": f"节点 {current_node_id}({action_type}) 执行成功"}, ensure_ascii=False), flush=True)
            except Exception as e:
                print(json.dumps({"type": "error", "nodeId": current_node_id, "message": f"执行失败: {e}"}, ensure_ascii=False), flush=True)
                traceback.print_exc()
                raise e
        elif action_type != "unknown":
            print(json.dumps({"type": "log", "message": f"未知的动作类型: {action_type}"}, ensure_ascii=False), flush=True)

        # 🌟 如果当前是 Loop 节点且决定走 Body，把它自己压入栈
        if action_type in ["loop"] and isinstance(result, str) and result in ["Body"]:
            call_stack.append(current_node_id)

        # next_node_id 逻辑
        # 所有的节点的 next 都是字典
        if isinstance(next_node, dict):
            if node_data.get("type") == "loop": # 循环节点
                # Body & R
                branch_key = str(result) if result else "R"
                current_node_id = next_node.get(branch_key)
            elif node_data.get("type") == "decision": # 判断节点 B True R False
                branch_key = str(result) if result in ["B", "R"] else "R"
                other_key = "R" if branch_key == "B" else "B" # 获取到另一个分支

                current_node_id = next_node.get(branch_key)
                other_node_id = next_node.get(other_key)

                # 防止判断节点两个有没连的
                cur_type = flow_graph.get(current_node_id, {}).get("type") if current_node_id else None
                other_type = flow_graph.get(other_node_id, {}).get("type") if other_node_id else None

                if cur_type != "loop" and other_type == "loop": # 走了不是 loop 的那一个分支需要 pop 一下退出循环
                    if call_stack: # 防止条件判断不在循环中
                        popped_loop = call_stack.pop()
                    print(json.dumps({"type": "log", "message": f"弹出栈{popped_loop}"}, ensure_ascii=False), flush=True)

                # if not current_node_id and call_stack:
                #     next_node.get(flow_graph.get(call_stack.pop()).get("next").get("R"))

            else: # 普通节点 一个分支 R
                branch_key = "R"
                current_node_id = next_node.get(branch_key)

        # 如果发现没路走了（current_node_id 为空），看看栈里有没有
        if not current_node_id and call_stack:
            current_node_id = call_stack.pop()  # 弹出栈顶的循环节点，强制跳回去！
            print(json.dumps({"type": "log", "message": f"↩️ 触发隐式回弹，返回循环节点: {current_node_id}"},
                                     ensure_ascii=False), flush=True)

    if step_count >= max_total_steps:
        print(json.dumps({"type": "error", "message": "警告：触发全局安全锁 (上限1000步)，强制停止以保护设备！"}, ensure_ascii=False), flush=True)
    elif current_node_id is None:
        print(json.dumps({"type": "log", "message": "所有节点执行完毕！"}, ensure_ascii=False), flush=True)

if __name__ == "__main__":
    run_script()

