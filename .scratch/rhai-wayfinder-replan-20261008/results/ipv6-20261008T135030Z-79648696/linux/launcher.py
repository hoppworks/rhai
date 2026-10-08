import os,subprocess,json
from pathlib import Path
e=Path('/root/rhai-evidence/wayfinder-20261008/ipv6-082b13b7d2');env=os.environ.copy();env['TMPDIR']='/root/.local/share/agent-builds/rhai/ipv6-26e70d5b06'
with (e/'runner.stdout').open('wb') as out,(e/'runner.stderr').open('wb') as err:
 rc=subprocess.call(['python3','/var/home/workhorse/projects/agent-skills/tools/run_scoped.py','--timeout','1200','--','bash',str(e/'payload.sh'),str(e)],env=env,stdout=out,stderr=err)
(e/'runner.status').write_text(str(rc)+'\n');print('runner exit',rc,flush=True)
