$ErrorActionPreference='Stop'
$nonce='49243ecf52d64c609a876e3c52409500'
$id='rhai-project-command-'+$nonce
$marker='project-command-'+$nonce+'.bundle'
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
$control=Join-Path $media 'RunProjectCommandControl.ps1'
if((Get-FileHash -LiteralPath $archive).Hash.ToLowerInvariant() -cne '422507c89fef8094387a82e6af18d80453af1c56579ee12a55b332aaff30be93'){throw 'Frozen Rhai archive differs.'}
if((Get-FileHash -LiteralPath $manifestPath).Hash.ToLowerInvariant() -cne '1ed2dc76e988d82654f588e2c9e7c32c8526f2d888c44fbbaee9b996f7c847a1'){throw 'Frozen Rhai source manifest differs.'}
if((Get-FileHash -LiteralPath $control).Hash.ToLowerInvariant() -cne '50b8bb22866f18ae3f25f6ba47d40e18fb03ac043518b7e9e3b20c8899fbb01a'){throw 'Bounded native control differs.'}
$tokens=$null;$parseErrors=$null;$null=[Management.Automation.Language.Parser]::ParseFile($control,[ref]$tokens,[ref]$parseErrors)
if($parseErrors.Count -ne 0){throw ($parseErrors|Out-String)}
$manifest=Get-Content -LiteralPath $manifestPath -Raw|ConvertFrom-Json
if($manifest.source_commit -cne '25e78217dc75f4ccda64a16710ac1f53bee521cb' -or $manifest.file_count -ne 437 -or $manifest.total_source_bytes -ne 5088834 -or $manifest.archive_sha256 -cne '422507c89fef8094387a82e6af18d80453af1c56579ee12a55b332aaff30be93'){throw 'Frozen Rhai source identity differs.'}
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
$session=Join-Path $private ('project-control-'+$nonce)
$build=Join-Path $private 'backend-public-3cd277ed37eb4926b06e55c9c44279a4\run\monitor-source-3cd277ed37eb4926b06e55c9c44279a4\build'
if(!(Test-Path -LiteralPath $build -PathType Container)){throw 'Compatible native public build is absent.'}
if((Get-FileHash -LiteralPath (Join-Path ([IO.Directory]::GetParent($build).FullName) 'build-manifest.txt')).Hash.ToLowerInvariant() -cne '613361eba54c1edfaa0da576ccece3a6cb0009cfc4e35af582d46f967e1a320a'){throw 'Retained public build manifest differs from accepted readback.'}
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
$copiedCargo=Join-Path $source 'cargo.exe'
if((& $copiedCargo --version) -cne $cargoVersion){throw 'Copied Cargo proxy resolved a different toolchain.'}
$record=[ordered]@{id=$id;guest_user=$env:USERNAME;source_commit=$manifest.source_commit;source_manifest_sha256='1ed2dc76e988d82654f588e2c9e7c32c8526f2d888c44fbbaee9b996f7c847a1';archive_sha256='422507c89fef8094387a82e6af18d80453af1c56579ee12a55b332aaff30be93';source_files=437;cargo_proxy=$cargoProxy;cargo_sha256=$cargoHash;cargo_version=$cargoVersion;rustc_proxy=$rustcProxy;rustc_proxy_sha256=$cargoHash;rustc_version=$rustcVersion;public_build_manifest_sha256='613361eba54c1edfaa0da576ccece3a6cb0009cfc4e35af582d46f967e1a320a';own_scope=$session}
[IO.File]::WriteAllText((Join-Path $session 'preflight.json'),($record|ConvertTo-Json -Compress),[Text.UTF8Encoding]::new($false))
Write-Output 'PROJECT_SOURCE_PREFLIGHT_OK'
& ([scriptblock]::Create((Get-Content -LiteralPath $control -Raw))) -Session $session -SourceRoot $source -BuildRoot $build -Id $id -CargoSha256 $cargoHash
Write-Output 'PROJECT_COMMAND_CONTROL_COMPLETE;guest originals retained for independent export/readback and exact cleanup'
