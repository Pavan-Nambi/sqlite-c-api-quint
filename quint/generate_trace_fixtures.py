#!/usr/bin/env python3
"""Generate canonical ITF traces for Quint trace replay harnesses."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


SERDE_DEFAULT = {
    "readTxn": False,
    "backupSource": False,
    "readonlyRead": False,
    "readonlyWriteRejected": False,
    "resizeableGrew": False,
    "walImageUseFailed": False,
    "grewWithinLimit": False,
    "rejectedBeyondLimit": False,
    "rc": "NO_CALL",
    "divergence": False,
}

LIFECYCLE_DEFAULT = {
    "stage": 0,
    "connOpen": False,
    "connZombie": False,
    "closeNullCalled": False,
    "closeV2NullCalled": False,
    "prepareCaseSelected": False,
    "prepareComparedEqual": False,
    "stmtHandleLive": False,
    "backupHandleLive": False,
    "backupQueryMatched": False,
    "destReadTxnStarted": False,
    "divergence": False,
}

STMT_DEFAULT = {
    "stage": 0,
    "bindingsSet": False,
    "resetCalled": False,
    "clearCalled": False,
    "firstStepRow": False,
    "secondStepRow": False,
    "misuseObserved": False,
    "dataCountBeforeZero": False,
    "dataCountRowNonZero": False,
    "dataCountDoneZero": False,
    "blobZeroIsNull": False,
    "divergence": False,
}

SERDE_TRACES: dict[str, list[dict[str, object]]] = {
    "deserialize_read_txn_busy": [
        {},
        {"readTxn": True},
        {"readTxn": True, "rc": "SQLITE_BUSY"},
    ],
    "deserialize_backup_busy": [
        {},
        {"backupSource": True},
        {"backupSource": True, "rc": "SQLITE_BUSY"},
    ],
}

LIFECYCLE_TRACES: dict[str, list[dict[str, object]]] = {
    "finalize_null": [
        {"stage": 0},
        {"stage": 1},
    ],
    "close_null": [
        {"stage": 0},
        {"stage": 0, "closeNullCalled": True},
        {"stage": 0, "closeNullCalled": True, "closeV2NullCalled": True},
    ],
    "close_live_stmt": [
        {"stage": 0, "connOpen": True},
        {"stage": 1, "connOpen": True, "stmtHandleLive": True},
        {"stage": 2, "connOpen": True, "stmtHandleLive": True},
        {"stage": 3, "connOpen": True, "stmtHandleLive": True},
        {"stage": 4, "connOpen": True, "stmtHandleLive": False},
        {"stage": 5, "connOpen": False, "stmtHandleLive": False},
    ],
    "close_v2_live_stmt": [
        {"stage": 0, "connOpen": True},
        {"stage": 1, "connOpen": True, "stmtHandleLive": True},
        {"stage": 2, "connOpen": True, "connZombie": True, "stmtHandleLive": True},
        {"stage": 3, "connOpen": True, "connZombie": True, "stmtHandleLive": True},
        {"stage": 4, "connOpen": False, "connZombie": False, "stmtHandleLive": False},
    ],
    "prepare_v2_v3_zero_flags": [
        {"stage": 0, "connOpen": True},
        {"stage": 1, "connOpen": True, "prepareCaseSelected": True},
        {
            "stage": 2,
            "connOpen": True,
            "prepareCaseSelected": True,
            "prepareComparedEqual": True,
        },
        {
            "stage": 3,
            "connOpen": False,
            "prepareCaseSelected": True,
            "prepareComparedEqual": True,
        },
    ],
    "close_live_backup": [
        {"stage": 0, "connOpen": True},
        {"stage": 1, "connOpen": True, "backupHandleLive": True},
        {"stage": 2, "connOpen": True, "backupHandleLive": True},
        {"stage": 3, "connOpen": True, "backupHandleLive": True},
        {"stage": 4, "connOpen": True, "backupHandleLive": False},
        {"stage": 5, "connOpen": False, "backupHandleLive": False},
    ],
    "close_v2_live_backup": [
        {"stage": 0, "connOpen": True},
        {"stage": 1, "connOpen": True, "backupHandleLive": True},
        {"stage": 2, "connOpen": True, "connZombie": True, "backupHandleLive": True},
        {"stage": 3, "connOpen": False, "connZombie": False, "backupHandleLive": False},
    ],
    "backup_step_done_finish": [
        {"stage": 0, "connOpen": True},
        {"stage": 1, "connOpen": True, "backupHandleLive": True},
        {"stage": 2, "connOpen": True, "backupHandleLive": True},
        {"stage": 3, "connOpen": True, "backupHandleLive": False, "backupQueryMatched": True},
        {"stage": 4, "connOpen": False, "backupHandleLive": False, "backupQueryMatched": True},
    ],
    "backup_finish_incomplete": [
        {"stage": 0, "connOpen": True},
        {"stage": 1, "connOpen": True, "backupHandleLive": True},
        {"stage": 2, "connOpen": True, "backupHandleLive": True},
        {"stage": 3, "connOpen": False, "backupHandleLive": False},
    ],
    "backup_step_zero_no_progress": [
        {"stage": 0, "connOpen": True},
        {"stage": 1, "connOpen": True, "backupHandleLive": True},
        {"stage": 2, "connOpen": True, "backupHandleLive": True},
        {"stage": 3, "connOpen": True, "backupHandleLive": True},
        {"stage": 4, "connOpen": True, "backupHandleLive": False, "backupQueryMatched": True},
        {"stage": 5, "connOpen": False, "backupHandleLive": False, "backupQueryMatched": True},
    ],
    "backup_step_negative_all_remaining_done": [
        {"stage": 0, "connOpen": True},
        {"stage": 1, "connOpen": True, "backupHandleLive": True},
        {"stage": 2, "connOpen": True, "backupHandleLive": True},
        {"stage": 3, "connOpen": True, "backupHandleLive": False, "backupQueryMatched": True},
        {"stage": 4, "connOpen": False, "backupHandleLive": False, "backupQueryMatched": True},
    ],
    "backup_step_transient_conflict_retry": [
        {"stage": 0, "connOpen": True},
        {"stage": 1, "connOpen": True, "backupHandleLive": True},
        {"stage": 2, "connOpen": True, "backupHandleLive": True, "backupQueryMatched": True},
        {"stage": 3, "connOpen": True, "backupHandleLive": True, "backupQueryMatched": True},
        {"stage": 4, "connOpen": True, "backupHandleLive": False, "backupQueryMatched": True},
        {"stage": 5, "connOpen": False, "backupHandleLive": False, "backupQueryMatched": True},
    ],
    "backup_init_same_connection_error": [
        {"stage": 0, "connOpen": True},
        {"stage": 1, "connOpen": True},
    ],
    "backup_init_dest_read_txn_error": [
        {"stage": 0, "connOpen": True},
        {"stage": 1, "connOpen": True, "destReadTxnStarted": True},
        {"stage": 2, "connOpen": True, "destReadTxnStarted": True},
    ],
}

STMT_TRACES: dict[str, list[dict[str, object]]] = {
    "bind_reset_retains": [
        {"stage": 0},
        {"stage": 1, "bindingsSet": True},
        {"stage": 2, "bindingsSet": True, "firstStepRow": True},
        {"stage": 3, "bindingsSet": True, "firstStepRow": True, "resetCalled": True},
        {"stage": 4, "bindingsSet": True, "firstStepRow": True, "resetCalled": True, "secondStepRow": True},
    ],
    "clear_bindings_null": [
        {"stage": 0},
        {"stage": 1, "bindingsSet": True},
        {"stage": 2, "bindingsSet": True, "firstStepRow": True},
        {"stage": 3, "bindingsSet": True, "firstStepRow": True, "resetCalled": True},
        {"stage": 4, "bindingsSet": False, "firstStepRow": True, "resetCalled": True, "clearCalled": True},
        {"stage": 5, "bindingsSet": False, "firstStepRow": True, "resetCalled": True, "clearCalled": True, "secondStepRow": True},
    ],
    "bind_after_step_misuse": [
        {"stage": 0},
        {"stage": 1, "firstStepRow": True},
        {"stage": 2, "firstStepRow": True, "misuseObserved": True},
    ],
    "data_count_row_done": [
        {"stage": 0},
        {"stage": 1, "dataCountBeforeZero": True},
        {"stage": 2, "dataCountBeforeZero": True, "firstStepRow": True, "dataCountRowNonZero": True},
        {"stage": 3, "dataCountBeforeZero": True, "firstStepRow": True, "secondStepRow": True, "dataCountRowNonZero": True},
        {"stage": 4, "dataCountBeforeZero": True, "firstStepRow": True, "secondStepRow": True, "dataCountRowNonZero": True, "dataCountDoneZero": True},
    ],
    "column_blob_zero_length_null": [
        {"stage": 0},
        {"stage": 1, "firstStepRow": True},
        {"stage": 2, "firstStepRow": True, "blobZeroIsNull": True},
    ],
}


def wrap_states(
    scenario: str,
    raw_states: list[dict[str, object]],
    defaults: dict[str, object],
) -> dict[str, object]:
    states = []
    for raw in raw_states:
        state = dict(defaults)
        state.update(raw)
        state["scenario"] = scenario
        states.append({"state": state})
    return {"states": states}


def write_family(
    traces: dict[str, list[dict[str, object]]],
    defaults: dict[str, object],
    out_dir: Path,
) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    for scenario, raw_states in sorted(traces.items()):
        payload = wrap_states(scenario, raw_states, defaults)
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

    if args.family in {"all", "serde"}:
        write_family(SERDE_TRACES, SERDE_DEFAULT, args.out_dir)
    if args.family in {"all", "lifecycle"}:
        write_family(LIFECYCLE_TRACES, LIFECYCLE_DEFAULT, args.out_dir)
    if args.family in {"all", "stmt"}:
        write_family(STMT_TRACES, STMT_DEFAULT, args.out_dir)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
