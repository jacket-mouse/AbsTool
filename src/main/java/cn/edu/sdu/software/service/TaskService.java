package cn.edu.sdu.software.service;

import cn.edu.sdu.software.dto.TaskDto;
import cn.edu.sdu.software.entity.TaskInfo;
import com.baomidou.mybatisplus.extension.plugins.pagination.Page;

public interface TaskService {
    Page<TaskDto> getTaskList(TaskDto.TaskListRequest request);
    TaskDto createTask(TaskDto.TaskCreateRequest request);
    void deleteTask(String taskId);
    void updateTaskStatus(String taskId, String status);
    TaskDto updateTask(TaskDto.TaskUpdateRequest request);
    TaskDto getTaskDetail(String taskId);
}
