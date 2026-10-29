"""Validate the original native expected-RED reproduction without claiming acceptance."""
from pathlib import Path
import hashlib,json,zipfile
p=Path(__file__).resolve().parent
b=json.loads((p/'binding.json').read_text());pre=json.loads((p/'host-dispatch-preflight-final.json').read_text())
capture=json.loads((p/'serial-capture-binding.json').read_text());export=json.loads((p/'original-export-readback.json').read_text())
j=json.loads((p/'journal-readback.json').read_text());o=json.loads((p/'original-export/observer.json').read_text())
def sha(x):return hashlib.sha256(x).hexdigest()
assert b['base_head']=='9a03f2ce9a1800293bf09b98e5ee6bc1d23c8c4b'
assert sha((p/'media-input/rhai-source.zip').read_bytes())==b['archive_sha256']
assert sha((p/'media-input/source-manifest.json').read_bytes())==b['source_manifest_sha256']==o['source_manifest_sha256']
assert sha((p/'media-input/Cargo.lock').read_bytes())==b['lock_sha256']==o['lock_sha256']
with zipfile.ZipFile(p/'media-input/rhai-source.zip') as z:assert sha(z.read('tests/sys_process_windows.rs'))==b['overlay_sha256']
raw=(p/'serial-original.bin').read_bytes()
assert sha(raw)==capture['sha256']==export['serial_sha256'] and len(raw)==capture['bytes']
assert capture['inode']==pre['serial_inode'] and capture['offset_start']==pre['serial_offset']
assert capture['rotation']['old_suffix_bytes']+capture['rotation']['new_prefix_bytes']==len(raw)
assert export['frames']==202 and len(export['files'])==15
for name,v in export['files'].items():
 data=(p/'original-export'/name).read_bytes();assert len(data)==v['length'] and sha(data)==v['sha256'],name
assert o['accepted'] and o['baseline_reproduced'] and o['actual_outcome']=='expected-red' and o['driver_exit']==0
assert o['driver_exited'] and o['pipes_drained'] and o['process_disposed'] and o['owned_executables_stopped']
assert not o['wrong_expectation_rejected'] and not o['target_suite_complete'] and not o['product_acceptance'] and not o['custody_pending'] and not o['observer_kill_used']
assert j['records']==8 and j['terminal_removed'] and j['crc32_and_length_valid'] and j['payload_exit']=='00000000'
runtime=next((p/'original-export/run').glob('.scoped-evidence-*/runtime'))
assert 'cargo 1.77.2' in (runtime/'cargo-version.txt').read_text() and 'rustc 1.77.2' in (runtime/'rustc-version.txt').read_text()
log=(runtime/'env-remove-baseline.log').read_text()
for token in ['windows_env_remove_preserves_parent_and_applies_overrides','label=direct-run observation=None','unsupported Windows process option `env_remove`','ENV_REMOVE_CONTRACT direct-run','test result: FAILED. 0 passed; 1 failed;']:
 assert token in log,token
stdout=(runtime.parent/'stdout.log').read_text()
assert 'RHAI_ENV_REMOVE_BASELINE_EXIT=101' in stdout and 'RHAI_ENV_REMOVE_BASELINE_REPRODUCED' in stdout
result={'baseline_red':True,'product_acceptance':False,'test_exit':101,'driver_exit':0,'driver_seconds':o['driver_elapsed_seconds'],'frames':202,'original_files':15,'journal_records':8,'serial_rotation_reconstructed':True,'guest_and_host_cleanup_pending_at_readback':True}
(p/'readback.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
