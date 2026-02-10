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
}
