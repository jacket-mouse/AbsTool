package cn.edu.sdu.software.service.impl;

import cn.edu.sdu.software.dto.TaskDto;
import cn.edu.sdu.software.entity.TaskInfo;
import cn.edu.sdu.software.mapper.TaskInfoMapper;
import cn.edu.sdu.software.service.TaskService;
import com.baomidou.mybatisplus.core.conditions.query.QueryWrapper;
import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import org.springframework.beans.BeanUtils;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;
import org.springframework.util.StringUtils;

import java.time.LocalDateTime;
import java.util.UUID;
import java.util.stream.Collectors;

@Service
public class TaskServiceImpl implements TaskService {

    @Autowired
    private TaskInfoMapper taskInfoMapper;

    @Autowired
    private cn.edu.sdu.software.scheduler.TaskSchedulerManager taskSchedulerManager;

    @Override
    public Page<TaskDto> getTaskList(TaskDto.TaskListRequest request) {
        Page<TaskInfo> page = new Page<>(request.getPage(), request.getSize());
        QueryWrapper<TaskInfo> queryWrapper = new QueryWrapper<>();
        
        if (StringUtils.hasText(request.getKeyword())) {
            queryWrapper.like("name", request.getKeyword());
        }
        if (StringUtils.hasText(request.getStatus())) {
            queryWrapper.eq("status", request.getStatus());
        }
        
        queryWrapper.orderByDesc("create_time");
        taskInfoMapper.selectPage(page, queryWrapper);

        Page<TaskDto> dtoPage = new Page<>(request.getPage(), request.getSize(), page.getTotal());
        dtoPage.setRecords(page.getRecords().stream().map(this::convertToDto).collect(Collectors.toList()));
        return dtoPage;
    }

    @Override
    public TaskDto createTask(TaskDto.TaskCreateRequest request) {
        TaskInfo task = new TaskInfo();
        task.setTaskId(UUID.randomUUID().toString().replace("-", ""));
        task.setName(request.getName());
        task.setScriptId(request.getScriptId());
        task.setTemplateId(request.getTemplateId());
        task.setTriggerType(request.getTriggerType());
        task.setCronExpression(request.getCronExpression());
        task.setStatus("PENDING");
        task.setCreator(request.getCreator());
        task.setCreateTime(LocalDateTime.now());
        
        taskInfoMapper.insert(task);
        
        // Schedule if it is a cron task
        if ("SCHEDULED".equals(task.getTriggerType()) && task.getCronExpression() != null) {
            taskSchedulerManager.scheduleTask(task.getTaskId(), task.getCronExpression());
        }
        
        return convertToDto(task);
    }

    @Override
    public TaskDto updateTask(TaskDto.TaskUpdateRequest request) {
        TaskInfo task = taskInfoMapper.selectById(request.getTaskId());
        if (task != null) {
            task.setName(request.getName());
            task.setScriptId(request.getScriptId());
            task.setTemplateId(request.getTemplateId());
            task.setTriggerType(request.getTriggerType());
            task.setCronExpression(request.getCronExpression());
            taskInfoMapper.updateById(task);
            
            // Re-schedule based on updated info
            if ("SCHEDULED".equals(task.getTriggerType()) && task.getCronExpression() != null && !task.getCronExpression().isEmpty()) {
                taskSchedulerManager.scheduleTask(task.getTaskId(), task.getCronExpression());
            } else {
                taskSchedulerManager.cancelTask(task.getTaskId());
            }
            
            return convertToDto(task);
        }
        return null;
    }

    @Override
    public void deleteTask(String taskId) {
        taskInfoMapper.deleteById(taskId);
        taskSchedulerManager.cancelTask(taskId);
    }

    @Override
    public void updateTaskStatus(String taskId, String status) {
        TaskInfo task = taskInfoMapper.selectById(taskId);
        if (task != null) {
            task.setStatus(status);
            if ("RUNNING".equals(status)) {
                task.setStartTime(LocalDateTime.now());
            } else if ("COMPLETED".equals(status) || "FAILED".equals(status)) {
                task.setEndTime(LocalDateTime.now());
            }
            taskInfoMapper.updateById(task);
        }
    }

    @Override
    public TaskDto getTaskDetail(String taskId) {
        TaskInfo task = taskInfoMapper.selectById(taskId);
        if (task == null) return null;
        return convertToDto(task);
    }
    
    private TaskDto convertToDto(TaskInfo info) {
        TaskDto dto = new TaskDto();
        BeanUtils.copyProperties(info, dto);
        return dto;
    }
}
