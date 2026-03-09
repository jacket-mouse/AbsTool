在可视化编程和 RPA（机器人流程自动化）领域，实现脚本与脚本之间的逻辑复用，最标准、最优雅的做法是引入**“子流程（Sub-flow / Sub-script）”节点**。

这就像在编程中“封装一个函数”然后在别处“调用这个函数”一样。

以下是将其落地到你的 Vue + GoJS + Python 架构中的完整设计方案：

### 一、 核心概念：“子脚本节点” (Sub-Script Node)

在画布上，你不应该通过复制粘贴几十个节点来实现复用（那叫代码冗余），而是提供一个特殊的动作节点，名叫 **“调用子脚本”**。

- **视觉体现**：在 GoJS 画布中，这个节点可以设计得比普通节点更宽大，图标使用类似“文件夹”或“嵌套方块”的样子，背景色区分开（比如深蓝色）。节点上直接显示被调用脚本的名称（例如：`[调用] 淘宝自动登录`）。
- **交互体现**：当用户点击这个节点时，右侧的属性面板弹出一个下拉框，下拉框的数据源是**数据库中其他已保存的脚本列表**。用户从中选择一个即可。

### 二、 数据结构与依赖打包 (JSON)

当用户配置好并保存时，这个节点在 `logic_json` 中的结构非常简单：

```json
{
  "node_888": {
    "type": "sub_script",
    "targetScriptId": "script_login_001",
    "scriptName": "淘宝自动登录",
    "next": "node_889"
  }
}
```

**后端（Java）的关键处理：打包依赖**
当用户点击“运行”主脚本时，Java 后端不能只把主脚本的 JSON 发给 Python。Java 需要做一个“依赖收集”：

1. 扫描主脚本，发现它引用了 `script_login_001`。
2. 去数据库查出 `script_login_001` 的 `logic_json`。
3. 把主图和所有的子图打包成一个大字典发给 Python 引擎。

发给 Python 的数据结构应该是这样的：

```json
{
  "main_flow": { "start_node": "...", "nodes": { ... } },
  "sub_flows": {
    "script_login_001": { "start_node": "...", "nodes": { ... } }
  }
}

```

### 三、 执行引擎的改造：引入“调用栈 (Call Stack)”

为了让你的 Python 状态机能执行子脚本，并且执行完后还能**“活着回来”**继续往下走，你需要对之前的路由引擎做一次升维：引入**递归**或**调用栈**。

下面是 Python 引擎处理 `sub_script` 的核心改造代码：

```python
# 改造后的执行引擎，支持执行特定的 flow_graph
def execute_flow(device, flow_nodes, start_node_id, sub_flows_dict):
    current_node_id = start_node_id
    step_count = 0
    max_steps = 1000

    while current_node_id and step_count < max_steps:
        step_count += 1
        node = flow_nodes.get(current_node_id)
        if not node: break

        action_type = node.get("type")

        # --- 新增：子脚本处理逻辑 ---
        if action_type == "sub_script":
            target_id = node.get("targetScriptId")
            emit_event("log", message=f"开始进入子脚本: {node.get('scriptName')}")

            sub_flow_data = sub_flows_dict.get(target_id)
            if sub_flow_data:
                # 【核心】：递归调用 execute_flow，开启新的状态机副本
                sub_nodes = sub_flow_data.get("nodes", {})
                sub_start = sub_flow_data.get("start_node")

                # 等待子脚本执行完毕 (阻塞当前线程)
                execute_flow(device, sub_nodes, sub_start, sub_flows_dict)

                emit_event("log", message=f"子脚本 {node.get('scriptName')} 执行完毕，返回主流程")
            else:
                emit_event("error", message=f"找不到依赖的子脚本: {target_id}")
                raise Exception("缺失子脚本")

        # --- 其他普通节点逻辑 (click, wait, jump等) ---
        elif action_type == "click":
            # ... 执行点击 ...
            pass

        # 走向下一步
        current_node_id = node.get("next")

```

### 四、 避坑与体验优化（前端必须要做的限制）

引入子脚本后，你的工具能力成倍提升，但也引入了编程界最可怕的灾难：**循环依赖（死循环爆炸）**。

- **问题场景**：脚本 A 调用了 脚本 B。用户又去编辑 脚本 B，让它调用 脚本 A。
- **后果**：运行时，A调B，B调A，瞬间栈溢出（Stack Overflow），工具崩溃。
- **前端解决方案**：

1. 在“调用子脚本”的下拉列表中，**必须过滤掉当前正在编辑的脚本**（不许自己调自己）。
2. （进阶）在保存脚本时，后端做一次有向图的**环路检测（DAG Cycle Detection）**，如果发现 A->B->A，直接拒绝保存并提示用户。

- **UX 优化 (双击穿透)**：在 GoJS 中给 `sub_script` 节点绑定一个双击事件 (`doubleClick`)。当用户双击这个节点时，Vue 拦截事件，直接新开一个浏览器标签页，跳转到该子脚本的编辑页面。这会让你的工具用起来非常专业。

