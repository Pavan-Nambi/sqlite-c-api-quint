#!/usr/bin/env python3
"""Generate canonical ITF traces for Quint trace replay harnesses."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from trace_scenarios import FAMILY_TRACES, wrap_states


def write_family(family: str, out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    for scenario in sorted(FAMILY_TRACES[family]):
        payload = wrap_states(scenario)
        out_path = out_dir / f"{scenario}.itf.json"
        out_path.write_text(json.dumps(payload, indent=2) + "\n")
        print(f"wrote {out_path}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--out-dir",
        type=Path,
        default=Path(__file__).resolve().parent / "traces",
        help="Output directory for generated *.itf.json traces",
    )
    parser.add_argument(
        "--family",
        choices=["all", "lifecycle", "serde", "stmt"],
        default="all",
        help="Which trace family to generate",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    for family in ("serde", "lifecycle", "stmt"):
        if args.family in {"all", family}:
            write_family(family, args.out_dir)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
