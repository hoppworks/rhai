#!/usr/bin/env python3
"""Local source-shaped probes for the Linux final-drop evidence recipes."""
from __future__ import annotations
import ast, hashlib, importlib.util, json, os, re, shlex, shutil, subprocess, tarfile, tempfile, time, threading
from pathlib import Path
from types import SimpleNamespace

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
OBSERVER = HERE / 'drop-false-observer.py'
PROOF = HERE / 'linux-drop-false-proof.py'
COLLECTOR = HERE / 'collect-originals.py'
PATCH = ROOT / 'linux-drop-false-observer-handshake.patch'
BASE_HELPER = ROOT / 'check-linux-current-msrv-examples.py'
BASELINE = '523608648dcae99bc0f6b46eaf2bb91fa4ecc752'
BASE_TEST_HASH = '5836af855f7410213367786e195c0b9b09c0da005cde37244cfa241baf59c4cb'
PATCHED_TEST_HASH = '90d55b205d93816b156dd0c592d05d1987d92f851dc8031f91dadaac0e040166'

def load(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod

def probe_git_patch_application(proof):
    """Apply the pinned diff to exact 523 bytes and verify the fixed patched-source digest."""
    apply_patch=getattr(proof,'apply_handshake_patch',None)
    if not callable(apply_patch): raise AssertionError('proof helper lacks strict git patch application seam')
    with tempfile.TemporaryDirectory(prefix='drop-false-git-apply-') as td:
        root=Path(td); source=root/'source'; test=source/'tests'/'sys_process.rs'; evidence=root/'evidence'
        git_only=root/'git-only-bin'; test.parent.mkdir(parents=True); evidence.mkdir(); git_only.mkdir()
        (git_only/'git').symlink_to(shutil.which('git'))
        old_path=os.environ.get('PATH','')
        try:
            os.environ['PATH']=str(git_only)
            result=subprocess.run(['git','show',f'{BASELINE}:tests/sys_process.rs'],cwd=ROOT,check=True,capture_output=True)
            test.write_bytes(result.stdout)
            if hashlib.sha256(test.read_bytes()).hexdigest()!=BASE_TEST_HASH:
                raise AssertionError('git source baseline bytes differ from accepted 523 test hash')
            apply_patch(source,PATCH,evidence)
        finally:
            os.environ['PATH']=old_path
        if hashlib.sha256(test.read_bytes()).hexdigest()!=PATCHED_TEST_HASH:
            raise AssertionError('git apply output differs from independently fixed patched-source bytes')
        if not (evidence/'patch-check.stdout').is_file() or not (evidence/'patch-apply.stdout').is_file():
            raise AssertionError('strict check/apply transcript files were not produced')

def rust_template(text: str, marker: str) -> str:
    region = text.split(marker, 1)[1]
    match = re.search(r'&format!\(\s*\+?\s*("(?:\\.|[^"\\])*")', region)
    if not match:
        raise AssertionError(f'no actual Rust format template after {marker!r}')
    return ast.literal_eval(match.group(1))

def render(template: str, named: dict[str, str], positional: list[str]) -> str:
    index = 0
    def sub(m):
        nonlocal index
        key = m.group(1)
        if key:
            if key not in named: raise AssertionError(f'missing producer value {key}')
            return named[key]
        value = positional[index]; index += 1
        return value
    rendered = re.sub(r'\{([A-Za-z_][A-Za-z_0-9]*)?\}', sub, template)
    if index != len(positional): raise AssertionError('unused producer positional values')
    return rendered

def probe_full_custody(collector, exported, archive, actual_sample_lines):
    """Execute the exact isolated custody program with only proc/ps and pin inputs localized."""
    from types import SimpleNamespace
    with tempfile.TemporaryDirectory(prefix='drop-false-custody-probe-') as td:
        root=Path(td); stage=root/'stage'; proof=stage/'proof-evidence'; outer=stage/'outer-evidence'; proof.mkdir(parents=True); outer.mkdir()
        shutil.copytree(exported,proof,dirs_exist_ok=True)
        scope=Path('/root/.local/share/agent-builds/rhai/linux-drop-false-523-20261004'); runtime=scope/'agent-build-l4b8wpaz'
        proof.joinpath('early-runtime-identity.json').write_text(json.dumps({'runtime':str(runtime)}))
        proof.joinpath('resource-samples.jsonl').write_text('{}\n')
        proof.joinpath('control-results.json').write_text('{}\n')
        sample_rows=[json.loads(line.removeprefix('sample=')) for line in actual_sample_lines]
        outer.joinpath('outer.log').write_text('PRIVATE_RUNTIME '+str(runtime)+'\n'+'\n'.join(actual_sample_lines)+'\ncommand=direct-red argv=[cargo]\nouter_status=0\n')
        pids={'helper':10,'scoped-supervisor':20,'launcher':30,'run-scoped':40,
              'command:direct-red':201,'command:managed-red':202,'command:direct-green':203,'command:managed-green':204}
        starts={pid:pid+1000 for pid in pids.values()}
        def row(label,pid,ppid,pgid,cmd): return f'{label}\t{pid}\t{ppid}\t{pgid}\t{starts[pid]}\t{cmd}'
        helper=str(stage/'linux-drop-false-proof.py'); run=str(stage/'runner/tools/run_scoped.py'); launch=str(stage/'launch.sh')
        rows=['label\tpid\tppid\tpgid\tstart_ticks\tcmdline',row('helper',10,20,10,'python3 '+helper),row('scoped-supervisor',20,40,20,'python3 '+run)]
        rows += [row('command:direct-red',201,10,201,'cargo test direct-red'),row('command:managed-red',202,10,202,'cargo test managed-red'),row('command:direct-green',203,10,203,'cargo test direct-green'),row('command:managed-green',204,10,204,'cargo test managed-green')]
        proof.joinpath('process-identities.tsv').write_text('\n'.join(rows)+'\n')
        outer.joinpath('launcher-identities.tsv').write_text('label\tpid\tppid\tpgid\tstart_ticks\tcmdline\n'+row('launcher',30,1,30,'bash '+launch)+'\n'+row('run-scoped',40,30,40,'python3 '+run)+'\n')
        for name in ('outer-status.txt','run-scoped.status','pid-readback.status','pid-readback-launcher.status'): outer.joinpath(name).write_text('0\n')
        for name in ('runtime-cleanup.tsv','scope-cleanup.tsv'): outer.joinpath(name).write_text('status=0\n')
        def terminal(ids): return [{'label':n,'pid':v['pid'],'start_ticks':v['start_ticks'],'absent':True} for n,v in ids.items()]
        def obs_case(case,host,cargo,ids,req,groups):
            live={'request':req,'host':host,'cargo':cargo,'identities':ids,'fixture_root':req['fixture_root'],'complete':True}
            proof.joinpath(case+'-observer-readback.json').write_text(json.dumps({'case':case,'complete':True,'live_observation':live,'terminal_identities':terminal({'host':host,**ids}),'groups_censused':groups,'fixture_root_absent':True}))
        canonical_runtime=Path('/var/roothome/.local/share/agent-builds/rhai/linux-drop-false-523-20261004/agent-build-l4b8wpaz')
        directroot=str(canonical_runtime/'tmp'/'rhai-sys-test-401-direct_spawn_kill_on_drop_false_preserves_child_and_capture-0'); managedroot=str(canonical_runtime/'tmp'/'rhai-sys-test-501-managed_spawn_kill_on_drop_false_preserves_group_until_leader_exit-0')
        dh={'pid':401,'ppid':203,'pgid':401,'start_ticks':1401}; dc={'pid':402,'ppid':401,'pgid':402,'start_ticks':1402}; dcar={'pid':203,'start_ticks':starts[203]}
        obs_case('direct',dh,dcar,{'child':dc},{'case':'direct','test_pid':'401','test_start_ticks':'1401','child_pid':'402','child_start_ticks':'1402','child_pgid':'402','fixture_root':directroot},[])
        mh={'pid':501,'ppid':204,'pgid':501,'start_ticks':1501}; mi={'sentinel':{'pid':502,'ppid':501,'pgid':502,'start_ticks':1502},'leader':{'pid':503,'ppid':501,'pgid':503,'start_ticks':1503},'worker':{'pid':504,'ppid':503,'pgid':503,'start_ticks':1504},'leaf':{'pid':505,'ppid':504,'pgid':503,'start_ticks':1505}}
        mreq={'case':'managed','test_pid':'501','test_start_ticks':'1501','sentinel_pid':'502','sentinel_start_ticks':'1502','sentinel_pgid':'502','leader_pid':'503','leader_start_ticks':'1503','leader_pgid':'503','worker_pid':'504','worker_start_ticks':'1504','worker_pgid':'503','leaf_pid':'505','leaf_start_ticks':'1505','leaf_pgid':'503','group':'503','fixture_root':managedroot}
        obs_case('managed',mh,{'pid':204,'start_ticks':starts[204]},mi,mreq,[502,503])
        for case,host,others,rootpath,groups in (('direct',601,{'child':602},str(runtime/'tmp'/'rhai-sys-test-601-direct_spawn_kill_on_drop_false_preserves_child_and_capture-0'),[]),('managed',701,{'sentinel':702,'leader':703,'worker':704,'leaf':705},str(runtime/'tmp'/'rhai-sys-test-701-managed_spawn_kill_on_drop_false_preserves_group_until_leader_exit-0'),[702,703])):
            marker={'host_pid':host,'host_start_ticks':host+1000,'fixture_root':rootpath}
            parents={'child':host,'sentinel':host,'leader':host,'worker':host+2,'leaf':host+3}
            for name,pid in others.items():
                marker[name+'_pid']=pid; marker[name+'_start_ticks']=pid+1000
                if name!='host': marker[name+'_ppid']=parents[name]
            ids={'host':{'pid':host,'start_ticks':host+1000,'absent':True}}
            ids.update({n:{'pid':pid,'start_ticks':pid+1000,'absent':True} for n,pid in others.items()})
            if case=='direct': marker.update({'child_ppid':host,'child_pgid':host,'alive':'true','challenge_ack':'true','completion_exists':'false'})
            else: marker.update({'sentinel_ppid':host,'sentinel_pgid':702,'leader_ppid':host,'leader_pgid':703,'worker_ppid':703,'worker_pgid':703,'leaf_ppid':704,'leaf_pgid':703,'group':703,'challenge_ack_count':'3','challenge_ok':'1'})
            proof.joinpath(case+'-red-terminal.json').write_text(json.dumps({'case':case,'marker':marker,'terminal_identities':ids,'groups_censused':groups,'fixture_root_absent':True}))
        # Stage exactly the twelve immutable inputs; only their expected local hashes are substituted.
        skill=Path('/Users/hoppworks/projects/agent-skills/tools')
        sources={'source.tar':None,'Cargo.lock.accepted':ROOT/'current-msrv-examples-evidence'/'Cargo.lock','check-linux-current-msrv-examples.py':ROOT/'check-linux-current-msrv-examples.py','archive-build-source.py':ROOT/'archive-build-source.py','drop-false-observer-handshake.patch':PATCH,'drop-false-observer.py':OBSERVER,'linux-drop-false-proof.py':PROOF,'contract.md':HERE/'contract.md','launch.sh':HERE/'launch.sh','runner/tools/run_scoped.py':skill/'run_scoped.py','runner/tools/agentskills/__init__.py':skill/'agentskills'/'__init__.py','runner/tools/agentskills/pyguard.py':skill/'agentskills'/'pyguard.py'}
        sources['source.tar']=None
        import io
        for name,src in sources.items():
            target=stage/name; target.parent.mkdir(parents=True,exist_ok=True)
            target.write_bytes(archive if src is None else Path(src).read_bytes())
        expected={name:hashlib.sha256((stage/name).read_bytes()).hexdigest() for name in sources}
        manifest=''.join(expected[n]+'  '+n+'\n' for n in sorted(expected)); (stage/'input-identities.sha256').write_text(manifest)
        files={x.relative_to(stage).as_posix():hashlib.sha256(x.read_bytes()).hexdigest() for x in stage.rglob('*') if x.is_file()}
        dirs=sorted(x.relative_to(stage).as_posix() for x in stage.rglob('*') if x.is_dir())
        inventory={'files':files,'directories':dirs}
        code=collector.CUSTODY
        code=re.sub(r"expected=\{[^\n]*\}", 'expected='+repr(expected), code, count=1)
        code=code.replace("pathlib.Path('/root/rhai-linux-drop-false-523-20261004')",'pathlib.Path('+repr(str(stage))+')')
        code=code.replace("pathlib.Path('/var/roothome/rhai-linux-drop-false-523-20261004')",'pathlib.Path('+repr(str(stage.resolve()))+')')
        original_read=Path.read_text; original_check=subprocess.check_output; oldargv=list(__import__('sys').argv)
        def localized_read(path,*args,**kwargs):
            if str(path).startswith('/proc/'): raise FileNotFoundError(str(path))
            return original_read(path,*args,**kwargs)
        Path.read_text=localized_read; subprocess.check_output=lambda *a,**k:''; __import__('sys').argv=['custody',str(stage),str(scope),str(stage.resolve()),json.dumps(inventory)]
        def run():
            ns={}; exec(code,ns); return ns
        try: run()
        finally: Path.read_text=original_read; subprocess.check_output=original_check; __import__('sys').argv=oldargv
        # The sample stream is derived from the exact launcher log. The whole isolated
        # consumer must reject absent, malformed, reordered and over-cap samples.
        original_log=(outer/'outer.log').read_text()
        for label,bad_log in (
            ('empty', 'PRIVATE_RUNTIME '+str(runtime)+'\nouter_status=0\n'),
            ('malformed', 'PRIVATE_RUNTIME '+str(runtime)+'\nsample={bad json}\nouter_status=0\n'),
            ('out-of-order', 'PRIVATE_RUNTIME '+str(runtime)+'\n'+'\n'.join(reversed(actual_sample_lines))+'\nouter_status=0\n'),
            ('over-cap', 'PRIVATE_RUNTIME '+str(runtime)+'\nsample='+json.dumps({'monotonic_seconds':.1,'storage_kib':1572864,'rss_kib':1,'descendants':1})+'\nouter_status=0\n')):
            outer.joinpath('outer.log').write_text(bad_log)
            try:
                old=Path.read_text; Path.read_text=localized_read; subprocess.check_output=lambda *a,**k:''; __import__('sys').argv=['custody',str(stage),str(scope),str(stage.resolve()),json.dumps(inventory)]
                try: run()
                except SystemExit: pass
                else: raise AssertionError('full CUSTODY accepted '+label+' resource sample stream')
            finally: Path.read_text=old; subprocess.check_output=original_check; __import__('sys').argv=oldargv; outer.joinpath('outer.log').write_text(original_log)
        # Re-execute the whole code against invalid group and foreign-argv corruption.
        saved=(proof/'managed-observer-readback.json').read_text(); bad=json.loads(saved); bad['groups_censused']=[]; (proof/'managed-observer-readback.json').write_text(json.dumps(bad))
        try:
            old=Path.read_text; Path.read_text=localized_read; subprocess.check_output=lambda *a,**k:''; __import__('sys').argv=['custody',str(stage),str(scope),str(stage.resolve()),json.dumps(inventory)]
            try: run()
            except SystemExit: pass
            else: raise AssertionError('full CUSTODY accepted empty managed group census')
        finally: Path.read_text=old; subprocess.check_output=original_check; __import__('sys').argv=oldargv; (proof/'managed-observer-readback.json').write_text(saved)
        savedrows=(proof/'process-identities.tsv').read_text(); (proof/'process-identities.tsv').write_text(savedrows.replace(helper,str(stage/'other.py')))
        try:
            old=Path.read_text; Path.read_text=localized_read; subprocess.check_output=lambda *a,**k:''; __import__('sys').argv=['custody',str(stage),str(scope),str(stage.resolve()),json.dumps(inventory)]
            try: run()
            except SystemExit: pass
            else: raise AssertionError('full CUSTODY accepted foreign helper argv path')
        finally: Path.read_text=old; subprocess.check_output=original_check; __import__('sys').argv=oldargv; (proof/'process-identities.tsv').write_text(savedrows)
        scoped=savedrows.replace(str(stage/'runner/tools/run_scoped.py'),str(stage/'run_scoped.py'))
        (proof/'process-identities.tsv').write_text(scoped)
        try:
            old=Path.read_text; Path.read_text=localized_read; subprocess.check_output=lambda *a,**k:''; __import__('sys').argv=['custody',str(stage),str(scope),str(stage.resolve()),json.dumps(inventory)]
            try: run()
            except SystemExit: pass
            else: raise AssertionError('full CUSTODY accepted incorrect scoped-supervisor relative path')
        finally: Path.read_text=old; subprocess.check_output=original_check; __import__('sys').argv=oldargv; (proof/'process-identities.tsv').write_text(savedrows)
        direct_saved=(proof/'direct-observer-readback.json').read_text(); direct_bad=json.loads(direct_saved)
        direct_bad['live_observation']['fixture_root']=str(runtime/'tmp'/'rhai-sys-test-401-foreign')
        (proof/'direct-observer-readback.json').write_text(json.dumps(direct_bad))
        try:
            old=Path.read_text; Path.read_text=localized_read; subprocess.check_output=lambda *a,**k:''; __import__('sys').argv=['custody',str(stage),str(scope),str(stage.resolve()),json.dumps(inventory)]
            try: run()
            except SystemExit: pass
            else: raise AssertionError('full CUSTODY accepted foreign fixture root under runtime')
        finally: Path.read_text=old; subprocess.check_output=original_check; __import__('sys').argv=oldargv; (proof/'direct-observer-readback.json').write_text(direct_saved)

def post_retirement_source(collector_path: Path) -> str:
    tree=ast.parse(collector_path.read_text())
    node=next(n for n in tree.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='POST_RETIREMENT' for t in n.targets))
    return ast.literal_eval(node.value)

def probe_post_retirement(collector, collector_path: Path):
    code=post_retirement_source(collector_path)
    if code != collector.POST_RETIREMENT or "physical=pathlib.Path(sys.argv[3])" not in code:
        raise AssertionError('embedded post-retirement source does not bind the physical stage argument')
    with tempfile.TemporaryDirectory(prefix='drop-false-post-retirement-') as td:
        root=Path(td); stage=root/'stage'; scope=root/'scope'; physical=root/'physical'; runtime=scope/'agent-build-test'; proc=root/'proc'
        model={'runtime':str(runtime),'owned_processes':[{'pid':811,'start_ticks':101}],
               'launcher_processes':[{'pid':812,'start_ticks':102}],
               'fixture_identities':[{'pid':813,'start_ticks':103}], 'groups_absent':[91,92]}
        localized=code.replace("pathlib.Path('/proc',str(pid),'stat')",'pathlib.Path('+repr(str(proc))+",str(pid),'stat')")
        def run(value=model, *, ps='1 1\n', stage_arg=None, scope_arg=None, physical_arg=None):
            oldargv=__import__('sys').argv; oldcheck=subprocess.check_output
            __import__('sys').argv=['postcheck',str(stage if stage_arg is None else stage_arg),str(scope if scope_arg is None else scope_arg),str(physical if physical_arg is None else physical_arg),json.dumps(value)]
            subprocess.check_output=lambda *a,**k:ps
            try: exec(localized,{})
            finally: subprocess.check_output=oldcheck; __import__('sys').argv=oldargv
        run()  # full actual postcheck success with all identities absent and groups empty
        for label,value,kwargs,ps in (
            ('malformed identities',{'runtime':str(runtime),'owned_processes':[{'pid':'bad','start_ticks':101}],'groups_absent':[91]}, {},'1 1\n'),
            ('unknown process identity',dict(model,owned_processes=[{'pid':811,'start_ticks':101}]), {},'1 1\n'),
            ('invalid empty groups',dict(model,groups_absent=[]), {},'1 1\n'),
            ('populated owned group',model, {},'7 91\n'),
            ('physical stage remains',model, {},'1 1\n'),
            ('foreign runtime scope',dict(model,runtime=str(root/'foreign'/'runtime')), {},'1 1\n'),
        ):
            if label=='unknown process identity':
                target=proc/'811'; target.mkdir(parents=True); (target/'stat').write_text('malformed\n')
            if label=='physical stage remains': physical.mkdir()
            try:
                try: run(value,ps=ps,**kwargs)
                except (SystemExit,ValueError): pass
                else: raise AssertionError('whole postcheck accepted '+label)
            finally:
                if label=='unknown process identity': shutil.rmtree(proc/'811')
                if label=='physical stage remains': physical.rmdir()
        # Exercise cleanup orchestration: the retirement receipt must be durable
        # before the separate fresh postcheck can fail.
        destination=root/'export'; destination.mkdir(); original_tree=destination/'stage-originals'; original_tree.mkdir()
        (original_tree/'a').write_bytes(b'original'); (original_tree/'empty').mkdir()
        files={'a':hashlib.sha256(b'original').hexdigest()}; directories=['empty']
        readback={'files':files,'directories':directories,'runtime':str(runtime)}
        readback_hash=hashlib.sha256(json.dumps(readback,sort_keys=True).encode()).hexdigest()
        raw_tar=destination.with_name(destination.name+'.stage-originals.tar')
        with tarfile.open(raw_tar,'w:') as tf: tf.add(original_tree/'a',arcname='a'); tf.add(original_tree/'empty',arcname='empty')
        (destination/'independent-readback.json').write_text(json.dumps(readback))
        (destination/'export-manifest.json').write_text(json.dumps({'stage':collector.STAGE,'scope':collector.SCOPE,'files':files,'directories':directories,'readback_sha256':readback_hash,'raw_tar_path':str(raw_tar),'raw_tar_sha256':hashlib.sha256(raw_tar.read_bytes()).hexdigest()}))
        (destination/'fresh-custody-readback.json').write_text(json.dumps({'stage_inventory_still_exact':True,'inventory_sha256':readback_hash}))
        old_inventory=collector.inventory; old_ssh=collector.ssh_json
        calls=[]
        def fake_inventory(): return readback
        def fake_ssh(source, supplied=None):
            calls.append(source)
            if source==collector.CUSTODY: return {'stage_inventory_still_exact':True,'inventory_sha256':readback_hash}
            if source.startswith(collector.CUSTODY+'\n'): return {'stage_absent':True,'scope_absent':True,'removed_files':1,'removed_directories':1}
            if source==collector.POST_RETIREMENT: raise RuntimeError('injected postcheck failure after deletion receipt')
            raise AssertionError('unexpected remote program')
        collector.inventory=fake_inventory; collector.ssh_json=fake_ssh
        try:
            try: collector.cleanup(destination)
            except RuntimeError as exc:
                if 'injected postcheck failure' not in str(exc): raise
            else: raise AssertionError('injected postcheck failure was not observed')
            receipt=json.loads((destination/'remote-retirement.json').read_text())
            if receipt.get('removed_files')!=1 or receipt.get('removed_directories')!=1 or (destination/'remote-cleanup.json').exists():
                raise AssertionError('retirement receipt was not persisted before the failing postcheck')
        finally: collector.inventory=old_inventory; collector.ssh_json=old_ssh

def probe_coupled_green(proof, observer_module, case, *, expect_success, request_before_callback=False, identity_override=Ellipsis, host_parent=None):
    """Call real run_case and real observer; localize only command/proc/ps boundaries."""
    class NoAckDuringCommand(RuntimeError):
        pass
    with tempfile.TemporaryDirectory(prefix='drop-false-coupled-'+case+'-') as td:
        root=Path(td); runtime=root/'runtime'; stage=root/'stage'; runtime.mkdir(); stage.mkdir()
        host=99 if case=='direct' else 199
        cargo_pid=50; cargo_start=600
        fixture=runtime/(case+'-fixture'); directory=runtime/('observer-'+case)
        original_proc=observer_module.proc
        original_ps=observer_module.subprocess.check_output
        original_observe=observer_module.observe
        trace=[]; active={'value':True}; started=threading.Event(); ack_seen_before_return={'value':False}; observer_start_identity={'value':None}
        def proc(pid):
            if not active['value']: raise FileNotFoundError(pid)
            rows={cargo_pid:{'pid':cargo_pid,'ppid':1,'pgid':cargo_pid,'start_ticks':cargo_start,'state':'S'},
                  host:{'pid':host,'ppid':cargo_pid if host_parent is None else host_parent,'pgid':host+50,'start_ticks':700,'state':'S'}}
            if case=='direct': rows[host+1]={'pid':host+1,'ppid':host,'pgid':host+1,'start_ticks':801,'state':'S'}
            else:
                rows.update({host+1:{'pid':host+1,'ppid':host,'pgid':host+1,'start_ticks':801,'state':'S'},
                             host+2:{'pid':host+2,'ppid':host,'pgid':host+2,'start_ticks':802,'state':'S'},
                             host+3:{'pid':host+3,'ppid':host+2,'pgid':host+2,'start_ticks':803,'state':'S'},
                             host+4:{'pid':host+4,'ppid':host+3,'pgid':host+2,'start_ticks':804,'state':'S'}})
            return rows[pid]
        def observe_wrapper(*args):
            observer_start_identity['value']=dict(args[4].get('cargo_process_identity') or {})
            trace.append('observer-start')
            try: return original_observe(*args)
            finally: started.set()
        observer_module.proc=proc
        observer_module.subprocess.check_output=lambda *a,**k:''
        observer_module.observe=observe_wrapper
        class FakeBase:
            RUNTIME=runtime; STAGE=stage
            def __init__(self): self.records=[]; self.record_process_identity=self._record
            def _record(self,label,pid,identity): self.records.append((label,pid,dict(identity) if identity else None)); trace.append('record')
            def run_command(self,label,command,env,expected_status):
                assert env['RHAI_DROP_FALSE_OBSERVER_DIR']==str(directory)
                fixture.mkdir()
                if case=='direct':
                    (fixture/'record.challenge-ack').write_text('ok')
                    fields={'request_id':f'direct-{host}','case':'direct','test_pid':str(host),'test_start_ticks':'700','fixture_root':str(fixture),'child_pid':str(host+1),'child_start_ticks':'801','child_pgid':str(host+1),'challenge_ack':'1','completion':'false'}
                else:
                    for name in ('ack-leader','ack-worker','ack-leaf'): (fixture/name).write_text('ok')
                    fields={'request_id':f'managed-{host}','case':'managed','test_pid':str(host),'test_start_ticks':'700','fixture_root':str(fixture),'sentinel_pid':str(host+1),'sentinel_start_ticks':'801','sentinel_pgid':str(host+1),'leader_pid':str(host+2),'leader_start_ticks':'802','leader_pgid':str(host+2),'worker_pid':str(host+3),'worker_start_ticks':'803','worker_pgid':str(host+2),'leaf_pid':str(host+4),'leaf_start_ticks':'804','leaf_pgid':str(host+2),'group':str(host+2),'challenge_ack_count':'3','challenge_ok':'1'}
                request='\n'.join(f'{k}={v}' for k,v in fields.items())+'\n'
                def write_request(): directory.joinpath(fields['request_id']+'.request').write_text(request)
                if request_before_callback: write_request()
                identity={'pid':cargo_pid,'start_ticks':cargo_start,'ppid':1,'pgid':cargo_pid} if identity_override is Ellipsis else identity_override
                self.record_process_identity('command:'+label,cargo_pid,identity)
                if not request_before_callback: write_request()
                deadline=time.monotonic()+0.65
                ack=directory/(fields['request_id']+'.ack')
                while time.monotonic()<deadline and not ack.exists(): time.sleep(.002)
                if not ack.exists():
                    active['value']=False
                    raise NoAckDuringCommand
                if ack.read_text()!=request+'observer_ack=true\n': raise AssertionError('actual observer ACK bytes differ')
                ack_seen_before_return['value']=True
                if not started.wait(1): raise AssertionError('actual observer did not return after ACK')
                if request_before_callback and trace.index('observer-start')<trace.index('record'):
                    # Observer may be launched only by the post-record identity callback.
                    raise AssertionError('observer thread started before command identity recording')
                if request_before_callback and observer_start_identity['value']!={'pid':cargo_pid,'start_ticks':cargo_start,'ppid':1,'pgid':cargo_pid}:
                    raise AssertionError('request-before-callback thread missed published Cargo identity')
                active['value']=False
                shutil.rmtree(fixture)
                name=proof.DIRECT if case=='direct' else proof.MANAGED
                (stage/(label+'.stdout')).write_text(f'test {name} ... ok\ntest result: ok. 1 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 0.00s\n')
                (stage/(label+'.stderr')).write_text('')
            def read_text(self,path): return Path(path).read_text()
            def write_json(self,path,value): Path(path).write_text(json.dumps(value))
            def verify_pass(self,*args): self.verified=args
        base=FakeBase(); proof.BASE=base; proof.OBS=observer_module
        original_record=base.record_process_identity
        try:
            if expect_success:
                proof.run_case(case,proof.DIRECT if case=='direct' else proof.MANAGED,Path('/fake/cargo'),{},expected=0,handshake=True)
                if not ack_seen_before_return['value'] or not getattr(base,'verified',None): raise AssertionError(case+' GREEN returned without live ACK-before-command-return')
                if trace.index('record')>=trace.index('observer-start'): raise AssertionError(case+' observer start preceded original identity recorder')
                if observer_start_identity['value']!={'pid':cargo_pid,'start_ticks':cargo_start,'ppid':1,'pgid':cargo_pid}: raise AssertionError(case+' callback did not publish full Cargo identity before observer start')
                if base.record_process_identity is not original_record: raise AssertionError('record hook was not restored after successful GREEN')
            else:
                try: proof.run_case(case,proof.DIRECT if case=='direct' else proof.MANAGED,Path('/fake/cargo'),{},expected=0,handshake=True)
                except NoAckDuringCommand: pass
                else: raise AssertionError('unchanged 772 unexpectedly completed coupled GREEN')
                if ack_seen_before_return['value']: raise AssertionError('invalid identity unexpectedly produced ACK before command return')
                partial=json.loads((stage/f'{case}-observer-partial.json').read_text())
                live=partial.get('live',{})
                if identity_override is None:
                    if started.is_set() or observer_start_identity['value'] is not None or 'live' in partial:
                        raise AssertionError('missing Cargo identity started an observer or published live evidence')
                    if 'target Cargo command identity' not in partial.get('error',''):
                        raise AssertionError('missing Cargo identity was not retained as the failure cause')
                    if not base.records or not base.records[-1][0].startswith('command:'):
                        raise AssertionError('missing-identity failure discarded the original identity callback record')
                else:
                    if not started.is_set() or live.get('complete') is not False:
                        raise AssertionError('invalid identity did not retain incomplete live-observer evidence')
                    if 'error' not in live or partial.get('ack_written'):
                        raise AssertionError('invalid identity was acknowledged or its failure cause was lost')
                    if identity_override is not Ellipsis and identity_override.get('start_ticks') == 601 and 'start' not in live['error']:
                        raise AssertionError('wrong Cargo start-time identity was not rejected')
                    if host_parent is not None and 'parent' not in live['error']:
                        raise AssertionError('wrong host parent identity was not rejected')
                if base.record_process_identity is not original_record: raise AssertionError('record hook was not restored after failing GREEN')
        finally:
            observer_module.proc=original_proc; observer_module.subprocess.check_output=original_ps; observer_module.observe=original_observe
            active['value']=False
            proof.BASE=None; proof.OBS=None

def main():
    patch_text = PATCH.read_text()
    observer = load(OBSERVER, 'drop_false_observer_probe')
    rendered = {}
    # Pin actual RED format arguments to the process-identity tuple positions.
    for marker, expected in (
        ('let child_identity = managed_proc_identity(pid as i32)', ['fixture.root.as_script_path()', 'child_identity.3', 'child_identity.1', 'child_identity.2', 'fixture.path("record.complete").exists()']),
        ('let sentinel_identity = managed_proc_identity(sentinel_pid)', ['fixture.root.as_script_path()', 'sentinel_identity.3', 'sentinel_identity.1', 'leader_identity.3', 'leader_identity.1', 'leader_identity.2', 'worker_identity.3', 'worker_identity.1', 'worker_identity.2', 'leaf_identity.3', 'leaf_identity.1', 'leaf_identity.2', 'acks.len()', 'u8::from(challenge_ok)']),
    ):
        region=patch_text.split(marker,1)[1]
        macro=re.search(r'eprintln!\(\"(?:\\.|[^\"\\])*\",(.*?)\);',region,re.S)
        if not macro: raise AssertionError('actual RED format argument list missing after '+marker)
        args=[x.strip() for x in macro.group(1).split(',')]
        if args!=expected: raise AssertionError('actual RED tuple/positional field mapping changed: '+repr(args))
    for case, marker, named, positional in (
        ('direct', '\"direct\",\n+        fixture.root.path()',
         {'pid':'411','alive_after_drop':'true'}, ['812','411','1']),
        ('managed', '\"managed\",\n+        fixture.root.path()',
         {'sentinel_pid':'421','sentinel_pgid':'421','leader':'422','worker':'423','leaf':'424','group':'422','challenge_ok':'1'},
         ['813','814','422','815','422','816','422','3','1']),
    ):
        template = rust_template(patch_text, marker)
        fields = render(template, named, positional)
        if case == 'direct':
            fields = fields.replace('completion=false', 'completion=false')
            required = {'child_pid':'411','child_start_ticks':'812','child_pgid':'411','challenge_ack':'1','completion':'false'}
        else:
            required = {'sentinel_pid':'421','sentinel_start_ticks':'813','sentinel_pgid':'421','leader_pid':'422','leader_start_ticks':'814','leader_pgid':'422',
                        'worker_pid':'423','worker_start_ticks':'815','worker_pgid':'422','leaf_pid':'424','leaf_start_ticks':'816','leaf_pgid':'422','group':'422','challenge_ack_count':'3','challenge_ok':'1'}
        # The patch passes these actual field strings to the actual request writer.
        request = (f'request_id={case}-99\ncase={case}\ntest_pid=99\ntest_start_ticks=700\n'
                   'fixture_root=/tmp/owned-fixture\n' + fields)
        actual = observer.parse_request_bytes(request.encode(), case)
        for key, value in required.items():
            if actual[key] != value: raise AssertionError(f'{case} producer field mismatch: {key}')
        rendered[case] = request
        for bad in (request + 'test_pid=100\n', request.replace('test_start_ticks=700','test_start_ticks=0')):
            try: observer.parse_request_bytes(bad.encode(), case)
            except (ValueError, UnicodeError): pass
            else: raise AssertionError(f'{case} malformed actual-shaped request accepted')
    collector = load(COLLECTOR, 'drop_false_collector_probe')
    probe_post_retirement(collector, COLLECTOR)
    proof = load(PROOF, 'drop_false_proof_probe')
    probe_git_patch_application(proof)
    with tempfile.TemporaryDirectory(prefix='drop-false-export-probe-') as td:
        root = Path(td); runtime = root/'runtime'; stage=runtime/'stage'; evidence=root/'exported'
        source=runtime/'source'; stage.mkdir(parents=True); source.mkdir()
        archive=subprocess.check_output(['git','archive','523608648dcae99bc0f6b46eaf2bb91fa4ecc752'],cwd=ROOT.parents[1])
        with tarfile.open(fileobj=__import__('io').BytesIO(archive), mode='r:') as frozen: frozen.extractall(source)
        test=source/'tests'/'sys_process.rs'; original=test.read_bytes(); test.write_bytes(b'overlaid')
        lock_source=ROOT/'current-msrv-examples-evidence'/'Cargo.lock'
        lock=(source/'Cargo.lock'); lock.write_bytes(lock_source.read_bytes())
        os.environ.update(AGENT_RUNTIME_DIR=str(runtime), PROOF_STAGE=str(ROOT), EXPECTED_PROOF_STAGE=str(root/'stage'), RUSTUP_BIN='/bin/true', TMPDIR=str(runtime/'tmp'))
        base=load(BASE_HELPER,'drop_false_base_probe')
        base.RUNTIME=runtime; base.STAGE=stage; base.EVIDENCE=evidence; base.SOURCE=source
        base.START=time.monotonic(); base.REVISION='523608648dcae99bc0f6b46eaf2bb91fa4ecc752'; base.INTERRUPTED=None
        base.CARGO_MANIFESTS=base.manifest_hashes()
        base.ORIGINAL_EXAMPLES={test:original}
        base.ORIGINAL_EXAMPLE_HASHES={'tests/sys_process.rs':'5836af855f7410213367786e195c0b9b09c0da005cde37244cfa241baf59c4cb'}
        base.INJECTED_EXAMPLE_HASHES={'direct-wrong-expectation':'a'*64}
        base.CONTROL_RESULTS=[]
        for name, status in [('direct-red',101),('managed-red',101),('direct-green',0),('managed-green',0)]:
            (stage/f'{name}.status').write_text(f'{status}\n')
            if status==101: base.verify_control(name,status,status,'named intended assertion', ['named intended assertion'])
            else: base.verify_pass(name,status,'independent child readback','independent child readback')
        base.COMMANDS=[{'name':x,'status':n,'expected_status':n} for x,n in [('direct-red',101),('managed-red',101),('direct-green',0),('managed-green',0)]]
        base.write_json(stage/'commands.json',base.COMMANDS)
        base.write_json(stage/'source-inputs.json',{'revision':'523608648dcae99bc0f6b46eaf2bb91fa4ecc752','archive_sha256':'998c31fab8c3026f292ef13484a8b112da90e5ead1e0288845bffeee9186179b','baseline_test_sha256':'5836af855f7410213367786e195c0b9b09c0da005cde37244cfa241baf59c4cb','observer_patch_sha256':'78d7f123c570e5efb94563b77c737fd4ed97ac9a594090c4a7dba664b461e9dd','test_after_patch_sha256':'1'*64,'cargo_lock_sha256':'2ba4b3a0807e32b613ff2e972b893c3fd2e0923fd91803611963f09e93265425','cargo_manifests_sha256':base.CARGO_MANIFESTS})
        proof.BASE=base
        proof.export()
        validation={'json':json,'re':re}; exec(collector.PACKAGE_VALIDATION,validation)
        result, restoration, rows=validation['validate_package'](evidence)
        if result['status']!=0 or len(rows)!=4 or test.read_bytes()!=original: raise AssertionError('actual exporter/consumer positive failed')
        result_path=evidence/'package-result.json'; original_result=result_path.read_text()
        mutated=json.loads(original_result); mutated['source_revision']='wrong'; result_path.write_text(json.dumps(mutated))
        try: validation['validate_package'](evidence)
        except SystemExit: pass
        else: raise AssertionError('actual consumer accepted mutated source pin')
        result_path.write_text(original_result)
        inputs_path=evidence/'source-inputs.json'; original_inputs=inputs_path.read_text()
        inputs=json.loads(original_inputs); inputs['cargo_manifests_sha256']={'Cargo.toml':'0'*64}; inputs_path.write_text(json.dumps(inputs))
        try: validation['validate_package'](evidence)
        except SystemExit: pass
        else: raise AssertionError('actual consumer accepted mutated manifest provenance')
        inputs_path.write_text(original_inputs)
        status_path=evidence/'direct-green.status'; status_value=status_path.read_text(); status_path.write_text('1\n')
        try: validation['validate_package'](evidence)
        except SystemExit: pass
        else: raise AssertionError('actual consumer accepted wrong named test status')
        status_path.write_text(status_value)
        original_root=Path('/Users/hoppworks/projects/rhai/.worktrees/all-tickets-environment-recovery/.scratch/all-tickets/linux-drop-false-native2-originals')
        original_stage=original_root/'stage-originals'
        original_log=(original_stage/'outer-evidence'/'outer.log').read_bytes()
        original_manifest=json.loads((original_root/'export-manifest.json').read_text())
        if hashlib.sha256(original_log).hexdigest()!='e219e4a6f6fcdc9092763d9d11e5ea22812c80f3f9c85f5534689f79e26c7dbd' or original_manifest['files'].get('outer-evidence/outer.log')!=hashlib.sha256(original_log).hexdigest():
            raise AssertionError('preserved Native2 outer log differs from its independent-readback pin')
        original_proof=original_stage/'proof-evidence'
        original_identity_bytes=(original_proof/'process-identities.tsv').read_bytes()
        if original_manifest['files'].get('proof-evidence/process-identities.tsv')!=hashlib.sha256(original_identity_bytes).hexdigest():
            raise AssertionError('preserved Native2 process identities differ from their independent-readback pin')
        identity_rows=[line.split('\t',5) for line in original_identity_bytes.decode('utf-8').splitlines()[1:]]
        scoped_rows=[row for row in identity_rows if row[0]=='scoped-supervisor']
        expected_scoped='/var/roothome/rhai-linux-drop-false-523-20261004/runner/tools/run_scoped.py'
        if len(scoped_rows)!=1 or expected_scoped not in shlex.split(scoped_rows[0][5]):
            raise AssertionError('preserved Native2 scoped-supervisor argv differs from the exact physical runner path')
        actual_runtime=Path(json.loads((original_proof/'early-runtime-identity.json').read_text())['runtime'])
        if str(actual_runtime)!='/root/.local/share/agent-builds/rhai/linux-drop-false-523-20261004/agent-build-l4b8wpaz':
            raise AssertionError('preserved Native2 logical runtime path changed')
        for case,kind in (('direct','observer'),('managed','observer'),('direct','red'),('managed','red')):
            receipt=json.loads((original_proof/(case+('-observer-readback.json' if kind=='observer' else '-red-terminal.json'))).read_text())
            if kind=='observer':
                root_value=receipt['live_observation']['fixture_root']; host_pid=receipt['live_observation']['host']['pid']
            else:
                root_value=receipt['marker']['fixture_root']; host_pid=receipt['marker']['host_pid']
            alias=Path('/var/roothome') if kind=='observer' else Path('/root')
            test_name='direct_spawn_kill_on_drop_false_preserves_child_and_capture' if case=='direct' else 'managed_spawn_kill_on_drop_false_preserves_group_until_leader_exit'
            expected_fixture=alias/actual_runtime.relative_to('/root')/'tmp'/f'rhai-sys-test-{host_pid}-{test_name}-0'
            if Path(root_value)!=expected_fixture:
                raise AssertionError('preserved Native2 fixture path no longer matches its exact runtime alias/test identity')
        original_lines=original_log.decode('utf-8').splitlines()
        actual_sample_lines=[line for line in original_lines if line.startswith('sample=')]
        if len(actual_sample_lines)!=53:
            raise AssertionError('preserved Native2 launcher log has an unexpected periodic sample count')
        probe_full_custody(collector,evidence,archive,actual_sample_lines)
    # Exercise actual observer live/ACK/terminal consumers and byte-mutation refusal.
    with tempfile.TemporaryDirectory(prefix='drop-false-observer-probe-') as td:
        root=Path(td); runtime=root/'runtime'; runtime.mkdir(); out=root/'evidence'; out.mkdir(); obs=load(OBSERVER,'drop_false_live_probe')
        def run_live(case, fields, identities):
            directory=runtime/('obs-'+case); fixture=runtime/('fixture-'+case); directory.mkdir(); fixture.mkdir()
            for name in (['record.challenge-ack'] if case=='direct' else ['ack-leader','ack-worker','ack-leaf']): (fixture/name).write_text('ok')
            fields['fixture_root']=str(fixture); fields['request_id']=case+'-'+fields['test_pid']; fields['case']=case
            request=directory/(fields['request_id']+'.request'); request.write_text('\n'.join(f'{k}={v}' for k,v in fields.items())+'\n')
            cargo={'pid':50,'ppid':1,'pgid':50,'start_ticks':600,'cmdline':'cargo test'}
            bypid={50:{'pid':50,'ppid':1,'pgid':50,'start_ticks':600,'state':'S'},99:{'pid':99,'ppid':50,'pgid':60,'start_ticks':700,'state':'S'},**identities}
            obs.proc=lambda pid: dict(bypid[pid])
            done=__import__('threading').Event(); result={'cargo_process_identity':cargo}; obs.observe(directory,case,runtime,done,result)
            if not result.get('ack_written') or (directory/(fields['request_id']+'.ack')).read_text()!=request.read_text()+'observer_ack=true\n': raise AssertionError(case+' exact observer ACK failed: '+repr(result))
            shutil.rmtree(fixture); obs.proc=lambda pid: (_ for _ in ()).throw(FileNotFoundError(pid))
            obs.terminal(result,case,out)
            if json.loads((out/(case+'-observer-readback.json')).read_text()).get('fixture_root_absent') is not True: raise AssertionError(case+' terminal readback missing')
        direct_fields={'test_pid':'99','test_start_ticks':'700','child_pid':'100','child_start_ticks':'800','child_pgid':'100','challenge_ack':'1','completion':'false'}
        direct_ids={100:{'pid':100,'ppid':99,'pgid':100,'start_ticks':800,'state':'S'}}
        run_live('direct',direct_fields,direct_ids)
        managed_fields={'test_pid':'99','test_start_ticks':'700','sentinel_pid':'101','sentinel_start_ticks':'801','sentinel_pgid':'101','leader_pid':'102','leader_start_ticks':'802','leader_pgid':'102','worker_pid':'103','worker_start_ticks':'803','worker_pgid':'102','leaf_pid':'104','leaf_start_ticks':'804','leaf_pgid':'102','group':'102','challenge_ack_count':'3','challenge_ok':'1'}
        managed_ids={101:{'pid':101,'ppid':99,'pgid':101,'start_ticks':801,'state':'S'},102:{'pid':102,'ppid':99,'pgid':102,'start_ticks':802,'state':'S'},103:{'pid':103,'ppid':102,'pgid':102,'start_ticks':803,'state':'S'},104:{'pid':104,'ppid':103,'pgid':102,'start_ticks':804,'state':'S'}}
        run_live('managed',managed_fields,managed_ids)
        directory=runtime/'mutated'; fixture=runtime/'fixture-mutated'; directory.mkdir(); fixture.mkdir(); (fixture/'record.challenge-ack').write_text('ok')
        fields={'request_id':'direct-99','case':'direct','test_pid':'99','test_start_ticks':'700','fixture_root':str(fixture),'child_pid':'100','child_start_ticks':'800','child_pgid':'100','challenge_ack':'1','completion':'false'}
        request=directory/'direct-99.request'; original='\n'.join(f'{k}={v}' for k,v in fields.items())+'\n'; request.write_text(original)
        obs.proc=lambda pid: {'pid':pid,'ppid':1 if pid==50 else (50 if pid==99 else 99),'pgid':50 if pid==50 else (60 if pid==99 else 100),'start_ticks':600 if pid==50 else (700 if pid==99 else 800),'state':'S'}
        parse=obs.parse_request_bytes
        def mutate_after_parse(raw, case):
            value=parse(raw,case); request.write_text(original+'test_start_ticks=701\n'); return value
        obs.parse_request_bytes=mutate_after_parse; result={'cargo_process_identity':{'pid':50,'start_ticks':600}}
        obs.observe(directory,'direct',runtime,__import__('threading').Event(),result)
        if 'request bytes changed' not in result.get('error','') or list(directory.glob('*.ack')): raise AssertionError('observer ACK accepted changed request bytes')
    # Exercise actual run_case at its command boundary: Cargo identity alone is not a handshake.
    with tempfile.TemporaryDirectory(prefix='drop-false-run-case-probe-') as td:
        root=Path(td); proof=load(PROOF,'drop_false_run_case_probe'); stage=root/'stage'; runtime=root/'runtime'; stage.mkdir(); runtime.mkdir()
        class FakeBase:
            RUNTIME=runtime; STAGE=stage; record_process_identity=staticmethod(lambda *a: None)
            def run_command(self,label,command,env,expected_status):
                self.record_process_identity('command:'+label,77,{'pid':77,'start_ticks':700})
                (stage/(label+'.stdout')).write_text('test sample ... FAILED\ntest result: FAILED\n')
                (stage/(label+'.stderr')).write_text("direct_drop_after_final_client_drop host_pid=1\nEXPECTED_ASSERTION\nthread 'sample' panicked at tests/sys_process.rs:1:1\n")
            def read_text(self,path): return Path(path).read_text()
            def verify_control(self,*a): pass
            def write_json(self,*a): raise AssertionError('RED case must not publish observer output')
        class FakeObserver:
            def control_terminal(self,stderr,case,evidence):
                if 'direct_drop_after_final_client_drop' not in stderr: raise AssertionError('actual RED emitter marker absent')
        proof.BASE=FakeBase(); proof.OBS=FakeObserver()
        proof.run_case('direct','sample',Path('/bin/cargo'),{},expected=101,assertion='EXPECTED_ASSERTION',handshake=False)
    # Corrected actual coupled GREEN: request on each side of the identity callback.
    coupled_proof=load(PROOF,'drop_false_coupled_green_probe'); coupled_observer=load(OBSERVER,'drop_false_coupled_green_observer')
    for coupled_case in ('direct','managed'):
        probe_coupled_green(coupled_proof,coupled_observer,coupled_case,expect_success=True)
        probe_coupled_green(coupled_proof,coupled_observer,coupled_case,expect_success=True,request_before_callback=True)
    for invalid_case,kwargs,expected_text in (
        ('direct',{'identity_override':None},'target Cargo command identity'),
        ('direct',{'identity_override':{'pid':50,'start_ticks':601,'ppid':1,'pgid':50}},'start'),
        ('managed',{'host_parent':777},'parent'),
    ):
        probe_coupled_green(coupled_proof,coupled_observer,invalid_case,expect_success=False,**kwargs)
    coupled_results={'direct_green_request_after_callback':True,'direct_green_request_before_callback':True,
                     'managed_green_request_after_callback':True,'managed_green_request_before_callback':True,
                     'invalid_cargo_identity_no_ack':True,'wrong_cargo_start_rejected':True,
                     'wrong_host_parent_rejected':True}
    # A later Cargo identity failure must preserve the already-read host as incomplete evidence.
    with tempfile.TemporaryDirectory(prefix='drop-false-partial-probe-') as td:
        root=Path(td); runtime=root/'runtime'; runtime.mkdir(); directory=runtime/'obs'; fixture=runtime/'fixture'; directory.mkdir(); fixture.mkdir()
        (fixture/'record.challenge-ack').write_text('ok')
        fields={'request_id':'direct-99','case':'direct','test_pid':'99','test_start_ticks':'700','fixture_root':str(fixture),'child_pid':'100','child_start_ticks':'800','child_pgid':'100','challenge_ack':'1','completion':'false'}
        (directory/'direct-99.request').write_text('\n'.join(f'{k}={v}' for k,v in fields.items())+'\n')
        obs=load(OBSERVER,'drop_false_partial_probe'); calls=[]
        def fail_after_host(pid):
            calls.append(pid)
            if pid==99: return {'pid':99,'ppid':50,'pgid':60,'start_ticks':700,'state':'S'}
            raise PermissionError(pid)
        obs.proc=fail_after_host; result={'cargo_process_identity':{'pid':50,'start_ticks':600}}
        obs.observe(directory,'direct',runtime,__import__('threading').Event(),result)
        if result.get('live',{}).get('complete') is not False or result['live'].get('host',{}).get('pid')!=99 or 'error' not in result['live'] or result.get('ack_written'):
            raise AssertionError('observer discarded partial host identity or reported success after later read failure')
        # Later managed-leaf denial must retain Cargo, host, sentinel, leader and worker rows.
        managed={'request_id':'managed-99','case':'managed','test_pid':'99','test_start_ticks':'700','fixture_root':str(fixture),'sentinel_pid':'101','sentinel_start_ticks':'801','sentinel_pgid':'101','leader_pid':'102','leader_start_ticks':'802','leader_pgid':'102','worker_pid':'103','worker_start_ticks':'803','worker_pgid':'102','leaf_pid':'104','leaf_start_ticks':'804','leaf_pgid':'102','group':'102','challenge_ack_count':'3','challenge_ok':'1'}
        (directory/'direct-99.request').unlink()
        (directory/'managed-99.request').write_text('\n'.join(f'{k}={v}' for k,v in managed.items())+'\n')
        good={50:{'pid':50,'ppid':1,'pgid':50,'start_ticks':600,'state':'S'},99:{'pid':99,'ppid':50,'pgid':60,'start_ticks':700,'state':'S'},101:{'pid':101,'ppid':99,'pgid':101,'start_ticks':801,'state':'S'},102:{'pid':102,'ppid':99,'pgid':102,'start_ticks':802,'state':'S'},103:{'pid':103,'ppid':102,'pgid':102,'start_ticks':803,'state':'S'}}
        def fail_leaf(pid):
            if pid==104: raise PermissionError(pid)
            return good[pid]
        obs.proc=fail_leaf; result={'cargo_process_identity':{'pid':50,'start_ticks':600}}
        obs.observe(directory,'managed',runtime,__import__('threading').Event(),result)
        live=result.get('live',{}); ids=live.get('identities',{})
        if live.get('complete') is not False or [live.get('cargo',{}).get('pid'),live.get('host',{}).get('pid')]+[ids.get(k,{}).get('pid') for k in ('sentinel','leader','worker')] != [50,99,101,102,103] or 'error' not in live or result.get('ack_written'):
            raise AssertionError('managed later-member failure discarded earlier identities or reported success')
    # Exercise the actual RED terminal consumer against exact patched-emitter markers and corruption.
    with tempfile.TemporaryDirectory(prefix='drop-false-terminal-probe-') as td:
        out=Path(td); obs=load(OBSERVER,'drop_false_terminal_probe'); obs.proc=lambda pid: (_ for _ in ()).throw(FileNotFoundError(pid))
        direct='host_pid=101 host_start_ticks=201 fixture_root='+str(out/'absent-direct')+' child_pid=102 child_start_ticks=202 child_ppid=101 child_pgid=101 alive=true challenge_ack=true completion_exists=false'
        (out/'direct.stderr').write_text('direct_drop_after_final_client_drop '+direct+'\n')
        obs.control_terminal((out/'direct.stderr').read_text(),'direct',out)
        managed='host_pid=301 host_start_ticks=401 fixture_root='+str(out/'absent-managed')+' sentinel_pid=302 sentinel_start_ticks=402 sentinel_ppid=301 sentinel_pgid=302 leader_pid=303 leader_start_ticks=403 leader_ppid=301 leader_pgid=303 worker_pid=304 worker_start_ticks=404 worker_ppid=303 worker_pgid=303 leaf_pid=305 leaf_start_ticks=405 leaf_ppid=304 leaf_pgid=303 group=303 challenge_ack_count=3 challenge_ok=1'
        (out/'managed.stderr').write_text('managed_drop_false_terminal '+managed+'\n')
        obs.control_terminal((out/'managed.stderr').read_text(),'managed',out)
        for bad,reason in ((managed.replace('challenge_ack_count=3','challenge_ack_count=2'),'challenge count'),(managed.replace('group=303','group=999'),'leader group')):
            try: obs.control_terminal('managed_drop_false_terminal '+bad+'\n','managed',out)
            except RuntimeError: pass
            else: raise AssertionError('actual terminal consumer accepted corrupted '+reason)
    # Terminal and RED-control failures retain every earlier successful identity read.
    with tempfile.TemporaryDirectory(prefix='drop-false-terminal-partial-probe-') as td:
        out=Path(td); obs=load(OBSERVER,'drop_false_terminal_partial_probe'); calls=[]
        def fail_second(pid):
            calls.append(pid)
            if len(calls)==1: return {'pid':pid,'ppid':1,'pgid':pid,'start_ticks':999,'state':'S'}
            raise PermissionError(pid)
        obs.proc=fail_second
        live={'host':{'pid':10,'start_ticks':100,'pgid':10},'identities':{'child':{'pid':11,'start_ticks':101,'pgid':11}},'fixture_root':str(out/'gone')}
        try: obs.terminal({'live':live,'ack_written':True},'direct',out)
        except PermissionError: pass
        else: raise AssertionError('terminal observer swallowed later identity permission failure')
        partial=json.loads((out/'direct-observer-readback.partial.json').read_text())
        if partial.get('complete') is not False or [x.get('label') for x in partial.get('terminal_identities',[])]!=['host'] or 'error' not in partial:
            raise AssertionError('terminal partial receipt lost earlier host or error')
        calls.clear()
        red='host_pid=101 host_start_ticks=201 fixture_root='+str(out/'absent-red')+' child_pid=102 child_start_ticks=202 child_ppid=101 child_pgid=101 alive=true challenge_ack=true completion_exists=false'
        try: obs.control_terminal('direct_drop_after_final_client_drop '+red+'\n','direct',out)
        except PermissionError: pass
        else: raise AssertionError('RED control swallowed later identity permission failure')
        partial=json.loads((out/'direct-red-terminal.partial.json').read_text())
        if partial.get('complete') is not False or 'host' not in partial.get('terminal_identities',{}) or 'error' not in partial:
            raise AssertionError('RED control partial receipt lost earlier host or error')
    transport_code='print("line one\\nline two")'
    remote='python3 -c '+shlex.quote(transport_code)+' '+shlex.quote('/tmp/stage with spaces')
    if shlex.split(remote)!=['python3','-c',transport_code,'/tmp/stage with spaces']:
        raise AssertionError('whole-command SSH quoting failed round-trip')
    print(json.dumps({'actual_patch_request_producer':'PASS direct+managed',
                      'exact_523_patch_via_git_apply':'PASS strict precheck and output hash '+PATCHED_TEST_HASH,
                      'baseline_parser_control':'RED direct+managed packed records',
                      'current_parser_malformed_controls':'PASS duplicate+invalid numeric',
                      'actual_exporter_shared_consumer':'PASS four controls + baseline restoration',
                      'actual_RED_terminal_consumer':'PASS direct+managed exact marker, reject challenge mutation',
                      'actual_live_observer':'PASS direct+managed exact ACK+terminal; reject changed request bytes',
                      'consumer_source_pin_mutation':'REJECTED',
                      'consumer_manifest_mutation':'REJECTED', 'consumer_named_status_mutation':'REJECTED',
                      'whole_remote_command_quoting':'PASS',
                      'whole_isolated_CUSTODY':'PASS actual 53 pinned samples and exact fixture roots; reject empty/malformed/reordered/over-cap samples, wrong runner path, foreign fixture, empty groups and foreign argv',
                      'observer_later_member_failure':'PASS retains Cargo, host, sentinel, leader, worker before leaf PermissionError',
                      'coupled_actual_run_case_and_observer':coupled_results},sort_keys=True))

if __name__ == '__main__': main()
