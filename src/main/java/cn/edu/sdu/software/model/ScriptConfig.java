package cn.edu.sdu.software.model;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.util.List;
import java.util.ArrayList;

@Data
@Builder
@AllArgsConstructor
@NoArgsConstructor
public class ScriptConfig {
    private List<ScriptNode> nodes = new ArrayList<>();
    private List<Connection> connections = new ArrayList<>();
}
