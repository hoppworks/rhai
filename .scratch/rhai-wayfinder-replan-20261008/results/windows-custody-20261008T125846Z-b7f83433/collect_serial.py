"""Offline readback of the existing bounded guest export; never launches guests."""
import base64, hashlib, json, sys
from pathlib import Path

p=Path(__file__).resolve().parent; tag=sys.argv[1]; nonce=sys.argv[2]
out=p/(tag+'-export'); out.mkdir(exist_ok=False)
frames=[]
for line in (p/(tag+'-serial-original.txt')).read_text().splitlines():
    if line.startswith('RHAI_BOOTSTRAP '+nonce+' '):
        _, identity, sequence, kind, encoded=line.split(' ',4)
        assert identity==nonce and len(encoded)<=3500
        frames.append((int(sequence),kind,json.loads(base64.b64decode(encoded,validate=True))))
assert frames and frames[0][1]=='BEGIN' and frames[-1][1]=='END'
assert [f[0] for f in frames]==list(range(len(frames)))
assert frames[0][2]['id']==nonce and frames[-1][2]['id']==nonce
assert frames[0][2]['exit']==frames[-1][2]['exit'] and frames[0][2]['accepted']==frames[-1][2]['accepted']
files={}; current=None; data=bytearray()
for _,kind,item in frames[1:-1]:
    if kind=='FILE':
        assert current is None; current=item; data=bytearray(); name=Path(item['path'])
        assert not name.is_absolute() and '..' not in name.parts and '\\' not in item['path'] and ':' not in item['path']
        assert item['path'] not in files and 0<=item['length']<=4*1024**2
    elif kind=='CHUNK':
        assert current and item['path']==current['path'] and item['offset']==len(data)
        chunk=base64.b64decode(item['data'],validate=True); assert 0<len(chunk)<=1024
        data.extend(chunk); assert len(data)<=current['length']
    elif kind=='FILE_END':
        assert item==current and len(data)==item['length'] and hashlib.sha256(data).hexdigest()==item['sha256']
        f=out/item['path']; f.parent.mkdir(parents=True,exist_ok=True); f.write_bytes(data)
        files[item['path']]=item; current=None
    else: raise AssertionError(kind)
assert current is None and len(files)==frames[-1][2]['files'] and len(files)<=64
assert sum(f['length'] for f in files.values())<=16*1024**2
record={'frames':len(frames),'files':files,'complete':True,'begin':frames[0][2],'end':frames[-1][2]}
(p/(tag+'-export-readback.json')).write_text(json.dumps(record,indent=2)+'\n')
print(json.dumps(record['end']))
for name in ('bootstrap.stdout','bootstrap.stderr'): print(name+':\n'+(out/name).read_text())
