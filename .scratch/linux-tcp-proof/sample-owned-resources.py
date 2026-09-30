#!/usr/bin/env python3
"""Sample private runtime disk use and descendant socket descriptors."""
import os
import sys
import time

root_pid = int(sys.argv[1])
runtime = sys.argv[2]
output = sys.argv[3]


def process_tree(root):
    parents = {}
    for item in os.listdir("/proc"):
        if not item.isdigit():
            continue
        try:
            raw = open(f"/proc/{item}/stat", "r", encoding="ascii").read()
            fields = raw[raw.rfind(")") + 2 :].split()
            parents[int(item)] = int(fields[1])
        except (OSError, ValueError, IndexError):
            pass
    found = {root}
    changed = True
    while changed:
        changed = False
        for pid, parent in parents.items():
            if parent in found and pid not in found:
                found.add(pid)
                changed = True
    return found


def allocated_bytes(path):
    total = 0
    for current, dirs, files in os.walk(path, followlinks=False):
        dirs[:] = [name for name in dirs if not os.path.islink(os.path.join(current, name))]
        for name in dirs:
            try:
                total += os.stat(os.path.join(current, name), follow_symlinks=False).st_blocks * 512
            except OSError:
                pass
        for name in files:
            try:
                total += os.stat(os.path.join(current, name), follow_symlinks=False).st_blocks * 512
            except OSError:
                pass
    return total


max_sockets = 0
max_disk = 0
next_disk_sample = 0.0
while os.path.exists(f"/proc/{root_pid}"):
    socket_fds = 0
    for pid in process_tree(root_pid):
        try:
            entries = os.listdir(f"/proc/{pid}/fd")
        except OSError:
            continue
        for fd in entries:
            try:
                if os.readlink(f"/proc/{pid}/fd/{fd}").startswith("socket:["):
                    socket_fds += 1
            except OSError:
                pass
    max_sockets = max(max_sockets, socket_fds)
    now = time.monotonic()
    if now >= next_disk_sample:
        max_disk = max(max_disk, allocated_bytes(runtime))
        next_disk_sample = now + 1.0
    time.sleep(0.1)

with open(output, "w", encoding="ascii") as stream:
    stream.write(f"sampled_socket_fd_max={max_sockets}\n")
    stream.write(f"sampled_private_disk_max_bytes={max_disk}\n")
