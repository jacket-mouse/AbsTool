package cn.edu.sdu.software.service.impl

import cn.edu.sdu.software.mapper.ActionMappingMapper
import cn.edu.sdu.software.model.ActionMapping
import cn.edu.sdu.software.service.ActionMappingService
import com.baomidou.mybatisplus.core.conditions.query.QueryWrapper
import com.baomidou.mybatisplus.extension.service.impl.ServiceImpl
import org.springframework.stereotype.Service

@Service
class ActionMappingServiceImpl : ServiceImpl<ActionMappingMapper, ActionMapping>(), ActionMappingService {

    // Simple cache definition (can be replaced by Redis later)
    private val mappingCache = mutableMapOf<String, String>()

    override fun getMapping(nodeType: String, framework: String): String? {
        val cacheKey = "map_\${nodeType}_\${framework}"
        if (mappingCache.containsKey(cacheKey)) {
            return mappingCache[cacheKey]
        }
        val wrapper = QueryWrapper<ActionMapping>()
            .eq("node_type", nodeType)
            .eq("target_framework", framework)
        val entity = getOne(wrapper)
        return if (entity != null) {
            mappingCache[cacheKey] = entity.templateCode
            entity.templateCode
        } else {
            null
        }
    }
}
