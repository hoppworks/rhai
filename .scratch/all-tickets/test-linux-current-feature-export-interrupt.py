"""Pure regression for preserving partial evidence after an interrupt."""
from __future__ import annotations

import os
from pathlib import Path
import runpy
import tempfile

HELPER = Path(__file__).with_name('check-linux-current-feature-compilation.py')


def main() -> None:
    names = ('PROOF_STAGE', 'AGENT_RUNTIME_DIR', 'TMPDIR', 'INTERRUPT_REQUEST')
    previous = {name: os.environ.get(name) for name in names}
    with tempfile.TemporaryDirectory(prefix='feature-compile-interrupt-test-') as temp_dir:
        request = Path(temp_dir) / 'interrupt.request'
        os.environ.update({
            'PROOF_STAGE': '/root/rhai-linux-current-features-msrv-1ca21e32-20261002',
            'AGENT_RUNTIME_DIR': '/private/runtime',
            'TMPDIR': '/private/runtime/tmp',
            'INTERRUPT_REQUEST': str(request),
        })
        try:
            namespace = runpy.run_path(str(HELPER))
        finally:
            for name, value in previous.items():
                if value is None:
                    os.environ.pop(name, None)
                else:
                    os.environ[name] = value

        check_deadline = namespace['check_deadline']
        module_globals = check_deadline.__globals__
        module_globals['DEADLINE'] = module_globals['START'] + 540
        module_globals['WORK_DEADLINE'] = module_globals['START'] + 510
        request.touch()
        try:
            check_deadline()
        except InterruptedError:
            print('interrupted_compile_stopped=pass')
        else:
            raise AssertionError('interrupt request allowed compile work to continue')
        check_deadline(during_export=True)
        print('interrupted_partial_evidence_export_allowed=pass')
        module_globals['DEADLINE'] = module_globals['START'] - 1
        try:
            check_deadline(during_export=True)
        except TimeoutError:
            print('expired_partial_evidence_export_rejected=pass')
        else:
            raise AssertionError('expired helper deadline allowed evidence export')


if __name__ == '__main__':
    main()
