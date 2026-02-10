package cn.edu.sdu.software.dto

import cn.edu.sdu.software.model.ScriptConfig

class ScriptEditorDto {

    data class SaveRequest(
        var scriptId: String = "",
        var content: ScriptConfig? = null
    )

    data class SaveResponse(
        var success: Boolean = false,
        var version: String = ""
    )

    data class ValidateRequest(
        var content: ScriptConfig? = null
    )

    data class ValidateResponse(
        var valid: Boolean = false,
        var errors: List<String> = emptyList()
    )

    data class PreviewRequest(
        var content: ScriptConfig? = null
    )

    data class PreviewResponse(
        var mermaidCode: String = ""
    )
}
