#!/usr/bin/env python3
"""Read-only Workhorse admission and staged-input identity check."""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import platform
import shutil
import sys
import time


SESSION_ID = "x11-env-remove-20261007-1436z-8702248"
SCOPE = Path("/root/.local/share/agent-builds/rhai") / SESSION_ID
STAGE = SCOPE / "stage"
RUNNER = Path("/home/workhorse/projects/agent-skills/tools/run_scoped.py")
EXPECTED_FILES = {
    "Cargo.lock.accepted": "2ba4b3a0807e32b613ff2e972b893c3fd2e0923fd91803611963f09e93265425",
    "input-identities.json": "911bd3c0ffb32bb307265ba6511f203bcb45f20b63386a584d1aaa3eaebc147a",
    "run-env-remove-proof.py": "6a3a3e81acc86e8665daab51b55d3e25806518ee8184c19cb5720474dca43e47",
    "source.tar.gz": "5faabf07990049bfd34272cac294de21a63386803ceefeddcb9262ffb9f05132",
    "sys_process.rs": "b585903b21aa64d3725cd5c1bfb883f71c40104273f928404e1ba86997ba16e7",
}
RUNNER_SHA256 = "25d42cec15827652d08148f51d7f226aa23bbb58ee96ffd68594548044428c2e"
HEAVY_NAMES = {"cargo", "rustc", "flutter", "dart", "cmake", "ninja", "make",
               "gcc", "clang", "cc1", "go", "javac"}


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def active_heavy() -> list[dict[str, object]]:
    found = []
    for entry in Path("/proc").iterdir():
        if not entry.name.isdigit() or int(entry.name) == os.getpid():
            continue
        try:
            raw = (entry / "stat").read_text(encoding="ascii")
            marker = raw.rfind(")")
            comm = raw[raw.index("(") + 1:marker]
            fields = raw[marker + 2:].split()
            if not fields or fields[0] in {"Z", "X", "x"}:
                continue
            argv = [value.decode(errors="replace") for value in
                    (entry / "cmdline").read_bytes().split(b"\0") if value]
            runner = any(Path(value).name == "run_scoped.py" for value in argv[:5])
            if comm not in HEAVY_NAMES and not runner:
                continue
            found.append({"pid": int(entry.name), "comm": comm,
                          "start_ticks": int(fields[19]), "pgid": int(fields[2]),
                          "argv": argv[:6]})
        except (FileNotFoundError, ProcessLookupError):
            continue
        except (PermissionError, OSError, IndexError, ValueError) as exc:
            raise RuntimeError(f"cannot classify process {entry.name}: {exc}") from exc
    return found


def main() -> int:
    phase = sys.argv[1]
    if phase not in {"before", "staged"}:
        raise ValueError("phase must be before or staged")
    if platform.system() != "Linux" or platform.machine() != "x86_64":
        raise RuntimeError("unexpected Workhorse platform")
    resolved_scope = SCOPE.resolve(strict=False)
    home = Path("/root").resolve(strict=True)
    if resolved_scope.parent != (home / ".local/share/agent-builds/rhai").resolve(strict=False):
        raise RuntimeError("Session scope does not resolve under the required central build root")
    if phase == "before":
        if SCOPE.exists() or SCOPE.is_symlink():
            raise RuntimeError("the unique Session scope already exists; preserve it")
        disk_path = Path("/root")
    else:
        if not SCOPE.is_dir() or SCOPE.is_symlink() or not STAGE.is_dir() or STAGE.is_symlink():
            raise RuntimeError("the owned Session scope/stage is missing or not a real directory")
        if SCOPE.stat().st_uid != os.getuid() or SCOPE.stat().st_mode & 0o077:
            raise RuntimeError("Session scope ownership or private permissions changed")
        for name, expected in EXPECTED_FILES.items():
            path = STAGE / name
            if path.is_symlink() or not path.is_file() or sha(path) != expected:
                raise RuntimeError(f"staged input identity mismatch: {name}")
        pins = json.loads((STAGE / "input-identities.json").read_text(encoding="utf-8"))
        if pins["source_revision"] != "8702248b508a7d02b87cb23f70b3853022e11a0e":
            raise RuntimeError("staged source revision differs from the authorized base")
        if sha(RUNNER) != RUNNER_SHA256:
            raise RuntimeError("canonical run_scoped.py identity changed")
        disk_path = STAGE
    mem_available_kib = int(next(line.split()[1] for line in Path("/proc/meminfo").read_text().splitlines()
                                 if line.startswith("MemAvailable:")))
    disk_free_bytes = shutil.disk_usage(disk_path).free
    heavy = active_heavy()
    ready = (mem_available_kib >= 16 * 1024 * 1024
             and disk_free_bytes >= 16 * 1024**3
             and len(heavy) <= 2)
    receipt = {
        "utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "phase": phase,
        "ready": ready,
        "user": os.getuid(),
        "home_resolved": str(home),
        "session_scope": str(SCOPE),
        "session_scope_resolved": str(resolved_scope),
        "mem_available_kib": mem_available_kib,
        "disk_free_bytes": disk_free_bytes,
        "active_heavy": heavy,
        "runner_sha256": sha(RUNNER),
        "input_hashes_verified": len(EXPECTED_FILES) if phase == "staged" else 0,
    }
    print(json.dumps(receipt, indent=2, sort_keys=True))
    if not ready:
        raise RuntimeError("Machine admission failed; do not launch the build")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
