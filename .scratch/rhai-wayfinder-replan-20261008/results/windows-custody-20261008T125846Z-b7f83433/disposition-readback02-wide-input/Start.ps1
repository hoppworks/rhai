$ErrorActionPreference='Stop'
$id='rhai-disposition-readback02-20261008T125846Z-b7f83433'
$queryErrors=@(); $events=@(Get-WinEvent -LogName Application -MaxEvents 256 -ErrorAction SilentlyContinue -ErrorVariable +queryErrors | Where-Object { $_.Message -match 'Job disposition failed|Watchdog timer refused disposal|Watchdog callback did not drain|CloseHandle\(job\)' } | Select-Object -First 4 TimeCreated,RecordId,Id,ProviderName,Message)
$r=[ordered]@{id=$id;guest_utc=(Get-Date).ToUniversalTime().ToString('o');query_errors=@($queryErrors|ForEach-Object{$_.ToString()});events=$events;active=@(Get-Process cargo,rustc,csc,ScopedRunner,MonitorAcceptanceDriver,PayloadFixture -ErrorAction SilentlyContinue|Select-Object Id,ProcessName);read_only=$true;no_run=$true}
$j=$r|ConvertTo-Json -Compress -Depth 6
if([Text.Encoding]::UTF8.GetByteCount($j) -gt 12000){throw 'Own event diagnostic exceeds declared export bound.'}
$p=[IO.Ports.SerialPort]::new('COM1',115200);$p.WriteTimeout=2000
try{$p.Open();$p.WriteLine('RHAI_DISPOSITION '+$j)}finally{$p.Dispose()}
$j
