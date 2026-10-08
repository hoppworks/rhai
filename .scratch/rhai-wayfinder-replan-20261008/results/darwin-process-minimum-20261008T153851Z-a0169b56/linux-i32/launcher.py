import os,subprocess,json
from pathlib import Path
e=Path('/root/rhai-evidence/wayfinder-20261008/process-i32-39b945d2d4');scope=Path('/root/.local/share/agent-builds/rhai/process-i32-39b945d2d4');scope.mkdir(parents=True,exist_ok=False)
stat=scope.stat();(e/'scope.json').write_text(json.dumps({'path':str(scope),'device':stat.st_dev,'inode':stat.st_ino,'uid':stat.st_uid})+'\n')
env=os.environ.copy();env['TMPDIR']=str(scope)
with (e/'runner.stdout').open('wb') as out,(e/'runner.stderr').open('wb') as err:
 rc=subprocess.call(['python3','/var/home/workhorse/projects/agent-skills/tools/run_scoped.py','--timeout','600','--','bash',str(e/'payload.sh'),str(e)],env=env,stdout=out,stderr=err)
(e/'runner.status').write_text(str(rc)+'\n');print('runner exit',rc,flush=True)
r=json.loads((e/'result.json').read_text()) if (e/'result.json').exists() else {}
identity=scope.stat();same=(identity.st_dev,identity.st_ino,identity.st_uid)==(stat.st_dev,stat.st_ino,stat.st_uid)
if same and not list(scope.iterdir()):scope.rmdir()
(e/'cleanup.json').write_text(json.dumps({'runner_exit':rc,'runtime_absent':not Path(r.get('runtime',str(scope/'missing'))).exists(),'scope_absent':not scope.exists(),'owned_identity_matches':same,'logs_retained':True},indent=2)+'\n')
raise SystemExit(rc)
