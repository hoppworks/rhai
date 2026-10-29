"""Prepare attempt-specific host tools from the last verified route."""
from pathlib import Path
import hashlib,json
root=Path(__file__).resolve().parent; old=root.parent/'managed-overflow-attempt01'
b=json.loads((root/'binding.json').read_text()); ob=json.loads((old/'binding.json').read_text())
oldn=ob['nonce'];n=b['nonce'];placeholder='0'*64
files=['assemble-native-media.py','assemble-launch.sh','attach-host.py','cleanup-host.py','capture-serial.py','decode-native-export.py','check-journal.py','console-key-input.py','type-dispatch.py','type-guest-command.py','parser-command.txt','scope-absence-command.txt','guest-retire-command.txt','guest-retirement-confirm-command.txt']
for name in files:
 s=(old/name).read_text().replace(oldn,n).replace(oldn[:8],n[:8]).replace(ob['iso_sha256'],placeholder).replace(ob['start_sha256'],b['start_sha256'])
 if name=='assemble-launch.sh':s=s.replace('windows-managed-overflow-iso-','windows-noindex-scalar-iso-')
 (root/name).write_text(s)
dispatch=(old/'dispatch-command.txt').read_text().replace(ob['start_sha256'].upper(),b['start_sha256'].upper())
(root/'dispatch-command.txt').write_text(dispatch)
pre=(old/'host-dispatch-preflight.py').read_text().replace(oldn,n).replace(oldn[:8],n[:8]).replace(ob['iso_sha256'],placeholder)
for name in ('Start.ps1','RunRhaiContractControl.ps1','RunRhaiContract.cmd','ClearOwnedWorkReadOnly.ps1'):
 pre=pre.replace(ob['media_files'][name]['sha256'],b['media_files'][name]['sha256'])
for a,c in [(ob['base_head'],b['base_head']),(ob['overlay_sha256'],b['overlay_sha256']),(ob['test'],b['test']),(ob['target'],b['target']),(ob['features'],b['features'])]:
 assert a in pre;pre=pre.replace(a,c)
pre=pre.replace(hashlib.sha256((old/'dispatch-command.txt').read_bytes()).hexdigest(),hashlib.sha256(dispatch.encode()).hexdigest())
(root/'host-dispatch-preflight.py').write_text(pre)
print('Host tools prepared; ISO pin will be filled after verified assembly.')
