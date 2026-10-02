"""Injected affected regressions; no processes, signals or native API calls."""
import importlib.util,json,os,sys,tempfile,time,unittest
from pathlib import Path
from unittest.mock import patch
spec=importlib.util.spec_from_file_location('review_action_adapter',Path(__file__).with_name('action-correction-source')/'.scratch/all-tickets/run-macos-process-overhead-scoped.py')
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
 def test_capture_failure_cannot_leave_action_eligible_capturing_receipt(self):
  identities={slot:dict(pid=pid,start_seconds=1,start_microseconds=pid) for slot,pid in [('client',90),('gate',101),('anchor',102),('managed_host',101),('fixture',103)]}
  evidence=dict(managed_host_live=True,fixture_live=True,fixture_topology_live=True,fixture_thread_count=4,fixture_path='/private/fixture',capture_generation=2,stdout_bytes_read=100,stderr_bytes_read=100)
  ready=a.make_case_ready_event('managed','published',identities,evidence)
  stopped={**evidence,'managed_host_stopped':True};witness=a.managed_stopped_output_witness(stopped);stopped.update(witness)
  fresh=a.make_case_ready_event('managed','stopped',identities,stopped);fresh['stop_proof']=dict(host_status=a.DARWIN_SSTOP,host_identity=identities['managed_host'],capture_generation=2,output_witness=witness)
  request=dict(op='interrupt',case='managed',event_id='published',target='managed_host',signal='KILL');gate=type('Gate',(),dict(pid=101,returncode=None))()
  # Rust fail() has taken stdin/stdout/stderr, but has not submitted fixture
  # cleanup yet. No receipt invalidation occurs; all listed identities/tasks
  # can still be live at this scheduler boundary.
  capture_endpoints_open=False
  with patch.object(a.select,'select',return_value=([object()],[],[])),patch.object(a,'read_line',return_value=request),patch.object(a.os,'kill'):
   action=a.service_controller(object(),'managed',ready,False,None,gate,time.monotonic()+2,pre_action_validate=lambda:fresh,confirm_stopped=lambda proc,identity,deadline:{**identity,'status':a.DARWIN_SSTOP},confirm_fixture_live=lambda identity,deadline:{**identity,'path':'/private/fixture','pgid':103,'status':3})
  self.assertTrue(capture_endpoints_open or action is None,'aborted capture still produces an accepted Managed action from stale stage=capturing receipt')
if __name__=='__main__':unittest.main()
