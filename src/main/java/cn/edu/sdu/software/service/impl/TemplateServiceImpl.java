package cn.edu.sdu.software.service.impl;

import cn.edu.sdu.software.dto.TemplateDto;
import cn.edu.sdu.software.entity.ScriptTemplate;
import cn.edu.sdu.software.entity.ScriptTemplateRel;
import cn.edu.sdu.software.mapper.ScriptTemplateMapper;
import cn.edu.sdu.software.mapper.ScriptTemplateRelMapper;
import cn.edu.sdu.software.service.TemplateService;
import com.baomidou.mybatisplus.core.conditions.query.QueryWrapper;
import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import org.springframework.beans.BeanUtils;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.util.StringUtils;

import java.time.LocalDateTime;
import java.util.List;
import java.util.UUID;
import java.util.stream.Collectors;

@Service
public class TemplateServiceImpl implements TemplateService {

    @Autowired
    private ScriptTemplateMapper templateMapper;

    @Autowired
    private ScriptTemplateRelMapper templateRelMapper;

    @Autowired
    private cn.edu.sdu.software.service.ScriptService scriptService;

    @Autowired
    private cn.edu.sdu.software.engine.PythonScriptGenerator pythonScriptGenerator;

    @Override
    public Page<TemplateDto> listTemplates(int pageNum, int pageSize, String keyword) {
        Page<ScriptTemplate> page = new Page<>(pageNum, pageSize);
        QueryWrapper<ScriptTemplate> queryWrapper = new QueryWrapper<>();
        if (StringUtils.hasText(keyword)) {
            queryWrapper.like("name", keyword);
        }
        queryWrapper.orderByDesc("create_time");
        templateMapper.selectPage(page, queryWrapper);

        Page<TemplateDto> result = new Page<>(pageNum, pageSize, page.getTotal());
        result.setRecords(page.getRecords().stream().map(this::convertToDto).collect(Collectors.toList()));
        return result;
    }

    @Override
    @Transactional(rollbackFor = Exception.class)
    public void saveTemplate(TemplateDto dto, String userId) {
        boolean isNew = !StringUtils.hasText(dto.getTemplateId());
        ScriptTemplate template;
        
        if (isNew) {
            template = new ScriptTemplate();
            template.setTemplateId(UUID.randomUUID().toString().replace("-", ""));
            template.setCreateTime(LocalDateTime.now());
            template.setCreator(userId);
            dto.setTemplateId(template.getTemplateId());
        } else {
            template = templateMapper.selectById(dto.getTemplateId());
            if (template == null) {
                throw new RuntimeException("Template not found");
            }
        }
        
        template.setName(dto.getName());
        template.setDescription(dto.getDescription());
        
        if (isNew) {
            templateMapper.insert(template);
        } else {
            templateMapper.updateById(template);
            // Delete old relationships
            QueryWrapper<ScriptTemplateRel> queryWrapper = new QueryWrapper<>();
            queryWrapper.eq("template_id", template.getTemplateId());
            templateRelMapper.delete(queryWrapper);
        }
        
        // Save new relationships
        if (dto.getScripts() != null) {
            for (int i = 0; i < dto.getScripts().size(); i++) {
                TemplateDto.TemplateScriptDto relDto = dto.getScripts().get(i);
                ScriptTemplateRel rel = new ScriptTemplateRel();
                rel.setTemplateId(template.getTemplateId());
                rel.setScriptId(relDto.getScriptId());
                rel.setSortOrder(relDto.getSortOrder() != null ? relDto.getSortOrder() : i + 1);
                rel.setIsDefault(relDto.getIsDefault() != null ? relDto.getIsDefault() : 0);
                rel.setCreateTime(LocalDateTime.now());
                templateRelMapper.insert(rel);
            }
        }
    }

    @Override
    @Transactional(rollbackFor = Exception.class)
    public void deleteTemplate(String templateId) {
        templateMapper.deleteById(templateId);
        QueryWrapper<ScriptTemplateRel> queryWrapper = new QueryWrapper<>();
        queryWrapper.eq("template_id", templateId);
        templateRelMapper.delete(queryWrapper);
    }

    @Override
    public TemplateDto getTemplateDetail(String templateId) {
        ScriptTemplate template = templateMapper.selectById(templateId);
        if (template == null) {
            throw new RuntimeException("Template not found");
        }
        TemplateDto dto = convertToDto(template);
        
        QueryWrapper<ScriptTemplateRel> queryWrapper = new QueryWrapper<>();
        queryWrapper.eq("template_id", templateId);
        queryWrapper.orderByAsc("sort_order");
        List<ScriptTemplateRel> rels = templateRelMapper.selectList(queryWrapper);
        
        List<TemplateDto.TemplateScriptDto> scripts = rels.stream().map(rel -> {
            TemplateDto.TemplateScriptDto relDto = new TemplateDto.TemplateScriptDto();
            relDto.setScriptId(rel.getScriptId());
            relDto.setSortOrder(rel.getSortOrder());
            relDto.setIsDefault(rel.getIsDefault());
            return relDto;
        }).collect(Collectors.toList());
        
        dto.setScripts(scripts);
        return dto;
    }
    
    private TemplateDto convertToDto(ScriptTemplate template) {
        TemplateDto dto = new TemplateDto();
        BeanUtils.copyProperties(template, dto);
        return dto;
    }

    @Override
    public String generatePythonForTemplate(String templateId) throws Exception {
        TemplateDto detail = getTemplateDetail(templateId);
        if (detail == null || detail.getScripts() == null || detail.getScripts().isEmpty()) {
            throw new RuntimeException("Template is empty or not found");
        }

        List<cn.edu.sdu.software.model.ScriptNode> mergedNodes = new java.util.ArrayList<>();
        List<cn.edu.sdu.software.model.Connection> mergedConnections = new java.util.ArrayList<>();

        // Keep track of the previous script's end nodes (nodes with no outgoing connections)
        List<String> prevEndNodes = new java.util.ArrayList<>();

        for (TemplateDto.TemplateScriptDto scriptDto : detail.getScripts()) {
            String scriptId = scriptDto.getScriptId();
            cn.edu.sdu.software.dto.ScriptEditorDto.LoadResponse loadRes = scriptService.loadScript(scriptId);
            if (loadRes == null || loadRes.getContent() == null) {
                continue;
            }
            cn.edu.sdu.software.model.ScriptConfig config = loadRes.getContent();
            List<cn.edu.sdu.software.model.ScriptNode> nodes = config.getNodes();
            List<cn.edu.sdu.software.model.Connection> conns = config.getConnections();
            
            if (nodes == null || nodes.isEmpty()) continue;

            // Compute in-degree and out-degree for this script
            java.util.Map<String, Integer> inDegree = new java.util.HashMap<>();
            java.util.Map<String, Integer> outDegree = new java.util.HashMap<>();
            for (cn.edu.sdu.software.model.ScriptNode n : nodes) {
                inDegree.put(n.getId(), 0);
                outDegree.put(n.getId(), 0);
            }
            if (conns != null) {
                for (cn.edu.sdu.software.model.Connection c : conns) {
                    outDegree.put(c.getFrom(), outDegree.getOrDefault(c.getFrom(), 0) + 1);
                    inDegree.put(c.getTo(), inDegree.getOrDefault(c.getTo(), 0) + 1);
                }
            }

            // Find start nodes of this script
            List<String> currentStartNodes = new java.util.ArrayList<>();
            for (cn.edu.sdu.software.model.ScriptNode n : nodes) {
                if (inDegree.getOrDefault(n.getId(), 0) == 0) {
                    currentStartNodes.add(scriptId + "_" + n.getId());
                }
            }
            if (currentStartNodes.isEmpty()) {
                currentStartNodes.add(scriptId + "_" + nodes.get(0).getId());
            }

            // Link prevEndNodes to currentStartNodes
            if (!prevEndNodes.isEmpty()) {
                for (String prevEnd : prevEndNodes) {
                    for (String currStart : currentStartNodes) {
                        cn.edu.sdu.software.model.Connection link = new cn.edu.sdu.software.model.Connection();
                        link.setFrom(prevEnd);
                        link.setTo(currStart);
                        mergedConnections.add(link);
                    }
                }
            }

            // Prefix node IDs
            List<String> currentEndNodes = new java.util.ArrayList<>();
            for (cn.edu.sdu.software.model.ScriptNode n : nodes) {
                String oldId = n.getId();
                n.setId(scriptId + "_" + oldId);
                mergedNodes.add(n);
                if (outDegree.getOrDefault(oldId, 0) == 0) {
                    currentEndNodes.add(n.getId());
                }
            }

            // Prefix connection IDs
            if (conns != null) {
                for (cn.edu.sdu.software.model.Connection c : conns) {
                    c.setFrom(scriptId + "_" + c.getFrom());
                    c.setTo(scriptId + "_" + c.getTo());
                    mergedConnections.add(c);
                }
            }

            prevEndNodes = currentEndNodes;
        }

        cn.edu.sdu.software.model.ScriptConfig mergedConfig = new cn.edu.sdu.software.model.ScriptConfig(mergedNodes, mergedConnections);
        return pythonScriptGenerator.generate(mergedConfig);
    }
}
