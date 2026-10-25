$ErrorActionPreference='Stop'
$nonce='49243ecf52d64c609a876e3c52409500'
$id='rhai-project-export-'+$nonce
$marker='project-export-'+$nonce+'.bundle'
$mediaCandidates=@(('D:\','E:\','F:\')|Where-Object{
 $drive=$_.Substring(0,1)
 $null -ne (Get-PSDrive -Name $drive -PSProvider FileSystem -ErrorAction SilentlyContinue) -and
 (Test-Path -LiteralPath (Join-Path $_ $marker) -PathType Leaf)
})
if($mediaCandidates.Count -ne 1){throw 'Expected exactly one own read-only export medium.'}
$media=$mediaCandidates[0]
if((Get-Content -LiteralPath (Join-Path $media $marker) -Raw).Trim() -cne $id){throw 'Export medium identity differs.'}
if($env:USERPROFILE -cne 'C:\Users\RhaiTest' -or $env:USERNAME -cne 'RhaiTest'){throw 'Wrong native guest owner.'}
$private=Join-Path $env:USERPROFILE '.local\share\agent-builds\rhai'
$session=Join-Path $private ('project-control-'+$nonce)
$run=Join-Path $session 'run'
if(!(Test-Path -LiteralPath $run -PathType Container)){throw 'Exact own original run is absent.'}
$observerPath=Join-Path $session 'observer.json'
$observer=Get-Content -LiteralPath $observerPath -Raw|ConvertFrom-Json
if($observer.id -cne ('rhai-project-command-'+$nonce) -or !$observer.accepted -or $observer.driver_exit -ne 0 -or $observer.failure -or $observer.custody_pending -or !$observer.owned_executables_stopped){throw 'Original native project observer did not accept the run.'}
if($observer.public_build_manifest_sha256 -cne '613361eba54c1edfaa0da576ccece3a6cb0009cfc4e35af582d46f967e1a320a' -or $observer.source_manifest_sha256 -cne '1ed2dc76e988d82654f588e2c9e7c32c8526f2d888c44fbbaee9b996f7c847a1'){throw 'Original source/public build identity differs.'}
$runtime=[IO.Path]::GetFullPath([string]$observer.runtime)
if([IO.Path]::GetDirectoryName($runtime) -cne $run -or [IO.Path]::GetFileName($runtime) -notmatch '^scoped-[0-9a-f]{32}$' -or (Test-Path -LiteralPath $runtime)){throw 'Fresh native runtime absence failed.'}
$journals=@(Get-ChildItem -LiteralPath $run -File -Force -Filter '.scoped-run-*.journal')
$evidence=@(Get-ChildItem -LiteralPath $run -Directory -Force -Filter '.scoped-evidence-*')
if($journals.Count -ne 1 -or $evidence.Count -ne 1){throw 'Exact original journal/evidence roots differ.'}
$files=@(
 (Get-Item -LiteralPath $observerPath),
 (Get-Item -LiteralPath (Join-Path $session 'preflight.json')),
 (Get-Item -LiteralPath (Join-Path $session 'source-manifest.json')),
 (Get-Item -LiteralPath (Join-Path $session 'build-manifest.txt')),
 (Get-Item -LiteralPath (Join-Path $session 'driver.stdout')),
 (Get-Item -LiteralPath (Join-Path $session 'driver.stderr')),
 $journals[0],
 (Get-Item -LiteralPath (Join-Path $evidence[0].FullName 'stdout.log')),
 (Get-Item -LiteralPath (Join-Path $evidence[0].FullName 'stderr.log')),
 (Get-Item -LiteralPath (Join-Path $evidence[0].FullName 'manifest.txt'))
)
if($files.Count -ne 10 -or @($files|Select-Object -ExpandProperty FullName -Unique).Count -ne 10){throw 'Selected original file inventory differs.'}
$total=0L
foreach($file in $files){
 if(($file.Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0 -or $file.Length -gt 4MB){throw 'Selected original is a reparse point or exceeds4MiB.'}
 if(!$file.FullName.StartsWith($session+'\',[StringComparison]::OrdinalIgnoreCase)){throw 'Selected original escaped exact own scope.'}
 $total+=$file.Length
}
if($total -gt 16MB){throw 'Selected original total exceeds16MiB.'}
$serial=[IO.Ports.SerialPort]::new('COM1',115200);$serial.WriteTimeout=2000;$script:sequence=0;$deadline=[Diagnostics.Stopwatch]::StartNew()
function Emit-Frame([string]$Kind,[object]$Value){
 if($deadline.Elapsed.TotalSeconds -gt 180){throw 'Read-only original export exceeded180seconds; guest originals retained.'}
 $encoded=[Convert]::ToBase64String([Text.Encoding]::UTF8.GetBytes(($Value|ConvertTo-Json -Compress -Depth 8)))
 if($encoded.Length -gt 3500){throw 'Original export frame exceeds declared bound.'}
 $serial.WriteLine("RHAI_BOOTSTRAP $id $($script:sequence) $Kind $encoded");$script:sequence++
}
try{
 $serial.Open()
 Emit-Frame 'BEGIN' @{id=$id;scope=$session;accepted=$true;driver_exit=0;runtime_absent=$true;original_files=$files.Count;original_bytes=$total}
 foreach($file in $files){
  $relative=$file.FullName.Substring($session.Length+1).Replace('\','/')
  $bytes=[IO.File]::ReadAllBytes($file.FullName)
  $sha=[Security.Cryptography.SHA256]::Create()
  try{$hash=[BitConverter]::ToString($sha.ComputeHash($bytes)).Replace('-','').ToLowerInvariant()}finally{$sha.Dispose()}
  Emit-Frame 'FILE' @{path=$relative;length=$bytes.Length;sha256=$hash}
  for($offset=0;$offset -lt $bytes.Length;$offset+=1024){$length=[Math]::Min(1024,$bytes.Length-$offset);Emit-Frame 'CHUNK' @{path=$relative;offset=$offset;data=[Convert]::ToBase64String($bytes,$offset,$length)}}
  Emit-Frame 'FILE_END' @{path=$relative;length=$bytes.Length;sha256=$hash}
 }
 Emit-Frame 'END' @{id=$id;files=$files.Count;bytes=$total;accepted=$true;runtime_absent=$true;guest_originals_retained=$true}
}finally{$serial.Dispose()}
Write-Output "PROJECT_ORIGINAL_EXPORT_OK files=$($files.Count) bytes=$total;guest originals retained"
