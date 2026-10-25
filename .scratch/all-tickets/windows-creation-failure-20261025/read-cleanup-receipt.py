from pathlib import Path
import json,subprocess,shlex,base64,hashlib
p=Path(__file__).resolve().parent;d=json.loads((p/'cleanup-dispatch.json').read_text());proof=json.loads((p/'cleanup-host-manifest.json').read_text())
code='''from pathlib import Path
import os,sys
base=Path('/var/log/libvirt/qemu/rhai-win11-quality-serial0.log');old=base.with_name(base.name+'.0');expected=INODE;offset=OFFSET
paths=[x for x in (old,base)if x.exists() and x.stat().st_ino==expected];assert len(paths)==1
with paths[0].open('rb')as f:
 assert os.fstat(f.fileno()).st_ino==expected;f.seek(offset);data=f.read()
if paths[0]==old:
 with base.open('rb')as f:data+=f.read()
assert len(data)<1024*1024;sys.stdout.buffer.write(data)
'''.replace('INODE',str(d['serial_inode'])).replace('OFFSET',str(d['serial_offset']))
r=subprocess.run(['ssh','workhorse','python3 -c '+shlex.quote(code)],capture_output=True,check=True);(p/'cleanup-serial-original.txt').write_bytes(r.stdout)
lines=[line.split(b' ',1)[1]for line in r.stdout.splitlines()if line.startswith(b'RHAI_CREATION_CLEANUP ')];assert len(lines)==1,'Actual cleanup receipt not available; no blind repeat'
o=json.loads(base64.b64decode(lines[0],validate=True));assert o['nonce']==proof['nonce'] and o['host_manifest_sha256']==hashlib.sha256((p/'cleanup-host-manifest.json').read_bytes()).hexdigest() and o['host_receipt_sha256']==proof['host_receipt_sha256']
assert sorted(o['retired'])==sorted(s['scope']for s in proof['scopes']) and o['all_scopes_absent'] and o['retained_build_preserved'] and o['retained_build']==proof['retain']['scope'] and not o['foreign_resources_touched'] and o['failed_originals_exported']
expected={(s['trace']['process_id'],s['trace']['creation'])for s in proof['scopes']if s.get('profile')=='POST_CREATE_ABORT'}
assert {(x['pid'],x['creation'])for x in o['actor_checks']}==expected and all(not x['original_alive']for x in o['actor_checks'])
(p/'guest-cleanup-receipt.json').write_text(json.dumps(o,indent=2)+'\n');print('Native cleanup readback:7scopes absent,3exact actor identities stopped,baseline preserved')
