#!/bin/zsh
setopt pipefail
evidence_dir=/Users/hoppworks/projects/rhai-process-unix-run/.scratch/process-unix-run/evidence
mkdir -p "$evidence_dir"
evidence=$(mktemp "$evidence_dir/reaped-driver-unwind.XXXXXX")
print -r -- "evidence_path=$evidence"
python3 /Users/hoppworks/projects/agent-skills/tools/run_scoped.py --timeout 600 -- python3 /Users/hoppworks/projects/rhai-process-unix-run/.scratch/process-unix-run/reaped-driver-unwind.py > "$evidence" 2>&1
runner_rc=$?
cat "$evidence"
runtime_paths=(${(f)"$(sed -n 's/^runtime_path=//p' "$evidence")"})
cleanup_rc=0
if (( ${#runtime_paths[@]} != 1 )); then
  print -r -- "cleanup_readback=missing_or_ambiguous count=${#runtime_paths[@]}"
  cleanup_rc=1
else
  runtime=$runtime_paths[1]
  if [[ "$runtime" != /* ]]; then
    print -r -- "cleanup_readback=invalid_path runtime=$runtime"
    cleanup_rc=1
  elif [[ -L "$runtime" || -e "$runtime" ]]; then
    print -r -- "cleanup_readback=present runtime=$runtime"
    cleanup_rc=1
  else
    print -r -- "cleanup_readback=absent runtime=$runtime"
  fi
fi
print -r -- "runner_status=$runner_rc cleanup_status=$cleanup_rc evidence_path=$evidence"
(( runner_rc == 0 && cleanup_rc == 0 ))
