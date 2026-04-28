"""Independent validation oracles for supported trace replay scenarios."""

from __future__ import annotations

from trace_scenarios import (
    FAMILY_DEFAULTS,
    _stage_value,
    all_supported_scenarios,
    scenario_family,
)


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

SERDE_EXPECTED_DESERIALIZE_RC: dict[str, str] = {
    "deserialize_read_txn_busy": "SQLITE_BUSY",
    "deserialize_backup_busy": "SQLITE_BUSY",
    "deserialize_null_schema_main": "SQLITE_OK",
    "deserialize_attached_schema": "SQLITE_OK",
    "deserialize_temp_schema_error": "SQLITE_ERROR",
    "deserialize_missing_schema_error": "SQLITE_ERROR",
    "deserialize_readonly_read_write": "SQLITE_OK",
    "deserialize_resizeable_growth": "SQLITE_OK",
    "deserialize_nonresizeable_growth": "SQLITE_OK",
}


LIFECYCLE_EXPECTED_STEPS: dict[str, list[str]] = {
    "finalize_null": ["stage_0_to_1"],
    "close_null": ["close_null_called", "close_v2_null_called"],
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
    "backup_init_same_connection_error": ["stage_0_to_1"],
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
    "deserialize_read_txn_busy": ["start_read_txn", "deserialize"],
    "deserialize_backup_busy": ["start_backup_source", "deserialize"],
    "deserialize_null_schema_main": ["deserialize"],
    "deserialize_attached_schema": ["deserialize"],
    "deserialize_temp_schema_error": ["deserialize"],
    "deserialize_missing_schema_error": ["deserialize"],
    "deserialize_readonly_read_write": [
        "deserialize",
        "readonly_read",
        "readonly_write_reject",
    ],
    "deserialize_resizeable_growth": ["deserialize", "resizeable_grow"],
    "deserialize_nonresizeable_growth": [
        "deserialize",
        "grow_within_limit",
        "reject_beyond_limit",
    ],
}


FAMILY_TERMINAL_FACTS = {
    "serde": SERDE_TERMINAL_FACTS,
    "lifecycle": LIFECYCLE_TERMINAL_FACTS,
    "stmt": STMT_TERMINAL_FACTS,
}

FAMILY_EXPECTED_STEPS = {
    "serde": SERDE_EXPECTED_STEPS,
    "lifecycle": LIFECYCLE_EXPECTED_STEPS,
    "stmt": STMT_EXPECTED_STEPS,
}


def _terminal_fact_table(
    scenario: str,
    family_tables: dict[str, dict[str, dict[str, object]]],
) -> dict[str, dict[str, object]]:
    family = scenario_family(scenario)
    if family is None:
        supported = ", ".join(all_supported_scenarios())
        raise ValueError(f"unsupported scenario '{scenario}'. Supported scenarios: {supported}")
    return family_tables[family]


def _expected_steps_table(scenario: str) -> dict[str, list[str]]:
    family = scenario_family(scenario)
    if family is None:
        supported = ", ".join(all_supported_scenarios())
        raise ValueError(f"unsupported scenario '{scenario}'. Supported scenarios: {supported}")
    return FAMILY_EXPECTED_STEPS[family]


def expected_steps(scenario: str) -> list[str]:
    table = _expected_steps_table(scenario)
    return list(table[scenario])


def terminal_facts(scenario: str) -> dict[str, object]:
    family = scenario_family(scenario)
    if family is None:
        supported = ", ".join(all_supported_scenarios())
        raise ValueError(f"unsupported scenario '{scenario}'. Supported scenarios: {supported}")

    table = _terminal_fact_table(scenario, FAMILY_TERMINAL_FACTS)
    facts = dict(FAMILY_DEFAULTS[family])
    facts.update(table[scenario])
    facts["scenario"] = scenario
    return facts


def staged_terminal_stage(scenario: str) -> int:
    family = scenario_family(scenario)
    if family == "serde":
        raise ValueError(f"{scenario}: serde traces do not have staged terminal states")
    return _stage_value(terminal_facts(scenario))


def expected_deserialize_rc(scenario: str) -> str:
    family = scenario_family(scenario)
    if family != "serde":
        raise ValueError(f"{scenario}: only serde scenarios have deserialize rc oracles")
    return SERDE_EXPECTED_DESERIALIZE_RC[scenario]
