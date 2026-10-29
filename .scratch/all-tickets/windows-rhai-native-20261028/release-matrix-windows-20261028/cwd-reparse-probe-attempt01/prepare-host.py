"""Adapt the previously verified host custody and console route."""
import hashlib
import json
from pathlib import Path

root = Path(__file__).resolve().parent
old = root.parent / 'streams-4m-attempt02'
new = json.loads((root / 'binding.json').read_text())
prior = json.loads((old / 'binding.json').read_text())
placeholder = '0' * 64
names = ['assemble-native-media.py', 'assemble-launch.sh', 'attach-host.py', 'cleanup-host.py',
         'capture-serial.py', 'capture-serial-rotation.py', 'decode-native-export.py', 'check-journal.py',
         'console-key-input.py', 'type-dispatch.py', 'type-guest-command.py', 'parser-command.txt',
         'scope-absence-command.txt', 'guest-retire-command.txt', 'guest-retirement-confirm-command.txt']
for name in names:
    content = (old / name).read_text().replace(prior['nonce'], new['nonce']).replace(prior['nonce'][:8], new['nonce'][:8]).replace(prior['iso_sha256'], placeholder).replace(prior['start_sha256'], new['start_sha256'])
    if name == 'assemble-launch.sh': content = content.replace('windows-streams-iso-', 'windows-reparse-iso-')
    (root / name).write_text(content)
dispatch = (old / 'dispatch-command.txt').read_text().replace(prior['start_sha256'].upper(), new['start_sha256'].upper())
(root / 'dispatch-command.txt').write_text(dispatch)
preflight = (old / 'host-dispatch-preflight.py').read_text().replace(prior['nonce'], new['nonce']).replace(prior['nonce'][:8], new['nonce'][:8]).replace(prior['iso_sha256'], placeholder)
for name in ('Start.ps1', 'RunRhaiContractControl.ps1', 'RunRhaiContract.cmd', 'ClearOwnedWorkReadOnly.ps1'):
    preflight = preflight.replace(prior['media_files'][name]['sha256'], new['media_files'][name]['sha256'])
for key in ('base_head', 'overlay_sha256', 'test', 'target', 'features'):
    assert prior[key] in preflight, key
    preflight = preflight.replace(prior[key], new[key])
prior_dispatch = hashlib.sha256((old / 'dispatch-command.txt').read_bytes()).hexdigest()
preflight = preflight.replace(prior_dispatch, hashlib.sha256(dispatch.encode()).hexdigest())
(root / 'host-dispatch-preflight.py').write_text(preflight)
print('Prepared bounded native custody route; bind the actual ISO hash after assembly.')
