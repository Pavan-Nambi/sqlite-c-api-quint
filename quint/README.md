# Motivation

i wanted to learn more about how to use quint or formal methods. 
yes this specs might be wrong but for that plan is to run this specs first against sqlite - we only target sqlite - if it passes against sqlite, it's correct obviously. after that we can run same specs against turso and we can be 100% confident that we are not missing anything sqlite does.well atleast in c-api...(maybe?)

EDIT: i severly underestimated how much time this takes it's absolutely nuts.

EDIT: this found a [crash](https://sqlite.org/forum/forumpost/39134ba029) in sqlite...

> note: this readme could potentially contain paths and stuff that do not make sense. that's cuz this is part of full formal-methods/repo i have locally where i did some other stupid stuff.., some notes..etc

> this is not complete but i hope to complete this tho.

## Contents

- `lifecycle_api.qnt`: close/finalize/prepare/backup lifecycle state machine and invariants.
- `stmt_api.qnt`: bind/reset/clear + column/data_count statement state machine and invariants.
- `serde_api.qnt`: docs-profile serialize/deserialize state machine and invariants.
- `formal_models.toml`: mechanized-model ledger records consumed by repo checkers.
- `c_quint_conformance_check.py`: checks serde probe divergence lines against documented BUSY cases.
- `lifecycle_trace_conformance_check.py`: checks lifecycle trace replays for unexpected divergence.
- `stmt_trace_conformance_check.py`: checks statement trace replays for unexpected divergence.
- `trace_codegen.py`: converts Apalache ITF traces into executable C repro harnesses (and optional Tcl scaffolds).
- `generate_trace_fixtures.py`: emits canonical ITF traces for all supported lifecycle/stmt/serde scenarios.
- `run.sh`: single command entrypoint for model checks, ITF replay, and trace conformance lanes.

## Prerequisites

- `quint` on `PATH`
- `bash`
- `python3`
- `rg`
- C compiler (`cc` or `clang`) for replay scripts

## SQLite Source Setup (Replay Scripts)

`run.sh trace-repro` and `run.sh trace-conformance` compile and execute against a
pinned SQLite source checkout. Set:

```sh
export SQLITE_SOURCE_DIR=/path/to/pinned/sqlite/checkout
```

That checkout must contain:

- `sqlite3.c`
- `sqlite3.h`
- `manifest.uuid`

The manifest/version/source-id must match `../spec/upstream.toml`.

## Run Quint Model

Default (standalone or when you `cd quint`):

```sh
./run.sh model lifecycle
./run.sh model stmt
./run.sh model serde
```

If this folder is embedded in the full monorepo:

```sh
./quint/run.sh model lifecycle
./quint/run.sh model stmt
./quint/run.sh model serde
```

## Run C/Quint Conformance Check

The checker expects lines in this format on stdin:

- `case <case-name>`
- `diverge <case-name> <event> <fact=value>...`

Example when running inside `quint/` (standalone-friendly):

```sh
printf 'case deserialize-read-transaction-busy\ncase deserialize-backup-source-busy\n' \
  | python3 ./c_quint_conformance_check.py
```

If this folder is embedded in the full monorepo:

```sh
printf 'case deserialize-read-transaction-busy\ncase deserialize-backup-source-busy\n' \
  | python3 ./quint/c_quint_conformance_check.py
```

In this repo, the normal wired path is:

```sh
./model/run_check.sh divergence
```

Lifecycle replay conformance path:

```sh
./model/run_check.sh quint-lifecycle-trace
```

Statement replay conformance path:

```sh
./model/run_check.sh quint-stmt-trace
```

## Generate Repros From Quint Traces

From an Apalache ITF trace:

```sh
./quint/run.sh trace-repro _apalache-out/server/<run-id>/violation.itf.json
```

This writes generated artifacts under `$TMPDIR/sqlite-capi-proof/quint-trace-repro/`
and executes the generated C harness against the pinned SQLite source.

To also emit a SQLite testfixture Tcl scaffold:

```sh
./quint/run.sh trace-repro _apalache-out/server/<run-id>/violation.itf.json --emit-tcl
```

To run a sanitized replay (ASan/UBSan):

```sh
./quint/run.sh trace-repro _apalache-out/server/<run-id>/violation.itf.json --sanitize
```

## Run Lifecycle Upstream Conformance

Generate canonical lifecycle traces and replay all of them against upstream SQLite:

```sh
./quint/run.sh trace-conformance lifecycle
```

Sanitized lane:

```sh
./quint/run.sh trace-conformance lifecycle --sanitize
```

This lane emits `case` / `diverge` lines and fails if any lifecycle case diverges.
Current lifecycle coverage includes close/finalize/prepare obligations and
backup step edge semantics (`step(0)`, `step(-1)`, and transient `BUSY/LOCKED`
conflict retry paths).

## Run Statement Upstream Conformance

Generate canonical statement traces and replay all of them against upstream SQLite:

```sh
./quint/run.sh trace-conformance stmt
```

Sanitized lane:

```sh
./quint/run.sh trace-conformance stmt --sanitize
```

This lane emits `case` / `diverge` lines and fails if any statement case diverges.
