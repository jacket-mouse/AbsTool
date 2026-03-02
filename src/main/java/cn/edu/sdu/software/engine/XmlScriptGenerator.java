package cn.edu.sdu.software.engine;

import cn.edu.sdu.software.model.ScriptConfig;
import org.springframework.stereotype.Service;

@Service
public class XmlScriptGenerator {

    public String generate(ScriptConfig config) {
        return "<!-- XML Generator (Stub) -->\n<xml></xml>";
    }
}
