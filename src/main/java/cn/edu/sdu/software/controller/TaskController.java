package cn.edu.sdu.software.controller;

import cn.edu.sdu.software.dto.TaskDto;
import cn.edu.sdu.software.service.TaskService;
import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.web.bind.annotation.*;

import java.util.HashMap;
import java.util.Map;

@RestController
@RequestMapping("/api/task")
public class TaskController {

    @Autowired
    private TaskService taskService;

    @PostMapping("/list")
    public Object list(@RequestBody TaskDto.TaskListRequest request) {
        Page<TaskDto> resultPage = taskService.getTaskList(request);

        Map<String, Object> data = new HashMap<>();
        data.put("list", resultPage.getRecords());
        data.put("total", resultPage.getTotal());

        Map<String, Object> result = new HashMap<>();
        result.put("success", true);
        result.put("data", data);
        return result;
    }

    @PostMapping("/create")
    public Object create(@RequestBody TaskDto.TaskCreateRequest request) {
        Map<String, Object> result = new HashMap<>();
        try {
            TaskDto dto = taskService.createTask(request);
            result.put("success", true);
            result.put("data", dto);
        } catch (Exception e) {
            result.put("success", false);
            result.put("message", e.getMessage());
        }
        return result;
    }

    @DeleteMapping("/delete/{taskId}")
    public Object delete(@PathVariable("taskId") String taskId) {
        Map<String, Object> result = new HashMap<>();
        try {
            taskService.deleteTask(taskId);
            result.put("success", true);
        } catch (Exception e) {
            result.put("success", false);
            result.put("message", e.getMessage());
        }
        return result;
    }
    @PostMapping("/update")
    public Object update(@RequestBody TaskDto.TaskUpdateRequest request) {
        Map<String, Object> result = new HashMap<>();
        try {
            TaskDto dto = taskService.updateTask(request);
            result.put("success", true);
            result.put("data", dto);
        } catch (Exception e) {
            result.put("success", false);
            result.put("message", e.getMessage());
        }
        return result;
    }

    @PostMapping("/updateStatus")
    public Object updateStatus(@RequestBody Map<String, String> body) {
        Map<String, Object> result = new HashMap<>();
        try {
            taskService.updateTaskStatus(body.get("taskId"), body.get("status"));
            result.put("success", true);
        } catch (Exception e) {
            result.put("success", false);
            result.put("message", e.getMessage());
        }
        return result;
    }
}
