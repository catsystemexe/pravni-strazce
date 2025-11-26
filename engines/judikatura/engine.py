"""
Judikatura engine – vyhledávání a vkládání judikatury do výstupu.

TODO:
- definovat rozhraní pro napojení na externí zdroje (manuální / automatické)
- logika NONE_FOUND / CONFLICT / OK
- propojení s citation_policy
"""

from ..shared_types import EngineInput, EngineOutput


def run(engine_input: EngineInput) -> EngineOutput:
    # TODO: implementace skutečné logiky judikatury
    return EngineOutput(
        name="judikatura_engine",
        payload={
            "status": "NONE_FOUND",
            "cases": [],
            "note": "Judikatura engine skeleton – zde bude práce s judikaturou.",
        },
        notes=["judikatura_engine not fully implemented yet"],
    )
