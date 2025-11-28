"""
Domain Rules Loader

Cíl:
- z textové domény typu "občanské právo", "trestní", "rodinné" atd.
  udělat interní klíč (civil, trestni, rodinne, spravni, ...)
- načíst YAML profil dané domény (legal_issues, risk_keywords, priority_rules, ...)

Pokud profil neexistuje, vrací prázdný dict – engine se dál chová korektně.
"""

from __future__ import annotations

from typing import Dict, Any, Optional

from runtime.config_loader import load_yaml


def normalize_domain_name(raw: Optional[str]) -> str:
    """
    Vezme libovolný slovní popis domény (česky) a vrátí interní klíč.

    Příklady:
    - "občanské právo" -> "civil"
    - "trestní právo" -> "trestni"
    - "rodinné právo" -> "rodinne"
    - "správní právo" -> "spravni"
    - "školské právo" -> "skolske"
    - "pracovní právo" -> "pracovni"
    - "notářská agenda" -> "notarska"
    - "zdravotnické právo" -> "zdravotnicke"
    - "ochrana spotřebitele" -> "spotrebitel"

    Pokud nic nesedí, vrací "civil" jako konzervativní default.
    """
    if not raw:
        return "civil"

    text = raw.strip().lower()

    # hrubé heuristiky podle podřetězců
    if "trest" in text:
        return "trestni"
    if "rodin" in text:
        return "rodinne"
    if "správn" in text or "spravn" in text:
        return "spravni"
    if "škol" in text or "skol" in text:
        return "skolske"
    if "pracovn" in text:
        return "pracovni"
    if "notář" in text or "notar" in text:
        return "notarska"
    if "zdravotn" in text:
        return "zdravotnicke"
    if "spotřebit" in text or "spotreb" in text:
        return "spotrebitel"

    # civilní právo / obecné občanské
    if "občans" in text or "obcans" in text:
        return "civil"

    # fallback – raději civil než nic
    return "civil"


def load_domain_profile(domain_name: Optional[str]) -> Dict[str, Any]:
    """
    Načte YAML profil pro danou doménu.

    - domain_name: volná textová doména (např. 'občanské právo', 'trestní')
    - vrací dict s klíči jako:
      - domain_key
      - label
      - legal_issues
      - risk_keywords
      - priority_rules
      - typical_parties
      - notes

    Pokud se cokoliv nepodaří (soubor neexistuje, špatný YAML...),
    vrací prázdný dict.
    """
    key = normalize_domain_name(domain_name)

    # soubory jsou v engines/domain_rules/<key>.yaml
    rel_path = f"engines/domain_rules/{key}.yaml"

    try:
        data = load_yaml(rel_path)
        if isinstance(data, dict):
            return data
        return {}
    except FileNotFoundError:
        return {}
    except Exception:
        # nechceme shodit engine kvůli chybě v doménovém profilu
        return {}