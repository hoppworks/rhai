"""Type one recorded guest console command without submitting it."""
from pathlib import Path
import subprocess
import sys

stage = Path(sys.argv[1]).resolve()
assert stage.name == 'windows-rhai-native-c61eb47971c24dee985173da67278b42'
name = sys.argv[2]
assert name in {'parser-command.txt', 'scope-absence-command.txt', 'guest-closure-command.txt', 'guest-retire-command.txt', 'guest-retirement-confirm-command.txt', 'diagnostic-command.txt'}
command = (stage / name).read_text().rstrip('\n')
assert command and '\n' not in command
subprocess.run(['python3', '-B', str(stage / 'console-key-input.py'), command], check=True)
