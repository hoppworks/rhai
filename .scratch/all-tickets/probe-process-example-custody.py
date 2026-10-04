#!/usr/bin/env python3
"""Bounded parser probes over the preserved original process example rows."""
import ast, contextlib, copy, importlib.util, io, json, pathlib, shutil, subprocess, sys, tempfile
ROOT=pathlib.Path('/Users/hoppworks/.codex/worktrees/all-tickets-continuation/rhai/.scratch/all-tickets/process-example1-originals/stage-originals')
EXPECTED={'proof-evidence/process-identities.tsv':'f7949153ace6ecfc2b7a4b491308f6e1cd72d01b3c7d2fbab0a422a24a3a9aaf','outer-evidence/launcher-identities.tsv':'a3ef24e9092e530e7e41dc7d147bea70fe216769a321bcf2d49abd339d60de81'}
def digest(p):
 import hashlib
 return hashlib.sha256(p.read_bytes()).hexdigest()
for rel,want in EXPECTED.items(): assert digest(ROOT/rel)==want, rel
spec=importlib.util.spec_from_file_location('collector',pathlib.Path(__file__).with_name('collect-linux-sys-process-example.py')); c=importlib.util.module_from_spec(spec); spec.loader.exec_module(c)
ast.parse(c.REMOTE_INVENTORY); ast.parse(c.REMOTE_CUSTODY)
def deletion_assignment(source):
 tree=ast.parse(source); retire=next(x for x in tree.body if isinstance(x,ast.FunctionDef) and x.name=='retire')
 return next(x.value for x in retire.body if isinstance(x,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='deletion' for t in x.targets))
module_tree=ast.parse(pathlib.Path(spec.origin).read_text())
deletion_node=deletion_assignment(pathlib.Path(spec.origin).read_text())
compile(deletion_node.value,'<REMOTE_DELETION>','exec')
proc_path=ROOT/'proof-evidence/process-identities.tsv'; launch_path=ROOT/'outer-evidence/launcher-identities.tsv'; original_proc=proc_path.read_text(); original_launch=launch_path.read_text()
def produce(proc_text=original_proc,launch_text=original_launch,stat='absent',collector=c):
 recorded={int(f[1]):int(f[4]) for text in (proc_text,launch_text) for line in text.splitlines()[1:] if len((f:=line.split('\t',5)))==6}
 with tempfile.TemporaryDirectory() as td:
  stage=pathlib.Path(td)/'stage'; shutil.copytree(ROOT,stage); (stage/'proof-evidence/process-identities.tsv').write_text(proc_text); (stage/'outer-evidence/launcher-identities.tsv').write_text(launch_text)
  old_check=subprocess.check_output; old_read=pathlib.Path.read_text; old_exists=pathlib.Path.exists; old_link=pathlib.Path.is_symlink
  def check(*args,**kwargs):
   if stat=='ps-failure': raise subprocess.CalledProcessError(1,args[0])
   if stat=='bad-ps': return 'malformed census\n'
   if stat=='group-live': return '99 3061340\n'
   return ''
  def read(path,*args,**kwargs):
   if str(path).startswith('/proc/') and str(path).endswith('/stat'):
    pid=int(str(path).split('/')[-2])
    if stat=='absent': raise FileNotFoundError(str(path))
    if stat=='permission': raise PermissionError(str(path))
    if stat=='badframe': return str(pid)+' (bad S x'
    if stat=='badstart': return str(pid)+' (x) S '+' '.join(['1']*18+['nonnumeric'])
    if stat=='badzero': return str(pid)+' (x) S '+' '.join(['1']*18+['0'])
    if stat in ('missing-open','wrong-pid-prefix','different-pid-prefix'):
     ticks=999999999
     prefix=') S ' if stat=='missing-open' else (str(pid+1)+' (x) S ' if stat=='different-pid-prefix' else '999999999 (x) S ')
     return prefix+' '.join(['1']*18+[str(ticks)])
    if stat in ('live','zombie','reused','reused-signed'):
     ticks=recorded[pid] if stat in ('live','zombie') else 999999999
     state='Z' if stat=='zombie' else 'S'
     values=['1']*18+[str(ticks)]
     if stat=='reused-signed': values[3]=values[4]='-1'
     return str(pid)+' (comm with ) parens) '+state+' '+' '.join(values)
   return old_read(path,*args,**kwargs)
  def exists(path):
   if stat in ('runtime-present','runtime-symlink') and str(path).startswith(collector.SCOPE+'/agent-build-'): return stat=='runtime-present'
   return old_exists(path)
  def is_symlink(path):
   if stat=='runtime-symlink' and str(path).startswith(collector.SCOPE+'/agent-build-'): return True
   return old_link(path)
  subprocess.check_output=check; pathlib.Path.read_text=read; pathlib.Path.exists=exists; pathlib.Path.is_symlink=is_symlink; saved=sys.argv; sys.argv=['custody',str(stage),collector.SCOPE]; output=io.StringIO()
  try:
   with contextlib.redirect_stdout(output): exec(compile(collector.REMOTE_CUSTODY,'<REMOTE_CUSTODY>','exec'),{'__name__':'__main__'})
  finally: subprocess.check_output=old_check; pathlib.Path.read_text=old_read; pathlib.Path.exists=old_exists; pathlib.Path.is_symlink=old_link; sys.argv=saved
  return json.loads(output.getvalue())
legacy_source=subprocess.check_output(['git','show','e537a830200519eb39e4477ae46bb3cb144b089b:.scratch/all-tickets/collect-linux-sys-process-example.py'],text=True)
with tempfile.TemporaryDirectory() as td:
 legacy_path=pathlib.Path(td)/'legacy_collector.py'; legacy_path.write_text(legacy_source)
 legacy_spec=importlib.util.spec_from_file_location('legacy_collector',legacy_path); legacy=importlib.util.module_from_spec(legacy_spec); legacy_spec.loader.exec_module(legacy)
 legacy_result=produce(collector=legacy)
 assert not legacy_result['custody_ready'] and any('duplicate identity label' in e for e in legacy_result['errors'])
c600_source=subprocess.check_output(['git','show','c600773798be9c4b7a134d33e8059622a330b67d:.scratch/all-tickets/collect-linux-sys-process-example.py'],text=True)
with tempfile.TemporaryDirectory() as td:
 c600_path=pathlib.Path(td)/'c600_collector.py'; c600_path.write_text(c600_source)
 c600_spec=importlib.util.spec_from_file_location('c600_collector',c600_path); c600=importlib.util.module_from_spec(c600_spec); c600_spec.loader.exec_module(c600)
c600_deletion_node=deletion_assignment(c600_source)
base=produce(); assert base['custody_ready'] and c.validate_custody_receipt(base)
assert len(base['process_identities'])==64 and len(base['launcher_identities'])==2
assert sum(r['label']=='command:du' for r in base['process_identities'])==29 and sum(r['label']=='command:ps' for r in base['process_identities'])==29
assert sum(r['label'].startswith('command:') and r['cmdline']=='' for r in base['process_identities'])==3
assert len({r['pid'] for r in base['process_identities']+base['launcher_identities']})==66
assert all(not produce(stat=state)['custody_ready'] for state in ('badframe','badstart','badzero','live','zombie'))
reused=produce(stat='reused'); assert reused['custody_ready'] and c.validate_custody_receipt(reused) and all(x['state']=='pid-reused-original-absent' for x in reused['pid_start_observations'])
reused_signed=produce(stat='reused-signed'); assert reused_signed['custody_ready'] and c.validate_custody_receipt(reused_signed)
assert all(not produce(stat=state)['custody_ready'] for state in ('permission','ps-failure','bad-ps','group-live','runtime-present','runtime-symlink'))
header,*lines=original_proc.splitlines(); first=lines[0].split('\t'); duplicate_pid='\t'.join([first[0],lines[1].split('\t')[1],*first[2:]])
assert not produce(header+'\n'+'\n'.join(lines+[duplicate_pid])+'\n')['custody_ready']
assert not produce(header+'\n'+'\n'.join(lines+[lines[0]])+'\n')['custody_ready']
assert not produce('wrong\n'+'\n'.join(lines)+'\n')['custody_ready']
assert not produce(header+'\n'+'\n'.join(lines[1:])+'\n')['custody_ready']
assert not produce(header+'\n'+'\n'.join(lines+[lines[0]])+'\n')['custody_ready']
empty_command_label=lines.copy(); command_index=next(i for i,x in enumerate(empty_command_label) if x.startswith('command:')); fields=empty_command_label[command_index].split('\t',5); fields[0]='command:'; empty_command_label[command_index]='\t'.join(fields)
assert not produce(header+'\n'+'\n'.join(empty_command_label)+'\n')['custody_ready']
empty_owner=lines[0].rsplit('\t',1)[0]+'\t'; assert not produce(header+'\n'+'\n'.join([empty_owner,*lines[1:]])+'\n')['custody_ready']
def rejects(mut):
 x=copy.deepcopy(base); mut(x); return not c.validate_custody_receipt(x)
mutations=[('wrong_parent',lambda x:x['process_identities'][1].__setitem__('ppid',1)),('wrong_owner_provenance',lambda x:x['process_identities'][0].__setitem__('cmdline','python unrelated.py')),('same_basename_wrong_path',lambda x:x['process_identities'][0].__setitem__('cmdline','python /tmp/run-examples.py')),('duplicate_identity_pid',lambda x:x['process_identities'][2].__setitem__('pid',x['process_identities'][1]['pid'])),('boolean_pid',lambda x:x['process_identities'][0].__setitem__('pid',True)),('missing_observation',lambda x:x['pid_start_observations'].pop()),('live_observation',lambda x:x['pid_start_observations'][0].__setitem__('state','live')),('wrong_groups',lambda x:x.__setitem__('groups',[1])),('unknown_runtime',lambda x:x.__setitem__('runtime_state','unknown')),('malformed_identity_object',lambda x:x['process_identities'].__setitem__(0,None))]
for name,mut in mutations: assert rejects(mut),name

# RED coverage: execute the actual custody consumer and each actual retirement
# stat loop against original identities with malformed, reused-looking records.
def isolated_retirement_loop(source, loop_index, stat_text, rows):
 tree=ast.parse(source); loops=[]
 for node in ast.walk(tree):
  if isinstance(node,ast.For) and ast.unparse(node.iter)=='c[\'process_identities\'] + c[\'launcher_identities\']': loops.append(node)
 assert len(loops)==2, len(loops)
 loop=copy.deepcopy(loops[loop_index]); original=pathlib.Path.read_text
 def fake_read(path,*args,**kwargs):
  if str(path).startswith('/proc/') and str(path).endswith('/stat'):
   if stat_text is None: raise FileNotFoundError(str(path))
   return stat_text
  return original(path,*args,**kwargs)
 pathlib.Path.read_text=fake_read
 ns={'c':rows,'pathlib':pathlib,'re':__import__('re'),'SystemExit':SystemExit,'PermissionError':PermissionError,'OSError':OSError,'IndexError':IndexError,'ValueError':ValueError,'FileNotFoundError':FileNotFoundError}
 if loop_index==1: ns['final_obs']=[]
 try:
  exec(compile(ast.Module(body=[loop],type_ignores=[]),'<actual-retirement-loop>','exec'),ns)
  return True
 except SystemExit:
  return False
 finally: pathlib.Path.read_text=original

def loop_results(source, malformed):
 # Correctly shaped reuse-looking tail with invalid framing/PID identity.
 for row in base['process_identities']+base['launcher_identities']:
  malformed_text=malformed(row)
  # Run one representative exact row per loop; all loops share this validator.
  single={'process_identities':[row],'launcher_identities':[],'groups':[row['pgid']]}
  accepted=isolated_retirement_loop(source,0,malformed_text,single)
  final_accepted=isolated_retirement_loop(source,1,malformed_text,single)
  return accepted,final_accepted

sample=base['process_identities'][0]
single_sample={'process_identities':[sample],'launcher_identities':[],'groups':[sample['pgid']]}
def shaped_stat(row,state,ticks):
 values=['1']*18+[str(ticks)]; values[3]=values[4]='-1'
 return str(row['pid'])+' (command with ) and spaces) '+state+' '+' '.join(values)
for source in (c600_deletion_node.value,deletion_node.value):
 for loop_index in (0,1):
  assert isolated_retirement_loop(source,loop_index,shaped_stat(sample,'S',sample['start_ticks']+1),single_sample)
  assert isolated_retirement_loop(source,loop_index,None,single_sample)
  for live_state in ('S','Z'):
   assert not isolated_retirement_loop(source,loop_index,shaped_stat(sample,live_state,sample['start_ticks']),single_sample)

for malformed_name, malformed in (
 ('missing-open',lambda row:') S '+' '.join(['1']*18+['999999999'])),
 ('wrong-pid-prefix',lambda row:'999999999 (x) S '+' '.join(['1']*18+['999999999'])),
 ('different-pid-prefix',lambda row:str(row['pid']+1)+' (x) S '+' '.join(['1']*18+['999999999']))):
 baseline_custody=produce(stat=malformed_name,collector=c600)
 assert baseline_custody['custody_ready'],('expected c600 custody RED',malformed_name,baseline_custody['errors'])
 assert all(loop_results(c600_deletion_node.value,malformed)),('expected c600 retirement RED',malformed_name)
 custody=produce(stat=malformed_name)
 assert not custody['custody_ready'],('malformed observation accepted by custody',malformed_name,custody['errors'])
 pre,post=loop_results(deletion_node.value,malformed)
 assert not pre and not post,('malformed observation accepted by retirement loop',malformed_name,pre,post)

# The actual helper used after remote deletion rejects incomplete/changed receipts.
final_receipt={'stage_absent':True,'scope_absent':True,'runtime_absent':True,'custody_rechecked':True,'final_groups':base['groups'],'final_group_census':[],'final_pid_start_observations':[dict(x,state=x['state']) for x in base['pid_start_observations']]}
assert c.validate_retirement_receipt(final_receipt,base)
for broken in (dict(final_receipt,final_pid_start_observations=final_receipt['final_pid_start_observations'][:-1]),dict(final_receipt,final_groups=[1]),dict(final_receipt,final_group_census=[[1,1]]),dict(final_receipt,scope_absent=False)):
 assert not c.validate_retirement_receipt(broken,base)

# Exercise the new route against the real preserved 49-file tree without SSH.
with tempfile.TemporaryDirectory() as td:
 dest=pathlib.Path(td)/'evidence'; dest.mkdir()
 shutil.copytree(ROOT,dest/'stage-originals')
 root_preservation=pathlib.Path('/Users/hoppworks/.codex/worktrees/all-tickets-continuation/rhai/.scratch/all-tickets/process-example1-originals/original-preservation.json')
 shutil.copy2(root_preservation,dest/'original-preservation.json')
 shutil.copy2(pathlib.Path('/Users/hoppworks/.codex/worktrees/all-tickets-continuation/rhai/.scratch/all-tickets/process-example1-originals/stage-originals.tar'),dest/'stage-originals.tar')
 (dest/'custody-readback.json').write_text('{\"historical\":true}\n')
 old_get_inventory=c.get_inventory; old_get_custody=c.get_custody
 preservation=json.loads((dest/'original-preservation.json').read_text())
 c.get_inventory=lambda: copy.deepcopy(preservation['inventory'])
 c.get_custody=lambda: copy.deepcopy(base)
 try: c.custody_readback(dest)
 finally: c.get_inventory=old_get_inventory; c.get_custody=old_get_custody
 assert json.loads((dest/'custody-readback.json').read_text())=={'historical':True}
 refreshed=json.loads((dest/'custody-readback-refresh.json').read_text())
assert refreshed['receipt_validated'] is True and c.validate_custody_receipt(refreshed)
with tempfile.TemporaryDirectory() as td:
 dest=pathlib.Path(td)/'evidence'; dest.mkdir(); shutil.copytree(ROOT,dest/'stage-originals')
 shutil.copy2(root_preservation,dest/'original-preservation.json'); shutil.copy2(pathlib.Path('/Users/hoppworks/.codex/worktrees/all-tickets-continuation/rhai/.scratch/all-tickets/process-example1-originals/stage-originals.tar'),dest/'stage-originals.tar')
 (dest/'custody-readback.json').write_text('{"historical":true}\n'); old_get_inventory=c.get_inventory; old_get_custody=c.get_custody
 preservation=json.loads((dest/'original-preservation.json').read_text()); bad=copy.deepcopy(preservation['inventory']); bad['input_binding_verified']=False
 c.get_inventory=lambda: bad; c.get_custody=lambda: copy.deepcopy(base)
 try:
  try: c.custody_readback(dest); raise AssertionError('changed immutable input unexpectedly accepted')
  except RuntimeError: pass
 finally: c.get_inventory=old_get_inventory; c.get_custody=old_get_custody
 assert not (dest/'custody-readback-refresh.json').exists() and (dest/'custody-readback.json').read_text()=='{"historical":true}\n'

preservation=json.loads(pathlib.Path('/Users/hoppworks/.codex/worktrees/all-tickets-continuation/rhai/.scratch/all-tickets/process-example1-originals/original-preservation.json').read_text())
binding=preservation['inventory']; assert c.validate_input_binding(binding)
for key,edit in [('input_manifest_exact',False),('input_binding_verified',False),('input_actual',{}),('inventory_errors',['changed']),('links',[{'path':'x'}])]:
 changed=copy.deepcopy(binding); changed[key]=edit; assert not c.validate_input_binding(changed),key

print(json.dumps({'original_hashes_verified':True,'frozen_e537_actual_original_red':True,'frozen_c600_bad_stat_red':True,'fixed_custody_bad_stat_rejected':True,'fixed_both_retirement_bad_stat_rejected':True,'valid_reused_stat_with_spaces_parentheses_and_signed_fields_supported':True,'absent_live_S_live_Z_retirement_cases':'PASS on c600 and fixed source','producer_ready_positive':True,'receiver_ready_positive':True,'refresh_route_preserves_historical_receipt':True,'refresh_route_rejects_changed_binding':True,'retirement_receipt_positive_and_mutations_rejected':True,'input_binding_positive_and_mutations_rejected':True,'embedded_inventory_custody_deletion_syntax':'PASS','rows':[64,2],'command_du':29,'command_ps':29,'empty_command_strings':3,'distinct_pids':66,'producer_negative_cases':['duplicate_pid','duplicate_row','wrong_header','missing_owner','duplicate_owner','empty_owner_cmdline','empty_command_suffix','missing_open_paren','wrong_pid_prefix','different_numeric_pid_prefix','malformed_stat_framing','nonnumeric_start_ticks','zero_start_ticks','permission_unknown','ps_failure','malformed_ps','owned_group_present','runtime_present','runtime_symlink','matching_live_S','matching_live_Z'],'receiver_negative_cases':[x[0] for x in mutations]},sort_keys=True,indent=2))
