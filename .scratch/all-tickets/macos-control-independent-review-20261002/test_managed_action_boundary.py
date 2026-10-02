"""Pure deterministic scheduling regression: no child, socket, or native call."""
import importlib.util
from pathlib import Path
import unittest
from unittest.mock import patch
import signal
import time
spec = importlib.util.spec_from_file_location('review_adapter', Path(__file__).with_name('correction-source') / '.scratch/all-tickets/run-macos-process-overhead-scoped.py')
adapter = importlib.util.module_from_spec(spec)
spec.loader.exec_module(adapter)
class InjectionBoundary(unittest.TestCase):
    def test_completed_fixture_after_fresh_observation_cannot_be_accepted(self):
        gate = type('Gate', (), {'pid': 101, 'returncode': None})()
        ready = adapter.make_case_ready_event('managed', 'published', {
            slot: {'pid': pid, 'start_seconds': 1, 'start_microseconds': pid}
            for slot,pid in [('managed_host',101),('gate',101),('anchor',102),('fixture',103),('client',90)]},
            {'managed_host_live':True,'fixture_live':True,'fixture_topology_live':True,
             'fixture_thread_count':4,'stdout_bytes_read':8,'stderr_bytes_read':8})
        fresh = {**ready, 'event_id':'fresh'}
        request = {'op':'interrupt','case':'managed','event_id':'published','target':'managed_host','signal':'KILL'}
        state = {'fixture_live':True}
        killed_after_completion=[]
        compare = adapter.same_case_readiness_state
        def compare_then_schedule_completion(*args):
            valid=compare(*args)
            # A runnable host/fixture may finish after the final native census
            # and readiness comparison, before the next adapter instruction.
            state['fixture_live']=False
            return valid
        def exact_kill(_pid, _signal):
            if not state['fixture_live']: killed_after_completion.append(True)
        with patch.object(adapter.select,'select',return_value=([object()],[],[])),              patch.object(adapter,'read_line',return_value=request),              patch.object(adapter,'same_case_readiness_state',side_effect=compare_then_schedule_completion),              patch.object(adapter.os,'kill',side_effect=exact_kill):
            action=adapter.service_controller(object(),'managed',ready,False,None,gate,time.monotonic()+2,
                pre_action_validate=lambda:fresh)
        self.assertEqual(killed_after_completion,[],
            'valid cached action receipt is returned even when fixture completes before exact KILL')
if __name__ == '__main__': unittest.main()
