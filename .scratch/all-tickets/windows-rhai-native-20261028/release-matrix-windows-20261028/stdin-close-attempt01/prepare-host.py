"""Prepare attempt-specific host tooling; ISO pin is finalized after assembly."""
from pathlib import Path
import hashlib
import json
root=Path(__file__).resolve().parent
old=root.parent/'managed-controls-attempt01'
b=json.loads((root/'binding.json').read_text())
oldnonce='73bbed61f32a48679390d099b4c3a9f5'
nonce=b['nonce']
oldiso='628f5daaad1d6ec668f5632eb093f4ab4b3fe82a1e141eaf8db9baada99b1cbc'
placeholder='0'*64
oldstart='c574625f7c8b385c881d02c313c55e589f1a4d2aa4ac7c2bd36728a45df49e41'
oldcontrol='4c3c7ad0bb0ec0c714ee3aa2671b81577bd2f1300fe23f763c122b8593804409'
oldcontract='34470cc6d296c9e02aba5a5779f7f3dccafc9577ada280ddad4f74b09aca41f5'
oldclear='3a0766ec64f83135d1fd8a6dbae443dea07023c0aec94b6ee3130860de38440f'
files=['assemble-native-media.py','assemble-launch.sh','attach-host.py','cleanup-host.py','capture-serial.py','decode-native-export.py','check-journal.py','console-key-input.py','type-dispatch.py','type-guest-command.py','parser-command.txt','scope-absence-command.txt','guest-retire-command.txt','guest-retirement-confirm-command.txt']
for name in files:
    s=(old/name).read_text()
    s=s.replace(oldnonce,nonce).replace(oldnonce[:8],nonce[:8]).replace(oldiso,placeholder)
    s=s.replace(oldstart,b['start_sha256'])
    if name=='assemble-launch.sh':
        s=s.replace('windows-managed-iso-', 'windows-stdin-close-iso-')
    (root/name).write_text(s)
dispatch=(old/'dispatch-command.txt').read_text().replace(oldstart.upper(),b['start_sha256'].upper())
(root/'dispatch-command.txt').write_text(dispatch)
pre=(old/'host-dispatch-preflight.py').read_text()
pre=pre.replace(oldnonce,nonce).replace(oldnonce[:8],nonce[:8]).replace(oldiso,placeholder)
for before,name in [(oldstart,'Start.ps1'),(oldcontrol,'RunRhaiContractControl.ps1'),(oldcontract,'RunRhaiContract.cmd'),(oldclear,'ClearOwnedWorkReadOnly.ps1')]:
    pre=pre.replace(before,b['media_files'][name]['sha256'])
oldassert='assert binding["source_commit"] == "7019821fc9d7814d0632fea06de50933aa9e35ee" and binding["integrated_head_at_prepare"] == "7dacf2ae09ef657cfbb53d3a0b35b9bb7dc2f4ac" and binding["source_tree_matches_integrated_head"] is True'
assert oldassert in pre
pre=pre.replace(oldassert,'assert binding["base_head"] == "'+b['base_head']+'" and binding["overlay_sha256"] == "'+b['overlay_sha256']+'"')
oldtargets='assert binding["planned_target_count"] == 1 and binding["planned_targets"] == ["sys_process_windows"] and binding["planned_features"] == "testing-environ,sys,net"'
assert oldtargets in pre
pre=pre.replace(oldtargets,'assert binding["target"] == "sys_process_windows" and binding["features"] == "testing-environ,sys,net" and binding["test"] == "windows_spawn_retains_early_stdin_close_error"')
oldcontrols='assert binding["planned_controls"] == ["managed-kill-wrong", "managed-timeout-wrong", "managed-drop-kill-wrong", "managed-drop-retain-wrong"]'
assert oldcontrols in pre
pre=pre.replace(oldcontrols,'assert binding["native_started"] is False')
pre=pre.replace('c39f110b6dd104b4be94f5300f05764c9fd69d86322e0df7353865c0c89652b8',hashlib.sha256(dispatch.encode()).hexdigest())
(root/'host-dispatch-preflight.py').write_text(pre)
print('Host inputs prepared with ISO hash placeholder; finalize after assembly.')
