package cn.edu.sdu.software.controller;

import cn.edu.sdu.software.dto.ScriptEditorDto;
import cn.edu.sdu.software.service.ScriptService;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.web.bind.annotation.*;

@RestController
@RequestMapping("/api/script/editor")
public class ScriptEditorController {

    @Autowired
    private ScriptService scriptService;

    @PostMapping("/save")
    public ScriptEditorDto.SaveResponse save(@RequestBody ScriptEditorDto.SaveRequest request) {
        return scriptService.saveScript(request);
    }

    @PostMapping("/validate")
    public ScriptEditorDto.ValidateResponse validate(@RequestBody ScriptEditorDto.ValidateRequest request) {
        return scriptService.validateScript(request);
    }

    @PostMapping("/preview")
    public ScriptEditorDto.PreviewResponse preview(@RequestBody ScriptEditorDto.PreviewRequest request) {
        return scriptService.previewScript(request);
    }
    
    @GetMapping("/load/{scriptId}")
    public ScriptEditorDto.LoadResponse load(@PathVariable("scriptId") String scriptId) {
        return scriptService.loadScript(scriptId);
    }

    @GetMapping("/load/{scriptId}/{versionId}")
    public ScriptEditorDto.LoadResponse loadVersion(@PathVariable("scriptId") String scriptId, @PathVariable("versionId") String versionId) {
        return scriptService.loadScriptVersion(scriptId, versionId);
    }

    @GetMapping("/history/{scriptId}")
    public ScriptEditorDto.HistoryResponse getHistory(@PathVariable("scriptId") String scriptId) {
        return scriptService.getScriptHistory(scriptId);
    }
}
