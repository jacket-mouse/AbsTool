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


    def _generate_internal(self, config: ScriptConfig, is_debug: bool) -> str:
        # 1. 拿到拍平后的图结构和起点
        instructions, start_node_id = self._compile_flow_graph(config)

        report = self._check_isolated_nodes(instructions, start_node_id)

        # 如果根本没有起点，或者存在孤岛节点，拒绝生成代码！
        if not report.get("valid") or report.get("has_islands"):
            # 抛出具体的错误信息。
            # 你的 WebSocket 外层 try...except 会捕获这个 ValueError，并把 message 发给前端
            raise ValueError(f"图结构校验失败: {report.get('message')}")


        # 2. 补上刚才漏掉的 instructions 变量
        flow_graph_json = json.dumps(instructions, ensure_ascii=False)
        debug_flag = "True" if is_debug else "False"

        # 3. 读取原始模板文件（只读操作，极其安全）
        lines = TEMPLATE_PATH.read_text(encoding="utf-8").splitlines(keepends=True)

        # 4. 逐行扫描，替换含标记的配置行
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

        # 5. 在内存中拼接成最终要执行的 Python 脚本代码
        content = "".join(new_lines)

        # 6. 直接返回最终代码内容
        return content

    def _compile_flow_graph(self, config):
        """编译阶段：把可视化图翻译成极简的线性指令集"""
        nodes = config.nodes or []
        connections = config.connections or []

        instructions = {}
        start_node_id = ""
        start_node_placeholder = ""  # 记录画布上那个虚拟的 start 节点 ID

        # 1. 注册所有节点，并进行属性“大一统”打包
        for node in nodes:

            # 将 node 对象安全转为字典（兼容 FastAPI 的 Pydantic 模型或普通 Python 对象）
            node_data = node.dict() if hasattr(node, "dict") else vars(node)

            if node.type == "start": # 起始节点
                start_node_placeholder = str(node.id)
                continue

            # 获取基础的 properties (防止为空)
            props = dict(node_data.get("properties", {}) or {})

            # 把外层的所有其他属性“打包”进 props 里面
            for k, v in node_data.items():
                # 避开基础路由字段和原有的 properties 字段
                if k not in ["id", "type", "properties"]:
                    # 只有非 None 的值才塞进去，避免覆盖原有的默认值
                    if v is not None:
                        props[k] = v

            # 定义需要剔除的前端 UI 无用元数据（保持引擎纯净）
            ui_garbage_keys = [
                "loc", "color", "icon",
                "iconLabel", "title", "desc", "isGroup", "group", "desc"
            ]

            # 统一清洗
            for k in ui_garbage_keys:
                props.pop(k, None)


            # 存入最终的指令集
            instructions[node.id] = {
                "type": node.type,
                "properties": props,
                "next": {}  # 统一使用字典存出口，等待后续边解析填入
            }

        # 2. 绑定连线（纯粹的指针建立）
        for conn in connections:
            if conn.from_node in instructions and conn.to_node in instructions:
                port = conn.from_port or "default"
                instructions[conn.from_node]["next"][port] = conn.to_node
            else:
                if conn.from_node == start_node_placeholder and start_node_id == "" and conn.to_node in instructions: # 等于起始节点
                    start_node_id = conn.to_node

        return instructions, start_node_id

    def _check_isolated_nodes(self, instructions: dict, start_node_id: str) -> dict:
        """
        使用 BFS (广度优先搜索) 检查流程图中是否存在孤岛节点。
        返回给前端的校验报告。
        """
        all_nodes = set(instructions.keys())
        visited = set()

        # 1. 边界防御：如果图是空的，或者起点根本不存在
        if not instructions:
            return {"valid": True, "has_islands": False, "isolated_nodes": [], "message": "画布为空"}

        if not start_node_id or start_node_id not in instructions:
            return {
                "valid": False,
                "has_islands": True,
                "isolated_nodes": list(all_nodes),
                "message": "未找到有效的起点 (Start) 节点连接，保存失败"
            }

        # 2. BFS 遍历 (使用简单的 List 作为队列)
        queue = [start_node_id]

        while queue:
            # 从队列头部取出一个节点 (BFS)
            current_id = queue.pop(0)

            if current_id not in visited:
                visited.add(current_id)

                # 获取该节点的所有出口连线
                node_data = instructions.get(current_id, {})
                next_dict = node_data.get("next", {})

                # 遍历它连向的所有下一站节点
                for port, next_id in next_dict.items():
                    # 只有当下一站节点真实存在，且还没被访问过时，才加入队列
                    if next_id in instructions and next_id not in visited:
                        queue.append(next_id)

        # 3. 集合运算：求差集，找出没被访问到的孤岛
        isolated_nodes = all_nodes - visited

        # 4. 组装返回给前端的数据结构
        has_islands = len(isolated_nodes) > 0

        return {
            "valid": True,  # 代表校验过程成功执行
            "has_islands": has_islands,
            "isolated_nodes": list(isolated_nodes),  # 转为 list 方便 JSON 序列化
            "visited_count": len(visited),
            "total_count": len(all_nodes),
            "message": f"检测到 {len(isolated_nodes)} 个孤立节点" if has_islands else "图结构健康，无孤岛。"
        }