package cn.edu.sdu.software.dto

import java.time.LocalDateTime

class ScriptDto {
    data class ScriptListItem(
        var scriptId: String = "",
        var name: String = "",
        var type: String = "",
        var status: String = "",
        var creator: String = "",
        var createTime: LocalDateTime? = null,
        var latestVersion: String = ""
    )
    
    data class ScriptListRequest(
        var page: Long = 1,
        var size: Long = 10,
        var keyword: String? = null,
        var status: String? = null // 可选：按状态过滤
    )
    
    data class ScriptListResponse(
        var list: List<ScriptListItem> = emptyList(),
        var total: Long = 0
    )
    
    data class DeleteRequest(
        var scriptId: String = ""
    )
    
     data class DeleteResponse(
        var success: Boolean = false,
        var message: String? = null
    )
}
