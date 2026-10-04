import json,subprocess,sys,time,pathlib
preflight=json.loads(sys.stdin.read());deadline=time.monotonic()+180
while True:
 p=subprocess.run([sys.executable,'-c',preflight],capture_output=True,text=True,timeout=20)
 print('SLOT_OBSERVATION '+json.dumps(dict(returncode=p.returncode,stdout=p.stdout,stderr=p.stderr)),flush=True)
 if p.returncode==0:
  p.check_returncode(); receipt=json.loads(p.stdout);assert receipt['ready'] is True and receipt['inputs_verified']==12 and receipt['heavy']==[]
  allocation=dict(source='523608648dcae99bc0f6b46eaf2bb91fa4ecc752',native_drop_false_launch=2,preflight=receipt,outer_seconds=600,runner_seconds=585,helper_seconds=540,history='drop-false native1 consumed setup-only missingpatch, zero tests; first failed stage retired, native2 prospective; failed corrections2, Expert20 single follow-up; native110 unallocated; stopped chains unchanged')
  with pathlib.Path('/root/rhai-linux-drop-false-523-20261004/drop-false-launch2-allocation.json').open('x') as f:json.dump(allocation,f,indent=2)
  print('DROP_FALSE_NATIVE2_ALLOCATED '+json.dumps(allocation),flush=True)
  r=subprocess.run(['bash','/root/rhai-linux-drop-false-523-20261004/launch.sh'],timeout=615)
  print('DROP_FALSE_NATIVE2_TERMINAL '+str(r.returncode),flush=True);raise SystemExit(r.returncode)
 if p.returncode!=3:raise RuntimeError('preflight infrastructure failure: '+p.stderr)
 if time.monotonic()>=deadline:raise SystemExit(3)
 time.sleep(1)
