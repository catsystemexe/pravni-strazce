# 🛡️ Právní Strážce – core AI framework

Tento repozitář obsahuje **core backendový framework** pro AI agenta „Právní Strážce“ – právního asistenta pro veřejnost v ČR.

Cíl jádra:

- strukturovaně zpracovat právní dotaz laika,
- rozdělit práci mezi specializované moduly (engines),
- vytvořit konzistentní výstup (shrnutí, právní analýza, judikatura, rizika, další postup),
- umožnit postupné napojení LLM (OpenAI), databází judikatury a dalších zdrojů.

Aktuální stav: **Skeleton v0 – plně průchozí struktura + testy (`4 passed`).**  
Logika je zjednodušená, ale architektura je připravená na rozšíření.

---

## 🔍 Co framework umí teď (Skeleton v0)

Při volání `run_pipeline()`:

- vezme vstupní dotaz uživatele (např. „Notářka mi odmítá umožnit nahlédnout do spisu, jak mám postupovat?“),
- pošle ho do orchestrátoru,
- orchestrátor zavolá:
  - `core_legal_engine` – vytvoří **IRAC skeleton** (issues, rules, analysis, conclusion),
  - `judikatura_engine` – zatím **mock**, připravený na budoucí napojení,
  - risk / next-steps vrstvy ve skeleton režimu,
- poskládá **Markdown výstup**:

  - 🧩 Shrnutí  
  - ⚖️ Právní analýza  
  - 📚 Judikatura  
  - ⚠️ Rizika a nejistoty  
  - 🧭 Další postup  

Skeleton verze výslovně říká, že jde o ukázkovou strukturu a že reálné právní závěry teprve přibudou.

---

## 🏗️ Architektura

Zjednodušený přehled:

```text
.
├── api/                # (do budoucna) HTTP/API vrstvy
├── engines/
│   ├── core_legal/     # Hlavní právní analýza (IRAC)
│   ├── judikatura/     # Vyhledávání a práce s judikaturou
│   └── shared_types.py # EngineInput, EngineOutput, sdílené typy
├── llm/
│   ├── client.py       # Abstraktní LLM klient (OpenAI wrapper)
│   ├── config.yaml     # Modely, teploty, limity
│   └── prompts/        # Prompt šablony pro jednotlivé moduly
├── product/            # (do budoucna) produktové konfigurace, presets
├── runtime/
│   ├── orchestrator.py # Hlavní orchestrátor – skládá výstup
│   └── config_loader.py# Načítání YAML configů
├── templates/          # Šablony výstupů (Markdown, HTML, atd.)
├── tests/              # Pytest testy pro engines i orchestrátor
└── README.md
