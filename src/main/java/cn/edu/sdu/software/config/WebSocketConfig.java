package cn.edu.sdu.software.config;

import org.springframework.context.annotation.Configuration;
import org.springframework.web.socket.config.annotation.EnableWebSocket;
import org.springframework.web.socket.config.annotation.WebSocketConfigurer;
import org.springframework.web.socket.config.annotation.WebSocketHandlerRegistry;

/**
 * ┌─────────────────────────────────────────────────────────────────────┐
 * │                    WebSocket 全局配置类                               │
 * │                                                                     │
 * │  职责：将 WebSocket 处理器（Handler）绑定到特定 URL 路径，               │
 * │        实现从 HTTP 协议到 WebSocket 协议的"升级"入口点注册。             │
 * │                                                                     │
 * │  WebSocket 握手流程：                                                 │
 * │    ① 前端发起 HTTP GET 请求，携带 Upgrade: websocket 请求头             │
 * │    ② Spring 识别该路径已注册 Handler，响应 101 Switching Protocols      │
 * │    ③ 连接升级为全双工 TCP 长连接，后续通信不再走 HTTP                    │
 * │    ④ ScriptDebugWebSocketHandler 接管该连接的所有生命周期事件           │
 * └─────────────────────────────────────────────────────────────────────┘
 */
@Configuration  // 声明这是一个 Spring 配置类，容器启动时自动扫描并加载
@EnableWebSocket // 激活 Spring WebSocket 支持，相当于打开"开关"，
                 // 使得 WebSocketConfigurer 接口的 registerWebSocketHandlers 方法会被调用
public class WebSocketConfig implements WebSocketConfigurer {

    /**
     * 通过构造器注入调试专用 Handler。
     * 使用构造器注入（而非 @Autowired 字段注入）是 Spring 官方推荐做法，
     * 好处：依赖关系明确、方便单测 Mock、避免循环依赖。
     */
    private final ScriptDebugWebSocketHandler debugWebSocketHandler;
    private final TaskDebugWebSocketHandler taskWebSocketHandler;

    public WebSocketConfig(ScriptDebugWebSocketHandler debugWebSocketHandler,
                           TaskDebugWebSocketHandler taskWebSocketHandler) {
        this.debugWebSocketHandler = debugWebSocketHandler;
        this.taskWebSocketHandler = taskWebSocketHandler;
    }

    /**
     * 注册 WebSocket 处理器 —— 系统中所有 WebSocket 端点均在此方法中声明。
     *
     * @param registry Spring 提供的 Handler 注册表，调用 addHandler 即可完成绑定
     *
     * 关键配置说明：
     *  · addHandler(handler, path)：将 Handler 与 URL 路径绑定
     *    - 当前路径：/api/ws/script/debug（用于脚本实时调试）
     *    - 协议格式：ws://host/api/ws/script/debug（HTTP）
     *             或 wss://host/api/ws/script/debug（HTTPS 下自动使用）
     *
     *  · setAllowedOrigins("*")：设置跨域策略
     *    - 开发阶段允许所有域名（*），避免浏览器同源策略拦截
     *    - 生产环境建议改为具体域名，例如 .setAllowedOrigins("https://yourdomain.com")
     */
    @Override
    public void registerWebSocketHandlers(WebSocketHandlerRegistry registry) {
        registry.addHandler(debugWebSocketHandler, "/api/ws/script/debug")
                .setAllowedOrigins("*"); 
                
        registry.addHandler(taskWebSocketHandler, "/api/ws/task/execute")
                .setAllowedOrigins("*");
    }
}
