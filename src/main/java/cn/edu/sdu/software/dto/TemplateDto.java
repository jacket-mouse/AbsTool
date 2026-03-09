package cn.edu.sdu.software.dto;

import lombok.Data;
import java.util.List;
import com.fasterxml.jackson.annotation.JsonFormat;

public class TemplateDto {
    private String templateId;
    private String name;
    private String description;
    private String creator;
    
    @JsonFormat(pattern = "yyyy-MM-dd HH:mm:ss", timezone = "GMT+8")
    private java.time.LocalDateTime createTime;
    
    // List of scripts associated with this template
    private List<TemplateScriptDto> scripts;

    public String getTemplateId() { return templateId; }
    public void setTemplateId(String templateId) { this.templateId = templateId; }
    
    public String getName() { return name; }
    public void setName(String name) { this.name = name; }
    
    public String getDescription() { return description; }
    public void setDescription(String description) { this.description = description; }
    
    public String getCreator() { return creator; }
    public void setCreator(String creator) { this.creator = creator; }
    
    public java.time.LocalDateTime getCreateTime() { return createTime; }
    public void setCreateTime(java.time.LocalDateTime createTime) { this.createTime = createTime; }
    
    public List<TemplateScriptDto> getScripts() { return scripts; }
    public void setScripts(List<TemplateScriptDto> scripts) { this.scripts = scripts; }

    public static class TemplateScriptDto {
        private String scriptId;
        private Integer sortOrder;
        private Integer isDefault;
        
        public String getScriptId() { return scriptId; }
        public void setScriptId(String scriptId) { this.scriptId = scriptId; }
        
        public Integer getSortOrder() { return sortOrder; }
        public void setSortOrder(Integer sortOrder) { this.sortOrder = sortOrder; }
        
        public Integer getIsDefault() { return isDefault; }
        public void setIsDefault(Integer isDefault) { this.isDefault = isDefault; }
    }
}
