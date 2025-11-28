# llm/config.py
# =============================================================================
# DEPRECATED / LEGACY MODULE
#
# Tento modul (llm/config.py) je považován za **DEPRECATED**.
# Původně obsahoval alternativního LLMClienta vázaného na llm/config.yaml.
#
# Nově je jediným oficiálním LLM klientem:
#     `llm.client.LLMClient` a `llm.client.LLMMessage`
#
# Všechny nové enginy a kód by měly používat `llm.client`.
# Tento modul je zde pouze z historických důvodů a může být v budoucnu odstraněn.
# =============================================================================

from __future__ import annotations

from runtime.config_loader import load_yaml

# Pokud někde někdo ještě používá llm/config.yaml přímo,
# může si config načíst přes tuto pomocnou funkci.
# Nedáváme sem žádného klienta, aby nevznikala duplicita.

_CONFIG = load_yaml("llm/config.yaml")


def get_raw_llm_config() -> dict:
    """
    Vrátí syrovou konfiguraci LLM z llm/config.yaml.
    Používej raději llm.client.get_llm_params_for_use_case().
    """
    return _CONFIG
