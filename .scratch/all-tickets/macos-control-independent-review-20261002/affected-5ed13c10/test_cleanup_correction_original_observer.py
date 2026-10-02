"""Injected affected regressions; no processes, signals or native API calls."""
import importlib.util,json,os,sys,tempfile,time,unittest
from pathlib import Path
from unittest.mock import patch
spec=importlib.util.spec_from_file_location('review_action_adapter',Path(__file__).with_name('cleanup-correction-source')/'.scratch/all-tickets/run-macos-process-overhead-scoped.py')
a=importlib.util.module_from_spec(spec);spec.loader.exec_module(a)
class ActionRegressions(unittest.TestCase):
 def test_real_stopped_observer_retains_validated_host_status(self):
  with tempfile.TemporaryDirectory(dir=Path(__file__).parent) as temporary:
   root=Path(temporary).resolve();host=root/'target/debug/examples/macos-managed-capture-companion';fixture=root/'target/debug/deps/sys_process-frozen';fixture.parent.mkdir(parents=True);fixture.touch()
   ready,record,complete,progress=[root/name for name in ('managed-host-ready.json','managed-fixture.record','managed-host-complete','managed-capture-progress.json')]
   ready.write_text(json.dumps({'schema':1,'host_pid':101,'stage':'managed-run-entering'}));record.write_text('child-pid=103 child-ready=1\n');progress.write_text(json.dumps({'schema':1,'stage':'capturing','generation':2,'host_pid':101,'fixture_pid':103,'stdout_bytes_read':100,'stderr_bytes_read':100}))
   def row(pid,ppid,pgid,path,status=3):return dict(pid=pid,ppid=ppid,pgid=pgid,path=str(path),status=status,start_seconds=1,start_microseconds=pid,thread_count=4)
   rows=[row(101,os.getpid(),101,host,a.DARWIN_SSTOP),row(102,os.getpid(),101,sys.executable),row(103,101,103,fixture),row(90,os.getpid(),90,sys.executable)]
   class Reader:
    def complete_listing(self,deadline):return rows
   class Custody:
    _adapter_process_reader=Reader()
    @staticmethod
    def descendants(by_pid,pid):return [r for r in rows if r['pid'] in (102,103)]
   gate=type('Gate',(),{'pid':101})();anchor=type('Anchor',(),{'pid':102})();client=type('Client',(),{'pid':90})()
   with patch.object(a,'merge_observed_identities'):
    event=a.observe_managed_case_ready(Custody(),[str(host),str(fixture),str(ready),str(record),str(complete),str(progress)],gate,anchor,client,time.monotonic()+2,root,require_stopped=True)
   self.assertEqual(event['stop_proof']['host_status'],a.DARWIN_SSTOP)

if __name__=='__main__':unittest.main()
