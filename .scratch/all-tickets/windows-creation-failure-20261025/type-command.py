"""Type the exact hash-guarded native entry without Enter; inspect before commit."""
from pathlib import Path
import sys,subprocess,json,hashlib,shlex,datetime,re
p=Path(sys.argv[1]).resolve() if len(sys.argv)>1 else Path(__file__).resolve().parent;b=json.loads((p/'binding.json').read_text());m=json.loads((p/'media-readback.json').read_text())
now=datetime.datetime.now(datetime.timezone.utc);expiry=datetime.datetime.fromisoformat(b['retained']['expires_utc']);assert (expiry-now).total_seconds()>900
assert hashlib.sha256((p/'Start.ps1').read_bytes()).hexdigest()==b['start_sha256']==m['files']['Start.ps1']
for name,h in b['files'].items():assert hashlib.sha256((p/'input'/name).read_bytes()).hexdigest()==h
r=subprocess.run(['ssh','workhorse','virsh domuuid rhai-win11-quality; stat -c "%i %s" /var/log/libvirt/qemu/rhai-win11-quality-serial0.log; df -B1 /var'],capture_output=True,text=True,check=True)
assert b['host_source_root'].startswith('/var/roothome/projects/rhai-creation-failure-') and 'dc5b8fd5-1a0b-4d86-8b8f-aaa1bd492b19' in r.stdout
(p/'admission-query.stdout').write_text(r.stdout)
match=re.search(r'(?m)^([0-9]+) ([0-9]+)$',r.stdout);assert match,r.stdout
inode,offset=map(int,match.groups());d={'utc':now.isoformat(),'serial_inode':inode,'serial_offset':offset,'source_sha256':b['start_sha256'],'manifest_sha256':b['input_manifest_sha256'],'medium_sha256':m['sha256'],'enter_sent':False,'capacity':r.stdout,'native_launches_before_enter':0}
(p/'dispatch.json').write_text(json.dumps(d,indent=2)+'\n')
subprocess.run(['ssh','workhorse','virsh change-media rhai-win11-quality sdc '+shlex.quote(b['medium'])+' --live --force'],check=True)
repo=next(a for a in p.parents if (a/'tools/windows-scoped-runner').is_dir());code=(repo/'.scratch/all-tickets/windows-workhorse-retirement-20261025/console-key-input.py').read_text();command=(p/'dispatch-command.txt').read_text().rstrip('\n');assert '\n' not in command
scope='/var/roothome/.local/share/agent-builds/rhai/creation-keyboard-'+b['nonce']
run='mkdir '+shlex.quote(scope)+'\nTMPDIR='+shlex.quote(scope)+' PYTHONDONTWRITEBYTECODE=1 python3 /var/home/workhorse/projects/agent-skills/tools/run_scoped.py --timeout 90 -- python3 -B -c '+shlex.quote(code)+' '+shlex.quote(command)+'\nkeyboard_status=$?\nrmdir '+shlex.quote(scope)+'\nexit "$keyboard_status"'
r=subprocess.run(['ssh','workhorse',run],capture_output=True,text=True);(p/'type.stdout').write_text(r.stdout);(p/'type.stderr').write_text(r.stderr);r.check_returncode();print('Exact command typed, Enter deliberately pending screenshot check.')
