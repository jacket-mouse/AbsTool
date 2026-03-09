package cn.edu.sdu.software.controller;

import cn.edu.sdu.software.dto.ScriptDto;
import cn.edu.sdu.software.service.ScriptService;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.web.bind.annotation.*;

@RestController
@RequestMapping("/api/script")
public class ScriptController {

    @Autowired
    private ScriptService scriptService;

    @PostMapping("/list")
    public ScriptDto.ScriptListResponse list(@RequestBody ScriptDto.ScriptListRequest request) {
        return scriptService.getScriptList(request);
    }
    
    @DeleteMapping("/delete/{scriptId}")
    public ScriptDto.DeleteResponse delete(@PathVariable("scriptId") String scriptId) {
        return scriptService.deleteScript(scriptId);
    }

    @PostMapping("/update")
    public ScriptDto.UpdateResponse update(@RequestBody ScriptDto.UpdateRequest request) {
        return scriptService.updateScript(request);
    }
}
