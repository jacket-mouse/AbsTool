package cn.edu.sdu.software.dto;

import cn.edu.sdu.software.model.ScriptConfig;
import java.util.List;

public class ScriptEditorDto {

    public static class SaveRequest {
        private String scriptId;
        private String scriptName;
        private String scriptType;
        private ScriptConfig content;
        
        public String getScriptId() { return scriptId; }
        public void setScriptId(String scriptId) { this.scriptId = scriptId; }
        public String getScriptName() { return scriptName; }
        public void setScriptName(String scriptName) { this.scriptName = scriptName; }
        public String getScriptType() { return scriptType; }
        public void setScriptType(String scriptType) { this.scriptType = scriptType; }
        public ScriptConfig getContent() { return content; }
        public void setContent(ScriptConfig content) { this.content = content; }
    }

    public static class SaveResponse {
        private boolean success;
        private String data;
        
        public SaveResponse() {}
        public SaveResponse(boolean success, String data) {
            this.success = success;
            this.data = data;
        }
        public boolean isSuccess() { return success; }
        public void setSuccess(boolean success) { this.success = success; }
        public String getData() { return data; }
        public void setData(String data) { this.data = data; }
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
}
