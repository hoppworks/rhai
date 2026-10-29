"""Type one recorded guest console command without submitting it."""
from pathlib import Path
import subprocess
import sys

stage = Path(sys.argv[1]).resolve()
assert stage.name == 'windows-rhai-native-32483e8898a29b4e86f408e3748ef210'
name = sys.argv[2]
assert name in {'parser-command.txt', 'scope-absence-command.txt', 'guest-sdk-kernel32-query-command.txt', 'guest-linker-hash-command.txt', 'guest-rsp-search-command.txt', 'guest-closure-command.txt', 'guest-retire-command.txt', 'guest-retirement-confirm-command.txt'}
command = (stage / name).read_text().rstrip('\n')
assert command and '\n' not in command
subprocess.run(['python3', '-B', str(stage / 'console-key-input.py'), command], check=True)
