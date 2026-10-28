$ErrorActionPreference='Stop'
$nonce='9f3636e89a7447e49cdce5e81ad00f2c'
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
if((Get-FileHash -LiteralPath $archive).Hash.ToLowerInvariant() -cne '7f26d16f07eaa11a1ac3fa0a1f6fe947f8e49df68138055135451dd09ec754c0'){throw 'Frozen Rhai archive differs.'}
if((Get-FileHash -LiteralPath $manifestPath).Hash.ToLowerInvariant() -cne '7b5634223c87e3984b02f4ba840bb03576c1e538155120bc380d3111d2fd57c4'){throw 'Frozen Rhai source manifest differs.'}
if((Get-FileHash -LiteralPath $control).Hash.ToLowerInvariant() -cne 'ef471c0d4a48dd333ff304cb4933b1e9795545aee8890da05d739b117eef1f78'){throw 'Bounded native control differs.'}
if((Get-FileHash -LiteralPath $lock).Hash.ToLowerInvariant() -cne '2ba4b3a0807e32b613ff2e972b893c3fd2e0923fd91803611963f09e93265425'){throw 'Accepted lock differs.'}
if((Get-FileHash -LiteralPath $contract).Hash.ToLowerInvariant() -cne '60d8f88be2bb03174d45341d70637e0cc6c7bd6380b9df313e12bb423846301a'){throw 'Native Rhai contract differs.'}
if((Get-FileHash -LiteralPath $attributeControl).Hash.ToLowerInvariant() -cne '121004581447d9e8f133d5d014d0eefb613d3d66688d6f235a5be28dfbd5bf34'){throw 'Owned work attribute control differs.'}
$tokens=$null;$parseErrors=$null;$null=[Management.Automation.Language.Parser]::ParseFile($control,[ref]$tokens,[ref]$parseErrors)
if($parseErrors.Count -ne 0){throw ($parseErrors|Out-String)}
$manifest=Get-Content -LiteralPath $manifestPath -Raw|ConvertFrom-Json
if($manifest.source_commit -cne '4f3e4cc3197616638c09b234cf90e20f42a31221' -or $manifest.file_count -ne 437 -or $manifest.total_source_bytes -ne 5092340 -or $manifest.archive_sha256 -cne '7f26d16f07eaa11a1ac3fa0a1f6fe947f8e49df68138055135451dd09ec754c0'){throw 'Frozen Rhai source identity differs.'}
if($env:USERPROFILE -cne 'C:\Users\RhaiTest' -or $env:USERNAME -cne 'RhaiTest'){throw 'Wrong native guest owner.'}
if((Get-PSDrive -Name C -PSProvider FileSystem).Free -lt 2147483648){throw 'Native guest free disk below2GiB launch floor.'}
if(([long](Get-CimInstance Win32_OperatingSystem).FreePhysicalMemory*1024) -lt 1073741824){throw 'Native guest free physical memory below1GiB launch floor.'}
$cargoProxy=(Get-Command cargo.exe -ErrorAction Stop).Source
if($cargoProxy -cne 'C:\Users\RhaiTest\.cargo\bin\cargo.exe'){throw 'Guest Cargo proxy path differs.'}
$rustcProxy=(Get-Command rustc.exe -ErrorAction Stop).Source
if($rustcProxy -cne 'C:\Users\RhaiTest\.cargo\bin\rustc.exe'){throw 'Guest Rustc proxy path differs.'}
$cargoVersion=& $cargoProxy --version
$rustcVersion=& $rustcProxy --version
if($cargoVersion -cne 'cargo 1.93.0 (083ac5135 2025-12-15)' -or $rustcVersion -cne 'rustc 1.93.0 (254b59607 2026-01-19)'){throw 'Exact guest Rust/Cargo toolchain differs.'}
$cargoHash=(Get-FileHash -LiteralPath $cargoProxy).Hash.ToLowerInvariant()
if($cargoHash -cne '6f4bef66261261fcb43131be8720bab817d403a09edec7455c371974b90bdb7e'){throw 'Guest Cargo proxy differs from independent preflight.'}
if((Get-FileHash -LiteralPath $rustcProxy).Hash.ToLowerInvariant() -cne $cargoHash){throw 'Guest Rustc proxy differs from independent preflight.'}
$private=Join-Path $env:USERPROFILE '.local\share\agent-builds\rhai'
$session=Join-Path $private ('n-'+$nonce.Substring(0,8))
$build=Join-Path $private 'public-refresh-3b2a5af2029c4c89b3a4e48d9284f2e5\run\monitor-source-3b2a5af2029c4c89b3a4e48d9284f2e5\build'
if(!(Test-Path -LiteralPath $build -PathType Container)){throw 'Compatible native public build is absent.'}
if((Get-FileHash -LiteralPath (Join-Path ([IO.Directory]::GetParent($build).FullName) 'build-manifest.txt')).Hash.ToLowerInvariant() -cne '90e10dd760e2d24eb9cb9dd2f5fc7028e4a3bb981f7a6280055682e9d0549116'){throw 'Retained public build manifest differs from accepted readback.'}
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
if($actual.Count -ne 437 -or ($actual -join "`n") -cne ($expected -join "`n")){throw 'Expanded Rhai source inventory differs.'}
foreach($entry in @(Get-ChildItem -LiteralPath $source -Force -Recurse)){if(($entry.Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0){throw 'Expanded Rhai source reparse point refused.'}}
foreach($pin in $manifest.files.PSObject.Properties){
 if($pin.Name -match '(^|/)\.\.(/|$)' -or $pin.Name -match '^[/\\]'){throw 'Source manifest traversal refused.'}
 $path=[IO.Path]::GetFullPath((Join-Path $source $pin.Name.Replace('/','\')))
 if(!$path.StartsWith($sourcePrefix,[StringComparison]::OrdinalIgnoreCase) -or (Get-FileHash -LiteralPath $path).Hash.ToLowerInvariant() -cne $pin.Value.sha256){throw "Expanded Rhai source differs: $($pin.Name)"}
}
Copy-Item -LiteralPath $cargoProxy -Destination (Join-Path $source 'cargo.exe')
if((Get-FileHash -LiteralPath (Join-Path $source 'cargo.exe')).Hash.ToLowerInvariant() -cne $cargoHash){throw 'Private Cargo proxy copy differs.'}
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
if((Get-FileHash -LiteralPath (Join-Path $source 'cmd.exe')).Hash.ToLowerInvariant() -cne $cmdHash -or (Get-FileHash -LiteralPath (Join-Path $source 'Cargo.lock')).Hash.ToLowerInvariant() -cne '2ba4b3a0807e32b613ff2e972b893c3fd2e0923fd91803611963f09e93265425' -or (Get-FileHash -LiteralPath (Join-Path $source 'RunRhaiContract.cmd')).Hash.ToLowerInvariant() -cne '60d8f88be2bb03174d45341d70637e0cc6c7bd6380b9df313e12bb423846301a' -or (Get-FileHash -LiteralPath (Join-Path $source 'ClearOwnedWorkReadOnly.ps1')).Hash.ToLowerInvariant() -cne '121004581447d9e8f133d5d014d0eefb613d3d66688d6f235a5be28dfbd5bf34'){throw 'Private native contract inputs differ.'}
$copiedCargo=Join-Path $source 'cargo.exe'
if((& $copiedCargo --version) -cne $cargoVersion){throw 'Copied Cargo proxy resolved a different toolchain.'}
$record=[ordered]@{id=$id;guest_user=$env:USERNAME;source_commit=$manifest.source_commit;source_manifest_sha256='7b5634223c87e3984b02f4ba840bb03576c1e538155120bc380d3111d2fd57c4';archive_sha256='7f26d16f07eaa11a1ac3fa0a1f6fe947f8e49df68138055135451dd09ec754c0';source_files=442;lock_sha256='2ba4b3a0807e32b613ff2e972b893c3fd2e0923fd91803611963f09e93265425';contract_sha256='60d8f88be2bb03174d45341d70637e0cc6c7bd6380b9df313e12bb423846301a';attribute_control_sha256='121004581447d9e8f133d5d014d0eefb613d3d66688d6f235a5be28dfbd5bf34';cmd_exe_sha256=$cmdHash;powershell_exe_sha256=$powershellHash;fsutil_exe_sha256=$fsutilHash;cargo_proxy=$cargoProxy;cargo_sha256=$cargoHash;cargo_version=$cargoVersion;rustc_proxy=$rustcProxy;rustc_proxy_sha256=$cargoHash;rustc_version=$rustcVersion;public_build_manifest_sha256='90e10dd760e2d24eb9cb9dd2f5fc7028e4a3bb981f7a6280055682e9d0549116';own_scope=$session}
[IO.File]::WriteAllText((Join-Path $session 'preflight.json'),($record|ConvertTo-Json -Compress),[Text.UTF8Encoding]::new($false))
Write-Output 'PROJECT_SOURCE_PREFLIGHT_OK'
& ([scriptblock]::Create((Get-Content -LiteralPath $control -Raw))) -Session $session -SourceRoot $source -BuildRoot $build -Id $id -CargoSha256 $cargoHash
Write-Output 'PROJECT_COMMAND_CONTROL_COMPLETE;guest originals retained for independent export/readback and exact cleanup'
