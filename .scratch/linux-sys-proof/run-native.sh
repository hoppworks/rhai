#!/usr/bin/env bash
set -euo pipefail

: "${AGENT_RUNTIME_DIR:?run via run_scoped.py}"
: "${PROOF_STAGE:?exact owned staging path required}"
: "${SOURCE_REVISION:?source revision required}"

log="$PROOF_STAGE/evidence/native-linux-sys.log"
mkdir -p "$AGENT_RUNTIME_DIR/source" "$AGENT_RUNTIME_DIR/cargo-home" "$AGENT_RUNTIME_DIR/target"
tar -xf "$PROOF_STAGE/source.tar" -C "$AGENT_RUNTIME_DIR/source"
export CARGO_HOME="$AGENT_RUNTIME_DIR/cargo-home"
export CARGO_TARGET_DIR="$AGENT_RUNTIME_DIR/target"
source="$AGENT_RUNTIME_DIR/source"
test_file="$source/tests/sys_fs.rs"

{
    printf 'Source revision: %s\n' "$SOURCE_REVISION"
    printf 'Source archive SHA256: '
    sha256sum "$PROOF_STAGE/source.tar"
    printf 'Runtime directory: %s\n' "$AGENT_RUNTIME_DIR"
    uname -a
    cat /etc/os-release
    rustc --version --verbose
    cargo --version --verbose
    printf '%s\n' 'Command: cargo test --features testing-environ,sys,metadata --test sys_policy --test sys_env --test sys_fs -- --nocapture'
} > "$log"

cd "$source"
suite_status=0
cargo test --features testing-environ,sys,metadata --test sys_policy --test sys_env --test sys_fs -- --nocapture >> "$log" 2>&1 || suite_status=$?
printf '\nFull sys suite exit status: %s\n' "$suite_status" >> "$log"

cp "$test_file" "$AGENT_RUNTIME_DIR/sys_fs.rs.correct"
python3 - "$test_file" <<'PY'
from pathlib import Path
import sys
p = Path(sys.argv[1])
b = p.read_bytes()
old = b'assert!(matches!(err, SysError::NotUtf8(..)), "{err}");'
new = b'assert!(matches!(err, SysError::Io { .. }), "{err}");'
assert b.count(old) == 1, f'expected one assertion, found {b.count(old)}'
p.write_bytes(b.replace(old, new))
PY
printf '\nFalse assertion control (expect failure): wrong read_dir error variant\n' >> "$log"
false_status=0
cargo test --features testing-environ,sys,metadata --test sys_fs test_non_utf8_file_name -- --exact --nocapture >> "$log" 2>&1 || false_status=$?
printf 'False assertion control exit status: %s\n' "$false_status" >> "$log"
if [ "$false_status" -eq 0 ]; then
    printf 'False assertion control unexpectedly passed\n' >> "$log"
    exit 1
fi

cp "$AGENT_RUNTIME_DIR/sys_fs.rs.correct" "$test_file"
cmp -s "$test_file" "$AGENT_RUNTIME_DIR/sys_fs.rs.correct"
printf '\nCorrect assertion restored byte-for-byte; rerun public invalid UTF-8 test\n' >> "$log"
correct_status=0
cargo test --features testing-environ,sys,metadata --test sys_fs test_non_utf8_file_name -- --exact --nocapture >> "$log" 2>&1 || correct_status=$?
printf 'Correct assertion exit status: %s\n' "$correct_status" >> "$log"

printf '\nFinal source assertion SHA256: ' >> "$log"
sha256sum "$test_file" >> "$log"
cat "$log"
if [ "$suite_status" -ne 0 ] || [ "$correct_status" -ne 0 ]; then
    exit 1
fi
