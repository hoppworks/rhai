from pathlib import Path
import os,shutil,subprocess,json,sys
p=Path(sys.argv[1]).resolve() if len(sys.argv)>1 else Path(__file__).resolve().parent;b=json.loads((p/'binding.json').read_text());r=Path(os.environ['AGENT_RUNTIME_DIR']);repo=next(a for a in p.parents if (a/'tools/windows-scoped-runner').is_dir())
helper=repo/'.scratch/rhai-wayfinder-replan-20261008/results/windows-custody-20261008T125846Z-b7f83433/collect_serial.py'
for c in b['controls']:
 stage=r/c['tag'];stage.mkdir();shutil.copyfile(helper,stage/'collect_serial.py');shutil.copyfile(p/'serial-original.txt',stage/(c['tag']+'-serial-original.txt'))
 subprocess.run([sys.executable,'-B',str(stage/'collect_serial.py'),c['tag'],c['id']],check=True,stdout=subprocess.DEVNULL)
 shutil.copytree(stage/(c['tag']+'-export'),p/(c['tag']+'-export'));shutil.copyfile(stage/(c['tag']+'-export-readback.json'),p/(c['tag']+'-export-readback.json'))
 d=json.loads((p/(c['tag']+'-export-readback.json')).read_text());print(c['profile'],d['frames'],'frames',len(d['files']),'files',d['end']['accepted'])
if b.get('purpose')!='diagnostic-only':
 helper=Path(__file__).resolve().parent/'verify-results.py'
 subprocess.run([sys.executable,'-B',str(helper),str(p)],check=True)
