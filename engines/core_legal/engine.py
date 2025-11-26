"""
Core legal engine – hlavní právní rozbor.

TODO:
- napojení na LLM
- využití config.yaml (domény, pravidla pro odvozování)
- generování strukturovaného právního rozboru (issues, rules, analysis, conclusion)
"""

from ..shared_types import EngineInput, EngineOutput


def run(engine_input: EngineInput) -> EngineOutput:
    # TODO: implementace skutečné logiky
    return EngineOutput(
        name="core_legal_engine",
        payload={
            "analysis": "core_legal_engine skeleton – zde bude hlavní právní rozbor.",
        },
        notes=["core_legal_engine not fully implemented yet"],
    )
