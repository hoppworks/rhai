"""Pure affected protocol regression; all census and signal operations injected."""
import importlib.util
import json
import signal
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch

source = Path(__file__).with_name('cleanup-correction-source') / '.scratch/all-tickets/test-macos-process-overhead-source.py'
spec = importlib.util.spec_from_file_location('cleanup_tests', source)
tests = importlib.util.module_from_spec(spec)
spec.loader.exec_module(tests)
a = tests.custodian


class IndependentBoundary(unittest.TestCase):
    def test_real_aborted_observer_cannot_produce_kill_action(self):
        with tempfile.TemporaryDirectory(dir=Path(__file__).parent) as directory:
            root = Path(directory).resolve()
            custody, argv, gate, anchor, client = tests.EnvironmentTests()._managed_observer_fixture(root)
            with patch.object(a, 'merge_observed_identities'):
                ready = a.observe_managed_case_ready(custody, argv, gate, anchor, client,
                    time.monotonic() + 2, root)
            progress = json.loads(Path(argv[-1]).read_text())
            progress.update(stage='aborted', generation=0)
            Path(argv[-1]).write_text(json.dumps(progress))
            gate.returncode = None
            request = dict(op='interrupt', case='managed', event_id=ready['event_id'],
                target='managed_host', signal='KILL')
            def fresh():
                return a.observe_managed_case_ready(custody, argv, gate, anchor, client,
                    time.monotonic() + 2, root, require_stopped=True)
            with patch.object(a.select, 'select', return_value=([object()], [], [])), \
                    patch.object(a, 'read_line', return_value=request), \
                    patch.object(a.os, 'kill') as kill:
                with self.assertRaisesRegex(ValueError, 'changed before injection'):
                    a.service_controller(object(), 'managed', ready, False, None, gate,
                        time.monotonic() + 2, pre_action_validate=fresh,
                        confirm_stopped=lambda proc, identity, deadline: {
                            **identity, 'status': a.DARWIN_SSTOP},
                        confirm_fixture_live=lambda *_: self.fail('aborted receipt reached post-KILL'))
            kill.assert_called_once_with(gate.pid, signal.SIGSTOP)


if __name__ == '__main__':
    unittest.main()
