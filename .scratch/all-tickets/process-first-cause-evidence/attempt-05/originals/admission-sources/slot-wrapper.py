import ast,hashlib,json,pathlib,subprocess,sys,time
remote=json.loads(sys.stdin.read())
stage=pathlib.Path('/root/rhai-linux-process-first-cause-fc-20261007-ack05-7d11e2c4')
guard_path=stage/'linux-process-first-cause-preflight.py'
wrapper_path=stage/'linux-process-first-cause-slot-wrapper.py'
assert pathlib.Path(__file__).resolve()==wrapper_path.resolve()
assert not guard_path.is_symlink() and not wrapper_path.is_symlink()
guard_bytes=guard_path.read_bytes();wrapper_bytes=wrapper_path.read_bytes()
assignments=[n for n in ast.parse(guard_bytes).body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='remote' for t in n.targets)]
assert len(assignments)==1 and ast.literal_eval(assignments[0].value)==remote
guard_hash=hashlib.sha256(guard_bytes).hexdigest()
wrapper_hash=hashlib.sha256(wrapper_bytes).hexdigest()
deadline=time.monotonic()+180
while True:
 result=subprocess.run([sys.executable,'-c',remote],capture_output=True,text=True,timeout=20)
 print('FIRST_CAUSE_SLOT_OBSERVATION '+json.dumps(dict(returncode=result.returncode,stdout=result.stdout,stderr=result.stderr)),flush=True)
 if result.returncode==0:
  result.check_returncode();receipt=json.loads(result.stdout)
  assert receipt['ready'] is True and receipt['inputs_verified']==16 and not receipt['heavy']
  allocation=dict(source_revision='ce1f40b23588ba08b260439c7f441d8318368425',native_launch=1,campaign_allocation=5,preflight_source_sha256=guard_hash,slot_wrapper_source_sha256=wrapper_hash,classification='initial planning estimate, all launches counted',preflight=receipt,outer_seconds=600,runner_seconds=585,helper_seconds=540)
  with pathlib.Path('/root/rhai-linux-process-first-cause-fc-20261007-ack05-7d11e2c4/native-allocation.json').open('x') as out: json.dump(allocation,out,indent=2)
  print('FIRST_CAUSE_ALLOCATED '+json.dumps(allocation),flush=True)
  run=subprocess.run(['bash','/root/rhai-linux-process-first-cause-fc-20261007-ack05-7d11e2c4/launch.sh'],timeout=615)
  print('FIRST_CAUSE_TERMINAL '+str(run.returncode),flush=True)
  raise SystemExit(run.returncode)
 if result.returncode!=3: raise RuntimeError('preflight infrastructure failure: '+result.stderr)
 if time.monotonic()>=deadline: raise SystemExit(3)
 time.sleep(1)
