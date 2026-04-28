#!/usr/bin/env python3
"""Generate validated canonical replay artifacts from Apalache ITF traces.

Supported model families:
- serde_api.qnt: deserialize-focused scenarios (existing path)
- lifecycle_api.qnt: close/finalize/prepare/backup lifecycle scenarios
- stmt_api.qnt: bind/reset/clear + column/data_count statement scenarios

Primary path in this repo:
- Supported ITF trace shape -> standalone C repro harness for that canonical
  scenario on upstream SQLite. This is not arbitrary semantic trace replay.

Secondary path:
- ITF trace -> SQLite testfixture Tcl script scaffold.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import textwrap


SERDE_SCENARIOS = {
    "deserialize_read_txn_busy": {
        "case_name": "deserialize-read-transaction-busy",
        "event_name": "deserialize_read_txn_trace_mismatch",
        "setup": "read_txn",
        "tcl_axis": "active read transaction",
    },
    "deserialize_backup_busy": {
        "case_name": "deserialize-backup-source-busy",
        "event_name": "deserialize_backup_source_trace_mismatch",
        "setup": "backup_source",
        "tcl_axis": "active backup source",
    },
    "deserialize_null_schema_main": {
        "case_name": "deserialize-null-schema-main",
        "event_name": "deserialize_null_schema_main_trace_mismatch",
        "setup": "none",
        "tcl_axis": "NULL schema aliases main",
    },
    "deserialize_attached_schema": {
        "case_name": "deserialize-attached-schema",
        "event_name": "deserialize_attached_schema_trace_mismatch",
        "setup": "none",
        "tcl_axis": "attached schema deserialize success",
    },
    "deserialize_temp_schema_error": {
        "case_name": "deserialize-temp-schema-error",
        "event_name": "deserialize_temp_schema_trace_mismatch",
        "setup": "none",
        "tcl_axis": "temp schema rejected",
    },
    "deserialize_missing_schema_error": {
        "case_name": "deserialize-missing-schema-error",
        "event_name": "deserialize_missing_schema_trace_mismatch",
        "setup": "none",
        "tcl_axis": "missing schema rejected",
    },
    "deserialize_readonly_read_write": {
        "case_name": "deserialize-readonly-read-write",
        "event_name": "deserialize_readonly_trace_mismatch",
        "setup": "none",
        "tcl_axis": "readonly deserialize permits reads and rejects writes",
    },
    "deserialize_resizeable_growth": {
        "case_name": "deserialize-resizeable-growth",
        "event_name": "deserialize_resizeable_growth_trace_mismatch",
        "setup": "none",
        "tcl_axis": "resizeable deserialize can grow",
    },
    "deserialize_nonresizeable_growth": {
        "case_name": "deserialize-nonresizeable-growth",
        "event_name": "deserialize_nonresizeable_growth_trace_mismatch",
        "setup": "none",
        "tcl_axis": "nonresizeable deserialize is bounded by supplied buffer",
    },
}

LIFECYCLE_SCENARIOS = {
    "finalize_null": {
        "case_name": "finalize-null",
        "event_name": "finalize_null_trace_mismatch",
        "expected_terminal_stage": 1,
        "tcl_axis": "sqlite3_finalize(NULL) no-op",
    },
    "close_null": {
        "case_name": "close-null",
        "event_name": "close_null_trace_mismatch",
        "expected_terminal_stage": 0,
        "tcl_axis": "sqlite3_close/sqlite3_close_v2 NULL no-op",
    },
    "close_live_stmt": {
        "case_name": "close-live-stmt",
        "event_name": "close_live_stmt_trace_mismatch",
        "expected_terminal_stage": 5,
        "tcl_axis": "sqlite3_close busy with live statement",
    },
    "close_v2_live_stmt": {
        "case_name": "close-v2-live-stmt",
        "event_name": "close_v2_live_stmt_trace_mismatch",
        "expected_terminal_stage": 4,
        "tcl_axis": "sqlite3_close_v2 zombie with live statement",
    },
    "prepare_v2_v3_zero_flags": {
        "case_name": "prepare-v2-v3-zero-flags",
        "event_name": "prepare_v2_v3_zero_flags_trace_mismatch",
        "expected_terminal_stage": 3,
        "tcl_axis": "sqlite3_prepare_v2/v3 zero-flag equivalence",
    },
    "close_live_backup": {
        "case_name": "close-live-backup",
        "event_name": "close_live_backup_trace_mismatch",
        "expected_terminal_stage": 5,
        "tcl_axis": "sqlite3_close busy with live backup source",
    },
    "close_v2_live_backup": {
        "case_name": "close-v2-live-backup",
        "event_name": "close_v2_live_backup_trace_mismatch",
        "expected_terminal_stage": 3,
        "tcl_axis": "sqlite3_close_v2 zombie with live backup source",
    },
    "backup_step_done_finish": {
        "case_name": "backup-step-done-finish-ok",
        "event_name": "backup_step_done_finish_trace_mismatch",
        "expected_terminal_stage": 4,
        "tcl_axis": "backup step DONE then finish OK",
    },
    "backup_finish_incomplete": {
        "case_name": "backup-finish-incomplete-ok",
        "event_name": "backup_finish_incomplete_trace_mismatch",
        "expected_terminal_stage": 3,
        "tcl_axis": "backup finish OK after incomplete step",
    },
    "backup_step_zero_no_progress": {
        "case_name": "backup-step-zero-no-progress",
        "event_name": "backup_step_zero_no_progress_trace_mismatch",
        "expected_terminal_stage": 5,
        "tcl_axis": "backup step(0) does not copy pages",
    },
    "backup_step_negative_all_remaining_done": {
        "case_name": "backup-step-negative-all-remaining-done",
        "event_name": "backup_step_negative_all_remaining_done_trace_mismatch",
        "expected_terminal_stage": 4,
        "tcl_axis": "backup step(-1) copies all remaining pages",
    },
    "backup_step_transient_conflict_retry": {
        "case_name": "backup-step-transient-conflict-retry",
        "event_name": "backup_step_transient_conflict_retry_trace_mismatch",
        "expected_terminal_stage": 5,
        "tcl_axis": "backup step BUSY/LOCKED is transient and retryable",
    },
    "backup_init_same_connection_error": {
        "case_name": "backup-init-same-connection-error",
        "event_name": "backup_init_same_connection_trace_mismatch",
        "expected_terminal_stage": 1,
        "tcl_axis": "backup init rejects identical source/destination",
    },
    "backup_init_dest_read_txn_error": {
        "case_name": "backup-init-destination-read-transaction-error",
        "event_name": "backup_init_dest_read_txn_trace_mismatch",
        "expected_terminal_stage": 2,
        "tcl_axis": "backup init rejects destination read transaction",
    },
}

STMT_SCENARIOS = {
    "bind_reset_retains": {
        "case_name": "bind-reset-retains",
        "event_name": "bind_reset_retains_trace_mismatch",
        "expected_terminal_stage": 4,
        "tcl_axis": "sqlite3_reset retains prior bindings",
    },
    "clear_bindings_null": {
        "case_name": "clear-bindings-null",
        "event_name": "clear_bindings_null_trace_mismatch",
        "expected_terminal_stage": 5,
        "tcl_axis": "sqlite3_clear_bindings resets all parameters to NULL",
    },
    "bind_after_step_misuse": {
        "case_name": "bind-after-step-misuse",
        "event_name": "bind_after_step_misuse_trace_mismatch",
        "expected_terminal_stage": 2,
        "tcl_axis": "sqlite3_bind after step-before-reset returns SQLITE_MISUSE",
    },
    "data_count_row_done": {
        "case_name": "data-count-row-done",
        "event_name": "data_count_row_done_trace_mismatch",
        "expected_terminal_stage": 4,
        "tcl_axis": "sqlite3_data_count row/non-row transitions",
    },
    "column_blob_zero_length_null": {
        "case_name": "column-blob-zero-length-null",
        "event_name": "column_blob_zero_length_null_trace_mismatch",
        "expected_terminal_stage": 2,
        "tcl_axis": "sqlite3_column_blob zero-length blob returns NULL",
    },
}

VALID_RC = {
    "NO_CALL",
    "SQLITE_OK",
    "SQLITE_BUSY",
    "SQLITE_ERROR",
    "SQLITE_MISUSE",
    "SQLITE_READONLY",
    "SQLITE_FULL",
    "SQLITE_CANTOPEN",
}


LIFECYCLE_TERMINAL_FACTS: dict[str, dict[str, object]] = {
    "finalize_null": {
        "stage": 1,
        "connOpen": False,
        "connZombie": False,
        "stmtHandleLive": False,
        "backupHandleLive": False,
    },
    "close_null": {
        "stage": 0,
        "connOpen": False,
        "connZombie": False,
        "stmtHandleLive": False,
        "backupHandleLive": False,
        "closeNullCalled": True,
        "closeV2NullCalled": True,
    },
    "close_live_stmt": {
        "stage": 5,
        "connOpen": False,
        "connZombie": False,
        "stmtHandleLive": False,
    },
    "close_v2_live_stmt": {
        "stage": 4,
        "connOpen": False,
        "connZombie": False,
        "stmtHandleLive": False,
    },
    "prepare_v2_v3_zero_flags": {
        "stage": 3,
        "connOpen": False,
        "prepareCaseSelected": True,
        "prepareComparedEqual": True,
    },
    "close_live_backup": {
        "stage": 5,
        "connOpen": False,
        "connZombie": False,
        "backupHandleLive": False,
    },
    "close_v2_live_backup": {
        "stage": 3,
        "connOpen": False,
        "connZombie": False,
        "backupHandleLive": False,
    },
    "backup_step_done_finish": {
        "stage": 4,
        "connOpen": True,
        "backupHandleLive": False,
        "backupQueryMatched": True,
    },
    "backup_finish_incomplete": {
        "stage": 3,
        "connOpen": True,
        "backupHandleLive": False,
        "backupQueryMatched": False,
    },
    "backup_step_zero_no_progress": {
        "stage": 5,
        "connOpen": False,
        "backupHandleLive": False,
        "backupQueryMatched": True,
    },
    "backup_step_negative_all_remaining_done": {
        "stage": 4,
        "connOpen": False,
        "backupHandleLive": False,
        "backupQueryMatched": True,
    },
    "backup_step_transient_conflict_retry": {
        "stage": 5,
        "connOpen": False,
        "backupHandleLive": False,
        "backupQueryMatched": True,
    },
    "backup_init_same_connection_error": {
        "stage": 1,
        "connOpen": True,
        "connZombie": False,
        "backupHandleLive": False,
    },
    "backup_init_dest_read_txn_error": {
        "stage": 2,
        "connOpen": True,
        "destReadTxnStarted": True,
        "backupHandleLive": False,
    },
}


STMT_TERMINAL_FACTS: dict[str, dict[str, object]] = {
    "bind_reset_retains": {
        "stage": 4,
        "bindingsSet": True,
        "resetCalled": True,
        "firstStepRow": True,
        "secondStepRow": True,
    },
    "clear_bindings_null": {
        "stage": 5,
        "bindingsSet": False,
        "resetCalled": True,
        "clearCalled": True,
        "firstStepRow": True,
        "secondStepRow": True,
    },
    "bind_after_step_misuse": {
        "stage": 2,
        "firstStepRow": True,
        "misuseObserved": True,
    },
    "data_count_row_done": {
        "stage": 4,
        "firstStepRow": True,
        "secondStepRow": True,
        "dataCountBeforeZero": True,
        "dataCountRowNonZero": True,
        "dataCountDoneZero": True,
    },
    "column_blob_zero_length_null": {
        "stage": 2,
        "firstStepRow": True,
        "blobZeroIsNull": True,
    },
}


LIFECYCLE_EXPECTED_STEPS: dict[str, list[str]] = {
    "finalize_null": [
        "stage_0_to_1",
    ],
    "close_null": [
        "close_null_called",
        "close_v2_null_called",
    ],
    "close_live_stmt": [
        "stage_0_to_1",
        "stmt_live",
        "stage_1_to_2",
        "stage_2_to_3",
        "stage_3_to_4",
        "stage_4_to_5",
    ],
    "close_v2_live_stmt": [
        "stage_0_to_1",
        "stmt_live",
        "stage_1_to_2",
        "stage_2_to_3",
        "stage_3_to_4",
    ],
    "prepare_v2_v3_zero_flags": [
        "stage_0_to_1",
        "prepare_case_selected",
        "stage_1_to_2",
        "prepare_compared_equal",
        "stage_2_to_3",
    ],
    "close_live_backup": [
        "stage_0_to_1",
        "backup_live",
        "stage_1_to_2",
        "stage_2_to_3",
        "stage_3_to_4",
        "stage_4_to_5",
    ],
    "close_v2_live_backup": [
        "stage_0_to_1",
        "backup_live",
        "stage_1_to_2",
        "stage_2_to_3",
    ],
    "backup_step_done_finish": [
        "stage_0_to_1",
        "backup_live",
        "stage_1_to_2",
        "stage_2_to_3",
        "stage_3_to_4",
        "backup_query_matched",
    ],
    "backup_finish_incomplete": [
        "stage_0_to_1",
        "backup_live",
        "stage_1_to_2",
        "stage_2_to_3",
    ],
    "backup_step_zero_no_progress": [
        "stage_0_to_1",
        "backup_live",
        "stage_1_to_2",
        "stage_2_to_3",
        "stage_3_to_4",
        "backup_query_matched",
        "stage_4_to_5",
    ],
    "backup_step_negative_all_remaining_done": [
        "stage_0_to_1",
        "backup_live",
        "stage_1_to_2",
        "stage_2_to_3",
        "backup_query_matched",
        "stage_3_to_4",
    ],
    "backup_step_transient_conflict_retry": [
        "stage_0_to_1",
        "backup_live",
        "stage_1_to_2",
        "backup_query_matched",
        "stage_2_to_3",
        "stage_3_to_4",
        "stage_4_to_5",
    ],
    "backup_init_same_connection_error": [
        "stage_0_to_1",
    ],
    "backup_init_dest_read_txn_error": [
        "stage_0_to_1",
        "dest_read_txn_started",
        "stage_1_to_2",
    ],
}


STMT_EXPECTED_STEPS: dict[str, list[str]] = {
    "bind_reset_retains": [
        "stage_0_to_1",
        "bindings_set",
        "stage_1_to_2",
        "first_step_row",
        "stage_2_to_3",
        "reset_called",
        "stage_3_to_4",
        "second_step_row",
    ],
    "clear_bindings_null": [
        "stage_0_to_1",
        "bindings_set",
        "stage_1_to_2",
        "first_step_row",
        "stage_2_to_3",
        "reset_called",
        "stage_3_to_4",
        "clear_called",
        "stage_4_to_5",
        "second_step_row",
    ],
    "bind_after_step_misuse": [
        "stage_0_to_1",
        "first_step_row",
        "stage_1_to_2",
        "misuse_observed",
    ],
    "data_count_row_done": [
        "stage_0_to_1",
        "data_count_before_zero",
        "stage_1_to_2",
        "first_step_row",
        "data_count_row_nonzero",
        "stage_2_to_3",
        "second_step_row",
        "stage_3_to_4",
        "data_count_done_zero",
    ],
    "column_blob_zero_length_null": [
        "stage_0_to_1",
        "first_step_row",
        "stage_1_to_2",
        "blob_zero_is_null",
    ],
}


SERDE_EXPECTED_STEPS: dict[str, list[str]] = {
    "deserialize_read_txn_busy": [
        "start_read_txn",
        "deserialize",
    ],
    "deserialize_backup_busy": [
        "start_backup_source",
        "deserialize",
    ],
    "deserialize_null_schema_main": [
        "deserialize",
    ],
    "deserialize_attached_schema": [
        "deserialize",
    ],
    "deserialize_temp_schema_error": [
        "deserialize",
    ],
    "deserialize_missing_schema_error": [
        "deserialize",
    ],
    "deserialize_readonly_read_write": [
        "deserialize",
        "readonly_read",
        "readonly_write_reject",
    ],
    "deserialize_resizeable_growth": [
        "deserialize",
        "resizeable_grow",
    ],
    "deserialize_nonresizeable_growth": [
        "deserialize",
        "grow_within_limit",
        "reject_beyond_limit",
    ],
}


SERDE_TERMINAL_FACTS: dict[str, dict[str, object]] = {
    "deserialize_read_txn_busy": {
        "readTxn": True,
        "deserialized": False,
        "rc": "SQLITE_BUSY",
    },
    "deserialize_backup_busy": {
        "backupSource": True,
        "deserialized": False,
        "rc": "SQLITE_BUSY",
    },
    "deserialize_null_schema_main": {
        "deserialized": True,
        "rc": "SQLITE_OK",
    },
    "deserialize_attached_schema": {
        "deserialized": True,
        "rc": "SQLITE_OK",
    },
    "deserialize_temp_schema_error": {
        "deserialized": False,
        "rc": "SQLITE_ERROR",
    },
    "deserialize_missing_schema_error": {
        "deserialized": False,
        "rc": "SQLITE_ERROR",
    },
    "deserialize_readonly_read_write": {
        "deserialized": True,
        "readonlyRead": True,
        "readonlyWriteRejected": True,
        "rc": "SQLITE_READONLY",
    },
    "deserialize_resizeable_growth": {
        "deserialized": True,
        "resizeableGrew": True,
        "rc": "SQLITE_OK",
    },
    "deserialize_nonresizeable_growth": {
        "deserialized": True,
        "grewWithinLimit": True,
        "rejectedBeyondLimit": True,
        "rc": "SQLITE_FULL",
    },
}


def all_supported_scenarios() -> list[str]:
    return sorted(set(SERDE_SCENARIOS) | set(LIFECYCLE_SCENARIOS) | set(STMT_SCENARIOS))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--itf", required=True, type=Path, help="Path to *.itf.json")
    parser.add_argument(
        "--out-dir",
        type=Path,
        default=Path("/tmp/quint-trace-repro"),
        help="Output directory for generated artifacts",
    )
    parser.add_argument(
        "--prefix",
        default="trace_repro",
        help="Output file prefix (without extension)",
    )
    parser.add_argument(
        "--emit-tcl",
        action="store_true",
        help="Also emit SQLite testfixture Tcl scaffold",
    )
    return parser.parse_args()


def load_states(itf_path: Path) -> list[dict[str, object]]:
    data = json.loads(itf_path.read_text())
    states = data.get("states")
    if not isinstance(states, list) or not states:
        raise ValueError(f"{itf_path}: missing non-empty states[]")

    extracted: list[dict[str, object]] = []
    for idx, wrapper in enumerate(states):
        if not isinstance(wrapper, dict) or "state" not in wrapper:
            raise ValueError(f"{itf_path}: states[{idx}] missing state object")
        raw_state = wrapper["state"]
        if not isinstance(raw_state, dict):
            raise ValueError(f"{itf_path}: states[{idx}].state must be an object")
        extracted.append(raw_state)
    return extracted


def infer_serde_transition_steps(states: list[dict[str, object]]) -> list[str]:
    steps: list[str] = []
    for prev, curr in zip(states, states[1:]):
        if bool(curr.get("readTxn")) and not bool(prev.get("readTxn")):
            steps.append("start_read_txn")
        if bool(curr.get("backupSource")) and not bool(prev.get("backupSource")):
            steps.append("start_backup_source")
        if prev.get("rc") == "NO_CALL" and curr.get("rc") != prev.get("rc"):
            steps.append("deserialize")

        if bool(curr.get("readonlyRead")) and not bool(prev.get("readonlyRead")):
            steps.append("readonly_read")
        if bool(curr.get("readonlyWriteRejected")) and not bool(prev.get("readonlyWriteRejected")):
            steps.append("readonly_write_reject")
        if bool(curr.get("resizeableGrew")) and not bool(prev.get("resizeableGrew")):
            steps.append("resizeable_grow")
        if bool(curr.get("walImageUseFailed")) and not bool(prev.get("walImageUseFailed")):
            steps.append("wal_image_fail")
        if bool(curr.get("grewWithinLimit")) and not bool(prev.get("grewWithinLimit")):
            steps.append("grow_within_limit")
        if bool(curr.get("rejectedBeyondLimit")) and not bool(prev.get("rejectedBeyondLimit")):
            steps.append("reject_beyond_limit")
    return steps


def _stage_value(state: dict[str, object]) -> int:
    stage = state.get("stage")
    if not isinstance(stage, int) or stage < 0:
        raise ValueError(f"invalid lifecycle stage value: {stage!r}")
    return stage


def validate_staged_trace(
    scenario: str,
    states: list[dict[str, object]],
    expected_terminal_stage: int,
    terminal_facts: dict[str, object],
) -> None:
    stages = [_stage_value(state) for state in states]
    if stages[0] != 0:
        raise ValueError(f"{scenario}: trace must start at stage 0, got {stages[0]}")

    for idx, (prev_stage, curr_stage) in enumerate(zip(stages, stages[1:]), 1):
        if curr_stage < prev_stage:
            raise ValueError(
                f"{scenario}: stage regressed at transition {idx}: "
                f"{prev_stage} -> {curr_stage}"
            )
        if curr_stage - prev_stage > 1:
            raise ValueError(
                f"{scenario}: stage skipped at transition {idx}: "
                f"{prev_stage} -> {curr_stage}"
            )

    observed_terminal_stage = max(stages)
    if observed_terminal_stage != expected_terminal_stage:
        raise ValueError(
            f"{scenario}: expected terminal stage {expected_terminal_stage}, "
            f"observed {observed_terminal_stage}"
        )
    if stages[-1] != expected_terminal_stage:
        raise ValueError(
            f"{scenario}: final trace state is stage {stages[-1]}, "
            f"expected terminal stage {expected_terminal_stage}"
        )

    validate_terminal_facts(scenario, states[-1], terminal_facts)


def validate_expected_steps(
    scenario: str,
    observed_steps: list[str],
    expected_steps: list[str],
) -> None:
    if observed_steps != expected_steps:
        raise ValueError(
            f"{scenario}: expected steps {expected_steps!r}, got {observed_steps!r}"
        )


def validate_terminal_facts(
    scenario: str,
    state: dict[str, object],
    terminal_facts: dict[str, object],
) -> None:
    for key, expected in terminal_facts.items():
        observed = state.get(key)
        if observed != expected:
            raise ValueError(
                f"{scenario}: terminal {key} expected {expected!r}, got {observed!r}"
            )


def infer_lifecycle_transition_steps(states: list[dict[str, object]]) -> list[str]:
    steps: list[str] = []
    for prev, curr in zip(states, states[1:]):
        prev_stage = _stage_value(prev)
        curr_stage = _stage_value(curr)
        if curr_stage != prev_stage:
            steps.append(f"stage_{prev_stage}_to_{curr_stage}")

        if bool(curr.get("closeNullCalled")) and not bool(prev.get("closeNullCalled")):
            steps.append("close_null_called")
        if bool(curr.get("closeV2NullCalled")) and not bool(prev.get("closeV2NullCalled")):
            steps.append("close_v2_null_called")
        if bool(curr.get("prepareCaseSelected")) and not bool(prev.get("prepareCaseSelected")):
            steps.append("prepare_case_selected")
        if bool(curr.get("prepareComparedEqual")) and not bool(prev.get("prepareComparedEqual")):
            steps.append("prepare_compared_equal")
        if bool(curr.get("stmtHandleLive")) and not bool(prev.get("stmtHandleLive")):
            steps.append("stmt_live")
        if bool(curr.get("backupHandleLive")) and not bool(prev.get("backupHandleLive")):
            steps.append("backup_live")
        if bool(curr.get("backupQueryMatched")) and not bool(prev.get("backupQueryMatched")):
            steps.append("backup_query_matched")
        if bool(curr.get("destReadTxnStarted")) and not bool(prev.get("destReadTxnStarted")):
            steps.append("dest_read_txn_started")
    return steps


def infer_stmt_transition_steps(states: list[dict[str, object]]) -> list[str]:
    steps: list[str] = []
    for prev, curr in zip(states, states[1:]):
        prev_stage = _stage_value(prev)
        curr_stage = _stage_value(curr)
        if curr_stage != prev_stage:
            steps.append(f"stage_{prev_stage}_to_{curr_stage}")

        if bool(curr.get("bindingsSet")) and not bool(prev.get("bindingsSet")):
            steps.append("bindings_set")
        if bool(curr.get("resetCalled")) and not bool(prev.get("resetCalled")):
            steps.append("reset_called")
        if bool(curr.get("clearCalled")) and not bool(prev.get("clearCalled")):
            steps.append("clear_called")
        if bool(curr.get("firstStepRow")) and not bool(prev.get("firstStepRow")):
            steps.append("first_step_row")
        if bool(curr.get("secondStepRow")) and not bool(prev.get("secondStepRow")):
            steps.append("second_step_row")
        if bool(curr.get("misuseObserved")) and not bool(prev.get("misuseObserved")):
            steps.append("misuse_observed")
        if bool(curr.get("dataCountBeforeZero")) and not bool(prev.get("dataCountBeforeZero")):
            steps.append("data_count_before_zero")
        if bool(curr.get("dataCountRowNonZero")) and not bool(prev.get("dataCountRowNonZero")):
            steps.append("data_count_row_nonzero")
        if bool(curr.get("dataCountDoneZero")) and not bool(prev.get("dataCountDoneZero")):
            steps.append("data_count_done_zero")
        if bool(curr.get("blobZeroIsNull")) and not bool(prev.get("blobZeroIsNull")):
            steps.append("blob_zero_is_null")
    return steps


def infer_serde_model(scenario: str, states: list[dict[str, object]]) -> dict[str, object]:
    rcs = [state.get("rc") for state in states if state.get("rc") != "NO_CALL"]
    if not rcs:
        raise ValueError("trace does not include a deserialize/result state (rc != NO_CALL)")
    expected_rc = rcs[0]
    if not isinstance(expected_rc, str) or expected_rc not in VALID_RC:
        raise ValueError(f"unsupported expected rc value: {expected_rc!r}")

    info = SERDE_SCENARIOS[scenario]
    inferred_steps = infer_serde_transition_steps(states)
    validate_expected_steps(scenario, inferred_steps, SERDE_EXPECTED_STEPS[scenario])
    validate_terminal_facts(scenario, states[-1], SERDE_TERMINAL_FACTS[scenario])

    return {
        "family": "serde",
        "scenario": scenario,
        "case_name": info["case_name"],
        "event_name": info["event_name"],
        "setup": info["setup"],
        "expected_rc": expected_rc,
        "steps": inferred_steps,
        "divergence": bool(states[-1].get("divergence", False)),
    }


def infer_lifecycle_model(scenario: str, states: list[dict[str, object]]) -> dict[str, object]:
    info = LIFECYCLE_SCENARIOS[scenario]
    validate_staged_trace(
        scenario,
        states,
        int(info["expected_terminal_stage"]),
        LIFECYCLE_TERMINAL_FACTS[scenario],
    )
    inferred_steps = infer_lifecycle_transition_steps(states)
    validate_expected_steps(scenario, inferred_steps, LIFECYCLE_EXPECTED_STEPS[scenario])
    terminal_stage = max(_stage_value(state) for state in states)

    return {
        "family": "lifecycle",
        "scenario": scenario,
        "case_name": info["case_name"],
        "event_name": info["event_name"],
        "expected_terminal_stage": info["expected_terminal_stage"],
        "observed_terminal_stage": terminal_stage,
        "steps": inferred_steps,
        "divergence": bool(states[-1].get("divergence", False)),
    }


def infer_stmt_model(scenario: str, states: list[dict[str, object]]) -> dict[str, object]:
    info = STMT_SCENARIOS[scenario]
    validate_staged_trace(
        scenario,
        states,
        int(info["expected_terminal_stage"]),
        STMT_TERMINAL_FACTS[scenario],
    )
    inferred_steps = infer_stmt_transition_steps(states)
    validate_expected_steps(scenario, inferred_steps, STMT_EXPECTED_STEPS[scenario])
    terminal_stage = max(_stage_value(state) for state in states)

    return {
        "family": "stmt",
        "scenario": scenario,
        "case_name": info["case_name"],
        "event_name": info["event_name"],
        "expected_terminal_stage": info["expected_terminal_stage"],
        "observed_terminal_stage": terminal_stage,
        "steps": inferred_steps,
        "divergence": bool(states[-1].get("divergence", False)),
    }


def infer_trace_model(states: list[dict[str, object]]) -> dict[str, object]:
    first = states[0]
    scenario = first.get("scenario")
    if not isinstance(scenario, str) or not scenario:
        raise ValueError("trace state missing scenario")

    for idx, state in enumerate(states):
        if state.get("scenario") != scenario:
            raise ValueError(
                f"trace switches scenario at states[{idx}] ({state.get('scenario')!r})"
            )

    if scenario in SERDE_SCENARIOS:
        return infer_serde_model(scenario, states)
    if scenario in LIFECYCLE_SCENARIOS:
        return infer_lifecycle_model(scenario, states)
    if scenario in STMT_SCENARIOS:
        return infer_stmt_model(scenario, states)

    supported = ", ".join(all_supported_scenarios())
    raise ValueError(f"unsupported scenario '{scenario}'. Supported scenarios: {supported}")


def emit_manifest(model: dict[str, object], out_path: Path) -> None:
    out_path.write_text(json.dumps(model, indent=2, sort_keys=True) + "\n")


def emit_c_serde(model: dict[str, object], out_path: Path) -> None:
    expected_rc = str(model["expected_rc"])
    case_name = str(model["case_name"])
    event_name = str(model["event_name"])
    steps = ", ".join(str(step) for step in model["steps"])

    source = f"""\
#include "sqlite3.h"

#include <stdio.h>
#include <string.h>

/* Generated from Quint ITF trace.
 * family: {model['family']}
 * scenario: {model['scenario']}
 * expected_rc: {expected_rc}
 * inferred_steps: {steps}
 */

static void emit_case(const char *name) {{
  printf("case %s\\n", name);
}}

static const char *rc_name(int rc) {{
  switch (rc) {{
    case SQLITE_OK: return "SQLITE_OK";
    case SQLITE_BUSY: return "SQLITE_BUSY";
    case SQLITE_ERROR: return "SQLITE_ERROR";
    case SQLITE_MISUSE: return "SQLITE_MISUSE";
    case SQLITE_READONLY: return "SQLITE_READONLY";
    case SQLITE_FULL: return "SQLITE_FULL";
    case SQLITE_CANTOPEN: return "SQLITE_CANTOPEN";
    default: return "SQLITE_OTHER";
  }}
}}

static void emit_diverge(const char *name, int observed_rc) {{
  printf("diverge %s {event_name} api=sqlite3_deserialize expected={expected_rc} observed=%s\\n",
      name, rc_name(observed_rc));
}}

static int fail_msg(const char *name, const char *msg) {{
  fprintf(stderr, "%s: %s\\n", name, msg);
  return 1;
}}

static int fail_rc(const char *name, int expected, int got) {{
  fprintf(stderr, "%s: expected rc=%d got rc=%d\\n", name, expected, got);
  return 1;
}}

static int query_count_sql(sqlite3 *db, const char *sql, int *count);

static int check_rc(
    const char *case_name,
    const char *event_name,
    const char *api_name,
    int expected,
    int observed) {{
  if (observed == expected) return 0;
  printf("diverge %s %s api=%s expected=%s observed=%s\\n",
      case_name,
      event_name,
      api_name,
      rc_name(expected),
      rc_name(observed));
  return 1;
}}

static int check_count(
    const char *case_name,
    const char *event_name,
    sqlite3 *db,
    const char *sql,
    int expected) {{
  int count = 0;
  if (query_count_sql(db, sql, &count) != 0) return 1;
  if (count == expected) return 0;
  printf("diverge %s %s api=sqlite3_step expected=count_%d observed=count_%d\\n",
      case_name,
      event_name,
      expected,
      count);
  return 1;
}}

static int open_memory(sqlite3 **db) {{
  int rc = sqlite3_open(":memory:", db);
  if (rc != SQLITE_OK) {{
    fprintf(stderr, "sqlite3_open(:memory:) failed rc=%d\\n", rc);
    return 1;
  }}
  return 0;
}}

static int exec_ok(sqlite3 *db, const char *sql) {{
  char *errmsg = 0;
  int rc = sqlite3_exec(db, sql, 0, 0, &errmsg);
  if (rc != SQLITE_OK) {{
    fprintf(stderr, "sqlite3_exec failed rc=%d sql=%s errmsg=%s\\n",
        rc, sql, errmsg ? errmsg : "(null)");
    sqlite3_free(errmsg);
    return 1;
  }}
  return 0;
}}

static int exec_rc(sqlite3 *db, const char *sql) {{
  char *errmsg = 0;
  int rc = sqlite3_exec(db, sql, 0, 0, &errmsg);
  sqlite3_free(errmsg);
  return rc;
}}

static int make_small_source(sqlite3 **db) {{
  if (open_memory(db) != 0) return 1;
  return exec_ok(*db,
      "CREATE TABLE t1(a INTEGER PRIMARY KEY);"
      "INSERT INTO t1 VALUES(1),(2),(3);");
}}

static int make_blob_source(sqlite3 **db) {{
  if (open_memory(db) != 0) return 1;
  return exec_ok(*db,
      "CREATE TABLE t1(x BLOB);"
      "INSERT INTO t1 VALUES(zeroblob(16));");
}}

static int query_count(sqlite3 *db, int *count) {{
  return query_count_sql(db, "SELECT count(*) FROM t1", count);
}}

static int query_count_sql(sqlite3 *db, const char *sql, int *count) {{
  sqlite3_stmt *stmt = 0;
  int rc = sqlite3_prepare_v2(db, sql, -1, &stmt, 0);
  if (rc != SQLITE_OK) return 1;
  rc = sqlite3_step(stmt);
  if (rc != SQLITE_ROW) {{
    sqlite3_finalize(stmt);
    return fail_rc("query count step", SQLITE_ROW, rc);
  }}
  *count = sqlite3_column_int(stmt, 0);
  rc = sqlite3_finalize(stmt);
  if (rc != SQLITE_OK) return fail_rc("query count finalize", SQLITE_OK, rc);
  return 0;
}}

static int serialize_copy(sqlite3 *db, unsigned char **data, sqlite3_int64 *size) {{
  *size = -1;
  *data = sqlite3_serialize(db, "main", size, 0);
  if (*data == 0) return fail_msg("sqlite3_serialize(copy)", "returned NULL");
  if (*size <= 0) {{
    sqlite3_free(*data);
    return fail_msg("sqlite3_serialize(copy)", "returned non-positive size");
  }}
  return 0;
}}

static int serialize_with_capacity(
    sqlite3 *db,
    unsigned char **data,
    sqlite3_int64 *size,
    sqlite3_int64 capacity) {{
  unsigned char *source = 0;
  sqlite3_int64 source_size = 0;
  if (serialize_copy(db, &source, &source_size) != 0) return 1;
  if (capacity < source_size) {{
    sqlite3_free(source);
    return fail_msg("serialize_with_capacity", "capacity smaller than source image");
  }}
  *data = sqlite3_malloc64((sqlite3_uint64)capacity);
  if (*data == 0) {{
    sqlite3_free(source);
    return fail_msg("serialize_with_capacity", "sqlite3_malloc64 returned NULL");
  }}
  memcpy(*data, source, (size_t)source_size);
  sqlite3_free(source);
  *size = source_size;
  return 0;
}}

static int run_deserialize_read_txn_busy(const char *case_name, const char *event_name) {{
  sqlite3 *src = 0;
  sqlite3 *target = 0;
  unsigned char *data = 0;
  sqlite3_int64 size = 0;
  int count = 0;
  int rc;

  emit_case(case_name);
  if (make_small_source(&src) != 0) return 1;
  if (make_small_source(&target) != 0) return 1;
  if (serialize_copy(src, &data, &size) != 0) return 1;

  if (exec_ok(target, "BEGIN") != 0) return 1;
  if (query_count(target, &count) != 0) return 1;
  if (count != 3) return fail_msg(case_name, "read transaction query mismatch");
  if (sqlite3_txn_state(target, "main") != SQLITE_TXN_READ) {{
    return fail_msg(case_name, "target is not in SQLITE_TXN_READ state");
  }}

  rc = sqlite3_deserialize(target, "main", data, size, size,
      SQLITE_DESERIALIZE_FREEONCLOSE);
  if (rc != SQLITE_BUSY) {{
    emit_diverge(case_name, rc);
  }}

  if (sqlite3_close(target) != SQLITE_OK) return fail_msg(case_name, "close target failed");
  if (sqlite3_close(src) != SQLITE_OK) return fail_msg(case_name, "close src failed");
  return 0;
}}

static int run_deserialize_backup_busy(const char *case_name, const char *event_name) {{
  sqlite3 *src = 0;
  sqlite3 *target = 0;
  sqlite3 *backup_dst = 0;
  sqlite3_backup *backup = 0;
  unsigned char *data = 0;
  sqlite3_int64 size = 0;
  int rc;

  emit_case(case_name);
  if (make_small_source(&src) != 0) return 1;
  if (make_small_source(&target) != 0) return 1;
  if (serialize_copy(src, &data, &size) != 0) return 1;

  if (open_memory(&backup_dst) != 0) return 1;
  backup = sqlite3_backup_init(backup_dst, "main", target, "main");
  if (backup == 0) return fail_msg(case_name, "sqlite3_backup_init returned NULL");

  rc = sqlite3_deserialize(target, "main", data, size, size,
      SQLITE_DESERIALIZE_FREEONCLOSE);
  if (rc != SQLITE_BUSY) {{
    emit_diverge(case_name, rc);
  }}

  rc = sqlite3_backup_finish(backup);
  if (rc != SQLITE_OK) return fail_rc("backup finish", SQLITE_OK, rc);
  if (sqlite3_close(backup_dst) != SQLITE_OK) return fail_msg(case_name, "close backup dst failed");
  if (sqlite3_close(target) != SQLITE_OK) return fail_msg(case_name, "close target failed");
  if (sqlite3_close(src) != SQLITE_OK) return fail_msg(case_name, "close src failed");
  return 0;
}}

static int run_deserialize_null_schema_main(const char *case_name, const char *event_name) {{
  sqlite3 *src = 0;
  sqlite3 *target = 0;
  unsigned char *data = 0;
  sqlite3_int64 size = 0;
  int rc;

  emit_case(case_name);
  if (make_small_source(&src) != 0 || open_memory(&target) != 0) return 1;
  if (serialize_copy(src, &data, &size) != 0) return 1;

  rc = sqlite3_deserialize(target, 0, data, size, size, SQLITE_DESERIALIZE_FREEONCLOSE);
  if (check_rc(case_name, event_name, "sqlite3_deserialize", SQLITE_OK, rc) != 0) return 1;
  if (check_count(case_name, event_name, target, "SELECT count(*) FROM t1", 3) != 0) return 1;

  if (sqlite3_close(target) != SQLITE_OK) return fail_msg(case_name, "close target failed");
  if (sqlite3_close(src) != SQLITE_OK) return fail_msg(case_name, "close src failed");
  return 0;
}}

static int run_deserialize_attached_schema(const char *case_name, const char *event_name) {{
  sqlite3 *src = 0;
  sqlite3 *target = 0;
  unsigned char *data = 0;
  sqlite3_int64 size = 0;
  int rc;

  emit_case(case_name);
  if (make_small_source(&src) != 0 || open_memory(&target) != 0) return 1;
  if (exec_ok(target, "ATTACH ':memory:' AS aux") != 0) return 1;
  if (serialize_copy(src, &data, &size) != 0) return 1;

  rc = sqlite3_deserialize(target, "aux", data, size, size, SQLITE_DESERIALIZE_FREEONCLOSE);
  if (check_rc(case_name, event_name, "sqlite3_deserialize", SQLITE_OK, rc) != 0) return 1;
  if (check_count(case_name, event_name, target, "SELECT count(*) FROM aux.t1", 3) != 0) return 1;

  if (sqlite3_close(target) != SQLITE_OK) return fail_msg(case_name, "close target failed");
  if (sqlite3_close(src) != SQLITE_OK) return fail_msg(case_name, "close src failed");
  return 0;
}}

static int run_deserialize_temp_schema_error(const char *case_name, const char *event_name) {{
  sqlite3 *src = 0;
  sqlite3 *target = 0;
  unsigned char *data = 0;
  sqlite3_int64 size = 0;
  int rc;

  emit_case(case_name);
  if (make_small_source(&src) != 0 || open_memory(&target) != 0) return 1;
  if (serialize_copy(src, &data, &size) != 0) return 1;

  rc = sqlite3_deserialize(target, "temp", data, size, size, SQLITE_DESERIALIZE_FREEONCLOSE);
  if (check_rc(case_name, event_name, "sqlite3_deserialize", SQLITE_ERROR, rc) != 0) return 1;

  if (sqlite3_close(target) != SQLITE_OK) return fail_msg(case_name, "close target failed");
  if (sqlite3_close(src) != SQLITE_OK) return fail_msg(case_name, "close src failed");
  return 0;
}}

static int run_deserialize_missing_schema_error(const char *case_name, const char *event_name) {{
  sqlite3 *src = 0;
  sqlite3 *target = 0;
  unsigned char *data = 0;
  sqlite3_int64 size = 0;
  int rc;

  emit_case(case_name);
  if (make_small_source(&src) != 0 || open_memory(&target) != 0) return 1;
  if (serialize_copy(src, &data, &size) != 0) return 1;

  rc = sqlite3_deserialize(target, "missing", data, size, size, SQLITE_DESERIALIZE_FREEONCLOSE);
  if (check_rc(case_name, event_name, "sqlite3_deserialize", SQLITE_ERROR, rc) != 0) return 1;

  if (sqlite3_close(target) != SQLITE_OK) return fail_msg(case_name, "close target failed");
  if (sqlite3_close(src) != SQLITE_OK) return fail_msg(case_name, "close src failed");
  return 0;
}}

static int run_deserialize_readonly_read_write(const char *case_name, const char *event_name) {{
  sqlite3 *src = 0;
  sqlite3 *target = 0;
  unsigned char *data = 0;
  sqlite3_int64 size = 0;
  int rc;

  emit_case(case_name);
  if (make_small_source(&src) != 0 || open_memory(&target) != 0) return 1;
  if (serialize_copy(src, &data, &size) != 0) return 1;

  rc = sqlite3_deserialize(target, "main", data, size, size,
      SQLITE_DESERIALIZE_FREEONCLOSE | SQLITE_DESERIALIZE_READONLY);
  if (check_rc(case_name, event_name, "sqlite3_deserialize", SQLITE_OK, rc) != 0) return 1;
  if (check_count(case_name, event_name, target, "SELECT count(*) FROM t1", 3) != 0) return 1;

  rc = exec_rc(target, "INSERT INTO t1 VALUES(4)");
  if (check_rc(case_name, event_name, "sqlite3_exec", SQLITE_READONLY, rc) != 0) return 1;

  if (sqlite3_close(target) != SQLITE_OK) return fail_msg(case_name, "close target failed");
  if (sqlite3_close(src) != SQLITE_OK) return fail_msg(case_name, "close src failed");
  return 0;
}}

static int run_deserialize_resizeable_growth(const char *case_name, const char *event_name) {{
  sqlite3 *src = 0;
  sqlite3 *target = 0;
  unsigned char *data = 0;
  sqlite3_int64 size = 0;
  sqlite3_int64 capacity = 0;
  int rc;

  emit_case(case_name);
  if (make_blob_source(&src) != 0 || open_memory(&target) != 0) return 1;
  if (serialize_copy(src, &data, &size) != 0) return 1;
  sqlite3_free(data);
  capacity = size + 1024 * 1024;
  if (serialize_with_capacity(src, &data, &size, capacity) != 0) return 1;

  rc = sqlite3_deserialize(target, "main", data, size, capacity,
      SQLITE_DESERIALIZE_FREEONCLOSE | SQLITE_DESERIALIZE_RESIZEABLE);
  if (check_rc(case_name, event_name, "sqlite3_deserialize", SQLITE_OK, rc) != 0) return 1;

  rc = exec_rc(target, "INSERT INTO t1 VALUES(zeroblob(200000))");
  if (check_rc(case_name, event_name, "sqlite3_exec", SQLITE_OK, rc) != 0) return 1;

  if (sqlite3_close(target) != SQLITE_OK) return fail_msg(case_name, "close target failed");
  if (sqlite3_close(src) != SQLITE_OK) return fail_msg(case_name, "close src failed");
  return 0;
}}

static int run_deserialize_nonresizeable_growth(const char *case_name, const char *event_name) {{
  sqlite3 *src = 0;
  sqlite3 *target = 0;
  unsigned char *data = 0;
  sqlite3_int64 size = 0;
  sqlite3_int64 capacity = 0;
  int rc;

  emit_case(case_name);
  if (make_blob_source(&src) != 0 || open_memory(&target) != 0) return 1;
  capacity = 1024 * 1024;
  if (serialize_with_capacity(src, &data, &size, capacity) != 0) return 1;

  rc = sqlite3_deserialize(target, "main", data, size, capacity, SQLITE_DESERIALIZE_FREEONCLOSE);
  if (check_rc(case_name, event_name, "sqlite3_deserialize", SQLITE_OK, rc) != 0) return 1;

  rc = exec_rc(target, "INSERT INTO t1 VALUES(zeroblob(100))");
  if (check_rc(case_name, event_name, "sqlite3_exec", SQLITE_OK, rc) != 0) return 1;

  rc = exec_rc(target, "INSERT INTO t1 VALUES(zeroblob(2000000))");
  if (check_rc(case_name, event_name, "sqlite3_exec", SQLITE_FULL, rc) != 0) return 1;

  if (sqlite3_close(target) != SQLITE_OK) return fail_msg(case_name, "close target failed");
  if (sqlite3_close(src) != SQLITE_OK) return fail_msg(case_name, "close src failed");
  return 0;
}}

int main(void) {{
  const char *scenario = "{model['scenario']}";
  const char *case_name = "{case_name}";
  const char *event_name = "{event_name}";
  (void)event_name;
  (void)"{expected_rc}";

  if (strcmp(scenario, "deserialize_read_txn_busy") == 0) {{
    return run_deserialize_read_txn_busy(case_name, event_name);
  }}
  if (strcmp(scenario, "deserialize_backup_busy") == 0) {{
    return run_deserialize_backup_busy(case_name, event_name);
  }}
  if (strcmp(scenario, "deserialize_null_schema_main") == 0) {{
    return run_deserialize_null_schema_main(case_name, event_name);
  }}
  if (strcmp(scenario, "deserialize_attached_schema") == 0) {{
    return run_deserialize_attached_schema(case_name, event_name);
  }}
  if (strcmp(scenario, "deserialize_temp_schema_error") == 0) {{
    return run_deserialize_temp_schema_error(case_name, event_name);
  }}
  if (strcmp(scenario, "deserialize_missing_schema_error") == 0) {{
    return run_deserialize_missing_schema_error(case_name, event_name);
  }}
  if (strcmp(scenario, "deserialize_readonly_read_write") == 0) {{
    return run_deserialize_readonly_read_write(case_name, event_name);
  }}
  if (strcmp(scenario, "deserialize_resizeable_growth") == 0) {{
    return run_deserialize_resizeable_growth(case_name, event_name);
  }}
  if (strcmp(scenario, "deserialize_nonresizeable_growth") == 0) {{
    return run_deserialize_nonresizeable_growth(case_name, event_name);
  }}

  fprintf(stderr, "unsupported serde scenario: %s\\n", scenario);
  return 2;
}}
"""
    out_path.write_text(source)


LIFECYCLE_C_TEMPLATE = r'''#include "sqlite3.h"

#include <stdio.h>
#include <string.h>

/* Generated from Quint ITF trace.
 * family: @@FAMILY@@
 * scenario: @@SCENARIO@@
 * expected_terminal_stage: @@EXPECTED_STAGE@@
 * observed_terminal_stage: @@OBSERVED_STAGE@@
 * inferred_steps: @@STEPS@@
 */

static void emit_case(const char *name) {
  printf("case %s\n", name);
}

static const char *rc_name(int rc) {
  switch (rc) {
    case SQLITE_OK: return "SQLITE_OK";
    case SQLITE_BUSY: return "SQLITE_BUSY";
    case SQLITE_LOCKED: return "SQLITE_LOCKED";
    case SQLITE_ERROR: return "SQLITE_ERROR";
    case SQLITE_MISUSE: return "SQLITE_MISUSE";
    case SQLITE_READONLY: return "SQLITE_READONLY";
    case SQLITE_FULL: return "SQLITE_FULL";
    case SQLITE_CANTOPEN: return "SQLITE_CANTOPEN";
    case SQLITE_DONE: return "SQLITE_DONE";
    case SQLITE_ROW: return "SQLITE_ROW";
    default: return "SQLITE_OTHER";
  }
}

static void emit_diverge_rc(
    const char *case_name,
    const char *event_name,
    const char *api_name,
    int expected_rc,
    int observed_rc) {
  printf("diverge %s %s api=%s expected=%s observed=%s\n",
      case_name,
      event_name,
      api_name,
      rc_name(expected_rc),
      rc_name(observed_rc));
}

static void emit_diverge_text(
    const char *case_name,
    const char *event_name,
    const char *api_name,
    const char *expected,
    const char *observed) {
  printf("diverge %s %s api=%s expected=%s observed=%s\n",
      case_name,
      event_name,
      api_name,
      expected,
      observed);
}

static int fail_msg(const char *name, const char *msg) {
  fprintf(stderr, "%s: %s\n", name, msg);
  return 1;
}

static int check_rc(
    const char *case_name,
    const char *event_name,
    const char *api_name,
    int expected,
    int observed) {
  if (observed == expected) return 0;
  emit_diverge_rc(case_name, event_name, api_name, expected, observed);
  return 1;
}

static int check_rc_busy_or_locked(
    const char *case_name,
    const char *event_name,
    const char *api_name,
    int observed) {
  if (observed == SQLITE_BUSY || observed == SQLITE_LOCKED) return 0;
  emit_diverge_text(
      case_name,
      event_name,
      api_name,
      "SQLITE_BUSY_or_SQLITE_LOCKED",
      rc_name(observed));
  return 1;
}

static int open_memory(sqlite3 **db) {
  int rc = sqlite3_open(":memory:", db);
  if (rc != SQLITE_OK) {
    fprintf(stderr, "sqlite3_open(:memory:) failed rc=%d\n", rc);
    return 1;
  }
  return 0;
}

static int exec_ok(sqlite3 *db, const char *sql) {
  char *errmsg = 0;
  int rc = sqlite3_exec(db, sql, 0, 0, &errmsg);
  if (rc != SQLITE_OK) {
    fprintf(stderr, "sqlite3_exec failed rc=%d sql=%s errmsg=%s\n",
        rc, sql, errmsg ? errmsg : "(null)");
    sqlite3_free(errmsg);
    return 1;
  }
  return 0;
}

static int make_small_source(sqlite3 **db) {
  if (open_memory(db) != 0) return 1;
  return exec_ok(*db,
      "CREATE TABLE t1(a INTEGER PRIMARY KEY);"
      "INSERT INTO t1 VALUES(1),(2),(3);");
}

static int make_large_source(sqlite3 **db) {
  if (open_memory(db) != 0) return 1;
  return exec_ok(*db,
      "PRAGMA page_size=512;"
      "CREATE TABLE t1(x BLOB);"
      "WITH RECURSIVE c(x) AS (VALUES(1) UNION ALL SELECT x+1 FROM c WHERE x<200)"
      "INSERT INTO t1 SELECT zeroblob(400) FROM c;");
}

static int prepare_select(sqlite3 *db, sqlite3_stmt **stmt) {
  int rc = sqlite3_prepare_v2(db, "SELECT 1", -1, stmt, 0);
  if (rc != SQLITE_OK) {
    fprintf(stderr, "sqlite3_prepare_v2 failed rc=%d errmsg=%s\n", rc, sqlite3_errmsg(db));
    return 1;
  }
  return 0;
}

static int start_read_txn(sqlite3 *db, sqlite3_stmt **stmt) {
  int rc = sqlite3_prepare_v2(db, "SELECT a FROM t1 ORDER BY a", -1, stmt, 0);
  if (rc != SQLITE_OK) {
    fprintf(stderr, "prepare read txn failed rc=%d errmsg=%s\n", rc, sqlite3_errmsg(db));
    return 1;
  }
  rc = sqlite3_step(*stmt);
  if (rc != SQLITE_ROW) {
    sqlite3_finalize(*stmt);
    fprintf(stderr, "read txn step failed rc=%d\n", rc);
    return 1;
  }
  return 0;
}

static int query_count(sqlite3 *db, const char *sql, int *count) {
  sqlite3_stmt *stmt = 0;
  int rc = sqlite3_prepare_v2(db, sql, -1, &stmt, 0);
  if (rc != SQLITE_OK) {
    fprintf(stderr, "prepare count failed rc=%d errmsg=%s\n", rc, sqlite3_errmsg(db));
    return 1;
  }
  rc = sqlite3_step(stmt);
  if (rc != SQLITE_ROW) {
    sqlite3_finalize(stmt);
    fprintf(stderr, "count step failed rc=%d\n", rc);
    return 1;
  }
  *count = sqlite3_column_int(stmt, 0);
  rc = sqlite3_finalize(stmt);
  if (rc != SQLITE_OK) {
    fprintf(stderr, "count finalize failed rc=%d\n", rc);
    return 1;
  }
  return 0;
}

static int open_backup(sqlite3 **src, sqlite3 **dst, sqlite3_backup **backup) {
  if (make_small_source(src) != 0 || open_memory(dst) != 0) return 1;
  *backup = sqlite3_backup_init(*dst, "main", *src, "main");
  if (*backup == 0) {
    fprintf(stderr, "sqlite3_backup_init failed dst_err=%s src_err=%s\n",
        sqlite3_errmsg(*dst), sqlite3_errmsg(*src));
    return 1;
  }
  return 0;
}

typedef struct PrepareObservation {
  int rc;
  int has_stmt;
  long tail_offset;
  int column_count;
  int step_rc;
  int first_value;
  int finalize_rc;
  char errmsg[160];
} PrepareObservation;

static void observe_prepare(
    sqlite3 *db,
    const char *sql,
    int nbyte,
    int use_v3,
    PrepareObservation *out) {
  sqlite3_stmt *stmt = 0;
  const char *tail = 0;
  memset(out, 0, sizeof(*out));
  out->column_count = -1;
  out->step_rc = -1;
  out->finalize_rc = SQLITE_OK;

  if (use_v3) {
    out->rc = sqlite3_prepare_v3(db, sql, nbyte, 0, &stmt, &tail);
  } else {
    out->rc = sqlite3_prepare_v2(db, sql, nbyte, &stmt, &tail);
  }

  out->has_stmt = stmt != 0;
  out->tail_offset = tail ? (long)(tail - sql) : -1;
  snprintf(out->errmsg, sizeof(out->errmsg), "%s", sqlite3_errmsg(db));

  if (out->rc == SQLITE_OK && stmt != 0) {
    out->column_count = sqlite3_column_count(stmt);
    out->step_rc = sqlite3_step(stmt);
    if (out->step_rc == SQLITE_ROW && out->column_count > 0) {
      out->first_value = sqlite3_column_int(stmt, 0);
    }
    out->finalize_rc = sqlite3_finalize(stmt);
  } else if (stmt != 0) {
    out->finalize_rc = sqlite3_finalize(stmt);
  }
}

static int compare_observations(
    const char *case_name,
    const char *event_name,
    const char *subcase,
    const PrepareObservation *v2,
    const PrepareObservation *v3) {
  (void)subcase;
  if (v2->rc != v3->rc) {
    emit_diverge_text(case_name, event_name, "sqlite3_prepare_v2_v3", "equal", "rc_mismatch");
    return 1;
  }
  if (v2->has_stmt != v3->has_stmt) {
    emit_diverge_text(case_name, event_name, "sqlite3_prepare_v2_v3", "equal", "stmt_presence_mismatch");
    return 1;
  }
  if (v2->tail_offset != v3->tail_offset) {
    emit_diverge_text(case_name, event_name, "sqlite3_prepare_v2_v3", "equal", "tail_mismatch");
    return 1;
  }
  if (v2->column_count != v3->column_count) {
    emit_diverge_text(case_name, event_name, "sqlite3_prepare_v2_v3", "equal", "column_count_mismatch");
    return 1;
  }
  if (v2->step_rc != v3->step_rc) {
    emit_diverge_text(case_name, event_name, "sqlite3_prepare_v2_v3", "equal", "step_rc_mismatch");
    return 1;
  }
  if (v2->first_value != v3->first_value) {
    emit_diverge_text(case_name, event_name, "sqlite3_prepare_v2_v3", "equal", "first_value_mismatch");
    return 1;
  }
  if (v2->finalize_rc != v3->finalize_rc) {
    emit_diverge_text(case_name, event_name, "sqlite3_prepare_v2_v3", "equal", "finalize_rc_mismatch");
    return 1;
  }
  if (strcmp(v2->errmsg, v3->errmsg) != 0) {
    emit_diverge_text(case_name, event_name, "sqlite3_prepare_v2_v3", "equal", "errmsg_mismatch");
    return 1;
  }
  return 0;
}

static int run_finalize_null(const char *case_name, const char *event_name) {
  int rc;
  emit_case(case_name);
  rc = sqlite3_finalize(0);
  return check_rc(case_name, event_name, "sqlite3_finalize", SQLITE_OK, rc);
}

static int run_close_null(const char *case_name, const char *event_name) {
  int rc;
  emit_case(case_name);
  rc = sqlite3_close(0);
  if (check_rc(case_name, event_name, "sqlite3_close", SQLITE_OK, rc) != 0) return 1;
  rc = sqlite3_close_v2(0);
  if (check_rc(case_name, event_name, "sqlite3_close_v2", SQLITE_OK, rc) != 0) return 1;
  return 0;
}

static int run_close_live_stmt(const char *case_name, const char *event_name) {
  sqlite3 *db = 0;
  sqlite3_stmt *stmt = 0;
  int rc;

  emit_case(case_name);
  if (open_memory(&db) != 0 || prepare_select(db, &stmt) != 0) return 1;

  rc = sqlite3_close(db);
  if (check_rc(case_name, event_name, "sqlite3_close", SQLITE_BUSY, rc) != 0) return 1;
  rc = sqlite3_step(stmt);
  if (check_rc(case_name, event_name, "sqlite3_step", SQLITE_ROW, rc) != 0) return 1;
  rc = sqlite3_finalize(stmt);
  if (check_rc(case_name, event_name, "sqlite3_finalize", SQLITE_OK, rc) != 0) return 1;
  rc = sqlite3_close(db);
  if (check_rc(case_name, event_name, "sqlite3_close", SQLITE_OK, rc) != 0) return 1;
  return 0;
}

static int run_close_v2_live_stmt(const char *case_name, const char *event_name) {
  sqlite3 *db = 0;
  sqlite3_stmt *stmt = 0;
  int rc;

  emit_case(case_name);
  if (open_memory(&db) != 0 || prepare_select(db, &stmt) != 0) return 1;

  rc = sqlite3_close_v2(db);
  if (check_rc(case_name, event_name, "sqlite3_close_v2", SQLITE_OK, rc) != 0) return 1;
  rc = sqlite3_step(stmt);
  if (check_rc(case_name, event_name, "sqlite3_step", SQLITE_ROW, rc) != 0) return 1;
  rc = sqlite3_finalize(stmt);
  if (check_rc(case_name, event_name, "sqlite3_finalize", SQLITE_OK, rc) != 0) return 1;
  return 0;
}

static int run_prepare_v2_v3_zero_flags(const char *case_name, const char *event_name) {
  sqlite3 *db = 0;
  PrepareObservation v2;
  PrepareObservation v3;
  int rc;

  static const char sql_trunc[] = "SELECT 12; SELECT 99";
  static const char sql_embedded_nul[] = "SELECT 7\0SELECT 99";

  struct {
    const char *name;
    const char *sql;
    int nbyte;
  } cases[] = {
    {"success", "SELECT 41+1", -1},
    {"syntax_error", "SELECT FROM", -1},
    {"tail", "SELECT 1; SELECT 2", -1},
    {"nbyte_truncation", sql_trunc, (int)strlen("SELECT 12")},
    {"embedded_nul", sql_embedded_nul, (int)sizeof(sql_embedded_nul) - 1},
    {"zero_nbyte", "SELECT 1", 0},
  };
  size_t i;

  emit_case(case_name);
  if (open_memory(&db) != 0) return 1;

  for (i = 0; i < sizeof(cases) / sizeof(cases[0]); ++i) {
    observe_prepare(db, cases[i].sql, cases[i].nbyte, 0, &v2);
    observe_prepare(db, cases[i].sql, cases[i].nbyte, 1, &v3);
    if (compare_observations(case_name, event_name, cases[i].name, &v2, &v3) != 0) {
      sqlite3_close(db);
      return 1;
    }
  }

  rc = sqlite3_close(db);
  if (check_rc(case_name, event_name, "sqlite3_close", SQLITE_OK, rc) != 0) return 1;
  return 0;
}

static int run_close_live_backup(const char *case_name, const char *event_name) {
  sqlite3 *src = 0;
  sqlite3 *dst = 0;
  sqlite3_backup *backup = 0;
  int rc;

  emit_case(case_name);
  if (open_backup(&src, &dst, &backup) != 0) return 1;

  rc = sqlite3_close(src);
  if (check_rc(case_name, event_name, "sqlite3_close", SQLITE_BUSY, rc) != 0) return 1;
  rc = sqlite3_backup_step(backup, -1);
  if (check_rc(case_name, event_name, "sqlite3_backup_step", SQLITE_DONE, rc) != 0) return 1;
  rc = sqlite3_backup_finish(backup);
  if (check_rc(case_name, event_name, "sqlite3_backup_finish", SQLITE_OK, rc) != 0) return 1;
  rc = sqlite3_close(src);
  if (check_rc(case_name, event_name, "sqlite3_close", SQLITE_OK, rc) != 0) return 1;
  rc = sqlite3_close(dst);
  if (check_rc(case_name, event_name, "sqlite3_close", SQLITE_OK, rc) != 0) return 1;
  return 0;
}

static int run_close_v2_live_backup(const char *case_name, const char *event_name) {
  sqlite3 *src = 0;
  sqlite3 *dst = 0;
  sqlite3_backup *backup = 0;
  int rc;

  emit_case(case_name);
  if (open_backup(&src, &dst, &backup) != 0) return 1;

  rc = sqlite3_close_v2(src);
  if (check_rc(case_name, event_name, "sqlite3_close_v2", SQLITE_OK, rc) != 0) return 1;
  rc = sqlite3_backup_finish(backup);
  if (check_rc(case_name, event_name, "sqlite3_backup_finish", SQLITE_OK, rc) != 0) return 1;
  rc = sqlite3_close(dst);
  if (check_rc(case_name, event_name, "sqlite3_close", SQLITE_OK, rc) != 0) return 1;
  return 0;
}

static int run_backup_step_done_finish(const char *case_name, const char *event_name) {
  sqlite3 *src = 0;
  sqlite3 *dst = 0;
  sqlite3_backup *backup = 0;
  int count = 0;
  int rc;

  emit_case(case_name);
  if (make_small_source(&src) != 0 || open_memory(&dst) != 0) return 1;

  backup = sqlite3_backup_init(dst, "main", src, "main");
  if (backup == 0) return fail_msg(case_name, "sqlite3_backup_init returned NULL");

  rc = sqlite3_backup_step(backup, -1);
  if (check_rc(case_name, event_name, "sqlite3_backup_step", SQLITE_DONE, rc) != 0) return 1;
  rc = sqlite3_backup_finish(backup);
  if (check_rc(case_name, event_name, "sqlite3_backup_finish", SQLITE_OK, rc) != 0) return 1;

  if (query_count(dst, "SELECT count(*) FROM t1", &count) != 0) return 1;
  if (count != 3) {
    emit_diverge_text(case_name, event_name, "sqlite3_backup", "count=3", "count_mismatch");
    return 1;
  }

  rc = sqlite3_close(dst);
  if (check_rc(case_name, event_name, "sqlite3_close", SQLITE_OK, rc) != 0) return 1;
  rc = sqlite3_close(src);
  if (check_rc(case_name, event_name, "sqlite3_close", SQLITE_OK, rc) != 0) return 1;
  return 0;
}

static int run_backup_finish_incomplete(const char *case_name, const char *event_name) {
  sqlite3 *src = 0;
  sqlite3 *dst = 0;
  sqlite3_backup *backup = 0;
  int page_count = 0;
  int rc;

  emit_case(case_name);
  if (make_large_source(&src) != 0 || open_memory(&dst) != 0) return 1;
  if (query_count(src, "PRAGMA page_count", &page_count) != 0) return 1;
  if (page_count <= 1) return fail_msg(case_name, "large source did not allocate multiple pages");

  backup = sqlite3_backup_init(dst, "main", src, "main");
  if (backup == 0) return fail_msg(case_name, "sqlite3_backup_init returned NULL");

  rc = sqlite3_backup_step(backup, 1);
  if (check_rc(case_name, event_name, "sqlite3_backup_step", SQLITE_OK, rc) != 0) return 1;
  rc = sqlite3_backup_finish(backup);
  if (check_rc(case_name, event_name, "sqlite3_backup_finish", SQLITE_OK, rc) != 0) return 1;

  rc = sqlite3_close(dst);
  if (check_rc(case_name, event_name, "sqlite3_close", SQLITE_OK, rc) != 0) return 1;
  rc = sqlite3_close(src);
  if (check_rc(case_name, event_name, "sqlite3_close", SQLITE_OK, rc) != 0) return 1;
  return 0;
}

static int run_backup_step_zero_no_progress(const char *case_name, const char *event_name) {
  sqlite3 *src = 0;
  sqlite3 *dst = 0;
  sqlite3_backup *backup = 0;
  int remaining_before = 0;
  int remaining_after = 0;
  int page_count_before = 0;
  int page_count_after = 0;
  int count = 0;
  int rc;

  emit_case(case_name);
  if (make_large_source(&src) != 0 || open_memory(&dst) != 0) return 1;

  backup = sqlite3_backup_init(dst, "main", src, "main");
  if (backup == 0) return fail_msg(case_name, "sqlite3_backup_init returned NULL");

  rc = sqlite3_backup_step(backup, 1);
  if (check_rc(case_name, event_name, "sqlite3_backup_step", SQLITE_OK, rc) != 0) return 1;

  remaining_before = sqlite3_backup_remaining(backup);
  page_count_before = sqlite3_backup_pagecount(backup);
  if (remaining_before <= 0 || page_count_before <= 0) {
    return fail_msg(case_name, "backup counters were not initialized after first step");
  }

  rc = sqlite3_backup_step(backup, 0);
  if (check_rc(case_name, event_name, "sqlite3_backup_step", SQLITE_OK, rc) != 0) return 1;

  remaining_after = sqlite3_backup_remaining(backup);
  page_count_after = sqlite3_backup_pagecount(backup);

  if (remaining_after != remaining_before) {
    emit_diverge_text(case_name, event_name, "sqlite3_backup_remaining", "unchanged", "changed");
    return 1;
  }
  if (page_count_after != page_count_before) {
    emit_diverge_text(case_name, event_name, "sqlite3_backup_pagecount", "unchanged", "changed");
    return 1;
  }

  rc = sqlite3_backup_step(backup, -1);
  if (check_rc(case_name, event_name, "sqlite3_backup_step", SQLITE_DONE, rc) != 0) return 1;
  rc = sqlite3_backup_finish(backup);
  if (check_rc(case_name, event_name, "sqlite3_backup_finish", SQLITE_OK, rc) != 0) return 1;

  if (query_count(dst, "SELECT count(*) FROM t1", &count) != 0) return 1;
  if (count != 200) {
    emit_diverge_text(case_name, event_name, "sqlite3_backup", "count=200", "count_mismatch");
    return 1;
  }

  rc = sqlite3_close(dst);
  if (check_rc(case_name, event_name, "sqlite3_close", SQLITE_OK, rc) != 0) return 1;
  rc = sqlite3_close(src);
  if (check_rc(case_name, event_name, "sqlite3_close", SQLITE_OK, rc) != 0) return 1;
  return 0;
}

static int run_backup_step_negative_all_remaining_done(
    const char *case_name,
    const char *event_name) {
  sqlite3 *src = 0;
  sqlite3 *dst = 0;
  sqlite3_backup *backup = 0;
  int remaining = 0;
  int count = 0;
  int rc;

  emit_case(case_name);
  if (make_large_source(&src) != 0 || open_memory(&dst) != 0) return 1;

  backup = sqlite3_backup_init(dst, "main", src, "main");
  if (backup == 0) return fail_msg(case_name, "sqlite3_backup_init returned NULL");

  rc = sqlite3_backup_step(backup, -1);
  if (check_rc(case_name, event_name, "sqlite3_backup_step", SQLITE_DONE, rc) != 0) return 1;

  remaining = sqlite3_backup_remaining(backup);
  if (remaining != 0) {
    emit_diverge_text(case_name, event_name, "sqlite3_backup_remaining", "0", "nonzero");
    return 1;
  }

  rc = sqlite3_backup_finish(backup);
  if (check_rc(case_name, event_name, "sqlite3_backup_finish", SQLITE_OK, rc) != 0) return 1;

  if (query_count(dst, "SELECT count(*) FROM t1", &count) != 0) return 1;
  if (count != 200) {
    emit_diverge_text(case_name, event_name, "sqlite3_backup", "count=200", "count_mismatch");
    return 1;
  }

  rc = sqlite3_close(dst);
  if (check_rc(case_name, event_name, "sqlite3_close", SQLITE_OK, rc) != 0) return 1;
  rc = sqlite3_close(src);
  if (check_rc(case_name, event_name, "sqlite3_close", SQLITE_OK, rc) != 0) return 1;
  return 0;
}

static int run_backup_step_transient_conflict_retry(const char *case_name, const char *event_name) {
  sqlite3 *src = 0;
  sqlite3 *dst = 0;
  sqlite3_backup *backup = 0;
  int count = 0;
  int rc;

  emit_case(case_name);
  if (make_large_source(&src) != 0 || open_memory(&dst) != 0) return 1;

  backup = sqlite3_backup_init(dst, "main", src, "main");
  if (backup == 0) return fail_msg(case_name, "sqlite3_backup_init returned NULL");

  if (exec_ok(src, "BEGIN; INSERT INTO t1 VALUES(zeroblob(400));") != 0) return 1;

  rc = sqlite3_backup_step(backup, 5000);
  if (check_rc_busy_or_locked(case_name, event_name, "sqlite3_backup_step", rc) != 0) {
    sqlite3_exec(src, "ROLLBACK", 0, 0, 0);
    sqlite3_backup_finish(backup);
    return 1;
  }

  if (exec_ok(src, "ROLLBACK") != 0) return 1;

  rc = sqlite3_backup_step(backup, -1);
  if (check_rc(case_name, event_name, "sqlite3_backup_step", SQLITE_DONE, rc) != 0) return 1;

  rc = sqlite3_backup_finish(backup);
  if (check_rc(case_name, event_name, "sqlite3_backup_finish", SQLITE_OK, rc) != 0) return 1;

  if (query_count(dst, "SELECT count(*) FROM t1", &count) != 0) return 1;
  if (count != 200) {
    emit_diverge_text(case_name, event_name, "sqlite3_backup", "count=200", "count_mismatch");
    return 1;
  }

  rc = sqlite3_close(dst);
  if (check_rc(case_name, event_name, "sqlite3_close", SQLITE_OK, rc) != 0) return 1;
  rc = sqlite3_close(src);
  if (check_rc(case_name, event_name, "sqlite3_close", SQLITE_OK, rc) != 0) return 1;
  return 0;
}

static int run_backup_init_same_connection_error(const char *case_name, const char *event_name) {
  sqlite3 *db = 0;
  sqlite3_backup *backup = 0;
  int rc;

  emit_case(case_name);
  if (make_small_source(&db) != 0) return 1;

  backup = sqlite3_backup_init(db, "main", db, "main");
  if (backup != 0) {
    sqlite3_backup_finish(backup);
    emit_diverge_text(case_name, event_name, "sqlite3_backup_init", "NULL", "handle");
    return 1;
  }
  rc = sqlite3_errcode(db);
  if (check_rc(case_name, event_name, "sqlite3_errcode", SQLITE_ERROR, rc) != 0) return 1;

  rc = sqlite3_close(db);
  if (check_rc(case_name, event_name, "sqlite3_close", SQLITE_OK, rc) != 0) return 1;
  return 0;
}

static int run_backup_init_dest_read_txn_error(const char *case_name, const char *event_name) {
  sqlite3 *src = 0;
  sqlite3 *dst = 0;
  sqlite3_stmt *stmt = 0;
  sqlite3_backup *backup = 0;
  int rc;

  emit_case(case_name);
  if (make_small_source(&src) != 0 || make_small_source(&dst) != 0) return 1;
  if (start_read_txn(dst, &stmt) != 0) return 1;

  backup = sqlite3_backup_init(dst, "main", src, "main");
  if (backup != 0) {
    sqlite3_backup_finish(backup);
    emit_diverge_text(case_name, event_name, "sqlite3_backup_init", "NULL", "handle");
    sqlite3_finalize(stmt);
    return 1;
  }
  rc = sqlite3_errcode(dst);
  if (check_rc(case_name, event_name, "sqlite3_errcode", SQLITE_ERROR, rc) != 0) {
    sqlite3_finalize(stmt);
    return 1;
  }

  rc = sqlite3_finalize(stmt);
  if (check_rc(case_name, event_name, "sqlite3_finalize", SQLITE_OK, rc) != 0) return 1;
  rc = sqlite3_close(dst);
  if (check_rc(case_name, event_name, "sqlite3_close", SQLITE_OK, rc) != 0) return 1;
  rc = sqlite3_close(src);
  if (check_rc(case_name, event_name, "sqlite3_close", SQLITE_OK, rc) != 0) return 1;
  return 0;
}

int main(void) {
  const char *scenario = "@@SCENARIO@@";
  const char *case_name = "@@CASE_NAME@@";
  const char *event_name = "@@EVENT_NAME@@";

  if (strcmp(scenario, "finalize_null") == 0) {
    return run_finalize_null(case_name, event_name);
  }
  if (strcmp(scenario, "close_null") == 0) {
    return run_close_null(case_name, event_name);
  }
  if (strcmp(scenario, "close_live_stmt") == 0) {
    return run_close_live_stmt(case_name, event_name);
  }
  if (strcmp(scenario, "close_v2_live_stmt") == 0) {
    return run_close_v2_live_stmt(case_name, event_name);
  }
  if (strcmp(scenario, "prepare_v2_v3_zero_flags") == 0) {
    return run_prepare_v2_v3_zero_flags(case_name, event_name);
  }
  if (strcmp(scenario, "close_live_backup") == 0) {
    return run_close_live_backup(case_name, event_name);
  }
  if (strcmp(scenario, "close_v2_live_backup") == 0) {
    return run_close_v2_live_backup(case_name, event_name);
  }
  if (strcmp(scenario, "backup_step_done_finish") == 0) {
    return run_backup_step_done_finish(case_name, event_name);
  }
  if (strcmp(scenario, "backup_finish_incomplete") == 0) {
    return run_backup_finish_incomplete(case_name, event_name);
  }
  if (strcmp(scenario, "backup_step_zero_no_progress") == 0) {
    return run_backup_step_zero_no_progress(case_name, event_name);
  }
  if (strcmp(scenario, "backup_step_negative_all_remaining_done") == 0) {
    return run_backup_step_negative_all_remaining_done(case_name, event_name);
  }
  if (strcmp(scenario, "backup_step_transient_conflict_retry") == 0) {
    return run_backup_step_transient_conflict_retry(case_name, event_name);
  }
  if (strcmp(scenario, "backup_init_same_connection_error") == 0) {
    return run_backup_init_same_connection_error(case_name, event_name);
  }
  if (strcmp(scenario, "backup_init_dest_read_txn_error") == 0) {
    return run_backup_init_dest_read_txn_error(case_name, event_name);
  }

  fprintf(stderr, "unsupported lifecycle scenario: %s\n", scenario);
  return 2;
}
'''


def emit_c_lifecycle(model: dict[str, object], out_path: Path) -> None:
    steps = ", ".join(str(step) for step in model["steps"])
    source = (
        LIFECYCLE_C_TEMPLATE
        .replace("@@FAMILY@@", str(model["family"]))
        .replace("@@SCENARIO@@", str(model["scenario"]))
        .replace("@@CASE_NAME@@", str(model["case_name"]))
        .replace("@@EVENT_NAME@@", str(model["event_name"]))
        .replace("@@EXPECTED_STAGE@@", str(model["expected_terminal_stage"]))
        .replace("@@OBSERVED_STAGE@@", str(model["observed_terminal_stage"]))
        .replace("@@STEPS@@", steps)
    )
    out_path.write_text(source)


STMT_C_TEMPLATE = r'''#include "sqlite3.h"

#include <stdio.h>
#include <string.h>

/* Generated from Quint ITF trace.
 * family: @@FAMILY@@
 * scenario: @@SCENARIO@@
 * expected_terminal_stage: @@EXPECTED_STAGE@@
 * observed_terminal_stage: @@OBSERVED_STAGE@@
 * inferred_steps: @@STEPS@@
 */

static void emit_case(const char *name) {
  printf("case %s\n", name);
}

static const char *rc_name(int rc) {
  switch (rc) {
    case SQLITE_OK: return "SQLITE_OK";
    case SQLITE_BUSY: return "SQLITE_BUSY";
    case SQLITE_ERROR: return "SQLITE_ERROR";
    case SQLITE_MISUSE: return "SQLITE_MISUSE";
    case SQLITE_READONLY: return "SQLITE_READONLY";
    case SQLITE_FULL: return "SQLITE_FULL";
    case SQLITE_CANTOPEN: return "SQLITE_CANTOPEN";
    case SQLITE_DONE: return "SQLITE_DONE";
    case SQLITE_ROW: return "SQLITE_ROW";
    default: return "SQLITE_OTHER";
  }
}

static void emit_diverge_rc(
    const char *case_name,
    const char *event_name,
    const char *api_name,
    int expected_rc,
    int observed_rc) {
  printf("diverge %s %s api=%s expected=%s observed=%s\n",
      case_name,
      event_name,
      api_name,
      rc_name(expected_rc),
      rc_name(observed_rc));
}

static void emit_diverge_text(
    const char *case_name,
    const char *event_name,
    const char *api_name,
    const char *expected,
    const char *observed) {
  printf("diverge %s %s api=%s expected=%s observed=%s\n",
      case_name,
      event_name,
      api_name,
      expected,
      observed);
}

static int check_rc(
    const char *case_name,
    const char *event_name,
    const char *api_name,
    int expected,
    int observed) {
  if (observed == expected) return 0;
  emit_diverge_rc(case_name, event_name, api_name, expected, observed);
  return 1;
}

static int open_memory(sqlite3 **db) {
  int rc = sqlite3_open(":memory:", db);
  if (rc != SQLITE_OK) {
    fprintf(stderr, "sqlite3_open(:memory:) failed rc=%d\n", rc);
    return 1;
  }
  return 0;
}

static int check_text(
    const char *case_name,
    const char *event_name,
    sqlite3_stmt *stmt,
    int i_col,
    const char *expected) {
  const unsigned char *text = sqlite3_column_text(stmt, i_col);
  if (text == 0 || strcmp((const char *)text, expected) != 0) {
    emit_diverge_text(case_name, event_name, "sqlite3_column_text", expected, text ? (const char *)text : "NULL");
    return 1;
  }
  return 0;
}

static int run_bind_reset_retains(const char *case_name, const char *event_name) {
  sqlite3 *db = 0;
  sqlite3_stmt *stmt = 0;
  int rc;

  emit_case(case_name);
  if (open_memory(&db) != 0) return 1;
  rc = sqlite3_prepare_v2(db, "SELECT ?1, ?2", -1, &stmt, 0);
  if (check_rc(case_name, event_name, "sqlite3_prepare_v2", SQLITE_OK, rc) != 0) return 1;
  rc = sqlite3_bind_int(stmt, 1, 11);
  if (check_rc(case_name, event_name, "sqlite3_bind_int", SQLITE_OK, rc) != 0) return 1;
  rc = sqlite3_bind_text(stmt, 2, "abc", -1, SQLITE_STATIC);
  if (check_rc(case_name, event_name, "sqlite3_bind_text", SQLITE_OK, rc) != 0) return 1;

  rc = sqlite3_step(stmt);
  if (check_rc(case_name, event_name, "sqlite3_step", SQLITE_ROW, rc) != 0) return 1;
  if (sqlite3_column_int(stmt, 0) != 11) {
    emit_diverge_text(case_name, event_name, "sqlite3_column_int", "11", "mismatch");
    return 1;
  }
  if (check_text(case_name, event_name, stmt, 1, "abc") != 0) return 1;

  rc = sqlite3_reset(stmt);
  if (check_rc(case_name, event_name, "sqlite3_reset", SQLITE_OK, rc) != 0) return 1;
  rc = sqlite3_step(stmt);
  if (check_rc(case_name, event_name, "sqlite3_step", SQLITE_ROW, rc) != 0) return 1;
  if (sqlite3_column_int(stmt, 0) != 11) {
    emit_diverge_text(case_name, event_name, "sqlite3_column_int", "11", "mismatch");
    return 1;
  }
  if (check_text(case_name, event_name, stmt, 1, "abc") != 0) return 1;

  rc = sqlite3_finalize(stmt);
  if (check_rc(case_name, event_name, "sqlite3_finalize", SQLITE_OK, rc) != 0) return 1;
  rc = sqlite3_close(db);
  if (check_rc(case_name, event_name, "sqlite3_close", SQLITE_OK, rc) != 0) return 1;
  return 0;
}

static int run_clear_bindings_null(const char *case_name, const char *event_name) {
  sqlite3 *db = 0;
  sqlite3_stmt *stmt = 0;
  int rc;

  emit_case(case_name);
  if (open_memory(&db) != 0) return 1;
  rc = sqlite3_prepare_v2(db, "SELECT ?1, ?2", -1, &stmt, 0);
  if (check_rc(case_name, event_name, "sqlite3_prepare_v2", SQLITE_OK, rc) != 0) return 1;
  rc = sqlite3_bind_int(stmt, 1, 5);
  if (check_rc(case_name, event_name, "sqlite3_bind_int", SQLITE_OK, rc) != 0) return 1;
  rc = sqlite3_bind_int(stmt, 2, 9);
  if (check_rc(case_name, event_name, "sqlite3_bind_int", SQLITE_OK, rc) != 0) return 1;
  rc = sqlite3_step(stmt);
  if (check_rc(case_name, event_name, "sqlite3_step", SQLITE_ROW, rc) != 0) return 1;
  rc = sqlite3_reset(stmt);
  if (check_rc(case_name, event_name, "sqlite3_reset", SQLITE_OK, rc) != 0) return 1;
  rc = sqlite3_clear_bindings(stmt);
  if (check_rc(case_name, event_name, "sqlite3_clear_bindings", SQLITE_OK, rc) != 0) return 1;

  rc = sqlite3_step(stmt);
  if (check_rc(case_name, event_name, "sqlite3_step", SQLITE_ROW, rc) != 0) return 1;
  if (sqlite3_column_type(stmt, 0) != SQLITE_NULL || sqlite3_column_type(stmt, 1) != SQLITE_NULL) {
    emit_diverge_text(case_name, event_name, "sqlite3_column_type", "SQLITE_NULL,SQLITE_NULL", "mismatch");
    return 1;
  }
  if (sqlite3_column_bytes(stmt, 0) != 0 || sqlite3_column_bytes(stmt, 1) != 0) {
    emit_diverge_text(case_name, event_name, "sqlite3_column_bytes", "0,0", "mismatch");
    return 1;
  }

  rc = sqlite3_finalize(stmt);
  if (check_rc(case_name, event_name, "sqlite3_finalize", SQLITE_OK, rc) != 0) return 1;
  rc = sqlite3_close(db);
  if (check_rc(case_name, event_name, "sqlite3_close", SQLITE_OK, rc) != 0) return 1;
  return 0;
}

static int run_bind_after_step_misuse(const char *case_name, const char *event_name) {
  sqlite3 *db = 0;
  sqlite3_stmt *stmt = 0;
  int rc;

  emit_case(case_name);
  if (open_memory(&db) != 0) return 1;
  rc = sqlite3_prepare_v2(db, "SELECT ?1", -1, &stmt, 0);
  if (check_rc(case_name, event_name, "sqlite3_prepare_v2", SQLITE_OK, rc) != 0) return 1;
  rc = sqlite3_step(stmt);
  if (check_rc(case_name, event_name, "sqlite3_step", SQLITE_ROW, rc) != 0) return 1;

  rc = sqlite3_bind_int(stmt, 1, 7);
  if (check_rc(case_name, event_name, "sqlite3_bind_int", SQLITE_MISUSE, rc) != 0) return 1;

  rc = sqlite3_reset(stmt);
  if (check_rc(case_name, event_name, "sqlite3_reset", SQLITE_OK, rc) != 0) return 1;
  rc = sqlite3_finalize(stmt);
  if (check_rc(case_name, event_name, "sqlite3_finalize", SQLITE_OK, rc) != 0) return 1;
  rc = sqlite3_close(db);
  if (check_rc(case_name, event_name, "sqlite3_close", SQLITE_OK, rc) != 0) return 1;
  return 0;
}

static int run_data_count_row_done(const char *case_name, const char *event_name) {
  sqlite3 *db = 0;
  sqlite3_stmt *stmt = 0;
  int rc;
  int dc;

  emit_case(case_name);
  if (open_memory(&db) != 0) return 1;
  rc = sqlite3_prepare_v2(db, "SELECT 1 UNION ALL SELECT 2", -1, &stmt, 0);
  if (check_rc(case_name, event_name, "sqlite3_prepare_v2", SQLITE_OK, rc) != 0) return 1;

  dc = sqlite3_data_count(stmt);
  if (dc != 0) {
    emit_diverge_text(case_name, event_name, "sqlite3_data_count", "0-before-step", "nonzero-before-step");
    return 1;
  }

  rc = sqlite3_step(stmt);
  if (check_rc(case_name, event_name, "sqlite3_step", SQLITE_ROW, rc) != 0) return 1;
  dc = sqlite3_data_count(stmt);
  if (dc <= 0) {
    emit_diverge_text(case_name, event_name, "sqlite3_data_count", "nonzero-at-row", "zero-at-row");
    return 1;
  }

  rc = sqlite3_step(stmt);
  if (check_rc(case_name, event_name, "sqlite3_step", SQLITE_ROW, rc) != 0) return 1;
  dc = sqlite3_data_count(stmt);
  if (dc <= 0) {
    emit_diverge_text(case_name, event_name, "sqlite3_data_count", "nonzero-at-row", "zero-at-row");
    return 1;
  }

  rc = sqlite3_step(stmt);
  if (check_rc(case_name, event_name, "sqlite3_step", SQLITE_DONE, rc) != 0) return 1;
  dc = sqlite3_data_count(stmt);
  if (dc != 0) {
    emit_diverge_text(case_name, event_name, "sqlite3_data_count", "0-at-done", "nonzero-at-done");
    return 1;
  }

  rc = sqlite3_finalize(stmt);
  if (check_rc(case_name, event_name, "sqlite3_finalize", SQLITE_OK, rc) != 0) return 1;
  rc = sqlite3_close(db);
  if (check_rc(case_name, event_name, "sqlite3_close", SQLITE_OK, rc) != 0) return 1;
  return 0;
}

static int run_column_blob_zero_length_null(const char *case_name, const char *event_name) {
  sqlite3 *db = 0;
  sqlite3_stmt *stmt = 0;
  int rc;
  const void *blob;
  int bytes;

  emit_case(case_name);
  if (open_memory(&db) != 0) return 1;
  rc = sqlite3_prepare_v2(db, "SELECT zeroblob(0)", -1, &stmt, 0);
  if (check_rc(case_name, event_name, "sqlite3_prepare_v2", SQLITE_OK, rc) != 0) return 1;
  rc = sqlite3_step(stmt);
  if (check_rc(case_name, event_name, "sqlite3_step", SQLITE_ROW, rc) != 0) return 1;

  blob = sqlite3_column_blob(stmt, 0);
  if (blob != 0) {
    emit_diverge_text(case_name, event_name, "sqlite3_column_blob", "NULL", "nonnull");
    return 1;
  }
  bytes = sqlite3_column_bytes(stmt, 0);
  if (bytes != 0) {
    emit_diverge_text(case_name, event_name, "sqlite3_column_bytes", "0", "nonzero");
    return 1;
  }

  rc = sqlite3_finalize(stmt);
  if (check_rc(case_name, event_name, "sqlite3_finalize", SQLITE_OK, rc) != 0) return 1;
  rc = sqlite3_close(db);
  if (check_rc(case_name, event_name, "sqlite3_close", SQLITE_OK, rc) != 0) return 1;
  return 0;
}

int main(void) {
  const char *scenario = "@@SCENARIO@@";
  const char *case_name = "@@CASE_NAME@@";
  const char *event_name = "@@EVENT_NAME@@";

  if (strcmp(scenario, "bind_reset_retains") == 0) {
    return run_bind_reset_retains(case_name, event_name);
  }
  if (strcmp(scenario, "clear_bindings_null") == 0) {
    return run_clear_bindings_null(case_name, event_name);
  }
  if (strcmp(scenario, "bind_after_step_misuse") == 0) {
    return run_bind_after_step_misuse(case_name, event_name);
  }
  if (strcmp(scenario, "data_count_row_done") == 0) {
    return run_data_count_row_done(case_name, event_name);
  }
  if (strcmp(scenario, "column_blob_zero_length_null") == 0) {
    return run_column_blob_zero_length_null(case_name, event_name);
  }

  fprintf(stderr, "unsupported stmt scenario: %s\n", scenario);
  return 2;
}
'''


def emit_c_stmt(model: dict[str, object], out_path: Path) -> None:
    steps = ", ".join(str(step) for step in model["steps"])
    source = (
        STMT_C_TEMPLATE
        .replace("@@FAMILY@@", str(model["family"]))
        .replace("@@SCENARIO@@", str(model["scenario"]))
        .replace("@@CASE_NAME@@", str(model["case_name"]))
        .replace("@@EVENT_NAME@@", str(model["event_name"]))
        .replace("@@EXPECTED_STAGE@@", str(model["expected_terminal_stage"]))
        .replace("@@OBSERVED_STAGE@@", str(model["observed_terminal_stage"]))
        .replace("@@STEPS@@", steps)
    )
    out_path.write_text(source)


def emit_c(model: dict[str, object], out_path: Path) -> None:
    family = str(model["family"])
    if family == "serde":
        emit_c_serde(model, out_path)
        return
    if family == "lifecycle":
        emit_c_lifecycle(model, out_path)
        return
    if family == "stmt":
        emit_c_stmt(model, out_path)
        return
    raise ValueError(f"unsupported model family: {family}")


def emit_tcl_serde(model: dict[str, object], out_path: Path) -> None:
    axis = SERDE_SCENARIOS[str(model["scenario"])]['tcl_axis']
    expected_rc = str(model["expected_rc"])
    case_name = str(model["case_name"])

    setup_block = ""
    if str(model["setup"]) == "read_txn":
        setup_block = textwrap.dedent(
            """\
            db eval {BEGIN; SELECT count(*) FROM t1;}
            """
        )
    elif str(model["setup"]) == "backup_source":
        setup_block = textwrap.dedent(
            """\
            sqlite3 bdst :memory:
            set bk [sqlite3_backup B bdst main db main]
            """
        )

    cleanup_block = ""
    if str(model["setup"]) == "read_txn":
        cleanup_block = "db close\n"
    elif str(model["setup"]) == "backup_source":
        cleanup_block = "B finish\nbdst close\ndb close\n"

    script = f"""\
# Generated from Quint ITF trace for SQLite testfixture style Tcl.
# family: {model['family']}
# scenario: {model['scenario']}
# axis: {axis}
# expected deserialize rc: {expected_rc}

set testdir [file dirname $argv0]
source $testdir/tester.tcl
set testprefix quint_trace_{case_name.replace('-', '_')}

do_not_use_codec

reset_db
do_execsql_test 1.0 {{
  CREATE TABLE t1(a INTEGER PRIMARY KEY);
  INSERT INTO t1 VALUES(1),(2),(3);
}} {{}}

set ser [db serialize main]

{setup_block.rstrip()}

# Note: Tcl deserialize wrapper raises on non-SQLITE_OK. Use catch to capture rc/msg.
set got [catch {{db deserialize main $ser}} msg]
puts "case {case_name}"
if {{$got != 0}} {{
  puts "diverge {case_name} tcl_deserialize_mismatch expected={expected_rc} observed=$msg"
}}

{cleanup_block.rstrip()}
finish_test
"""
    out_path.write_text(script)


def emit_tcl_lifecycle(model: dict[str, object], out_path: Path) -> None:
    axis = LIFECYCLE_SCENARIOS[str(model["scenario"])]['tcl_axis']
    case_name = str(model["case_name"])

    script = f"""\
# Generated from Quint ITF trace for SQLite testfixture style Tcl.
# family: {model['family']}
# scenario: {model['scenario']}
# axis: {axis}
# NOTE: this is a scaffold for the lifecycle scenario. The executable conformance
# path in this repo is the generated C harness from trace_codegen.py.

set testdir [file dirname $argv0]
source $testdir/tester.tcl
set testprefix quint_trace_{case_name.replace('-', '_')}

puts "case {case_name}"

# Fill in concrete Tcl steps for scenario {model['scenario']} if you need a
# direct testfixture-native variant. The generated C harness already checks this
# scenario against upstream SQLite.

finish_test
"""
    out_path.write_text(script)


def emit_tcl_stmt(model: dict[str, object], out_path: Path) -> None:
    axis = STMT_SCENARIOS[str(model["scenario"])]['tcl_axis']
    case_name = str(model["case_name"])

    script = f"""\
# Generated from Quint ITF trace for SQLite testfixture style Tcl.
# family: {model['family']}
# scenario: {model['scenario']}
# axis: {axis}
# NOTE: this is a scaffold for the statement scenario. The executable conformance
# path in this repo is the generated C harness from trace_codegen.py.

set testdir [file dirname $argv0]
source $testdir/tester.tcl
set testprefix quint_trace_{case_name.replace('-', '_')}

puts "case {case_name}"

# Fill in concrete Tcl steps for scenario {model['scenario']} if you need a
# direct testfixture-native variant. The generated C harness already checks this
# scenario against upstream SQLite.

finish_test
"""
    out_path.write_text(script)


def emit_tcl(model: dict[str, object], out_path: Path) -> None:
    family = str(model["family"])
    if family == "serde":
        emit_tcl_serde(model, out_path)
        return
    if family == "lifecycle":
        emit_tcl_lifecycle(model, out_path)
        return
    if family == "stmt":
        emit_tcl_stmt(model, out_path)
        return
    raise ValueError(f"unsupported model family: {family}")


def main() -> int:
    args = parse_args()

    states = load_states(args.itf)
    model = infer_trace_model(states)

    args.out_dir.mkdir(parents=True, exist_ok=True)

    manifest = args.out_dir / f"{args.prefix}.json"
    out_c = args.out_dir / f"{args.prefix}.c"

    emit_manifest(model, manifest)
    emit_c(model, out_c)

    if args.emit_tcl:
        out_tcl = args.out_dir / f"{args.prefix}.test.tcl"
        emit_tcl(model, out_tcl)

    print(f"generated manifest: {manifest}")
    print(f"generated c repro: {out_c}")
    if args.emit_tcl:
        print(f"generated tcl scaffold: {args.out_dir / (args.prefix + '.test.tcl')}")

    print("compile example:")
    print("  cc -std=c11 -O0 -g -I \"$SQLITE_SOURCE_DIR\" \\")
    print(f"     \"$SQLITE_SOURCE_DIR/sqlite3.c\" \"{out_c}\" -o \"{args.out_dir / args.prefix}\" -lpthread -lm")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
