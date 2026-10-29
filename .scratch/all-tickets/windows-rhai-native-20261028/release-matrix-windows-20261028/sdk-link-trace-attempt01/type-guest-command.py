"""Type one recorded guest console command without submitting it."""
from pathlib import Path
import subprocess
import sys

stage = Path(sys.argv[1]).resolve()
assert stage.name == 'windows-rhai-native-7e51e9f298df4665810426dcaaa288d9'
name = sys.argv[2]
assert name in {'parser-command.txt', 'scope-absence-command.txt', 'guest-linker-hash-command.txt', 'guest-closure-command.txt', 'guest-retire-command.txt', 'guest-retirement-confirm-command.txt'}
command = (stage / name).read_text().rstrip('\n')
assert command and '\n' not in command
subprocess.run(['python3', '-B', str(stage / 'console-key-input.py'), command], check=True)
