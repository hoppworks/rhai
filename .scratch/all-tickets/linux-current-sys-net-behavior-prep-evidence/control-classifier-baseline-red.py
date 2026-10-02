from pathlib import Path

root = Path('/Users/hoppworks/.codex/worktrees/all-tickets-continuation/rhai/.scratch')
no_object = (root / 'net-feature-proof/logs/noobj-peer-wrong.log').read_text()
expected_no_object_diagnostic = 'independent peer observed exact script bytes'
old_no_object_accepts_intended_red = expected_no_object_diagnostic in no_object
compile_failure_with_digit = 'error[E0432]: unresolved import; diagnostic code 254'
old_write_accepts_incidental_101 = 101 == 101 and '254' in compile_failure_with_digit
print(f'old_no_object_accepts_intended_red={old_no_object_accepts_intended_red}')
print(f'old_write_accepts_incidental_101={old_write_accepts_incidental_101}')
failures = []
if not old_no_object_accepts_intended_red:
    failures.append('no_object old selector missed its intentional wrong-peer assertion')
if old_write_accepts_incidental_101:
    failures.append('write old selector accepted unrelated status 101 containing 254')
for failure in failures:
    print('REGRESSION_RED: ' + failure)
if failures:
    raise SystemExit(1)
