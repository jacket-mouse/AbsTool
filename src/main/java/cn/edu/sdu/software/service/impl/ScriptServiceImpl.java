package cn.edu.sdu.software.service.impl;

import cn.edu.sdu.software.dto.ScriptEditorDto;
import cn.edu.sdu.software.entity.ScriptInfo;
import cn.edu.sdu.software.entity.ScriptVersion;
import cn.edu.sdu.software.mapper.ScriptInfoMapper;
import cn.edu.sdu.software.mapper.ScriptVersionMapper;
import cn.edu.sdu.software.model.Connection;
import cn.edu.sdu.software.model.ScriptConfig;
import cn.edu.sdu.software.model.ScriptNode;
import cn.edu.sdu.software.service.MinioFileService;
import cn.edu.sdu.software.service.ScriptService;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import cn.edu.sdu.software.context.UserContext;
import cn.edu.sdu.software.dto.ScriptDto;
import com.baomidou.mybatisplus.core.conditions.query.QueryWrapper;
import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import org.springframework.util.StringUtils;

import java.time.LocalDateTime;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.stream.Collectors;
import java.util.Map;

@Service
public class ScriptServiceImpl implements ScriptService {

    @Autowired
    private ScriptInfoMapper scriptInfoMapper;

    @Autowired
    private ScriptVersionMapper scriptVersionMapper;

    @Autowired
    private ObjectMapper objectMapper;

    @Autowired
    private MinioFileService minioFileService;

    @Autowired
    private cn.edu.sdu.software.engine.PythonScriptGenerator pythonScriptGenerator;

    @Autowired
    private cn.edu.sdu.software.engine.XmlScriptGenerator xmlScriptGenerator;

    @Override
    @Transactional
    public ScriptEditorDto.SaveResponse saveScript(ScriptEditorDto.SaveRequest request) {
        // 获取信息
        String scriptId = request.getScriptId();
        ScriptConfig content = request.getContent();
        String currentUser = UserContext.getUserId();

        boolean isNew = false;
        ScriptInfo scriptInfo = null;

        if (scriptId != null && !scriptId.isEmpty()) {
            scriptInfo = scriptInfoMapper.selectById(scriptId);
        }

        if (scriptInfo == null) {
            isNew = true;
            scriptInfo = new ScriptInfo();
            // 自增 ScriptId
            List<ScriptInfo> allScripts = scriptInfoMapper.selectList(new QueryWrapper<>());
            int maxId = 0;
            for (ScriptInfo info : allScripts) {
                try {
                    int id = Integer.parseInt(info.getScriptId());
                    if (id > maxId) maxId = id;
                } catch (NumberFormatException ignored) {}
            }
            scriptId = String.valueOf(maxId + 1);
            
            scriptInfo.setScriptId(scriptId);
            scriptInfo.setCreateTime(LocalDateTime.now());
            scriptInfo.setLatestVersion("1");
            scriptInfo.setCreator(currentUser);
            String providedName = request.getScriptName();
            scriptInfo.setName(StringUtils.hasText(providedName) ? providedName : "脚本-" + scriptId);
            scriptInfo.setType("GENERAL"); // 默认类型
            scriptInfo.setStatus("ENABLED"); // 默认状态
        }

        // 计算新版本号：以数字递增
        String currentVersion = scriptInfo.getLatestVersion();
        if (currentVersion == null || currentVersion.isEmpty() || currentVersion.startsWith("V")) {
            currentVersion = "0"; // fallback if old version format
        }
        
        String newVersionStr = "1";
        try {
            int v = Integer.parseInt(currentVersion);
            newVersionStr = String.valueOf(v + 1);
        } catch (NumberFormatException ignored) {}
        
        if (isNew) {
            newVersionStr = "1";
        }

//        // 节点 ID 重写为 脚本ID-节点编号，同步更新边和 groupKey
//        if (content != null && content.getNodes() != null) {
//            // 第一步：构建 oldId -> newId 映射
//            Map<String, String> idRemap = new HashMap<>();
//            for (ScriptNode node : content.getNodes()) {
//                String oldId = node.getId();
//                if (oldId == null || oldId.isEmpty()) continue;
//                if (oldId.contains("-")) {
//                    String[] parts = oldId.split("-");
//                    String newId = parts[parts.length - 1]; // 只保留最后的数字编号部分
//                    if (!oldId.equals(newId)) {
//                        idRemap.put(oldId, newId);
//                    }
//                }
//            }
//            // 第二步：应用映射到节点 ID、连线 from/to、以及 groupKey
//            for (ScriptNode node : content.getNodes()) {
//                String oldId = node.getId();
//                if (idRemap.containsKey(oldId)) {
//                    node.setId(idRemap.get(oldId));
//                }
//                // 同步更新 groupKey（子节点所属的 Group ID 也需要重写）
//                if (node.getGroupKey() != null && idRemap.containsKey(node.getGroupKey())) {
//                    node.setGroupKey(idRemap.get(node.getGroupKey()));
//                }
//            }
//            if (content.getConnections() != null) {
//                for (Connection conn : content.getConnections()) {
//                    if (conn.getFrom() != null && idRemap.containsKey(conn.getFrom())) {
//                        conn.setFrom(idRemap.get(conn.getFrom()));
//                    }
//                    if (conn.getTo() != null && idRemap.containsKey(conn.getTo())) {
//                        conn.setTo(idRemap.get(conn.getTo()));
//                    }
//                }
//            }
//        }

        try {
            String contentJson = objectMapper.writeValueAsString(content);
            
            // 1. 上传配置 JSON 到 MinIO
            String fileName = "scripts/" + scriptId + "/" + newVersionStr + ".json";
            minioFileService.uploadFile(fileName, contentJson, "application/json");

            // 2. 自动生成并上传 Python 脚本
            try {
                String pythonCode = pythonScriptGenerator.generate(content);
                String pyFileName = "scripts/" + scriptId + "/" + newVersionStr + ".py";
                minioFileService.uploadFile(pyFileName, pythonCode, "text/x-python");
                System.out.println("成功生成并存储 Python 脚本至: " + pyFileName);
            } catch (Exception pyErr) {
                System.err.println("自动生成 Python 脚本失败: " + pyErr.getMessage());
            }

            // 3. 自动生成并上传 XML 测试用例
            try {
                String xmlCode = xmlScriptGenerator.generate(content);
                String xmlFileName = "scripts/" + scriptId + "/" + newVersionStr + ".xml";
                minioFileService.uploadFile(xmlFileName, xmlCode, "application/xml");
                System.out.println("成功生成并存储 XML 脚本至: " + xmlFileName);
            } catch (Exception xmlErr) {
                System.err.println("自动生成 XML 脚本失败: " + xmlErr.getMessage());
            }

            // 更新 ScriptInfo，存储文件路径
            scriptInfo.setContent(fileName);
            scriptInfo.setLatestVersion(newVersionStr);
            
            String providedName = request.getScriptName();
            if (StringUtils.hasText(providedName)) {
                scriptInfo.setName(providedName);
            }
            
            if (isNew) {
                scriptInfoMapper.insert(scriptInfo);
            } else {
                scriptInfoMapper.updateById(scriptInfo);
            }

            // 插入 ScriptVersion
            ScriptVersion scriptVersion = new ScriptVersion();
            // Version ID 也使用自增：获取最大的 version_id (如果是数字)
            List<ScriptVersion> allVersions = scriptVersionMapper.selectList(new QueryWrapper<>());
            int maxVersionId = 0;
            for (ScriptVersion info : allVersions) {
                try {
                    int id = Integer.parseInt(info.getVersionId());
                    if (id > maxVersionId) maxVersionId = id;
                } catch (NumberFormatException ignored) {}
            }
            scriptVersion.setVersionId(String.valueOf(maxVersionId + 1));
            scriptVersion.setScriptId(scriptId);
            scriptVersion.setVersion(newVersionStr);
            scriptVersion.setContent(fileName); // 存储 JSON 文件路径
            scriptVersion.setModifyTime(LocalDateTime.now());
            scriptVersion.setModifier(currentUser); // 设置修改人
            scriptVersion.setChangeLog(request.getChangelog()); // 记录变更日志
            
            
            scriptVersionMapper.insert(scriptVersion);

            return new ScriptEditorDto.SaveResponse(true, scriptId, newVersionStr, "保存成功");

        } catch (Exception e) {
            e.printStackTrace();
            return new ScriptEditorDto.SaveResponse(false, scriptId, currentVersion, "Error: " + e.getMessage());
        }
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

    @Override
    public ScriptEditorDto.LoadResponse loadScript(String scriptId) {
        System.out.println("Loading script: " + scriptId);
        ScriptInfo info = scriptInfoMapper.selectById(scriptId);
        if (info == null) {
            System.out.println("ScriptInfo not found for: " + scriptId);
            return new ScriptEditorDto.LoadResponse("", null);
        }

        ScriptConfig config = null;
        try {
            // 获取最新版本
            QueryWrapper<ScriptVersion> query = new QueryWrapper<>();
            query.eq("script_id", scriptId);
            query.orderByDesc("modify_time");
            query.last("LIMIT 1");
            ScriptVersion latestVersion = scriptVersionMapper.selectOne(query);

            if (latestVersion != null) {
                System.out.println("Latest version found: " + latestVersion.getVersion() + ", content path: " + latestVersion.getContent());
                if (StringUtils.hasText(latestVersion.getContent())) {
                    String jsonContent = minioFileService.getFileContent(latestVersion.getContent());
                    if (StringUtils.hasText(jsonContent)) {
                        System.out.println("File content retrieved (len=" + jsonContent.length() + ")");
                        config = objectMapper.readValue(jsonContent, ScriptConfig.class);
                    } else {
                        System.out.println("File content is empty or null");
                    }
                } else {
                     System.out.println("Version content path is empty");
                }
            } else {
                System.out.println("No version records found for script: " + scriptId);
            }
        } catch (Exception e) {
            System.out.println("Error loading script: " + e.getMessage());
            e.printStackTrace();
        }

        // Self-Healing: If config is null (e.g. version missing or file missing), return empty config
        if (config == null) {
            System.out.println("Returning empty config for self-healing.");
            config = new ScriptConfig(new ArrayList<>(), new ArrayList<>());
        }

        return new ScriptEditorDto.LoadResponse(info.getName(), config);
    }

    @Override
    public ScriptEditorDto.LoadResponse loadScriptVersion(String scriptId, String versionId) {
        System.out.println("Loading script version: " + scriptId + " v=" + versionId);
        ScriptInfo info = scriptInfoMapper.selectById(scriptId);
        if (info == null) {
            return new ScriptEditorDto.LoadResponse("", null);
        }

        ScriptConfig config = null;
        try {
            QueryWrapper<ScriptVersion> query = new QueryWrapper<>();
            query.eq("script_id", scriptId);
            query.eq("version_id", versionId);
            ScriptVersion v = scriptVersionMapper.selectOne(query);

            if (v != null && StringUtils.hasText(v.getContent())) {
                String jsonContent = minioFileService.getFileContent(v.getContent());
                if (StringUtils.hasText(jsonContent)) {
                    config = objectMapper.readValue(jsonContent, ScriptConfig.class);
                }
            }
        } catch (Exception e) {
            e.printStackTrace();
        }

        if (config == null) {
            config = new ScriptConfig(new ArrayList<>(), new ArrayList<>());
        }
        return new ScriptEditorDto.LoadResponse(info.getName(), config);
    }

    @Override
    public ScriptEditorDto.HistoryResponse getScriptHistory(String scriptId) {
        QueryWrapper<ScriptVersion> query = new QueryWrapper<>();
        query.eq("script_id", scriptId);
        query.orderByDesc("modify_time");
        List<ScriptVersion> versions = scriptVersionMapper.selectList(query);
        
        List<ScriptEditorDto.HistoryVersionDto> list = new ArrayList<>();
        java.time.format.DateTimeFormatter formatter = java.time.format.DateTimeFormatter.ofPattern("yyyy-MM-dd HH:mm:ss");
        for (ScriptVersion v : versions) {
            String cTime = v.getModifyTime() != null ? v.getModifyTime().format(formatter) : "";
            // Simplified summary
            String summary = StringUtils.hasText(v.getChangeLog()) ? v.getChangeLog() : "无提要";
            list.add(new ScriptEditorDto.HistoryVersionDto(v.getVersionId(), v.getVersion(), cTime, summary));
        }
        return new ScriptEditorDto.HistoryResponse(list);
    }

    @Override
    public ScriptDto.ScriptListResponse getScriptList(ScriptDto.ScriptListRequest request) {
        Page<ScriptInfo> page = new Page<>(request.getPage(), request.getSize());
        QueryWrapper<ScriptInfo> query = new QueryWrapper<>();
        
        // 过滤当前用户的脚本，如果 UserContext 能取到
        String userId = UserContext.getUserId();
        if (StringUtils.hasText(userId)) {
            query.eq("creator", userId);
        }
        
        if (StringUtils.hasText(request.getKeyword())) {
            query.like("name", request.getKeyword());
        }
        
        if (StringUtils.hasText(request.getType())) {
            query.eq("type", request.getType());
        }
        
        // 默认按时间倒序
        query.orderByDesc("create_time");
        
        // 分页查询
        Page<ScriptInfo> result = scriptInfoMapper.selectPage(page, query);
        
        // 转换 entity -> dto
        List<ScriptDto.ScriptListItem> list = result.getRecords().stream().map(info -> {
            ScriptDto.ScriptListItem item = new ScriptDto.ScriptListItem();
            item.setScriptId(info.getScriptId());
            item.setName(info.getName());
            item.setType(info.getType());
            item.setStatus(info.getStatus());
            item.setCreator(info.getCreator());
            item.setCreateTime(info.getCreateTime());
            item.setLatestVersion(info.getLatestVersion());
            return item;
        }).collect(Collectors.toList());
        
        return new ScriptDto.ScriptListResponse(list, result.getTotal());
    }

    @Override
    @Transactional
    public ScriptDto.DeleteResponse deleteScript(String scriptId) {
        try {
            // 1. 删除关联的版本记录
            QueryWrapper<ScriptVersion> versionQuery = new QueryWrapper<>();
            versionQuery.eq("script_id", scriptId);
            scriptVersionMapper.delete(versionQuery);
            
            // 2. 删除脚本信息
            int rows = scriptInfoMapper.deleteById(scriptId);
            
            if (rows > 0) {
                return new ScriptDto.DeleteResponse(true, "删除成功");
            } else {
                return new ScriptDto.DeleteResponse(false, "脚本不存在或已删除");
            }
        } catch (Exception e) {
            e.printStackTrace();
            return new ScriptDto.DeleteResponse(false, "删除失败: " + e.getMessage());
        }
    }

    @Override
    @Transactional
    public ScriptDto.UpdateResponse updateScript(ScriptDto.UpdateRequest request) {
        try {
            ScriptInfo info = scriptInfoMapper.selectById(request.getScriptId());
            if (info != null) {
                if (StringUtils.hasText(request.getName())) {
                    info.setName(request.getName());
                }
                if (StringUtils.hasText(request.getType())) {
                    info.setType(request.getType());
                }
                scriptInfoMapper.updateById(info);
                return new ScriptDto.UpdateResponse(true, "更新成功");
            }
            return new ScriptDto.UpdateResponse(false, "脚本未找到");
        } catch (Exception e) {
            e.printStackTrace();
            return new ScriptDto.UpdateResponse(false, "更新失败: " + e.getMessage());
        }
    }
}
