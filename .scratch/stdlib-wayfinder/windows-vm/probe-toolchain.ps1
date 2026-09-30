$port = New-Object System.IO.Ports.SerialPort COM1,115200,None,8,One
try {
    $port.Open()
    $port.WriteLine('RHAI_TOOLCHAIN_PROBE')
    $identity = [Security.Principal.WindowsIdentity]::GetCurrent()
    $principal = New-Object Security.Principal.WindowsPrincipal $identity
    $admin = $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
    $port.WriteLine("RHAI_GUEST_TOKEN User=$($identity.Name) Administrator=$admin")
    Get-Process | Where-Object ProcessName -Match 'setup|vs_|rustup|cargo|rustc' | ForEach-Object {
        $port.WriteLine("PROCESS $($_.ProcessName) Id=$($_.Id) CPU=$($_.CPU)")
    }
    Get-ChildItem "$env:TEMP\dd_*" -ErrorAction SilentlyContinue | Sort-Object LastWriteTime -Descending | Select-Object -First 3 | ForEach-Object {
        $port.WriteLine("INSTALL_LOG $($_.Name) Bytes=$($_.Length) Updated=$($_.LastWriteTime.ToString('o'))")
    }
} finally { $port.Dispose() }
