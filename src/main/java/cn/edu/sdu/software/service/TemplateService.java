package cn.edu.sdu.software.service;

import cn.edu.sdu.software.dto.TemplateDto;
import com.baomidou.mybatisplus.extension.plugins.pagination.Page;

public interface TemplateService {
    
    Page<TemplateDto> listTemplates(int page, int size, String keyword);
    
    void saveTemplate(TemplateDto dto, String userId);
    
    void deleteTemplate(String templateId);
    
    TemplateDto getTemplateDetail(String templateId);

    String generatePythonForTemplate(String templateId) throws Exception;
}
