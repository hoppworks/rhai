$ErrorActionPreference = 'Stop'
function Report([string]$message) {
    $port = New-Object System.IO.Ports.SerialPort COM1,115200,None,8,One
    try { $port.Open(); $port.WriteLine($message) } finally { $port.Dispose() }
}
$group = Get-LocalGroup -SID 'S-1-5-32-544'
$account = Get-LocalUser -Name 'RhaiTest'
$member = Get-LocalGroupMember $group | Where-Object SID -EQ $account.SID
if (!$member) { throw 'RhaiTest is not the expected temporary administrator' }
Remove-LocalGroupMember -Group $group -Member $account
if (Get-LocalGroupMember $group | Where-Object SID -EQ $account.SID) {
    throw 'Temporary administration membership remains'
}
Report 'RHAI_TEMPORARY_ADMIN_REMOVED RhaiTest'
# Do not create or enable a new passwordless administrator. The previously
# verified WinRE/safe-mode Administrator recovery path is retained.
$builtin = Get-LocalUser | Where-Object { $_.SID.Value -Match '-500$' }
Report "RHAI_BUILTIN_ADMIN Enabled=$($builtin.Enabled)"
