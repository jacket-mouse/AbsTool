# ============================================================
# 自动生成的 Android 行为模拟脚本 (State Machine 核心引擎驱动)
# 关键配置区域（由生成器自动填充，请勿手动修改标注行）
# ============================================================
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
    try:
        dur_sec = float(node.get("duration", 1000)) / 1000.0
    except (ValueError, TypeError):
        dur_sec = 1.0
    if target_type == "元素 ID" and element_id:
        elem = device(resourceId=element_id)
        if elem.wait(timeout=5.0):
            elem.long_click(duration=dur_sec)
        else:
            raise Exception(f"长按失败：5秒内未找到元素 ID [{element_id}]")
    elif target_type == "坐标":
        x = node.get("x", 0)
        y = node.get("y", 0)
        canvas_width = 1080.0
        canvas_height = 1920.0
        real_width = device.info['displayWidth']
        real_height = device.info['displayHeight']
        real_x = int((float(x) / canvas_width) * real_width)
        real_y = int((float(y) / canvas_height) * real_height)
        real_x = max(0, min(real_x, real_width - 1))
        real_y = max(0, min(real_y, real_height - 1))
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
    except Exception:
        dur = 0.25
    device.swipe_ext("up", scale=0.8)
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
    except Exception:
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

# 获取 APP 当前状态
def handle_app_state(device, node):
    pkg = node.get("packageName", "")
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
    pwd = str(node.get("password", ""))
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
def handle_brightness(device, node):
    brightness_raw = node.get("brightness", 50)
    try:
        val = float(brightness_raw)
        val = max(0.0, min(100.0, val))
    except (ValueError, TypeError):
        val = 50.0
    device.shell(["settings", "put", "system", "screen_brightness_mode", "0"])
    float_val = val / 100.0
    output, exit_code = device.shell(["cmd", "display", "set-brightness", str(float_val)])
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
    except Exception:
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

# 🌟 极简版：计数循环执行器 (Stateful)
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

