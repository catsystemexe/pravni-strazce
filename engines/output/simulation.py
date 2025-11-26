"""
Procedural outcome simulator – generuje scénáře vývoje řízení.

TODO:
- pracovat s rizikem a mírou znalosti faktů
- odlišit obecné scénáře vs. případově specifické
"""

from ..shared_types import EngineInput, EngineOutput


def run(engine_input: EngineInput) -> EngineOutput:
    # TODO: simulace procesního vývoje
    return EngineOutput(
        name="procedural_outcome_simulator",
        payload={
            "scenarios": [],
            "note": "Simulator skeleton – zde budou obecné i konkrétní scénáře.",
        },
        notes=["procedural_outcome_simulator not fully implemented yet"],
    )
