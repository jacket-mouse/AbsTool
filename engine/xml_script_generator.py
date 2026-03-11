# engine/xml_script_generator.py
from schemas.script_editor import ScriptConfig


class XmlScriptGenerator:

    def generate(self, config: ScriptConfig) -> str:
        return "<!-- XML Generator (Stub) -->\n<xml></xml>"
