$ErrorActionPreference='Stop'
$expected='C:\Users\RhaiTest\.local\share\agent-builds\rhai\n-6c165808\run'
$runtime=[IO.Path]::GetFullPath($env:AGENT_RUNTIME_DIR)
if(!$runtime.StartsWith($expected+'\',[StringComparison]::OrdinalIgnoreCase)){
 throw 'Runtime is outside the exact owned project run root.'
}
$work=[IO.Path]::GetFullPath((Join-Path $runtime 'work'))
if($env:CARGO_HOME -ine (Join-Path $work 'cargo-home') -or $env:CARGO_TARGET_DIR -ine (Join-Path $work 'target')){
 throw 'Private Cargo output roots differ.'
}
$fsutil='C:\Windows\System32\fsutil.exe'
if((Get-FileHash -LiteralPath $fsutil).Hash.ToLowerInvariant() -cne '3fca44b7ce971031c08296647821e04dc7aa62c0f5846a3a0dc7015d5a4bc501'){
 throw 'Guest hardlink inventory utility differs.'
}
$volumeRelativePrefix=$work.Substring(2).TrimEnd('\')+'\'
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
  if(($attributes -band [IO.FileAttributes]::Directory) -eq 0){
   $aliases=@(& $fsutil hardlink list $path 2>&1)
   if($LASTEXITCODE -ne 0 -or $aliases.Count -eq 0 -or $aliases.Count -gt 64){throw "Private work hardlink inventory failed: $path"}
   foreach($alias in $aliases){
    if(!([string]$alias).Trim().StartsWith($volumeRelativePrefix,[StringComparison]::OrdinalIgnoreCase)){
     throw "ReadOnly file has an alias outside the owned work tree: $path"
    }
   }
  }
  [IO.File]::SetAttributes($path,($attributes -band (-bnot [IO.FileAttributes]::ReadOnly)))
 }
}
Write-Output 'RHAI_READONLY_ALIAS_SCOPE_CONFIRMED'
Write-Output 'RHAI_WORK_READONLY_CLEARED'
