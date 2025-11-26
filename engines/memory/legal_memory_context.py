"""
Legal memory context engine – rozhoduje, co ukládat z dialogu a co ignorovat.

TODO:
- definovat jednoduchý interface pro memory store (zatím klidně in-memory)
- filtrování podle store_categories / ignore_categories
"""

from ..shared_types import EngineInput, EngineOutput


def run(engine_input: EngineInput) -> EngineOutput:
    # TODO: implementace ukládání a filtrace paměti
    return EngineOutput(
        name="legal_memory_context_engine",
        payload={"stored_items": [], "ignored_items": []},
        notes=["legal_memory_context_engine skeleton – zatím bez reálné paměti."],
    )
