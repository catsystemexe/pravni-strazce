#!/usr/bin/env python
"""
Interaktivní demo pro Právní Strážce.

- používá runtime.orchestrator.run_pipeline
- podporuje LLM on/off (přes env + přepínání v CLI)
- zobrazuje hlavní odpověď + stručné debug info (risk, judikatura, core_legal)
"""

import os
from typing import Any, Dict

from runtime.orchestrator import run_pipeline


def _llm_enabled() -> bool:
    """Zjistí, zda je LLM povoleno přes env proměnnou."""
    return (
        os.getenv("CORE_LEGAL_USE_LLM", "").lower() in ("1", "true", "yes")
        or os.getenv("PIPELINE_USE_LLM", "").lower() in ("1", "true", "yes")
    )


def _extract_payload(maybe_engine: Any) -> Dict[str, Any]:
    """
    Bezpečně vytáhne payload z EngineOutput nebo dictu.
    Vrací vždy dict (může být prázdný).
    """
    if hasattr(maybe_engine, "payload"):
        try:
            return maybe_engine.payload  # type: ignore[attr-defined]
        except Exception:
            return {}
    if isinstance(maybe_engine, dict):
        return maybe_engine.get("payload", {})
    return {}


def main() -> None:
    print("=== Právní Strážce – DEMO ===")
    print("Prázdný dotaz = konec.\n")

    # výchozí režim – podle env (don.sh/doff.sh)
    use_llm = _llm_enabled()
    print(f"(Start: LLM režim podle env = {'ON' if use_llm else 'OFF'})\n")

    while True:
        print(f"[REŽIM] LLM: {'ON' if use_llm else 'OFF'}")
        user_query = input("Dotaz> ").strip()

        # speciální příkazy v CLI
        cmd = user_query.lower()
        if cmd in ("llm on", ":llm on"):
            use_llm = True
            print("→ LLM režim přepnut na: ON\n")
            continue
        if cmd in ("llm off", ":llm off"):
            use_llm = False
            print("→ LLM režim přepnut na: OFF\n")
            continue
        if cmd in ("llm", ":llm"):
            use_llm = not use_llm
            print(f"→ LLM režim přepnut na: {'ON' if use_llm else 'OFF'}\n")
            continue

        if not user_query:
            print("Konec.")
            break

        # nastavení env pro enginy (core_legal, orchestrator, judikatura…)
        if use_llm:
            os.environ["CORE_LEGAL_USE_LLM"] = "1"
            os.environ["PIPELINE_USE_LLM"] = "1"
        else:
            os.environ.pop("CORE_LEGAL_USE_LLM", None)
            os.environ.pop("PIPELINE_USE_LLM", None)

        # spuštění pipeline
        result = run_pipeline(
            user_query=user_query,
            use_llm=use_llm,
            mode="full",
            debug=False,
            raw=False,
        )

        final_answer = result.get("final_answer", "").strip()

        core = _extract_payload(result.get("core_legal"))
        risk = _extract_payload(result.get("risk"))
        jud = _extract_payload(result.get("judikatura"))

        # --- Výstup ---
        print("\n==============================")
        print("=== 📌 HLAVNÍ ODPOVĚĎ ===\n")
        if final_answer:
            print(final_answer)
        else:
            print("(Žádná final_answer ve výstupu.)")

        # --- Risk engine ---
        if risk:
            level = risk.get("level", "UNKNOWN")
            score = risk.get("score", "?")
            print("\n--- ⚠️ Rizikovost ---")
            print(f"Úroveň: {level}, skóre: {score}")

        # --- Judikatura ---
        if jud:
            status = jud.get("status", "UNKNOWN")
            matches = jud.get("matches") or jud.get("cases") or []
            print("\n--- ⚖️ Judikatura ---")
            print(f"Status: {status}")
            if matches:
                for idx, c in enumerate(matches[:2], start=1):
                    ref = c.get("reference") or c.get("id") or "bez ref."
                    court = c.get("court_level") or "?"
                    issue = c.get("legal_issue") or ""
                    print(f"  {idx}. [{court}] {ref} – {issue}")
            else:
                print("  (Žádné nalezené judikáty.)")

        # --- Core legal (stručné info) ---
        if core:
            meta = core.get("meta", {})
            domain = meta.get("domain", "unknown")
            intent = meta.get("intent", "unknown")
            llm_mode = meta.get("llm_mode", "skeleton")

            print("\n--- 🧠 Core legal ---")
            print(f"Doména: {domain}, intent: {intent}, režim: {llm_mode}")

            conclusion = core.get("conclusion") or {}
            summary = conclusion.get("summary")
            if summary:
                print("\nShrnutí závěru (core_legal):")
                print(summary)

        print("\n==============================\n")


if __name__ == "__main__":
    main()