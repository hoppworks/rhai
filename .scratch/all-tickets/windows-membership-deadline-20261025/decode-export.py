import json,os,shutil,subprocess,sys
from pathlib import Path
p=Path(sys.argv[1]);tag=sys.argv[2];nonce=sys.argv[3]
r=Path(os.environ['AGENT_RUNTIME_DIR']);stage=r/('decode-'+tag);stage.mkdir()
repo=p.parents[2];source=repo/'.scratch/rhai-wayfinder-replan-20261008/results/windows-custody-20261008T125846Z-b7f83433/collect_serial.py'
shutil.copyfile(source,stage/'collect_serial.py');shutil.copyfile(p/(tag+'-serial-original.txt'),stage/(tag+'-serial-original.txt'))
subprocess.run([sys.executable,'-B',str(stage/'collect_serial.py'),tag,nonce],check=True,stdout=subprocess.DEVNULL)
shutil.copytree(stage/(tag+'-export'),p/(tag+'-export'));shutil.copyfile(stage/(tag+'-export-readback.json'),p/(tag+'-export-readback.json'))
d=json.loads((p/(tag+'-export-readback.json')).read_text());print(json.dumps({'frames':d['frames'],'files':len(d['files']),'end':d['end']}))
