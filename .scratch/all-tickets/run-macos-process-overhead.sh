#!/bin/zsh
setopt pipefail
if [[ $# == 0 ]]; then
 control_case=normal
elif [[ $# == 2 && $1 == --control-case ]]; then
 control_case=$2
else
 print -r -- "usage: run-macos-process-overhead.sh [--control-case setup|build|deadline]" >&2
 exit 2
fi
if [[ $control_case != normal ]]; then
 case "$control_case" in
  setup|build|deadline) ;;
  managed) print -r -- "Managed control is unready: fixture/stream observations are not implemented" >&2; exit 2 ;;
  *) print -r -- "invalid finite control case: $control_case" >&2; exit 2 ;;
 esac
fi
source "${0:A:h}/runtime-path-parser.zsh"
script_dir="${0:A:h}"
repo="${script_dir:h:h}"
evidence_dir=$repo/.scratch/all-tickets/macos-process-overhead-evidence
mkdir -p "$evidence_dir"
build_root=${HOME}/.local/share/agent-builds/rhai
mkdir -p "$build_root"
scope=$(mktemp -d "$build_root/macos-overhead-XXXXXXXX")
mkdir -m 700 "$scope/tmp"
export AGENT_BUILD_SCOPE="$scope"
export TMPDIR="$scope/tmp" TMP="$scope/tmp" TEMP="$scope/tmp"
evidence=$(mktemp "$evidence_dir/macos-process-overhead.XXXXXX")
log_base="$evidence.driver"
print -r -- "evidence_path=$evidence"
print -r -- "cargo_log_base=$log_base"
print -r -- "wrapper_pid=$$ wrapper_pgid=$(ps -o pgid= -p $$ | tr -d ' ')"
export RHAI_OVERHEAD_LOG_BASE="$log_base"
adapter_args=(--timeout 585)
if [[ $control_case != normal ]]; then adapter_args+=(--control-case "$control_case"); fi
python3 "$repo/.scratch/all-tickets/run-macos-process-overhead-scoped.py" "${adapter_args[@]}" > "$evidence" 2>&1
runner_rc=$?
cat "$evidence"
cleanup_rc=0
if runtime=$(runtime_path_from_evidence "$evidence" "$scope/runtime"); then
 print -r -- "cleanup_readback=absent runtime=$runtime"
else
 print -r -- "cleanup_readback=missing_conflicting_or_invalid_runtime_record"; cleanup_rc=1
fi
if [[ $control_case == normal ]]; then
 log="$log_base.cargo-output.log"
 if [[ -L "$log" || ! -f "$log" ]]; then print -r -- "cargo_log_readback=missing_or_invalid path=$log"; cleanup_rc=1
 else print -r -- "cargo_log_readback=present bytes=$(wc -c < "$log" | tr -d ' ') path=$log"; fi
 samples_dir="$log_base.samples"
 for name in raw-samples.csv summary.json cargo-output.log cargo.status; do
  path="$samples_dir/$name"
  if [[ -L "$path" || ! -f "$path" ]]; then print -r -- "measurement_readback=missing_or_invalid path=$path"; cleanup_rc=1
  else print -r -- "measurement_readback=present bytes=$(wc -c < "$path" | tr -d ' ') path=$path"; fi
 done
fi
receipt="$log_base.custody.json"
if [[ -L "$receipt" || ! -f "$receipt" ]]; then print -r -- "custody_receipt=missing_or_invalid path=$receipt"; cleanup_rc=1
else print -r -- "custody_receipt=present bytes=$(wc -c < "$receipt" | tr -d ' ') path=$receipt"; fi
if [[ -d "$scope" && ! -L "$scope" ]]; then
 if [[ -d "$scope/tmp" && ! -L "$scope/tmp" ]]; then rmdir "$scope/tmp" 2>/dev/null || true; fi
 if rmdir "$scope" 2>/dev/null; then print -r -- "agent_build_scope=removed path=$scope"
 else print -r -- "agent_build_scope=retained_nonempty path=$scope"; cleanup_rc=1; fi
else
 print -r -- "agent_build_scope=missing_or_invalid path=$scope"; cleanup_rc=1
fi
print -r -- "runner_status=$runner_rc cleanup_status=$cleanup_rc evidence_path=$evidence"
(( runner_rc == 0 && cleanup_rc == 0 ))
