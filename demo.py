# 自动生成的Android行为模拟脚本（适配UiAutomator2）
from uiautomator2 import connect
import time

# 设备初始化
try:
    device = connect() # 默认连接当前连入电脑的设备
    print("设备连接成功:", device.serial)
except Exception as e:
    print(f"设备连接失败: {e}")
    exit(1)

# 节点：1772156477990 (openApp)
try:
    device.app_start("com.tencent.mobileqq")
    print("节点1772156477990执行成功")
except Exception as e:
    print(f"节点1772156477990执行失败: {str(e)}")
    raise

# 脚本执行完成
print("所有节点执行完毕")