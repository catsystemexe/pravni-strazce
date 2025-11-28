================================================================================
ODPOVĚĎ CODING AGENTA:

## 1. Co chápu ze struktury projektu

- **Jádro je orchestrátorová pipeline**  
  - `runtime/orchestrator.run_pipeline` skládá výsledek z více engine modulů (core_legal, judikatura, risk, intent, safety, output, memory).
  - `engines/shared_types.EngineInput/EngineOutput` dávají všem engine jednotné rozhraní.

- **LLM vrstva je částečně duplicitní**  
  - V `llm/client.py` je robustní klient s mock/openai backendem řízeným env proměnnými.  
  - V `llm/config.py` je druhý, starší LLMClient založený přímo na `OpenAI`, používá `llm/config.yaml`.  
  - Hrozí zmatek, který z těchto klientů mají enginy používat.

- **Domény a policy: 2 paralelní zdroje pravomocí/domén**
  - `engines/domain_rules/*.yaml` – doménově specifická pravidla (civil, rodinne, trestni, spravni, skolskE, zdravotnicke, spotrebitel, notarske).  
  - `runtime/domain_catalog.py` (zatím nevidím obsah, ale existuje) + `data/schema/domains.json` – zjevný pokus o „master katalog“ domén.  
  - Nad tím: `packs/*` (např. `packs/family/config.yaml`, `packs/civil/config.yaml`) jako high‑level výběry funkcí/domén.

- **Intent & klasifikace**  
  - `engines/intent/engine.py` – čistě heuristický klasifikátor (string match na klíčová slova) → vrací `intent`, `domain`, `confidence`, raw skóre.  
  - `engines/intent/prompts/intent_classification.md` – prompt pro LLM-based intent engine; popisuje bohatší JSON výstup (`reasoning`, `questions_for_user` atd.).  
  - V datech: `data/intents/**/*` – JSON popisy konkrétních use‑cases (např. `labor_law/labor_termination.json`, `administrative_law/traffic_speed_offence.json`).  
  - Zatím nejsou jasná pravidla, jak se tyto JSON „intenty“ napojují na heuristický/LLM intent engine.

- **Core právní engine (IRAC skeleton)**  
  - `engines/core_legal/engine.py` + prompty v `engines/core_legal/prompts/*` (issue_identification, rules, analysis, conclusion, certainty, domain_classification, fact_extraction).  
  - Output se používá v orchestrátoru pro generaci finální odpovědi.  
  - `templates/answers/legal_answer_with_judikatura.md` – šablona finální odpovědi (strukturovaná).

- **Judikatura, risk, safety, output, memory**  
  - `engines/judikatura/*` – vlastní engine s konfigem a promptem.  
  - `engines/risk/*`, `engines/safety/*`, `engines/output/*`, `engines/memory/*` – každé má config a případně prompty / šablony.  
  - Jsou připravené skeletony, ale není plně definovaný jednotný „contract“ pro payload (jen implicitně v testech).

- **Produktová vrstva a policy**  
  - `product/e_advokat_pro/*.yaml` – product config, risk policy, licensing, feature flags.  
  - `prompts/policy/*` – globální policy pro jednotlivé enginy (core_legal, risk, intent, judikatura…).  
  - `tools/apply_policy.py`, `tools/validate_data.py` – pomocné nástroje.

- **Intents & domény v datech**  
  - `data/intents/_template/intent_template.json` – datový vzor.  
  - Konkrétní intents jsou rozdělené do podsložek podle „právní větve“ (`labor_law`, `administrative_law`, `criminal_law`, `consumer_finance_law`).
  - `knowledge/legal_dictionary.md` – slovníček/terminologie.

- **Runtime**  
  - `runtime/config_loader.py`, `runtime/context.py`, `runtime/legal_sources.py`, `runtime/domain_catalog.py` – pomocné vrstvy pro načítání configů, katalog domén, zdroje práva.  
  - `tests/*` – pokrývají domain_rules, judikaturu, pipeline, core_legal.

---

## 2. Návrh konkrétních dalších kroků

### 1) Ujednotit LLM vrstvu (odstranit duplicitní klienty)

1.1 Rozhodnout, který LLM klient je „single source of truth“  
- Doporučení:  
  - Použít **`llm/client.py`** jako jediný klient: umí mock režim, fallback při chybách a přepínání backendu přes env.  
  - Funkce z `llm/config.py` (čtení `llm/config.yaml`, řízení model/teplota/max_tokens podle use_case) přesunout jako **konfigurační vrstvu nad `LLMClient` z `llm/client.py`**.

1.2 Refaktor:  
- Vytvořit v `llm/client.py` malou utilitu: `load_llm_params(use_case: str) -> dict` čtoucí `llm/config.yaml`.  
- Uvnitř `LLMClient.chat()` použít tyto parametry namísto ad‑hoc env proměnných.  
- Odstranit nebo deprekovat `llm/config.py` (přidat poznámku v docstringu, že je legacy a nebude používaný).

1.3 Dokumentace:  
- Do README přidat sekci „LLM architektura“:  
  - jak se volá `LLMClient`,  
  - jak nastavit `LLM_BACKEND`, `OPENAI_API_KEY`, `OPENAI_MODEL`,  
  - jak se mapují use_case → model, teplota, limity.

---

### 2) Zavést jednotný „master“ katalog domén

2.1 Jednotný zdroj domén  
- Aktuálně existují:  
  - `engines/domain_rules/*.yaml` – mají názvy jako `civil`, `spotrebitel`, `skolske`, `trestni`…  
  - `data/schema/domains.json` – master schema (potřeba zkontrolovat obsah).  
  - Domény v intent engine (`civil`, `criminal`, `administrative`, `school`, `family`, `inheritance`, `labour`, `other`).  
- Navrhuji:  
  - Vytvořit **centrální definici** v `data/schema/domains.json` (každá doména s klíči: `id`, `name`, `aliases`, `parent`, `description`, `engine_rules_file`, `packs`).  
  - `runtime/domain_catalog.py` pak při startu načte toto JSON a poskytne API:

    ```python
    from runtime.domain_catalog import get_domain_by_id, match_domain_alias, list_domains
    ```

2.2 Mapování domain_rules ↔ master katalog  
- Do každého `engines/domain_rules/*.yaml` doplnit pole `domain_id: "civil"` atd., aby se dalo spolehlivě spojit s master katalogem.  
- V testech (`test_domain_rules.py`) ověřit, že pro každý `domain_id` z katalogu existuje odpovídající YAML a naopak.

2.3 Aktualizace ostatních částí  
- Upravit `engines/intent/engine.py`, aby pro `domain` vracel pouze hodnoty, které existují v master katalogu (příp. fallback `other`).  
- V `core_legal` a `packs/*/config.yaml` místo ručních stringů používat `domain_id` z katalogu.

---

### 3) Zpřesnit vazbu mezi intent enginem, `data/intents` a doménami

3.1 Standardizovat strukturu `data/intents/*/*.json`  
- Zkontrolovat `_template/intent_template.json`, definovat minimální mandatory pole, např.:

  ```json
  {
    "id": "labor_termination",
    "title": "...",
    "domain_id": "labour",
    "primary_intent": "document_check",
    "description": "...",
    "patterns": ["výpověď", "okamžité zrušení pracovního poměru", ...],
    "examples": [
      {"user_query": "...", "notes": "..."}
    ]
  }
  ```

- Doplnit do `README` nebo do `data/schema/intent_schema.json` formální JSON schema.

3.2 Napojit heuristický intent engine na `data/intents`  
- V `engines/intent/engine.py` dnes jsou ručně psané seznamy klíčových slov.  
- Návrh:  
  1. Zavést loader, např. `runtime.intent_catalog` (analogicky k domain_catalog).  
  2. Převést klíčová slova z jednotlivých JSON intentů (`patterns`) do indexu (např. dictionary: keyword → {intent_id, domain_id}).  
  3. Heuristický engine:  
     - Namísto tvrdého kódu seznamů využít data z katalogu: pro každý intent/keyword spočítat skóre.  
     - Vrátit `intent_id` (např. `labor_termination`) a zároveň `high_level_intent` (např. `document_check`) + `domain_id`.

3.3 Duální režim: heuristika + LLM  
- Využít `engines/intent/prompts/intent_classification.md` tak, že:  
  - intent engine dostane parametr `use_llm` (z env nebo orchestrátoru).  
  - v LLM režimu:  
    - 1. krok – heuristika (rychlá, levná, navrhne kandidáty).  
    - 2. krok – LLM dostane jako vstup dotaz + top N kandidátů z heuristiky a rozhodne:  
      - `intent_id`,  
      - `domain_id`,  
      - `confidence`,  
      - `reasoning`, `questions_for_user`.  
- Output sjednotit: i v čistě heuristickém režimu generovat JSON se stejnými klíči, jen např. `reasoning` stručný text „heuristický výběr na základě klíčových slov“.

---

### 4) Vyčistit a sjednotit šablony výstupu (answers/documents)

4.1 Standardizovat answer template  
- `templates/answers/legal_answer_with_judikatura.md` – zkontrolovat, které placeholdery opravdu orchestrátor vyplňuje (`{{summary}}`, `{{analysis}}`, `{{judikatura}}`, `{{risk}}`, `{{next_steps}}` atd.).  
- Vytvořit v `runtime/orchestrator.py` jasnou transformaci: payload → templating context (dict).  
- Zvážit použití jednoduchého templating engine (Jinja2) nebo vlastního minimal templateru, aby se vyhla ručnímu `.replace()`.

4.2 Propojit templates/documents s právními doménami / intentem  
- `templates/documents/*.md` (ultra_clean_export_40y, ultra_legal_document_40y) – zřejmě výstupní formáty dokumentů (smlouvy, podání).  
- Doporučení:  
  - Přidat do `data/intents/*` atribut `document_templates: ["ultra_clean_export_40y"]` apod.  
  - V orchestrátoru podle `intent_id` (např. „appeal_admin_decision“) nabídnout vhodnou šablonu dokumentu (i když zatím jen textový skeleton).

4.3 Dodat mini-dokumentaci k šablonám  
- V `templates/README.md` (nový soubor) vysvětlit:  
  - typy šablon (answers vs. documents),  
  - jaké proměnné mohou obsahovat,  
  - příklady, jak z orchestrátoru vyplňovat.

---

### 5) Doménová pravidla – formální kontrakt a validace

5.1 Standardizovat strukturu `engines/domain_rules/*.yaml`  
- Vytvořit `data/schema/domain_rules_schema.yaml` nebo JSON schema s alespoň:  
  - `domain_id`,  
  - `name`,  
  - `keywords` (pro baseline rozpoznávání),  
  - `important_acts` (seznam zákonů a paragrafů),  
  - `typical_issues` (popis typických situací).

5.2 Runtime API pro domain_rules  
- Rozšířit `engines/domain_rules/loader.py` tak, aby poskytoval:  

  ```python
  def get_rules_for_domain(domain_id: str) -> dict
  def list_domains_with_rules() -> List[str]
  ```

- Core_legal engine při identifikaci domény může využít `keywords` z těchto files jako doplněk k LLM heuristice (pro skeleton režim bez LLM).

5.3 Testy a validace  
- Rozšířit `tests/test_domain_rules.py`:  
  - validace proti schema,  
  - kontrola, že každý `domain_id` z `domains.json` má existující rules YAML,  
  - kontrola, že YAML obsahuje povinné klíče.

---

### 6) Zpřehlednit produktovou vrstvu a „packs“

6.1 Jasný vztah: product ↔ packs ↔ domains  
- `product/e_advokat_pro/product.yaml` – definice produktu by měla obsahovat:  
  - které packs jsou zapnuté (např. `common`, `family`, `civil`)  
  - jaké domény jsou podporované.  
- `packs/*/config.yaml` – each pack definovat:  
  - `domains` (list of domain_id),  
  - `enabled_engines` (např. `["core_legal", "judikatura", "risk"]`),  
  - extra policy (např. striktnější risk policy pro trestní doménu).

6.2 Orchestrátor a konfigurace  
- `runtime/orchestrator.py` rozšířit, aby při startu načetl `product.yaml` a aktivoval pouze příslušné domény/enginy.  
- V testech vytvořit jeden „minimal product config“ (např. jen civil) a ověřit, že pipeline správně restriktivně reaguje (např. dotazy z jiných domén označí jako „mimo rozsah“).

---

### 7) Dokumentace pro vývoj domén, intentů a šablon

7.1 Dev‑dokument „Jak přidat nový intent“  
- V `README.md` nebo `docs/adding_intents.md` popsat:  
  1. Vytvoř JSON podle `_template/intent_template.json`.  
  2. Vyber nebo doplň doménu v `data/schema/domains.json`.  
  3. Přidej klíčová slova (patterns) – budou použita heuristickým intent enginem.  
  4. (Volitelně) Přidej document templates.  
  5. Přidej testy (unit test pro intent engine s konkrétním dotazem).

7.2 Dev‑dokument „Jak přidat novou doménu“  
- Postup:  
  1. Zapsat doménu do `domains.json`.  
  2. Vytvořit `engines/domain_rules/<new>.yaml` podle schema.  
  3. Rozšířit `packs/*` (kde dává smysl) o novou doménu.  
  4. Přidat aspoň 1–2 intents v `data/intents/<domain>/`.  
  5. Test: nový test v `tests/test_domain_rules.py` / `tests/test_runtime_pipeline.py`.

7.3 Dev‑dokument „Jak měnit šablony výstupů“  
- Popis proměnných v `templates/answers/legal_answer_with_judikatura.md` a v `templates/documents/*`.  
- Příklad: jak orchestrátor předává data (payload core_legal, judikatura, risk) do šablon.

---

## 3. Co není jasné / co chybí pro přesnější návrhy

Aby bylo možné jít ještě detailněji (např. navrhovat přesnou strukturu JSON schema a konkrétní typy), potřeboval bych:

1. **Obsah těchto klíčových souborů:**
   - `runtime/orchestrator.py` – přesně jak skládá výstup, jaké payload klíče očekává od jednotlivých engine.  
   - `runtime/domain_catalog.py` – jestli už definuje master seznam domén, nebo je jen placeholder.  
   - `data/schema/domains.json` – aktuální definice domén a jejich struktura.  
   - jeden dva ukázkové soubory z `data/intents/` (např. `labor_termination.json`, `traffic_speed_offence.json`) – abych navrhl přesné schema.  
   - `engines/core_legal/engine.py` – abych mohl standardizovat kontrakt mezi core_legal a šablonou odpovědi.  
   - `templates/answers/legal_answer_with_judikatura.md` – přesné placeholdery.

2. **Produktové preference:**
   - Zda preferujete **co nejvíc logiky v datech** (domain_rules, intent_patterns, templates) a enginy spíše jako generické procesory, nebo jste OK s větším množstvím „if‑else“ v kódu.  
   - Jak moc má být intent/domena klasifikace **strictly deterministic** vs. LLM‑driven.

3. **Směr vývoje LLM integrace:**
   - Jestli je cílem mít **full LLM pipeline**, kde heuristiky slouží jen jako fallback, nebo naopak **LLM jen jako nadstavbu** nad deterministickým skeletonem pro některé produkty (např. kvůli nákladům/bezpečnosti).

---

Pokud pošleš obsah zmíněných souborů (orchestrator, domains.json, jeden intent JSON, core_legal.engine, answer template), můžu navrhnout konkrétní JSON/YAML schémata a přesný „contract“ mezi enginy a šablonami.
================================================================================
