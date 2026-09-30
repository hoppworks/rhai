#!/usr/bin/env python3
import os
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

stage = Path(sys.argv[1])
revision = sys.argv[2]
script = stage / "run-native.sh"
log = (stage / "runner.log").open("wb")
env = os.environ.copy()
env.update(PROOF_STAGE=str(stage), SOURCE_REVISION=revision)
runner = stage / "runner" / "run_scoped.py"
started = datetime.now(timezone.utc).isoformat()
proc = subprocess.Popen([sys.executable, str(runner), "--timeout", "900", "--", "bash", str(script)], env=env, stdout=log, stderr=subprocess.STDOUT)
pids = {proc.pid}

def descendants(roots):
    parents = {}
    for item in os.listdir("/proc"):
        if item.isdigit():
            try:
                raw = Path("/proc", item, "stat").read_text()
                fields = raw[raw.rfind(")") + 2 :].split()
                parents[int(item)] = int(fields[1])
            except (OSError, ValueError, IndexError):
                pass
    found = set(roots)
    while True:
        new = found | {pid for pid, parent in parents.items() if parent in found}
        if new == found:
            return found
        found = new

while proc.poll() is None:
    pids.update(descendants(pids))
    time.sleep(0.1)
rc = proc.wait()
log.close()
evidence = stage / "evidence" / "native-linux-net-release.log"
runtime = ""
if evidence.exists():
    for line in evidence.read_text(errors="replace").splitlines():
        if line.startswith("Runtime directory: "):
            runtime = line.split(": ", 1)[1]
            break
absent_pids = sorted(pid for pid in pids if not Path("/proc", str(pid)).exists())
present_pids = sorted(pids - set(absent_pids))
runtime_absent = bool(runtime) and not Path(runtime).exists()
end = datetime.now(timezone.utc).isoformat()
(stage / "runner-result.txt").write_text(
    f"start_utc={started}\nend_utc={end}\nlauncher_pid={proc.pid}\n"
    f"captured_descendant_pids={','.join(map(str, sorted(pids)))}\n"
    f"absent_pids_after_completion={','.join(map(str, absent_pids))}\n"
    f"still_present_pids_after_completion={','.join(map(str, present_pids))}\n"
    f"runtime_directory={runtime}\nruntime_absent_after_completion={runtime_absent}\n"
    f"stage_directory={stage}\nrunner_status={rc}\n"
)
sys.exit(rc)
