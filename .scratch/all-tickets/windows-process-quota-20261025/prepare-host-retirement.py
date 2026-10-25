"""Read and bind own staging/media before the separate reviewed retirement."""
from pathlib import Path,PurePosixPath
import subprocess,json,hashlib
p=Path(__file__).resolve().parent;read=lambda f:json.loads(f.read_text());sha=lambda f:hashlib.sha256(f.read_bytes()).hexdigest();base=read(p/'binding.json')['host_source_root']
refs=[('initial',p/'media-readback.json',p),('attempt02',p/'attempt02/media-readback.json',p/'attempt02'),('attempt03',p/'attempt03/media-readback.json',p/'attempt03'),('attempt04',p/'attempt04/media-readback.json',p/'attempt04'),('build04',p/'build04-readback/media-readback.json',p/'build04-readback'),('build03',p/'build03-readback/media-readback.json',p/'build03-readback'),('retirement01',p/'retirement/media-readback.json',p/'retirement'),('retirement02',p/'retirement02/media-readback.json',p/'retirement02')]
expected={};optional={};media=[]
for tag,ref,packet in refs:
 m=read(ref);relative=str(PurePosixPath(m['source']).relative_to(base));assert relative!='.'and '..'not in PurePosixPath(relative).parts
 for name,h in m['files'].items():expected[relative+'/'+name]=h
 expected[relative+'/media-readback.json']=sha(ref)
 optional[relative+'/binding.json']=packet/'binding.json'
 inventory=packet/'export-inventory.md'
 if inventory.exists():expected[relative+'/export-inventory.md']=sha(inventory)
 media.append({'tag':tag,'path':m['medium'],'sha256':m['sha256']})
expected['assemble-medium.py']=sha(p.parent/'windows-job-resources-20261025/assemble-medium.py');expected['console-key-input.py']=sha(p.parent/'windows-workhorse-retirement-20261025/console-key-input.py')
code='''from pathlib import Path
import json,hashlib,stat
root=Path(ROOT);assert str(root)=='/var/roothome/projects/rhai-process-quota-20261025-475b06d7'and root.is_dir()and not root.is_symlink()
files={};dirs=[];bindings={};total=0;entries=list(root.rglob('*'));assert len(entries)<=256
for f in entries:
 mode=f.lstat().st_mode;name=f.relative_to(root).as_posix()
 if stat.S_ISDIR(mode):dirs.append(name)
 else:
  assert stat.S_ISREG(mode)and f.stat().st_size<=4194304
  raw=f.read_bytes();total+=len(raw);assert total<=16777216
  files[name]={'sha256':hashlib.sha256(raw).hexdigest(),'bytes':len(raw)}
  if name.endswith('/binding.json'):bindings[name]=json.loads(raw)
print(json.dumps({'root':str(root),'files':files,'directories':sorted(dirs),'bindings':bindings,'bytes':total,'read_only':True}))
'''.replace('ROOT',repr(base))
r=subprocess.run(['ssh','workhorse','python3 -B -'],input=code,capture_output=True,text=True,check=True);snapshot=json.loads(r.stdout)
for name,item in snapshot['files'].items():
 if name in optional:
  remote=snapshot['bindings'][name];local=read(optional[name]);assert remote['nonce']==local['nonce']
  for key in ('files','source_sha256','manifest_sha256'):
   if key in local:assert remote[key]==local[key],(name,key)
  expected[name]=item['sha256']
 assert name in expected and item['sha256']==expected[name],name
assert set(expected)==set(snapshot['files'])
dirs={str(x)for name in expected for x in Path(name).parents if str(x)!='.'};assert dirs==set(snapshot['directories'])
out=p/'media';out.mkdir(exist_ok=True)
for item in media:
 f=out/(item['tag']+'.iso');assert not f.exists();subprocess.run(['scp','-q','workhorse:'+item['path'],str(f)],check=True);assert sha(f)==item['sha256'];item['exported']='media/'+f.name
record={'root':base,'files':{k:x['sha256']for k,x in snapshot['files'].items()},'directories':snapshot['directories'],'file_count':len(expected),'entry_count':len(expected)+len(dirs),'bytes':snapshot['bytes'],'media':media,'all_immutable_inputs_matched':True,'metadata_binding_fields_matched':True,'read_only':True}
(p/'host-staging-before.json').write_text(json.dumps(record,indent=2)+'\n');print('Own staging bound:',len(expected),'files,',len(dirs),'dirs;',len(media),'media exported')
