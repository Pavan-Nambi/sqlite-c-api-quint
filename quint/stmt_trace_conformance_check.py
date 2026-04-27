#!/usr/bin/env python3
"""Fail when statement Quint trace replays diverge from documented contracts."""

from __future__ import annotations

import sys


REQUIRED_CASES = {
    "bind-reset-retains",
    "clear-bindings-null",
    "bind-after-step-misuse",
    "data-count-row-done",
    "column-blob-zero-length-null",
}


def parse(lines: list[str]) -> tuple[set[str], list[tuple[str, str, frozenset[str]]]]:
    cases_seen: set[str] = set()
    divergences: list[tuple[str, str, frozenset[str]]] = []

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
            divergences.append((case_name, event, facts))
            continue

        raise ValueError(f"line {line_number}: unexpected line: {line}")

    missing_cases = sorted(REQUIRED_CASES - cases_seen)
    if missing_cases:
        raise ValueError("missing cases: " + ", ".join(missing_cases))
    return cases_seen, divergences


def check(divergences: list[tuple[str, str, frozenset[str]]]) -> None:
    if not divergences:
        return

    rendered: list[str] = []
    for case_name, event, facts in divergences:
        rendered.append(f"{case_name}:{event} {' '.join(sorted(facts))}")
    raise ValueError("unexpected statement divergences: " + "; ".join(rendered))


def main() -> int:
    try:
        _cases_seen, divergences = parse(sys.stdin.readlines())
        check(divergences)
    except ValueError as err:
        print(f"statement trace conformance check failed: {err}", file=sys.stderr)
        return 1

    print(
        "statement trace conformance check passed: "
        f"0 divergences across {len(REQUIRED_CASES)} cases"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
