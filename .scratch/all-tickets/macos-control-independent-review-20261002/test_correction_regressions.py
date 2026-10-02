"""Non-native regressions for the immutable finite-control source."""
import importlib.util
import os
from pathlib import Path
import signal
import sys
import tempfile
import unittest
from unittest.mock import patch

SOURCE = Path(__file__).with_name('correction-source') / '.scratch/all-tickets/run-macos-process-overhead-control-package.py'
spec = importlib.util.spec_from_file_location('review_control_package', SOURCE)
package = importlib.util.module_from_spec(spec)
spec.loader.exec_module(package)


class SourceRegressions(unittest.TestCase):
    def test_managed_not_ready_probe_emits_no_controller_frame(self):
        adapter = package.control_client.adapter
        class Child:
            pid = 12345
            returncode = 0
        class Controller:
            def __init__(self): self.frames = []
            def sendall(self, frame): self.frames.append(frame)
        controller = Controller()
        gate, anchor = Child(), Child()
        record = {}
        setup = (gate, anchor, {}, {}, set(), {'issued': True}, record)
        with patch.object(adapter, 'require_active'), \
                patch.object(adapter, 'spawn_anchored', return_value=setup), \
                patch.object(adapter, 'waitid_nonreap', side_effect=[None, object()]), \
                patch.object(adapter, 'observe_case_ready', return_value=None), \
                patch.object(adapter, 'stop_anchored', return_value=[0, 0]), \
                patch.object(adapter.time, 'sleep'), \
                patch.object(signal, 'pthread_sigmask', return_value=set()):
            adapter.owned_command(object(), ['/usr/bin/xcrun', '--version'],
                Path('/unused'), {}, Path('/unused/output'),
                adapter.time.monotonic() + 5, adapter.time.monotonic() + 10,
                control_context=(controller, 'managed', Child()))
        self.assertEqual(controller.frames, [], 'not-ready must not become a null readiness event')

    def test_bootstrap_executes_target_vector_after_python_c_option(self):
        target = [sys.executable, str(package.ADAPTER), '--timeout', '585', '--control-case', 'setup']
        observed = []
        # This is the interpreter's documented argv layout for -c. No child,
        # exec, native process API, control workload or measurement is run.
        with patch.object(sys, 'argv', ['-c', *target]), \
                patch.object(os, 'execv', lambda path, argv: observed.append((path, list(argv)))), \
                patch.object(signal, 'pthread_sigmask', return_value=set()):
            exec(package.BOOTSTRAP, {})
        self.assertEqual(observed, [(target[0], target)])

    def test_pending_signal_leaves_created_child_available_for_cleanup(self):
        class Child:
            pid = 12345
            returncode = None
            def __init__(self): self.signals, self.waits = [], []
            def poll(self): return self.returncode
            def send_signal(self, signum): self.signals.append(signum)
            def wait(self, timeout):
                self.waits.append(timeout)
                self.returncode = -signal.SIGTERM
                return self.returncode

        child = Child()
        created = []
        def fake_popen(*args, **kwargs):
            created.append(child)
            return child
        def pending_mask(how, mask):
            if how == signal.SIG_SETMASK:
                raise package.ControlCancelled('pending signal delivered on unmask')
            return set()

        with tempfile.TemporaryDirectory(dir=Path(__file__).parent) as temporary:
            root = Path(temporary).resolve()
            scope = root / 'scope'
            scope.mkdir()
            (scope / 'tmp').mkdir()
            logs = root / 'logs'
            logs.mkdir()
            with patch.object(package, 'EVIDENCE', logs), \
                    patch.object(signal, 'pthread_sigmask', side_effect=pending_mask):
                with self.assertRaises(package.ControlCancelled):
                    package.run_control_case('setup', scope, logs / 'control',
                        popen_factory=fake_popen, manage_signals=False)
            self.assertEqual(created, [child])
            self.assertEqual(child.signals, [signal.SIGTERM],
                'pending delivery lost the already-created direct-child handle')
            self.assertEqual(len(child.waits), 1)


if __name__ == '__main__':
    unittest.main()
