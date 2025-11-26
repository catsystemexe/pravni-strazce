"""
Legal safety layer – řízení rizikovosti, blokace nebezpečných odpovědí,
omezení kreativních závěrů u high-risk domén.

TODO:
- interpretace risk_profiles z config.yaml
- rozhodování, kdy odpověď zkrátit / varovat / odmítnout
"""

from ..shared_types import EngineInput, EngineOutput


def run(engine_input: EngineInput) -> EngineOutput:
    # TODO: skutečná logika safety layeru
    return EngineOutput(
        name="legal_safety_layer",
        payload={"decision": "allow", "notes": ["safety layer skeleton"]},
        notes=["legal_safety_layer not fully implemented yet"],
    )
