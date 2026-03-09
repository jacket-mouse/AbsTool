package cn.edu.sdu.software.dto;

import java.util.List;

public class ScriptDto {

    public static class ScriptListRequest {
        private int page = 1;
        private int size = 10;
        private String keyword;
        private String type;
        public int getPage() { return page; }
        public void setPage(int page) { this.page = page; }
        public int getSize() { return size; }
        public void setSize(int size) { this.size = size; }
        public String getKeyword() { return keyword; }
        public void setKeyword(String keyword) { this.keyword = keyword; }
        public String getType() { return type; }
        public void setType(String type) { this.type = type; }
    }

    public static class ScriptListItem {
        private String scriptId;
        private String name;
        private String type;
        private String status;
        private String creator;
        private java.time.LocalDateTime createTime;
        private String updateTime;
        private String latestVersion;

        public String getScriptId() { return scriptId; }
        public void setScriptId(String scriptId) { this.scriptId = scriptId; }
        public String getName() { return name; }
        public void setName(String name) { this.name = name; }
        public String getType() { return type; }
        public void setType(String type) { this.type = type; }
        public String getStatus() { return status; }
        public void setStatus(String status) { this.status = status; }
        public String getCreator() { return creator; }
        public void setCreator(String creator) { this.creator = creator; }
        public java.time.LocalDateTime getCreateTime() { return createTime; }
        public void setCreateTime(java.time.LocalDateTime createTime) { this.createTime = createTime; }
        public String getUpdateTime() { return updateTime; }
        public void setUpdateTime(String updateTime) { this.updateTime = updateTime; }
        public String getLatestVersion() { return latestVersion; }
        public void setLatestVersion(String latestVersion) { this.latestVersion = latestVersion; }
    }

    public static class ScriptListResponse {
        private List<ScriptListItem> list;
        private long total;
        public ScriptListResponse() {}
        public ScriptListResponse(List<ScriptListItem> list, long total) {
            this.list = list;
            this.total = total;
        }
        public List<ScriptListItem> getList() { return list; }
        public void setList(List<ScriptListItem> list) { this.list = list; }
        public long getTotal() { return total; }
        public void setTotal(long total) { this.total = total; }
    }

    public static class DeleteResponse {
        private boolean success;
        private String message;
        public DeleteResponse(boolean success, String message) {
            this.success = success;
            this.message = message;
        }
        public boolean isSuccess() { return success; }
        public void setSuccess(boolean success) { this.success = success; }
        public String getMessage() { return message; }
        public void setMessage(String message) { this.message = message; }
    }

    public static class UpdateRequest {
        private String scriptId;
        private String name;
        private String type;
        
        public String getScriptId() { return scriptId; }
        public void setScriptId(String scriptId) { this.scriptId = scriptId; }
        public String getName() { return name; }
        public void setName(String name) { this.name = name; }
        public String getType() { return type; }
        public void setType(String type) { this.type = type; }
    }

    public static class UpdateResponse {
        private boolean success;
        private String message;
        
        public UpdateResponse() {}
        public UpdateResponse(boolean success, String message) {
            this.success = success;
            this.message = message;
        }
        public boolean isSuccess() { return success; }
        public void setSuccess(boolean success) { this.success = success; }
        public String getMessage() { return message; }
        public void setMessage(String message) { this.message = message; }
    }
}
