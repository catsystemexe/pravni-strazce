# orchestrator.py
from typing import Any, Dict, List, Optional
from datetime import datetime, timezone

import os

from engines.shared_types import EngineInput, EngineOutput
from engines.core_legal.engine import run as core_legal_engine
from engines.risk.engine import run as risk_engine
from engines.judikatura.engine import run as judikatura_engine
from engines.intent.engine import run as intent_engine


# =====================================================================
#  Hlavní orchestrátor – jediná správná verze run_pipeline
# =====================================================================

def run_pipeline(
    user_query: str,
    *,
    use_llm: Optional[bool] = None,
    mode: str = "full",
    debug: bool = False,
    raw: bool = False,
) -> Dict[str, Any]:
    """
    Hlavní orchestrátor celého systému.
    ...
    """

    # 1) Rozhodnutí, zda použít LLM
    if use_llm is None:
        env_flag = os.getenv("PIPELINE_USE_LLM", "").lower() in ("1", "true", "yes")
        use_llm_flag = env_flag
    else:
        use_llm_flag = bool(use_llm)

    case_ctx = {"user_query": user_query}

    # 1a) INTENT & DOMAIN ENGINE
    intent_out: EngineOutput = intent_engine(
        EngineInput(
            context={
                "case": case_ctx,
            }
        )
    )
    intent_payload = intent_out.payload

    # 2) CORE LEGAL ENGINE
    core_out: EngineOutput = core_legal_engine(
        EngineInput(
            context={
                "case": case_ctx,
                "use_llm": use_llm_flag,
            }
        )
    )
    core_payload = core_out.payload

    # doplníme intent/domain do meta core enginu
    core_meta = core_payload.get("meta") or {}
    core_payload["meta"] = core_meta  # jistota, že meta existuje

    # nepřepisujeme, pokud už by náhodou bylo nastavené
    if intent_payload.get("domain") and not core_meta.get("domain"):
        core_meta["domain"] = intent_payload["domain"]

    core_meta["intent"] = intent_payload.get("intent")
    core_meta["intent_confidence"] = intent_payload.get("confidence")

    # 3) RISK ENGINE
    risk_out: EngineOutput = risk_engine(
        EngineInput(
            context={
                "case": case_ctx,
                "core": core_payload,
                "use_llm": False,  # risk engine zatím čistě heuristický
            }
        )
    )
    risk_payload = risk_out.payload

    # 4) JUDIKATURA ENGINE
    jud_out: EngineOutput = judikatura_engine(
        EngineInput(
            context={
                "case": case_ctx,
                "use_llm": use_llm_flag,
            }
        )
    )
    jud_payload = jud_out.payload


    # 5) Sestavení finální odpovědi
    if mode == "short":
        final_text = _build_final_answer(
            user_query,
            core_payload,
            risk_payload,
            jud_payload,
            intent_payload,
        )
    else:
        final_text = _build_final_answer(
            user_query,
            core_payload,
            risk_payload,
            jud_payload,
            intent_payload,
        )

    # 6) Metadata + debug
    metadata: Dict[str, Any] = {
        "version": "orchestrator_v2",
        "mode": mode,
        "use_llm": use_llm_flag,
        "debug": debug,
        "raw": raw,
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "has_llm_error": bool(core_payload.get("llm_error")),
        "intent": intent_payload.get("intent"),
        "domain": intent_payload.get("domain"),
        "intent_confidence": intent_payload.get("confidence"),
    }

    if debug:
        metadata["engine_notes"] = {
            "core_legal": core_out.notes,
            "risk": risk_out.notes,
            "judikatura": jud_out.notes,
            "intent": intent_out.notes,
        }

    result: Dict[str, Any] = {
        "final_answer": final_text,
        "core_legal": core_out,
        "risk": risk_out,
        "judikatura": jud_out,
        "intent": intent_out,
        "metadata": metadata,
    }

    return result



# =====================================================================
#  Sekce builderů textu
# =====================================================================

def _build_final_answer(
    user_query: str,
    core: Dict[str, Any],
    risk: Dict[str, Any],
    jud: Dict[str, Any],
    intent_payload: Dict[str, Any],
) -> str:
    parts: List[str] = []

    # 1) Shrnutí – musí obsahovat přesně tenhle řádek kvůli testu
    parts.append("# 🧩 Shrnutí")
    parts.append(_build_summary_section(core, risk, jud))

    # 2) Právní analýza
    parts.append("\n## 📑 Právní analýza")
    parts.append(_build_irac_section(core))

    # 3) Judikatura
    parts.append("\n## ⚖️ Judikatura")
    parts.append(_build_judikatura_section(jud))

    # 4) Rizika
    parts.append("\n## ⚠️ Rizika a naléhavost")
    parts.append(_build_risk_section(risk))

    # 5) Doporučený postup  🔧 TADY OPRAVA
    parts.append("\n## 🧭 Doporučený další postup")
    parts.append(_build_steps_section(risk, intent_payload))  # <-- přidán intent_payload

    # 6) Co doplnit
    parts.append("\n## ❗ Co by bylo dobré doplnit")
    parts.append(_build_missing_facts_section(core, risk, jud))

    # 7) Další otázky pro klienta
    parts.append("\n## ❓ Další možné otázky")
    parts.append(_build_client_questions_section(core, risk, intent_payload))

    # 8) Nejistoty a limity analýzy
    parts.append("\n## 🧩 Nejistoty a limity analýzy")

    parts.append(
        _build_uncertainty_section(
            user_query,
            core,
            risk,
            intent_payload
        )
    )

    return "\n".join(parts)

# =====================================================================
#  Next quetions section
# =====================================================================

def _build_next_questions_section(
    user_query: str,
    risk: Dict[str, Any],
    jud: Dict[str, Any],
) -> str:
    """
    Návrhy na další otázky – adaptované podle intentu, domény a rizik.
    Cíl: pomoct uživateli formulovat další kroky / dotazy, aniž bychom
    přecházeli do konkrétní právní rady.
    """
    parts: List[str] = []

    # ⚠️ Nadpis držíme kvůli testům
    parts.append("## ❓ Další možné otázky")
    parts.append("")

    intent = risk.get("intent")
    domain = risk.get("domain")
    level = str(risk.get("level", "UNKNOWN")).upper()

    questions: List[str] = []

    # -------------------------
    # Intent-specifické otázky
    # -------------------------

    if intent == "school_dispute" or domain == "school":
        questions.extend(
            [
                "Jak konkrétně škola postupovala (časová osa kroků školy, OSPOD, ČŠI)?",
                "Zaznamenal(a) jsi někde písemně, co přesně bylo škole / OSPOD sděleno a kdy?",
                "Existují svědci (spolužáci, učitelé), kteří mohou popsat průběh událostí jinak?",
                "Chceš společně projít možnosti stížnosti na školu, zřizovatele nebo ČŠI?",
            ]
        )

    if intent == "criminal_defense" or domain == "criminal":
        questions.extend(
            [
                "Jaký je přesný procesní stav věci (podezřelý, obviněný, svědek)?",
                "Obdržel(a) jsi písemné poučení o právech a povinnostech? Máš ho k dispozici?",
                "Proběhl už výslech? Pokud ano, máš z něj záznam nebo protokol?",
                "Chceš si ujasnit rozdíl mezi právem nevypovídat a povinností vypovídat jako svědek?",
            ]
        )

    if intent == "inheritance" or domain == "inheritance":
        questions.extend(
            [
                "Jaká konkrétní rozhodnutí nebo zápisy notáře považuješ za problematické?",
                "Máš k dispozici kopie všech usnesení a zápisů z jednání u notáře?",
                "Chceš se zaměřit spíše na rozdělení podílů, nebo na postup notáře (procesní stránku)?",
                "Uvažuješ o stížnosti na notáře nebo o napadení usnesení u soudu?",
            ]
        )

    if intent == "complaint":
        questions.extend(
            [
                "Víš, jaká je lhůta pro podání stížnosti / odvolání v tvé konkrétní věci?",
                "Máš už sepsaný základní návrh stížnosti, nebo bys chtěl(a) pomoci strukturovat text?",
                "Je cílem stížnosti změna rozhodnutí, nebo spíš přezkum postupu úřadu / instituce?",
            ]
        )

    if intent == "document_check":
        questions.extend(
            [
                "Chceš projít celý dokument, nebo jen konkrétní sporné pasáže?",
                "Máš možnost poslat dokument v čitelné podobě (PDF / sken) a anonymizovat citlivé údaje?",
                "Je dokument už podepsaný, nebo se teprve rozhoduješ, zda ho podepsat?",
            ]
        )

    # -------------------------
    # Obecné otázky podle rizika
    # -------------------------

    if level in ("HIGH", "CRITICAL"):
        questions.extend(
            [
                "Co by pro tebe bylo nejhorší možné vyústění situace (scénář, kterého se nejvíc obáváš)?",
                "Jaké máš aktuálně časové lhůty nebo termíny, které nesmíš propásnout?",
                "Má někdo další v té věci formální roli (opatrovník, obhájce, zástupce školy, OSPOD)?",
            ]
        )
    elif level == "MEDIUM":
        questions.extend(
            [
                "Jaké dokumenty a záznamy máš už pohromadě a co ti ještě chybí?",
                "Chceš se zaměřit spíš na prevenci zhoršení situace, nebo na aktivní obranu?",
            ]
        )
    else:  # LOW / UNKNOWN
        questions.extend(
            [
                "Chceš spíš obecně pochopit právní rámec, nebo se zaměřit na konkrétní krok (doporučený postup)?",
                "Existuje někdo, kdo by mohl situaci zhoršit (proti strana, instituce), pokud nebudeš reagovat?",
            ]
        )

    # -------------------------
    # Fallback – obecné dotazy
    # -------------------------

    if not questions:
        questions.extend(
            [
                "Chceš přesněji sepsat fakta a časovou osu případu, aby šlo lépe posoudit situaci?",
                "Chceš se zaměřit na možnosti stížnosti / odvolání, nebo spíš na hledání smírného řešení?",
            ]
        )

    # Odstraníme duplicity při různých větvích
    deduped: List[str] = []
    for q in questions:
        if q not in deduped:
            deduped.append(q)

    for q in deduped:
        parts.append(f"- {q}")

    return "\n".join(parts)

# ---------------------------------------------------------------------
#  IRAC výstup
# ---------------------------------------------------------------------

def _build_irac_section(core: Dict[str, Any]) -> str:
    """
    Právní analýza jako IRAC:
    - Issues
    - Rules
    - Analysis
    - Conclusion
    """
    issues = core.get("issues") or []
    rules = core.get("rules") or []
    analysis = core.get("analysis") or []
    conclusion = core.get("conclusion") or {}

    parts: List[str] = []
    parts.append("## ⚖️ Právní analýza")

    # I – Issues
    parts.append("### 🧱 Hlavní právní otázky (Issues)")
    if issues:
        for item in issues:
            if isinstance(item, dict):
                label = item.get("label") or "Otázka"
                text = item.get("text") or ""
                parts.append(f"- **{label}** – {text}".rstrip())
            else:
                parts.append(f"- {item}")
    else:
        parts.append(
            "- Skeleton verze core_legal_engine – místo plné analýzy je zde pouze "
            "obecný popis hlavní právní otázky. Plná verze využívá LLM k přesnému "
            "pojmenování problému."
        )

    # R – Rules
    parts.append("\n### 📜 Relevantní právní úprava (Rules)")
    if rules:
        for r in rules:
            if isinstance(r, dict):
                label = r.get("label") or "Pravidlo"
                text = r.get("text") or r.get("raw_text") or ""
                parts.append(f"- **{label}** – {text}".rstrip())
            else:
                parts.append(f"- {r}")
    else:
        parts.append(
            "- V této skeleton verzi nejsou načtené konkrétní paragrafy. "
            "V plné verzi zde budou konkrétní ustanovení zákonů podle detekované "
            "právní domény."
        )

    # A – Analysis
    parts.append("\n### 🧠 Aplikace na konkrétní situaci (Analysis)")
    if analysis:
        if isinstance(analysis, list):
            for a in analysis:
                if isinstance(a, dict):
                    text = a.get("text") or ""
                    parts.append(f"- {text}".rstrip())
                else:
                    parts.append(f"- {a}")
        else:
            parts.append(str(analysis))
    else:
        parts.append(
            "- Na základě stručného popisu situace bude v plné verzi provedena "
            "aplikace právní úpravy na konkrétní fakta případu. Tahle skeleton "
            "verze jen drží strukturu pro budoucí výstup."
        )

    # C – Conclusion
    parts.append("\n### ✅ Závěr (Conclusion)")
    if isinstance(conclusion, dict):
        summary = conclusion.get("summary") or ""
        parts.append(summary or "- Závěr bude doplněn v plné verzi.")
    else:
        parts.append(str(conclusion))

    return "\n".join(parts)


# ---------------------------------------------------------------------
#  Shrnutí
# ---------------------------------------------------------------------

def _build_summary_section(core: Dict[str, Any], risk: Dict[str, Any], jud: Dict[str, Any]) -> str:
    """
    Shrnutí: orientační právní přehled + truth-layer info.

    - Uživateli jasně řekne, že jde o orientační výstup.
    - Přizná zdroje: skeleton / LLM hook, judikatura ano/ne, riziková úroveň.
    - Nepředstírá vyšší jistotu, než jaká plyne z payloadu.
    """
    meta = core.get("meta", {}) or {}
    domain = meta.get("domain", "unknown")
    intent = meta.get("intent", "unknown")
    llm_mode = meta.get("llm_mode", "skeleton")

    level = risk.get("level", "LOW")
    score = risk.get("score", 0)

    jud_status = jud.get("status", "NONE_FOUND")
    has_jud = bool(jud.get("matches") or jud.get("cases"))

    lines: List[str] = []
    lines.append("Tento výstup je **orientační právní přehled** založený na popisu situace, interní analýze a základních pravidlech pro posouzení rizik. Nejde o individuální právní službu ani závaznou právní radu.\n")

    # Riziko
    lines.append(f"- Orientační úroveň rizika: **{level}** (score: {score}).")

    # Intent / typ dotazu
    if intent != "unknown":
        lines.append(f"- Předběžný typ dotazu: **{intent}**.")
    else:
        lines.append("- Předběžný typ dotazu: **zatím nejednoznačný**.")

    # Doména
    if domain != "unknown":
        lines.append(f"- Předběžná právní oblast: **{domain}**.")
    else:
        lines.append("- Předběžná právní oblast: **neurčena / smíšená oblast**.")

    # LLM režim – truth layer
    if llm_mode == "conclusion_only":
        lines.append(
            "- Poznámka: LLM režim pro právní analýzu je aktivní pouze pro **formulaci závěru**. "
            "Zbytek struktury (otázky, právní úprava, analýza) zůstává v bezpečném skeleton režimu."
        )
    else:
        lines.append(
            "- Poznámka: LLM režim pro právní analýzu není aktivní – použita je bezpečná skeleton verze, "
            "která drží strukturu, ale nenahrazuje práci advokáta."
        )

    # Judikatura – přiznání zdrojů
    if has_jud and jud_status == "OK":
        lines.append(
            "- Judikatura: byly nalezeny **relevantní judikáty**, které podporují rámcový závěr. "
            "Detailní čísla spisů jsou uvedena v sekci Judikatura."
        )
    elif jud_status == "CONFLICT":
        lines.append(
            "- Judikatura: nalezen **konflikt v judikatuře** – existují rozhodnutí "
            "podporující různé směry výkladu. Je vhodné řešit s advokátem."
        )
    else:
        lines.append(
            "- Judikatura: k dotazu se nepodařilo najít konkrétní judikaturu, závěr je tedy "
            "více obecný a opřený hlavně o pravidla a analogii."
        )

    lines.append(
        "- V komplikovaných nebo emočně náročných případech je osobní konzultace s advokátem "
        "obvykle nejbezpečnější cestou."
    )

    return "\n".join(lines)


# ---------------------------------------------------------------------
#  Judikatura
# ---------------------------------------------------------------------

def _build_judikatura_section(jud: Dict[str, Any]) -> str:
    """
    Sekce judikatury – respektuje status:
    - NONE_FOUND
    - CONFLICT
    - OK
    """
    status = jud.get("status") or "NONE_FOUND"
    cases = jud.get("cases") or []
    conflict_info = jud.get("conflict_info") or {}

    parts: List[str] = []
    parts.append("## 📚 Judikatura")

    if status == "NONE_FOUND" or not cases:
        parts.append("K dotazu se nepodařilo najít relevantní judikaturu.")
        return "\n".join(parts)

    if status == "CONFLICT":
        parts.append("Byly nalezeny protichůdné judikáty:")
    else:
        parts.append("Byly nalezeny tyto relevantní judikáty:")

    for c in cases[:5]:
        ref = c.get("reference", "neznámá spisová značka")
        issue = c.get("legal_issue", "")
        holding = c.get("holding_summary", "")
        parts.append(f"- **{ref}** – {issue}. {holding}".rstrip())

    if conflict_info.get("conflict"):
        dirs = ", ".join(conflict_info.get("directions", []))
        parts.append(f"\n⚠️ Poznámka: judikatura je částečně konfliktní (směr: {dirs}).")

    return "\n".join(parts)


# ---------------------------------------------------------------------
#  Rizika
# ---------------------------------------------------------------------

def _build_risk_section(risk: Dict[str, Any]) -> str:
    """
    Sekce rizik – kombinuje:
    - celkovou úroveň rizika
    - základní dimenze z risk enginu
    """
    level = str(risk.get("level", "UNKNOWN"))
    score = risk.get("score", 0)
    flags = risk.get("flags", []) or []

    parts: List[str] = []
    parts.append("## ⚠️ Rizika a naléhavost")
    parts.append("")
    parts.append(f"- Úroveň rizika: **{level}** (score: {score})")

    dims: Dict[str, int] = risk.get("dimensions", {}) or {}
    if dims:
        parts.append("\n- Klíčové oblasti rizika:")
        for dim, val in dims.items():
            parts.append(f"  - {dim}: {val}")

    if flags:
        parts.append("\n- Signály z textu:")
        for f in flags:
            flag = f.get("flag")
            kws = f.get("keywords_hit") or []
            parts.append(f"  - {flag}: {', '.join(map(str, kws))}")

    return "\n".join(parts)



# ---------------------------------------------------------------------
#  Missing facts section
# ---------------------------------------------------------------------

def _build_missing_facts_section(core: Dict[str, Any], risk: Dict[str, Any], jud: Dict[str, Any]) -> str:
    meta = core.get("meta", {}) or {}
    intent = (meta.get("intent") or "").lower()
    domain = (meta.get("domain") or "").lower()

    flags = risk.get("flags", []) or []
    flag_names = {f.get("flag") for f in flags}
    dims = risk.get("dimensions", {}) or {}

    hints: List[str] = []

    # Procesní / lhůty
    if "deadline_sensitive" in flag_names or dims.get("procedural", 0) > 0:
        hints.append(
            "Upřesni, jaké **konkrétní lhůty** ti běží (do kdy lze podat odvolání, stížnost apod.) a kdy jsi obdržel/a poslední písemnost."
        )

    # Trestní oblast
    if dims.get("criminal", 0) > 0 or "trestn" in domain:
        hints.append(
            "Doplň, v jaké **fázi trestního řízení** se věc nachází (podezření, zahájení trestního stíhání, obžaloba, hlavní líčení…)."
        )

    # Dětský / školní rozměr
    if dims.get("child", 0) > 0 or domain in ("school", "family"):
        hints.append(
            "Napiš, jaké **písemné záznamy** existují (zápisy školy, zprávy OSPOD, rozhodnutí, e-maily) a zda jsi měl/a možnost se k nim vyjádřit."
        )

    # Dokument / smlouva
    if "document" in intent or "contract" in intent or "smlouv" in intent:
        hints.append(
            "Uveď, zda je dokument už **podepsaný**, kdo ho připravil a zda máš k dispozici **plné znění** (ne jen výřez)."
        )

    # Obecný fallback
    if not hints:
        hints = [
            "Upřesni, jaké máš k dispozici **dokumenty** (rozhodnutí, smlouvy, e-maily, zprávy).",
            "Popiš stručně **časovou osu** – co se stalo kdy, kdo ti co poslal nebo řekl.",
            "Napiš, jaký je tvůj **hlavní cíl** (čeho chceš dosáhnout – zrušení rozhodnutí, náhrada škody, ochrana dítěte…?).",
        ]

    return "\n".join(f"- {h}" for h in hints)



# ---------------------------------------------------------------------
#  Client questions section
# ---------------------------------------------------------------------

def _build_client_questions_section(
    core: Dict[str, Any],
    risk: Dict[str, Any],
    intent_payload: Optional[Dict[str, Any]] = None,
) -> str:
    """
    Sekce s návrhy otázek pro klienta.
    `intent_payload` je volitelný – pokud není, použijeme obecné otázky.
    """
    lines: List[str] = []

    lines.append(
        "- Chceš spíš obecně pochopit právní rámec, nebo se zaměřit na konkrétní krok (doporučený postup)?"
    )
    lines.append(
        "- Existuje někdo, kdo by mohl situaci zhoršit (proti strana, instituce), pokud nebudeš reagovat?"
    )

    # sem můžeš později přidat logiku podle intent_payload (např. jiné otázky pro 'document_check' apod.)

    return "\n".join(lines)



# ---------------------------------------------------------------------
#  Doporučení
# ---------------------------------------------------------------------

def _build_steps_section(
    risk: Dict[str, Any],
    intent_payload: Dict[str, Any],
) -> str:
    level = risk.get("level", "UNKNOWN")
    score = risk.get("score", "?")

    intent = intent_payload.get("intent", "general")
    domain = intent_payload.get("domain", "unknown")

    parts: List[str] = []

    parts.append(f"- Úroveň rizika: **{level}** (score: {score}).")
    parts.append(
        f"- Předběžný typ dotazu: **{intent}** / oblast: **{domain}**."
    )
    parts.append(
        "- Skelet doporučení: v plné verzi budou konkrétnější kroky "
        "(podání, lhůty, návrhy na důkazy). Zatím jen orientační nástin."
    )

    return "\n".join(parts)

    # skeleton disclaimer
    parts.append(
        "Skeleton verze: v plné verzi zde budou konkrétnější doporučené kroky "
        "(co teď můžeš udělat, jaká podání zvážit, kdy jít za advokátem)."
    )
    parts.append("")

    # ---- 1) Rámec podle úrovně rizika ----
    if level in ("HIGH", "CRITICAL"):
        parts.append(
            "Na základě vyhodnocení jako **vysoké riziko** je vhodné postupovat "
            "s maximální obezřetností a neodkládat další kroky."
        )
    elif level in ("MEDIUM",):
        parts.append(
            "Riziko je vyhodnoceno jako **střední** – situace není triviální a "
            "vyplatí se jí věnovat systematickou pozornost."
        )
    elif level in ("LOW",):
        parts.append(
            "Riziko je aktuálně hodnoceno jako spíše **nižší**, přesto je rozumné "
            "udržovat přehled o dokumentech a vývoji situace."
        )
    else:
        parts.append(
            "Úroveň rizika nebyla jednoznačně určena – doporučení níže ber jako "
            "orientační vodítka, ne jako závazný návod."
        )

    parts.append("")

    # ---- 2) Bezprostřední kroky podle typů rizik ----
    parts.append("### 1. Co má smysl řešit co nejdříve")

    # Procesní rizika – lhůty, odvolání, stížnosti
    if dims.get("procedural", 0) > 0 or intent in ("complaint",) or "administrative" in domain:
        parts.append(
            "- Zkontroluj přesné **lhůty pro odvolání, stížnosti nebo jiné podání** "
            "v poučení rozhodnutí nebo doprovodných dokumentech."
        )
        parts.append(
            "- Pokud si nejsi jistý/á výkladem lhůt, je vhodné se **rychle poradit s advokátem**, "
            "protože zmeškání lhůty může mít nevratné důsledky."
        )

    # Trestněprávní rovina
    if dims.get("criminal", 0) > 0 or intent == "criminal_defense" or domain == "criminal":
        parts.append(
            "- Pokud se věc týká **policie, trestního oznámení nebo obvinění**, "
            "zvaž, zda neposkytovat detailní výpovědi bez předchozí konzultace s obhájcem."
        )
        parts.append(
            "- Ujisti se, že rozumíš svým právům (právo nevypovídat, právo na obhájce, "
            "právo nahlížet do spisu)."
        )

    # Dítě / škola / nezletilí
    if (
        dims.get("child", 0) > 0
        or intent == "school_dispute"
        or domain in ("school", "family")
    ):
        parts.append(
            "- Pokud se situace týká **nezletilého / dítěte / školy**, začni si dělat "
            "**podrobné zápisky**: kdo, kdy, kde a co řekl nebo udělal."
        )
        parts.append(
            "- Ukládej veškerou komunikaci se školou, OSPOD nebo jinými institucemi "
            "(e-maily, dopisy, zápisy z jednání)."
        )

    # Dědictví / notář
    if intent == "inheritance" or domain == "inheritance":
        parts.append(
            "- U dědických věcí si uschovej veškerou korespondenci s notářem, usnesení, "
            "zápisy z jednání a podané stížnosti či námitky."
        )
        parts.append(
            "- Zvaž, zda není vhodné **písemně požádat o nahlédnutí do spisu** a vyžádat si "
            "kopie důležitých listin (zápisy z jednání, protokoly, podání ostatních účastníků)."
        )

    # Kontrola dokumentu / smlouvy
    if intent == "document_check":
        parts.append(
            "- Pokud chceš zkontrolovat **smlouvu nebo jiný dokument**, připrav si jeho kopii "
            "(ideálně v PDF nebo čitelné fotografii) a případně zvýrazni sporné pasáže."
        )
        parts.append(
            "- Před sdílením dokumentu s kýmkoli dalším zvaž anonymizaci citlivých údajů "
            "(rodné číslo, číslo OP, přesná adresa atd.)."
        )

    # Autority – soud, úřady, vedení školy
    if dims.get("authority", 0) > 0 or domain in ("school", "administrative"):
        parts.append(
            "- Veškerou komunikaci se soudem, úřadem nebo vedením školy se snaž vést "
            "písemně nebo si dělej detailní záznamy (datum, obsah, kdo byl přítomen)."
        )

    if not any(dims.values()) and intent == "general":
        # fallback pro případy s nízkým / neurčitým rizikem a bez specifik
        parts.append(
            "- Sepiš si stručně fakta a časovou osu situace – to je základ pro další "
            "práci s advokátem nebo pro další dotazy."
        )

    # ---- 3) Střednědobé kroky (1–4 týdny) ----
    parts.append("\n### 2. Co dále v horizontu 1–4 týdnů")
    parts.append(
        "- Shromažďuj a archivuj **důkazy**: dokumenty, e-maily, SMS, interní zápisy, "
        "vyjádření protistrany, případně svědecké kontakty."
    )

    # špetka specializace podle intentu/domainu
    if intent == "school_dispute" or domain == "school":
        parts.append(
            "- U školních sporů zjisti, jaké má škola **vnitřní předpisy** (řád školy, "
            "postupy řešení kázeňských přestupků) a zda je dodržuje."
        )
        parts.append(
            "- Zvaž možnost obrátit se na **ČŠI nebo zřizovatele školy**, pokud máš podezření "
            "na závažnější pochybení školy."
        )

    if intent == "complaint":
        parts.append(
            "- U stížností a odvolání si připrav **časovou osu** a přehled hlavních pochybení, "
            "ať můžeš jasně formulovat, co konkrétně napadáš."
        )

    if intent == "inheritance" or domain == "inheritance":
        parts.append(
            "- U dědického řízení zvaž, zda se neporadit s advokátem, pokud máš pocit, že "
            "postup notáře není nestranný nebo dostatečně srozumitelný."
        )

    # ---- 4) Kdy je vhodné bezodkladně za advokátem ----
    parts.append("\n### 3. Kdy už je vhodné neotálet s právníkem")

    if level in ("HIGH", "CRITICAL") or dims.get("criminal", 0) > 0 or intent == "criminal_defense":
        parts.append(
            "- Pokud jsi obdržel(a) **obvinění, zahájení trestního stíhání, návrh na opatření "
            "vůči dítěti nebo rozhodnutí s krátkou lhůtou**, je rozumné **bezodkladně** "
            "vyhledat advokáta."
        )
    else:
        parts.append(
            "- Pokud začne přibývat písemností, výzev, předvolání nebo se situace subjektivně "
            "zhoršuje, je lepší zapojit odborníka dříve než později."
        )

    parts.append(
        "\nTato doporučení jsou obecná a orientační. Nenahrazují individuální právní "
        "poradenství – složitější nebo vyhrocené případy je vždy vhodné řešit s advokátem."
    )

    return "\n".join(parts)



# ---------------------------------------------------------------------
#  Uncertainty section
# ---------------------------------------------------------------------

def _build_uncertainty_section(
    user_query: str,
    core: Dict[str, Any],
    risk: Dict[str, Any],
    intent: Dict[str, Any]
) -> str:
    missing = []

    # Pokud analýza nic nedokázala určit
    if core.get("llm_error"):
        missing.append("LLM nebylo dostupné → chybí plná právní analýza.")

    # Pokud risk engine nenašel žádné klíčové signály
    if risk.get("score", 0) == 0:
        missing.append("Popis neobsahuje žádné konkrétní časové nebo procesní údaje.")

    # Pokud intent_engine nerozpoznal záměr klienta
    if intent.get("confidence", 0) < 0.3:
        missing.append("Z popisu není jasný účel dotazu (obrana, nárok, stížnost, dokument).")

    if not missing:
        return "V této chvíli nebyly identifikovány žádné zásadní nejistoty."

    return "- " + "\n- ".join(missing)