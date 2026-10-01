#!/usr/bin/env bash
set -euo pipefail
: "${PROOF_STAGE:?set the exact fresh stage path}"
stage=$PROOF_STAGE
evidence="$stage/evidence"
test -d "$stage" && test ! -L "$stage"
test -d "$evidence" && test ! -L "$evidence"
exec > >(tee -a "$evidence/outer.log") 2>&1
trap 'rc=$?; printf "%s\n" "$rc" > "$evidence/outer-status.txt"' EXIT

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

PROOF_STAGE="$stage" PROOF_CUSTODY_READY="$evidence/runner-process-identities.ready" PROOF_CUSTODY_HEARTBEAT="$evidence/runner-process-identities.heartbeat" python3 "$stage/runner/tools/run_scoped.py" --timeout 585 -- \
  python3 "$stage/linux-process-proof.py" > "$evidence/driver-outer.log" 2>&1 &
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
def snapshot():
    found = {}
    for p in pathlib.Path('/proc').iterdir():
        if p.name.isdigit():
            try: found[int(p.name)] = ident(int(p.name))
            except (FileNotFoundError, ProcessLookupError, PermissionError, IndexError, ValueError): pass
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
with out.open('w', buffering=1) as stream:
    stream.write('utc_epoch\tpid\tstart_ticks\tppid\tpgid\tcmdline\n')
    ready.write_text(f'pid={root} start_ticks={root_identity[0]}\n')
    while True:
        # Publish a complete timestamp atomically. The driver reads this file
        # concurrently; truncating it in place creates a false stale-monitor
        # result when a read lands between truncate and write.
        with tempfile.NamedTemporaryFile(mode='w', dir=heartbeat.parent,
                                         prefix=heartbeat.name + '.',
                                         delete=False) as stream:
            heartbeat_tmp = pathlib.Path(stream.name)
            stream.write(f'{time.time():.6f}\n')
            stream.flush()
            os.fsync(stream.fileno())
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
        if len(owned) > 16:
            signal.pidfd_send_signal(rootfd, signal.SIGTERM)
            raise SystemExit(f'owned process tree exceeded 16 identities: {len(owned)}')
        for pid in sorted(owned):
            value = current.get(pid)
            if value is None: continue
            previous = seen.get(pid)
            if previous is not None and previous[0] != value[0]:
                signal.pidfd_send_signal(rootfd, signal.SIGTERM)
                raise SystemExit(f'PID {pid} reused while in runner custody')
            if previous != value:
                seen[pid] = value
                stream.write(f'{time.time():.3f}\t{pid}\t{value[0]}\t{value[1]}\t{value[2]}\t{value[3]}\n')
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
launcher_rows = (e / 'launcher-identities.tsv').read_text().splitlines()[1:]
launcher_group = next(int(row.split('\t')[4]) for row in launcher_rows if row.split('\t', 1)[0] == 'launcher')
for name in ('process-identities.tsv', 'command-identities.tsv'):
    p = e / name
    if not p.exists():
        continue
    for line in p.read_text(errors='replace').splitlines()[1:]:
        f = line.split('\t', 5)
        if name == 'process-identities.tsv' and len(f) == 5 and f[0].isdigit():
            pid, start, ppid, pgid = int(f[0]), f[1], f[2], f[3]
        elif name == 'command-identities.tsv' and len(f) == 6 and f[1].isdigit() and f[2].isdigit():
            label, pid, start, ppid, pgid = f[0], int(f[1]), f[2], f[3], f[4]
        else:
            continue
        if start.isdigit() and pgid.isdigit():
            observed[(pid, start)] = (name, int(pgid))
            if int(pgid) != launcher_group:
                groups.add(int(pgid))
for line in (e / 'runner-process-identities.tsv').read_text(errors='replace').splitlines()[1:]:
    f = line.split('\t', 5)
    if len(f) == 6 and f[1].isdigit() and f[2].isdigit() and f[4].isdigit():
        pid, start, pgid = int(f[1]), f[2], int(f[4])
        observed[(pid, start)] = ('runner-process-identities.tsv', pgid)
        if pgid != launcher_group:
            groups.add(pgid)
for line in launcher_rows:
    f = line.split('\t', 5)
    if len(f) != 6:
        raise SystemExit('malformed launcher identity ledger')
    label, pid, start, ppid, pgid, cmd = f
    if label == 'run-scoped' and start.isdigit() and pgid.isdigit():
        observed[(int(pid), start)] = ('launcher-identities.tsv', int(pgid))
        if int(pgid) != launcher_group:
            groups.add(int(pgid))
    elif label != 'launcher':
        raise SystemExit('unexpected launcher identity row')
alive = []
fds = {}
for (pid, start), (source, pgid) in observed.items():
    try:
        raw = pathlib.Path('/proc', str(pid), 'stat').read_text()
        f = raw[raw.rfind(')') + 2:].split()
        same = f[19] == start
    except (FileNotFoundError, ProcessLookupError, PermissionError, IndexError):
        same = False
    if same:
        alive.append((pid, start, source))
failed_run = (e / 'run-scoped.status').read_text().strip() != '0'
if alive and failed_run:
    if not hasattr(os, 'pidfd_open') or not hasattr(signal, 'pidfd_send_signal'):
        raise SystemExit('pidfd support unavailable for exact interrupted-launch cleanup')
    for pid, start, source in alive:
        fd = None
        transferred = False
        try:
            fd = os.pidfd_open(pid, 0)
            raw = pathlib.Path('/proc', str(pid), 'stat').read_text()
            f = raw[raw.rfind(')') + 2:].split()
            if f[19] != start:
                continue
            signal.pidfd_send_signal(fd, signal.SIGTERM)
            fds[(pid, start)] = fd
            transferred = True
        except (FileNotFoundError, ProcessLookupError):
            continue
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
        except (FileNotFoundError, ProcessLookupError):
            pass
    for fd in fds.values(): os.close(fd)
    time.sleep(.05)
    alive = []
    for (pid, start), (source, pgid) in observed.items():
        try:
            raw = pathlib.Path('/proc', str(pid), 'stat').read_text()
            f = raw[raw.rfind(')') + 2:].split()
            same = f[19] == start
        except (FileNotFoundError, ProcessLookupError, PermissionError, IndexError):
            same = False
        if same: alive.append((pid, start, source))
ps = subprocess.check_output(['ps', '-e', '-o', 'pid=,pgid='], text=True)
group_members = []
for line in ps.splitlines():
    f = line.split()
    if len(f) == 2 and int(f[1]) in groups:
        group_members.append((int(f[0]), int(f[1])))
(e / 'pid-readback.tsv').write_text(
    'observed_exact_pid_start_pairs=' + repr(sorted(observed)) + '\n' +
    'matching_identities_alive=' + repr(alive) + '\n' +
    'owned_pgids=' + repr(sorted(groups)) + '\n' +
    'owned_pgid_members_alive=' + repr(sorted(group_members)) + '\n')
if alive or group_members:
    raise SystemExit('exact observed PID/start identity or owned process group remains live')
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
