#!/bin/zsh
setopt pipefail
repo=/Users/hoppworks/projects/rhai-all-tickets
evidence_dir=$repo/.scratch/all-tickets/macos-process-overhead-evidence
mkdir -p "$evidence_dir"
evidence=$(mktemp "$evidence_dir/macos-process-overhead.XXXXXX")
log_base="$evidence.driver"
print -r -- "evidence_path=$evidence"
print -r -- "cargo_log_base=$log_base"
print -r -- "wrapper_pid=$$ wrapper_pgid=$(ps -o pgid= -p $$ | tr -d ' ')"
export RHAI_OVERHEAD_LOG_BASE="$log_base"
python3 "$repo/.scratch/all-tickets/run-macos-process-overhead-scoped.py" --timeout 585 > "$evidence" 2>&1
runner_rc=$?
cat "$evidence"
runtime_paths=(${(f)"$(sed -n 's/^runtime_path=//p' "$evidence")"})
cleanup_rc=0
if (( ${#runtime_paths[@]} != 1 )); then
 print -r -- "cleanup_readback=missing_or_ambiguous count=${#runtime_paths[@]}"; cleanup_rc=1
else
 runtime=$runtime_paths[1]
 if [[ "$runtime" != /* || -L "$runtime" || -e "$runtime" ]]; then print -r -- "cleanup_readback=present_or_invalid runtime=$runtime"; cleanup_rc=1
 else print -r -- "cleanup_readback=absent runtime=$runtime"; fi
fi
for suffix in .measurement-driver.log; do
 log="$log_base$suffix"
 if [[ -L "$log" || ! -f "$log" ]]; then print -r -- "cargo_log_readback=missing_or_invalid path=$log"; cleanup_rc=1
 else print -r -- "cargo_log_readback=present bytes=$(wc -c < "$log" | tr -d ' ') path=$log"; fi
done
samples_dir="$log_base.samples"
for name in raw-samples.csv summary.json cargo-output.log cargo.status; do
 path="$samples_dir/$name"
 if [[ -L "$path" || ! -f "$path" ]]; then print -r -- "measurement_readback=missing_or_invalid path=$path"; cleanup_rc=1
 else print -r -- "measurement_readback=present bytes=$(wc -c < "$path" | tr -d ' ') path=$path"; fi
done
print -r -- "runner_status=$runner_rc cleanup_status=$cleanup_rc evidence_path=$evidence"
(( runner_rc == 0 && cleanup_rc == 0 ))
