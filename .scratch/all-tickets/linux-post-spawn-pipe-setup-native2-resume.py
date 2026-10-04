"""Resume custody and exact retirement of the sole preserved native2 export."""
import hashlib, importlib.util, json, pathlib, subprocess
ROOT = pathlib.Path(__file__).resolve().parent
DEST = ROOT / 'linux-post-spawn-pipe-setup-native2-originals'
ARCHIVE = ROOT / 'linux-post-spawn-pipe-setup-native2-originals.originals.tar'
assert hashlib.sha256(ARCHIVE.read_bytes()).hexdigest() == '3083b009dcfdbcb83f9d9acec60db250328de5d37fe73e9b5247f01624a2cca4'
manifest = json.loads((DEST / 'export-manifest.json').read_text())
readback = json.loads((DEST / 'independent-readback.json').read_text())
assert manifest['archive_sha256'] == hashlib.sha256(ARCHIVE.read_bytes()).hexdigest()
files, dirs = {}, []
for p in sorted((DEST / 'stage-originals').rglob('*')):
    name = p.relative_to(DEST / 'stage-originals').as_posix()
    assert not p.is_symlink()
    if p.is_dir(): dirs.append(name)
    elif p.is_file(): files[name] = hashlib.sha256(p.read_bytes()).hexdigest()
    else: raise AssertionError('unexpected original object')
assert files == readback['files'] == manifest['files']
assert dirs == readback['directories'] == manifest['directories']
spec = importlib.util.spec_from_file_location('collector', ROOT / 'linux-post-spawn-pipe-setup-523-evidence/collect-originals.py')
collector = importlib.util.module_from_spec(spec); spec.loader.exec_module(collector)
def save(name, data):
    with (DEST / name).open('x') as f: json.dump(data, f, indent=2, sort_keys=True)
assert collector.inventory() == readback
custody = collector.ssh_json(collector.CUSTODY, readback)
save('fresh-custody-readback.json', custody)
assert collector.inventory() == readback
retirement = collector.ssh_json(collector.RETIRE, readback)
save('retirement-readback.json', retirement)
print(json.dumps({'custody': custody, 'retirement': retirement}, indent=2))
