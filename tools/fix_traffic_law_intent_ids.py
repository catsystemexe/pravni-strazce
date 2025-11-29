#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path

# Kořen repozitáře = parent adresář tools/
REPO_ROOT = Path(__file__).resolve().parents[1]
TRAFFIC_RUNTIME_DIR = REPO_ROOT / "data" / "intents" / "traffic_law"


def fix_traffic_law_intent_ids() -> int:
    if not TRAFFIC_RUNTIME_DIR.exists():
        print(f"[ERROR] Traffic-law runtime dir does not exist: {TRAFFIC_RUNTIME_DIR}")
        return 1

    changed = 0

    for path in sorted(TRAFFIC_RUNTIME_DIR.glob("*.json")):
        try:
            raw = path.read_text(encoding="utf-8")
            data = json.loads(raw)
        except Exception as e:  # noqa: BLE001
            print(f"[ERROR] {path}: cannot parse JSON: {e}")
            continue

        intent_id = data.get("intent_id")
        if not isinstance(intent_id, str):
            print(f"[WARN] {path}: missing or non-str intent_id, skipping")
            continue

        # Už je v pořádku
        if intent_id.startswith("traffic_law_"):
            print(f"[OK]   {path.name}: intent_id already has prefix ({intent_id})")
            continue

        new_id = f"traffic_law_{intent_id}"
        data["intent_id"] = new_id

        # Přepíšeme soubor pěkně formátovaným JSONem
        path.write_text(
            json.dumps(data, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        changed += 1
        print(f"[FIX]  {path.name}: '{intent_id}' -> '{new_id}'")

    if changed == 0:
        print(f"[INFO] No intent_id needed prefix fix in {TRAFFIC_RUNTIME_DIR}")
    else:
        print(f"[INFO] Fixed {changed} intents in {TRAFFIC_RUNTIME_DIR}")

    return 0


if __name__ == "__main__":
    raise SystemExit(fix_traffic_law_intent_ids())
