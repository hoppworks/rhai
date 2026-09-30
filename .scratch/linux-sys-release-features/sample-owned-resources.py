#!/usr/bin/env python3
"""Sample the scoped command tree and private runtime storage once per second."""
import os
import signal
import sys
import time

root_pid = int(sys.argv[1])
runtime = sys.argv[2]
output = sys.argv[3]
stop_file = sys.argv[4]


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
        for name in dirs + files:
            try:
                total += os.stat(os.path.join(current, name), follow_symlinks=False).st_blocks * 512
            except OSError:
                pass
    return total


max_processes = 0
max_disk = 0
samples = 0
preempted = "none"
while os.path.exists(f"/proc/{root_pid}"):
    tree = process_tree(root_pid)
    max_processes = max(max_processes, len(tree))
    max_disk = max(max_disk, allocated_bytes(runtime))
    samples += 1
    reason = None
    if max_processes > 16:
        reason = "owned_process_count_over_16"
    elif max_disk > 1610612736:
        reason = "private_disk_over_1_5_gib"
    if reason is not None:
        preempted = reason
        with open(stop_file, "w", encoding="ascii") as stream:
            stream.write(f"reason={reason}\n")
            stream.write(f"sampled_process_count={max_processes}\n")
            stream.write(f"sampled_private_disk_bytes={max_disk}\n")
        try:
            os.kill(root_pid, signal.SIGTERM)
        except ProcessLookupError:
            pass
        break
    time.sleep(1.0)

with open(output, "w", encoding="ascii") as stream:
    stream.write(f"sampled_process_count_max={max_processes}\n")
    stream.write(f"sampled_private_disk_max_bytes={max_disk}\n")
    stream.write(f"one_second_samples={samples}\n")
    stream.write(f"preempted_reason={preempted}\n")
