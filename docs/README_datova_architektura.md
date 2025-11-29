📘 Právní Strážce – Datová Architektura

Tato dokumentace popisuje kompletní architekturu datového systému Právního Strážce.
Cílem je udržet přehlednost, auditovatelnost a škálovatelnost při generování právních dat.

🧭 1. Architektura projektu

Právní Strážce používá dvouvrstvý datový model:
  1.	YAML zdroje (ručně editovatelné)
  2.	JSON kompiláty (runtime data pro engine)

Flow:
  •	YAML ⇒ generátor ⇒ JSON ⇒ načtení enginem

📁 2. Struktura adresářů

data/
├── _source/
│   └── domains/
│       └── traffic_law/
│           ├── domain.yaml
│           ├── subdomains.yaml
│           └── intents/
│               ├── speeding.yaml
│               ├── alcohol_drugs.yaml
│               └── police_interaction.yaml
└── intents/
└── traffic_law/
├── traffic_speed_offense.json
├── alcohol_test_refusal.json
└── police_interaction_basic.json
  •	YAML = zdrojová data
  •	JSON = kompilovaná data, která engine používá

⚙️ 3. Generační pipeline
  1.	Domain YAML
  2.	Subdomain YAML
  3.	Intent YAML
  4.	Python generátor vytvoří JSON
  5.	Validace + testy
  6.	Engine načte JSON

Pipeline:

Editor/LLM/uživatel
→ YAML domain
→ YAML subdomain
→ YAML intent
→ python -m tools.generate
→ JSON
→ runtime engine

🧱 4. Sémantický model

DOMAIN
→ SUBDOMAIN
→ INTENT

INTENT obsahuje:
keywords
negative_keywords
risk_patterns
normative_references
basic_questions
safety_questions
conclusion_skeletons

Domain a subdomain nesměřují přímo k právní akci — jen kategorizují prostor.
Intent je jediná jednotka určující právní scénář.

🧾 5. Popis všech souborů

A) domain.yaml

Definuje celou doménu:

domain_id
label_cs
description_domain_cs
global_keywords

B) subdomains.yaml

Definuje podkategorie domény:

subdomain_id
label_cs
description_subdomain_cs
seed_keywords

C) intents/*.yaml

Popisuje konkrétní právní scénáře:

intent_id
label_cs
description_cs
subdomains
keywords
negative_keywords
examples
risk_patterns
basic_questions
safety_questions
normative_references
conclusion_skeletons
notes
version

D) JSON (runtime)

Kompilované výstupy používané enginem.

🛠 6. Workflow
  1.	Upravit YAML:
data/_source/domains//
  2.	Spustit generátor:
python -m tools.generate_intents_from_domains –domain traffic_law
  3.	Validovat:
python -m tools.validate_intents
  4.	Spustit testy:
pytest
  5.	Engine automaticky načte JSON.

🔒 7. Pravidla

✔ YAML = editable source
✔ JSON = compiled, read-only
✔ Každá doména má vlastní adresář
✔ Subdomény a intents odděleně
✔ JSONy se negenerují ručně
✔ Validace musí mít 0 errors
✔ Testy musí projít před mergem

🌱 8. Roadmapa
  •	✔ Domain/Subdomain/Intent pipeline
  •	✔ Hotový traffic_law
  •	🔜 Auto-generátor YAML skeletonů
  •	🔜 CI validace v GitHub Actions
  •	🔜 mermaid diagramy
  •	🔜 webová dokumentace (MkDocs)
