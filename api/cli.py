from __future__ import annotations

import sys
from textwrap import dedent

from runtime.orchestrator import run_pipeline


def main() -> None:
    """
    Jednoduché CLI pro Právního strážce.

    Použití:
      python -m api.cli "Můj dotaz..."
    nebo bez argumentu:
      python -m api.cli
      (dotaz se zadá přes input() a ukončí Enterem)
    """
    if len(sys.argv) > 1:
        user_query = " ".join(sys.argv[1:])
    else:
        user_query = input("Zadej právní dotaz: ").strip()

    if not user_query:
        print("⚠️ Nebyl zadán žádný dotaz.")
        sys.exit(1)

    res = run_pipeline(user_query)
    answer = res.get("final_answer", "").strip()

    header = dedent(
        """
        =====================================
        🛡  PRÁVNÍ STRÁŽCE – VÝSTUP PIPELINY
        =====================================
        """
    ).strip()

    print(header)
    print()
    print(answer)


if __name__ == "__main__":
    main()