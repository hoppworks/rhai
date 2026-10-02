import subprocess, sys, time

LOWER = {c: [f'KEY_{c.upper()}'] for c in 'abcdefghijklmnopqrstuvwxyz'}
DIGITS = {c: [f'KEY_{c}'] for c in '0123456789'}
KEYS = {**LOWER, **DIGITS, ' ': ['KEY_SPACE'], '\\': ['KEY_BACKSLASH'], '-': ['KEY_MINUS'], ':': ['KEY_LEFTSHIFT', 'KEY_SEMICOLON'], '.': ['KEY_DOT'], '/': ['KEY_SLASH'], ';': ['KEY_SEMICOLON'], '|': ['KEY_LEFTSHIFT', 'KEY_BACKSLASH'], '(': ['KEY_LEFTSHIFT', 'KEY_9'], ')': ['KEY_LEFTSHIFT', 'KEY_0'], '[': ['KEY_LEFTBRACE'], ']': ['KEY_RIGHTBRACE'], '{': ['KEY_LEFTSHIFT', 'KEY_LEFTBRACE'], '}': ['KEY_LEFTSHIFT', 'KEY_RIGHTBRACE'], '$': ['KEY_LEFTSHIFT', 'KEY_4'], '_': ['KEY_LEFTSHIFT', 'KEY_MINUS'], '>': ['KEY_LEFTSHIFT', 'KEY_DOT'], '=': ['KEY_EQUAL'], "'": ['KEY_APOSTROPHE'], '+': ['KEY_LEFTSHIFT', 'KEY_EQUAL'], ',': ['KEY_COMMA']}
from pathlib import Path
for letter in 'ABCDEFGHIJKLMNOPQRSTUVWXYZ':
    KEYS[letter] = ['KEY_LEFTSHIFT', 'KEY_' + letter]
command = Path(sys.argv[1]).read_text()
missing = sorted(set(command) - KEYS.keys())
if missing:
    raise SystemExit(f'unsupported input characters: {missing!r}')
print(f'validated_chars={len(command)} key_events={len(command)}')
print(command)
if len(sys.argv) > 2 and sys.argv[2] == '--send':
    for index, char in enumerate(command, 1):
        cmd = ['ssh', '-o', 'BatchMode=yes', 'workhorse', 'virsh', '-c', 'qemu:///system', 'send-key', 'rhai-win11-quality', '--codeset', 'linux', '--holdtime', '80', *KEYS[char]]
        result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        if result.returncode:
            raise SystemExit(f'key {index}/{len(command)} failed for {char!r}: {result.stderr.strip()}')
        time.sleep(0.45)
    print(f'sent_chars={len(command)}')
