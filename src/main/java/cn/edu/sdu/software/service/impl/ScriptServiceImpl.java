package cn.edu.sdu.software.service.impl;

import cn.edu.sdu.software.dto.ScriptEditorDto;
import cn.edu.sdu.software.entity.ScriptInfo;
import cn.edu.sdu.software.entity.ScriptVersion;
import cn.edu.sdu.software.mapper.ScriptInfoMapper;
import cn.edu.sdu.software.mapper.ScriptVersionMapper;
import cn.edu.sdu.software.model.Connection;
import cn.edu.sdu.software.model.ScriptConfig;
import cn.edu.sdu.software.model.ScriptNode;
import cn.edu.sdu.software.service.ScriptService;
import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import cn.edu.sdu.software.context.UserContext;
import java.time.LocalDateTime;
import java.util.ArrayList;
import java.util.List;
import java.util.UUID;

@Service
public class ScriptServiceImpl implements ScriptService {

    @Autowired
    private ScriptInfoMapper scriptInfoMapper;

    @Autowired
    private ScriptVersionMapper scriptVersionMapper;

    @Autowired
    private ObjectMapper objectMapper;

    @Override
    @Transactional
    public ScriptEditorDto.SaveResponse saveScript(ScriptEditorDto.SaveRequest request) {
        String scriptId = request.getScriptId();
        ScriptConfig content = request.getContent();
        // 获取当前登录用户
        String currentUser = UserContext.getUserId();

        ScriptInfo scriptInfo = scriptInfoMapper.selectById(scriptId);
        if (scriptInfo == null) {
            // 如果不存在则新建
            scriptInfo = new ScriptInfo();
            scriptInfo.setScriptId(scriptId);
            scriptInfo.setCreateTime(LocalDateTime.now());
            scriptInfo.setLatestVersion("V1.0");
            scriptInfo.setCreator(currentUser); // 设置创建人
            // scriptInfo.setName(); // TODO: 从 request 获取 name
            // 其他字段默认
        }

        // 计算新版本号
        String currentVersion = scriptInfo.getLatestVersion();
        if (currentVersion == null || currentVersion.isEmpty()) {
            currentVersion = "V1.0";
        }
        // 简单版本号递增逻辑，假设格式为 V1.0, V1.1 等，或者直接用 V2
        // 这里简化，直接解析数字部分
        String newVersion = incrementVersion(currentVersion);

        try {
            String contentJson = objectMapper.writeValueAsString(content);
            
            // 更新 ScriptInfo
            scriptInfo.setContent(contentJson);
            scriptInfo.setLatestVersion(newVersion);
            // scriptInfo.setUpdateTime(LocalDateTime.now()); // 如果有 updatesTime
            
            if (scriptInfoMapper.selectById(scriptId) == null) {
                scriptInfoMapper.insert(scriptInfo);
            } else {
                scriptInfoMapper.updateById(scriptInfo);
            }

            // 插入 ScriptVersion
            ScriptVersion scriptVersion = new ScriptVersion();
            scriptVersion.setVersionId(UUID.randomUUID().toString());
            scriptVersion.setScriptId(scriptId);
            scriptVersion.setVersion(newVersion);
            scriptVersion.setContent(contentJson);
            scriptVersion.setModifyTime(LocalDateTime.now());
            scriptVersion.setModifier(currentUser); // 设置修改人
            
            scriptVersionMapper.insert(scriptVersion);

            return new ScriptEditorDto.SaveResponse(true, newVersion);

        } catch (JsonProcessingException e) {
            e.printStackTrace();
            return new ScriptEditorDto.SaveResponse(false, currentVersion);
        }
    }

    private String incrementVersion(String version) {
        // 简单实现：V1 -> V2, V1.0 -> V1.1
        if (version.startsWith("V")) {
            try {
                int v = Integer.parseInt(version.substring(1));
                return "V" + (v + 1);
            } catch (NumberFormatException e) {
                // ignore
            }
        }
        return "V" + System.currentTimeMillis(); // Fallback
    }

    @Override
    public ScriptEditorDto.ValidateResponse validateScript(ScriptEditorDto.ValidateRequest request) {
        ScriptConfig content = request.getContent();
        List<String> errors = new ArrayList<>();

        if (content == null) {
            errors.add("脚本内容不能为空");
            return new ScriptEditorDto.ValidateResponse(false, errors);
        }

        if (content.getNodes() == null || content.getNodes().isEmpty()) {
            errors.add("脚本必须包含至少一个节点");
        }

        // 检查是否有 Start 节点? 假设 Start 节点不是必须的类型，或者检查连通性
        // 这里做简单检查
        for (ScriptNode node : content.getNodes()) {
            if (node.getType() == null) {
                errors.add("节点 " + node.getId() + " 类型缺失");
            }
        }

        return new ScriptEditorDto.ValidateResponse(errors.isEmpty(), errors);
    }

    @Override
    public ScriptEditorDto.PreviewResponse previewScript(ScriptEditorDto.PreviewRequest request) {
        ScriptConfig content = request.getContent();
        if (content == null || content.getNodes() == null) {
             return new ScriptEditorDto.PreviewResponse("");
        }

        StringBuilder mermaid = new StringBuilder();
        mermaid.append("graph TD;\n");

        // 添加节点
        for (ScriptNode node : content.getNodes()) {
            // 处理节点名称，防止特殊字符
            String label = node.getType() != null ? node.getType() : "Node";
            // 如果有更友好的名称可以替换
            String safeId = node.getId().replace("-", "_"); // Mermaid ID 不支持 -
            mermaid.append("    ").append(safeId).append("[\"").append(label).append("\"]\n");
        }

        // 添加连线
        if (content.getConnections() != null) {
            for (Connection conn : content.getConnections()) {
                String from = conn.getFrom().replace("-", "_");
                String to = conn.getTo().replace("-", "_");
                mermaid.append("    ").append(from).append(" --> ").append(to).append("\n");
            }
        }

        return new ScriptEditorDto.PreviewResponse(mermaid.toString());
    }
}
