"""
Tenká API vrstva (např. FastAPI/Flask) pro volání runtime orchestrátoru.

Zatím jen skeleton – můžeš sem později doplnit:
- endpoint /legal/advice
- endpoint /legal/document
- mapování requestu na CaseContext
"""

def health_check() -> dict:
    return {"status": "ok", "component": "e-advokat-core"}
