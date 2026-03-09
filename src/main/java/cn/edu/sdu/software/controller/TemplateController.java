package cn.edu.sdu.software.controller;

import cn.edu.sdu.software.dto.TemplateDto;
import cn.edu.sdu.software.service.TemplateService;
import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import org.springframework.web.bind.annotation.*;

import org.springframework.beans.factory.annotation.Autowired;
import java.util.HashMap;
import java.util.Map;

@RestController
@RequestMapping("/api/template")
public class TemplateController {

    @Autowired
    private TemplateService templateService;

    @PostMapping("/list")
    public Object list(@RequestBody Map<String, Object> params) {
        int page = (int) params.getOrDefault("page", 1);
        int size = (int) params.getOrDefault("size", 10);
        String keyword = (String) params.get("keyword");

        Page<TemplateDto> resultPage = templateService.listTemplates(page, size, keyword);

        Map<String, Object> data = new HashMap<>();
        data.put("list", resultPage.getRecords());
        data.put("total", resultPage.getTotal());

        Map<String, Object> result = new HashMap<>();
        result.put("success", true);
        result.put("data", data);
        return result;
    }

    @PostMapping("/save")
    public Object save(@RequestBody TemplateDto dto) {
        Map<String, Object> result = new HashMap<>();
        try {
            templateService.saveTemplate(dto, dto.getCreator() != null ? dto.getCreator() : "anonymous");
            result.put("success", true);
        } catch (Exception e) {
            result.put("success", false);
            result.put("message", e.getMessage());
        }
        return result;
    }

    @DeleteMapping("/delete/{id}")
    public Object delete(@PathVariable("id") String id) {
        Map<String, Object> result = new HashMap<>();
        try {
            templateService.deleteTemplate(id);
            result.put("success", true);
        } catch (Exception e) {
            result.put("success", false);
            result.put("message", e.getMessage());
        }
        return result;
    }

    @GetMapping("/detail/{id}")
    public Object detail(@PathVariable("id") String id) {
        Map<String, Object> result = new HashMap<>();
        try {
            TemplateDto dto = templateService.getTemplateDetail(id);
            result.put("success", true);
            result.put("data", dto);
        } catch (Exception e) {
            result.put("success", false);
            result.put("message", e.getMessage());
        }
        return result;
    }

    @GetMapping("/python/{id}")
    public String generatePython(@PathVariable("id") String id) {
        try {
            return templateService.generatePythonForTemplate(id);
        } catch (Exception e) {
            return "# Generate Error: " + e.getMessage();
        }
    }
}
