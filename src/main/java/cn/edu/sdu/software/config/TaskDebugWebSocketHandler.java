package cn.edu.sdu.software.config;

import cn.edu.sdu.software.engine.PythonScriptGenerator;
import cn.edu.sdu.software.model.ScriptConfig;
import cn.edu.sdu.software.service.TaskService;
import cn.edu.sdu.software.entity.ScriptExecLog;
import cn.edu.sdu.software.mapper.ScriptExecLogMapper;
import cn.edu.sdu.software.service.TemplateService;
import cn.edu.sdu.software.service.ScriptService;
import cn.edu.sdu.software.dto.ScriptEditorDto;
import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.springframework.stereotype.Component;
import org.springframework.web.socket.CloseStatus;
import org.springframework.web.socket.TextMessage;
import org.springframework.web.socket.WebSocketSession;
import org.springframework.web.socket.handler.TextWebSocketHandler;

import java.io.*;
import java.time.LocalDateTime;
import java.util.Map;
import java.util.UUID;
import java.util.concurrent.ConcurrentHashMap;

@Component
public class TaskDebugWebSocketHandler extends TextWebSocketHandler {

    private final ObjectMapper objectMapper;
    private final PythonScriptGenerator pythonScriptGenerator;
    private final TaskService taskService;
    private final ScriptExecLogMapper logMapper;
    private final TemplateService templateService;
    private final ScriptService scriptService;

    private final Map<String, Process> processMap = new ConcurrentHashMap<>();
    private final Map<String, BufferedWriter> processInputMap = new ConcurrentHashMap<>();
    private final Map<String, String> sessionTaskMap = new ConcurrentHashMap<>(); // sessionId -> taskId
    
    // For calculating execution duration
    private final Map<String, Long> taskStartTimeMap = new ConcurrentHashMap<>();

    public TaskDebugWebSocketHandler(ObjectMapper objectMapper, 
                                    PythonScriptGenerator pythonScriptGenerator,
                                    TaskService taskService,
                                    ScriptExecLogMapper logMapper,
                                    TemplateService templateService,
                                    ScriptService scriptService) {
        this.objectMapper = objectMapper;
        this.pythonScriptGenerator = pythonScriptGenerator;
        this.taskService = taskService;
        this.logMapper = logMapper;
        this.templateService = templateService;
        this.scriptService = scriptService;
    }

    @Override
    public void afterConnectionEstablished(WebSocketSession session) {
        System.out.println("Task WebSocket Connected: " + session.getId());
    }

    @Override
    public void afterConnectionClosed(WebSocketSession session, CloseStatus status) {
        System.out.println("Task WebSocket Closed: " + session.getId());
        terminateProcess(session.getId());
    }

    private void terminateProcess(String sessionId) {
        Process p = processMap.remove(sessionId);
        if (p != null) {
            p.destroyForcibly();
        }
        processInputMap.remove(sessionId);
        
        String taskId = sessionTaskMap.remove(sessionId);
        if (taskId != null) {
            // Unclean exit, mark task as FAILED if still running
            try {
                cn.edu.sdu.software.dto.TaskDto task = taskService.getTaskDetail(taskId);
                if (task != null && "RUNNING".equals(task.getStatus())) {
                    taskService.updateTaskStatus(taskId, "FAILED");
                }
            } catch (Exception e) {}
        }
        taskStartTimeMap.remove(sessionId);
    }

    @Override
    protected void handleTextMessage(WebSocketSession session, TextMessage message) throws Exception {
        JsonNode root = objectMapper.readTree(message.getPayload());
        String action = root.has("action") ? root.get("action").asText() : "";
        String taskId = root.has("taskId") ? root.get("taskId").asText() : "";

        if ("start".equals(action) && !taskId.isEmpty()) {
            terminateProcess(session.getId());
            sessionTaskMap.put(session.getId(), taskId);
            taskStartTimeMap.put(session.getId(), System.currentTimeMillis());

            // 1. Mark task as RUNNING
            taskService.updateTaskStatus(taskId, "RUNNING");

            // 2. Retrieve Task Information and prepare Python Script
            cn.edu.sdu.software.dto.TaskDto taskDto = taskService.getTaskDetail(taskId);
            String pythonCode = "";
            
            try {
                if (taskDto.getTemplateId() != null && !taskDto.getTemplateId().isEmpty()) {
                    pythonCode = templateService.generatePythonForTemplate(taskDto.getTemplateId());
                } else if (taskDto.getScriptId() != null && !taskDto.getScriptId().isEmpty()) {
                    ScriptEditorDto.LoadResponse loadRes = scriptService.loadScript(taskDto.getScriptId());
                    pythonCode = pythonScriptGenerator.generate(loadRes.getContent());
                } else {
                    throw new RuntimeException("Task has no script or template configured.");
                }
            } catch (Exception e) {
                // Formatting error
                taskService.updateTaskStatus(taskId, "FAILED");
                session.sendMessage(new TextMessage("{\"type\": \"log\", \"status\": \"error\", \"message\": \"Failed to compile script: " + e.getMessage() + "\"}"));
                return;
            }

            File tempFile = File.createTempFile("task_script_" + session.getId(), ".py");
            try (PrintWriter out = new PrintWriter(tempFile)) {
                out.println(pythonCode);
            }

            ProcessBuilder pb = new ProcessBuilder(
                "/Users/leeson/Documents/毕业设计/AbsTool/venv/bin/python3",
                "-u",                          
                tempFile.getAbsolutePath()     
            );
            Process process = pb.start();

            processMap.put(session.getId(), process);
            processInputMap.put(session.getId(), new BufferedWriter(new OutputStreamWriter(process.getOutputStream())));

            new Thread(() -> {
                try (BufferedReader reader = new BufferedReader(new InputStreamReader(process.getInputStream()))) {
                    String line;
                    while ((line = reader.readLine()) != null) {
                        try {
                            JsonNode logNode = objectMapper.readTree(line);
                            if (logNode.has("type") && "log".equals(logNode.get("type").asText())) {
                                // Realtime output to frontend
                                if (session.isOpen()) session.sendMessage(new TextMessage(line));
                                
                                // Save to DB
                                String status = logNode.has("status") ? logNode.get("status").asText() : "SUCCESS";
                                String msg = logNode.has("message") ? logNode.get("message").asText() : "";
                                String stepName = logNode.has("action") ? logNode.get("action").asText() : "Execution Step";
                                
                                ScriptExecLog execLog = new ScriptExecLog();
                                execLog.setLogId(UUID.randomUUID().toString().replace("-", ""));
                                execLog.setTaskId(taskId);
                                execLog.setScriptId(taskDto.getScriptId());
                                execLog.setStepName(stepName);
                                execLog.setStatus("error".equals(status) ? "FAIL" : "SUCCESS"); // Normalize to DB schema
                                execLog.setErrorMsg("error".equals(status) ? msg : null);
                                execLog.setExecTime(LocalDateTime.now());
                                
                                // Simple mock duration for individual steps, since we don't have accurate step end times currently
                                execLog.setDuration(100); 
                                logMapper.insert(execLog);
                            } else {
                                if (session.isOpen()) session.sendMessage(new TextMessage(line));
                            }
                        } catch (Exception e) {
                            if (session.isOpen()) session.sendMessage(new TextMessage(line));
                        }
                    }
                } catch (IOException e) {
                    e.printStackTrace();
                }

                boolean hasError = false;
                try (BufferedReader reader = new BufferedReader(new InputStreamReader(process.getErrorStream()))) {
                    String line;
                    while ((line = reader.readLine()) != null) {
                        hasError = true;
                        if (session.isOpen()) {
                            try {
                                session.sendMessage(new TextMessage(
                                    "{\"type\": \"log\", \"status\": \"error\", \"message\": \"Stderr: "
                                    + line.replace("\"", "\\\"") + "\"}"
                                ));
                                
                                ScriptExecLog execLog = new ScriptExecLog();
                                execLog.setLogId(UUID.randomUUID().toString().replace("-", ""));
                                execLog.setTaskId(taskId);
                                execLog.setStepName("System Error");
                                execLog.setStatus("FAIL");
                                execLog.setErrorMsg(line);
                                execLog.setExecTime(LocalDateTime.now());
                                logMapper.insert(execLog);
                                
                            } catch (Exception ignored) {}
                        }
                    }
                } catch (IOException e) {
                    e.printStackTrace();
                }

                // Finishing Task
                taskService.updateTaskStatus(taskId, hasError ? "FAILED" : "COMPLETED");

                if (session.isOpen()) {
                    try {
                        long duration = System.currentTimeMillis() - taskStartTimeMap.getOrDefault(session.getId(), System.currentTimeMillis());
                        // Send report and finished event
                        String report = String.format("{\"type\": \"report\", \"duration\": %d, \"success\": %b}", duration, !hasError);
                        session.sendMessage(new TextMessage(report));
                        session.sendMessage(new TextMessage("{\"type\": \"finished\"}"));
                    } catch (Exception ignored) {}
                }

                sessionTaskMap.remove(session.getId());
                taskStartTimeMap.remove(session.getId());
            }).start(); 

        } else if ("stop".equals(action)) {
            terminateProcess(session.getId());
            if (!taskId.isEmpty()) {
                taskService.updateTaskStatus(taskId, "FAILED");
            }
        }
    }
}
