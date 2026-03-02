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

@Component
public class ScriptDebugWebSocketHandler extends TextWebSocketHandler {

    private final ObjectMapper objectMapper;
    private final PythonScriptGenerator pythonScriptGenerator;

    // session ID to running Process
    private final Map<String, Process> processMap = new ConcurrentHashMap<>();
    private final Map<String, BufferedWriter> processInputMap = new ConcurrentHashMap<>();

    public ScriptDebugWebSocketHandler(ObjectMapper objectMapper, PythonScriptGenerator pythonScriptGenerator) {
        this.objectMapper = objectMapper;
        this.pythonScriptGenerator = pythonScriptGenerator;
    }

    @Override
    public void afterConnectionEstablished(WebSocketSession session) {
        System.out.println("Debug WebSocket Connected: " + session.getId());
    }

    @Override
    public void afterConnectionClosed(WebSocketSession session, CloseStatus status) {
        System.out.println("Debug WebSocket Closed: " + session.getId());
        terminateProcess(session.getId());
    }

    private void terminateProcess(String sessionId) {
        Process p = processMap.remove(sessionId);
        if (p != null) {
            p.destroyForcibly();
        }
        processInputMap.remove(sessionId);
    }

    @Override
    protected void handleTextMessage(WebSocketSession session, TextMessage message) throws Exception {
        JsonNode root = objectMapper.readTree(message.getPayload());
        String action = root.has("action") ? root.get("action").asText() : "";

        if ("start".equals(action)) {
            // Terminate existing if any
            terminateProcess(session.getId());

            ScriptConfig config = objectMapper.treeToValue(root.get("config"), ScriptConfig.class);
            
            // Generate Debug Python Script
            String pythonCode = pythonScriptGenerator.generateDebug(config);

            // Write to a temporary file
            File tempFile = File.createTempFile("debug_script_" + session.getId(), ".py");
            try (PrintWriter out = new PrintWriter(tempFile)) {
                out.println(pythonCode);
            }

            // Start Python Process
            // Start Python Process using venv python
            ProcessBuilder pb = new ProcessBuilder("/Users/leeson/Documents/毕业设计/AbsTool/venv/bin/python3", "-u", tempFile.getAbsolutePath());
            Process process = pb.start();
            processMap.put(session.getId(), process);
            processInputMap.put(session.getId(), new BufferedWriter(new OutputStreamWriter(process.getOutputStream())));

            // Start a thread to read stdout and forward to websocket
            new Thread(() -> {
                try (BufferedReader reader = new BufferedReader(new InputStreamReader(process.getInputStream()))) {
                    String line;
                    while ((line = reader.readLine()) != null) {
                        if (session.isOpen()) {
                            try {
                                session.sendMessage(new TextMessage(line));
                            } catch(Exception ignored) {}
                        }
                    }
                } catch (IOException e) {
                    e.printStackTrace();
                }
                
                // Read stderr
                try (BufferedReader reader = new BufferedReader(new InputStreamReader(process.getErrorStream()))) {
                    String line;
                    while ((line = reader.readLine()) != null) {
                        if (session.isOpen()) {
                            try {
                                session.sendMessage(new TextMessage("{\"type\": \"log\", \"status\": \"error\", \"message\": \"Stderr: " + line.replace("\"", "\\\"") + "\"}"));
                            } catch(Exception ignored) {}
                        }
                    }
                } catch (IOException e) {
                    e.printStackTrace();
                }
                
                if (session.isOpen()) {
                    try {
                        session.sendMessage(new TextMessage("{\"type\": \"finished\"}"));
                    } catch(Exception ignored) {}
                }
            }).start();
        } else if ("stop".equals(action)) {
            terminateProcess(session.getId());
        } else if ("step".equals(action) || "run".equals(action)) {
            BufferedWriter writer = processInputMap.get(session.getId());
            if (writer != null) {
                // Forward the command to python script stdin
                // "{"action": "run", "overrideCode": "device.click(10,20)"}"
                writer.write(message.getPayload() + "\n");
                writer.flush();
            }
        }
    }
}
