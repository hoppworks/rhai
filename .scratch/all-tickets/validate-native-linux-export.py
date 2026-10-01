import pathlib,json,hashlib,sys
p=pathlib.Path(sys.argv[1] if len(sys.argv)>1 else '.scratch/process-rust-io-followup-evidence/linux1772-20261001-060839UTC');l=json.loads((p/'run-ledger.json').read_text());checks=[]
def digest(b):return hashlib.sha256(b).hexdigest()
def hashed(n,h):assert digest((p/n).read_bytes())==h,n;checks.append(n)
order=['normal','cancel','missing-wake','term','kill']+[f'{s}-{n}-{x}' for s in ['stdout','stderr'] for n in [4096,0] for x in [n,n+1]]
assert l['case_order']==order and [c['control'] for c in l['cases']]==order
for c in l['cases']:
 hashed(c['receipt'],c['sha256']);hashed(c['finalizer'],c['finalizer_sha256'])
 d=json.loads((p/c['receipt']).read_text());f=json.loads((p/c['finalizer']).read_text());name=c['control']
 assert f['terminal_receipt_sha256']==c['sha256'];assert all(x['still_same_process']==x['expected_live'] for x in f['original_process_identities'])
 assert d['custodian_fds_closed'] and d['sentinel_alive_before_cleanup'];assert d['native_live_snapshot']['anchor'] and d['native_live_snapshot']['sentinel']
 if name in ['term','kill']:
  assert d['children']['runner']['wait_status']==(15 if name=='term' else 9);assert 'native_io' not in d;assert all(d['runner_interruption_precondition'].values());continue
 a=d['native_io'];assert a['workers_started']==a['workers_joined']==3 and 0<=a['wake_to_join_ms']<=1000
 for s in ['stdin','stdout','stderr']:
  n=a[s+'_bytes'];block=bytes(i^(0xa5 if s=='stderr' and name in ['normal','cancel','missing-wake'] else 0) for i in range(256));b=(block*((n+255)//256))[:n]
  assert a[s+'_sha256']==digest(b),(name,s)
  if s!='stdin':assert bytes.fromhex(a[s+'_prefix_hex'])==b[:min(n,64 if name in ['normal','cancel','missing-wake'] else 4096)]
 if name=='normal':
  assert all(a[s+'_bytes']==2097152 for s in ['stdin','stdout','stderr']);assert a['stdin_end']=='complete' and a['stdout_end']==a['stderr_end']=='eof'
 elif name in ['cancel','missing-wake']:
  assert a['stdin_bytes']==1114112 and a['stdout_bytes']==a['stderr_bytes']==1048576;assert all(a[s+'_end']=='cancelled' for s in ['stdin','stdout','stderr']);assert d['native_live_snapshot']['holder'];assert a['missing_wake_observation_ms']==(250 if name=='missing-wake' else 0)
 else:
  s,n,x=name.split('-');n=int(n);x=int(x);other='stderr' if s=='stdout' else 'stdout';over=x>n
  assert a==d['raw_cap_readback'];assert a[s+'_bytes']==n and a[other+'_bytes']==0 and a['stdin_bytes']==73728
  assert a['first_cause']==(s+'-output-limit' if over else None);assert a[s+'_end']==('output_limit' if over else 'eof');assert a[other+'_end']==('cancelled' if over else 'eof')
  r=d['raw_cap_readiness'];assert r['channel']==s and r['requested_bytes']==x and r['stdin_bytes']==4096 and r['stdin_sha256']==digest(bytes(range(256))*16);assert r['pid']==r['pgid']==d['children']['leader']['pid']
  buf=d['cap_protocol_socket_buffers'];assert buf['requested_bytes']==65536;assert all(v>=65536 for endpoint in buf['endpoints'].values() for v in endpoint.values())
  if over:assert d['raw_cap_holder_live_after_joins'] and d['native_live_snapshot']['holder']
  else:assert d['raw_cap_boundary_natural_eof']
for row in l['setup']+l['builds']:
 assert row['status']==0 and not row['timed_out'] and row['output_complete'] and row['stop_reason'] is None;hashed(row['log'],row['log_sha256'])
for row in l['resolved_lockfiles']:hashed(row['name'],row['sha256']);assert (p/row['name']).stat().st_size==row['bytes']
assert l['toolchain']['verified_versions']==dict.fromkeys(['rustc','cargo','rustdoc'],'1.77.2')
for n in ['rustc','cargo','rustdoc']:assert (p/(n+'-version.log')).read_text().split()[:2]==[n,'1.77.2']
s=json.loads((p/'sampler-children.json').read_text());assert all(x['terminal'] and x['returncode']==0 for x in s)
assert len(s)==len(l['resource_samples']) and l['sampler_failure'] is None
assert max(x['private_bytes'] for x in l['resource_samples'])==l['sampled_private_bytes_max']<1073741824
assert max(x['owned_processes_including_sampler'] for x in l['resource_samples'])==l['sampled_process_max']==8
for n in ['outer/outer-status.txt','outer/run-scoped.status']:assert (p/n).read_text().strip()=='0'
out={'cases':13,'distinct_ledger_hashed_files':len(set(checks)),'sampler_children_terminal':len(s),'valid_resource_samples':len(l['resource_samples']),'sampled_private_bytes_max':l['sampled_private_bytes_max'],'sampled_process_max':8,'wrapper_status':0,'limitations':['Standalone native prototype, not public Engine API','External custodian pipe holder does not prove workload-spawned escaped-descendant topology','Resource maxima are sampled, not continuous peaks','Runner interruption proves custody, not worker joins']}
pathlib.Path('.scratch/all-tickets/native-linux-independent-raw-check.json').write_text(json.dumps(out,indent=2)+'\n');print(out)
