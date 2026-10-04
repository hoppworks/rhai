"""Finite probes of the actual collection recovery against immutable native originals."""
import copy,csv,hashlib,importlib.util,json,pathlib
ROOT=pathlib.Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('recovery',ROOT/'collect-originals-recovery.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
tree=ROOT/'originals/stage-originals';proof=tree/'proof-evidence'
inventory=json.loads((ROOT/'originals/independent-readback.json').read_text())
request=m.validate(tree,inventory)
commands=json.loads((proof/'commands.json').read_text());by={}
for row in csv.DictReader((proof/'process-identities.tsv').open(),delimiter='\t'):by.setdefault(row['label'],[]).append(row)
results=['actual native corpus accepted without changing original bytes']
def rejects(name,command,rows,labels):
 try:m.validate_command_identity(command,rows,labels)
 except ValueError:results.append(name+' rejected');return
 raise AssertionError(name+' wrongly accepted')
c=commands[0];r=by['command:rustup-install']
bad=copy.deepcopy(r);bad[0]['start_ticks']='11387240';rejects('empty identity reuse',c,bad,by)
bad=copy.deepcopy(r);bad[0]['cmdline']='unrelated populated command';rejects('populated setup mismatch',c,bad,by)
bad=copy.deepcopy(c);bad['status']=1;rejects('unsuccessful setup',bad,r,by)
bad=copy.deepcopy(c);bad['argv']=['wrong spawn'];rejects('wrong setup spawn',bad,r,by)
bad=copy.deepcopy(by);bad['helper'][0]['pgid']='1';rejects('foreign helper group',c,r,bad)
for command in commands[1:]:
 rows=copy.deepcopy(by['command:'+command['name']]);rows[0]['cmdline']='';rejects('unapproved empty '+command['name'],command,rows,by)
 rows=copy.deepcopy(by['command:'+command['name']]);rows[0]['cmdline']='wrong populated argv';rejects('populated mismatch '+command['name'],command,rows,by)
old=m.RECOVERY_PROOF_PINS['commands.json'];m.RECOVERY_PROOF_PINS['commands.json']='0'*64
try:
 try:m.validate(tree,inventory)
 except ValueError as e:assert 'original binding changed commands.json' in str(e);results.append('changed original binding rejected')
 else:raise AssertionError('changed binding accepted')
finally:m.RECOVERY_PROOF_PINS['commands.json']=old
receipt={'adapter_sha256':hashlib.sha256((ROOT/'collect-originals-recovery.py').read_bytes()).hexdigest(),'original_archive_sha256':m.RECOVERY_ARCHIVE_SHA,'cases':results,'validated_identity_count':len(request['identities']),'scope':'local consumer probes; no SSH, signal, retirement or native allocation','observed_setup_argv':'unavailable; exact cause unknown'}
print(json.dumps(receipt,indent=2))
