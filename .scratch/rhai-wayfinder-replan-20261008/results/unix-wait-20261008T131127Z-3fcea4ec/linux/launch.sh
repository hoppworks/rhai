#!/bin/bash
set +e
PYTHONDONTWRITEBYTECODE=1 TMPDIR=/root/.local/share/agent-builds/rhai/unix-wait-29a33c10da /usr/bin/python3 /var/home/workhorse/projects/agent-skills/tools/run_scoped.py --timeout 1200 -- bash /root/rhai-evidence/wayfinder-20261008/unix-wait-93576e4c32/payload.sh /root/rhai-evidence/wayfinder-20261008/unix-wait-93576e4c32 > /root/rhai-evidence/wayfinder-20261008/unix-wait-93576e4c32/runner.log 2>&1
RHAI_STATUS=$?
printf '%s\n' "$RHAI_STATUS" > /root/rhai-evidence/wayfinder-20261008/unix-wait-93576e4c32/runner.status
exit "$RHAI_STATUS"
