mkdir /var/roothome/.local/share/agent-builds/rhai/linux-fs-fresh-cache-90b93d3bc7a341f295e0c9518bcae56e
TMPDIR=/var/roothome/.local/share/agent-builds/rhai/linux-fs-fresh-cache-90b93d3bc7a341f295e0c9518bcae56e PYTHONDONTWRITEBYTECODE=1 python3 /var/home/workhorse/projects/agent-skills/tools/run_scoped.py --timeout 1500 -- python3 -B /var/roothome/projects/rhai-linux-fs-20261025-23772744/run.py > /var/roothome/projects/rhai-linux-fs-20261025-23772744/run-scoped.stdout 2> /var/roothome/projects/rhai-linux-fs-20261025-23772744/run-scoped.stderr
linux_fs_status=$?
printf "%s\n" "$linux_fs_status" > /var/roothome/projects/rhai-linux-fs-20261025-23772744/run-scoped.status
rmdir /var/roothome/.local/share/agent-builds/rhai/linux-fs-fresh-cache-90b93d3bc7a341f295e0c9518bcae56e
exit "$linux_fs_status"
