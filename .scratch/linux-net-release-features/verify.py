#!/usr/bin/env python3
import os
import signal
import subprocess
import sys
import time
from pathlib import Path

source, runtime, revision, stage = map(Path, sys.argv[1:])
log_path = Path(os.environ["PROOF_LOG"])
status_path = Path(os.environ["PROOF_STATUS"])
stage_evidence = stage / "evidence"
log = []
statuses = []
max_sockets = 0
max_disk = 0
disk_cap = 1_610_612_736  # 1.5 GiB, below the 2 GiB hard package cap


def descendants(root):
    parents = {}
    for item in os.listdir("/proc"):
        if not item.isdigit():
            continue
        try:
            raw = Path("/proc", item, "stat").read_text()
            fields = raw[raw.rfind(")") + 2 :].split()
            parents[int(item)] = int(fields[1])
        except (OSError, ValueError, IndexError):
            continue
    found = {root}
    while True:
        extra = {pid for pid, parent in parents.items() if parent in found}
        new = found | extra
        if new == found:
            return found
        found = new


def allocated_bytes(root):
    total = 0
    for current, dirs, files in os.walk(root, followlinks=False):
        dirs[:] = [name for name in dirs if not os.path.islink(os.path.join(current, name))]
        for name in dirs + files:
            try:
                total += os.stat(os.path.join(current, name), follow_symlinks=False).st_blocks * 512
            except OSError:
                pass
    return total


def record(label, command, expected=0, env=None, check=None):
    global max_sockets, max_disk
    line = f"\n===== {label} =====\nCommand: {' '.join(map(str, command))}\n"
    log.append(line)
    output_path = runtime / f"{label}.out"
    child_env = os.environ.copy()
    if env:
        child_env.update(env)
    with output_path.open("wb") as output:
        proc = subprocess.Popen(command, cwd=source, env=child_env, stdout=output,
                                stderr=subprocess.STDOUT, start_new_session=True)
        next_disk = 0.0
        capped = False
        while proc.poll() is None:
            pids = descendants(proc.pid)
            sockets = 0
            for pid in pids:
                try:
                    for fd in os.listdir(f"/proc/{pid}/fd"):
                        try:
                            sockets += Path(f"/proc/{pid}/fd/{fd}").is_symlink() and os.readlink(f"/proc/{pid}/fd/{fd}").startswith("socket:[")
                        except OSError:
                            pass
                except OSError:
                    pass
            max_sockets = max(max_sockets, sockets)
            now = time.monotonic()
            if now >= next_disk:
                max_disk = max(max_disk, allocated_bytes(runtime))
                if max_disk >= disk_cap:
                    capped = True
                    os.killpg(proc.pid, signal.SIGTERM)
                    break
                next_disk = now + 1.0
            time.sleep(0.1)
        try:
            rc = proc.wait(timeout=2)
        except subprocess.TimeoutExpired:
            os.killpg(proc.pid, signal.SIGKILL)
            rc = proc.wait()
        if capped:
            log.append(f"PREEMPTIVE STOP: sampled private runtime reached {max_disk} bytes (cap {disk_cap}).\n")
            rc = 125
    data = output_path.read_text(errors="replace")
    log.append(data)
    statuses.append(f"{label}\t{rc}\texpected={expected}\n")
    (stage_evidence / f"{label}.log").write_text(data)
    log_path.write_text("".join(log))
    status_path.write_text("".join(statuses))
    (stage_evidence / "status.tsv").write_text("".join(statuses))
    (stage_evidence / "native-linux-net-release.log").write_text("".join(log))
    if rc != expected:
        raise RuntimeError(f"{label}: status {rc}, expected {expected}")
    if check and not check(data):
        raise RuntimeError(f"{label}: expected assertion evidence absent")


def cargo(label, features, target, exact=None, expected=0, env=None):
    cmd = ["cargo", "test", "--locked", "--jobs", "2", "--features", features, "--test", target]
    if exact:
        cmd += [exact, "--", "--exact", "--test-threads=1", "--nocapture"]
    else:
        cmd += ["--", "--test-threads=1", "--nocapture"]
    record(label, cmd, expected, env)


log.append(f"Source revision: {revision}\nRuntime directory: {runtime}\nLauncher PID: {os.getppid()}\n")
log.append(subprocess.run(["uname", "-a"], capture_output=True, text=True, check=True).stdout)
log.append(Path("/etc/os-release").read_text())
log.append(subprocess.run(["rustc", "--version", "--verbose"], capture_output=True, text=True, check=True).stdout)
log.append(subprocess.run(["cargo", "--version", "--verbose"], capture_output=True, text=True, check=True).stdout)
log.append(f"Private runtime disk cap: {2**31} bytes; preemptive stop: {disk_cap} bytes; sampling interval: 1s.\n")
log.append(f"Socket descriptor cap: 16; jobs: 2; test threads: 1; Cargo debug: 0; incremental: 0.\n")

record("generate-lockfile", ["cargo", "generate-lockfile"])
lock_hash = subprocess.run(["sha256sum", "Cargo.lock"], cwd=source, capture_output=True, text=True, check=True).stdout
log.append(f"Generated lockfile: {lock_hash}")

targets = ("net_connect", "net_listen", "net_reads", "net_writes")
rows = (
    ("net,metadata,serde", True),
    ("net,only_i32,no_float", False),
    ("net,unchecked", False),
    ("net,no_index,sync,metadata", False),
    ("net,f32_float", False),
)
for features, metadata in rows:
    slug = features.replace(",", "_")
    for target in targets:
        cargo(f"{slug}-{target}", features, target)
    if metadata:
        cargo(f"{slug}-net_metadata", features, "net_metadata")

cargo("net_no_object-dedicated", "net,no_object", "net_no_object")
cargo("net_no_object_metadata-serde", "net,no_object,metadata,serde", "net_metadata")

wrong = "net,f32_float"
cargo("wrong-peer-byte-control", wrong, "net_writes", "script_write_blob_preserves_exact_bytes", 101,
      {"RHAI_NET_WRONG_WRITE_EXPECTATION": "1"})
wrong_output = (runtime / "wrong-peer-byte-control.out").read_text(errors="replace")
if "left: [0, 255, 65]" not in wrong_output or "right: [0, 254, 65]" not in wrong_output or "script_write_blob_preserves_exact_bytes" not in wrong_output:
    raise RuntimeError("wrong-peer-byte control did not fail at the intended independent peer assertion")
cargo("restored-peer-byte-readback", wrong, "net_writes", "script_write_blob_preserves_exact_bytes")

if max_sockets > 16:
    raise RuntimeError(f"sampled socket descriptors {max_sockets} exceeded 16")
if max_disk >= disk_cap:
    raise RuntimeError(f"sampled runtime storage {max_disk} reached preemptive cap {disk_cap}")
log.append(f"\nSampled maxima (not true peaks): socket_fds={max_sockets}; private_disk_bytes={max_disk}.\n")
log.append(f"Final runtime allocated bytes: {allocated_bytes(runtime)}\n")
log.append(f"Source working-tree status:\n{(subprocess.run(['git', 'status', '--short'], cwd=source, capture_output=True, text=True).stdout)}\n")
log_path.write_text("".join(log))
status_path.write_text("".join(statuses))
for name, content in (("native-linux-net-release.log", "".join(log)), ("status.tsv", "".join(statuses))):
    (stage_evidence / name).write_text(content)
print(log_path.read_text())
print(status_path.read_text())
