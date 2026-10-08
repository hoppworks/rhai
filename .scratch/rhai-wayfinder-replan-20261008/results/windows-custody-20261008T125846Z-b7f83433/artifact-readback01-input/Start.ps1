$ErrorActionPreference='Stop'
$id='rhai-artifact-readback01-20261008T125846Z-b7f83433'
$run=Join-Path $env:USERPROFILE '.local\share\agent-builds\rhai\cap-g05-b7f83433\run\monitor-source-497d77ab72bb4928bd7eacad0e4858b3'
$pins=@{
'tools/windows-scoped-runner/LaunchSpecification.cs'='e08957b13d5ed5f86cb37d0545aa876aac50e507692d112b39882f465fff8f2b'
'tools/windows-scoped-runner/LeaseMonitor.cs'='72c79f18c96e28f27cd1b7b39b1025da9a250e0608885de7dc48934512a46bfc'
'tools/windows-scoped-runner/MonitorAcceptanceDriver.cs'='4b4a41789223fb20395f5c1dbe041d8407a57c9cc978e53d7f22ff6bab42b492'
'tools/windows-scoped-runner/MonitorPayloadJob.cs'='ac5c62bdcd4402b1f103131e082ab6e35a6d979b80629ea6ffef82b386f2353b'
'tools/windows-scoped-runner/MonitorSpecificationIntake.cs'='0f0a71563e6c3d99f0c643644d4b56951f6c69ceb3b10b03157f68dc37bb8412'
'tools/windows-scoped-runner/MonitorStagingHandoff.cs'='c541f7d885d032c074461a5a0173b9ae6291ef7d8cd1b9fd2ce4a4f56d1e0e6e'
'tools/windows-scoped-runner/MonitorTransport.cs'='ed23c8615af7d8c1b545d3108342640c46f7e245b4e6a83a7c98bf1720a74de8'
'tools/windows-scoped-runner/ScopedRunner.cs'='d3a77f0daeebd5beed2b277fae9dc6a522acf1454bb5d8d776d84e1dc8e896c8'
'tools/windows-scoped-runner/SpecificationTransfer.cs'='7a9edfe98d84868b55146280bd5ed29576ee0c8725cf9f6c785b784bc0ad25c2'
'tools/windows-scoped-runner/WindowsCustodyBackend.cs'='ba8c3a97fb07e424f18db33bfe814f00f9d9034a6de39094235dc7429b8724a2'
'tools/windows-scoped-runner/fixtures/CustodyBackendFixture.cs'='1cd3885d596ab5c847ab9d7f38a8c3a821860a445839b128153f4ec10fb88d8a'
'tools/windows-scoped-runner/fixtures/NativeScopePolicyFixture.cs'='8f43d33928262ae181aa5396feffef9b0260653609b5be8b01da7b0a7e7b00f7'
'tools/windows-scoped-runner/fixtures/PayloadFixture.cs'='e806b393f9f7fe24d349879e70ff247479592373831a1eb30f55e5950d341676'
'tools/windows-scoped-runner/fixtures/MonitorAcceptanceDriverFixture.cs'='1040e99ea83a43428993b2422aad4cffc373fdcbe99ea6b460db13beb23ffe61'
}
$sourceChecks=@()
foreach($relative in $pins.Keys){$p=Join-Path (Join-Path $run 'input') $relative;$sha=(Get-FileHash -LiteralPath $p).Hash.ToLowerInvariant();if($sha -cne $pins[$relative]){throw ('Retained source changed: '+$relative)};$sourceChecks+=@{path=$relative;sha256=$sha}}
$artifacts=@()
foreach($name in @('ScopedRunner.exe','MonitorAcceptanceDriver.exe','PayloadFixture.exe')){$p=Join-Path (Join-Path $run 'build') $name;$f=Get-Item -LiteralPath $p;if($f.Attributes -band [IO.FileAttributes]::ReparsePoint){throw 'Retained artifact is a reparse point.'};$artifacts+=@{name=$name;length=$f.Length;sha256=(Get-FileHash -LiteralPath $p).Hash.ToLowerInvariant()}}
$active=@(Get-Process csc,ScopedRunner,MonitorAcceptanceDriver,PayloadFixture -ErrorAction SilentlyContinue|Select-Object Id,ProcessName)
$r=[ordered]@{id=$id;run=$run;compiler_sha256=(Get-FileHash 'C:\BuildTools\MSBuild\Current\Bin\Roslyn\csc.exe').Hash.ToLowerInvariant();sources=$sourceChecks;artifacts=$artifacts;active=$active;read_only=$true;no_run=$true}
$j=$r|ConvertTo-Json -Compress -Depth 6
if([Text.Encoding]::UTF8.GetByteCount($j) -gt 12000){throw 'Readback exceeds declared export bound.'}
$p=[IO.Ports.SerialPort]::new('COM1',115200);$p.WriteTimeout=2000
try{$p.Open();$p.WriteLine('RHAI_ARTIFACT '+$j)}finally{$p.Dispose()}
$j
