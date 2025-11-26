"""
Runtime orchestrátor – hlavní pipeline:

1. role_detection
2. intent_detection
3. domain & risk routing
4. spuštění core_legal_engine
5. judikatura + citace
6. safety vrstvy
7. složení výstupu přes modular_output

Zatím skeleton – konkrétní logiku budeš doplňovat postupně.
"""

from .context import CaseContext, EngineResult


def run_pipeline(user_query: str) -> dict:
    """
    Entry point pro core agenta (zatím bez reálného volání LLM).
    Vrací zatím jen stub strukturu, kterou můžeš postupně napojovat
    na jednotlivé engines.
    """
    ctx = CaseContext(user_query=user_query)

    # TODO: role_detection / intent_detection / domain_routing
    ctx.role = "client"
    ctx.intent = "legal_explanation"
    ctx.domain = "civil"
    ctx.risk_level = "medium"

    results: list[EngineResult] = []

    # TODO: call engines.core_legal, engines.judikatura, engines.safety, engines.output
    results.append(EngineResult(name="core_legal", data={"note": "not implemented yet"}))

    return {
        "context": ctx.__dict__,
        "engine_results": [r.__dict__ for r in results],
        "message": "Skeleton runtime – doplň logiku podle návrhu architektury."
    }
