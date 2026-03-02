package cn.edu.sdu.software.model;

import java.util.List;
import java.util.ArrayList;

public class ScriptConfig {
    private List<ScriptNode> nodes = new ArrayList<>();
    private List<Connection> connections = new ArrayList<>();

    public ScriptConfig() {}
    public ScriptConfig(List<ScriptNode> nodes, List<Connection> connections) {
        this.nodes = nodes;
        this.connections = connections;
    }
    public List<ScriptNode> getNodes() { return nodes; }
    public void setNodes(List<ScriptNode> nodes) { this.nodes = nodes; }
    public List<Connection> getConnections() { return connections; }
    public void setConnections(List<Connection> connections) { this.connections = connections; }
}
