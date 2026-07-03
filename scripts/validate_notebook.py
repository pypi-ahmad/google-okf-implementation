"""Validate tutorial notebook structure and required coverage topics."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_PATH = PROJECT_ROOT / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""

    parser = argparse.ArgumentParser(description="Validate a tutorial notebook.")
    parser.add_argument(
        "notebook_path",
        nargs="?",
        default="notebooks/tutorial.ipynb",
        help="Path to notebook file.",
    )
    parser.add_argument(
        "--skip-compile",
        action="store_true",
        help="Skip syntax checks for code cells.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print machine-readable JSON output.",
    )
    return parser.parse_args()


def main() -> int:
    """Run notebook validation and return process exit code."""

    args = parse_args()
    from enterprise_okf_ai.docs.notebook_validator import validate_notebook

    result = validate_notebook(
        notebook_path=args.notebook_path,
        compile_code_cells=not args.skip_compile,
    )

    if args.json:
        print(json.dumps(result.to_dict(), indent=2, sort_keys=True))
    else:
        print(f"Notebook: {result.notebook_path}")
        print(f"Passed: {result.passed}")
        print(f"Stats: {result.stats}")
        if result.warnings:
            print("Warnings:")
            for warning in result.warnings:
                print(f"- {warning}")
        if result.errors:
            print("Errors:")
            for error in result.errors:
                print(f"- {error}")

    return 0 if result.passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
