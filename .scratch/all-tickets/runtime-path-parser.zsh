function runtime_path_from_evidence() {
 emulate -L zsh
 local evidence_path="$1"
 local expected_path="$2"
 local candidate
 local record
 local -a runtime_paths
 runtime_paths=("${(@f)$(sed -n 's/^runtime_path=//p' "$evidence_path")}")
 (( ${#runtime_paths[@]} > 0 )) || return 1
 candidate="$runtime_paths[1]"
 for record in "${runtime_paths[@]}"; do
  [[ "$record" == "$candidate" ]] || return 1
 done
 [[ "$candidate" == "$expected_path" && "$candidate" == /* ]] || return 1
 [[ ! -L "$candidate" && ! -e "$candidate" ]] || return 1
 print -r -- "$candidate"
}
