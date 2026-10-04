#!/usr/bin/env python3
"""Create the fixed 60048 collector copy without running collection modes."""
import hashlib
import os
import pathlib

HERE = pathlib.Path(__file__).resolve().parent
BASE = HERE / 'collect-linux-sys-process-example.py'
BASE_SHA256 = 'f2864de1aad1b02a498152dfc0efece8fbc45a1e1eac6c062c8b874a094a7d01'
OUTPUT = pathlib.Path('/private/tmp/rhai-process-example60048-collector.py')

OLD_ROOT = '/root/rhai-linux-sys-process-example-66379d30-20261004'
OLD_PHYSICAL = '/var/roothome/rhai-linux-sys-process-example-66379d30-20261004'
OLD_SCOPE = '/root/.local/share/agent-builds/rhai/linux-sys-process-example-66379d30-20261004'
NEW_ROOT = '/root/rhai-linux-sys-process-example-60048ec4-20261004'
NEW_PHYSICAL = '/var/roothome/rhai-linux-sys-process-example-60048ec4-20261004'
NEW_SCOPE = '/root/.local/share/agent-builds/rhai/linux-sys-process-example-60048ec4-20261004'

# Frozen from the reviewed corrected60048 preflight; importing that script would
# execute SSH, so this local-only configurator owns the exact reviewed map.
INPUTS = {
    'source.tar': 'ce8bcb76a6e839a5ee293f53d70784731bcfbb65b6694aa0e5b1ded2b00661d6',
    'Cargo.lock.accepted': '2ba4b3a0807e32b613ff2e972b893c3fd2e0923fd91803611963f09e93265425',
    'run-examples.py': 'c5422e7895f5afacf987be55df2297b63b0763618ccbdc2a8374116a1421edd9',
    'contract.md': '526a8d5a35910f097fc398fd218e8abae6cf1142c083aaf791bd08f4e9739abf',
    'launch.sh': '1f544fd9c5bdd2594a17eaab9c803ed3b5a889ada66eaace6b0ce0a4d4b12675',
    'stage.sh': '6bdc4dd245e6e3df82318d42fe1c5e409aafc93031acc41373cbbe5ad9fa3bd1',
    'archive-build-source.py': 'a75b4e807f03e8247ed821df871ceb35e776b7f699046d7a099dd0b85199fd8b',
    'runner/tools/run_scoped.py': '9edd5bc53260c697174552498f6064e65ab821d28838af2291a0cbb6e510c36d',
    'runner/tools/agentskills/__init__.py': 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855',
    'runner/tools/agentskills/pyguard.py': 'a3739f4947744303e1adf3fb0875ac743944a272e5b95c94b1baba53029d313f',
}


def replace_once(source: str, old: str, new: str, expected: int = 1) -> str:
    actual = source.count(old)
    if actual != expected:
        raise RuntimeError(f'replacement guard failed ({actual} != {expected}): {old!r}')
    return source.replace(old, new)


def build() -> bytes:
    raw = BASE.read_bytes()
    if hashlib.sha256(raw).hexdigest() != BASE_SHA256:
        raise RuntimeError('frozen collector input hash mismatch')
    source = raw.decode('utf-8')
    source = replace_once(source, f"STAGE='{OLD_ROOT}'", f"STAGE='{NEW_ROOT}'")
    source = replace_once(source, f"PHYSICAL='{OLD_PHYSICAL}'", f"PHYSICAL='{NEW_PHYSICAL}'")
    source = replace_once(source, f"SCOPE='{OLD_SCOPE}'", f"SCOPE='{NEW_SCOPE}'")

    start = source.index('INPUTS={')
    end_marker = '}\nINPUT_ORDER=tuple(INPUTS)'
    end = source.index(end_marker, start) + 1
    old_block = source[start:end]
    new_block = 'INPUTS={\n' + ''.join(f" '{name}':'{digest}',\n" for name, digest in INPUTS.items()) + '}'
    source = replace_once(source, old_block, new_block)

    # Each provenance table contains the root and physical root once.
    source = replace_once(source, OLD_ROOT, NEW_ROOT, expected=2)
    source = replace_once(source, OLD_PHYSICAL, NEW_PHYSICAL, expected=2)
    if OLD_SCOPE in source or OLD_ROOT in source or OLD_PHYSICAL in source:
        raise RuntimeError('old stage identity remains in configured executable')
    if "'source.tar':'0ab9ec63" in source:
        raise RuntimeError('old archive pin remains in configured executable')
    return source.encode('utf-8')


def main() -> None:
    payload = build()
    if OUTPUT.exists() or OUTPUT.is_symlink():
        if OUTPUT.is_symlink() or not OUTPUT.is_file() or OUTPUT.read_bytes() != payload:
            raise FileExistsError(f'refusing to replace existing output: {OUTPUT}')
        print(f'existing configured output matches: {OUTPUT}')
        return
    temporary = OUTPUT.with_name(OUTPUT.name + '.tmp')
    if temporary.exists() or temporary.is_symlink():
        raise FileExistsError(f'refusing to replace temporary output: {temporary}')
    temporary.write_bytes(payload)
    os.replace(temporary, OUTPUT)
    print(f'configured collector written: {OUTPUT}')


if __name__ == '__main__':
    main()
