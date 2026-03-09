package cn.edu.sdu.software.model;
import com.fasterxml.jackson.annotation.JsonProperty;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.util.Map;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
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
}
