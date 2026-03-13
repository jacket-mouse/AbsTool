# routers/generator_router.py
from fastapi import APIRouter
from schemas.script_editor import ScriptConfig
from engine.python_script_generator import PythonScriptGenerator

router = APIRouter(prefix="/api/generator")

python_gen = PythonScriptGenerator()


@router.post("/python")
def generate_python(config: ScriptConfig):
    try:
        return python_gen.generate(config)
    except Exception as e:
        return f"# Generate Error: {e}"
