$ErrorActionPreference='Stop'
$expected='C:\Users\RhaiTest\.local\share\agent-builds\rhai\n-d4ece7b0\run'
$runtime=[IO.Path]::GetFullPath($env:AGENT_RUNTIME_DIR)
if(!$runtime.StartsWith($expected+'\',[StringComparison]::OrdinalIgnoreCase)){
 throw 'Runtime is outside the exact owned project run root.'
}
$work=[IO.Path]::GetFullPath((Join-Path $runtime 'work'))
if($env:CARGO_HOME -ine (Join-Path $work 'cargo-home') -or $env:CARGO_TARGET_DIR -ine (Join-Path $work 'target')){
 throw 'Private Cargo output roots differ.'
}
$cursor=$work
while($cursor){
 if(!(Test-Path -LiteralPath $cursor)){throw "Private work path absent: $cursor"}
 if(([IO.File]::GetAttributes($cursor) -band [IO.FileAttributes]::ReparsePoint) -ne 0){throw "Reparse ancestor refused: $cursor"}
 if($cursor -ieq $expected){break}
 $parent=[IO.Directory]::GetParent($cursor)
 if($null -eq $parent){throw 'Owned work ancestry ended early.'}
 $cursor=$parent.FullName
}
$stack=[Collections.Generic.Stack[string]]::new()
$stack.Push($work)
$paths=[Collections.Generic.List[string]]::new()
$clock=[Diagnostics.Stopwatch]::StartNew()
while($stack.Count -gt 0){
 if($paths.Count -ge 65536 -or $clock.Elapsed.TotalSeconds -ge 30){throw 'Private work inventory bound exceeded.'}
 $directory=$stack.Pop()
 foreach($path in [IO.Directory]::EnumerateFileSystemEntries($directory)){
  $attributes=[IO.File]::GetAttributes($path)
  if(($attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0){throw "Private work reparse point refused: $path"}
  $paths.Add($path)
  if(($attributes -band [IO.FileAttributes]::Directory) -ne 0){$stack.Push($path)}
 }
}
foreach($path in $paths){
 if($clock.Elapsed.TotalSeconds -ge 45){throw 'Private work attribute bound exceeded.'}
 $attributes=[IO.File]::GetAttributes($path)
 if(($attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0){throw "Private work changed to reparse point: $path"}
 if(($attributes -band [IO.FileAttributes]::ReadOnly) -ne 0){
  [IO.File]::SetAttributes($path,($attributes -band (-bnot [IO.FileAttributes]::ReadOnly)))
 }
}
Write-Output 'RHAI_WORK_READONLY_CLEARED'
