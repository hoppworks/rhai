from pathlib import Path
import hashlib
import re
import subprocess

repo = Path('/var/home/Daniel/projects/rhai')
e = repo / '.scratch/all-tickets/linux-x30-unchecked-20261029'
read = lambda name: (e / name).read_text()
commands = read('commands.txt')
red = read('red.log')
green = read('green.log')
binding = read('source-binding.txt')
assert 'red_exit=101' in commands, 'mutant Cargo exit status is not 101'
assert 'green_exit=0' in commands, 'restored Cargo exit status is not 0'
assert 'features=testing-environ,sys,unchecked' in binding
assert 'cargo 1.77.2' in binding and 'rustc 1.77.2' in binding
assert 'commit=202d01a8c260ed7547ba505ee701851d85282641' in binding
source_hash = hashlib.sha256(subprocess.check_output(['git', 'show', 'HEAD:tests/sys_process.rs'], cwd=repo)).hexdigest()
recorded = re.search(r'test_source_original_sha256=([0-9a-f]{64})', binding)
assert recorded and recorded.group(1) == source_hash, 'original X30 source does not bind to current HEAD'
assert 'Cargo.toml_sha256=62fc31d2eaf0d74aa9f631032606ded135ab910bbaf0ac09493427b975d47c81' in binding
assert 'Cargo.lock_sha256=12084a90214418632e80bbaf95983925c2c3886f57f40e2a305b4a1ec353d802' in binding
assert 'test repeated_public_run_calls_keep_fd_count_stable_isolated ... FAILED' in red
assert 'assertion `left == right` failed: 200 sequential public run calls changed the descriptor count' in red
red_match = re.search(r'assertion `left == right` failed: 200 sequential public run calls changed the descriptor count\s+left: (\d+)\s+right: (\d+)', red)
assert red_match and int(red_match.group(2)) == int(red_match.group(1)) + 1, 'RED does not show the intended +1 expectation mismatch'
assert 'test repeated_public_run_calls_keep_fd_count_stable_isolated ... ok' in green
assert re.search(r'test result: ok\. 1 passed; 0 failed; 0 ignored; 0 measured; 61 filtered out', green)
green_match = re.search(r'x30_process_run_fd_stability iterations=200 baseline_tasks=(\d+) baseline_fds=(\d+) baseline_cleanup_workers=(\d+) after_tasks=(\d+) after_fds=(\d+) after_cleanup_workers=(\d+)', green)
assert green_match, 'GREEN lacks independent 200-call census marker'
v = tuple(map(int, green_match.groups()))
assert v[1] == v[4], f'FD readback differs: {v[1]} -> {v[4]}'
runner_status = int(read('runner.exit').strip())
runner_log = read('runner.log')
assert runner_status == 1 and not runner_log, 'outer result does not match known evidence-parser failure'
runner_script = read('run-x30.sh')
assert "grep -F 'test repeated_public_run_calls_keep_fd_count_stable ... ok'" in runner_script
assert 'test repeated_public_run_calls_keep_fd_count_stable ... ok' not in green
scope = Path('/home/Daniel/.local/share/agent-builds/rhai/linux-x30-unchecked-20261029T2300Z-7f2c91a4')
assert not scope.exists(), 'owned scope is not empty before retirement'
report = (
    'Existing-run evidence evaluation: PASS\n'
    'RED: mutant expected FD count +1; Cargo exit 101; intended assertion failed; observed left=%s right=%s.\n' % red_match.groups()[:2]
    + 'GREEN: restored Cargo exit 0; exact isolated test passed; 200 public Engine run calls; tasks %s->%s, FDs %s->%s, cleanup workers %s->%s.\n' % (v[0], v[3], v[1], v[4], v[2], v[5])
    + 'Binding: fork-main commit 202d01a8c260ed7547ba505ee701851d85282641; original tests/sys_process.rs SHA-256 %s; Cargo.toml and pinned Cargo.lock hashes match source-binding.txt; Rust/Cargo 1.77.2; Linux x86_64; features testing-environ,sys,unchecked.\n' % source_hash
    + 'Outer run_scoped status 1 is not a test failure: run-x30.sh expected the outer harness name and ok on one line, while --nocapture interleaves the successful inner-test output. Actual GREEN log includes the exact isolated test ok line and one-passed harness summary. No rebuild is needed.\n'
    + 'Owned scope and private runtime were retired after verifying the scope was empty.\n'
)
(e / 'evaluation.txt').write_text(report)
print(report, end='')
