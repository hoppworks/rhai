#!/bin/zsh
setopt pipefail
repo=/Users/hoppworks/projects/rhai-process-unix-run
evidence_dir=$repo/.scratch/process-unix-run/evidence
mkdir -p "$evidence_dir"
evidence=$(mktemp "$evidence_dir/entered-wait.XXXXXX")
print -r -- "evidence_path=$evidence"
print -r -- "wrapper_pid=$$ wrapper_pgid=$(ps -o pgid= -p $$ | tr -d ' ')"
PROCESS_EVIDENCE="$evidence" python3 /Users/hoppworks/projects/agent-skills/tools/run_scoped.py --timeout 600 -- python3 "$repo/.scratch/process-unix-run/entered-wait.py" > "$evidence" 2>&1
runner_rc=$?
cat "$evidence"
runtime_paths=(${(f)"$(sed -n 's/^runtime=//p' "$evidence")"})
cleanup_rc=0
if (( ${#runtime_paths[@]} != 1 )); then
  print -r -- "cleanup_readback=missing_or_ambiguous count=${#runtime_paths[@]}"
  cleanup_rc=1
else
  runtime=$runtime_paths[1]
  if [[ "$runtime" != /* || -L "$runtime" || -e "$runtime" ]]; then
    print -r -- "cleanup_readback=present_or_invalid runtime=$runtime"
    cleanup_rc=1
  else
    print -r -- "cleanup_readback=absent runtime=$runtime"
  fi
fi
print -r -- "runner_status=$runner_rc cleanup_status=$cleanup_rc evidence_path=$evidence"
(( runner_rc == 0 && cleanup_rc == 0 ))
