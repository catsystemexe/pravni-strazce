📄 Právní Strážce – Třívrstvá Klasifikační Architektura (TXT Protokol)

(vložitelné jako .txt / .md bez úprav)

⸻

============================================================

1) DOMAIN MAP

============================================================

Kategorie

Domain (právní oblast) = nejvyšší orientační vrstva
Příklad: traffic_law, family_law, criminal_law

Popis

Domain reprezentuje širokou oblast práva, která sdružuje všechny subdomeny a situace, jež logicky patří do stejné právní sféry.
Domain slouží k rychlému rozhodnutí, “kam dotaz vůbec patří”.

Domain obsahuje pouze makro informace:
  •	velmi obecný popis právní oblasti
  •	široká témata
  •	základní klíčová slova (macro_keywords)
  •	negativní vylučující klíčová slova
  •	typické dokumenty (není povinné)
  •	seznam subdomen

Význam
  •	Domain je první filtr: určuje, do které právní oblasti dotaz spadá.
  •	AI získá zásadní kontext, ještě než se pustí do detailů.
  •	Zajišťuje rychlou orientaci, snižuje riziko chybného zařazení.
  •	Domain-level keywords jsou záměrně široké (např. “policie”, “přestupek”, “řidič”, “vozidlo”).
  •	Domain NEMÁ obsahovat detaily ani procesní logiku — ty přijdou až v dalších vrstvách.

⸻

============================================================

2) SUBDOMAIN MAP

============================================================

Kategorie

Subdomain = specifický typ problému v rámci jedné právní domény
Příklad:
  •	traffic_speed_offenses
  •	alcohol_test
  •	accident_liability
  •	driving_license

Popis

Subdomain je mezivrstva, která rozlišuje různé druhy problémů v rámci jedné právní oblasti.
Zatímco Domain říká „jsme v dopravním právu“, Subdomain říká „zde řešíme rychlost“ nebo „zde řešíme alkohol“.

Subdomain obsahuje meso informace:
  •	přesnější tematické zaměření
  •	klíčová slova (meso_keywords) pro odlišení subdomen mezi sebou
  •	typická rizika / patterny pro daný typ situací
  •	příklady typických hranic (co ještě patří / nepatří)
  •	seznam intentů, které do subdomain spadají

Význam
  •	Subdomain je druhá úroveň orientace po Domain.
  •	Zajišťuje, že AI pozná rozdíl mezi rychlost, alkohol, nehoda, řidičský průkaz.
  •	Pomáhá robustně zúžit kontext před tím, než engine pracuje s detailním intentem.
  •	Slouží jako logický most mezi obecným (Domain) a detailním (Intent).

⸻

============================================================

3) INTENT DEFINITIONS

============================================================

Kategorie

Intent = konkrétní právní situace nebo typový případ uživatele
Příklad:
  •	traffic_speed_offense
  •	alcohol_refusal_offense
  •	child_custody_contact
  •	inheritance_contestation
  •	workplace_termination

Popis

Intent představuje nejnižší, nejdetailnější a nejdůležitější vrstvu architektury.

Zde se definují:
  •	přesný typ problému
  •	konkrétní klíčová slova
  •	negativní klíčová slova
  •	příklady vzorových dotazů
  •	risk patterns (regex / patterny pro rizika)
  •	basic otázky pro získání doplňujících informací
  •	safety otázky (časové a právní bezpečnostní faktory)
  •	odkazy na právní normy
  •	šablony závěru (conclusion skeletons)
  •	poznámky k rizikům a hraničním situacím

Intent je úroveň, ze které engine generuje:
  •	analýzu,
  •	otázky,
  •	scénáře,
  •	závěry,
  •	rizika.

Význam
  •	Intent je jádro právní logiky, kde se odehrává skutečná práce.
  •	Obsahuje všechny detaily potřebné k vytvoření přesné právní analýzy.
  •	AI podle intentu ví, jaké otázky položit, jaké riziko řeší, a jaký postup doporučit.
  •	Intent definuje operacionalizované právní chování systému.

⸻

============================================================

🔥 PROČ TŘÍ-VRSTVÁ ARCHITEKTURA FUNGUJE TAK DOBŘE?

============================================================
  1.	Domain: rychlá orientace v právním světě
  2.	Subdomain: rozlišení typu problému v rámci oblasti
  3.	Intent: detailní znalost konkrétní právní situace

Tato struktura zajišťuje:
  •	minimální chyby v klasifikaci,
  •	vysokou vysvětlitelnost,
  •	možnost validace každé vrstvy,
  •	škálovatelnost (stačí přidat nové intent JSONy),
  •	zatímco Domain a Subdomain zůstávají stabilní.

⸻

============================================================

📌 SHRNUTÍ – CO KAŽDÁ VRSTVA OBSAHUJE

============================================================

Domain
  •	domain
  •	label_cs
  •	description_domain
  •	macro_keywords
  •	negative_keywords
  •	typical_documents
  •	subdomains

Subdomain
  •	subdomain_id
  •	label_cs
  •	description_subdomain
  •	meso_keywords
  •	boundary_includes / boundary_excludes
  •	typical_risks
  •	intents

Intent
  •	intent_id
  •	label_cs
  •	domain
  •	subdomain
  •	description_cs
  •	keywords
  •	negative_keywords
  •	examples
  •	risk_patterns
  •	basic_questions
  •	safety_questions
  •	normative_references
  •	conclusion_skeletons
  •	notes
  •	version
