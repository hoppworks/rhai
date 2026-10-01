import ast
import hashlib
import os
import re
import errno
from pathlib import Path

raw_path = Path('.scratch/process-unix-run/evidence/post-reap-kill.UbWTw2')
raw = raw_path.read_text()
fixture = Path('tests/fixtures/sys_process_shared_child_contract.rs').read_text()
raw_sha = hashlib.sha256(raw_path.read_bytes()).hexdigest()
expected_fixture_sha = '57429a385097e5bc9c06cc2fa7eef9b0e73ae57cfb5f2884d883c1993e240f95'
fixture_sha = hashlib.sha256(Path('tests/fixtures/sys_process_shared_child_contract.rs').read_bytes()).hexdigest()

control_start = raw.index('cargo_argv=', raw.index('post_reap_wrong_control_fixture_sha256='))
control_end = raw.index('post_reap_wrong_control status=', control_start)
control = raw[control_start:control_end]
green_start = raw.index("cargo_argv=", raw.index("post_reap_wrong_control_source_restored=True"))
green = raw[green_start:]

control_ok = (
    'cargo_status=101' in control
    and 'shared_child_contract::spawn_returns_while_large_stdin_is_blocked_and_wait_snapshots_are_stable' in control
    and 'post-completion kill preserves cached exit status' in control
    and 'left: 17' in control and 'right: 18' in control
    and 'shared-child controller_reaped scenario=blocked_input_wait_snapshot' in control
    and re.search(r'shared-child controller_esrch pid=\d+ verified=true', control)
    and re.search(r'shared-child fixture_cleanup pid=\d+ absent=true', control)
    and 'post_reap_wrong_control status=101 exact_failed_test=True one_failure=True intended_cached_snapshot_assertion=True controller_reaped=True controller_esrch=True fixture_child_esrch=True fixture_root_owned_absent=True' in raw
    and 'post_reap_wrong_control_source_restored=True' in raw
)

scenario = re.search(r'shared-child scenario=blocked_input_wait_snapshot controller_pid=(\d+) status=ok fixture_record=Some\("pid=(\d+) state=exited code=17\\n"\)', green)
if scenario:
    controller_pid, fixture_pid = map(int, scenario.groups())
    controller_reaped = re.search(rf'shared-child controller_reaped scenario=blocked_input_wait_snapshot pid={controller_pid} status=exit status: 0', green)
    controller_esrch = f'shared-child controller_esrch pid={controller_pid} verified=true' in green
    fixture_esrch = f'shared-child fixture_cleanup pid={fixture_pid} absent=true' in green
    try:
        os.kill(fixture_pid, 0)
        fixture_pid_absent = False
    except ProcessLookupError:
        fixture_pid_absent = True
    except PermissionError:
        fixture_pid_absent = False
    fixture_root = re.search(rf'shared-child controller_started scenario=blocked_input_wait_snapshot pid={controller_pid} root=(\S+)', green)
    root_absent = bool(fixture_root and not Path(fixture_root.group(1)).exists())
else:
    controller_pid = fixture_pid = 0
    controller_reaped = controller_esrch = fixture_esrch = root_absent = fixture_pid_absent = False

started = re.findall(r'(?m)^test (shared_child_contract::[^ ]+) \.\.\.', green)
all_tests = re.search(r'(?m)^test result: ok\. 6 passed; 0 failed;', green) is not None
manifest_re = lambda key, text: re.search(rf'(?m)^{key}=(\{{.*\}})$', text)
manifest_matches = {key: manifest_re(key, raw if key == 'private_source_hashes' else green) for key in ('private_source_hashes', 'final_private_source_hashes', 'final_original_overlay_hashes')}
all_manifest = all(match is not None for match in manifest_matches.values())
if all_manifest:
    private_manifest, final_manifest, original_manifest = (ast.literal_eval(manifest_matches[key].group(1)) for key in ('private_source_hashes', 'final_private_source_hashes', 'final_original_overlay_hashes'))
    injected_hash_match = re.search(r'(?m)^final_private_injected_test_hash=([0-9a-f]{64})$', green)
    expected_final = dict(private_manifest)
    all_manifest = injected_hash_match is not None
    if all_manifest:
        expected_final['tests/sys_process.rs'] = injected_hash_match.group(1)
        all_manifest = final_manifest == expected_final and original_manifest == private_manifest
        all_manifest = all_manifest and original_manifest['tests/sys_process.rs'] != injected_hash_match.group(1)

# The retained runner output includes exact final source hashes; require source-level assertions too.
source_assertions = all(token in fixture for token in (
    'child.kill()', 'post-completion kill preserves cached exit status',
    'after_kill_wait', 'after_kill_try_wait', 'assert_pid_reaped(pid)',
    'stdout_complete', 'stderr_complete',
))

# Prove the offline receipt checks reject altered scenario fields and control/restoration evidence.
def scenario_receipt(text):
    match = re.search(r'shared-child scenario=blocked_input_wait_snapshot controller_pid=(\d+) status=ok fixture_record=Some\(\"pid=(\d+) state=exited code=17\\n\"\)', text)
    if not match:
        return False
    controller, child = map(int, match.groups())
    return (
        f'shared-child controller_reaped scenario=blocked_input_wait_snapshot pid={controller} status=exit status: 0' in text
        and f'shared-child controller_esrch pid={controller} verified=true' in text
        and f'shared-child fixture_cleanup pid={child} absent=true' in text
    )

def control_receipt(text):
    return (
        'cargo_status=101' in text
        and re.search(r'(?m)^running 1 test$', text) is not None
        and re.search(r'(?m)^test shared_child_contract::spawn_returns_while_large_stdin_is_blocked_and_wait_snapshots_are_stable \.\.\.', text) is not None
        and 'failures:\n    shared_child_contract::scenario_entry' in text
        and 'post-completion kill preserves cached exit status' in text
        and 'left: 17\n right: 18' in text
        and 'post_reap_wrong_control_source_restored=True' in text
        and re.search(r'shared-child fixture_cleanup pid=\d+ absent=true', text)
    )

green_scenario_text = green[green.find('shared-child controller_started scenario=blocked_input_wait_snapshot'):green.find('shared-child scenario=blocked_input_wait_snapshot') + 400]
control_with_receipt = control + raw[control_end:raw.index('cargo_argv=', raw.index('post_reap_wrong_control_source_restored=True'))]
control_mutated_name = re.sub(r'(?m)^test shared_child_contract::spawn_returns_while_large_stdin_is_blocked_and_wait_snapshots_are_stable', 'test shared_child_contract::unrelated_test', control_with_receipt, count=1)
control_baseline_valid = control_receipt(control_with_receipt)
scenario_baseline_valid = scenario_receipt(green_scenario_text)
mutation_rejections = {
    'scenario_code': scenario_baseline_valid and not scenario_receipt(green_scenario_text.replace('code=17', 'code=16')),
    'controller_identity': scenario_baseline_valid and not scenario_receipt(green_scenario_text.replace(f'controller_pid={controller_pid}', 'controller_pid=99999', 1)),
    'wrong_control_assertion': control_baseline_valid and not control_receipt(control_with_receipt.replace('left: 17\n right: 18', 'left: 16\n right: 18', 1)),
    'named_failed_test': control_baseline_valid and not control_receipt(control_mutated_name),
    'source_restoration': control_baseline_valid and not control_receipt(control_with_receipt.replace('post_reap_wrong_control_source_restored=True', 'post_reap_wrong_control_source_restored=False', 1)),
    'module_success_summary': 'test result: ok. 6 passed; 0 failed;' in green and 'test result: ok. 6 passed; 0 failed;' not in green.replace('test result: ok. 6 passed; 0 failed;', 'test result: ok. 5 passed; 1 failed;', 1),
}

checks = {
    'raw_sha256': raw_sha == 'd2b2bad07dc9e283ad7e4ce690fe16007580c65da6b22c8b21ad63a61f85e7c1',
    'tested_fixture_hash_recorded_in_run': expected_fixture_sha in raw,
    'current_fixture_change_is_only_the_post-run_custody_comment': hashlib.sha256(fixture.replace('''/// The scoped runner owns the group watchdog; this guard terminates and reaps only the exact\n/// direct controller, then verifies any recorded OS fixture PID before its temp root is dropped.''', '''/// On timeout or assertion unwind the guard kills only that group, reaps its direct controller,\n/// then verifies any recorded OS fixture PID is absent before its temp root is dropped.''').encode()).hexdigest() == expected_fixture_sha,
    'wrong_control_exact_cached_code_assertion_after_cleanup': bool(control_ok),
    'restored_green_cargo_status_zero': 'cargo_status=0' in green,
    'restored_module_6_of_6': bool(all_tests and len(started) == 6),
    'scenario_exit_record_code17': bool(scenario),
    'matching_controller_reaped_and_esrch': bool(controller_reaped and controller_esrch),
    'fixture_cleanup_record_and_root_absent': bool(fixture_esrch and root_absent),
    'fixture_and_controller_pid_readback': bool(fixture_pid and controller_pid),
    'all_source_manifests_and_restoration': bool(all_manifest),
    'source_contains_required_cached_snapshot_assertions': bool(source_assertions),
    'captured_nested_marker_explanation_matches_controller_record': bool(scenario and 'state=exited code=17\\n' in scenario.group(0)),
    'mutated_receipts_are_rejected': all(mutation_rejections.values()),
    'control_and_scenario_baselines_are_valid': bool(control_baseline_valid and scenario_baseline_valid),
}
for key, value in mutation_rejections.items():
    print(f'mutation_{key}_rejected={str(value).lower()}')
for key, value in checks.items():
    print(f'{key}={str(value).lower()}')
print(f'green_scenario_controller_pid={controller_pid} fixture_pid={fixture_pid}')
print('nested_eprintln_marker_is_not_in_outer_output=true; validated using scenario status/fixture record plus passed Rust assertions')
if not all(checks.values()):
    raise SystemExit(1)
