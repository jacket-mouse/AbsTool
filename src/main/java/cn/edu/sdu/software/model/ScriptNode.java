package cn.edu.sdu.software.model;
import java.util.Map;

public class ScriptNode {
    private String id;
    private String type;
    private String title;
    private String desc;
    private String loc;
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
    public Map<String, Object> getProperties() { return properties; }
    public void setProperties(Map<String, Object> properties) { this.properties = properties; }
}
