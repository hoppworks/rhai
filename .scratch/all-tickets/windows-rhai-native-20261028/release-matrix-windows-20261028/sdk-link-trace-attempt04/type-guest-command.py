"""Type one recorded guest console command without submitting it."""
from pathlib import Path
import subprocess
import sys

stage = Path(sys.argv[1]).resolve()
assert stage.name == 'windows-rhai-native-e1534746c0394e61a2defda7c3a79c08'
name = sys.argv[2]
assert name in {'parser-command.txt', 'scope-absence-command.txt', 'guest-sdk-kernel32-query-command.txt', 'guest-linker-hash-command.txt', 'guest-rsp-search-command.txt', 'guest-closure-command.txt', 'guest-retire-command.txt', 'guest-retirement-confirm-command.txt'}
command = (stage / name).read_text().rstrip('\n')
assert command and '\n' not in command
subprocess.run(['python3', '-B', str(stage / 'console-key-input.py'), command], check=True)
