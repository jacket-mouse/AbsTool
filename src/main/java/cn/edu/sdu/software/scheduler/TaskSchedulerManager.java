package cn.edu.sdu.software.scheduler;

import cn.edu.sdu.software.dto.ScriptEditorDto;
import cn.edu.sdu.software.dto.TaskDto;
import cn.edu.sdu.software.engine.PythonScriptGenerator;
import cn.edu.sdu.software.entity.ScriptExecLog;
import cn.edu.sdu.software.entity.TaskInfo;
import cn.edu.sdu.software.mapper.ScriptExecLogMapper;
import cn.edu.sdu.software.mapper.TaskInfoMapper;
import cn.edu.sdu.software.service.ScriptService;
import cn.edu.sdu.software.service.TemplateService;
import com.baomidou.mybatisplus.core.conditions.query.QueryWrapper;
import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.springframework.context.annotation.Lazy;
import org.springframework.scheduling.concurrent.ThreadPoolTaskScheduler;
import org.springframework.scheduling.support.CronTrigger;
import org.springframework.stereotype.Component;

import jakarta.annotation.PostConstruct;
import jakarta.annotation.PreDestroy;
import java.io.*;
import java.time.LocalDateTime;
import java.util.List;
import java.util.Map;
import java.util.UUID;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.ScheduledFuture;

@Component
public class TaskSchedulerManager {

    private final TaskInfoMapper taskMapper;
    private final ThreadPoolTaskScheduler taskScheduler;
    private final Map<String, ScheduledFuture<?>> scheduledTasks = new ConcurrentHashMap<>();
    
    private final ObjectMapper objectMapper;
    private final PythonScriptGenerator pythonScriptGenerator;
    private final ScriptExecLogMapper logMapper;
    private final TemplateService templateService;
    private final ScriptService scriptService;

    public TaskSchedulerManager(TaskInfoMapper taskMapper,
                                ObjectMapper objectMapper,
                                PythonScriptGenerator pythonScriptGenerator,
                                ScriptExecLogMapper logMapper,
                                TemplateService templateService,
                                ScriptService scriptService) {
        this.taskMapper = taskMapper;
        this.objectMapper = objectMapper;
        this.pythonScriptGenerator = pythonScriptGenerator;
        this.logMapper = logMapper;
        this.templateService = templateService;
        this.scriptService = scriptService;

        this.taskScheduler = new ThreadPoolTaskScheduler();
        this.taskScheduler.setPoolSize(10);
        this.taskScheduler.setThreadNamePrefix("TaskScheduler-");
        this.taskScheduler.initialize();
    }

    @PostConstruct
    public void initAllScheduledTasks() {
        QueryWrapper<TaskInfo> query = new QueryWrapper<>();
        query.eq("trigger_type", "SCHEDULED").isNotNull("cron_expression");
        List<TaskInfo> tasks = taskMapper.selectList(query);
        for (TaskInfo task : tasks) {
            scheduleTask(task.getTaskId(), task.getCronExpression());
        }
    }

    public void scheduleTask(String taskId, String cron) {
        cancelTask(taskId);
        if (cron == null || cron.trim().isEmpty()) {
            return;
        }
        try {
            ScheduledFuture<?> future = taskScheduler.schedule(() -> executeBackground(taskId), new CronTrigger(cron));
            scheduledTasks.put(taskId, future);
            System.out.println("Scheduled Task Setup: " + taskId + " with cron: " + cron);
        } catch (Exception e) {
            System.err.println("Failed to schedule task " + taskId + ": " + e.getMessage());
        }
    }

    public void cancelTask(String taskId) {
        ScheduledFuture<?> future = scheduledTasks.remove(taskId);
        if (future != null) {
            future.cancel(false);
            System.out.println("Canceled Scheduled Task: " + taskId);
        }
    }

    @PreDestroy
    public void destroy() {
        this.taskScheduler.destroy();
    }

    private void updateTaskStatus(TaskInfo task, String status) {
        task.setStatus(status);
        if ("RUNNING".equals(status)) {
            task.setStartTime(LocalDateTime.now());
        } else if ("COMPLETED".equals(status) || "FAILED".equals(status)) {
            task.setEndTime(LocalDateTime.now());
        }
        taskMapper.updateById(task);
    }

    private void executeBackground(String taskId) {
        System.out.println("Executing Cron Task Background: " + taskId);
        TaskInfo task = taskMapper.selectById(taskId);
        if (task == null) return;
        
        try {
            updateTaskStatus(task, "RUNNING");
            
            String pythonCode = "";
            if (task.getTemplateId() != null && !task.getTemplateId().isEmpty()) {
                pythonCode = templateService.generatePythonForTemplate(task.getTemplateId());
            } else if (task.getScriptId() != null && !task.getScriptId().isEmpty()) {
                ScriptEditorDto.LoadResponse loadRes = scriptService.loadScript(task.getScriptId());
                pythonCode = pythonScriptGenerator.generate(loadRes.getContent());
            } else {
                throw new RuntimeException("No script or template configured.");
            }

            File tempFile = File.createTempFile("cron_task_", ".py");
            try (PrintWriter out = new PrintWriter(tempFile)) {
                out.println(pythonCode);
            }

            ProcessBuilder pb = new ProcessBuilder(
                "/Users/leeson/Documents/毕业设计/AbsTool/venv/bin/python3",
                "-u",                          
                tempFile.getAbsolutePath()     
            );
            Process process = pb.start();

            boolean hasError = false;
            try (BufferedReader reader = new BufferedReader(new InputStreamReader(process.getInputStream()))) {
                String line;
                while ((line = reader.readLine()) != null) {
                    try {
                        JsonNode logNode = objectMapper.readTree(line);
                        if (logNode.has("type") && "log".equals(logNode.get("type").asText())) {
                            String status = logNode.has("status") ? logNode.get("status").asText() : "SUCCESS";
                            String msg = logNode.has("message") ? logNode.get("message").asText() : "";
                            String stepName = logNode.has("action") ? logNode.get("action").asText() : "Execution Step";
                            ScriptExecLog execLog = new ScriptExecLog();
                            execLog.setLogId(UUID.randomUUID().toString().replace("-", ""));
                            execLog.setTaskId(taskId);
                            execLog.setScriptId(task.getScriptId());
                            execLog.setStepName(stepName);
                            execLog.setStatus("error".equals(status) ? "FAIL" : "SUCCESS");
                            execLog.setErrorMsg("error".equals(status) ? msg : null);
                            execLog.setExecTime(LocalDateTime.now());
                            execLog.setDuration(100); 
                            logMapper.insert(execLog);
                        }
                    } catch (Exception ignored) {}
                }
            }

            try (BufferedReader reader = new BufferedReader(new InputStreamReader(process.getErrorStream()))) {
                String line;
                while ((line = reader.readLine()) != null) {
                    hasError = true;
                    ScriptExecLog execLog = new ScriptExecLog();
                    execLog.setLogId(UUID.randomUUID().toString().replace("-", ""));
                    execLog.setTaskId(taskId);
                    execLog.setStepName("System Error");
                    execLog.setStatus("FAIL");
                    execLog.setErrorMsg(line);
                    execLog.setExecTime(LocalDateTime.now());
                    logMapper.insert(execLog);
                }
            }

            int exitCode = process.waitFor();
            updateTaskStatus(task, (hasError || exitCode != 0) ? "FAILED" : "COMPLETED");
            
        } catch (Exception e) {
            e.printStackTrace();
            updateTaskStatus(task, "FAILED");
            
            ScriptExecLog execLog = new ScriptExecLog();
            execLog.setLogId(UUID.randomUUID().toString().replace("-", ""));
            execLog.setTaskId(taskId);
            execLog.setStepName("System Exception");
            execLog.setStatus("FAIL");
            execLog.setErrorMsg(e.getMessage());
            execLog.setExecTime(LocalDateTime.now());
            logMapper.insert(execLog);
        }
    }
}
