#!/usr/bin/env python3
"""Fail when C probe traces violate documented Quint deserialize BUSY claims."""

from __future__ import annotations

import sys


REQUIRED_CASES = {
    "deserialize-read-transaction-busy",
    "deserialize-backup-source-busy",
}


def parse(lines: list[str]) -> tuple[set[str], list[tuple[str, str, frozenset[str]]]]:
    cases_seen: set[str] = set()
    mismatches: list[tuple[str, str, frozenset[str]]] = []

    for line_number, raw_line in enumerate(lines, 1):
        line = raw_line.strip()
        if not line:
            continue
        parts = line.split()
        if parts[0] == "case":
            if len(parts) != 2:
                raise ValueError(f"line {line_number}: malformed case line")
            case_name = parts[1]
            if case_name not in REQUIRED_CASES:
                raise ValueError(f"line {line_number}: unknown case {case_name}")
            if case_name in cases_seen:
                raise ValueError(f"line {line_number}: duplicate case {case_name}")
            cases_seen.add(case_name)
            continue
        if parts[0] == "diverge":
            if len(parts) < 4:
                raise ValueError(f"line {line_number}: malformed diverge line")
            case_name = parts[1]
            event = parts[2]
            facts = frozenset(parts[3:])
            if case_name not in REQUIRED_CASES:
                raise ValueError(f"line {line_number}: unknown divergence {case_name}")
            malformed = sorted(fact for fact in facts if "=" not in fact)
            if malformed:
                raise ValueError(
                    f"line {line_number}: malformed facts: " + ", ".join(malformed)
                )
            mismatches.append((case_name, event, facts))
            continue
        raise ValueError(f"line {line_number}: unexpected line: {line}")

    missing_cases = sorted(REQUIRED_CASES - cases_seen)
    if missing_cases:
        raise ValueError("missing cases: " + ", ".join(missing_cases))
    return cases_seen, mismatches


def check(mismatches: list[tuple[str, str, frozenset[str]]]) -> None:
    if not mismatches:
        return
    rendered: list[str] = []
    for case_name, event, facts in mismatches:
        rendered.append(f"{case_name}:{event} {' '.join(sorted(facts))}")
    raise ValueError(
        "documented Quint contract mismatches: " + "; ".join(rendered)
    )


def main() -> int:
    try:
        _cases_seen, mismatches = parse(sys.stdin.readlines())
        check(mismatches)
    except ValueError as err:
        print(f"C/Quint conformance check failed: {err}", file=sys.stderr)
        return 1

    print(
        "C/Quint conformance check passed: "
        f"0 mismatches across {len(REQUIRED_CASES)} documented BUSY cases"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
