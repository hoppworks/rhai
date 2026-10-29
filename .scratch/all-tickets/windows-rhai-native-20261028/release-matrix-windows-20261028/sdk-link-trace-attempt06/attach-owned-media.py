"""Attach exactly this attempt's immutable ISO to the existing live sdc."""
import hashlib
import json
import os
from pathlib import Path
import subprocess

nonce = '9dd1f408c6904bbe87d8cb18510b9029'
stage = Path('/var/roothome/.local/share/agent-builds/rhai/windows-rhai-native-' + nonce)
source = stage / 'rhai-native.iso'
target = Path('/var/lib/libvirt/images/rhai-win11-quality/rhai-native-' + nonce + '.iso')
original = Path('/var/lib/libvirt/images/rhai-win11-quality/acceptance-20261008T125846Z-b7f83433/monitor-fixture02.iso')
foreign = Path('/var/lib/libvirt/images/rhai-win11-quality/work-retirement-bounds-20261009-c18e85827e6f4404.iso')
pin = '644286a85b99ee2e3baf1a784688c2ef54be982abe23d298c1ffad8bbb0383e9'
assert stage.is_dir() and not stage.is_symlink() and source.is_file() and not source.is_symlink()
assert not target.exists() and not target.is_symlink()
assert hashlib.sha256(source.read_bytes()).hexdigest() == pin
assert subprocess.check_output(['virsh', 'domuuid', 'rhai-win11-quality'], text=True).strip() == 'dc5b8fd5-1a0b-4d86-8b8f-aaa1bd492b19'
def devices(inactive=False):
    cmd = ['virsh', 'domblklist', 'rhai-win11-quality', '--details']
    if inactive: cmd.append('--inactive')
    return subprocess.check_output(cmd, text=True)
def attached(rows, device, path):
    return any(line.split()[-2:] == [device, str(path)] for line in rows.splitlines() if len(line.split()) >= 4)
assert attached(devices(), 'sdc', original) and attached(devices(True), 'sdc', original)
assert attached(devices(), 'sdb', foreign) and attached(devices(True), 'sdb', foreign)
fd = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o644)
try:
    with os.fdopen(fd, 'wb') as out, source.open('rb') as inp:
        while chunk := inp.read(1024 * 1024): out.write(chunk)
except BaseException:
    target.unlink(missing_ok=True)
    raise
assert hashlib.sha256(target.read_bytes()).hexdigest() == pin
subprocess.run(['virsh', 'change-media', 'rhai-win11-quality', 'sdc', str(target), '--update', '--live'], check=True, capture_output=True, text=True)
assert attached(devices(), 'sdc', target) and attached(devices(True), 'sdc', original)
assert attached(devices(), 'sdb', foreign) and attached(devices(True), 'sdb', foreign)
print(json.dumps({'vm_uuid': 'dc5b8fd5-1a0b-4d86-8b8f-aaa1bd492b19', 'attached_live_sdc': str(target), 'sha256': pin, 'inactive_sdc_original': True, 'foreign_sdb_unchanged': True}, indent=2))
