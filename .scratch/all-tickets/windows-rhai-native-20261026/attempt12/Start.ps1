$ErrorActionPreference='Stop'
$nonce='ee369f78f6c44ca8a5a7c9abe3a9ba99'
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
if((Get-FileHash -LiteralPath $archive).Hash.ToLowerInvariant() -cne '09e58d48725560bed1b7164bb0b930ddeeeda07eabc42f35a0c9e28d13d3c5ae'){throw 'Frozen Rhai archive differs.'}
if((Get-FileHash -LiteralPath $manifestPath).Hash.ToLowerInvariant() -cne 'a7b6c7c9c6a7243aff406bfdb6f62dbb8006ad70e9e86a283a59dc0d02d2d251'){throw 'Frozen Rhai source manifest differs.'}
if((Get-FileHash -LiteralPath $control).Hash.ToLowerInvariant() -cne 'f3de5810880d000107447f95dff40b9c4f260c8cc01e965c7aa0ad7623f16583'){throw 'Bounded native control differs.'}
if((Get-FileHash -LiteralPath $lock).Hash.ToLowerInvariant() -cne '12084a90214418632e80bbaf95983925c2c3886f57f40e2a305b4a1ec353d802'){throw 'Accepted lock differs.'}
if((Get-FileHash -LiteralPath $contract).Hash.ToLowerInvariant() -cne '18fb77a0f08e9e14670d21ad76abaea7512cf7475bf6e4be4f9d5e8fae64cad9'){throw 'Native Rhai contract differs.'}
if((Get-FileHash -LiteralPath $attributeControl).Hash.ToLowerInvariant() -cne '0615fa1d025fa9dce8deb4a4388550889f42ab4fd5403545eac4af8e2f2a5661'){throw 'Owned work attribute control differs.'}
$tokens=$null;$parseErrors=$null;$null=[Management.Automation.Language.Parser]::ParseFile($control,[ref]$tokens,[ref]$parseErrors)
if($parseErrors.Count -ne 0){throw ($parseErrors|Out-String)}
$manifest=Get-Content -LiteralPath $manifestPath -Raw|ConvertFrom-Json
if($manifest.source_commit -cne '6f052eb3835bd3fd5f2911dea9593c6b97c3085c' -or $manifest.file_count -ne 439 -or $manifest.total_source_bytes -ne 5130849 -or $manifest.archive_sha256 -cne '09e58d48725560bed1b7164bb0b930ddeeeda07eabc42f35a0c9e28d13d3c5ae'){throw 'Frozen Rhai source identity differs.'}
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
$build=Join-Path $private 'public-refresh-47066f0d4e2a4f8bb45f1e62e8f7e5ad\run\monitor-source-47066f0d4e2a4f8bb45f1e62e8f7e5ad\build'
if(!(Test-Path -LiteralPath $build -PathType Container)){throw 'Compatible native public build is absent.'}
if((Get-FileHash -LiteralPath (Join-Path ([IO.Directory]::GetParent($build).FullName) 'build-manifest.txt')).Hash.ToLowerInvariant() -cne '63145b571f26bdfb4c482231259374557f87c1b9a1b48ddbd51b6f98377dab7c'){throw 'Retained public build manifest differs from accepted readback.'}
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
if($actual.Count -ne 439 -or ($actual -join "`n") -cne ($expected -join "`n")){throw 'Expanded Rhai source inventory differs.'}
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
if((Get-FileHash -LiteralPath (Join-Path $source 'cmd.exe')).Hash.ToLowerInvariant() -cne $cmdHash -or (Get-FileHash -LiteralPath (Join-Path $source 'Cargo.lock')).Hash.ToLowerInvariant() -cne '12084a90214418632e80bbaf95983925c2c3886f57f40e2a305b4a1ec353d802' -or (Get-FileHash -LiteralPath (Join-Path $source 'RunRhaiContract.cmd')).Hash.ToLowerInvariant() -cne '18fb77a0f08e9e14670d21ad76abaea7512cf7475bf6e4be4f9d5e8fae64cad9' -or (Get-FileHash -LiteralPath (Join-Path $source 'ClearOwnedWorkReadOnly.ps1')).Hash.ToLowerInvariant() -cne '0615fa1d025fa9dce8deb4a4388550889f42ab4fd5403545eac4af8e2f2a5661'){throw 'Private native contract inputs differ.'}
$copiedCargo=Join-Path $source 'cargo.exe'
if((& $copiedCargo --version) -cne $cargoVersion){throw 'Copied Cargo proxy resolved a different toolchain.'}
$record=[ordered]@{id=$id;guest_user=$env:USERNAME;source_commit=$manifest.source_commit;source_manifest_sha256='a7b6c7c9c6a7243aff406bfdb6f62dbb8006ad70e9e86a283a59dc0d02d2d251';archive_sha256='09e58d48725560bed1b7164bb0b930ddeeeda07eabc42f35a0c9e28d13d3c5ae';source_files=444;lock_sha256='12084a90214418632e80bbaf95983925c2c3886f57f40e2a305b4a1ec353d802';contract_sha256='18fb77a0f08e9e14670d21ad76abaea7512cf7475bf6e4be4f9d5e8fae64cad9';attribute_control_sha256='0615fa1d025fa9dce8deb4a4388550889f42ab4fd5403545eac4af8e2f2a5661';cmd_exe_sha256=$cmdHash;powershell_exe_sha256=$powershellHash;fsutil_exe_sha256=$fsutilHash;cargo_proxy=$cargoProxy;cargo_sha256=$cargoHash;cargo_version=$cargoVersion;rustc_proxy=$rustcProxy;rustc_proxy_sha256=$cargoHash;rustc_version=$rustcVersion;public_build_manifest_sha256='63145b571f26bdfb4c482231259374557f87c1b9a1b48ddbd51b6f98377dab7c';own_scope=$session}
[IO.File]::WriteAllText((Join-Path $session 'preflight.json'),($record|ConvertTo-Json -Compress),[Text.UTF8Encoding]::new($false))
Write-Output 'PROJECT_SOURCE_PREFLIGHT_OK'
& ([scriptblock]::Create((Get-Content -LiteralPath $control -Raw))) -Session $session -SourceRoot $source -BuildRoot $build -Id $id -CargoSha256 $cargoHash
Write-Output 'PROJECT_COMMAND_CONTROL_COMPLETE;guest originals retained for independent export/readback and exact cleanup'
