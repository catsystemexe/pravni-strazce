"""
Testy pro Core Legal Engine

Cíl:
- ověřit, že engine běží i bez LLM (fallback skeleton)
- ověřit základní strukturu IRAC výstupu
- povolit jak plnou LLM verzi, tak skeleton verzi
  (podle toho, zda je dostupný OPENAI_API_KEY)
"""

from engines.core_legal.engine import run
from engines.shared_types import EngineInput


def _run_engine(query: str = "Testovací dotaz"):
    """Pomocný wrapper pro spuštění enginu."""
    return run(
        EngineInput(
            context={
                "case": {
                    "user_query": query,
                }
            }
        )
    )


def test_core_legal_engine_runs():
    """
    Engine by měl běžet bez ohledu na to,
    zda je dostupný LLM klient (API klíč).
    """
    out = _run_engine("Jednoduchý testovací dotaz.")
    assert hasattr(out, "name")
    assert hasattr(out, "payload")
    assert hasattr(out, "notes")
    assert isinstance(out.notes, list)


def test_core_legal_engine_name_allows_llm_and_skeleton():
    """
    V dev/replit prostředí typicky neběží LLM (chybí API key),
    takže očekáváme fallback `core_legal_engine_skeleton`.

    Pokud ale někdo nastaví OPENAI_API_KEY a LLM poběží,
    jméno může být `core_legal_engine_v1`.
    """
    out = _run_engine("Test dotaz na notářku.")
    assert out.name in ("core_legal_engine_v1", "core_legal_engine_skeleton")


def test_core_legal_engine_payload_contains_irac_sections():
    """
    Výstup by měl obsahovat základní IRAC sekce
    (ať už jsou naplněné LLM, nebo skeleton textem).
    """
    out = _run_engine("Test IRAC struktury.")
    payload = out.payload

    # LLM verze má domain/facts/issues/..., skeleton má issues/rules/analysis/...
    # Ověříme minimálně přítomnost klíčových sekcí.
    assert isinstance(payload, dict)

    # minimálně jedna z IRAC sekcí musí existovat
    required_any = [
        "issues",
        "rules",
        "analysis",
        "conclusion",
    ]
    assert any(key in payload for key in required_any)


def test_core_legal_engine_skeleton_has_llm_error_if_no_llm():
    """
    Pokud neběží LLM klient (typicky v Replitu bez API klíče),
    fallback skeleton by měl připojit informaci o chybě LLM.
    """
    out = _run_engine("Dotaz bez LLM.")
    if out.name == "core_legal_engine_skeleton":
        # v skeleton režimu očekáváme v payload klíč llm_error
        assert "llm_error" in out.payload