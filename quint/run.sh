#!/usr/bin/env bash

set -euo pipefail

QUINT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
COMMON_LOADED=0

usage() {
  cat <<'USAGE'
usage:
  ./quint/run.sh model <lifecycle|stmt|serde>
  ./quint/run.sh trace-repro <itf.json> [--emit-tcl] [--sanitize]
  ./quint/run.sh trace-conformance <lifecycle|stmt|serde> [--sanitize] [--emit-tcl]
USAGE
}

require_quint() {
  if ! command -v quint >/dev/null 2>&1; then
    echo "quint is required for Quint model checks" >&2
    exit 2
  fi
}

load_common() {
  if [ "$COMMON_LOADED" -eq 1 ]; then
    return
  fi
  local common_path="$QUINT_DIR/../scripts/common.sh"
  if [ ! -f "$common_path" ]; then
    echo "missing shared script: $common_path" >&2
    exit 2
  fi
  # shellcheck source=../scripts/common.sh
  source "$common_path"
  COMMON_LOADED=1
}

run_lifecycle_model() {
  local spec="$QUINT_DIR/lifecycle_api.qnt"
  require_quint
  quint typecheck "$spec"

  local server_port=$((19000 + RANDOM % 10000))
  local server_endpoint="localhost:${server_port}"

  quint verify "$spec" \
    --init=initDoc \
    --step=step \
    --server-endpoint "$server_endpoint" \
    --verbosity=1 \
    --invariants \
      lifecycleFinalizeNullNoOp \
      lifecycleCloseNullNoOp \
      lifecycleCloseLiveStmtPath \
      lifecycleCloseV2LiveStmtPath \
      lifecyclePrepareV2V3ZeroFlagsEquivalent \
      lifecycleCloseLiveBackupPath \
      lifecycleCloseV2LiveBackupPath \
      lifecycleBackupStepDoneFinishPath \
      lifecycleBackupFinishIncompletePath \
      lifecycleBackupStepZeroNoProgressPath \
      lifecycleBackupStepNegativeAllRemainingPath \
      lifecycleBackupStepTransientConflictPath \
      lifecycleBackupInitSameConnectionErrorPath \
      lifecycleBackupInitDestReadTxnErrorPath \
    --max-steps=8

  echo "quint lifecycle API model passed: close/finalize/prepare/backup invariants hold (including backup step edge semantics)"
}

run_stmt_model() {
  local spec="$QUINT_DIR/stmt_api.qnt"
  require_quint
  quint typecheck "$spec"

  local server_port=$((19000 + RANDOM % 10000))
  local server_endpoint="localhost:${server_port}"

  quint verify "$spec" \
    --init=initDoc \
    --step=step \
    --server-endpoint "$server_endpoint" \
    --verbosity=1 \
    --invariants \
      stmtBindResetRetainsPath \
      stmtClearBindingsNullPath \
      stmtBindAfterStepMisusePath \
      stmtDataCountRowDonePath \
      stmtBlobZeroLengthNullPath \
    --max-steps=7

  echo "quint stmt API model passed: bind/reset/clear + column/data_count invariants hold"
}

run_serde_model() {
  local spec="$QUINT_DIR/serde_api.qnt"
  require_quint
  quint typecheck "$spec"

  local server_port=$((19000 + RANDOM % 10000))
  local server_endpoint="localhost:${server_port}"

  quint verify "$spec" \
    --init=initDoc \
    --step=step \
    --server-endpoint "$server_endpoint" \
    --verbosity=1 \
    --invariants \
      noDocDivergence \
      docBusyConflictsReturnBusy \
      docBusyConflictsDoNotInstall \
      successfulDeserializeInstalls \
      schemaErrorsDoNotInstall \
      apiArmorNegativeSizesReturnMisuse \
      readonlyWriteRequiresReadonlyDeserialize \
      resizeableGrowthRequiresResizeableDeserialize \
      walImageUseFailsCantopen \
      docFreeOnCloseFailureReturnsError \
      noSuccessfulDeserializeAfterFreeOnCloseFailure \
      nonresizeableRejectionRequiresBoundedGrowth \
    --max-steps=4

  echo "quint serde API model passed: documented profile invariants hold"
}

supports_flags() {
  local compiler=$1
  shift
  local src="$BUILD_DIR/sanitizer_flag_test.c"
  local out="$BUILD_DIR/sanitizer_flag_test"
  cat > "$src" <<'C'
int main(void) { return 0; }
C
  if "$compiler" "$src" -o "$out" "$@" >/dev/null 2>&1; then
    return 0
  fi
  return 1
}

run_trace_repro_core() {
  local itf_path=$1
  local emit_tcl=$2
  local sanitize=$3

  mkdir -p "$BUILD_DIR/quint-trace-repro"

  local prefix
  prefix="$(basename "$itf_path")"
  prefix="${prefix%.itf.json}"
  prefix="${prefix%.json}"

  if [ "$emit_tcl" -eq 1 ]; then
    python3 "$QUINT_DIR/trace_codegen.py" \
      --itf "$itf_path" \
      --out-dir "$BUILD_DIR/quint-trace-repro" \
      --prefix "$prefix" \
      --emit-tcl
  else
    python3 "$QUINT_DIR/trace_codegen.py" \
      --itf "$itf_path" \
      --out-dir "$BUILD_DIR/quint-trace-repro" \
      --prefix "$prefix"
  fi

  local src="$BUILD_DIR/quint-trace-repro/$prefix.c"
  local out="$BUILD_DIR/quint-trace-repro/$prefix"

  if [ "$sanitize" -eq 1 ]; then
    if ! supports_flags "$CC" -fsanitize=address,undefined -fno-omit-frame-pointer -fno-sanitize-recover=all -O1; then
      echo "compiler '$CC' does not support ASan/UBSan flags required by --sanitize" >&2
      exit 2
    fi
    # shellcheck disable=SC2046
    "$CC" -std=c11 -g -O1 \
      -fsanitize=address,undefined \
      -fno-omit-frame-pointer \
      -fno-sanitize-recover=all \
      -I "$SQLITE_SOURCE_DIR" \
      "$SQLITE_SOURCE_DIR/sqlite3.c" \
      "$src" \
      -o "$out" \
      $(sqlite_libs)
    ASAN_OPTIONS=detect_leaks=0 "$out"
  else
    # shellcheck disable=SC2046
    "$CC" -std=c11 -O0 -g \
      -I "$SQLITE_SOURCE_DIR" \
      "$SQLITE_SOURCE_DIR/sqlite3.c" \
      "$src" \
      -o "$out" \
      $(sqlite_libs)
    "$out"
  fi
}

cmd_trace_repro() {
  if [ $# -lt 1 ]; then
    usage >&2
    exit 2
  fi

  local itf_path=$1
  shift
  local emit_tcl=0
  local sanitize=0

  while [ $# -gt 0 ]; do
    case "$1" in
      --emit-tcl)
        emit_tcl=1
        ;;
      --sanitize)
        sanitize=1
        ;;
      *)
        usage >&2
        exit 2
        ;;
    esac
    shift
  done

  if [ ! -f "$itf_path" ]; then
    echo "missing ITF trace: $itf_path" >&2
    exit 2
  fi

  load_common
  require_sqlite_source
  run_trace_repro_core "$itf_path" "$emit_tcl" "$sanitize"
}

cmd_trace_conformance() {
  if [ $# -lt 1 ]; then
    usage >&2
    exit 2
  fi

  local family=$1
  shift

  load_common

  local sanitize=0
  local emit_tcl=0
  while [ $# -gt 0 ]; do
    case "$1" in
      --sanitize)
        sanitize=1
        ;;
      --emit-tcl)
        emit_tcl=1
        ;;
      *)
        usage >&2
        exit 2
        ;;
    esac
    shift
  done

  local checker=""
  local out_log=""
  local fixture_dir=""
  case "$family" in
    lifecycle)
      fixture_dir="$BUILD_DIR/quint-trace-fixtures/lifecycle"
      out_log="$BUILD_DIR/quint-trace-fixtures/lifecycle-repro.log"
      checker="$QUINT_DIR/lifecycle_trace_conformance_check.py"
      ;;
    stmt)
      fixture_dir="$BUILD_DIR/quint-trace-fixtures/stmt"
      out_log="$BUILD_DIR/quint-trace-fixtures/stmt-repro.log"
      checker="$QUINT_DIR/stmt_trace_conformance_check.py"
      ;;
    serde)
      fixture_dir="$BUILD_DIR/quint-trace-fixtures/serde"
      out_log="$BUILD_DIR/quint-trace-fixtures/serde-repro.log"
      checker="$QUINT_DIR/c_quint_conformance_check.py"
      ;;
    *)
      usage >&2
      exit 2
      ;;
  esac

  require_rg
  require_sqlite_source

  mkdir -p "$fixture_dir"
  python3 "$QUINT_DIR/generate_trace_fixtures.py" --family "$family" --out-dir "$fixture_dir"

  : > "$out_log"
  while IFS= read -r itf; do
    echo "replaying $(basename "$itf")" >&2
    run_trace_repro_core "$itf" "$emit_tcl" "$sanitize" | tee -a "$out_log"
  done < <(find "$fixture_dir" -type f -name '*.itf.json' | sort)

  rg '^(case|diverge) ' "$out_log" | python3 "$checker"
}

if [ $# -lt 1 ]; then
  usage >&2
  exit 2
fi

cmd=$1
shift

case "$cmd" in
  model)
    if [ $# -ne 1 ]; then
      usage >&2
      exit 2
    fi
    case "$1" in
      lifecycle)
        run_lifecycle_model
        ;;
      stmt)
        run_stmt_model
        ;;
      serde)
        run_serde_model
        ;;
      *)
        usage >&2
        exit 2
        ;;
    esac
    ;;
  trace-repro)
    cmd_trace_repro "$@"
    ;;
  trace-conformance)
    cmd_trace_conformance "$@"
    ;;
  -h|--help|help)
    usage
    ;;
  *)
    usage >&2
    exit 2
    ;;
esac
