# tests/test_judikatura_engine.py

from engines.judikatura.engine import run
from engines.shared_types import EngineInput


def test_judikatura_none_found():
    out = run(EngineInput(context={"case": {"domain": "civil"}}))
    assert out.payload["status"] in ("NONE_FOUND", "ERROR")


def test_judikatura_conflict_detection():
    candidates = [
        {
            "id": "1",
            "court_level": "ns",
            "reference": "21 Cdo 1111/2020",
            "year": 2020,
            "legal_issue": "Náhrada škody",
            "holding_summary": "Přiznání nároku poškozenému.",
            "holding_direction": "pro_appellant",
            "relevance_score": 0.9,
            "source": "NS ČR",
        },
        {
            "id": "2",
            "court_level": "ns",
            "reference": "21 Cdo 2222/2021",
            "year": 2021,
            "legal_issue": "Náhrada škody",
            "holding_summary": "Zamítnutí nároku poškozeného.",
            "holding_direction": "pro_defendant",
            "relevance_score": 0.88,
            "source": "NS ČR",
        },
    ]

    out = run(
        EngineInput(
            context={
                "case": {"domain": "civil"},
                "debug_candidates": candidates,
            }
        )
    )
    assert out.payload["status"] == "CONFLICT"
