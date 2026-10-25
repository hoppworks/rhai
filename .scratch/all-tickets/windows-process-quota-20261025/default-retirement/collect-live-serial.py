"""Read one bounded libvirt serial export while retaining rotated file handles."""
from pathlib import Path
import hashlib
import json
import os
import time

if not __debug__:
    raise RuntimeError("Optimization disables serial collection checks")

root = Path("/var/roothome/projects/rhai-default-build-retirement-20261025-278b19c6e05ac1725763aa778e031945")
log = Path("/var/log/libvirt/qemu/rhai-win11-quality-serial0.log")
identity = b"RHAI_BOOTSTRAP rhai-default-build-readback-278b19c6e05ac1725763aa778e031945 "
output = root / "serial-all-original.bin"
assert root.is_dir() and not root.is_symlink() and not output.exists()
deadline = time.monotonic() + 200
maximum = 8 * 1024 * 1024
frames = 0
last_sequence = -1
seen_end = False
pending = bytearray()
sources = []

with log.open("rb", buffering=0) as current, output.open("xb", buffering=0) as target:
    current.seek(0, os.SEEK_END)
    source_inode = os.fstat(current.fileno()).st_ino
    source_offset = current.tell()
    sources.append({"inode": source_inode, "start": source_offset})
    print("READY", source_inode, source_offset, flush=True)
    while time.monotonic() < deadline:
        chunk = current.read(65536)
        if chunk:
            if target.tell() + len(chunk) > maximum:
                raise RuntimeError("Serial collection exceeded 8 MiB")
            target.write(chunk)
            pending.extend(chunk)
            while b"\n" in pending:
                line, _, remaining = pending.partition(b"\n")
                pending = bytearray(remaining)
                if not line.startswith(identity):
                    continue
                parts = line.split(b" ", 4)
                if len(parts) != 5:
                    raise RuntimeError("Malformed matching serial frame")
                sequence = int(parts[2])
                if sequence != last_sequence + 1:
                    raise RuntimeError("Serial frame gap or duplicate")
                last_sequence = sequence
                frames += 1
                if parts[3] == b"END":
                    seen_end = True
                    break
            if seen_end:
                break
            continue
        current_inode = log.stat().st_ino
        if current_inode != source_inode:
            with log.open("rb", buffering=0) as next_log:
                next_inode = os.fstat(next_log.fileno()).st_ino
                if next_inode != current_inode:
                    continue
            current.close()
            current = log.open("rb", buffering=0)
            source_inode = os.fstat(current.fileno()).st_ino
            sources.append({"inode": source_inode, "start": 0})
            continue
        time.sleep(0.02)
    target.flush()
    os.fsync(target.fileno())
    current.close()

if not seen_end or frames < 2:
    raise RuntimeError("Completed serial END not observed within 200 seconds")
raw = output.read_bytes()
record = {
    "frames": frames,
    "last_sequence": last_sequence,
    "bytes": len(raw),
    "sha256": hashlib.sha256(raw).hexdigest(),
    "sources": sources,
    "end_seen": True,
    "read_only": True,
}
(root / "serial-collection.json").write_text(json.dumps(record, indent=2) + "\n")
print("COLLECTION_COMPLETE", json.dumps(record), flush=True)
