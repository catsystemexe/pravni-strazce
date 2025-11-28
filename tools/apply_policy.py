#!/usr/bin/env python
"""
apply_policy.py

Automaticky přidá GLOBAL a GROUP policy bloky do promptů (*.md)
pro jednotlivé enginy (core_legal, risk, intent, judikatura).

- Policy soubory se očekávají v: prompts/policy/
- Prompty se očekávají v:
    - engines/core_legal/prompts/
    - engines/risk/prompts/
    - engines/intent/prompts/
    - engines/judikatura/prompts/

Použití:
    python tools/apply_policy.py --dry-run   # jen vypíše, co by změnil
    python tools/apply_policy.py             # skutečně upraví soubory
"""

import argparse
import sys
from pathlib import Path
from typing import Dict, List, Tuple


# -----------------------------
# Konfigurace cest
# -----------------------------

REPO_ROOT = Path(__file__).resolve().parents[1]

POLICY_DIR = REPO_ROOT / "prompts" / "policy"

POLICY_FILES = {
    "global": "policy_global.md",
    "core_legal": "policy_core_legal.md",
    "risk": "policy_risk_engine.md",
    "intent": "policy_intent_engine.md",
    "judikatura": "policy_judikatura_engine.md",
}

# Mapování skupin na složky s prompty
GROUP_DIRECTORIES = {
    "core_legal": [REPO_ROOT / "engines" / "core_legal" / "prompts"],
    "risk": [REPO_ROOT / "engines" / "risk" / "prompts"],
    "intent": [REPO_ROOT / "engines" / "intent" / "prompts"],
    "judikatura": [REPO_ROOT / "engines" / "judikatura" / "prompts"],
}


# -----------------------------
# Pomocné funkce
# -----------------------------


def load_policy(name: str) -> str:
    """
    Načte obsah policy souboru dle logického jména ("global", "core_legal", ...).
    """
    filename = POLICY_FILES.get(name)
    if not filename:
        raise ValueError(f"Neznámý název policy: {name}")

    path = POLICY_DIR / filename
    if not path.is_file():
        raise FileNotFoundError(f"Policy soubor nenalezen: {path}")

    return path.read_text(encoding="utf-8").strip() + "\n\n"


def policy_already_present(content: str, marker: str) -> bool:
    """
    Jednoduchá detekce: jestli už v souboru je daný policy blok.

    Používáme rozpoznatelný nadpis, např.:
    - "GLOBAL POLICY – e-Advokát (baseline)"
    - "CORE LEGAL POLICY – právní jádro (IRAC)"
    atd.
    """
    return marker in content


def find_prompt_files(group_dirs: List[Path]) -> List[Path]:
    """
    Najde všechny .md soubory v daných složkách (rekurzivně).
    """
    files: List[Path] = []
    for base in group_dirs:
        if not base.exists():
            continue
        for path in base.rglob("*.md"):
            # ignorujeme samotné policy soubory (pro jistotu)
            if "prompts/policy" in str(path).replace("\\", "/"):
                continue
            files.append(path)
    return files


# -----------------------------
# Hlavní aplikační logika
# -----------------------------


def apply_policies_to_file(
    path: Path,
    global_policy: str,
    group_policy: str,
    dry_run: bool = True,
) -> Tuple[bool, List[str]]:
    """
    Aplikuje global + group policy na jeden soubor.

    Vrací:
        (changed, actions)
        - changed: True pokud by došlo k úpravě
        - actions: seznam textových popisů, co se změnilo
    """
    text = path.read_text(encoding="utf-8")

    actions: List[str] = []
    changed = False

    # Kontrolní markery (abychom nepřidali policy 2x)
    GLOBAL_MARKER = "GLOBAL POLICY – e-Advokát"
    CORE_MARKER = "CORE LEGAL POLICY –"
    RISK_MARKER = "RISK ENGINE POLICY –"
    INTENT_MARKER = "INTENT ENGINE POLICY –"
    JUDIK_MARKER = "JUDIKATURA ENGINE POLICY –"

    # Global policy
    if not policy_already_present(text, GLOBAL_MARKER):
        text = global_policy + text
        actions.append("přidána GLOBAL policy")
        changed = True

    # Group policy
    group_marker = None
    if "CORE LEGAL POLICY" in group_policy:
        group_marker = CORE_MARKER
    elif "RISK ENGINE POLICY" in group_policy:
        group_marker = RISK_MARKER
    elif "INTENT ENGINE POLICY" in group_policy:
        group_marker = INTENT_MARKER
    elif "JUDIKATURA ENGINE POLICY" in group_policy:
        group_marker = JUDIK_MARKER

    if group_marker and not policy_already_present(text, group_marker):
        # vložíme group policy hned za global policy (pokud byla přidaná),
        # nebo na úplný začátek (pokud global už byla).
        if policy_already_present(text, GLOBAL_MARKER):
            # najdeme konec prvního výskytu global markeru (tj. začátek global policy)
            # a vložíme group policy za něj.
            # Zjednodušeně: global_policy jsme právě nalepili na začátek,
            # takže můžeme vzít text ve tvaru: [global][zbytek]
            # → global_policy známe, má fixní délku.
            text = global_policy + group_policy + text[len(global_policy):]
        else:
            text = group_policy + text

        actions.append("přidána GROUP policy")
        changed = True

    if changed and not dry_run:
        path.write_text(text, encoding="utf-8")

    return changed, actions


def main(argv: List[str]) -> int:
    parser = argparse.ArgumentParser(description="Apply global/group policy to prompts.")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Pouze vypíše plánované změny, ale neupraví soubory.",
    )
    args = parser.parse_args(argv)

    try:
        global_policy = load_policy("global")
    except Exception as e:
        print(f"[ERROR] Nepodařilo se načíst global policy: {e}", file=sys.stderr)
        return 1

    # Načteme group policy texty dopředu
    group_policies: Dict[str, str] = {}
    for group_name in ("core_legal", "risk", "intent", "judikatura"):
        try:
            group_policies[group_name] = load_policy(group_name)
        except FileNotFoundError:
            # Pokud group policy neexistuje, jen ji přeskočíme
            print(f"[WARN] Chybí group policy pro {group_name}, přeskočeno.")
        except Exception as e:
            print(f"[ERROR] Chyba při načítání policy pro {group_name}: {e}", file=sys.stderr)

    any_changes = False

    for group_name, dirs in GROUP_DIRECTORIES.items():
        if group_name not in group_policies:
            continue

        group_policy = group_policies[group_name]
        prompt_files = find_prompt_files(dirs)

        if not prompt_files:
            continue

        print(f"\n=== Skupina: {group_name} ===")
        print(f"Nalezeno promptů: {len(prompt_files)}")

        for path in prompt_files:
            changed, actions = apply_policies_to_file(
                path,
                global_policy=global_policy,
                group_policy=group_policy,
                dry_run=args.dry_run,
            )
            if changed:
                any_changes = True
                rel = path.relative_to(REPO_ROOT)
                if args.dry_run:
                    print(f"[DRY-RUN] {rel} → {', '.join(actions)}")
                else:
                    print(f"[UPDATED] {rel} → {', '.join(actions)}")

    if not any_changes:
        print("\nŽádné soubory nebyly změněny (vše už má global + group policy nebo žádné prompty nenalezeny).")
    else:
        if args.dry_run:
            print("\nDRY-RUN hotov – žádné soubory nebyly fyzicky upraveny.")
        else:
            print("\nHotovo – policy byly aplikovány.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))