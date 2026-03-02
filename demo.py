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

# 节点：1772161913876 (unlock)
try:
    # 密码解锁
    device.screen_on()
    device.swipe_ext("up", scale=0.8)
    time.sleep(1)
    
    pwd = "139699"
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
    print("节点1772161913876执行成功")
except Exception as e:
    print(f"节点1772161913876执行失败: {str(e)}")
    raise

# 节点：1772267050904 (openApp)
try:
    device.app_start("com.tencent.mobileqq")
    print("节点1772267050904执行成功")
except Exception as e:
    print(f"节点1772267050904执行失败: {str(e)}")
    raise

# 节点：1772267337570 (click)
try:
    device.click(815, 700)
    print("节点1772267337570执行成功")
except Exception as e:
    print(f"节点1772267337570执行失败: {str(e)}")
    raise

# 节点：1772269633274 (input)
try:
    device(resourceId="com.tencent.mobileqq:id/input").set_text("你好")
    print("节点1772269633274执行成功")
except Exception as e:
    print(f"节点1772269633274执行失败: {str(e)}")
    raise

# 节点：1772267660969 (click)
try:
    device(resourceId="com.tencent.mobileqq:id/send_btn").click()
    print("节点1772267660969执行成功")
except Exception as e:
    print(f"节点1772267660969执行失败: {str(e)}")
    raise

# 节点：1772269142642 (longPress)
try:
    device(resourceId="com.tencent.mobileqq:id/v8e").long_click(duration=1.0)
    print("节点1772269142642执行成功")
except Exception as e:
    print(f"节点1772269142642执行失败: {str(e)}")
    raise

# 节点：1772269412031 (click)
try:
    device(resourceId="com.tencent.mobileqq:id/send_btn").click()
    print("节点1772269412031执行成功")
except Exception as e:
    print(f"节点1772269412031执行失败: {str(e)}")
    raise

# 节点：1772269400760 (longPress)
try:
    device.long_click(735, 585, 1.0)
    print("节点1772269400760执行成功")
except Exception as e:
    print(f"节点1772269400760执行失败: {str(e)}")
    raise

# 节点：1772269372432 (swipe)
try:
    device.swipe(685, 1195, 600, 2390, duration=0.25)
    print("节点1772269372432执行成功")
except Exception as e:
    print(f"节点1772269372432执行失败: {str(e)}")
    raise