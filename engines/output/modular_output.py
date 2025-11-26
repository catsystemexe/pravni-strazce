"""
Modular output system – skládá finální odpověď z jednotlivých bloků.

TODO:
- načíst config (blocks_order, templates)
- složit text z výstupů jednotlivých engines
"""

from ..shared_types import EngineInput, EngineOutput


def run(engine_input: EngineInput) -> EngineOutput:
    # TODO: implementace skládání modulárního výstupu
    return EngineOutput(
        name="modular_output_system",
        payload={
            "rendered_text": "Modular output skeleton – zde se složí finální odpověď.",
        },
        notes=["modular_output_system not fully implemented yet"],
    )
