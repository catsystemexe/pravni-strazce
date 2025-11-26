from engines.core_legal.engine import run
from engines.shared_types import EngineInput


def test_core_legal_engine_skeleton_runs():
    out = run(EngineInput(context={"user_query": "Test dotaz"}))
    assert out.name == "core_legal_engine"
