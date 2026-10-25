from pathlib import Path
import hashlib,json,os,subprocess,shutil,sys
src=Path(sys.argv[1]);out=Path(sys.argv[2]);assert not out.exists()
r=Path(os.environ['AGENT_RUNTIME_DIR']);tree=r/'input';tree.mkdir()
if len(sys.argv)==4 and sys.argv[3]=='cleanup':
 for name in ('cleanup.ps1','cleanup-host-manifest.json'):shutil.copyfile(src/name,tree/name)
else:
 shutil.copytree(src/'input',tree/'input')
 for f in [src/'Start.ps1',src/'input-manifest.json',*src.glob('*.bundle')]:shutil.copyfile(f,tree/f.name)
expected={str(f.relative_to(tree)):hashlib.sha256(f.read_bytes()).hexdigest()for f in tree.rglob('*')if f.is_file()}
iso=r/'job-resources.iso';subprocess.run(['genisoimage','-quiet','-J','-R','-V','RHAIJOBRES','-o',str(iso),str(tree)],check=True)
verified={}
for path in subprocess.check_output(['isoinfo','-J','-i',str(iso),'-f'],text=True).splitlines():
 name=path.lstrip('/').split(';')[0]
 if name not in expected:continue
 actual=subprocess.check_output(['isoinfo','-J','-i',str(iso),'-x',path]);assert hashlib.sha256(actual).hexdigest()==expected[name],name;verified[name]=expected[name]
assert verified==expected
shutil.copyfile(iso,out);out.chmod(0o644)
(src/'media-readback.json').write_text(json.dumps({'source':str(src),'medium':str(out),'sha256':hashlib.sha256(out.read_bytes()).hexdigest(),'files':verified,'native_started':False},indent=2)+'\n')
print('All',len(verified),'source-medium files read back')
