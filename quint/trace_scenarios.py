"""Canonical scenario metadata and ITF trace shapes for trace replay tools."""

from __future__ import annotations


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
        "tcl_axis": "sqlite3_finalize(NULL) no-op",
    },
    "close_null": {
        "case_name": "close-null",
        "event_name": "close_null_trace_mismatch",
        "tcl_axis": "sqlite3_close/sqlite3_close_v2 NULL no-op",
    },
    "close_live_stmt": {
        "case_name": "close-live-stmt",
        "event_name": "close_live_stmt_trace_mismatch",
        "tcl_axis": "sqlite3_close busy with live statement",
    },
    "close_v2_live_stmt": {
        "case_name": "close-v2-live-stmt",
        "event_name": "close_v2_live_stmt_trace_mismatch",
        "tcl_axis": "sqlite3_close_v2 zombie with live statement",
    },
    "prepare_v2_v3_zero_flags": {
        "case_name": "prepare-v2-v3-zero-flags",
        "event_name": "prepare_v2_v3_zero_flags_trace_mismatch",
        "tcl_axis": "sqlite3_prepare_v2/v3 zero-flag equivalence",
    },
    "close_live_backup": {
        "case_name": "close-live-backup",
        "event_name": "close_live_backup_trace_mismatch",
        "tcl_axis": "sqlite3_close busy with live backup source",
    },
    "close_v2_live_backup": {
        "case_name": "close-v2-live-backup",
        "event_name": "close_v2_live_backup_trace_mismatch",
        "tcl_axis": "sqlite3_close_v2 zombie with live backup source",
    },
    "backup_step_done_finish": {
        "case_name": "backup-step-done-finish-ok",
        "event_name": "backup_step_done_finish_trace_mismatch",
        "tcl_axis": "backup step DONE then finish OK",
    },
    "backup_finish_incomplete": {
        "case_name": "backup-finish-incomplete-ok",
        "event_name": "backup_finish_incomplete_trace_mismatch",
        "tcl_axis": "backup finish OK after incomplete step",
    },
    "backup_step_zero_no_progress": {
        "case_name": "backup-step-zero-no-progress",
        "event_name": "backup_step_zero_no_progress_trace_mismatch",
        "tcl_axis": "backup step(0) does not copy pages",
    },
    "backup_step_negative_all_remaining_done": {
        "case_name": "backup-step-negative-all-remaining-done",
        "event_name": "backup_step_negative_all_remaining_done_trace_mismatch",
        "tcl_axis": "backup step(-1) copies all remaining pages",
    },
    "backup_step_transient_conflict_retry": {
        "case_name": "backup-step-transient-conflict-retry",
        "event_name": "backup_step_transient_conflict_retry_trace_mismatch",
        "tcl_axis": "backup step BUSY/LOCKED is transient and retryable",
    },
    "backup_init_same_connection_error": {
        "case_name": "backup-init-same-connection-error",
        "event_name": "backup_init_same_connection_trace_mismatch",
        "tcl_axis": "backup init rejects identical source/destination",
    },
    "backup_init_dest_read_txn_error": {
        "case_name": "backup-init-destination-read-transaction-error",
        "event_name": "backup_init_dest_read_txn_trace_mismatch",
        "tcl_axis": "backup init rejects destination read transaction",
    },
}

STMT_SCENARIOS = {
    "bind_reset_retains": {
        "case_name": "bind-reset-retains",
        "event_name": "bind_reset_retains_trace_mismatch",
        "tcl_axis": "sqlite3_reset retains prior bindings",
    },
    "clear_bindings_null": {
        "case_name": "clear-bindings-null",
        "event_name": "clear_bindings_null_trace_mismatch",
        "tcl_axis": "sqlite3_clear_bindings resets all parameters to NULL",
    },
    "bind_after_step_misuse": {
        "case_name": "bind-after-step-misuse",
        "event_name": "bind_after_step_misuse_trace_mismatch",
        "tcl_axis": "sqlite3_bind after step-before-reset returns SQLITE_MISUSE",
    },
    "data_count_row_done": {
        "case_name": "data-count-row-done",
        "event_name": "data_count_row_done_trace_mismatch",
        "tcl_axis": "sqlite3_data_count row/non-row transitions",
    },
    "column_blob_zero_length_null": {
        "case_name": "column-blob-zero-length-null",
        "event_name": "column_blob_zero_length_null_trace_mismatch",
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

SERDE_DEFAULT = {
    "readTxn": False,
    "backupSource": False,
    "deserialized": False,
    "readonlyRead": False,
    "readonlyWriteRejected": False,
    "resizeableGrew": False,
    "walImageUseFailed": False,
    "grewWithinLimit": False,
    "rejectedBeyondLimit": False,
    "freeOnCloseFreed": False,
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
    "deserialize_null_schema_main": [
        {},
        {"rc": "SQLITE_OK", "deserialized": True},
    ],
    "deserialize_attached_schema": [
        {},
        {"rc": "SQLITE_OK", "deserialized": True},
    ],
    "deserialize_temp_schema_error": [
        {},
        {"rc": "SQLITE_ERROR"},
    ],
    "deserialize_missing_schema_error": [
        {},
        {"rc": "SQLITE_ERROR"},
    ],
    "deserialize_readonly_read_write": [
        {},
        {"rc": "SQLITE_OK", "deserialized": True},
        {"rc": "SQLITE_OK", "deserialized": True, "readonlyRead": True},
        {
            "rc": "SQLITE_READONLY",
            "deserialized": True,
            "readonlyRead": True,
            "readonlyWriteRejected": True,
        },
    ],
    "deserialize_resizeable_growth": [
        {},
        {"rc": "SQLITE_OK", "deserialized": True},
        {"rc": "SQLITE_OK", "deserialized": True, "resizeableGrew": True},
    ],
    "deserialize_nonresizeable_growth": [
        {},
        {"rc": "SQLITE_OK", "deserialized": True},
        {"rc": "SQLITE_OK", "deserialized": True, "grewWithinLimit": True},
        {
            "rc": "SQLITE_FULL",
            "deserialized": True,
            "grewWithinLimit": True,
            "rejectedBeyondLimit": True,
        },
    ],
}

LIFECYCLE_TRACES: dict[str, list[dict[str, object]]] = {
    "finalize_null": [{"stage": 0}, {"stage": 1}],
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
        {"stage": 3, "connOpen": True, "backupHandleLive": False},
        {"stage": 4, "connOpen": True, "backupHandleLive": False, "backupQueryMatched": True},
    ],
    "backup_finish_incomplete": [
        {"stage": 0, "connOpen": True},
        {"stage": 1, "connOpen": True, "backupHandleLive": True},
        {"stage": 2, "connOpen": True, "backupHandleLive": True},
        {"stage": 3, "connOpen": True, "backupHandleLive": False},
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

FAMILY_SCENARIOS = {
    "serde": SERDE_SCENARIOS,
    "lifecycle": LIFECYCLE_SCENARIOS,
    "stmt": STMT_SCENARIOS,
}

FAMILY_DEFAULTS = {
    "serde": SERDE_DEFAULT,
    "lifecycle": LIFECYCLE_DEFAULT,
    "stmt": STMT_DEFAULT,
}

FAMILY_TRACES = {
    "serde": SERDE_TRACES,
    "lifecycle": LIFECYCLE_TRACES,
    "stmt": STMT_TRACES,
}


def all_supported_scenarios() -> list[str]:
    scenarios = set()
    for family_scenarios in FAMILY_SCENARIOS.values():
        scenarios.update(family_scenarios)
    return sorted(scenarios)


def scenario_family(scenario: str) -> str | None:
    for family, family_scenarios in FAMILY_SCENARIOS.items():
        if scenario in family_scenarios:
            return family
    return None


def scenario_info(scenario: str) -> dict[str, object]:
    family = scenario_family(scenario)
    if family is None:
        supported = ", ".join(all_supported_scenarios())
        raise ValueError(f"unsupported scenario '{scenario}'. Supported scenarios: {supported}")
    return FAMILY_SCENARIOS[family][scenario]


def canonical_states(scenario: str) -> list[dict[str, object]]:
    family = scenario_family(scenario)
    if family is None:
        supported = ", ".join(all_supported_scenarios())
        raise ValueError(f"unsupported scenario '{scenario}'. Supported scenarios: {supported}")

    defaults = FAMILY_DEFAULTS[family]
    states = []
    for raw in FAMILY_TRACES[family][scenario]:
        state = dict(defaults)
        state.update(raw)
        state["scenario"] = scenario
        states.append(state)
    return states


def wrap_states(scenario: str) -> dict[str, object]:
    return {"states": [{"state": state} for state in canonical_states(scenario)]}


def _stage_value(state: dict[str, object]) -> int:
    stage = state.get("stage")
    if not isinstance(stage, int) or stage < 0:
        raise ValueError(f"invalid lifecycle stage value: {stage!r}")
    return stage


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
