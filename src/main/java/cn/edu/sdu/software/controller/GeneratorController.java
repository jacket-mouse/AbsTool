package cn.edu.sdu.software.controller;

import cn.edu.sdu.software.engine.PythonScriptGenerator; // 1. 导入 Kotlin 写的 Service
import cn.edu.sdu.software.model.ScriptConfig;           // 2. 导入 Kotlin 写的 Data Class
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.web.bind.annotation.*;

/**
 * 脚本生成接口 (Java 实现)
 */
@RestController
@RequestMapping("/api/generator")
public class GeneratorController {

    // 3. 像注入普通 Java Bean 一样注入 Kotlin Service
    @Autowired
    private PythonScriptGenerator scriptGenerator;

    /**
     * 接收前端 JSON，调用 Kotlin 引擎生成 Python 代码
     */
    @PostMapping("/python")
    public String generatePythonScript(@RequestBody ScriptConfig config) {
        // Spring Boot 的 Jackson 库会自动把 JSON 反序列化为 Kotlin 的 ScriptConfig 对象

        System.out.println("接收到脚本生成请求，节点数量: " + config.getNodes().size());

        // 4. 直接调用 Kotlin 的 generate 方法
        String pythonCode = scriptGenerator.generate(config);

        return pythonCode;
    }
}