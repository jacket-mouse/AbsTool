package cn.edu.sdu.software.config;

import org.springframework.context.annotation.Configuration;
import org.springframework.web.socket.config.annotation.EnableWebSocket;
import org.springframework.web.socket.config.annotation.WebSocketConfigurer;
import org.springframework.web.socket.config.annotation.WebSocketHandlerRegistry;

@Configuration
@EnableWebSocket
public class WebSocketConfig implements WebSocketConfigurer {

    private final ScriptDebugWebSocketHandler debugWebSocketHandler;

    public WebSocketConfig(ScriptDebugWebSocketHandler debugWebSocketHandler) {
        this.debugWebSocketHandler = debugWebSocketHandler;
    }

    @Override
    public void registerWebSocketHandlers(WebSocketHandlerRegistry registry) {
        registry.addHandler(debugWebSocketHandler, "/api/ws/script/debug")
                .setAllowedOrigins("*"); // Allow all origins for dev
    }
}
