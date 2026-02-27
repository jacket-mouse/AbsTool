package cn.edu.sdu.software.service

import cn.edu.sdu.software.model.ActionMapping
import com.baomidou.mybatisplus.extension.service.IService

interface ActionMappingService : IService<ActionMapping> {
    fun getMapping(nodeType: String, framework: String): String?
}
