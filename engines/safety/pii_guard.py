"""
PII Guard – kontrola a filtrování citlivých údajů ve výstupech.

TODO:
- definovat přesné kategorie PII
- implementovat jednoduché kontroly (regex / heuristiky)
- napojení na risk_profiles a produktovou konfiguraci
"""

from ..shared_types import EngineInput, EngineOutput


def run(engine_input: EngineInput) -> EngineOutput:
    # TODO: skutečná kontrola PII
    return EngineOutput(
        name="pii_guard",
        payload={"status": "not_implemented"},
        notes=["PII guard skeleton – zde bude kontrola citlivých údajů."],
    )
