# FSM 执行引擎详细流程图（Mermaid）

## 一、总体流程图

```mermaid
flowchart TD
    A([脚本入口 __main__]) --> B[run_script]

    subgraph INIT ["初始化阶段"]
        B --> C{读取设备序列号<br/>优先级: 环境变量 > 代码变量 > None}
        C --> D[u2.connect 连接设备]
        D --> E{连接成功?}
        E -- 否 --> F[输出 init error<br/>sys.exit 1]
        E -- 是 --> G[输出 init success]
        G --> H[初始化状态变量<br/>flow_graph = _FLOW_GRAPH_<br/>current_node_id = _START_NODE_ID_<br/>jump_counters = 空字典<br/>runtime_state.clear<br/>step_count = 0<br/>max_total_steps = 50000]
    end

    subgraph DEBUG_INIT ["调试模式初始化"]
        H --> I{_IS_DEBUG_MODE_?}
        I -- True --> J[debug_lock.clear<br/>初始为阻塞状态]
        I -- False --> K[debug_lock.set<br/>初始为放行状态]
        J --> L[启动 debug_listener<br/>后台守护线程]
        K --> L
        L --> M[初始化 call_stack = 空列表]
    end

    M --> LOOP

    subgraph LOOP ["主循环 while current_node_id AND step_count < 50000 AND engine_running"]
        direction TB
        N[step_count += 1] --> O[从 flow_graph 取出<br/>node_data = flow_graph.get current_node_id]
        O --> P{node_data 存在?}
        P -- 否 --> Q[输出错误: 节点不存在<br/>break 终止]
        P -- 是 --> R[解析 action_type 和 next_node]
        R --> S[输出 running_node 事件<br/>通知前端当前执行节点]
        S --> DEBUG_CHECK
    end

    subgraph DEBUG_CHECK ["调试断点检查"]
        T{is_debug_mode?}
        T -- 是 --> U[debug_lock.clear 设为阻塞]
        U --> V[输出 break 事件<br/>含 nodeId + action + code]
        V --> W[debug_lock.wait<br/>阻塞等待前端指令]
        W --> X{engine_running?}
        X -- 否 --> Y[break 终止]
        T -- 否 --> Z[继续执行]
        X -- 是 --> Z
    end

    Z --> ACTION_DISPATCH

    subgraph ACTION_DISPATCH ["动作分发执行"]
        direction TB
        AA{action_type == jump?}
        AA -- 是 --> AB[跳转逻辑<br/>检查 jump_counters<br/>是否超过 maxRetries]
        AB --> AC{未超最大次数?}
        AC -- 是 --> AD[current_node_id = targetNodeId<br/>continue 回主循环]
        AC -- 否 --> AE[current_node_id = next_node<br/>continue 回主循环]

        AA -- 否 --> AF{ACTION_DISPATCHER<br/>中存在 handler?}
        AF -- 否 --> AG[输出: 未知的动作类型]
        AF -- 是 --> AH{action_type == loop?}
        AH -- 是 --> AI[result = handler device, node_data, current_node_id]
        AH -- 否 --> AJ[result = handler device, node_data]
        AI --> AK[处理执行结果]
        AJ --> AL{执行成功?}
        AL -- 是 --> AM[输出: 节点执行成功]
        AL -- 否 --> AN[输出 error 事件<br/>raise 异常终止脚本]
        AM --> AK
    end

    AK --> NEXT_NODE

    subgraph NEXT_NODE ["下一节点路由"]
        direction TB
        BA{action_type == loop<br/>且 result == Body?}
        BA -- 是 --> BB[call_stack.push<br/>当前循环节点入栈]
        BA -- 否 --> BC[不压栈]

        BB --> BD{节点类型判断}
        BC --> BD

        BD -- loop 循环节点 --> BE[branch_key = result<br/>Body 或 R]
        BD -- decision 判断节点 --> BF[branch_key = result<br/>B True 或 R False]
        BD -- 普通节点 --> BG[branch_key = R]

        BE --> BH[current_node_id =<br/>next_node.get branch_key]
        BF --> BI[current_node_id =<br/>next_node.get branch_key]
        BG --> BJ[current_node_id =<br/>next_node.get R]

        BI --> BK{判断节点的另一分支<br/>指向 loop 节点?}
        BK -- 是且当前分支不是loop --> BL[call_stack.pop<br/>退出该循环层]
        BK -- 否 --> BM[不操作]

        BH --> BN{current_node_id 为空?}
        BL --> BN
        BM --> BN
        BJ --> BN

        BN -- 是且 call_stack 非空 --> BO[current_node_id =<br/>call_stack.pop<br/>隐式回弹到循环节点]
        BN -- 否 --> BP[回到主循环顶部]
        BO --> BP
    end

    BP --> N

    Q --> END_CHECK
    Y --> END_CHECK
    AG --> NEXT_NODE

    subgraph END_CHECK ["结束判定"]
        CA{step_count >= 50000?}
        CA -- 是 --> CB[输出: 触发全局安全锁<br/>强制停止]
        CA -- 否 --> CC{current_node_id == None?}
        CC -- 是 --> CD[输出: 所有节点执行完毕]
        CC -- 否 --> CE[engine_running == False<br/>被调试线程终止]
    end
```

---

## 二、调试监听线程（debug_listener）

```mermaid
flowchart TD
    A([debug_listener 线程启动]) --> B[循环: while engine_running]
    B --> C[sys.stdin.readline<br/>阻塞读取前端指令]
    C --> D{读到内容?}
    D -- 空行/EOF --> E[break 线程结束]
    D -- 有内容 --> F[JSON 解析指令]

    F --> G{有 overrideCode?}
    G -- 是 --> H[解析并更新<br/>_FLOW_GRAPH_ 中当前节点数据<br/>实现运行时参数热替换]
    G -- 否 --> I[跳过]

    H --> J{cmd_action 类型}
    I --> J

    J -- stop --> K["engine_running = False<br/>debug_lock.set 解除阻塞<br/>os._exit(0) 立即退出"]
    J -- pause --> L["is_debug_mode = True<br/>不操作 debug_lock<br/>效果: 当前节点跑完后暂停"]
    J -- run --> M["is_debug_mode = False<br/>debug_lock.set 解除阻塞<br/>效果: 立即继续 + 后续不暂停"]
    J -- step --> N["is_debug_mode = True<br/>debug_lock.set 解除阻塞<br/>效果: 只执行一步再暂停"]

    K --> O([线程结束])
    L --> B
    M --> B
    N --> B
```

---

## 三、ACTION_DISPATCHER 动作类型全览

```mermaid
flowchart LR
    D[ACTION_DISPATCHER] --> UI["UI 交互类"]
    D --> APP["应用管理类"]
    D --> DEVICE["设备控制类"]
    D --> FLOW["流程控制类"]

    UI --> click["click 点击<br/>支持: XPath / 坐标"]
    UI --> longPress["longPress 长按<br/>支持: XPath / 坐标 + 时长"]
    UI --> swipe["swipe 滑动<br/>起点 到 终点坐标"]
    UI --> input["input 输入文本<br/>XPath 定位输入框"]

    APP --> openApp["openApp 打开应用<br/>app_start packageName"]
    APP --> closeApp["closeApp 关闭应用<br/>app_stop packageName"]
    APP --> foreground["foreground 切前台<br/>app_start stop=False"]
    APP --> appState["appState 应用状态检测<br/>返回 R1前台/R2后台/R3未运行"]

    DEVICE --> wait["wait 等待<br/>sleep + 随机偏移"]
    DEVICE --> unlock["unlock 解锁屏幕<br/>亮屏 + 滑动 + 输密码"]
    DEVICE --> brightness["brightness 屏幕亮度<br/>cmd display set-brightness"]
    DEVICE --> notification["notification 模拟通知<br/>cmd notification post"]
    DEVICE --> network["network 切换网络<br/>WiFi / 移动数据 / 飞行模式"]

    FLOW --> decision["decision 条件分支<br/>返回 B=True / R=False"]
    FLOW --> loop["loop 计数循环<br/>返回 Body=继续 / R=跳出"]
    FLOW --> jump["jump 跳转<br/>直接在主循环处理<br/>不经过 dispatcher"]
```

---

## 四、条件分支（decision）判断逻辑

```mermaid
flowchart TD
    A[handle_decision] --> B{detectionType?}

    B -- 应用状态 --> C{appRunningState?}
    C -- 前台运行 --> D["device.app_current()<br/>package == 目标包名?"]
    D -- 匹配 --> E["返回 B (True)"]
    D -- 不匹配 --> F["返回 R (False)"]
    C -- 后台运行 --> G["device.shell pidof 包名<br/>有进程?"]
    G -- 有 --> E
    G -- 无 --> F
    C -- 未运行 --> H["device.shell pidof 包名<br/>无进程?"]
    H -- 是 --> E
    H -- 否 --> F

    B -- 设备状态 --> I{deviceStateType?}
    I -- 网络类型 --> J["检测 wlan_ip / ping<br/>WiFi? 数据? 飞行模式?"]
    J -- 匹配目标 --> E
    J -- 不匹配 --> F
    I -- 电池电量 --> K["dumpsys battery<br/>level 与阈值比较"]
    K -- 满足条件 --> E
    K -- 不满足 --> F
    I -- 屏幕开启 --> L["device.info screenOn<br/>与目标状态比较"]
    L -- 匹配 --> E
    L -- 不匹配 --> F
    I -- 正在充电 --> M["dumpsys battery<br/>status/AC/USB powered"]
    M -- 匹配 --> E
    M -- 不匹配 --> F

    B -- 元素存在性 --> N["device.xpath.wait 2秒<br/>元素是否出现?"]
    N -- 找到 --> E
    N -- 未找到 --> F
```

---

## 五、循环节点（loop）与调用栈协作

```mermaid
flowchart TD
    A["进入 loop 节点"] --> B["读取 runtime_state 中<br/>当前循环计数 current_count"]
    B --> C{current_count < max_iter?}

    C -- 是 --> D["runtime_state 计数 +1<br/>输出: 循环进度 N/M"]
    D --> E["返回 Body"]
    E --> F["主循环: call_stack.push<br/>将循环节点压入栈"]
    F --> G["current_node_id =<br/>next_node.get Body<br/>进入循环体"]
    G --> H["执行循环体内的节点链..."]
    H --> I{循环体走到尽头<br/>current_node_id == None?}
    I -- 是 --> J["call_stack.pop<br/>弹出循环节点<br/>隐式回弹"]
    J --> A

    C -- 否 --> K["runtime_state 计数归零<br/>输出: 循环完成，跳出"]
    K --> L["返回 R"]
    L --> M["current_node_id =<br/>next_node.get R<br/>走向循环后续节点"]

    style F fill:#e1f5fe
    style J fill:#fff3e0
```

### 循环嵌套示例（调用栈变化）

```mermaid
sequenceDiagram
    participant Main as 主循环
    participant Stack as call_stack

    Note over Main: 进入外层 Loop_A (3次)
    Main->>Stack: push(Loop_A)
    Note over Stack: [Loop_A]

    Note over Main: 进入内层 Loop_B (2次)
    Main->>Stack: push(Loop_B)
    Note over Stack: [Loop_A, Loop_B]

    Note over Main: 内层循环体执行...
    Note over Main: 内层循环体走到尽头
    Main->>Stack: pop() -> Loop_B (隐式回弹)
    Note over Stack: [Loop_A]

    Note over Main: Loop_B 第2次迭代...
    Main->>Stack: push(Loop_B)
    Note over Stack: [Loop_A, Loop_B]

    Note over Main: 内层循环体执行...
    Main->>Stack: pop() -> Loop_B
    Note over Stack: [Loop_A]

    Note over Main: Loop_B 计数达上限, 返回 R
    Note over Main: Loop_B 后续节点链走到尽头
    Main->>Stack: pop() -> Loop_A (隐式回弹)
    Note over Stack: []

    Note over Main: Loop_A 第2次迭代...
```

---

## 六、完整数据流概览

```mermaid
flowchart LR
    subgraph 前端
        A[可视化流程图 JSON]
        B[调试指令 stdin]
        C[日志展示 stdout]
    end

    subgraph 代码生成
        D[python_script_generator.py]
        E[script_template.py 模板]
    end

    subgraph FSM引擎运行时
        F[_FLOW_GRAPH_ 流程图数据]
        G[ACTION_DISPATCHER 动作分发]
        H[runtime_state 循环计数]
        I[call_stack 调用栈]
        J[debug_lock 调试信号]
        K[debug_listener 线程]
    end

    subgraph 设备
        L[Android 设备<br/>uiautomator2]
    end

    A -->|模板标记替换| D
    D -->|注入到| E
    E -->|生成| F
    F --> G
    G -->|click/swipe/input...| L
    L -->|状态反馈| G
    G -->|JSON stdout| C
    B -->|step/run/pause/stop| K
    K -->|控制| J
    H -.->|循环计数| G
    I -.->|嵌套回弹| G
```
