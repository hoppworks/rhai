#!/usr/bin/env bash
set -euo pipefail
: "${PROOF_STAGE:?set the exact fresh stage path}"
stage=$PROOF_STAGE
evidence="$stage/evidence"
test -d "$stage" && test ! -L "$stage"
test -d "$evidence" && test ! -L "$evidence"
session_base="$HOME/.local/share/agent-builds/rhai"
session_scope="$session_base/process-overhead-${stage##*/}-$$"
mkdir -p "$session_base"
test ! -e "$session_scope" && test ! -L "$session_scope"
mkdir -m 700 "$session_scope"
test -d "$session_scope" && test ! -L "$session_scope"
test -z "$(find "$session_scope" -mindepth 1 -maxdepth 1 -print -quit)"
exec > >(tee -a "$evidence/outer.log") 2>&1
trap 'rc=$?; printf "%s\n" "$rc" > "$evidence/outer-status.txt"; if rmdir "$session_scope" 2>/dev/null; then printf "session_scope_retired=empty:%s\n" "$session_scope" >> "$evidence/outer.log"; else printf "session_scope_retained_nonempty_or_unavailable=%s\n" "$session_scope" >> "$evidence/outer.log"; fi' EXIT

deadline=$(( $(date -u +%s) + 600 ))
printf 'launch_utc=%s\nlauncher_pid=%s\nlauncher_pgid=%s\nouter_deadline_epoch=%s\n' \
  "$(date -u +%FT%TZ)" "$$" "$(ps -o pgid= -p $$ | tr -d ' ')" "$deadline"

# Record exact launcher identity before starting the scoped runner.
python3 - "$evidence/launcher-identities.tsv" "$$" <<'PY'
import pathlib, sys
out, pid = pathlib.Path(sys.argv[1]), int(sys.argv[2])
raw = pathlib.Path('/proc', str(pid), 'stat').read_text()
f = raw[raw.rfind(')') + 2:].split()
cmd = pathlib.Path('/proc', str(pid), 'cmdline').read_bytes().replace(b'\0', b' ').decode(errors='replace').strip()
out.write_text('label\tpid\tstart_ticks\tppid\tpgid\tcmdline\n' + f'launcher\t{pid}\t{f[19]}\t{f[1]}\t{f[2]}\t{cmd}\n')
PY

TMPDIR="$session_scope" TMP="$session_scope" TEMP="$session_scope" \
PROOF_STAGE="$stage" PROOF_CUSTODY_READY="$evidence/runner-process-identities.ready" PROOF_CUSTODY_HEARTBEAT="$evidence/runner-process-identities.heartbeat" python3 "$stage/runner/tools/run_scoped.py" --timeout 585 -- \
  python3 "$stage/resource-census-proof.py" > "$evidence/driver-outer.log" 2>&1 &
runner_pid=$!
python3 - "$evidence/launcher-identities.tsv" "$runner_pid" <<'PY'
import pathlib, sys, time
out, pid = pathlib.Path(sys.argv[1]), int(sys.argv[2])
for _ in range(500):
    try:
        raw = pathlib.Path('/proc', str(pid), 'stat').read_text()
        f = raw[raw.rfind(')') + 2:].split()
        cmd = pathlib.Path('/proc', str(pid), 'cmdline').read_bytes().replace(b'\0', b' ').decode(errors='replace').strip()
        with out.open('a') as stream:
            stream.write(f'run-scoped\t{pid}\t{f[19]}\t{f[1]}\t{f[2]}\t{cmd}\n')
            stream.flush()
        break
    except FileNotFoundError:
        time.sleep(.01)
else:
    raise SystemExit('could not read back exact run_scoped identity')
PY

# Keep an independent process-tree identity ledger outside run_scoped's
# disposable runtime. The tree scan includes its session leader and detached
# fixture descendants while they still have an owned ancestry path.
python3 - "$runner_pid" "$evidence/runner-process-identities.tsv" "$evidence/launcher-identities.tsv" <<'PY' &
import os, pathlib, signal, sys, tempfile, time
root, out = int(sys.argv[1]), pathlib.Path(sys.argv[2])
ready, heartbeat = out.with_suffix('.ready'), out.with_suffix('.heartbeat')
ledger = pathlib.Path(sys.argv[3])
expected = None
for row in ledger.read_text().splitlines()[1:]:
    f = row.split('\t', 5)
    if len(f) == 6 and f[0] == 'run-scoped' and int(f[1]) == root:
        expected = f[2]
if expected is None or not hasattr(os, 'pidfd_open') or not hasattr(signal, 'pidfd_send_signal'):
    raise SystemExit('missing exact run_scoped start identity or pidfd support')
def ident(pid):
    raw = pathlib.Path('/proc', str(pid), 'stat').read_text()
    f = raw[raw.rfind(')') + 2:].split()
    cmd = pathlib.Path('/proc', str(pid), 'cmdline').read_bytes().replace(b'\0', b' ').decode(errors='replace').strip()
    return (f[19], int(f[1]), int(f[2]), cmd)
def resident_bytes(pid, expected_start, proc_root=pathlib.Path('/proc')):
    proc = proc_root / str(pid)
    try:
        before = (proc / 'stat').read_text()
        before_fields = before[before.rfind(')') + 2:].split()
        if before_fields[19] != expected_start:
            return None
        state = before_fields[0]
        status = (proc / 'status').read_text()
        rss = None
        for line in status.splitlines():
            if line.startswith('VmRSS:'):
                fields = line.split()
                if len(fields) >= 2 and fields[1].isdigit():
                    rss = int(fields[1]) * 1024
                break
        after = (proc / 'stat').read_text()
        after_fields = after[after.rfind(')') + 2:].split()
    except (FileNotFoundError, ProcessLookupError):
        return None
    except PermissionError as error:
        raise RuntimeError(f'cannot read resident memory for owned PID {pid}') from error
    if after_fields[19] != expected_start:
        return None
    if rss is None:
        if state in ('Z', 'X') and after_fields[0] in ('Z', 'X'):
            return 0
        raise RuntimeError(f'could not read resident memory for PID {pid}')
    return rss
def snapshot():
    found = {}
    for p in pathlib.Path('/proc').iterdir():
        if p.name.isdigit():
            try: found[int(p.name)] = ident(int(p.name))
            except (FileNotFoundError, ProcessLookupError, PermissionError, IndexError, ValueError, RuntimeError): pass
    return found
try:
    rootfd = os.pidfd_open(root, 0)
    root_identity = ident(root)
except (FileNotFoundError, ProcessLookupError):
    raise SystemExit('run_scoped exited before process-tree custody began')
if root_identity[0] != expected:
    os.close(rootfd)
    raise SystemExit('run_scoped PID start tick changed after pidfd anchoring')
seen = {}
memory_limit_bytes = 2 * 1024 * 1024 * 1024
next_resource_sample = time.monotonic()
with out.open('w', buffering=1) as stream:
    stream.write('utc_epoch\tpid\tstart_ticks\tppid\tpgid\tcmdline\n')
    with (out.parent / 'process-resource-samples.tsv').open('w', buffering=1) as resources:
        resources.write('utc_epoch\towned_descendants\towned_tree_rss_bytes\n')
        ready.write_text(f'pid={root} start_ticks={root_identity[0]}\n')
        while True:
            # Publish a complete timestamp atomically. The driver reads this file
            # concurrently; truncating it in place creates a false stale-monitor
            # result when a read lands between truncate and write.
            with tempfile.NamedTemporaryFile(mode='w', dir=heartbeat.parent,
                                             prefix=heartbeat.name + '.',
                                             delete=False) as heartbeat_stream:
                heartbeat_tmp = pathlib.Path(heartbeat_stream.name)
                heartbeat_stream.write(f'{time.time():.6f}\n')
                heartbeat_stream.flush()
                os.fsync(heartbeat_stream.fileno())
            os.replace(heartbeat_tmp, heartbeat)
            current = snapshot()
            if current.get(root) is None or current[root][0] != root_identity[0]:
                break
            children = {}
            for pid, value in current.items(): children.setdefault(value[1], []).append(pid)
            owned, todo = set(), [root]
            while todo:
                parent = todo.pop()
                for pid in children.get(parent, ()):
                    if pid not in owned: owned.add(pid); todo.append(pid)
            for pid in sorted(owned):
                value = current.get(pid)
                if value is None: continue
                previous = seen.get(pid)
                if previous is not None and previous[0] != value[0]:
                    signal.pidfd_send_signal(rootfd, signal.SIGTERM)
                    raise SystemExit(f'PID {pid} reused while in runner custody')
                if previous is None or previous != value:
                    seen[pid] = value
                    stream.write(f'{time.time():.3f}\t{pid}\t{value[0]}\t{value[1]}\t{value[2]}\t{value[3]}\n')
                else:
                    seen[pid] = value
            if len(owned) > 16:
                signal.pidfd_send_signal(rootfd, signal.SIGTERM)
                raise SystemExit(f'owned process tree exceeded 16 identities: {len(owned)}')
            sampled_now = time.monotonic()
            if sampled_now >= next_resource_sample:
                rss_bytes = 0
                for pid in owned | {root}:
                    value = current.get(pid)
                    if value is not None:
                        resident = resident_bytes(pid, value[0])
                        if resident is not None:
                            rss_bytes += resident
                resources.write(f'{time.time():.3f}\t{len(owned)}\t{rss_bytes}\n')
                next_resource_sample = sampled_now + 1.0
                if rss_bytes >= memory_limit_bytes:
                    signal.pidfd_send_signal(rootfd, signal.SIGTERM)
                    raise SystemExit(f'owned process-tree sampled RSS reached {rss_bytes} bytes (policy stop {memory_limit_bytes})')
            time.sleep(.1)
print(f'runner_tree_identity_count={len(seen)}')
os.close(rootfd)
PY
monitor_pid=$!

set +e
wait "$runner_pid"
runner_status=$?
wait "$monitor_pid"
monitor_status=$?
set -e
printf '%s\n' "$runner_status" > "$evidence/run-scoped.status"
printf '%s\n' "$monitor_status" > "$evidence/process-monitor.status"
cat "$evidence/driver-outer.log"

# Read back every exact PID/start-tick emitted by the driver, all recorded
# runner identities, and each recorded PGID after scoped cleanup. Never signal
# by stale PID or a group name; cleanup is performed by the driver using exact
# sampled PID/start-tick pairs while it still owns its runtime.
python3 - "$evidence" <<'PY'
import os, pathlib, signal, subprocess, sys, time
e = pathlib.Path(sys.argv[1])
observed = {}
groups = set()
failures = []
rss_samples = []
storage_samples = []
for required, minimum_lines in (
    ('measurement-command-identities.tsv', 2),
    ('runner-process-identities.tsv', 2),
    ('process-resource-samples.tsv', 2),
    ('resource-samples.tsv', 2),
):
    path = e / required
    try:
        complete = path.is_file() and not path.is_symlink() and len(path.read_text(errors='replace').splitlines()) >= minimum_lines
    except OSError as error:
        complete = False
        failures.append(f'cannot inspect required ledger {required}: {error}')
    if not complete:
        failures.append(f'missing or incomplete required identity/resource ledger: {required}')
def read_rows(name):
    path = e / name
    if not path.is_file() or path.is_symlink():
        return []
    try:
        return path.read_text(errors='replace').splitlines()
    except OSError as error:
        failures.append(f'cannot read {name}: {error}')
        return []
command_rows = read_rows('measurement-command-identities.tsv')
if command_rows:
    if (len(command_rows) != 2 or command_rows[0] != 'label\tpid\tstart_ticks\tppid\tpgid\tcmdline'):
        failures.append('measurement command identity ledger lacks exact driver receipt')
    else:
        command_fields = command_rows[1].split('\t', 5)
        if (len(command_fields) != 6 or command_fields[0] != 'measurement-driver'
                or not all(field.isdigit() for field in command_fields[1:5]) or not command_fields[5]):
            failures.append('measurement command identity receipt is malformed')
runner_identity_rows = read_rows('runner-process-identities.tsv')
def valid_runner_identity_row(row):
    fields = row.split('\t', 5)
    return (len(fields) == 6 and fields[0].replace('.', '', 1).isdigit()
            and all(field.isdigit() for field in fields[1:5]))
if runner_identity_rows:
    if runner_identity_rows[0] != 'utc_epoch\tpid\tstart_ticks\tppid\tpgid\tcmdline':
        failures.append('runner process identity ledger has an unexpected header')
    for row in runner_identity_rows[1:]:
        if not valid_runner_identity_row(row):
            failures.append('runner process identity ledger contains a malformed row')
    if len(runner_identity_rows) < 2:
        failures.append('runner process identity ledger contains no exact identities')
runner_resource_rows = read_rows('process-resource-samples.tsv')
if runner_resource_rows:
    if runner_resource_rows[0] != 'utc_epoch\towned_descendants\towned_tree_rss_bytes':
        failures.append('process RSS resource ledger has an unexpected header')
    for row in runner_resource_rows[1:]:
        fields = row.split('\t')
        try:
            if len(fields) != 3:
                raise ValueError('wrong field count')
            float(fields[0]); descendants = int(fields[1]); rss = int(fields[2])
        except ValueError:
            failures.append('malformed or non-numeric process RSS resource sample')
            continue
        rss_samples.append(rss)
        if descendants > 16 or rss < 0 or rss >= 2 * 1024 * 1024 * 1024:
            failures.append('sampled process count or RSS reached its stop limit')
    if not rss_samples:
        failures.append('process RSS resource ledger contains no samples')
storage_rows = read_rows('resource-samples.tsv')
if storage_rows:
    if storage_rows[0] != 'utc_epoch\tsampled_runtime_kib':
        failures.append('private runtime storage ledger has an unexpected header')
    for row in storage_rows[1:]:
        fields = row.split('\t')
        try:
            if len(fields) != 2:
                raise ValueError('wrong field count')
            float(fields[0]); size = int(fields[1])
        except ValueError:
            failures.append('malformed or non-numeric private runtime storage sample')
            continue
        storage_samples.append(size)
        if size < 0 or size >= 1_572_864:
            failures.append('sampled private runtime storage reached its stop limit')
    if not storage_samples:
        failures.append('private runtime storage ledger contains no samples')
launcher_all_rows = read_rows('launcher-identities.tsv')
launcher_rows = launcher_all_rows[1:] if launcher_all_rows else []
launcher_group = None
for row in launcher_rows:
    fields = row.split('\t', 5)
    if len(fields) == 6 and fields[0] == 'launcher' and fields[4].isdigit():
        launcher_group = int(fields[4])
        break
if launcher_group is None:
    failures.append('launcher identity ledger lacks exact launcher group')
for name in ('process-identities.tsv', 'command-identities.tsv', 'measurement-command-identities.tsv'):
    p = e / name
    try:
        if not p.exists():
            continue
        lines = p.read_text(errors='replace').splitlines()
    except OSError as error:
        failures.append(f'cannot read identity ledger {name}: {error}')
        continue
    for line in lines[1:]:
        f = line.split('\t', 5)
        if name == 'process-identities.tsv' and len(f) == 5 and f[0].isdigit():
            pid, start, ppid, pgid = int(f[0]), f[1], f[2], f[3]
        elif name in ('command-identities.tsv', 'measurement-command-identities.tsv') and len(f) == 6 and f[1].isdigit() and f[2].isdigit():
            label, pid, start, ppid, pgid = f[0], int(f[1]), f[2], f[3], f[4]
        else:
            continue
        if start.isdigit() and pgid.isdigit():
            observed[(pid, start)] = (name, int(pgid))
            if launcher_group is not None and int(pgid) != launcher_group:
                groups.add(int(pgid))
for line in runner_identity_rows[1:]:
    f = line.split('\t', 5)
    if len(f) == 6 and f[1].isdigit() and f[2].isdigit() and f[4].isdigit():
        pid, start, pgid = int(f[1]), f[2], int(f[4])
        observed[(pid, start)] = ('runner-process-identities.tsv', pgid)
        if launcher_group is not None and pgid != launcher_group:
            groups.add(pgid)
for line in launcher_rows:
    f = line.split('\t', 5)
    if len(f) != 6:
        failures.append('malformed launcher identity ledger')
        continue
    label, pid, start, ppid, pgid, cmd = f
    if label == 'run-scoped' and pid.isdigit() and start.isdigit() and pgid.isdigit():
        observed[(int(pid), start)] = ('launcher-identities.tsv', int(pgid))
        if launcher_group is not None and int(pgid) != launcher_group:
            groups.add(int(pgid))
    elif label != 'launcher':
        failures.append('unexpected launcher identity row')
alive = []
fds = {}
for (pid, start), (source, pgid) in observed.items():
    try:
        raw = pathlib.Path('/proc', str(pid), 'stat').read_text()
        f = raw[raw.rfind(')') + 2:].split()
        same = f[19] == start
    except (FileNotFoundError, ProcessLookupError):
        same = False
    except PermissionError as error:
        failures.append(f'cannot read exact PID/start identity {pid}/{start}: {error}')
        same = False
    except IndexError:
        failures.append(f'malformed /proc stat for exact PID/start identity {pid}/{start}')
        same = False
    if same:
        alive.append((pid, start, source))
initial_alive = list(alive)
cleanup_actions = []
try:
    run_status = (e / 'run-scoped.status').read_text().strip()
except OSError as error:
    run_status = 'unavailable'
    failures.append(f'cannot read run-scoped status: {error}')
if run_status != '0':
    failures.append(f'run-scoped exited with status {run_status}')
if run_status == '0' and initial_alive:
    failures.append('run-scoped reported success while exact owned identities remained live')
if alive:
    pidfd_available = hasattr(os, 'pidfd_open') and hasattr(signal, 'pidfd_send_signal')
    if not pidfd_available:
        failures.append('pidfd support unavailable for exact identity cleanup')
    for pid, start, source in (alive if pidfd_available else ()):
        fd = None
        transferred = False
        try:
            fd = os.pidfd_open(pid, 0)
            raw = pathlib.Path('/proc', str(pid), 'stat').read_text()
            f = raw[raw.rfind(')') + 2:].split()
            if f[19] != start:
                continue
            signal.pidfd_send_signal(fd, signal.SIGTERM)
            cleanup_actions.append((pid, start, 'SIGTERM'))
            fds[(pid, start)] = fd
            transferred = True
        except (FileNotFoundError, ProcessLookupError):
            continue
        except OSError as error:
            failures.append(f'exact PIDFD cleanup failed for {pid}/{start}: {error}')
        finally:
            if fd is not None and not transferred:
                os.close(fd)
    time.sleep(1)
    for (pid, start), fd in list(fds.items()):
        try:
            raw = pathlib.Path('/proc', str(pid), 'stat').read_text()
            f = raw[raw.rfind(')') + 2:].split()
            if f[19] == start:
                signal.pidfd_send_signal(fd, signal.SIGKILL)
                cleanup_actions.append((pid, start, 'SIGKILL'))
        except (FileNotFoundError, ProcessLookupError):
            pass
        except OSError as error:
            failures.append(f'exact PIDFD kill failed for {pid}/{start}: {error}')
    for fd in fds.values():
        try:
            os.close(fd)
        except OSError as error:
            failures.append(f'could not close owned pidfd: {error}')
    time.sleep(.05)
    alive = []
    for (pid, start), (source, pgid) in observed.items():
        try:
            raw = pathlib.Path('/proc', str(pid), 'stat').read_text()
            f = raw[raw.rfind(')') + 2:].split()
            same = f[19] == start
        except (FileNotFoundError, ProcessLookupError):
            same = False
        except PermissionError as error:
            failures.append(f'cannot read exact PID/start after cleanup {pid}/{start}: {error}')
            same = False
        except IndexError:
            failures.append(f'malformed /proc stat after cleanup for {pid}/{start}')
            same = False
        if same: alive.append((pid, start, source))
try:
    ps = subprocess.run(['ps', '-e', '-o', 'pid=,pgid='], capture_output=True, text=True, timeout=5, check=True).stdout
except (OSError, subprocess.SubprocessError) as error:
    failures.append(f'could not perform bounded PGID readback: {error}')
    ps = ''
group_members = []
for line in ps.splitlines():
    f = line.split()
    if len(f) == 2 and int(f[1]) in groups:
        group_members.append((int(f[0]), int(f[1])))
(e / 'pid-readback.tsv').write_text(
    'observed_exact_pid_start_pairs=' + repr(sorted(observed)) + '\n' +
    'initial_exact_identities_alive=' + repr(initial_alive) + '\n' +
    'exact_cleanup_actions=' + repr(cleanup_actions) + '\n' +
    'matching_identities_alive=' + repr(alive) + '\n' +
    'owned_pgids=' + repr(sorted(groups)) + '\n' +
    'owned_pgid_members_alive=' + repr(sorted(group_members)) + '\n' +
    'sampled_owned_tree_rss_max_bytes=' + str(max(rss_samples) if rss_samples else 'unavailable') + '\n' +
    'sampled_private_runtime_storage_max_kib=' + str(max(storage_samples) if storage_samples else 'unavailable') + '\n' +
    'acceptance_failures=' + repr(failures) + '\n')
if alive or group_members or failures:
    raise SystemExit('cleanup/readback completed with live owned identities or acceptance failures; see pid-readback.tsv')
PY

runtime=$(sed -n 's/^PRIVATE_RUNTIME //p' "$evidence/driver-outer.log" | tail -1)
if [[ -z "$runtime" || -e "$runtime" || -L "$runtime" ]]; then
  printf 'runtime_cleanup_status=1 runtime=%s\n' "$runtime"
  exit 1
fi
printf 'runtime_cleanup_status=0 runtime=%s\n' "$runtime"
if (( monitor_status != 0 )); then
  printf 'process_monitor_status=%s\n' "$monitor_status"
  exit 1
fi
exit "$runner_status"
