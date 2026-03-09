package cn.edu.sdu.software.service;

import cn.edu.sdu.software.dto.ScriptEditorDto;
import cn.edu.sdu.software.model.ScriptConfig;

/**
 * 脚本相关业务逻辑接口
 */
public interface ScriptService {

    /**
     * 保存脚本内容
     * @param request 保存请求包含 scriptId 和 content
     * @return 保存结果包含 success 和 version
     */
    ScriptEditorDto.SaveResponse saveScript(ScriptEditorDto.SaveRequest request);

    /**
     * 校验脚本合法性
     * @param request 校验请求包含 content
     * @return 校验结果包含 valid 和 errors
     */
    ScriptEditorDto.ValidateResponse validateScript(ScriptEditorDto.ValidateRequest request);

    /**
     * 生成脚本预览流程图
     * @param request 预览请求包含 content
     * @return 预览结果包含 mermaidCode
     */
    ScriptEditorDto.PreviewResponse previewScript(ScriptEditorDto.PreviewRequest request);

    ScriptEditorDto.LoadResponse loadScript(String scriptId);
    
    ScriptEditorDto.LoadResponse loadScriptVersion(String scriptId, String versionId);

    ScriptEditorDto.HistoryResponse getScriptHistory(String scriptId);
    
    /**
     * 获取脚本列表（分页）
     * @param request 查询条件
     * @return 列表结果
     */
    cn.edu.sdu.software.dto.ScriptDto.ScriptListResponse getScriptList(cn.edu.sdu.software.dto.ScriptDto.ScriptListRequest request);

    /**
     * 删除脚本
     * @param scriptId 脚本ID
     * @return 删除结果
     */
    cn.edu.sdu.software.dto.ScriptDto.DeleteResponse deleteScript(String scriptId);

    /**
     * 更新脚本信息
     * @param request 更新请求包括 scriptId, name, type
     * @return 更新结果
     */
    cn.edu.sdu.software.dto.ScriptDto.UpdateResponse updateScript(cn.edu.sdu.software.dto.ScriptDto.UpdateRequest request);
}
