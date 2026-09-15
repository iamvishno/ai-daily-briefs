#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys
from datetime import date
from pathlib import Path


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
SOURCE_ROOT = REPOSITORY_ROOT / "src"
if str(SOURCE_ROOT) not in sys.path:
    sys.path.insert(0, str(SOURCE_ROOT))

from ai_daily_brief.runner import run_daily  # noqa: E402


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Create one validated daily AI brief.")
    parser.add_argument(
        "--root",
        type=Path,
        default=REPOSITORY_ROOT,
        help="Repository root. Defaults to the directory above this script.",
    )
    parser.add_argument(
        "--date",
        type=date.fromisoformat,
        help="Override the UK date for local testing. Automated runs do not use this option.",
    )
    parser.add_argument(
        "--fixture",
        type=Path,
        help="Read an offline RSS/Atom fixture instead of contacting live sources.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate and print the proposed post without changing files.",
    )
    parser.add_argument(
        "--strict-ai",
        action="store_true",
        help="Fail instead of using the conservative fallback when Gemini is unavailable.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        path, result = run_daily(
            root=args.root,
            run_date=args.date,
            fixture_path=args.fixture,
            dry_run=args.dry_run,
            strict_ai=args.strict_ai,
        )
    except (FileExistsError, KeyError, OSError, RuntimeError, ValueError) as exc:
        print(f"Daily brief failed: {exc}", file=sys.stderr)
        return 1

    if args.dry_run:
        print(result)
        if path:
            print(f"\nProposed path: {path.relative_to(args.root.resolve()).as_posix()}")
    else:
        print(result)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
