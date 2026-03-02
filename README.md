现在脚本解析的思路为

1. 首先将前端传回的 Json 格式的字符串进行简化，将一些没用的属性（如位置信息）删除
2. 将上述简化过的字符串嵌入下面的 Python 脚本（仍不完善，需要完善具体操作的 Python 代码）中，生成最终的 Python 脚本，之后前端脚本若发生修改，则只需更改 Python 脚本中的嵌入字符串即可

```python
import uiautomator2 as u2
import time
import random

def run_script():
    # 1. 连接设备
    print("正在连接设备...")
    d = u2.connect()

    # 2. 注入从 JSON 解析来的图结构数据 (这就是你后端的翻译工作，直接把JSON灌进来)
    flow_graph = {
        "node_01": {"type": "click", "x": 0.5, "y": 0.5, "next": "node_02"},
        "node_02": {"type": "wait", "time": 2, "next": "node_03"},
        "node_03": {"type": "jump", "target": "node_01", "max_retries": 3, "next": None}
    }

    # 3. 初始化状态机和安全锁
    current_node_id = "node_01"
    jump_counters = {}       # 记录每个跳转节点跳了多少次
    max_total_steps = 1000   # 绝对安全锁：最多执行1000步，防止手机死机报错
    step_count = 0

    # 4. 状态机主循环 (核心路由)
    while current_node_id and step_count < max_total_steps:
        step_count += 1
        node_data = flow_graph.get(current_node_id)

        if not node_data:
            print(f"节点 {current_node_id} 不存在，流程异常终止！")
            break

        action_type = node_data['type']

        # --- 行为解析区 ---
        if action_type == "click":
            # 真实坐标转换逻辑 (假设基准分辨率宽1080，高1920)
            real_x = int(node_data['x'] * d.info['displayWidth'])
            real_y = int(node_data['y'] * d.info['displayHeight'])
            print(f"执行点击: ({real_x}, {real_y})")
            d.click(real_x, real_y)
            current_node_id = node_data['next'] # 流转到下一步

        elif action_type == "wait":
            wait_time = node_data['time']
            # 加入一点拟人化随机扰动 (0到0.5秒之间)
            actual_wait = wait_time + random.uniform(0, 0.5)
            print(f"执行等待: {actual_wait:.2f} 秒")
            time.sleep(actual_wait)
            current_node_id = node_data['next']

        elif action_type == "jump":
            # --- 跳转节点的安全判定逻辑 ---
            target = node_data['target']
            max_r = node_data.get('max_retries', 1)

            # 计数器加1
            jump_counters[current_node_id] = jump_counters.get(current_node_id, 0) + 1

            if jump_counters[current_node_id] <= max_r:
                print(f"执行跳转 ({jump_counters[current_node_id]}/{max_r}) -> 返回节点: {target}")
                current_node_id = target # 核心：直接把指针指向目标节点
            else:
                print(f"跳转节点已达到最大重试次数 {max_r}，跳出循环，继续往下走。")
                current_node_id = node_data.get('next') # 走到跳转节点的下方连线

    if step_count >= max_total_steps:
        print("警告：触发全局安全锁，强制停止以保护设备！")
    else:
        print("执行完毕！")

if __name__ == "__main__":
    run_script()

```

3. 之后对于脚本执行和调试，则通过检测脚本执行到哪一个节点，在前端进行可视化展示（该展示不包括Python 脚本中的具体操作，仅包括脚本执行到哪一个节点）

