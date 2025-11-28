# 📚 Slovník Právního Strážce – Master Doménový Katalog

Toto je centrální seznam právních domén, který používají:
- intent engine
- domain_rules (YAML)
- runtime/domain_catalog.py
- produktové „packs“

Každá doména má strojové ID, lidský název, vazbu na YAML s pravidly
a typické intenty.

| Domain_ID           | Label (CZ)                    | Popis / scope                                                                 | YAML soubor                         | Typické intenty                                      | Poznámky |
|---------------------|------------------------------|-------------------------------------------------------------------------------|-------------------------------------|------------------------------------------------------|----------|
| civil_law           | Občanské právo               | Smlouvy, náhrada škody, vlastnictví, sousedské spory, dluhy mezi osobami     | `engines/domain_rules/civil.yaml`   | `complaint`, `document_check`, `info`               | Základní default doména pro „běžné spory“ |
| family_law          | Rodinné právo                | Rozvod, péče o dítě, výživné, styky s dítětem                                 | `engines/domain_rules/rodinne.yaml` | `complaint`, `document_check`, `info`               | Často napojené na OSPOD a soudy péče o nezletilé |
| inheritance_law     | Dědické právo                | Dědická řízení, závěti, podíly dědiců, vypořádání pozůstalosti                | `engines/domain_rules/notarske.yaml`| `inheritance`, `complaint`, `document_check`, `info` | Typicky „notář + soud“ kombinace |
| labour_law          | Pracovní právo               | Výpovědi, okamžitá zrušení, mzda, přestávky, pracovní podmínky                | `engines/domain_rules/civil.yaml`   | `labor_termination`, `complaint`, `document_check`  | Pracovněprávní agenda – může sdílet YAML s civil, ale mít vlastní sekce |
| administrative_law  | Správní právo                | Úřady, rozhodnutí, odvolání, přestupky mimo dopravu                           | `engines/domain_rules/spravni.yaml` | `appeal_admin_decision`, `complaint`, `info`        | Včetně správních soudů (přezkum) |
| traffic_offences    | Dopravní přestupky           | Rychlost, pásy, telefon, zákaz řízení, bodový systém                          | `engines/domain_rules/spravni.yaml` | `traffic_speed_offence`, `complaint`, `info`        | Technicky správní právo, ale vyčleněné pro lepší UX |
| school_law          | Školské právo                | Vztah škola–žák–rodič, kázeňské postihy, vyloučení, OSPOD, šikana             | `engines/domain_rules/skolske.yaml` | `school_dispute`, `complaint`, `info`               | Speciální těžiště projektu, důraz na ochranu dítěte |
| criminal_law        | Trestní právo                | Podezření, obvinění, poškozený, náhrada škody v trestním řízení               | `engines/domain_rules/trestni.yaml` | `criminal_defense`, `info`                          | Zatím spíš high-level orientace, ne plná obhajoba |
| health_law          | Zdravotnické právo           | Zdravotní péče, souhlasy, odmítnutí léčby, pochybení lékaře, dokumentace      | `engines/domain_rules/zdravotnicke.yaml` | `complaint`, `document_check`, `info`         | Vztah pacient–zdrav. zařízení |
| consumer_law        | Spotřebitelské právo         | Reklamace, odstoupení, e-shopy, úvěry, pojištění, nekalé praktiky             | `engines/domain_rules/spotrebitel.yaml` | `consumer_credit`, `complaint`, `document_check` | Vhodné pro „rychlé checklisty“ |
| notarial_law        | Notářská agenda              | Dědictví, ověřování, notářské zápisy, úschovy                                 | `engines/domain_rules/notarske.yaml`| `inheritance`, `document_check`, `complaint`, `info`| Překrývá se s civil + inheritance |
| other               | Ostatní / neurčeno           | Nejasně zařaditelné dotazy, mix domén, obecné info                             | *(bez YAML, fallback)*              | `info`                                               | Výchozí koš, dokud se dotaz nezařadí přes LLM |