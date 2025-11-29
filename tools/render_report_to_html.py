#!/usr/bin/env python
# tools/render_report_to_html.py

from pathlib import Path
from datetime import datetime
import argparse
import html


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Zabalí textový report coding agenta do HTML a uloží latest + timestampovaný log."
    )
    parser.add_argument(
        "--mode",
        choices=["analysis", "fix", "check"],
        required=True,
        help="Režim běhu: analysis, fix nebo check.",
    )
    parser.add_argument(
        "--task",
        required=True,
        help="Popis úkolu, který byl předán coding agentovi (pro hlavičku logu).",
    )
    parser.add_argument(
        "--input",
        required=True,
        help="Cesta k textovému reportu od coding agenta (např. tmp/last_report.txt).",
    )
    parser.add_argument(
        "--output-root",
        default="docs/logs",
        help="Kořenový adresář pro HTML logy (default: docs/logs).",
    )
    args = parser.parse_args()

    # Načti surový text reportu
    input_path = Path(args.input)
    if not input_path.exists():
        raise SystemExit(f"Input report not found: {input_path}")

    raw_text = input_path.read_text(encoding="utf-8")

    # Timestamp v UTC – vhodný do názvu souboru
    ts = datetime.utcnow().strftime("%Y-%m-%dT%H%M%SZ")

    # Cílová složka pro daný režim (analysis / fix / check)
    mode_dir = Path(args.output_root) / args.mode
    mode_dir.mkdir(parents=True, exist_ok=True)

    # Krátká hlavička uvnitř <pre> – typ běhu, čas, úkol
    header_lines = [
        f"Run type : {args.mode.upper()}",
        f"Timestamp (UTC) : {ts}",
        f"Task : {args.task}",
        "-" * 72,
        "",
    ]
    header_text = "\n".join(header_lines)

    # Escapovaný obsah, aby HTML nerozbil speciální znaky
    escaped_body = html.escape(header_text + raw_text)

    pre_block = f"<pre>{escaped_body}</pre>"

    # Jednotná jednoduchá šablona pro všechny logy
    html_doc = f"""<!DOCTYPE html>
<html lang="cs">
<head>
    <meta charset="UTF-8">
    <title>Právní strážce – {args.mode} run ({ts})</title>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        body {{
            font-family: system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
            margin: 2rem;
            line-height: 1.5;
            background: #0f172a;
            color: #e5e7eb;
        }}
        pre {{
            white-space: pre-wrap;
            word-wrap: break-word;
            background: #020617;
            padding: 1.5rem;
            border-radius: 0.75rem;
            border: 1px solid #1f2937;
            box-shadow: 0 10px 30px rgba(0,0,0,0.5);
        }}
        h1 {{
            font-size: 1.5rem;
            margin-bottom: 1rem;
        }}
        .meta {{
            font-size: 0.85rem;
            color: #9ca3af;
            margin-bottom: 0.5rem;
        }}
    </style>
</head>
<body>
    <h1>Právní strážce – {args.mode.upper()} run</h1>
    <div class="meta">
        Tento soubor generuje GitHub Action z repozitáře catsystemexe/pravni-strazce.
        (UTC: {ts})
    </div>
    {pre_block}
</body>
</html>
"""

    # 1) Timestampovaný log – archiv
    timestamp_filename = f"{ts}_{args.mode}.html"
    timestamp_path = mode_dir / timestamp_filename
    timestamp_path.write_text(html_doc, encoding="utf-8")

    # 2) latest.html pro daný režim
    latest_mode_path = mode_dir / "latest.html"
    latest_mode_path.write_text(html_doc, encoding="utf-8")

    # 3) Globální alias docs/last_report.html – „poslední cokoliv“
    docs_dir = Path("docs")
    docs_dir.mkdir(parents=True, exist_ok=True)
    global_latest_path = docs_dir / "last_report.html"
    global_latest_path.write_text(html_doc, encoding="utf-8")

    print(f"Written mode log:      {timestamp_path}")
    print(f"Updated mode latest:   {latest_mode_path}")
    print(f"Updated global latest: {global_latest_path}")


if __name__ == "__main__":
    main()
