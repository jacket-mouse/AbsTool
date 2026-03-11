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
    def _build_flow_graph(self, config: ScriptConfig):
        """将 ScriptConfig 转换为运行时 flow_graph dict 和起始节点 ID。"""
        node_map: Dict[str, ScriptNode] = {}
        next_map: Dict[str, Any] = {}
        in_degree: Dict[str, int] = {}
        node_group_map: Dict[str, str] = {}  # childId -> groupNodeId

        nodes = config.nodes or []
        connections = config.connections or []

        # 节点解析
        for node in nodes:
            node_map[node.id] = node
            in_degree[node.id] = 0 # 入度统计方便判断起始节点和孤岛
            if node.group_key:
                node_group_map[node.id] = node.group_key

        # 边解析
        for conn in connections:
            if conn.from_node in node_map and conn.to_node in node_map:
                if conn.from_port:
                    # 分支节点
                    existing = next_map.get(conn.from_node)
                    if isinstance(existing, dict):
                        existing[conn.from_port] = conn.to_node
                    elif isinstance(existing, str):
                        next_map[conn.from_node] = {"default": existing, conn.from_port: conn.to_node}
                    else:
                        next_map[conn.from_node] = {conn.from_port: conn.to_node}
                else:
                    # 普通节点边
                    next_map[conn.from_node] = conn.to_node
                in_degree[conn.to_node] = in_degree.get(conn.to_node, 0) + 1

        # 构建 loop 组节点的子图
        loop_children_map: Dict[str, Dict[str, Any]] = {}
        for node in nodes:
            if node.is_group and node.type == "loop":
                child_nodes: Dict[str, Dict[str, Any]] = {}
                child_in_degree: Dict[str, int] = {}

                for child in nodes:
                    if child.group_key == node.id:
                        child_data: Dict[str, Any] = {"type": child.type, "next": next_map.get(child.id)}
                        if child.properties:
                            props = dict(child.properties)
                            for k in ("loc", "category", "key"):
                                props.pop(k, None)
                            child_data.update(props)
                        child_nodes[child.id] = child_data
                        child_in_degree[child.id] = 0

                for conn in connections:
                    if conn.from_node in child_nodes and conn.to_node in child_nodes:
                        child_in_degree[conn.to_node] = child_in_degree.get(conn.to_node, 0) + 1

                child_start = next(
                    (cid for cid, deg in child_in_degree.items() if deg == 0),
                    next(iter(child_nodes), ""),
                )
                loop_children_map[node.id] = {"nodes": child_nodes, "startNodeId": child_start}

        # 确定顶层起始节点
        start_node_id = next(
            (nid for nid, deg in in_degree.items() if deg == 0 and nid not in node_group_map),
            nodes[0].id if nodes else "",
        )

        # 构建 flow_graph（跳过子节点）
        flow_graph: Dict[str, Dict[str, Any]] = {}
        for node in nodes:
            if node.id in node_group_map:
                continue
            entry: Dict[str, Any] = {"type": node.type, "next": next_map.get(node.id)}
            if node.properties:
                props = dict(node.properties)
                for k in ("loc", "category", "key"):
                    props.pop(k, None)
                entry.update(props)
            if node.is_group and node.type == "loop" and node.id in loop_children_map:
                entry["children"] = loop_children_map[node.id]
            flow_graph[node.id] = entry

        return flow_graph, start_node_id
