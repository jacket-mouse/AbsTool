package cn.edu.sdu.software.config;

import cn.edu.sdu.software.engine.PythonScriptGenerator;
import cn.edu.sdu.software.model.ScriptConfig;
import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.springframework.stereotype.Component;
import org.springframework.web.socket.CloseStatus;
import org.springframework.web.socket.TextMessage;
import org.springframework.web.socket.WebSocketSession;
import org.springframework.web.socket.handler.TextWebSocketHandler;

import java.io.*;
import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;

/**
 * ╔══════════════════════════════════════════════════════════════════════════╗
 * ║          脚本调试 WebSocket 核心处理器（消息总线中枢）                      ║
 * ╠══════════════════════════════════════════════════════════════════════════╣
 * ║ 继承自 TextWebSocketHandler，Spring 会将此 Handler 绑定到                 ║
 * ║ /api/ws/script/debug 端点，每个浏览器连接对应一个独立的 WebSocketSession。  ║
 * ║                                                                          ║
 * ║ 核心职责（三大能力）：                                                       ║
 * ║  1. 【日志反推】  将 Python 进程 stdout 的每行 JSON 日志实时推送到前端，       ║
 * ║                  前端解析 nodeId 后在 GoJS 图上高亮对应节点。                ║
 * ║  2. 【异常感知】  捕获 Python 进程 stderr（崩溃堆栈），包装为 error 帧下推，   ║
 * ║                  前端可立刻感知哪个节点执行失败。                             ║
 * ║  3. 【终端操作】  将前端发来的 step/run/pause/stop/update_node 等控制指令    ║
 * ║                  透传到 Python 进程的 stdin，实现双向调试控制。              ║
 * ║                                                                          ║
 * ║ 并发安全保障：所有 session → 进程 的映射均使用 ConcurrentHashMap，          ║
 * ║              多用户同时调试时完全隔离，互不干扰。                             ║
 * ╚══════════════════════════════════════════════════════════════════════════╝
 */
@Component // 声明为 Spring 管理的 Bean，由容器负责创建和注入
public class ScriptDebugWebSocketHandler extends TextWebSocketHandler {

    // ── 依赖注入 ────────────────────────────────────────────────────────────────

    /** Jackson JSON 序列化/反序列化工具，用于解析前端发来的 JSON 指令帧 */
    private final ObjectMapper objectMapper;

    /** Python 脚本生成引擎，根据前端传来的图节点数据生成可执行的 Python 代码 */
    private final PythonScriptGenerator pythonScriptGenerator;

    // ── 会话级并发状态存储 ────────────────────────────────────────────────────────

    /**
     * sessionId → 对应的 Python 子进程
     *
     * 设计要点：
     *  · 每个 WebSocket 连接（session）对应一个独立 Python 进程，实现多用户隔离
     *  · 使用 ConcurrentHashMap 而非 HashMap：
     *    - WebSocket 回调线程、IO 读取线程、Spring 管理线程会并发访问此 Map
     *    - HashMap 在并发写时会产生数据竞争，甚至死循环（JDK7 已知问题）
     *    - ConcurrentHashMap 通过 CAS + 分段锁保证原子性，读操作完全无锁
     */
    private final Map<String, Process> processMap = new ConcurrentHashMap<>();

    /**
     * sessionId → Python 进程的标准输入流写入器（stdin）
     *
     * 作用：前端发来 step/run/pause/update_node 等控制指令时，
     *       通过此 Writer 将 JSON 字符串写入 Python 进程的 stdin，
     *       Python 内部的 debug_listener 线程读取后执行相应操作。
     * BufferedWriter：缓冲写入，配合 flush() 确保指令立即发送到进程管道。
     */
    private final Map<String, BufferedWriter> processInputMap = new ConcurrentHashMap<>();

    /** 构造器注入（Spring 推荐方式，便于单元测试 Mock） */
    public ScriptDebugWebSocketHandler(ObjectMapper objectMapper, PythonScriptGenerator pythonScriptGenerator) {
        this.objectMapper = objectMapper;
        this.pythonScriptGenerator = pythonScriptGenerator;
    }

    // ── WebSocket 生命周期回调 ────────────────────────────────────────────────────

    /**
     * 【生命周期 - 连接建立】
     * 当浏览器与服务端完成 WebSocket 握手后，Spring 自动调用此方法。
     * 此时 session 正式激活，可以开始收发消息。
     * 当前仅做日志记录，session 与进程的绑定在收到 "start" 指令后才真正建立。
     */
    @Override
    public void afterConnectionEstablished(WebSocketSession session) {
        System.out.println("Debug WebSocket Connected: " + session.getId());
    }

    /**
     * 【生命周期 - 连接断开】
     * 当连接关闭时（正常关闭、浏览器 Tab 关闭、网络断开等任意原因），Spring 自动调用此方法。
     *
     * 关键：必须在此强制终止 Python 子进程！
     * 原因：若浏览器直接关闭，Python 进程会变成"孤儿进程"，
     *       继续占用 ADB 连接和设备资源，直到 JVM 退出才会被 OS 回收。
     */
    @Override
    public void afterConnectionClosed(WebSocketSession session, CloseStatus status) {
        System.out.println("Debug WebSocket Closed: " + session.getId());
        terminateProcess(session.getId()); // 回收资源，防止僵尸进程
    }

    /**
     * 【工具方法】强制终止 Python 子进程并清理 Map 中的残留记录。
     *
     * destroyForcibly()：发送 SIGKILL 信号，立即强杀进程，不等待优雅退出。
     * 原因：Python 进程可能正在 time.sleep()、u2.click() 等阻塞操作中，
     *       普通 destroy()（SIGTERM）可能需要等待，不如直接 SIGKILL 可靠。
     *
     * Map.remove()：同时移除 Key，避免后续误用已关闭的进程引用。
     */
    private void terminateProcess(String sessionId) {
        Process p = processMap.remove(sessionId);
        if (p != null) {
            p.destroyForcibly(); // 强制终止，相当于 kill -9
        }
        processInputMap.remove(sessionId); // 清理 stdin 写入器，防止内存泄漏
    }

    // ── 消息处理核心 ─────────────────────────────────────────────────────────────

    /**
     * 【生命周期 - 收到文本消息】
     * 每当前端通过 WebSocket 发来一帧文本消息，Spring 自动调用此方法。
     * 这是整个调试系统的"消息总线"入口，所有上行指令在此分发处理。
     *
     * 支持的 action 类型：
     *  · "start"       → 编译脚本、启动 Python 进程、开始日志推流
     *  · "stop"        → 强制终止当前 Python 进程
     *  · "step"        → 单步执行（在断点处向前走一步）
     *  · "run"         → 取消断点，持续运行直到下一断点
     *  · "pause"       → 暂停，在下一个节点入口触发断点
     *  · "update_node" → 热更新某个节点的参数（不需要重启脚本）
     */
    @Override
    protected void handleTextMessage(WebSocketSession session, TextMessage message) throws Exception {
        // 将前端发来的 JSON 字符串解析为 Jackson 树形节点
        JsonNode root = objectMapper.readTree(message.getPayload());
        // 取出 action 字段，决定本次消息的处理分支
        String action = root.has("action") ? root.get("action").asText() : "";

        // ────────────────────────────────────────────────────────────────────────
        // CASE 1：start —— 脚本编译 + 进程启动 + IO 监听线程创建
        // ────────────────────────────────────────────────────────────────────────
        if ("start".equals(action)) {

            // Step 1：如果当前 session 已有运行中的进程（例如用户重复点击调试），先清理掉
            terminateProcess(session.getId());

            // Step 2：将前端 JSON 中的 config 字段（包含 nodes 和 connections）
            //         反序列化为 Java 的 ScriptConfig 对象，便于后续代码生成
            ScriptConfig config = objectMapper.treeToValue(root.get("config"), ScriptConfig.class);

            // Step 3：调用代码生成引擎，生成"调试模式"的 Python 脚本
            //         调试模式与正常模式的区别：脚本内部会包含 threading.Event 断点控制逻辑
            String pythonCode = pythonScriptGenerator.generateDebug(config);

            // Step 4：将生成的 Python 代码写入临时文件
            //         为什么不直接用 python -c "..."？
            //         · 命令行字符串长度有限制（OS 层约 131072 字节）
            //         · 命令行方式存在 Shell 注入风险（引号、换行符等特殊字符）
            //         · 临时文件方式更安全、更可靠
            File tempFile = File.createTempFile("debug_script_" + session.getId(), ".py");
            try (PrintWriter out = new PrintWriter(tempFile)) {
                out.println(pythonCode);
            }

            // Step 5：使用 venv 隔离的 Python 环境启动进程
            //         · 使用项目 venv 而非系统 Python，确保 uiautomator2 等依赖已正确安装
            //         · "-u" 参数（unbuffered）：关闭 Python 的 stdout 缓冲区，
            //           使 print() 输出立即写入管道，WebSocket 端才能真正"实时"看到日志
            //           （如果没有 -u，Python 会攒够 4KB 才批量输出，体验极差）
            ProcessBuilder pb = new ProcessBuilder(
                "/Users/leeson/Documents/毕业设计/AbsTool/venv/bin/python3",
                "-u",                          // 无缓冲模式，日志实时推流的关键
                tempFile.getAbsolutePath()     // 临时脚本文件路径
            );
            Process process = pb.start();

            // Step 6：将进程和 stdin 写入器存入 Map，以 sessionId 为 Key 实现多用户隔离
            processMap.put(session.getId(), process);
            processInputMap.put(session.getId(),
                new BufferedWriter(new OutputStreamWriter(process.getOutputStream()))
                // OutputStreamWriter：将 Java 字符流适配到 Python 进程的字节 stdin 管道
                // BufferedWriter：提供缓冲，配合 flush() 控制发送时机
            );

            // Step 7：启动独立 IO 监听线程（非阻塞设计的核心）
            //
            // 为什么必须开新线程？
            //   · process.getInputStream().readLine() 是阻塞调用
            //   · 如果在 handleTextMessage（Spring 的回调线程）里直接 readLine()，
            //     该线程会被卡住，无法再接收前端发来的 step/stop 等控制指令
            //   · 开独立线程后，主回调线程立即返回，随时能处理新消息，
            //     IO 线程专职读取 Python 输出并推送到 WebSocket，两者并行不阻塞
            new Thread(() -> {

                // ── 读取 stdout（业务日志主流）─────────────────────────────────
                // Python 脚本通过 print(json.dumps({...}), flush=True) 输出 JSON 帧
                // 这里逐行读取，每读一行就立刻通过 WebSocket 推给前端
                try (BufferedReader reader = new BufferedReader(
                        new InputStreamReader(process.getInputStream()))) {
                    String line;
                    while ((line = reader.readLine()) != null) { // readline 阻塞直到有新行
                        if (session.isOpen()) { // 防御性检查：连接可能在此期间被关闭
                            try {
                                session.sendMessage(new TextMessage(line)); // 实时推流
                            } catch (Exception ignored) {
                                // 连接已关闭时 sendMessage 会抛异常，直接忽略即可
                            }
                        }
                    }
                    // readLine() 返回 null 说明 Python 进程的 stdout 已关闭（进程结束）
                } catch (IOException e) {
                    e.printStackTrace();
                }

                // ── 读取 stderr（异常捕获）──────────────────────────────────────
                // Python 崩溃时（未捕获异常、语法错误等）会向 stderr 输出堆栈信息
                // 这里将 stderr 每行包装成 error 类型的 JSON 帧推给前端
                // 注意：stdout 读完后才读 stderr，因为进程结束时 stdout 先关闭
                try (BufferedReader reader = new BufferedReader(
                        new InputStreamReader(process.getErrorStream()))) {
                    String line;
                    while ((line = reader.readLine()) != null) {
                        if (session.isOpen()) {
                            try {
                                // 对 line 中的双引号转义，避免破坏 JSON 结构
                                session.sendMessage(new TextMessage(
                                    "{\"type\": \"log\", \"status\": \"error\", \"message\": \"Stderr: "
                                    + line.replace("\"", "\\\"") + "\"}"
                                ));
                            } catch (Exception ignored) {}
                        }
                    }
                } catch (IOException e) {
                    e.printStackTrace();
                }

                // ── 发送"执行完毕"信号 ─────────────────────────────────────────
                // stdout 和 stderr 都读完，说明 Python 进程已正常退出
                // 发送 finished 帧通知前端将 debugStatus 切换回 stopped
                if (session.isOpen()) {
                    try {
                        session.sendMessage(new TextMessage("{\"type\": \"finished\"}"));
                    } catch (Exception ignored) {}
                }

            }).start(); // 立即启动 IO 监听线程，不阻塞当前回调线程

        // ────────────────────────────────────────────────────────────────────────
        // CASE 2：stop —— 立即终止 Python 进程
        // ────────────────────────────────────────────────────────────────────────
        } else if ("stop".equals(action)) {
            // 强杀进程并清理 Map，IO 监听线程随着进程关闭会自动退出循环
            terminateProcess(session.getId());

        // ────────────────────────────────────────────────────────────────────────
        // CASE 3：step / run / pause / update_node —— 控制指令透传到 Python stdin
        //
        // 这四个指令的共同点：不需要 Java 层做任何业务逻辑处理，
        // 直接将前端发来的完整 JSON 字符串透传进 Python 进程的 stdin 管道。
        // Python 内部的 debug_listener 线程会 readline() 读取后自行解析处理。
        //
        // 透传支持的指令示例：
        //   · {"action":"step","overrideCode":"device.click(10,20)"}  单步+代码注入
        //   · {"action":"run"}                                         取消断点持续运行
        //   · {"action":"pause"}                                       请求下一节点暂停
        //   · {"action":"update_node","nodeId":"1","nodeData":{"x":50}} 热更新节点参数
        // ────────────────────────────────────────────────────────────────────────
        } else if ("step".equals(action) || "run".equals(action)
                || "pause".equals(action) || "update_node".equals(action)) {

            BufferedWriter writer = processInputMap.get(session.getId());
            if (writer != null) {
                // 将原始 JSON 字符串写入 Python stdin，末尾加 "\n" 作为行分隔符
                // Python 的 stdin.readline() 以换行符为读取终止标志
                writer.write(message.getPayload() + "\n");
                // flush() 至关重要！BufferedWriter 会缓冲数据，
                // 不调用 flush() 指令就会一直卡在缓冲区里，Python 读不到
                writer.flush();
            }
        }
    }
}
