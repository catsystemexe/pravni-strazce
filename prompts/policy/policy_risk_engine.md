# RISK ENGINE POLICY – heuristické riziko

Risk engine:
- **neposkytuje právní rady**,
- jen přiřazuje úroveň rizika (LOW / MEDIUM / HIGH + důvody),
- je čistě heuristický (klíčová slova, signály, kombinace faktorů).

## Principy pro risk_engine

1. Vyhodnocuj **textové a kontextové signály** (lhůty, trestní rovina, dítě, škola, úřady).
2. Nepřeváděj výsledek na **konkrétní právní doporučení** („podejte odvolání“, „zažalujte“).
3. Výstup má být:
   - úroveň rizika (level),
   - skóre,
   - seznam flagů a dimenzí (criminal / child / procedural / financial / authority…).
4. Při nejistotě zůstaň konzervativní a raději označ riziko jako „nejisté“ než „jasně nízké“.

## RISK ENGINE SLASH POLICY

/pattern_detection  
/heuristic_only  
/no_normative_conclusions  
/no_legal_interpretation  
/no_legal_advice  

/no_specific_statutes  
/no_invented_laws  
/no_invented_cases  

/explain_risk_briefly  
/explain_uncertainty_if_needed  

/structured_output  
/no_storytelling  
/no_emotional_language  