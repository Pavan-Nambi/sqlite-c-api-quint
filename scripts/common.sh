#!/usr/bin/env bash

set -euo pipefail

COMMON_SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
PROOF_DIR=$(CDPATH= cd -- "$COMMON_SCRIPT_DIR/.." && pwd)
UPSTREAM_TOML="$PROOF_DIR/spec/upstream.toml"

toml_string() {
  local key=$1
  awk -F '"' -v key="$key" '$1 ~ "^[[:space:]]*" key "[[:space:]]*=" { print $2; exit }' "$UPSTREAM_TOML"
}

toml_int() {
  local key=$1
  awk -F '=' -v key="$key" '$1 ~ "^[[:space:]]*" key "[[:space:]]*$" { gsub(/[[:space:]]/, "", $2); print $2; exit }' "$UPSTREAM_TOML"
}

EXPECTED_VERSION=$(toml_string version)
EXPECTED_VERSION_NUMBER=$(toml_int version_number)
EXPECTED_SOURCE_ID=$(toml_string source_id)
EXPECTED_MANIFEST=$(toml_string manifest_uuid)
SQLITE_SOURCE_DIR=${SQLITE_SOURCE_DIR:-}
BUILD_DIR=${TMPDIR:-/tmp}/sqlite-capi-proof
CC=${CC:-cc}

sqlite_libs() {
  if [ "$(uname -s)" = "Darwin" ]; then
    printf '%s\n' "-lpthread -lm"
  else
    printf '%s\n' "-lpthread -ldl -lm"
  fi
}

require_rg() {
  if ! command -v rg >/dev/null 2>&1; then
    echo "rg is required for evidence scanning" >&2
    exit 2
  fi
}

require_sqlite_source() {
  if [ -z "$SQLITE_SOURCE_DIR" ]; then
    echo "SQLITE_SOURCE_DIR is not set. Export it to a pinned SQLite checkout path." >&2
    echo "example: export SQLITE_SOURCE_DIR=/path/to/sqlite-src-official" >&2
    exit 2
  fi
  if [ ! -d "$SQLITE_SOURCE_DIR" ]; then
    echo "SQLITE_SOURCE_DIR does not exist: $SQLITE_SOURCE_DIR" >&2
    exit 2
  fi
  for file in sqlite3.c sqlite3.h manifest.uuid; do
    if [ ! -f "$SQLITE_SOURCE_DIR/$file" ]; then
      echo "missing $SQLITE_SOURCE_DIR/$file" >&2
      exit 2
    fi
  done

  local manifest
  manifest=$(tr -d '[:space:]' < "$SQLITE_SOURCE_DIR/manifest.uuid")
  if [ "$manifest" != "$EXPECTED_MANIFEST" ]; then
    echo "manifest mismatch: expected $EXPECTED_MANIFEST got $manifest" >&2
    exit 2
  fi

  if ! rg -Fq "#define SQLITE_VERSION        \"$EXPECTED_VERSION\"" "$SQLITE_SOURCE_DIR/sqlite3.h"; then
    echo "SQLITE_VERSION mismatch in $SQLITE_SOURCE_DIR/sqlite3.h" >&2
    exit 2
  fi
  if ! rg -Fq "#define SQLITE_VERSION_NUMBER $EXPECTED_VERSION_NUMBER" "$SQLITE_SOURCE_DIR/sqlite3.h"; then
    echo "SQLITE_VERSION_NUMBER mismatch in $SQLITE_SOURCE_DIR/sqlite3.h" >&2
    exit 2
  fi
  if ! rg -Fq "#define SQLITE_SOURCE_ID      \"$EXPECTED_SOURCE_ID\"" "$SQLITE_SOURCE_DIR/sqlite3.h"; then
    echo "SQLITE_SOURCE_ID mismatch in $SQLITE_SOURCE_DIR/sqlite3.h" >&2
    exit 2
  fi
}

compile_sqlite_probe() {
  local probe=$1
  local out=$2
  compile_sqlite_probe_with_cflags "$probe" "$out"
}

compile_sqlite_probe_with_cflags() {
  local probe=$1
  local out=$2
  shift 2
  mkdir -p "$BUILD_DIR"
  # shellcheck disable=SC2046
  "$CC" -std=c11 -O0 -g \
    "$@" \
    -I "$SQLITE_SOURCE_DIR" \
    "$SQLITE_SOURCE_DIR/sqlite3.c" \
    "$probe" \
    -o "$out" \
    $(sqlite_libs)
}

print_execution_model() {
  local compiler_version
  if compiler_version=$("$CC" --version 2>/dev/null | sed -n '1p'); then
    :
  else
    compiler_version=$CC
  fi

  echo "sqlite source: $SQLITE_SOURCE_DIR"
  echo "sqlite manifest: $EXPECTED_MANIFEST"
  echo "compiler: $compiler_version"
  echo "platform: $(uname -srm)"
  echo "amalgamation subject: $SQLITE_SOURCE_DIR/sqlite3.c"
  echo "probe cflags: -std=c11 -O0 -g"
}
