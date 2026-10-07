#!/usr/bin/env python3
import hashlib
import json
import os
import platform
import shutil
import subprocess
import sys
from pathlib import Path

scope = Path(sys.argv[1]).resolve(strict=True)
assert str(scope) == "/var/home/workhorse/.local/share/agent-builds/rhai/rhai-process-policy-20261007-800babdf0222466d9fce718cb2c4a559"
assert not scope.is_symlink()
uid = os.stat(scope).st_uid
assert uid == os.getuid(), (uid, os.getuid())
expected = {
    "source.tar": "d4a1378c68ba17eb9e716f0b20d5a912aa64e753404fabd78548fe0fd73707a0",
    "source/Cargo.lock": "2ba4b3a0807e32b613ff2e972b893c3fd2e0923fd91803611963f09e93265425",
    "source/tests/sys_process.rs": "60182121c6bec272e198a791f85f7a3ac5b799d23c2bb347314d945e563ed401",
    "run.sh": "dd51d8279e4848f0da2583b1024d2139a0324a3f4bc4906a41b341094613c55b",
    "run_scoped.py.local": "25d42cec15827652d08148f51d7f226aa23bbb58ee96ffd68594548044428c2e",
}
actual = {}
for rel, digest in expected.items():
    data = (scope / rel).read_bytes()
    actual[rel] = hashlib.sha256(data).hexdigest()
    assert actual[rel] == digest, (rel, actual[rel], digest)
runner = Path("/var/home/workhorse/projects/agent-skills/tools/run_scoped.py")
actual["runner"] = hashlib.sha256(runner.read_bytes()).hexdigest()
assert actual["runner"] == expected["run_scoped.py.local"]
archive_names = set(__import__("tarfile").open(scope / "source.tar").getnames())
required = {"build.template", "Cargo.toml", "tests/sys_process.rs"}
assert required <= archive_names, sorted(required - archive_names)
assert (scope / "source/build.template").is_file()

skills_repo = Path("/var/home/workhorse/projects/agent-skills")
revision = subprocess.check_output(["git", "-C", str(skills_repo), "rev-parse", "HEAD"], text=True).strip()
assert revision == "14617043b70d1ba2d40b720832cbad294fa8c008", revision
status = subprocess.check_output(["git", "-C", str(skills_repo), "status", "--short"], text=True).splitlines()
tracked_status = [line for line in status if not line.startswith("?? .scratch/")]
assert not tracked_status, tracked_status
rule_files = {
    "global": Path("/var/home/workhorse/.agents/AGENTS.md"),
    "campaign": skills_repo / "skills/campaign/SKILL.md",
    "tdd": skills_repo / "vendor/mattpocock--skills/tdd/SKILL.md",
    "e2e-proof": skills_repo / "skills/e2e-proof/SKILL.md",
}
rule_hashes = {name: hashlib.sha256(path.read_bytes()).hexdigest() for name, path in rule_files.items()}
assert rule_hashes == {
    "global": "81b103fac482171e3ea72e23d6c0dffac553359f3f75f610506e00c182d1f277",
    "campaign": "342885a50ec612bed6f43876457ec234f4a5784c5a94abdce592383987ce0d61",
    "tdd": "cb01f66bebfaa25fa1f88e6b7e769cd9fd9f35b1120b8563749820738814c927",
    "e2e-proof": "7f3f4d2c273e53bd89883e6254285b95aebc53976299c04d103d22be59846459",
}, rule_hashes

heavy_names = {"cargo", "rustc", "cmake", "ninja", "make", "gcc", "clang", "cc1", "go", "javac"}
heavy = []
for proc in Path("/proc").iterdir():
    if not proc.name.isdigit() or int(proc.name) == os.getpid():
        continue
    try:
        argv = [item.decode(errors="replace") for item in (proc / "cmdline").read_bytes().split(b"\0") if item]
        comm = (proc / "comm").read_text().strip()
    except (FileNotFoundError, ProcessLookupError):
        continue
    if comm in heavy_names or any(Path(arg).name == "run_scoped.py" for arg in argv):
        heavy.append({"pid": int(proc.name), "comm": comm, "argv": argv[:5]})
meminfo = Path("/proc/meminfo").read_text().splitlines()
mem_available = int(next(line.split()[1] for line in meminfo if line.startswith("MemAvailable:")))
disk_free = shutil.disk_usage(scope).free
load = os.getloadavg()
assert not heavy, heavy
assert mem_available >= 16 * 1024 * 1024, mem_available
assert disk_free >= 16 * 1024**3, disk_free
assert platform.system() == "Linux" and platform.machine() == "x86_64"
assert sorted(path.name for path in scope.iterdir()) == ["remote-preflight.py", "run.sh", "run_scoped.py.local", "source", "source.tar"]

result = {
    "ready": True,
    "utc_epoch": int(__import__("time").time()),
    "agent_skills_revision": revision,
    "agent_skills_untracked_scratch": status,
    "rule_hashes": rule_hashes,
    "inputs": actual,
    "archive_entries": len(archive_names),
    "active_heavy_processes": heavy,
    "mem_available_kib": mem_available,
    "disk_free_bytes": disk_free,
    "load": load,
    "machine": {"system": platform.system(), "release": platform.release(), "machine": platform.machine()},
    "scope_owner_uid": uid,
    "scope_entries": sorted(path.name for path in scope.iterdir()),
    "cargo_version": subprocess.check_output(["/home/linuxbrew/.linuxbrew/opt/rustup/bin/cargo", "--version"], text=True).strip(),
    "rustc_version": subprocess.check_output(["/home/linuxbrew/.linuxbrew/opt/rustup/bin/rustc", "--version"], text=True).strip(),
}
print(json.dumps(result, indent=2, sort_keys=True))
