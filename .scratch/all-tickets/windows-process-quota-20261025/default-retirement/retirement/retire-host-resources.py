"""Restore original VM media and retire exact exported workhorse resources."""
from pathlib import Path
import hashlib
import json
import subprocess

if not __debug__:
    raise RuntimeError("Optimization disables retirement safety assertions.")

p = Path(__file__).resolve().parent
load = lambda name: json.loads((p / name).read_text())
sha = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()
cleanup = load("host-cleanup-readback.json")
receipt = load("guest-cleanup-receipt.json")
snapshot = load("host-staging-before.json")
assert cleanup["accepted"] and cleanup["original_build_actor_absent"]
assert receipt["all_scopes_absent"] and receipt["original_build_retired"]
assert not receipt["foreign_resources_touched"]
assert len(receipt["retired"]) == 1
assert snapshot["archived_all_files"] and sha(p / snapshot["archive"]) == snapshot["archive_sha256"]
root = "/var/roothome/projects/rhai-default-build-retirement-20261025-278b19c6e05ac1725763aa778e031945"
assert snapshot["root"] == root and len(snapshot["files"]) == 13
media = {
    "/var/lib/libvirt/images/rhai-win11-quality/default-build-readback-278b19c6e05ac1725763aa778e031945.iso": (p.parent / "readback.iso", "6377ba8c22fb279be0bdf528c80410ef89f21eb8a59cfd62e1d6f7dd14ab95e1"),
    "/var/lib/libvirt/images/rhai-win11-quality/default-build-retirement-278b19c6e05ac1725763aa778e031945.iso": (p / "retirement.iso", "66cde43eae36095b1b02d053ab346f39a41b563201a50eb044584d4e1beadeac"),
}
for local, expected in media.values():
    assert sha(local) == expected
pins = {name: expected for name, (_, expected) in media.items()}

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
assert str(root)=='/var/roothome/projects/rhai-default-build-retirement-20261025-278b19c6e05ac1725763aa778e031945'
assert root.is_dir() and not root.is_symlink() and root.resolve()==root
assert subprocess.check_output(['virsh','domuuid','rhai-win11-quality'],text=True).strip()=='dc5b8fd5-1a0b-4d86-8b8f-aaa1bd492b19'
assert len(pins)==2
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
retirement='/var/lib/libvirt/images/rhai-win11-quality/default-build-retirement-278b19c6e05ac1725763aa778e031945.iso'
assert mounted.get('sdb')==sdb and mounted.get('sdc')==retirement
subprocess.run(['virsh','change-media','rhai-win11-quality','sdc',original,'--update','--live'],check=True,stdout=subprocess.DEVNULL)
mounted=blocks()
assert mounted.get('sdb')==sdb and mounted.get('sdc')==original

entries=list(root.rglob('*'))
assert len(entries)<32
files={};directories=set();total=0
for file in entries:
    mode=file.lstat().st_mode
    relative=file.relative_to(root).as_posix()
    if stat.S_ISDIR(mode):directories.add(relative)
    else:
        assert stat.S_ISREG(mode) and file.stat().st_size<=4*1024*1024
        raw=file.read_bytes();total+=len(raw);assert total<=8*1024*1024
        files[relative]={'size':len(raw),'sha256':hashlib.sha256(raw).hexdigest()}
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
remote = (remote.replace("__ROOT__", repr(root))
          .replace("__FILES__", repr(snapshot["files"]))
          .replace("__DIRECTORIES__", repr(snapshot["directories"]))
          .replace("__MEDIA__", repr(pins)))
result = subprocess.run(
    ["ssh", "-o", "BatchMode=yes", "workhorse", "python3 -B -"],
    input=remote, capture_output=True, text=True, timeout=120,
)
(p / "host-retirement.stdout").write_text(result.stdout)
(p / "host-retirement.stderr").write_text(result.stderr)
result.check_returncode()
retired = json.loads(result.stdout.splitlines()[-1])
assert retired["retired_media_count"] == 2 and retired["host_staging_absent"]
assert retired["all_exact_media_absent"] and not retired["foreign_resources_touched"]
(p / "host-retirement.json").write_text(json.dumps(retired, indent=2) + "\n")
print(json.dumps(retired))
