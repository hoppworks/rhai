"""Restore exact live media and retire only this native attempt's owned host files."""
from pathlib import Path
import hashlib
import json
import os
import shutil
import subprocess

nonce = '7e51e9f298df4665810426dcaaa288d9'
stage = Path('/var/roothome/.local/share/agent-builds/rhai/windows-rhai-native-' + nonce)
medium = Path('/var/lib/libvirt/images/rhai-win11-quality/rhai-native-' + nonce + '.iso')
original = Path('/var/lib/libvirt/images/rhai-win11-quality/acceptance-20261008T125846Z-b7f83433/monitor-fixture02.iso')
foreign = Path('/var/lib/libvirt/images/rhai-win11-quality/work-retirement-bounds-20261009-c18e85827e6f4404.iso')
assert stage.is_dir() and not stage.is_symlink() and medium.is_file() and not medium.is_symlink()
assert subprocess.check_output(['virsh', 'domuuid', 'rhai-win11-quality'], text=True).strip() == 'dc5b8fd5-1a0b-4d86-8b8f-aaa1bd492b19'
assert hashlib.sha256(medium.read_bytes()).hexdigest() == '239325edf5de193323faf43ec2d140c82a60395fcc72b51a8eb630a7fcfcf8b7'
assert medium.stat().st_nlink == 1
assert hashlib.sha256((stage / 'rhai-native.iso').read_bytes()).hexdigest() == '239325edf5de193323faf43ec2d140c82a60395fcc72b51a8eb630a7fcfcf8b7'
def devices(inactive=False):
    cmd = ['virsh', 'domblklist', 'rhai-win11-quality', '--details']
    if inactive: cmd.append('--inactive')
    return subprocess.check_output(cmd, text=True)
def attached(rows, dev, path):
    return any(line.split()[-2:] == [dev, str(path)] for line in rows.splitlines() if len(line.split()) >= 4)
live = devices()
inactive = devices(True)
assert attached(live, 'sdc', medium) and attached(live, 'sdb', foreign)
assert attached(inactive, 'sdc', original) and attached(inactive, 'sdb', foreign)
assert (stage / 'serial-original.bin').is_file() and (stage / 'serial-capture-binding.json').is_file()
assert (stage / 'host-dispatch-preflight-final.json').is_file()
for p in stage.rglob('*'):
    assert not p.is_symlink(), 'owned stage contains redirected entry: ' + str(p)
count = sum(p.is_file() for p in stage.rglob('*'))
subprocess.run(['virsh', 'change-media', 'rhai-win11-quality', 'sdc', str(original), '--update', '--live'], check=True, capture_output=True, text=True)
live = devices(); inactive = devices(True)
assert attached(live, 'sdc', original) and attached(inactive, 'sdc', original)
assert attached(live, 'sdb', foreign) and attached(inactive, 'sdb', foreign)
assert not attached(live, 'sdc', medium) and not attached(inactive, 'sdc', medium)
fuser = subprocess.run(['fuser', str(medium)], capture_output=True, text=True)
assert fuser.returncode == 1 and not fuser.stdout.strip(), (fuser.returncode, fuser.stdout, fuser.stderr)
assert medium.stat().st_nlink == 1
medium.unlink()
shutil.rmtree(stage)
assert not stage.exists() and not medium.exists()
print(json.dumps({'owned_host_stage':str(stage), 'owned_iso':str(medium), 'iso_sha256':'239325edf5de193323faf43ec2d140c82a60395fcc72b51a8eb630a7fcfcf8b7', 'stage_file_count':count, 'stage_absent':True, 'iso_absent':True, 'original_sdc_restored':True, 'foreign_sdb_unchanged':True, 'live_and_inactive_vm_checked':True, 'exact_fuser_no_holder':True},indent=2))
