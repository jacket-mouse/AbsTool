# routers/generator_router.py
from fastapi import APIRouter
from schemas.script_editor import ScriptConfig
from engine.python_script_generator import PythonScriptGenerator
from engine.xml_script_generator import XmlScriptGenerator

router = APIRouter(prefix="/api/generator")

python_gen = PythonScriptGenerator()
xml_gen = XmlScriptGenerator()


@router.post("/python")
def generate_python(config: ScriptConfig):
    try:
        return python_gen.generate(config)
    except Exception as e:
        return f"# Generate Error: {e}"


@router.post("/xml")
def generate_xml(config: ScriptConfig):
    try:
        return xml_gen.generate(config)
    except Exception as e:
        return f"<!-- Generate Error: {e} -->"
