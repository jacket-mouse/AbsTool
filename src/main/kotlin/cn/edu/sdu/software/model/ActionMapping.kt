package cn.edu.sdu.software.model

import com.baomidou.mybatisplus.annotation.IdType
import com.baomidou.mybatisplus.annotation.TableId
import com.baomidou.mybatisplus.annotation.TableName

@TableName("action_mapping")
data class ActionMapping(
    @TableId(type = IdType.AUTO)
    val id: Long? = null,
    val nodeType: String = "",
    val targetFramework: String = "",
    val templateCode: String = ""
)
