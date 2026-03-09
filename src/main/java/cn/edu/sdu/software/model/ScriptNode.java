package cn.edu.sdu.software.model;
import com.fasterxml.jackson.annotation.JsonProperty;
import java.util.Map;

public class ScriptNode {
    private String id;
    private String type;
    private String title;
    private String desc;
    private String loc;
    @JsonProperty("isGroup")
    private boolean isGroup;
    private String groupKey;
    private Map<String, Object> properties;

    public String getId() { return id; }
    public void setId(String id) { this.id = id; }
    public String getType() { return type; }
    public void setType(String type) { this.type = type; }
    public String getTitle() { return title; }
    public void setTitle(String title) { this.title = title; }
    public String getDesc() { return desc; }
    public void setDesc(String desc) { this.desc = desc; }
    public String getLoc() { return loc; }
    public void setLoc(String loc) { this.loc = loc; }

    @JsonProperty("isGroup")
    public boolean isGroup() { return isGroup; }
    @JsonProperty("isGroup")
    public void setIsGroup(boolean isGroup) { this.isGroup = isGroup; }

    public String getGroupKey() { return groupKey; }
    public void setGroupKey(String groupKey) { this.groupKey = groupKey; }
    public Map<String, Object> getProperties() { return properties; }
    public void setProperties(Map<String, Object> properties) { this.properties = properties; }
}
