"""
Testy pro runtime orchestrátor.

Cíl:
- ověřit, že run_pipeline vrací konzistentní strukturu
- ověřit, že finální odpověď obsahuje hlavní sekce
- ověřit, že se v odpovědi objeví informace o riziku
"""

from runtime.orchestrator import run_pipeline


def test_run_pipeline_returns_expected_structure():
    q = "Notářka mi odmítá umožnit nahlédnout do spisu."
    res = run_pipeline(q)

    assert isinstance(res, dict)
    assert "final_answer" in res
    assert "core_legal" in res
    assert "risk" in res
    assert "judikatura" in res

    assert isinstance(res["final_answer"], str)


def test_final_answer_contains_main_sections():
    res = run_pipeline("Testovací dotaz.")
    text = res["final_answer"]

    assert "# 🧩 Shrnutí" in text
    assert "## ⚖️ Právní analýza" in text
    assert "## 📚 Judikatura" in text
    assert "## ⚠️ Rizika a naléhavost" in text
    assert "## 🧭 Doporučený další postup" in text


def test_final_answer_includes_risk_level():
    """
    Pro dotaz s jasnými riziky by se měla v odpovědi objevit
    informace o úrovni rizika.
    """
    q = "Policie mi sdělila obvinění, běží lhůta pro podání stížnosti a jde o nezletilé dítě."
    res = run_pipeline(q)
    text = res["final_answer"]

    assert "Úroveň rizika" in text