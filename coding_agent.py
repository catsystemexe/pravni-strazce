import os
import json
import textwrap
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI

# Načtení .env (OPENAI_API_KEY)
load_dotenv()
client = OpenAI()

REPO_ROOT = Path(__file__).parent.resolve()
CONFIG_PATH = REPO_ROOT / "agent_config.json"


def load_config():
    if not CONFIG_PATH.exists():
        raise FileNotFoundError(f"agent_config.json nenalezen v {CONFIG_PATH}")
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def should_skip_dir(path: Path, exclude_paths):
    for ex in exclude_paths:
        if ex and ex in path.parts:
            return True
    return False


def collect_repo_structure(config):
    include_ext = set(config.get("include_extensions", []))
    exclude_paths = config.get("exclude_paths", [])
    max_files = int(config.get("max_files", 10))
    max_chars = int(config.get("max_chars_per_file", 8000))

    structure_lines = []
    selected_files = []

    for root, dirs, files in os.walk(REPO_ROOT):
        root_path = Path(root)
        if should_skip_dir(root_path, exclude_paths):
            dirs[:] = []
            continue

        rel_root = root_path.relative_to(REPO_ROOT)
        structure_lines.append(f"[DIR] {rel_root if rel_root != Path('.') else '.'}")

        for name in files:
            file_path = root_path / name
            rel_file = file_path.relative_to(REPO_ROOT)

            if include_ext and file_path.suffix not in include_ext:
                continue

            structure_lines.append(f"  - {rel_file}")

            if len(selected_files) < max_files:
                selected_files.append(file_path)

    structure_text = "\n".join(structure_lines)

    files_text_blocks = []
    for fp in selected_files:
        try:
            with open(fp, "r", encoding="utf-8") as f:
                content = f.read()
        except UnicodeDecodeError:
            continue

        if len(content) > max_chars:
            content = content[:max_chars] + "\n\n[... obsah zkrácen ...]"

        rel = fp.relative_to(REPO_ROOT)
        block = f"----- FILE: {rel} -----\n{content}"
        files_text_blocks.append(block)

    files_text = "\n\n".join(files_text_blocks)

    return structure_text, files_text


def build_prompt(user_task: str, structure_text: str, files_text: str, config):
    lang = config.get("language", "cs")

    header = textwrap.dedent(f"""
    Kontext:
    - Jsi expertní právní asistent pro projekt Právní strážce.
    - Pracuješ nad tímto konkrétním repozitářem (domény, intents, slovníky, šablony).
    - Neprovádíš zápisy do souborů, pouze navrhuješ konkrétní kroky.

    Jazyk odpovědi:
    - Preferovaný jazyk: {lang}

    Úkol od uživatele:
    {user_task}

    Nejprve:
    - Stručně shrň, co chápeš ze struktury projektu.
    Poté:
    - Navrhni konkrétní kroky (1,2,3...) zaměřené na architekturu, domény, intent slovníky nebo šablony.
    - Pokud něco není jasné, explicitně popiš, co ti chybí.
    """)

    repo_info = textwrap.dedent(f"""
    === STRUKTURA REPOZITÁŘE ===
    {structure_text}

    === OBSAH VYBRANÝCH SOUBORŮ ===
    {files_text}
    """)

    full_input = header + "\n\n" + repo_info
    return full_input


def run_agent(user_task: str):
    config = load_config()
    system_instructions = config.get("system_instructions", "")
    model = config.get("model", "gpt-5.1")

    structure_text, files_text = collect_repo_structure(config)
    full_input = build_prompt(user_task, structure_text, files_text, config)

    response = client.responses.create(
        model=model,
        instructions=system_instructions,
        input=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "input_text",
                        "text": full_input
                    }
                ]
            }
        ]
    )

    output = response.output_text

    # 🔹 ZÁPIS REPORTU DO /out/last_agent_report.md
    out_dir = REPO_ROOT / "out"
    out_dir.mkdir(exist_ok=True)
    report_path = out_dir / "last_agent_report.md"
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(output)

    # a zároveň print do logu
    print("=" * 80)
    print("ODPOVĚĎ CODING AGENTA:\n")
    print(output)
    print("=" * 80)

    return output


def main():
    import argparse

    parser = argparse.ArgumentParser(
        description="Minimalní coding/analysis agent pro projekt Právní strážce."
    )
    parser.add_argument(
        "task",
        nargs="*",
        help="Úkol pro agenta (např. 'Navrhni strukturu master doménového katalogu')."
    )
    args = parser.parse_args()

    if args.task:
        user_task = " ".join(args.task)
    else:
        print("Zadej úkol pro agenta (např. 'Analyzuj strukturu a navrhni domény'):")
        user_task = input("> ").strip()

    if not user_task:
        print("Nebyl zadán žádný úkol, končím.")
        return

    run_agent(user_task)


if __name__ == "__main__":
    main()
