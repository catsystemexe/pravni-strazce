#!/usr/bin/env python
from __future__ import annotations

import json
from pathlib import Path


def main() -> None:
    # root repo:  .../pravni-strazce/
    repo_root = Path(__file__).resolve().parents[1]

    src_dir = repo_root / "data" / "_source" / "domains" / "traffic_law" / "intents"
    dst_dir = repo_root / "data" / "intents" / "traffic_law"

    if not src_dir.is_dir():
        print(f"[bootstrap_traffic_law] SOURCE dir not found: {src_dir}")
        return

    dst_dir.mkdir(parents=True, exist_ok=True)

    copied = 0
    skipped = 0

    for src_path in sorted(src_dir.glob("*.json")):
        dst_path = dst_dir / src_path.name

        # načti zdroj
        try:
            raw = src_path.read_text(encoding="utf-8")
            data = json.loads(raw)
        except Exception as exc:
            print(f"[bootstrap_traffic_law] !! ERROR reading {src_path}: {exc}")
            skipped += 1
            continue

        # zajisti, že doména je traffic_law (když chybí, doplníme)
        if "domain" not in data:
            data["domain"] = "traffic_law"
        elif data["domain"] != "traffic_law":
            print(
                f"[bootstrap_traffic_law] WARNING: intent {src_path.name} "
                f"má domain={data['domain']} (čekám traffic_law)"
            )

        # zapiš do runtime adresáře – jednoduchý "copy + normalize"
        new_text = json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True)

        # pokud existuje stejný obsah, nezapisuj zbytečně
        if dst_path.exists():
            try:
                old_text = dst_path.read_text(encoding="utf-8")
            except Exception:
                old_text = ""
            if old_text == new_text:
                skipped += 1
                continue

        dst_path.write_text(new_text, encoding="utf-8")
        copied += 1
        print(f"[bootstrap_traffic_law] updated: {dst_path.relative_to(repo_root)}")

    print(
        f"[bootstrap_traffic_law] DONE – updated={copied}, unchanged={skipped}, "
        f"source_dir={src_dir}"
    )


if __name__ == "__main__":
    main()
