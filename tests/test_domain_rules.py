"""
Testy pro modul domain_rules (právní domény).
"""

from engines.domain_rules.loader import normalize_domain_name, load_domain_profile


def test_normalize_domain_name_basic_mapping():
    assert normalize_domain_name("občanské právo") == "civil"
    assert normalize_domain_name("trestní právo") == "trestni"
    assert normalize_domain_name("rodinné právo") == "rodinne"
    assert normalize_domain_name("správní právo") == "spravni"


def test_load_domain_profile_civil_exists():
    profile = load_domain_profile("občanské právo")
    assert isinstance(profile, dict)
    assert profile.get("domain_key") == "civil"
    assert "legal_issues" in profile
    assert isinstance(profile["legal_issues"], list)
    assert len(profile["legal_issues"]) > 0


def test_load_domain_profile_unknown_returns_fallback():
    profile = load_domain_profile("úplně neznámá doména")
    assert isinstance(profile, dict)
    # fallback = civil
    assert profile.get("domain_key") == "civil"