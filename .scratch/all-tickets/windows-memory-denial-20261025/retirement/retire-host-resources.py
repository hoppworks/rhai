"""Retire exact exported workhorse staging and media after guest cleanup."""
from pathlib import Path
import hashlib
import json
import subprocess

if not __debug__:
    raise RuntimeError("Optimization disables retirement safety assertions.")

p = Path(__file__).resolve().parent
read = lambda name: json.loads((p / name).read_text())
sha = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()
cleanup = read("host-cleanup-readback.json")
receipt = read("guest-cleanup-receipt.json")
manifest = read("cleanup-host-manifest.json")
snapshot = read("host-staging-before.json")
fresh = read("fresh-readback.json")
assert cleanup["accepted"] and receipt["all_scopes_absent"]
assert receipt["retained_verified"] and not receipt["foreign_resources_touched"]
assert sorted(receipt["retired"]) == sorted(scope["scope"] for scope in manifest["scopes"])
assert fresh["observed_line"] == "MEMORY_READBACK False False True"
assert not fresh["control_scope_present"] and not fresh["fixture_build_scope_present"]
assert fresh["retained_default_scope_present"]
assert snapshot["archived_all_files"] and sha(p / snapshot["archive"]) == snapshot["archive_sha256"]
root = "/var/roothome/projects/rhai-memory-denial-20261025-d12c080e901f44e8950847425a81d062"
assert snapshot["root"] == root

image_dir = Path("/var/lib/libvirt/images/rhai-win11-quality")
media = {
    "memory-denial-d12c080e901f44e8950847425a81d062.iso": ("attempt01.iso", "a748d5871ef579f3b46ad1edb66be5717fe6468d9be92147cfebfc7f6caa29f2"),
    "memory-denial-7dbb547163f84466a58fdd0ed80736ae.iso": ("attempt02.iso", "68a2695292e2eafbf347b8143c5fc2489c4681d484104629acda864e5aee6403"),
    "memory-denial-63a597390756484cbc31eb5c9bdeff3d.iso": ("attempt03.iso", "827fd7cf7138df1c7d5a48e7eafcd624d876dbf3617c7f8a6a695017fcafb8f0"),
    "memory-build-readback-01b8323d031c4d37b38935b342ed484a.iso": ("build-readback.iso", "90bf0c16d21c55bfea9362da43182ee9e75bf97d585d0986dbddea9c08bdf1a7"),
    "memory-retirement-197434e7a73dd8d7f20fd2f296895dce.iso": ("retirement.iso", "121a381b94e8abc392cf14ccdf1c5d16bd61bdba01ab095caa731960ef53bb06"),
}
pins = {str(image_dir / name): value[1] for name, value in media.items()}
for local, expected in media.values():
    assert sha(p.parent / "media" / local) == expected

remote = r'''
from pathlib import Path
import hashlib,json,os,shutil,stat,subprocess
if not __debug__:
    raise RuntimeError('Optimization disables retirement safety assertions.')
root=Path(__ROOT__)
expected=__FILES__
expected_dirs=set(__DIRECTORIES__)
pins=__MEDIA__
original='/var/lib/libvirt/images/rhai-win11-quality/acceptance-20261008T125846Z-b7f83433/monitor-fixture02.iso'
sdb='/var/lib/libvirt/images/rhai-win11-quality/work-retirement-bounds-20261009-c18e85827e6f4404.iso'
assert str(root)=='/var/roothome/projects/rhai-memory-denial-20261025-d12c080e901f44e8950847425a81d062'
assert root.is_dir() and not root.is_symlink() and root.resolve()==root
assert subprocess.check_output(['virsh','domuuid','rhai-win11-quality'],text=True).strip()=='dc5b8fd5-1a0b-4d86-8b8f-aaa1bd492b19'
assert len(pins)==5
for name,expected_hash in pins.items():
    file=Path(name)
    assert file.parent==Path('/var/lib/libvirt/images/rhai-win11-quality')
    assert file.resolve(strict=True)==file and stat.S_ISREG(file.lstat().st_mode)
    assert hashlib.sha256(file.read_bytes()).hexdigest()==expected_hash

def blocks(inactive=False):
    found={}
    args=['virsh','domblklist','rhai-win11-quality','--details']+(['--inactive']if inactive else [])
    for line in subprocess.check_output(args,text=True).splitlines():
        fields=line.split(None,3)
        if len(fields)==4 and fields[0] in ('file','block','network'):
            assert fields[2] not in found
            found[fields[2]]=fields[3]
    return found

mounted=blocks()
retirement='/var/lib/libvirt/images/rhai-win11-quality/memory-retirement-197434e7a73dd8d7f20fd2f296895dce.iso'
assert mounted.get('sdb')==sdb and mounted.get('sdc')==retirement
subprocess.run(['virsh','change-media','rhai-win11-quality','sdc',original,'--update','--live'],check=True,stdout=subprocess.DEVNULL)
mounted=blocks()
assert mounted.get('sdb')==sdb and mounted.get('sdc')==original

entries=list(root.rglob('*'))
assert len(entries)<256
files={};directories=set();total=0
for file in entries:
    mode=file.lstat().st_mode
    relative=file.relative_to(root).as_posix()
    if stat.S_ISDIR(mode):directories.add(relative)
    else:
        assert stat.S_ISREG(mode) and file.stat().st_size<=4*1024*1024
        raw=file.read_bytes();total+=len(raw);assert total<=32*1024*1024
        files[relative]=hashlib.sha256(raw).hexdigest()
assert files==expected and directories==expected_dirs

owned_real={os.path.realpath(name) for name in pins}
def uses_owned(value):
    if not value.startswith('/'):return False
    resolved=os.path.realpath(value.removesuffix(' (deleted)'))
    return resolved==str(root) or resolved.startswith(str(root)+'/') or resolved in owned_real

for proc in Path('/proc').iterdir():
    if not proc.name.isdigit() or int(proc.name)==os.getpid():continue
    try:
        command=(proc/'cmdline').read_bytes()
        assert all(marker.encode() not in command for marker in [str(root),*pins]),'Active own argv: '+proc.name
        try:cwd=os.readlink(proc/'cwd')
        except FileNotFoundError:cwd=''
        assert not uses_owned(cwd),'Active own cwd: '+proc.name
        for fd in (proc/'fd').iterdir():
            try:target=os.readlink(fd)
            except FileNotFoundError:continue
            assert not uses_owned(target),'Open own resource: '+proc.name
    except (FileNotFoundError,ProcessLookupError):continue
    except PermissionError:raise RuntimeError('Cannot prove inactivity for process '+proc.name)
inactive=blocks(True)
assert not (set(pins) & set(mounted.values())) and not (set(pins) & set(inactive.values()))
for name,expected_hash in pins.items():
    file=Path(name)
    assert not file.is_symlink() and hashlib.sha256(file.read_bytes()).hexdigest()==expected_hash
for name in pins:Path(name).unlink()
shutil.rmtree(root)
assert not root.exists() and all(not Path(name).exists() for name in pins)
after=blocks()
assert after.get('sdb')==sdb and after.get('sdc')==original
print(json.dumps({'retired_media':pins,'retired_media_count':len(pins),'original_sdc_restored':original,'original_sdb_preserved':True,'host_staging':str(root),'host_staging_files':len(files),'host_staging_directories':len(directories),'host_staging_absent':True,'all_exact_media_absent':True,'foreign_resources_touched':False}))
'''
remote = (
    remote.replace("__ROOT__", repr(root))
    .replace("__FILES__", repr(snapshot["files"]))
    .replace("__DIRECTORIES__", repr(snapshot["directories"]))
    .replace("__MEDIA__", repr(pins))
)
result = subprocess.run(
    ["ssh", "-o", "BatchMode=yes", "workhorse", "python3 -B -"],
    input=remote, capture_output=True, text=True, timeout=120,
)
(p / "host-retirement.stdout").write_text(result.stdout)
(p / "host-retirement.stderr").write_text(result.stderr)
result.check_returncode()
receipt = json.loads(result.stdout.splitlines()[-1])
assert receipt["retired_media_count"] == 5 and receipt["host_staging_absent"]
assert receipt["all_exact_media_absent"] and not receipt["foreign_resources_touched"]
(p / "host-retirement.json").write_text(json.dumps(receipt, indent=2) + "\n")
print(json.dumps(receipt))
