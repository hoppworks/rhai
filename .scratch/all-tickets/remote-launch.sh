#!/usr/bin/env bash
set -euo pipefail
: "${PROOF_STAGE:?set exact stage path}"
stage=$PROOF_STAGE
evidence="$stage/evidence"
mkdir -p "$evidence"
exec > >(tee -a "$evidence/outer.log") 2>&1
trap 'rc=$?; printf "%s\n" "$rc" > "$evidence/outer-status.txt"' EXIT
python3 - "$evidence/launcher-identities.tsv" "$$" <<'PY'
import pathlib,sys
p=int(sys.argv[2]); f=pathlib.Path('/proc',str(p),'stat').read_text(); a=f[f.rfind(')')+2:].split()
pathlib.Path(sys.argv[1]).write_text('label\tpid\tppid\tpgid\tstart_ticks\nlauncher\t%d\t%s\t%s\t%s\n'%(p,a[1],a[2],a[19]))
PY
PROOF_STAGE="$stage" python3 "$stage/runner/tools/run_scoped.py" --timeout 600 -- python3 "$stage/linux-process-proof.py" &
runner=$!
if wait "$runner"; then status=0; else status=$?; fi
printf '%s\n' "$status" > "$evidence/run-scoped.status"
python3 - "$evidence" "$runner" <<'PY'
import pathlib,sys,subprocess
e=pathlib.Path(sys.argv[1]); p=int(sys.argv[2]); rows=[]
try:
 f=pathlib.Path('/proc',str(p),'stat').read_text(); a=f[f.rfind(')')+2:].split(); rows.append((p,a[19],True))
except FileNotFoundError: rows.append((p,'<gone>',False))
(e/'pid-readback.tsv').write_text('pid\tstart_ticks\tmatching_alive\n'+''.join(f'{x}\t{y}\t{int(z)}\n' for x,y,z in rows))
PY
test ! -e "$(sed -n 's/^PRIVATE_RUNTIME //p' "$evidence/outer.log" | tail -1)"
exit "$status"
