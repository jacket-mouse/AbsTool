# engine/python_script_generator.py
"""
脚本生成器 —— 基于文件覆写的方案
核心思路：
  1. engine/script_template.py 是完整的 Python 脚本模板，关键配置行带有唯一标记注释
  2. 每次生成时：读取模板文件 → 按行扫描并替换标记行 → 写回文件 → 返回文件内容
  3. 本地模板文件始终保留（内容为最近一次生成的配置），下次生成只需覆盖三行即可
"""
import json
from pathlib import Path
from typing import Any, Dict

from schemas.script_editor import ScriptConfig, ScriptNode, Connection

# 模板文件路径（固定，所有生成共享此文件）
TEMPLATE_PATH = Path(__file__).parent / "script_template.py"

# 各配置行的唯一标记（写在行尾注释中）
MARKER_FLOW_GRAPH = "# __FLOW_GRAPH__"
MARKER_START_NODE = "# __START_NODE__"
MARKER_IS_DEBUG   = "# __IS_DEBUG__"


class PythonScriptGenerator:

    def generate(self, config: ScriptConfig) -> str:
        return self._generate_internal(config, is_debug=False)

    def generate_debug(self, config: ScriptConfig) -> str:
        return self._generate_internal(config, is_debug=True)

    # 内部实现

    def _generate_internal(self, config: ScriptConfig, is_debug: bool) -> str:
        flow_graph, start_node_id = self._build_flow_graph(config)

        flow_graph_json = json.dumps(flow_graph, ensure_ascii=False)
        debug_flag = "True" if is_debug else "False"

        # 读取模板文件（所有行）
        lines = TEMPLATE_PATH.read_text(encoding="utf-8").splitlines(keepends=True)

        # 逐行扫描，替换含标记的配置行
        new_lines = []
        for line in lines:
            if MARKER_FLOW_GRAPH in line:
                new_lines.append(f"_FLOW_GRAPH_ = {flow_graph_json}  {MARKER_FLOW_GRAPH}\n")
            elif MARKER_START_NODE in line:
                new_lines.append(f'_START_NODE_ID_ = "{start_node_id}"  {MARKER_START_NODE}\n')
            elif MARKER_IS_DEBUG in line:
                new_lines.append(f"_IS_DEBUG_MODE_ = {debug_flag}  {MARKER_IS_DEBUG}\n")
            else:
                new_lines.append(line)

        content = "".join(new_lines)

        # 写回模板文件（覆写关键信息，其余内容不变）
        TEMPLATE_PATH.write_text(content, encoding="utf-8")

        # 返回文件内容（供 MinIO 上传或直接执行使用）
        return content

    # 图结构计算
    def __build_flow_graph(self, config: ScriptConfig):
        """将 ScriptConfig 转换为运行时 flow_graph dict 和起始节点 ID。"""
        node_map: Dict[str, ScriptNode] = {} # nodeId -> ScriptNode
        next_map: Dict[str, Any] = {}        # FromScriptNode -> ToScriptNode / 分支节点 dict{}
        in_degree: Dict[str, int] = {}       # nodeId -> int
        node_group_map: Dict[str, str] = {}  # childId -> groupNodeId

        nodes = config.nodes or []
        connections = config.connections or []

        # 节点解析 TODO 有些属性没有正常解析
        for node in nodes:
            node_map[node.id] = node
            in_degree[node.id] = 0 # 入度统计方便判断起始节点和孤岛
            if not node.type == "loop" and node.properties.get("group", ""):
                node_group_map[node.id] = node.properties.get("group", "")

        # 边解析 没有考虑 goto
        for conn in connections:
            if conn.from_node in node_map and conn.to_node in node_map: # 过滤无效边
                from_node = node_map[conn.from_node]
                if from_node.type == "decision" or from_node.type == "appState":
                    # 分支节点
                    existing = next_map.get(conn.from_node) # 查看分支节点 from_node 是否已经登记过出口信息
                    if isinstance(existing, dict):
                        existing[conn.from_port] = conn.to_node # 在字典里追加另一个 from_port 信息
                    else: # 第一次写入该分支节点的信息
                        next_map[conn.from_node] = {conn.from_port: conn.to_node}
                elif from_node.type == "loop":
                    next_map[conn.from_node] = None if conn.to_node == "" else conn.to_node # 循环节点无下一个节点，而是从子节点开始执行
                else:
                    # 普通节点
                    next_map[conn.from_node] = conn.to_node
                in_degree[conn.to_node] = in_degree.get(conn.to_node, 0) + 1

        # 构建 loop 组节点的子图
        loop_children_map: Dict[str, Dict[str, Any]] = {} # loop_id -> nodes & startNodeId
        for node in nodes:
            if node.properties["isGroup"] and node.type == "loop":
                child_nodes: Dict[str, Dict[str, Any]] = {} # nodeId -> type next properties(部分)
                child_in_degree: Dict[str, int] = {}

                # 循环节点子图 节点处理
                for child in nodes:
                    if not child.type == "loop" and child.properties.get("group", "") == node.id: # 循环节点的 id = group 循环节点无 group 属性
                        child_data: Dict[str, Any] = {"type": child.type, "next": next_map.get(child.id)}
                        if child.properties:
                            props = dict(child.properties)
                            for k in ("loc", "category", "key"): # 删除不需要的元数据
                                props.pop(k, None)
                            child_data.update(props) # 将剩余数据合并到 child_data
                        child_nodes[child.id] = child_data
                        child_in_degree[child.id] = 0

                # 边处理 必须两个节点都在同一个组内部才算入度
                # 没有考虑 goto
                for conn in connections:
                    if conn.from_node in child_nodes and conn.to_node in child_nodes:
                        child_in_degree[conn.to_node] = child_in_degree.get(conn.to_node, 0) + 1

                # next(迭代器, 默认值)
                child_start = next(
                    (cid for cid, deg in child_in_degree.items() if deg == 0),
                    next(iter(child_nodes), ""),
                ) # 取入度为零的节点 默认值：child_nodes 里第一个值
                loop_children_map[node.id] = {"nodes": child_nodes, "startNodeId": child_start}

        # 确定顶层起始节点 排除在循环组里的节点
        start_node_id = next(
            (nid for nid, deg in in_degree.items() if deg == 0 and nid not in node_group_map),
            nodes[0].id if nodes else "",
        )

        # 构建 flow_graph（goto）
        flow_graph: Dict[str, Dict[str, Any]] = {} # nodeId -> dict{属性}
        for node in nodes:
            # 不是循环内部节点
            if node.id in node_group_map:
                continue
            entry: Dict[str, Any] = {"type": node.type, "next": next_map.get(node.id)}
            # 像循环节点那样删除部分属性
            if node.properties:
                props = dict(node.properties)
                for k in ("loc", "category", "key", "color", "icon", "iconLabel"):
                    props.pop(k, None)
                entry.update(props)
            # 循环节点 添加上子图信息
            if node.properties["isGroup"] and node.type == "loop" and node.id in loop_children_map:
                entry["iterations"] = node.properties["iterations"]
                entry["children"] = loop_children_map[node.id]
            flow_graph[node.id] = entry

        return flow_graph, start_node_id

    def _build_flow_graph(self, config):
        """将 ScriptConfig 转换为运行时 flow_graph dict 和起始节点 ID（完美支持无限嵌套与跨层级连线）"""
        nodes = config.nodes or []
        connections = config.connections or []

        node_map = {node.id: node for node in nodes}
        next_map = {}
        parent_map = {}

        # 1. 建立 parent_map 族谱，并解析所有节点的直接 next
        for node in nodes:
            parent_map[node.id] = node.properties.get("group") if node.properties else None

        for conn in connections:
            if conn.from_node in node_map and conn.to_node in node_map:
                from_node = node_map[conn.from_node]
                if from_node.type in ["decision", "appState"]:
                    existing = next_map.get(conn.from_node)
                    if isinstance(existing, dict):
                        existing[conn.from_port] = conn.to_node
                    else:
                        next_map[conn.from_node] = {conn.from_port: conn.to_node}
                else:
                    next_map[conn.from_node] = None if from_node.type == "loop" else conn.to_node

        # 2. 第一次遍历：把所有节点转换为标准字典（打平）
        flat_dict = {}
        for node in nodes:
            entry = {"type": node.type, "next": next_map.get(node.id)}
            if node.properties:
                props = dict(node.properties)
                for k in ("loc", "category", "key", "color", "icon", "iconLabel"):
                    props.pop(k, None)
                entry.update(props)
            flat_dict[node.id] = entry

        # 3. 统计每个父亲拥有哪些直接儿子
        group_to_children = {}
        for node in nodes:
            group_id = parent_map[node.id]
            if group_id:
                if group_id not in group_to_children:
                    group_to_children[group_id] = []
                group_to_children[group_id].append(node.id)

        # 🌟 核心算法 1：局部寻祖（寻找某个节点在特定 group 下的顶级身份）
        def get_top_child_in_group(node_id, target_group_id):
            curr = node_id
            while curr and parent_map.get(curr) != target_group_id:
                curr = parent_map.get(curr)
                if curr is None:
                    return None  # 该节点压根不在这个 group 的势力范围内
            return curr

        # 4. 为循环节点塞入 children，并利用 Edge Lifting 寻找真正的组内起点
        for node in nodes:
            if node.type == "loop":
                child_ids = group_to_children.get(node.id, [])
                child_nodes = {cid: flat_dict[cid] for cid in child_ids}
                child_in_degree = {cid: 0 for cid in child_ids}

                # 🌟 边提升：处理所有连线
                for conn in connections:
                    top_from = get_top_child_in_group(conn.from_node, node.id)
                    top_to = get_top_child_in_group(conn.to_node, node.id)
                    # 只要起点和终点最终都归属于这个组，且代表的直接子节点不同，就计算入度
                    if top_from and top_to and top_from != top_to:
                        child_in_degree[top_to] += 1

                # 找入度为 0 的节点作为循环内的起点
                child_start = next((cid for cid, deg in child_in_degree.items() if deg == 0),
                                   child_ids[0] if child_ids else "")

                flat_dict[node.id]["iterations"] = flat_dict[node.id].get("iterations", 1)
                flat_dict[node.id]["children"] = {
                    "nodes": child_nodes,
                    "startNodeId": child_start
                }

        # 🌟 核心算法 2：全局寻祖（寻找节点在最外层画布的顶级身份）
        def get_root_component(node_id):
            curr = node_id
            while curr and parent_map.get(curr) is not None:
                curr = parent_map.get(curr)
            return curr

        # 5. 构建最外层的 flow_graph
        flow_graph = {}
        root_nodes = [node.id for node in nodes if not parent_map.get(node.id)]
        root_in_degree = {nid: 0 for nid in root_nodes}

        for nid in root_nodes:
            flow_graph[nid] = flat_dict[nid]

        # 计算最外层的入度以寻找全局起点
        for conn in connections:
            top_from = get_root_component(conn.from_node)
            top_to = get_root_component(conn.to_node)
            if top_from and top_to and top_from != top_to:
                root_in_degree[top_to] += 1

        start_node_id = next((nid for nid, deg in root_in_degree.items() if deg == 0),
                             root_nodes[0] if root_nodes else "")

        return flow_graph, start_node_id

    def _compile_flow_graph(self, config):
        """编译阶段：把可视化图翻译成极简的线性指令集"""
        nodes = config.nodes or []
        connections = config.connections or []

        instructions = {}
        in_degree = {node.id: 0 for node in nodes}

        # 1. 注册所有节点
        for node in nodes:
            instructions[node.id] = {
                "type": node.type,
                "properties": node.properties or {},
                "next": {}  # 统一使用字典存出口
            }

        # 2. 绑定连线（纯粹的指针建立）
        for conn in connections:
            if conn.from_node in instructions and conn.to_node in instructions:
                port = conn.from_port or "default"
                instructions[conn.from_node]["next"][port] = conn.to_node
                in_degree[conn.to_node] += 1

        # 3. 找起点（由于图里可能有环，入度为 0 的绝对是真正的起点）
        start_node_id = next((nid for nid, deg in in_degree.items() if deg == 0), nodes[0].id if nodes else "")

        return instructions, start_node_id