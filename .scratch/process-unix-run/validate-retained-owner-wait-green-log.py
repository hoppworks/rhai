from pathlib import Path
import ast
import hashlib

repo = Path('/Users/hoppworks/projects/rhai-process-unix-run')
log = repo / '.scratch/process-unix-run/evidence/retained-owner-wait-green.yMPW3O'
runtime = Path('/var/folders/yk/m4dzf0ss5x9f4j4z3xb2rrv40000gn/T/agent-build-1k_k7mvq')
raw = log.read_text(errors='replace')
checks = {
    'wrong-control status101': 'case_status=101 label=retained-owner-wait-wrong-snapshot-control' in raw,
    'wrong-control expected assertion': 'assertion `left != right` failed: published report changed after cleanup' in raw,
    'wrong-control exact test failed': 'test packages::sys::process::unix::tests::non_consuming_cleanup_wait_failure_publishes_frozen_snapshot ... FAILED' in raw,
    'wrong-control child ESRCH': 'retained-owner-wait child_pid=10469 reap=ESRCH' in raw,
    'restored exact test passed': 'test packages::sys::process::unix::tests::non_consuming_cleanup_wait_failure_publishes_frozen_snapshot ... ok' in raw,
    'restored child ESRCH': 'retained-owner-wait child_pid=10501 reap=ESRCH' in raw,
    'run-scoped runtime absent': not runtime.exists() and not runtime.is_symlink(),
}
unit = 'src/packages/sys/process/unix.rs'
current_hash = hashlib.sha256((repo / unit).read_bytes()).hexdigest()
checks['tested unix source matches private manifest'] = "'src/packages/sys/process/unix.rs': '" + current_hash + "'" in raw and current_hash == 'fa15d7f91629b3507dc274efe8847a91efb5cd708df1e67d61b84766430c0fbb'
# The pre-GREEN restoration guard ran successfully before its cargo invocation; final manifest export was skipped by the validator bug.
assertion = 'non-consuming wait failure must publish an unavailable exit snapshot'
checks['frozen test contains unavailable-exit assertion'] = assertion in (repo / unit).read_text()
for name, ok in checks.items():
    print(f'replay_check={name} status={"PASS" if ok else "FAIL"}')
if not all(checks.values()):
    raise SystemExit(1)
print('replay_result=PASS; original wrapper status/cleanup status are separately retained in command receipt (1/0); no native command rerun')
