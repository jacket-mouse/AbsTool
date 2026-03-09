package cn.edu.sdu.software.dto;

import cn.edu.sdu.software.model.ScriptConfig;
import java.util.List;

public class ScriptEditorDto {

    public static class SaveRequest {
        private String scriptId;
        private String scriptName;
        private String scriptType;
        private ScriptConfig content;
        private String changelog;
        
        public String getScriptId() { return scriptId; }
        public void setScriptId(String scriptId) { this.scriptId = scriptId; }
        public String getScriptName() { return scriptName; }
        public void setScriptName(String scriptName) { this.scriptName = scriptName; }
        public String getScriptType() { return scriptType; }
        public void setScriptType(String scriptType) { this.scriptType = scriptType; }
        public ScriptConfig getContent() { return content; }
        public void setContent(ScriptConfig content) { this.content = content; }
        public String getChangelog() { return changelog; }
        public void setChangelog(String changelog) { this.changelog = changelog; }
    }

    public static class SaveResponse {
        private boolean success;
        private String scriptId;
        private String version;
        private String message;
        
        public SaveResponse() {}
        public SaveResponse(boolean success, String scriptId, String version, String message) {
            this.success = success;
            this.scriptId = scriptId;
            this.version = version;
            this.message = message;
        }
        public boolean isSuccess() { return success; }
        public void setSuccess(boolean success) { this.success = success; }
        public String getScriptId() { return scriptId; }
        public void setScriptId(String scriptId) { this.scriptId = scriptId; }
        public String getVersion() { return version; }
        public void setVersion(String version) { this.version = version; }
        public String getMessage() { return message; }
        public void setMessage(String message) { this.message = message; }
    }

    public static class ValidateRequest {
        private ScriptConfig content;
        public ScriptConfig getContent() { return content; }
        public void setContent(ScriptConfig content) { this.content = content; }
    }

    public static class ValidateResponse {
        private boolean success;
        private List<String> errors;
        public ValidateResponse() {}
        public ValidateResponse(boolean success, List<String> errors) {
            this.success = success;
            this.errors = errors;
        }
        public boolean isSuccess() { return success; }
        public void setSuccess(boolean success) { this.success = success; }
        public List<String> getErrors() { return errors; }
        public void setErrors(List<String> errors) { this.errors = errors; }
    }

    public static class PreviewRequest {
        private ScriptConfig content;
        public ScriptConfig getContent() { return content; }
        public void setContent(ScriptConfig content) { this.content = content; }
    }

    public static class PreviewResponse {
        private String code;
        public PreviewResponse() {}
        public PreviewResponse(String code) { this.code = code; }
        public String getCode() { return code; }
        public void setCode(String code) { this.code = code; }
    }

    public static class LoadResponse {
        private String scriptName;
        private ScriptConfig content;
        public LoadResponse() {}
        public LoadResponse(String scriptName, ScriptConfig content) {
            this.scriptName = scriptName;
            this.content = content;
        }
        public String getScriptName() { return scriptName; }
        public void setScriptName(String scriptName) { this.scriptName = scriptName; }
        public ScriptConfig getContent() { return content; }
        public void setContent(ScriptConfig content) { this.content = content; }
    }

    public static class HistoryVersionDto {
        private String versionId;
        private String version;
        private String createTime;
        private String summary;
        
        public HistoryVersionDto() {}
        public HistoryVersionDto(String versionId, String version, String createTime, String summary) {
            this.versionId = versionId;
            this.version = version;
            this.createTime = createTime;
            this.summary = summary;
        }
        public String getVersionId() { return versionId; }
        public void setVersionId(String versionId) { this.versionId = versionId; }
        public String getVersion() { return version; }
        public void setVersion(String version) { this.version = version; }
        public String getCreateTime() { return createTime; }
        public void setCreateTime(String createTime) { this.createTime = createTime; }
        public String getSummary() { return summary; }
        public void setSummary(String summary) { this.summary = summary; }
    }

    public static class HistoryResponse {
        private List<HistoryVersionDto> list;
        public HistoryResponse() {}
        public HistoryResponse(List<HistoryVersionDto> list) { this.list = list; }
        public List<HistoryVersionDto> getList() { return list; }
        public void setList(List<HistoryVersionDto> list) { this.list = list; }
    }
}
