package cn.edu.sdu.software.engine

import cn.edu.sdu.software.model.ScriptConfig
import cn.edu.sdu.software.service.ActionMappingService
import org.springframework.stereotype.Service

@Service
class XmlScriptGenerator(
    private val actionMappingService: ActionMappingService
) {

    /**
     * 核心入口：将配置对象转换为 XML 代码字符串 (UiAutomator Testcase Format)
     */
    fun generate(config: ScriptConfig): String {
        // 1. 构建抽象语法树(AST)，执行校验
        val parser = AbsScriptParser()
        val astSequenceNode = parser.parse(config)

        // 2. 传入 Visitor 并带入 MappingService 支持数据库动态映射
        val xmlVisitor = XmlAstVisitor(actionMappingService)
        astSequenceNode.accept(xmlVisitor)

        return xmlVisitor.getResult()
    }
}
