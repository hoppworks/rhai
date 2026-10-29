$ErrorActionPreference='Stop'
$nonce='ed665e3968e2453db7cba4dd594abeb2'
$id='rhai-native-'+$nonce
$marker='rhai-native-'+$nonce+'.bundle'
$mediaCandidates=@(('D:\','E:\','F:\')|Where-Object{
 $drive=$_.Substring(0,1)
 $null -ne (Get-PSDrive -Name $drive -PSProvider FileSystem -ErrorAction SilentlyContinue) -and
 (Test-Path -LiteralPath (Join-Path $_ $marker) -PathType Leaf)
})
if($mediaCandidates.Count -ne 1){throw 'Expected exactly one immutable project-control medium.'}
$media=$mediaCandidates[0]
if((Get-Content -LiteralPath (Join-Path $media $marker) -Raw).Trim() -cne $id){throw 'Project-control medium identity differs.'}
$archive=Join-Path $media 'rhai-source.zip'
$manifestPath=Join-Path $media 'source-manifest.json'
$control=Join-Path $media 'RunRhaiContractControl.ps1'
$lock=Join-Path $media 'Cargo.lock'
$contract=Join-Path $media 'RunRhaiContract.cmd'
$attributeControl=Join-Path $media 'ClearOwnedWorkReadOnly.ps1'
if((Get-FileHash -LiteralPath $archive).Hash.ToLowerInvariant() -cne 'df38e99dd7f67f8556237155a124deb70dc2031eb6ba2bf8bb87076bbcbc5d36'){throw 'Frozen Rhai archive differs.'}
if((Get-FileHash -LiteralPath $manifestPath).Hash.ToLowerInvariant() -cne 'e131ad8c2811569e6485fb594207aa5f60cf8f86ebbb4a3c691a72e586aa5075'){throw 'Frozen Rhai source manifest differs.'}
if((Get-FileHash -LiteralPath $control).Hash.ToLowerInvariant() -cne '851eb47f491a40307f9f5c976394843bc7eab7e77f95f1a1f66c587e6627bc51'){throw 'Bounded native control differs.'}
if((Get-FileHash -LiteralPath $lock).Hash.ToLowerInvariant() -cne '12084a90214418632e80bbaf95983925c2c3886f57f40e2a305b4a1ec353d802'){throw 'Accepted lock differs.'}
if((Get-FileHash -LiteralPath $contract).Hash.ToLowerInvariant() -cne 'ee797ff3168ac32fdad4d4ab19fec3ace18ade33891c780397c04ca231665873'){throw 'Native Rhai contract differs.'}
if((Get-FileHash -LiteralPath $attributeControl).Hash.ToLowerInvariant() -cne 'afb2351597ddc1e3e0f81af38fcc98434ba9738b0acaf626820cce731cc86c67'){throw 'Owned work attribute control differs.'}
$tokens=$null;$parseErrors=$null;$null=[Management.Automation.Language.Parser]::ParseFile($control,[ref]$tokens,[ref]$parseErrors)
if($parseErrors.Count -ne 0){throw ($parseErrors|Out-String)}
$manifest=Get-Content -LiteralPath $manifestPath -Raw|ConvertFrom-Json
if($manifest.source_commit -cne 'e0ec6fae0161a743b1f7e8ede9892f4f89787c87' -or $manifest.file_count -ne 449 -or $manifest.total_source_bytes -ne 5423810 -or $manifest.archive_sha256 -cne 'df38e99dd7f67f8556237155a124deb70dc2031eb6ba2bf8bb87076bbcbc5d36'){throw 'Frozen Rhai source identity differs.'}
if($env:USERPROFILE -cne 'C:\Users\RhaiTest' -or $env:USERNAME -cne 'RhaiTest'){throw 'Wrong native guest owner.'}
if((Get-PSDrive -Name C -PSProvider FileSystem).Free -lt 19327352832){throw 'Native guest free disk below18GiB launch floor.'}
if(([long](Get-CimInstance Win32_OperatingSystem).FreePhysicalMemory*1024) -lt 3221225472){throw 'Native guest free physical memory below3GiB launch floor.'}
$private=Join-Path $env:USERPROFILE '.local\share\agent-builds\rhai'
$retainedHome=Join-Path $private 'n-a7e54f39\toolchain-home'
$oldPreflight=Join-Path $private 'n-a7e54f39\preflight.json'
if((Get-FileHash -LiteralPath $oldPreflight).Hash.ToLowerInvariant() -cne '34907dd6b5943fac0b8cdd9a01a9614103792148941d435156de2a4cd1abe360'){throw 'Accepted retained scope identity differs.'}
if(!(Test-Path -LiteralPath $retainedHome -PathType Container) -or ((Get-Item -LiteralPath $retainedHome -Force).Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0){throw 'Retained toolchain home absent or redirected.'}
if([DateTime]::UtcNow -ge [DateTime]::Parse('2026-11-01T00:00:00Z').ToUniversalTime()){throw 'Retained toolchain authorization expired.'}
$toolchainBin=Join-Path $retainedHome 'toolchains\1.77.2-x86_64-pc-windows-msvc\bin'
$cargoExe=Join-Path $toolchainBin 'cargo.exe'
$rustcExe=Join-Path $toolchainBin 'rustc.exe'
if((Get-FileHash -LiteralPath $cargoExe).Hash.ToLowerInvariant() -cne '86e57909ec2d3340ad78fa25df377d70b656eeec866b6f8c6b2b517afbf9ce49'){throw 'Retained Cargo binary differs.'}
if((Get-FileHash -LiteralPath $rustcExe).Hash.ToLowerInvariant() -cne 'a95aa2d914c37e85cef157c2eb4150ee348b90f4f733348f39cbb219b642d7c9'){throw 'Retained Rustc binary differs.'}
$retainedBytes=0L
foreach($entry in Get-ChildItem -LiteralPath $retainedHome -Force -Recurse){
 if(($entry.Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0){throw 'Retained toolchain contains a redirected entry.'}
 if(!$entry.PSIsContainer){$retainedBytes+=[long]$entry.Length}
}
if($retainedBytes -gt 2147483648){throw 'Retained toolchain exceeds accepted 2GiB ceiling.'}
$cargoHash=(Get-FileHash -LiteralPath $cargoExe).Hash.ToLowerInvariant()
$session=Join-Path $private ('n-'+$nonce.Substring(0,8))
$build=Join-Path $private 'public-refresh-e2047d40e48afb4426d07e2a1e881f19\run\monitor-source-e2047d40e48afb4426d07e2a1e881f19\build'
if(!(Test-Path -LiteralPath $build -PathType Container)){throw 'Compatible native public build is absent.'}
if((Get-FileHash -LiteralPath (Join-Path ([IO.Directory]::GetParent($build).FullName) 'build-manifest.txt')).Hash.ToLowerInvariant() -cne '8c625daf866e4bb5e30259b9fb3d27cafcb4e8e5ee813a5b07b6a5e4160ee0d1'){throw 'Retained public build manifest differs from accepted readback.'}
if(Test-Path -LiteralPath $session){throw 'Own project scope already exists; preserve and inspect it.'}
$cursor=[IO.Path]::GetFullPath($session)
while($cursor){
 if((Test-Path -LiteralPath $cursor) -and ((Get-Item -LiteralPath $cursor -Force).Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0){throw "Reparse ancestor refused: $cursor"}
 $parent=[IO.Directory]::GetParent($cursor);$cursor=if($null -eq $parent){$null}else{$parent.FullName}
}
$source=Join-Path $session 'source'
New-Item -ItemType Directory -Path $source|Out-Null
Copy-Item -LiteralPath $manifestPath -Destination (Join-Path $session 'source-manifest.json')
Expand-Archive -LiteralPath $archive -DestinationPath $source
$sourcePrefix=[IO.Path]::GetFullPath($source).TrimEnd('\')+'\'
$actual=@(Get-ChildItem -LiteralPath $source -File -Force -Recurse|ForEach-Object{$_.FullName.Substring($sourcePrefix.Length).Replace('\','/')}|Sort-Object)
$expected=@($manifest.files.PSObject.Properties.Name|Sort-Object)
if($actual.Count -ne 449 -or ($actual -join "`n") -cne ($expected -join "`n")){throw 'Expanded Rhai source inventory differs.'}
foreach($entry in @(Get-ChildItem -LiteralPath $source -Force -Recurse)){if(($entry.Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0){throw 'Expanded Rhai source reparse point refused.'}}
foreach($pin in $manifest.files.PSObject.Properties){
 if($pin.Name -match '(^|/)\.\.(/|$)' -or $pin.Name -match '^[/\\]'){throw 'Source manifest traversal refused.'}
 $path=[IO.Path]::GetFullPath((Join-Path $source $pin.Name.Replace('/','\')))
 if(!$path.StartsWith($sourcePrefix,[StringComparison]::OrdinalIgnoreCase) -or (Get-FileHash -LiteralPath $path).Hash.ToLowerInvariant() -cne $pin.Value.sha256){throw "Expanded Rhai source differs: $($pin.Name)"}
}
Copy-Item -LiteralPath $cargoExe -Destination (Join-Path $source 'cargo.exe')
if((Get-FileHash -LiteralPath (Join-Path $source 'cargo.exe')).Hash.ToLowerInvariant() -cne $cargoHash){throw 'Private Cargo binary copy differs.'}
$cmdExe='C:\Windows\System32\cmd.exe'
$cmdHash='15cd209c995b7d3009c91ca40892d5b8f1fb162f3e5f10716642ea278e8e0d7b'
if((Get-FileHash -LiteralPath $cmdExe).Hash.ToLowerInvariant() -cne $cmdHash){throw 'Guest command interpreter differs.'}
$fsutilExe='C:\Windows\System32\fsutil.exe'
$fsutilHash='3fca44b7ce971031c08296647821e04dc7aa62c0f5846a3a0dc7015d5a4bc501'
if((Get-FileHash -LiteralPath $fsutilExe).Hash.ToLowerInvariant() -cne $fsutilHash){throw 'Guest hardlink inventory utility differs.'}
$powershellExe='C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe'
$powershellHash='60c9b29843624dd8af6b6a7b26147753be6aeef65098b9a503cc50850afe410f'
if($env:SystemRoot -ine 'C:\Windows' -or (Get-FileHash -LiteralPath $powershellExe).Hash.ToLowerInvariant() -cne $powershellHash){throw 'Guest PowerShell or SystemRoot differs.'}
Copy-Item -LiteralPath $cmdExe -Destination (Join-Path $source 'cmd.exe')
Copy-Item -LiteralPath $lock -Destination (Join-Path $source 'Cargo.lock')
Copy-Item -LiteralPath $contract -Destination (Join-Path $source 'RunRhaiContract.cmd')
Copy-Item -LiteralPath $attributeControl -Destination (Join-Path $source 'ClearOwnedWorkReadOnly.ps1')
if((Get-FileHash -LiteralPath (Join-Path $source 'cmd.exe')).Hash.ToLowerInvariant() -cne $cmdHash -or (Get-FileHash -LiteralPath (Join-Path $source 'Cargo.lock')).Hash.ToLowerInvariant() -cne '12084a90214418632e80bbaf95983925c2c3886f57f40e2a305b4a1ec353d802' -or (Get-FileHash -LiteralPath (Join-Path $source 'RunRhaiContract.cmd')).Hash.ToLowerInvariant() -cne 'ee797ff3168ac32fdad4d4ab19fec3ace18ade33891c780397c04ca231665873' -or (Get-FileHash -LiteralPath (Join-Path $source 'ClearOwnedWorkReadOnly.ps1')).Hash.ToLowerInvariant() -cne 'afb2351597ddc1e3e0f81af38fcc98434ba9738b0acaf626820cce731cc86c67'){throw 'Private native contract inputs differ.'}
$record=[ordered]@{id=$id;guest_user=$env:USERNAME;source_commit=$manifest.source_commit;source_manifest_sha256='e131ad8c2811569e6485fb594207aa5f60cf8f86ebbb4a3c691a72e586aa5075';archive_sha256='df38e99dd7f67f8556237155a124deb70dc2031eb6ba2bf8bb87076bbcbc5d36';source_files=449;staged_files=454;lock_sha256='12084a90214418632e80bbaf95983925c2c3886f57f40e2a305b4a1ec353d802';contract_sha256='ee797ff3168ac32fdad4d4ab19fec3ace18ade33891c780397c04ca231665873';attribute_control_sha256='afb2351597ddc1e3e0f81af38fcc98434ba9738b0acaf626820cce731cc86c67';cmd_exe_sha256=$cmdHash;powershell_exe_sha256=$powershellHash;fsutil_exe_sha256=$fsutilHash;cargo_binary=$cargoExe;cargo_sha256=$cargoHash;cargo_version_expected='cargo 1.77.2 (e52e36006 2024-03-26)';rustc_binary=$rustcExe;rustc_sha256='a95aa2d914c37e85cef157c2eb4150ee348b90f4f733348f39cbb219b642d7c9';rustc_version_expected='rustc 1.77.2 (25ef9e3d8 2024-04-09)';retained_toolchain_home=$retainedHome;retained_toolchain_bytes=$retainedBytes;public_build_manifest_sha256='8c625daf866e4bb5e30259b9fb3d27cafcb4e8e5ee813a5b07b6a5e4160ee0d1';own_scope=$session}
[IO.File]::WriteAllText((Join-Path $session 'preflight.json'),($record|ConvertTo-Json -Compress),[Text.UTF8Encoding]::new($false))
Write-Output 'PROJECT_SOURCE_PREFLIGHT_OK'
& ([scriptblock]::Create((Get-Content -LiteralPath $control -Raw))) -Session $session -SourceRoot $source -BuildRoot $build -Id $id -CargoSha256 $cargoHash
Write-Output 'PROJECT_COMMAND_CONTROL_COMPLETE;guest originals retained for independent export/readback and exact cleanup'
