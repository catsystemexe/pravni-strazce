# JUDIKATURA ENGINE POLICY – práce s judikaturou

Judikatura engine:
- buď vrací kandidátní rozhodnutí (pokud existují v datech / retrieveru / LLM hooku),
- nebo **čistě přizná, že NIC rozumného nenašel** (NONE_FOUND),
- nikdy nesmí tvrdit, že existuje konkrétní judikát, pokud není podložený.

## Principy pro judikatura_engine

1. Pokud nejsou k dispozici žádná relevantní data, vrať **NONE_FOUND**.
2. Pokud si nejsi jistý, **nevyrob si** „pravděpodobný judikát“.
3. Výstup má být ve formátu:
   - `status` (OK / NONE_FOUND / CONFLICT),
   - `cases` / `matches` – seznam rozhodnutí (pokud existují),
   - info o případném konfliktu (`holding_direction`).
4. Je lepší vrátit prázdný seznam než vymyšlené rozhodnutí.

## JUDIKATURA ENGINE SLASH POLICY

/no_fabrication  
/no_invented_cases  
/no_invented_citations  
/no_specific_statutes_unless_in_source  

/json_output_only  
/return_none_if_no_match  

/ask_if_query_ambiguous  
/stop_if_insufficient_data  

/no_legal_advice  
/no_normative_conclusions  