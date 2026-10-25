import hashlib,json,os,shutil,subprocess,sys
from pathlib import Path
src=Path(sys.argv[1]);out=Path(sys.argv[2]);assert not out.exists()
r=Path(os.environ['AGENT_RUNTIME_DIR']);inp=r/'input';shutil.copytree(src/'input',inp)
expected={str(f.relative_to(inp)):hashlib.sha256(f.read_bytes()).hexdigest() for f in inp.rglob('*') if f.is_file()}
iso=r/'membership.iso'
subprocess.run(['genisoimage','-quiet','-J','-R','-V','RHAIMEMBER','-o',str(iso),str(inp)],check=True)
verified={}
for path in subprocess.check_output(['isoinfo','-J','-i',str(iso),'-f'],text=True).splitlines():
 name=path.lstrip('/').split(';')[0]
 if name not in expected:continue
 data=subprocess.check_output(['isoinfo','-J','-i',str(iso),'-x',path]);assert hashlib.sha256(data).hexdigest()==expected[name],name
 verified[name]=expected[name]
assert verified==expected,(set(expected)-set(verified))
shutil.copyfile(iso,out);out.chmod(0o644)
(src/'media-readback.json').write_text(json.dumps({'source':str(src),'medium':str(out),'sha256':hashlib.sha256(out.read_bytes()).hexdigest(),'files':verified,'executed':False},indent=2))
print((src/'media-readback.json').read_text())
