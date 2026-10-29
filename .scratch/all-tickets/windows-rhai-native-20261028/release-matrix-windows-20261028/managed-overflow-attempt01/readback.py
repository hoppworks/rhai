"""Independently verify original source, native outputs and custody for this slice."""
from pathlib import Path
import hashlib,json,re,zipfile
root=Path(__file__).resolve().parent
project=root.parents[4]
p=json.loads((root/'preparation.json').read_text())
b=json.loads((root/'binding.json').read_text())
pre=json.loads((root/'host-dispatch-preflight-final.json').read_text())
capture=json.loads((root/'serial-capture-binding.json').read_text())
export=json.loads((root/'original-export-readback.json').read_text())
journal=json.loads((root/'journal-readback.json').read_text())
original=root/'original-export'
observer=json.loads((original/'observer.json').read_text())
def sha(data): return hashlib.sha256(data).hexdigest()
assert p['base_head']==b['base_head']=='f7c42546fc62d3082422be7877619719884bbd70'
assert pre['medium_sha256']==b['iso_sha256']
assert sha((root/'media-input/rhai-source.zip').read_bytes())==b['archive_sha256']
assert sha((root/'media-input/source-manifest.json').read_bytes())==b['source_manifest_sha256']==observer['source_manifest_sha256']
assert sha((root/'media-input/Cargo.lock').read_bytes())==b['lock_sha256']==observer['lock_sha256']
with zipfile.ZipFile(root/'media-input/rhai-source.zip') as z:
    manifest=json.loads((root/'media-input/source-manifest.json').read_text())
    assert len(z.namelist())==448==len(manifest['files'])
    for name,entry in manifest['files'].items():
        data=z.read(name)
        assert len(data)==entry['bytes'] and sha(data)==entry['sha256'],name
    assert sha(z.read('tests/sys_process_windows.rs'))==b['overlay_sha256']
assert capture['inode']==pre['serial_inode'] and capture['offset_start']==pre['serial_offset']
raw=(root/'serial-original.bin').read_bytes()
assert sha(raw)==capture['sha256']==export['serial_sha256']
assert len(raw)==capture['bytes']==capture['offset_end']-capture['offset_start']
assert export['frames']==212 and len(export['files'])==16
for name,entry in export['files'].items():
    data=(original/name).read_bytes()
    assert len(data)==entry['length'] and sha(data)==entry['sha256'],name
assert export['begin']['accepted'] and export['end']['accepted']
assert journal['records']==8 and journal['terminal_removed'] and journal['crc32_and_length_valid'] and journal['payload_exit']=='00000000'
assert observer['driver_exit']==0 and observer['accepted'] and observer['target_suite_complete'] and observer['wrong_expectation_rejected']
assert observer['driver_exited'] and observer['pipes_drained'] and observer['process_disposed'] and observer['owned_executables_stopped']
assert not observer['custody_pending'] and not observer['observer_kill_used'] and not observer['product_acceptance']
assert observer['driver_elapsed_seconds']<185
runtime=next((original/'run').glob('.scoped-evidence-*/runtime'))
assert 'cargo 1.77.2' in (runtime/'cargo-version.txt').read_text()
assert 'rustc 1.77.2' in (runtime/'rustc-version.txt').read_text()
compile_log=(runtime/'compile.log').read_text()
exe=re.search(r'Executable tests\\sys_process_windows\.rs \(([^)]+)\)',compile_log).group(1)
for name,summary in [('managed-overflow-wrong.log','test result: FAILED. 0 passed; 1 failed;'),('managed-overflow-green.log','test result: ok. 35 passed; 0 failed; 0 ignored;')]:
    text=(runtime/name).read_text()
    assert re.search(r'Running tests\\sys_process_windows\.rs \(([^)]+)\)',text).group(1)==exe
    assert 'windows_managed_output_limit_closes_descendant_and_preserves_sentinel' in text and 'windows_managed_overflow_readback' in text and 'worker_stopped=true' in text and 'parent_stopped=true' in text and 'sentinel_alive=true' in text and summary in text
assert 'deliberately wrong managed overflow closure expectation' in (runtime/'managed-overflow-wrong.log').read_text()
stdout=(runtime.parent/'stdout.log').read_text()
for marker in ['RHAI_MANAGED_OVERFLOW_COMPILE_EXIT=0','RHAI_MANAGED_OVERFLOW_WRONG_EXIT=101','RHAI_MANAGED_OVERFLOW_GREEN_EXIT=0','RHAI_CARGO_CLEAN_EXIT=0','RHAI_MANAGED_OVERFLOW_CONTROLS_PASS']:
    assert marker in stdout,marker
result={'source_base':b['base_head'],'overlay_sha256':b['overlay_sha256'],'features':b['features'],'red_exit':101,'green_exit':0,'same_executable':exe,'driver_exit':0,'driver_seconds':observer['driver_elapsed_seconds'],'frames':212,'original_files':16,'journal_records':8,'inner_runtime_removed':True,'outer_guest_and_host_cleanup_pending':True}
(root/'readback.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result,indent=2))
