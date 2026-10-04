import json,subprocess,sys,time,pathlib
preflight=json.loads(sys.stdin.read());deadline=time.monotonic()+180
while True:
 p=subprocess.run([sys.executable,'-c',preflight],capture_output=True,text=True,timeout=20)
 print('SLOT_OBSERVATION '+json.dumps(dict(returncode=p.returncode,stdout=p.stdout,stderr=p.stderr)),flush=True)
 if p.returncode==0:
  p.check_returncode(); receipt=json.loads(p.stdout);assert receipt['ready'] is True and receipt['inputs_verified']==10 and receipt['heavy']==[]
  allocation=dict(source='20d25ad8ed4483d4cd4079cf62c8481a629c00e3',native_example_launch=3,preflight=receipt,outer_seconds=600,runner_seconds=585,helper_seconds=540,history='launches1+2 consumed; native110 unallocated; stopped chains unchanged')
  with pathlib.Path('/root/rhai-linux-sys-process-example-20d25ad8-20261004/launch3-allocation.json').open('x') as f:json.dump(allocation,f,indent=2)
  print('NATIVE3_ALLOCATED '+json.dumps(allocation),flush=True)
  r=subprocess.run(['bash','/root/rhai-linux-sys-process-example-20d25ad8-20261004/launch.sh'],timeout=615)
  print('NATIVE3_TERMINAL '+str(r.returncode),flush=True);raise SystemExit(r.returncode)
 if p.returncode!=3:raise RuntimeError('preflight infrastructure failure: '+p.stderr)
 if time.monotonic()>=deadline:raise SystemExit(3)
 time.sleep(1)
