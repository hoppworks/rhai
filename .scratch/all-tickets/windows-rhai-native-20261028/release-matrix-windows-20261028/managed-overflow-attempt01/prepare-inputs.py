"""Bind the Managed overflow test and affected full suite to the supervised route."""
import hashlib,json
from pathlib import Path
root=Path(__file__).resolve().parent;old=root.parent/'stdin-close-attempt01';media=root/'media-input'
p=json.loads((root/'preparation.json').read_text());m=json.loads((media/'source-manifest.json').read_text())
ob=json.loads((old/'binding.json').read_text());oldn=ob['nonce'];n=p['nonce']
assert n=='996bad1b0372473bb01b3a7c2c770535'
def sha(b):return hashlib.sha256(b).hexdigest()
def text(name):return (old/'media-input'/name).read_text()
def write(name,s,crlf=False):
 s=s.replace('\r\n','\n')
 if crlf:s=s.replace('\n','\r\n')
 (media/name).write_bytes(s.encode());return sha((media/name).read_bytes())
def rep(s,a,b):
 assert a in s,a
 return s.replace(a,b)
clear=rep(text('ClearOwnedWorkReadOnly.ps1'),oldn[:8],n[:8]);clearh=write('ClearOwnedWorkReadOnly.ps1',clear)
contract=text('RunRhaiContract.cmd')
for a,b in [
 ('RHAI_WINDOWS_STDIN_CLOSE_WRONG_EXPECTATION','RHAI_WINDOWS_MANAGED_OVERFLOW_WRONG_EXPECTATION'),
 ('RHAI_STDIN_CLOSE','RHAI_MANAGED_OVERFLOW'),
 ('windows_spawn_retains_early_stdin_close_error','windows_managed_output_limit_closes_descendant_and_preserves_sentinel'),
 ('stdin-close','managed-overflow'),
 ('windows_stdin_close_readback','windows_managed_overflow_readback'),
 ('deliberately wrong managed-overflow error expectation','deliberately wrong managed overflow closure expectation')]:
 contract=rep(contract,a,b)
target='"%~dp0cargo.exe" test --locked --features %PROFILE% %TARGET% windows_managed_output_limit_closes_descendant_and_preserves_sentinel -- --exact --nocapture > managed-overflow-green.log 2>&1'
assert target in contract
contract=contract.replace(target,'"%~dp0cargo.exe" test --locked --features %PROFILE% %TARGET% -- --test-threads=1 --nocapture > managed-overflow-green.log 2>&1')
contracth=write('RunRhaiContract.cmd',contract,True)
control=text('RunRhaiContractControl.ps1')
for a,b in [
 (oldn[:8],n[:8]),(ob['source_manifest_sha256'],p['manifest_sha256']),
 ('RHAI_STDIN_CLOSE','RHAI_MANAGED_OVERFLOW'),
 ('stdin-close','managed-overflow'),
 ('windows_spawn_retains_early_stdin_close_error','windows_managed_output_limit_closes_descendant_and_preserves_sentinel'),
 ('windows_stdin_close_readback','windows_managed_overflow_readback'),
 ('retained=true','worker_stopped=true'),
 ('deliberately wrong managed-overflow error expectation','deliberately wrong managed overflow closure expectation'),
 ('test result: ok. 1 passed; 0 failed; 0 ignored;','test result: ok. 35 passed; 0 failed; 0 ignored;')]:
 control=rep(control,a,b)
controlh=write('RunRhaiContractControl.ps1',control)
start=text('Start.ps1')
oldm=json.loads((old/'media-input/source-manifest.json').read_text())
for a,b in [
 (oldn,n),(ob['archive_sha256'],p['archive_sha256']),(ob['source_manifest_sha256'],p['manifest_sha256']),
 (ob['media_files']['RunRhaiContractControl.ps1']['sha256'],controlh),
 (ob['media_files']['RunRhaiContract.cmd']['sha256'],contracth),
 (ob['media_files']['ClearOwnedWorkReadOnly.ps1']['sha256'],clearh),
 (ob['base_head'],p['base_head']),(str(oldm['total_source_bytes']),str(m['total_source_bytes']))]:
 start=rep(start,a,b)
starth=write('Start.ps1',start);write('rhai-native-'+n+'.bundle','rhai-native-'+n+'\n')
assert len(list(media.iterdir()))==8
files={x.name:{'bytes':x.stat().st_size,'sha256':sha(x.read_bytes())} for x in media.iterdir()}
b={'nonce':n,'base_head':p['base_head'],'overlay_sha256':p['overlay_sha256'],'source_manifest_sha256':p['manifest_sha256'],'archive_sha256':p['archive_sha256'],'lock_sha256':p['lock_sha256'],'features':'testing-environ,sys,net','target':'sys_process_windows','test':'windows_managed_output_limit_closes_descendant_and_preserves_sentinel','media_files':files,'driver_deadline_seconds':180,'observer_deadline_seconds':185,'export_deadline_seconds':180,'start_sha256':starth,'native_started':False}
(root/'binding.json').write_text(json.dumps(b,indent=2)+'\n')
print(json.dumps({'start_sha256':starth,'control_sha256':controlh,'contract_sha256':contracth,'attribute_sha256':clearh},indent=2))
