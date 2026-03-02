package cn.edu.sdu.software.engine;

import cn.edu.sdu.software.model.Connection;
import cn.edu.sdu.software.model.ScriptConfig;
import cn.edu.sdu.software.model.ScriptNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.springframework.stereotype.Service;

import java.util.HashMap;
import java.util.Map;

@Service
public class PythonScriptGenerator {

    private final ObjectMapper objectMapper = new ObjectMapper();

    public String generate(ScriptConfig config) throws Exception {
        return generateInternal(config, false);
    }

    public String generateDebug(ScriptConfig config) throws Exception {
        return generateInternal(config, true);
    }

    private String generateInternal(ScriptConfig config, boolean isDebug) throws Exception {
        Map<String, ScriptNode> nodeMap = new HashMap<>();
        Map<String, String> nextMap = new HashMap<>();
        Map<String, Integer> inDegree = new HashMap<>();

        if (config.getNodes() != null) {
            for (ScriptNode node : config.getNodes()) {
                nodeMap.put(node.getId(), node);
                inDegree.put(node.getId(), 0);
            }
        }

        if (config.getConnections() != null) {
            for (Connection conn : config.getConnections()) {
                if (nodeMap.containsKey(conn.getFrom()) && nodeMap.containsKey(conn.getTo())) {
                    nextMap.put(conn.getFrom(), conn.getTo());
                    inDegree.put(conn.getTo(), inDegree.getOrDefault(conn.getTo(), 0) + 1);
                }
            }
        }

        String startNodeId = "";
        for (Map.Entry<String, Integer> entry : inDegree.entrySet()) {
            if (entry.getValue() == 0) {
                startNodeId = entry.getKey();
                break;
            }
        }
        if (startNodeId.isEmpty() && config.getNodes() != null && !config.getNodes().isEmpty()) {
            startNodeId = config.getNodes().get(0).getId();
        }

        Map<String, Map<String, Object>> flowGraph = new HashMap<>();
        if (config.getNodes() != null) {
            for (ScriptNode node : config.getNodes()) {
                Map<String, Object> map = new HashMap<>();
                // 1. 净化节点数据：丢弃无需由 Python 执行关心的属性
                map.put("type", node.getType());
                map.put("next", nextMap.get(node.getId()));
                
                if (node.getProperties() != null) {
                    Map<String, Object> props = new HashMap<>(node.getProperties());
                    props.remove("loc");
                    props.remove("category");
                    props.remove("key");
                    map.putAll(props);
                }

                // 2. 将解析好的内置操作 Python 字符串提前预置到 JSON 中
                String codeStr = getBuiltInActionCode(node.getType(), map);
                map.put("code", codeStr);

                flowGraph.put(node.getId(), map);
            }
        }

        // 把图转成可以直接嵌入 Python 脚本里的 JSON 字符串
        String flowGraphJson = objectMapper.writeValueAsString(flowGraph);

        // 3. 最终生成组装的 Python 脚本模板
        String template = String.format("""
# 自动生成的Android行为模拟脚本 (State Machine 核心引擎驱动)
import uiautomator2 as u2
import time
import random
import json
import traceback
import sys

def run_script():
    # 1. 连接设备
    print(json.dumps({"type": "log", "message": "正在连接设备..."}), flush=True)
    try:
        device = u2.connect()
        print(json.dumps({"type": "init", "status": "success", "serial": device.serial}), flush=True)
    except Exception as e:
        print(json.dumps({"type": "init", "status": "error", "error": str(e)}), flush=True)
        sys.exit(1)

    # 2. 注入从前台配置精简与转译处理后的图节点与内置代码 (作为引擎食粮)
    flow_graph = %s
    
    # 3. 初始化状态机和安全互斥锁
    current_node_id = "%s"
    jump_counters = {}
    max_total_steps = 1000
    step_count = 0

    print(json.dumps({"type": "log", "message": "脚本状态机开始执行..."}), flush=True)
    # 4. 状态机主循环 (核心路由)
    while current_node_id and step_count < max_total_steps:
        step_count += 1
        node_data = flow_graph.get(current_node_id)
        
        if not node_data:
            print(json.dumps({"type": "error", "message": f"节点 {current_node_id} 不存在，流程异常终止！"}), flush=True)
            break
            
        action_type = node_data.get("type", "unknown")
        next_node = node_data.get("next")
        
        # 将正在执行的节点传给前端 (要求3：在前端进行可视化展示)
        # 用 running_node 发给 WebSocket 显示在编辑器界面高亮等
        print(json.dumps({"type": "running_node", "nodeId": current_node_id, "action": action_type}), flush=True)
        
        # --- 行为解析区 ---
        if action_type == "jump":
            target = node_data.get("targetNodeId")
            max_r_str = node_data.get("maxRetries", 1)
            try:
                max_r = int(max_r_str)
            except:
                max_r = 1
            
            # 计数器检测避免死循环
            jump_counters[current_node_id] = jump_counters.get(current_node_id, 0) + 1
            if jump_counters[current_node_id] <= max_r:
                print(json.dumps({"type": "log", "message": f"执行跳转 ({jump_counters[current_node_id]}/{max_r}) -> 跳转至节点: {target}"}), flush=True)
                current_node_id = target
            else:
                print(json.dumps({"type": "log", "message": f"跳转节点达到最大重试次数 {max_r}，继续往下走。"}), flush=True)
                current_node_id = next_node
            
            time.sleep(0.1)
            continue
            
        # 其它基础普通动作执行，通过执行预置好的 code
        code_str = node_data.get("code")
        if code_str:
            try:
                exec(code_str, globals(), locals())
                print(json.dumps({"type": "log", "message": f"节点 {current_node_id}({action_type}) 执行成功"}), flush=True)
            except Exception as e:
                print(json.dumps({"type": "error", "nodeId": current_node_id, "message": f"执行失败: {e}"}), flush=True)
                traceback.print_exc()
                raise e

        # 执行推进向下一步
        current_node_id = next_node

    if step_count >= max_total_steps:
        print(json.dumps({"type": "error", "message": "警告：触发全局安全锁 (上限1000步)，强制停止以保护设备！"}), flush=True)
    else:
        print(json.dumps({"type": "log", "message": "所有节点执行完毕！"}), flush=True)

if __name__ == "__main__":
    run_script()
""", flowGraphJson, startNodeId);

        return template;
    }

    private String getBuiltInActionCode(String actionType, Map<String, Object> props) {
        if (actionType == null) return "";
        switch (actionType) {
            case "click": {
                Object targetTypeObj = props.get("targetType");
                String targetType = targetTypeObj != null ? targetTypeObj.toString() : "";
                Object elementIdObj = props.get("elementId");
                String elementId = elementIdObj != null ? elementIdObj.toString() : "";
                if ("元素 ID".equals(targetType) && !elementId.isEmpty()) {
                    return String.format("device(resourceId=\"%s\").click()", elementId);
                } else {
                    Object xObj = props.get("x");
                    Object yObj = props.get("y");
                    String x = xObj != null ? xObj.toString() : "0";
                    String y = yObj != null ? yObj.toString() : "0";
                    return String.format("device.click(int(%s * device.info['displayWidth']), int(%s * device.info['displayHeight']))", x, y);
                }
            }
            case "longPress": {
                Object targetTypeObj = props.get("targetType");
                String targetType = targetTypeObj != null ? targetTypeObj.toString() : "";
                Object elementIdObj = props.get("elementId");
                String elementId = elementIdObj != null ? elementIdObj.toString() : "";
                Object durationObj = props.get("duration");
                String duration = durationObj != null ? durationObj.toString() : "1000";
                
                double durSec = 1.0;
                try {
                    durSec = Double.parseDouble(duration) / 1000.0;
                } catch(Exception ignored){}
                
                if ("元素 ID".equals(targetType) && !elementId.isEmpty()) {
                    return String.format("device(resourceId=\"%s\").long_click(duration=%.3f)", elementId, durSec);
                } else {
                    Object xObj = props.get("x");
                    Object yObj = props.get("y");
                    String x = xObj != null ? xObj.toString() : "0";
                    String y = yObj != null ? yObj.toString() : "0";
                    return String.format("device.long_click(int(%s * device.info['displayWidth']), int(%s * device.info['displayHeight']), duration=%.3f)", x, y, durSec);
                }
            }
            case "swipe": {
                Object sxObj = props.get("startX");
                Object syObj = props.get("startY");
                Object exObj = props.get("endX");
                Object eyObj = props.get("endY");
                Object stepsObj = props.get("steps");
                
                String sx = sxObj != null ? sxObj.toString() : "0.5";
                String sy = syObj != null ? syObj.toString() : "0.8";
                String ex = exObj != null ? exObj.toString() : "0.5";
                String ey = eyObj != null ? eyObj.toString() : "0.2";
                
                double dur = 0.25;
                try {
                    if (stepsObj != null) dur = Double.parseDouble(stepsObj.toString()) * 0.005;
                } catch(Exception ignored){}

                return String.format("""
                        device.swipe_ext("up", scale=0.8) # 暂时 fallback 简易滑动
                        device.swipe(%s, %s, %s, %s, duration=%.3f)""", sx, sy, ex, ey, dur);
            }
            case "input": {
                Object textObj = props.get("text");
                String text = textObj != null ? textObj.toString() : "";
                Object elementIdObj = props.get("elementId");
                String elementId = elementIdObj != null ? elementIdObj.toString() : "";
                if (!elementId.isEmpty()) {
                    return String.format("device(resourceId=\"%s\").set_text(\"%s\")", elementId, text);
                }
                return "pass # [Error] input操作需要元素ID绑定";
            }
            case "wait": {
                Object durationObj = props.get("duration");
                String duration = durationObj != null ? durationObj.toString() : "1000";
                double durSec = 1.0;
                try {
                    durSec = Double.parseDouble(duration) / 1000.0;
                } catch(Exception ignored){}
                return String.format("time.sleep(%.3f + random.uniform(0, 0.3))", durSec);
            }
            case "openApp": {
                Object pkg = props.get("packageName");
                return String.format("device.app_start(\"%s\")", pkg != null ? pkg.toString() : "");
            }
            case "closeApp": {
                Object pkg = props.get("packageName");
                return String.format("device.app_stop(\"%s\")", pkg != null ? pkg.toString() : "");
            }
            case "home":
                return "device.press(\"home\")";
            case "back":
                return "device.press(\"back\")";
            case "unlock": {
                Object unlockTypeObj = props.get("unlockType");
                String unlockType = unlockTypeObj != null ? unlockTypeObj.toString() : "密码";
                if ("手势".equals(unlockType)) {
                    Object gestureList = props.get("gesture");
                    String patternStr = "";
                    if (gestureList instanceof Iterable<?>) {
                        StringBuilder sb = new StringBuilder();
                        boolean first = true;
                        for (Object o : (Iterable<?>) gestureList) {
                            if(!first) sb.append(",");
                            sb.append(o.toString());
                            first = false;
                        }
                        patternStr = sb.toString();
                    }
                    return String.format("""
                        device.screen_on()
                        device.swipe_ext("up", scale=0.8)
                        time.sleep(1)
                        pattern_view = device(classNameMatches="(?i).*LockPatternView.*")
                        if pattern_view.exists:
                            bounds = pattern_view.info['bounds']
                            left, top, right, bottom = bounds['left'], bounds['top'], bounds['right'], bounds['bottom']
                            w = right - left
                            h = bottom - top
                            x_c = [left + w/6, left + w/2, left + w*5/6]
                            y_c = [top + h/6, top + h/2, top + h*5/6]
                        else:
                            width = device.info['displayWidth']
                            height = device.info['displayHeight']
                            x_c = [width*0.2, width*0.5, width*0.8]
                            y_c = [height*0.55, height*0.7, height*0.85]
                        pattern = [%s]
                        points = []
                        for idx in pattern:
                            row = int(idx) // 3
                            col = int(idx) %% 3
                            points.append((x_c[col], y_c[row]))
                        if points:
                            device.swipe_points(points, 0.05)""", patternStr);
                } else {
                    Object passwordObj = props.get("password");
                    String password = passwordObj != null ? passwordObj.toString() : "";
                    return String.format("""
                        device.screen_on()
                        device.swipe_ext("up", scale=0.8)
                        time.sleep(1)
                        pwd = "%s"
                        for char in pwd:
                            btn = device(text=char)
                            if not btn.exists: btn = device(description=char)
                            if btn.exists:
                                btn.click()
                            elif char.isdigit():
                                device.press(int(char) + 7)
                            time.sleep(0.2)
                        time.sleep(0.5)
                        enter_btn = device(textMatches="(?i)(确认|确定|完成|done|enter)")
                        if not enter_btn.exists: enter_btn = device(descriptionMatches="(?i)(确认|确定|完成|done|enter)")
                        if enter_btn.exists:
                            enter_btn.click()
                        else:
                            device.press("enter")""", password);
                }
            }
            case "jump":
                return "pass"; // Handled natively in state machine loop above
            default:
                return "pass # unknown node type: " + actionType;
        }
    }
}
