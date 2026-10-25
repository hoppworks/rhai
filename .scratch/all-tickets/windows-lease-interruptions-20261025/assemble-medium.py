import hashlib,json,os,shutil,subprocess,sys
from pathlib import Path
src=Path(sys.argv[1]);out=Path(sys.argv[2]);assert not out.exists()
r=Path(os.environ['AGENT_RUNTIME_DIR']);inp=r/'input';inp.mkdir()
for name in ('Start.ps1','bindings.json','disconnect-alive.ps1','client-death.ps1','replay.ps1','cleanup.ps1'):shutil.copyfile(src/name,inp/name)
iso=r/'recovery.iso'
subprocess.run(['genisoimage','-quiet','-J','-R','-V','RHAILEASE','-o',str(iso),str(inp)],check=True)
paths=subprocess.check_output(['isoinfo','-J','-i',str(iso),'-f'],text=True).splitlines();assert len(paths)==6,paths
verified={}
for path in paths:
 name=Path(path).name.split(';')[0];assert name in ('Start.ps1','bindings.json','disconnect-alive.ps1','client-death.ps1','replay.ps1','cleanup.ps1')
 data=subprocess.check_output(['isoinfo','-J','-i',str(iso),'-x',path]);assert data==(inp/name).read_bytes()
 verified[name]=hashlib.sha256(data).hexdigest()
shutil.copyfile(iso,out);out.chmod(0o644)
(src/'media-readback.json').write_text(json.dumps({'source':str(src),'output_medium':str(out),'iso_sha256':hashlib.sha256(out.read_bytes()).hexdigest(),'files':verified,'execution':'not yet','lifetime':'exact own immutable source medium; detach/remove after two proof steps; no compiler cache retained'},indent=2))
print((src/'media-readback.json').read_text())
