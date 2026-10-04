import json,subprocess,sys,time,pathlib
preflight=json.loads(sys.stdin.read());deadline=time.monotonic()+180
while True:
 p=subprocess.run([sys.executable,'-c',preflight],capture_output=True,text=True,timeout=20)
 print('SLOT_OBSERVATION '+json.dumps(dict(returncode=p.returncode,stdout=p.stdout,stderr=p.stderr)),flush=True)
 if p.returncode==0:
  p.check_returncode(); receipt=json.loads(p.stdout);assert receipt['ready'] is True and receipt['inputs_verified']==10 and receipt['allowed_heavy'] is True
  allocation=dict(source='523608648dcae99bc0f6b46eaf2bb91fa4ecc752',native_pipe_setup_launch=2,preflight=receipt,outer_seconds=600,runner_seconds=585,helper_seconds=540,history='pipe-setup optionalMSRV followup, native1 setup-cwd failure consumed, native2 prospective; existing native80/mac81 positive unchanged; prior histories retained; native110 and stopped paths not renewed')
  with pathlib.Path('/root/rhai-linux-post-spawn-pipe-setup-523-20261004/pipe-setup-launch2-allocation.json').open('x') as f:json.dump(allocation,f,indent=2)
  print('PIPE_SETUP_NATIVE2_ALLOCATED '+json.dumps(allocation),flush=True)
  r=subprocess.run(['bash','/root/rhai-linux-post-spawn-pipe-setup-523-20261004/launch.sh'],timeout=615)
  print('PIPE_SETUP_NATIVE2_TERMINAL '+str(r.returncode),flush=True);raise SystemExit(r.returncode)
 if p.returncode!=3:raise RuntimeError('preflight infrastructure failure: '+p.stderr)
 if time.monotonic()>=deadline:raise SystemExit(3)
 time.sleep(1)
