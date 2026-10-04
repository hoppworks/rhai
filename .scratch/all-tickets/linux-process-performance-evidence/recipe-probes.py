#!/usr/bin/env python3
"""Deterministic parser and custody probes; optional path-normalized originals check is local only."""
from __future__ import annotations
import argparse, hashlib, importlib.util, json, pathlib, re, shutil, subprocess, sys, tarfile, tempfile

ROOT = pathlib.Path(__file__).resolve().parent
parser=argparse.ArgumentParser();parser.add_argument('--preserved-originals',type=pathlib.Path,help='local stage-originals directory for structural consumer regression only');ARGS=parser.parse_args()
spec = importlib.util.spec_from_file_location('measurement_proof', ROOT / 'linux-process-performance-proof.py')
proof = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = proof
spec.loader.exec_module(proof)

def check_rejects(name, fn):
    try:
        fn()
    except (ValueError, KeyError, TypeError):
        return
    raise AssertionError(f'{name} unexpectedly accepted')

rows = []
next_fixture_pid=1_200_000_000
for i in range(5):
    order = ['direct', 'managed'] if i % 2 == 0 else ['managed', 'direct']
    for mode in order:
        next_fixture_pid+=1
        start_pgid=next_fixture_pid if mode=='managed' else 1100
        rows.append(f'PERF_START,index={i},mode={mode},order={order[0]}>{order[1]},pid={next_fixture_pid},start_ticks={2000+i*2+(mode=="managed")},pgid={start_pgid},ready_latency_ns=12345')
for i in range(3):
    order = ['direct', 'managed'] if i % 2 == 0 else ['managed', 'direct']
    for mode in order:
        rows.append(f'PERF_CAPTURE,index={i},mode={mode},order={order[0]}>{order[1]},bytes=1048576,captured_run_elapsed_ns=123456,captured_run_bytes_per_second=8493519958.528')
for mode, pid, pgid, owned in [('direct', 1300000001, 1300000000, 'false'), ('managed', 1300000002, 1300000002, 'true')]:
    rows.append(f'PERF_RESOURCE,sample_index=0,order=direct>managed,mode={mode},pid={pid},start_ticks=4000,pgid={pgid},live_ready_latency_ns=12345,child_threads=1,child_fds=3,host_threads_before=2,host_fds_before=4,host_threads_live=2,host_fds_live=5,group_members=1,group_members_owned={owned}')
    rows.append(f'PERF_RESOURCE_CLOSED,mode={mode},host_threads_after=2,host_fds_after=4,host_threads_delta=0,host_fds_delta=0')
measurement = '\n'.join(rows)
assert proof.validate_measurement_rows(measurement) == {'PERF_START': 10, 'PERF_CAPTURE': 6, 'PERF_RESOURCE': 2, 'PERF_RESOURCE_CLOSED': 2}
controls = '\n'.join([
    'PERF_CONTROL,kind=proc-census,malformed_rejected=true,unreadable_rejected=true,vanished_skipped=true,entry_error_rejected=true',
    'PERF_CONTROL,kind=byte-integrity,captures=1,corrupted_copy_rejected=true',
    'PERF_CONTROL,kind=resource-count,live_fixtures=1,zero_descriptor_control_rejected=true,pid=1400000001,start_ticks=6001',
])
proof.validate_control_receipts(controls)

check_rejects('missing start receipt', lambda: proof.validate_measurement_rows('\n'.join(rows[:-1])))
bad = measurement.replace('mode=direct,order=direct>managed', 'mode=direct,order=managed>direct', 1)
check_rejects('changed alternation label', lambda: proof.validate_measurement_rows(bad))
bad = measurement.replace('captured_run_bytes_per_second=8493519958.528', 'captured_run_bytes_per_second=nan', 1)
check_rejects('nonfinite throughput', lambda: proof.validate_measurement_rows(bad))
bad = measurement.replace('captured_run_bytes_per_second=8493519958.528', 'captured_run_bytes_per_second=8493.459', 1)
check_rejects('incorrect throughput quotient', lambda: proof.validate_measurement_rows(bad))
bad = measurement.replace('host_fds_delta=0', 'host_fds_delta=1', 1)
check_rejects('resource delta detached from same-mode counts', lambda: proof.validate_measurement_rows(bad))
bad = measurement.replace('host_threads_live=2', 'host_threads_live=0', 1)
check_rejects('empty live host count', lambda: proof.validate_measurement_rows(bad))
bad = controls.replace('unreadable_rejected=true', 'unreadable_rejected=false')
check_rejects('unreadable census accepted', lambda: proof.validate_control_receipts(bad))
bad = measurement.replace('group_members_owned=true', 'group_members_owned=false', 1)
check_rejects('wrong group ownership', lambda: proof.validate_measurement_rows(bad))
bad = measurement.replace('pgid=1300000002', 'pgid=1', 1)
check_rejects('managed group mismatch', lambda: proof.validate_measurement_rows(bad))
check_rejects('missing resource control', lambda: proof.validate_control_receipts(controls.splitlines()[0]))
check_rejects('wrong byte control', lambda: proof.validate_control_receipts(controls.replace('corrupted_copy_rejected=true', 'corrupted_copy_rejected=false')))

# Exercise the collector's whole emitted-evidence validator with one bounded fixture.
collector_spec = importlib.util.spec_from_file_location('performance_originals_collector', ROOT / 'collect-originals.py')
collector = importlib.util.module_from_spec(collector_spec)
sys.modules[collector_spec.name] = collector
collector_spec.loader.exec_module(collector)

def check_preserved_originals(stage_originals):
    """Run the whole consumer on local originals; this is structural, not remote custody."""
    if not stage_originals.is_dir() or stage_originals.is_symlink():
        raise ValueError('preserved originals path must be a real stage-originals directory')
    with tempfile.TemporaryDirectory(prefix='linux-process-preserved-originals-') as temporary:
        stage=pathlib.Path(temporary)/'stage';shutil.copytree(stage_originals,stage)
        physical=stage.resolve();scope=pathlib.Path(collector.SCOPE)
        for rel in ('proof-evidence/process-identities.tsv','proof-evidence/early-runtime-identity.json','outer-evidence/launcher-identities.tsv'):
            path=stage/rel
            content=path.read_text().replace('/root/rhai-linux-process-performance-8c0ee-20261004',str(stage)).replace('/var/roothome/rhai-linux-process-performance-8c0ee-20261004',str(stage))
            path.write_text(content)
        for rel in ('proof-evidence/process-identities.tsv','proof-evidence/early-runtime-identity.json'):
            path=stage/rel
            path.write_text(path.read_text().replace(str(stage)+'/runner/tools/run_scoped.py',str(physical)+'/runner/tools/run_scoped.py'))
        code=collector.PROCESS_CHECK.replace('/root/rhai-linux-process-performance-8c0ee-20261004',str(stage)).replace('/var/roothome/rhai-linux-process-performance-8c0ee-20261004',str(stage))
        code=code.replace(f"physical!=pathlib.Path('{stage}')",f"physical!=pathlib.Path('{physical}')")
        def manifest():
            files={p.relative_to(stage).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in stage.rglob('*') if p.is_file()}
            dirs=sorted(p.relative_to(stage).as_posix() for p in stage.rglob('*') if p.is_dir())
            return {'stage':str(stage),'scope':str(scope),'files':files,'directories':dirs}
        def run():
            return subprocess.run([sys.executable,'-c',code,str(stage),str(scope),str(physical),json.dumps(manifest())],text=True,capture_output=True)
        result=run()
        if result.returncode:raise AssertionError('local preserved-original consumer rejected stage: '+result.stderr.strip())
        ids=stage/'proof-evidence/process-identities.tsv';original=ids.read_text();changed=False
        for line in original.splitlines():
            fields=line.split('\t',5)
            if fields[0]=='command:du' and fields[5]:
                fields[5]=fields[5].replace(str(scope),'/tmp/foreign-runtime')
                ids.write_text(original.replace(line,'\t'.join(fields),1));changed=True;break
        if not changed:raise AssertionError('preserved originals have no captured du argv')
        result=run()
        if result.returncode==0 or 'sampler argv/runtime mismatch command:du' not in result.stderr:
            raise AssertionError('local wrong-runtime control did not fail at argv binding: '+result.stderr.strip())
        return {'whole_consumer':'pass on path-normalized preserved originals','wrong_runtime_control':'rejected','remote_custody':False}

preserved_originals_result=check_preserved_originals(ARGS.preserved_originals) if ARGS.preserved_originals else None

# Execute the embedded custody preamble locally with exact path literals remapped to a disposable empty fixture.
admission_root=collector.PREFLIGHT.parent
for allocation_inputs in (11, 10):
    with tempfile.TemporaryDirectory(prefix='linux-process-custody-runtime-') as temporary:
        physical_root=pathlib.Path(temporary).resolve()
        stage=physical_root/'physical-stage';stage.mkdir()
        (stage/'proof-evidence').mkdir()
        scope=physical_root/'absent-scope'
        guard_hash=hashlib.sha256(collector.PREFLIGHT.read_bytes()).hexdigest()
        wrapper_hash=hashlib.sha256(collector.SLOT_WRAPPER.read_bytes()).hexdigest()
        shutil.copy2(collector.PREFLIGHT,stage/'linux-process-performance-preflight.py')
        shutil.copy2(collector.SLOT_WRAPPER,stage/'linux-process-performance-slot-wrapper.py')
        (stage/'native-allocation.json').write_text(json.dumps({'source_revision':proof.REV,'native_launch':1,'preflight_source_sha256':guard_hash,'slot_wrapper_source_sha256':wrapper_hash,'preflight':{'ready':True,'inputs_verified':allocation_inputs,'heavy':[],'scope_absent':True}}))
        code=collector.PROCESS_CHECK.replace('/root/rhai-linux-process-performance-8c0ee-20261004',str(stage)).replace('/var/roothome/rhai-linux-process-performance-8c0ee-20261004',str(stage)).replace('/root/.local/share/agent-builds/rhai/linux-process-performance-8c0ee-20261004',str(scope)).replace('/var/roothome/.local/share/agent-builds/rhai/linux-process-performance-8c0ee-20261004',str(scope))
        inventory={'files':{p.relative_to(stage).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in stage.rglob('*') if p.is_file()},'directories':sorted(p.relative_to(stage).as_posix() for p in stage.rglob('*') if p.is_dir())}
        result=subprocess.run([sys.executable,'-c',code,str(stage),str(scope),str(stage),json.dumps(inventory)],text=True,capture_output=True)
        expected='performance proof originals missing' if allocation_inputs==11 else 'initial admission receipt is not successful'
        assert result.returncode!=0 and expected in result.stderr,(allocation_inputs,result.stdout,result.stderr)
with tempfile.TemporaryDirectory(prefix='linux-process-proof-probe-') as temporary:
    stage_root=pathlib.Path(temporary)
    evidence = stage_root / 'proof-evidence'
    evidence.mkdir()
    runtime=pathlib.Path(temporary)/'agent-build-probe'
    shutil.copy2(ROOT / 'linux-process-performance-proof.py', evidence / 'proof-used.py')
    shutil.copy2(ROOT / 'measurement-contract.md', evidence / 'measurement-contract.md')
    shutil.copy2(ROOT / 'linux_process_performance.rs', evidence / 'linux_process_performance.rs')
    (evidence / 'measurement-result.json').write_text(json.dumps({
        'source_revision': proof.REV, 'archive_sha256': proof.ARCHIVE, 'lock_sha256': proof.LOCK,
        'harness_sha256': proof.TEST, 'features': 'testing-environ,sys',
        'acceptance_claim': False, 'observed_row_counts': proof.validate_measurement_rows(measurement),
        'commands':[], 'controls': [{'name':'control-pass','status':0,'expected_status':0},
                     {'name':'measurements','status':0,'expected_status':0}],
    }))
    source_inputs = {'revision':proof.REV,'source_archive_sha256':proof.ARCHIVE,'lock_sha256':proof.LOCK,
        'base_helper_sha256':proof.BASE_HELPER,'archive_helper_sha256':proof.ARCHIVE_HELPER,
        'measurement_harness_sha256':proof.TEST,'contract_sha256':proof.CONTRACT,
        'test_target':'linux_process_performance','features':'testing-environ,sys','production_source_changed':False}
    (evidence / 'source-inputs.json').write_text(json.dumps(source_inputs))
    (evidence / 'source-restoration.json').write_text(json.dumps({'restored_examples_match_recorded_bytes':True,'cargo_lock_sha256':proof.LOCK,'restored_example_sha256':{'tests/linux_process_performance.rs':proof.TEST}}))
    commands=[]
    for name in ('rustup-install','rustc-version','cargo-version','control-pass','measurements'):
        row={'name':name,'status':0,'expected_status':0,'cwd':str(runtime if name in ('rustup-install','rustc-version','cargo-version') else runtime/'source'),'env_overrides':{}}
        if name in ('control-pass','measurements'):
            common=[str(runtime/'rustup-home/toolchains/1.77.2-x86_64-unknown-linux-gnu/bin/cargo'),'test','--locked','--test','linux_process_performance','--features','testing-environ,sys']
            row['argv']=common+(['measurement_controls_reject_corruption','--','--exact','--nocapture','--test-threads=1'] if name=='control-pass' else ['direct_managed_measurements','--','--exact','--ignored','--nocapture','--test-threads=1'])
        commands.append(row)
    controls_ledger=[{'name':'control-pass','status':0,'expected_status':0},{'name':'measurements','status':0,'expected_status':0}]
    result=json.loads((evidence/'measurement-result.json').read_text());result['commands']=commands;result['controls']=controls_ledger;(evidence/'measurement-result.json').write_text(json.dumps(result))
    (evidence / 'early-runtime-identity.json').write_text(json.dumps({'runtime':str(runtime)}))
    (evidence / 'rustc-version.stdout').write_text('rustc 1.77.2 probe\nhost: x86_64-unknown-linux-gnu\n')
    (evidence / 'cargo-version.stdout').write_text('cargo 1.77.2 probe\n')
    class ProducerBase:
        TOOLCHAIN='1.77.2-x86_64-unknown-linux-gnu';STAGE=evidence
        @staticmethod
        def read_text(path): return path.read_text()
        @staticmethod
        def write_json(path,value): path.write_text(json.dumps(value))
    version_receipt=proof.record_tool_versions(ProducerBase)
    assert json.loads((evidence/'tool-versions.json').read_text())==version_receipt
    (evidence / 'commands.json').write_text(json.dumps(commands));(evidence / 'control-results.json').write_text(json.dumps(controls_ledger))
    (evidence / 'measurements.stdout').write_text(measurement)
    (evidence / 'measurements.stderr').write_text('')
    (evidence / 'control-pass.stdout').write_text(controls)
    (evidence / 'control-pass.stderr').write_text('')
    samples = [{'monotonic_seconds':1.0,'storage_kib':100,'rss_kib':200,'descendants':3}]
    maxima = {'maxima':{'storage_kib':100,'rss_kib':200,'descendants':3},'sample_count':1,'samples_are_periodic_not_continuous_peak':True}
    (evidence / 'resource-samples.jsonl').write_text(json.dumps(samples[0])+'\n')
    (evidence / 'sampled-maxima.json').write_text(json.dumps(maxima))
    accepted_skills=pathlib.Path('/Users/hoppworks/projects/agent-skills/tools')
    staged_names=['source.tar','Cargo.lock.accepted','check-linux-current-msrv-examples.py','archive-build-source.py','linux_process_performance.rs','measurement-contract.md','linux-process-performance-proof.py','launch.sh']
    for name in staged_names: shutil.copy2(ROOT/name,stage_root/name)
    admission_root=collector.PREFLIGHT.parent
    shutil.copy2(admission_root/'linux-process-performance-preflight.py',stage_root/'linux-process-performance-preflight.py')
    shutil.copy2(admission_root/'linux-process-performance-slot-wrapper.py',stage_root/'linux-process-performance-slot-wrapper.py')
    (stage_root/'runner/tools/agentskills').mkdir(parents=True)
    (stage_root/'runner/tools/run_scoped.py').write_bytes((accepted_skills/'run_scoped.py').read_bytes())
    (stage_root/'runner/tools/agentskills/__init__.py').write_bytes(b'')
    (stage_root/'runner/tools/agentskills/pyguard.py').write_bytes((accepted_skills/'agentskills/pyguard.py').read_bytes())
    input_pins={'source.tar':proof.ARCHIVE,'Cargo.lock.accepted':proof.LOCK,'check-linux-current-msrv-examples.py':proof.BASE_HELPER,'archive-build-source.py':proof.ARCHIVE_HELPER,'linux_process_performance.rs':proof.TEST,'measurement-contract.md':proof.CONTRACT,'linux-process-performance-proof.py':hashlib.sha256((ROOT/'linux-process-performance-proof.py').read_bytes()).hexdigest(),'launch.sh':hashlib.sha256((ROOT/'launch.sh').read_bytes()).hexdigest(),'runner/tools/run_scoped.py':'9edd5bc53260c697174552498f6064e65ab821d28838af2291a0cbb6e510c36d','runner/tools/agentskills/__init__.py':'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855','runner/tools/agentskills/pyguard.py':'a3739f4947744303e1adf3fb0875ac743944a272e5b95c94b1baba53029d313f'}
    (stage_root/'input-identities.sha256').write_text(''.join(f'{value}  {name}\n' for name,value in input_pins.items()))
    preflight_hash=hashlib.sha256((admission_root/'linux-process-performance-preflight.py').read_bytes()).hexdigest()
    wrapper_hash=hashlib.sha256((admission_root/'linux-process-performance-slot-wrapper.py').read_bytes()).hexdigest()
    (stage_root/'native-allocation.json').write_text(json.dumps({'source_revision':proof.REV,'native_launch':1,'preflight_source_sha256':preflight_hash,'slot_wrapper_source_sha256':wrapper_hash,'preflight':{'ready':True,'inputs_verified':11,'heavy':[],'scope_absent':True}}))
    corrupted=(evidence/'proof-used.py').read_text()
    (evidence/'proof-used.py').write_text("raise AssertionError('untrusted exported consumer executed')\n")
    check_rejects('whole validator rejects corrupted proof before import', lambda: collector.validate_local(evidence,pathlib.Path(temporary)))
    (evidence/'proof-used.py').write_text(corrupted)
    collector.validate_local(evidence, pathlib.Path(temporary))
    corrupt = measurement.replace('captured_run_bytes_per_second=8493519958.528','captured_run_bytes_per_second=8493.459',1)
    (evidence / 'measurements.stdout').write_text(corrupt)
    check_rejects('whole collector rejects altered throughput', lambda: collector.validate_local(evidence, pathlib.Path(temporary)))
    (evidence / 'measurements.stdout').write_text(measurement)
    (evidence / 'resource-samples.jsonl').write_text(json.dumps({**samples[0],'storage_kib':1572864})+'\n')
    check_rejects('whole collector rejects storage-cap sample', lambda: collector.validate_local(evidence, pathlib.Path(temporary)))
    (evidence / 'resource-samples.jsonl').write_text(json.dumps(samples[0])+'\n')
    bad_admission=json.loads((stage_root/'native-allocation.json').read_text());bad_admission['preflight_source_sha256']='0'*64
    (stage_root/'native-allocation.json').write_text(json.dumps(bad_admission))
    check_rejects('whole collector rejects allocation provenance mismatch', lambda: collector.validate_local(evidence, pathlib.Path(temporary)))
    bad_admission['preflight_source_sha256']=preflight_hash
    (stage_root/'native-allocation.json').write_text(json.dumps(bad_admission))

    # Complete isolated originals fixture drives the actual collector and both
    # embedded custody/retirement programs; only SSH transport is replaced.
    proof_ids=evidence/'process-identities.tsv';outer=stage_root/'outer-evidence';outer.mkdir()
    (outer/'outer-status.txt').write_text('0\n');(outer/'run-scoped.status').write_text('0\n')
    (outer/'runtime-cleanup.tsv').write_text('cleanup_status=0\n');(outer/'scope-cleanup.tsv').write_text('cleanup_status=0\n')
    (outer/'control-pass.stdout').write_text(controls);(outer/'control-pass.stderr').write_text('')
    (proofdir/'measurement-result.json') if False else None
    (evidence/'measurements.stdout').write_text(measurement);(evidence/'measurements.stderr').write_text('')
    runtime=pathlib.Path(temporary)/'absent-scope'/'agent-build-probe'
    (evidence/'early-runtime-identity.json').write_text(json.dumps({'runtime':str(runtime)}))
    header='label\tpid\tppid\tpgid\tstart_ticks\tcmdline\n'
    launcher_pid,runner_pid,sup_pid,helper_pid=1500000001,1500000002,1500000003,1500000004
    rows_id=[('helper',helper_pid,sup_pid,helper_pid,701,f'/usr/bin/python3 {stage_root}/linux-process-performance-proof.py'),
        ('scoped-supervisor',sup_pid,runner_pid,sup_pid,702,f'/usr/bin/python3 {stage_root.resolve()}/runner/tools/run_scoped.py _supervise 1 python3 {stage_root}/linux-process-performance-proof.py')]
    names=('rustup-install','rustc-version','cargo-version','control-pass','measurements')
    for i,name in enumerate(names):rows_id.append((f'command:{name}',1500000100+i,helper_pid,1500000100+i,710+i,f'/usr/bin/python3 {name}'))
    rows_id.extend([('command:du',1500000201,helper_pid,1500000201,720,f'/usr/bin/du -sk {runtime}'),('command:ps',1500000202,helper_pid,1500000202,721,'/bin/ps -e -o pid=,ppid=,rss='),('command:du',1500000203,helper_pid,1500000203,722,f'/usr/bin/du -sk {runtime}'),('command:ps',1500000204,helper_pid,1500000204,723,'/bin/ps -e -o pid=,ppid=,rss=')])
    proof_ids.write_text(header+''.join(f'{a}\t{b}\t{c}\t{d}\t{e}\t{f}\n' for a,b,c,d,e,f in rows_id))
    early={'runtime':str(runtime),'helper':{'pid':helper_pid,'ppid':sup_pid,'pgid':helper_pid,'start_ticks':'701','cmdline':f'/usr/bin/python3 {stage_root}/linux-process-performance-proof.py'},'scoped_supervisor':{'pid':sup_pid,'ppid':runner_pid,'pgid':sup_pid,'start_ticks':'702','cmdline':f'/usr/bin/python3 {stage_root.resolve()}/runner/tools/run_scoped.py _supervise 1 python3 {stage_root}/linux-process-performance-proof.py'}}
    (evidence/'early-runtime-identity.json').write_text(json.dumps(early))
    launcherrows=[('launcher',launcher_pid,1,launcher_pid,700,str(stage_root/'launch.sh')),('run-scoped',runner_pid,launcher_pid,runner_pid,701,f'/usr/bin/python3 {stage_root}/runner/tools/run_scoped.py --timeout 585 -- python3 {stage_root}/linux-process-performance-proof.py')]
    (outer/'launcher-identities.tsv').write_text(header+''.join(f'{a}\t{b}\t{c}\t{d}\t{e}\t{f}\n' for a,b,c,d,e,f in launcherrows))
    with tempfile.TemporaryDirectory(prefix='linux-process-orchestration-') as sandbox:
        physical=pathlib.Path(sandbox)/'stage';shutil.copytree(stage_root,physical)
        scope=pathlib.Path(sandbox)/'absent-scope';dest=pathlib.Path(sandbox)/'originals'
        staged_early=json.loads((physical/'proof-evidence'/'early-runtime-identity.json').read_text())
        staged_early['runtime']=str(scope/'agent-build-probe')
        for key in ('helper','scoped_supervisor'):staged_early[key]['cmdline']=staged_early[key]['cmdline'].replace(str(stage_root.resolve()),str(physical.resolve())).replace(str(stage_root),str(physical))
        (physical/'proof-evidence'/'early-runtime-identity.json').write_text(json.dumps(staged_early))
        ids_path=physical/'proof-evidence'/'process-identities.tsv'
        ids_path.write_text(ids_path.read_text().replace(str(runtime),str(scope/'agent-build-probe')).replace(str(stage_root.resolve()),str(physical.resolve())).replace(str(stage_root),str(physical)))
        id_lines=ids_path.read_text().splitlines();blanked=set()
        for index,line in enumerate(id_lines[1:],1):
            fields=line.split('\t',5)
            if fields[0] in ('command:du','command:ps') and fields[0] not in blanked:
                fields[5]='';id_lines[index]='\t'.join(fields);blanked.add(fields[0])
        ids_path.write_text('\n'.join(id_lines)+'\n')
        launch_path=physical/'outer-evidence'/'launcher-identities.tsv'
        launch_path.write_text(launch_path.read_text().replace(str(stage_root),str(physical)))
        for filename in ('commands.json','measurement-result.json'):
            path=physical/'proof-evidence'/filename
            path.write_text(path.read_text().replace(str(pathlib.Path(temporary)/'agent-build-probe'),str(scope/'agent-build-probe')))
        old=(collector.STAGE,collector.SCOPE,collector.PHYSICAL,collector.inventory,collector.ssh_json,collector.subprocess.check_output)
        collector.STAGE=str(physical);collector.SCOPE=str(scope);collector.PHYSICAL=str(physical.resolve())
        def mapped(code):
            for source,target in (('/root/rhai-linux-process-performance-8c0ee-20261004',str(physical)),('/var/roothome/rhai-linux-process-performance-8c0ee-20261004',str(physical)),('/root/.local/share/agent-builds/rhai/linux-process-performance-8c0ee-20261004',str(scope)),('/var/roothome/.local/share/agent-builds/rhai/linux-process-performance-8c0ee-20261004',str(scope))):code=code.replace(source,target)
            code=code.replace(f"physical!=pathlib.Path('{physical}')",f"physical!=pathlib.Path('{physical.resolve()}')")
            return code
        def live_inventory():
            files={p.relative_to(physical).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in physical.rglob('*') if p.is_file()}
            dirs=sorted(p.relative_to(physical).as_posix() for p in physical.rglob('*') if p.is_dir())
            return {'stage':str(physical),'scope':str(scope),'files':files,'directories':dirs}
        collector.inventory=live_inventory
        real_check_output=subprocess.check_output
        tar_count={'value':0}
        def transport(args,**kwargs):
            if args[:2]==['ssh','workhorse'] and args[2]=='tar':
                tar_count['value']+=1
                import io
                stream=io.BytesIO()
                with tarfile.open(fileobj=stream,mode='w') as archive:
                    for item in sorted(physical.iterdir()):archive.add(item,arcname='./'+item.name,recursive=True)
                return stream.getvalue()
            return real_check_output(args,**kwargs)
        collector.subprocess.check_output=transport
        def execute(code,manifest=None):
            argv=[sys.executable,'-c',mapped(code),str(physical),str(scope),str(physical.resolve())]
            if manifest is not None:argv.append(json.dumps(manifest,sort_keys=True))
            result=subprocess.run(argv,text=True,capture_output=True)
            if result.returncode:raise RuntimeError(result.stderr.strip() or result.stdout.strip())
            return json.loads(result.stdout)
        collector.ssh_json=execute
        try:
            custody=execute(collector.PROCESS_CHECK,live_inventory())
            assert custody['owned_groups_empty'] and custody['public_fixture_identities_absent']==12 and len(custody['managed_fixture_groups'])==6
            original_ids=ids_path.read_text();wrong_ids=[];mutated=False
            for line in original_ids.splitlines():
                fields=line.split('\t',5)
                if fields[0]=='command:du' and fields[5] and not mutated:
                    fields[5]=fields[5].replace(str(scope/'agent-build-probe'),'/tmp/foreign-runtime')
                    mutated=True;line='\t'.join(fields)
                wrong_ids.append(line)
            assert mutated
            ids_path.write_text('\n'.join(wrong_ids)+'\n')
            try:execute(collector.PROCESS_CHECK,live_inventory())
            except RuntimeError as error:assert 'sampler argv/runtime mismatch command:du' in str(error)
            else:raise AssertionError('foreign sampler runtime argv unexpectedly passed custody')
            ids_path.write_text(original_ids)
            bad_group=mapped(collector.PROCESS_CHECK).replace("['/bin/ps','-e','-o','pid=,pgid=']", "['/bin/sh','-c','printf \\\"99 1500000001\\\\n\\\"']")
            result=subprocess.run([sys.executable,'-c',bad_group,str(physical),str(scope),str(physical.resolve()),json.dumps(live_inventory())],text=True,capture_output=True)
            assert result.returncode!=0 and 'owned process groups are nonempty' in result.stderr
            unknown=mapped(collector.PROCESS_CHECK).replace("raw=pathlib.Path('/proc',str(pid),'stat').read_text()", "raise PermissionError('controlled unknown identity read')")
            result=subprocess.run([sys.executable,'-c',unknown,str(physical),str(scope),str(physical.resolve()),json.dumps(live_inventory())],text=True,capture_output=True)
            assert result.returncode!=0 and 'process identity unknown' in result.stderr
            # Fail after the archive is safely preserved, then resume the exact
            # archive and prove the SSH tar exporter was called only once.
            first=[True];actual_execute=collector.ssh_json
            def interrupted(code,manifest=None):
                if code==collector.PROCESS_CHECK and first[0]:first[0]=False;raise RuntimeError('controlled custody interruption')
                return actual_execute(code,manifest)
            collector.ssh_json=interrupted
            try:collector.collect(dest)
            except RuntimeError as error:assert 'controlled custody interruption' in str(error)
            else:raise AssertionError('controlled first custody interruption was not reached')
            assert dest.is_dir() and dest.with_name(dest.name+'.originals.tar').is_file()
            collector.ssh_json=actual_execute
            # Archive already exists; a resumed collection must not request a
            # second remote tar. The first call reached tar through transport.
            collector.collect(dest)
            assert (dest/'fresh-custody-readback.json').is_file() and (dest/'retirement-readback.json').is_file()
            assert tar_count['value']==1,'resume exported a second originals archive'
            assert not physical.exists() and dest.with_name(dest.name+'.originals.tar').is_file()
        finally:
            collector.STAGE,collector.SCOPE,collector.PHYSICAL,collector.inventory,collector.ssh_json,collector.subprocess.check_output=old

# Exercise the actual export exception handler with a JSON-only fake base and
# force a copy failure after its progress receipt has been persisted.
class FailureBase:
    def __init__(self, root):
        self.STAGE=root/'stage';self.EVIDENCE=root/'evidence';self.SOURCE=root/'source'
        self.STAGE.mkdir();self.SOURCE.mkdir()
        (self.STAGE/'original').write_text('x');self.TOOLCHAIN='probe';self.MAXIMA={};self.SAMPLES=[]
        self.ORIGINAL_EXAMPLES={};self.ORIGINAL_EXAMPLE_HASHES={}
    def check_deadline(self, during_export=False): return None
    def restore_example_sources(self): return None
    def manifest_hashes(self): return {}
    def export_destination_is_safe(self): return True
    def write_json(self,path,value): path.write_text(json.dumps(value))
with tempfile.TemporaryDirectory(prefix='linux-process-export-failure-') as temporary:
    fake=FailureBase(pathlib.Path(temporary));old_base=proof.BASE;old_copy=proof.shutil.copy2
    proof.BASE=fake
    proof.shutil.copy2=lambda *args,**kwargs: (_ for _ in ()).throw(OSError('controlled copy fault'))
    try:
        try: proof.export()
        except OSError: pass
        else: raise AssertionError('forced exporter failure unexpectedly passed')
        failure=json.loads((fake.EVIDENCE/'export-failure.json').read_text())
        assert (fake.EVIDENCE/'export-progress.json').is_file()
        assert failure['partial_copy_preserved'] is True and failure['export_progress']==str(fake.EVIDENCE/'export-progress.json')
    finally:
        proof.BASE=old_base;proof.shutil.copy2=old_copy

pins = {
    'source_revision': proof.REV, 'source_archive_sha256': proof.ARCHIVE,
    'lock_sha256': proof.LOCK, 'base_helper_sha256': proof.BASE_HELPER,
    'archive_helper_sha256': proof.ARCHIVE_HELPER,
    'contract_sha256': hashlib.sha256((ROOT / 'measurement-contract.md').read_bytes()).hexdigest(),
    'harness_sha256': hashlib.sha256((ROOT / 'linux_process_performance.rs').read_bytes()).hexdigest(),
    'proof_sha256': hashlib.sha256((ROOT / 'linux-process-performance-proof.py').read_bytes()).hexdigest(),
}
stage_text = (ROOT / 'stage.sh').read_text()
for variable, expected in [('expected_test', proof.TEST), ('expected_contract', proof.CONTRACT)]:
    match=re.search(rf'^{variable}=([0-9a-f]{{64}})$',stage_text,re.M)
    assert match and match.group(1)==expected, f'{variable} pin mismatch'
proof_hash=hashlib.sha256((ROOT/'linux-process-performance-proof.py').read_bytes()).hexdigest()
assert proof_hash in stage_text, 'stage proof-consumer pin mismatch'
assert hashlib.sha256((ROOT/'linux_process_performance.rs').read_bytes()).hexdigest()==proof.TEST
assert hashlib.sha256((ROOT/'measurement-contract.md').read_bytes()).hexdigest()==proof.CONTRACT
for name, expected in [('source.tar', proof.ARCHIVE), ('Cargo.lock.accepted', proof.LOCK), ('check-linux-current-msrv-examples.py', proof.BASE_HELPER), ('archive-build-source.py', proof.ARCHIVE_HELPER)]:
    assert hashlib.sha256((ROOT / name).read_bytes()).hexdigest() == expected, name
blob = subprocess.check_output(['git', 'rev-parse', f'{proof.REV}:src/packages/sys/process/unix.rs'], text=True).strip()
assert blob == 'a80a4fb2e15f1331bd688e79a1d8fa9b8673b4da'
print(json.dumps({'synthetic_measurement_rows': proof.validate_measurement_rows(measurement), 'control_receipts': 3, 'negative_controls':'parser/local validation + altered measurement + admission mismatch + corrupted consumer + foreign sampler runtime + nonempty group + unknown identity + interrupted-export resume', 'collector_orchestration':'valid custody + empty exited sampler cmdline acceptance + wrong-runtime rejection + group/unknown-read rejection + sole-archive resume/retirement', 'preserved_originals_local_regression':preserved_originals_result, 'producer_tool_versions':'actual helper emits bound stdout', 'export_failure':'progress and JSON failure receipt preserved', 'corrupted_consumer':'rejected before import', 'pins': pins, 'native_execution': False}, sort_keys=True))
