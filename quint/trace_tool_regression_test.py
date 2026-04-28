#!/usr/bin/env python3
"""Regression checks for trace fixture generation and replay validation."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path

import trace_oracles
import trace_scenarios


QUINT_DIR = Path(__file__).resolve().parent
GENERATE = QUINT_DIR / "generate_trace_fixtures.py"
CODEGEN = QUINT_DIR / "trace_codegen.py"


def run_ok(args: list[str]) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(args, capture_output=True, text=True)
    if result.returncode != 0:
        raise AssertionError(
            f"command failed unexpectedly: {' '.join(args)}\n"
            f"stdout:\n{result.stdout}\n"
            f"stderr:\n{result.stderr}"
        )
    return result


def run_fail(args: list[str], expected: str) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(args, capture_output=True, text=True)
    if result.returncode == 0:
        raise AssertionError(f"command succeeded unexpectedly: {' '.join(args)}")
    combined = result.stdout + result.stderr
    if expected not in combined:
        raise AssertionError(
            f"command failed without expected text {expected!r}: {' '.join(args)}\n"
            f"stdout:\n{result.stdout}\n"
            f"stderr:\n{result.stderr}"
        )
    return result


def codegen_args(
    itf: Path,
    out_dir: Path,
    prefix: str,
    emit_tcl: bool = False,
) -> list[str]:
    args = [
        sys.executable,
        str(CODEGEN),
        "--itf",
        str(itf),
        "--out-dir",
        str(out_dir),
        "--prefix",
        prefix,
    ]
    if emit_tcl:
        args.append("--emit-tcl")
    return args


def load_itf(path: Path) -> dict[str, object]:
    return json.loads(path.read_text())


def write_itf(path: Path, payload: dict[str, object]) -> None:
    path.write_text(json.dumps(payload, indent=2) + "\n")


def state(payload: dict[str, object], idx: int) -> dict[str, object]:
    states = payload["states"]
    if not isinstance(states, list):
        raise AssertionError("states must be a list")
    wrapper = states[idx]
    if not isinstance(wrapper, dict):
        raise AssertionError("state wrapper must be an object")
    raw_state = wrapper["state"]
    if not isinstance(raw_state, dict):
        raise AssertionError("state must be an object")
    return raw_state


def main() -> int:
    oracle_source = (QUINT_DIR / "trace_oracles.py").read_text()
    forbidden_oracle_sources = ["FAMILY_TRACES", "canonical_states", "infer_transition_steps"]
    for forbidden in forbidden_oracle_sources:
        if forbidden in oracle_source:
            raise AssertionError(f"trace_oracles.py must not depend on {forbidden}")

    codegen_source = CODEGEN.read_text()
    if "canonical_expected_steps" in codegen_source or "canonical_terminal_facts" in codegen_source:
        raise AssertionError("trace_codegen.py must not use circular canonical trace oracles")

    for family, scenarios in trace_scenarios.FAMILY_SCENARIOS.items():
        scenario_names = set(scenarios)
        if set(trace_oracles.FAMILY_EXPECTED_STEPS[family]) != scenario_names:
            raise AssertionError(f"{family}: expected-step oracle coverage mismatch")
        if set(trace_oracles.FAMILY_TERMINAL_FACTS[family]) != scenario_names:
            raise AssertionError(f"{family}: terminal-fact oracle coverage mismatch")
    if set(trace_oracles.SERDE_EXPECTED_DESERIALIZE_RC) != set(trace_scenarios.SERDE_SCENARIOS):
        raise AssertionError("serde deserialize-rc oracle coverage mismatch")

    with tempfile.TemporaryDirectory(prefix="quint-trace-tools-") as tmp_raw:
        tmp = Path(tmp_raw)
        fixture_dir = tmp / "fixtures"
        out_dir = tmp / "out"
        fixture_dir.mkdir()
        out_dir.mkdir()

        run_ok(
            [
                sys.executable,
                str(GENERATE),
                "--family",
                "all",
                "--out-dir",
                str(fixture_dir),
            ]
        )

        traces = sorted(fixture_dir.glob("*.itf.json"))
        if not traces:
            raise AssertionError("fixture generation produced no traces")

        for itf in traces:
            run_ok(codegen_args(itf, out_dir, itf.name.removesuffix(".itf.json")))

        bad_terminal = load_itf(fixture_dir / "bind_reset_retains.itf.json")
        state(bad_terminal, -1)["resetCalled"] = False
        bad_terminal_path = tmp / "bad_terminal.itf.json"
        write_itf(bad_terminal_path, bad_terminal)
        run_fail(
            codegen_args(bad_terminal_path, out_dir, "bad_terminal"),
            "terminal resetCalled expected True, got False",
        )

        bad_default = load_itf(fixture_dir / "deserialize_null_schema_main.itf.json")
        state(bad_default, -1)["freeOnCloseFreed"] = True
        bad_default_path = tmp / "bad_default.itf.json"
        write_itf(bad_default_path, bad_default)
        run_fail(
            codegen_args(bad_default_path, out_dir, "bad_default"),
            "terminal freeOnCloseFreed expected False, got True",
        )

        bad_extra = load_itf(fixture_dir / "deserialize_null_schema_main.itf.json")
        state(bad_extra, -1)["unexpectedFact"] = True
        bad_extra_path = tmp / "bad_extra.itf.json"
        write_itf(bad_extra_path, bad_extra)
        run_fail(
            codegen_args(bad_extra_path, out_dir, "bad_extra"),
            "terminal state has unexpected keys ['unexpectedFact']",
        )

        bad_steps = load_itf(fixture_dir / "bind_after_step_misuse.itf.json")
        state(bad_steps, 1)["firstStepRow"] = False
        bad_steps_path = tmp / "bad_steps.itf.json"
        write_itf(bad_steps_path, bad_steps)
        run_fail(
            codegen_args(bad_steps_path, out_dir, "bad_steps"),
            "expected steps",
        )

        bad_rc = load_itf(fixture_dir / "deserialize_readonly_read_write.itf.json")
        state(bad_rc, 1)["rc"] = "SQLITE_BUSY"
        bad_rc_path = tmp / "bad_rc.itf.json"
        write_itf(bad_rc_path, bad_rc)
        run_fail(
            codegen_args(bad_rc_path, out_dir, "bad_rc"),
            "expected sqlite3_deserialize rc 'SQLITE_OK', got 'SQLITE_BUSY'",
        )

        run_ok(
            codegen_args(
                fixture_dir / "deserialize_null_schema_main.itf.json",
                out_dir,
                "serde_ok",
                emit_tcl=True,
            )
        )
        ok_tcl = (out_dir / "serde_ok.test.tcl").read_text()
        if "set expected_ok 1" not in ok_tcl or "if {$expected_ok}" not in ok_tcl:
            raise AssertionError("OK serde Tcl does not expect catch success")

        run_ok(
            codegen_args(
                fixture_dir / "deserialize_read_txn_busy.itf.json",
                out_dir,
                "serde_busy",
                emit_tcl=True,
            )
        )
        busy_tcl = (out_dir / "serde_busy.test.tcl").read_text()
        if "set expected_ok 0" not in busy_tcl:
            raise AssertionError("non-OK serde Tcl does not expect catch failure")
        if "expected=SQLITE_BUSY observed=SQLITE_OK" not in busy_tcl:
            raise AssertionError("non-OK serde Tcl missing success-as-divergence check")

    print("trace tool regression checks passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
