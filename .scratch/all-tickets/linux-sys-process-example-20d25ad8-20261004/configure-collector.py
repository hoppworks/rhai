#!/usr/bin/env python3
"""Create the fixed 20d25ad8 collector copy without running collection modes."""
import hashlib
import os
import pathlib

HERE = pathlib.Path(__file__).resolve().parent
BASE = HERE / 'collector-source-ea7.py'
BASE_SHA256 = 'f2864de1aad1b02a498152dfc0efece8fbc45a1e1eac6c062c8b874a094a7d01'
OUTPUT = pathlib.Path(__file__).with_name('collect-originals-20d25ad8.py')

OLD_ROOT = '/root/rhai-linux-sys-process-example-66379d30-20261004'
OLD_PHYSICAL = '/var/roothome/rhai-linux-sys-process-example-66379d30-20261004'
OLD_SCOPE = '/root/.local/share/agent-builds/rhai/linux-sys-process-example-66379d30-20261004'
NEW_ROOT = '/root/rhai-linux-sys-process-example-20d25ad8-20261004'
NEW_PHYSICAL = '/var/roothome/rhai-linux-sys-process-example-20d25ad8-20261004'
NEW_SCOPE = '/root/.local/share/agent-builds/rhai/linux-sys-process-example-20d25ad8-20261004'

# Frozen from the reviewed default one-heavy preflight for this frozen source; importing that script would
# execute SSH, so this local-only configurator owns the exact reviewed map.
INPUTS = {
    'source.tar': 'e7a9a118bd29c05e8a70e284196837594fc97811f3d80688d17f55167008be93',
    'Cargo.lock.accepted': '2ba4b3a0807e32b613ff2e972b893c3fd2e0923fd91803611963f09e93265425',
    'run-examples.py': 'e89c91496d8543c418149573c3b0f7a6fe41e04a02adf470cdb4811cf43fff4e',
    'contract.md': '8279084c6a1c8c85105fdc565810ecfe22233db4c17f2a84005564dc5a528b71',
    'launch.sh': '896d7aec52f3da44b01f1d692078c24d5ee4d869a4eb6510c7069a2458c1f045',
    'stage.sh': '321ea96b3f6ccc30cfeb2fc4dbee52d68061dfac0cef58ec17e94905fe43c0a3',
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
