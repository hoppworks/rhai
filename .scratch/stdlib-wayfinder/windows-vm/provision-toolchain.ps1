$ErrorActionPreference = 'Stop'
$root = 'C:\RhaiQuality'
New-Item -ItemType Directory -Force $root | Out-Null
Start-Transcript -Path "$root\provision-toolchain.log" -Append
function Report([string]$message) {
    Write-Host $message
    $port = New-Object System.IO.Ports.SerialPort COM1,115200,None,8,One
    try { $port.Open(); $port.WriteLine($message) } finally { $port.Dispose() }
}
try {
    Report 'RHAI_TOOLCHAIN_START'
    $vs = "$root\vs_buildtools.exe"
    Invoke-WebRequest -UseBasicParsing 'https://aka.ms/vs/17/release/vs_buildtools.exe' -OutFile $vs
    $signature = Get-AuthenticodeSignature $vs
    if ($signature.Status -ne 'Valid' -or $signature.SignerCertificate.Subject -notmatch 'Microsoft Corporation') {
        throw 'Build Tools bootstrapper signature validation failed'
    }
    Report 'RHAI_MSVC_INSTALL_START'
    $installer = Start-Process $vs -ArgumentList '--quiet --wait --norestart --nocache --installPath C:\BuildTools --add Microsoft.VisualStudio.Component.VC.Tools.x86.x64 --add Microsoft.VisualStudio.Component.Windows11SDK.26100 --addProductLang en-US' -Wait -PassThru
    Report "RHAI_MSVC_INSTALL_EXIT $($installer.ExitCode)"
    if ($installer.ExitCode -notin 0,3010) { throw "Build Tools exit $($installer.ExitCode)" }
    if (!(Test-Path 'C:\BuildTools\Common7\Tools\VsDevCmd.bat')) { throw 'Developer command prompt missing' }
    $rust = "$root\rustup-init.exe"
    Invoke-WebRequest -UseBasicParsing 'https://static.rust-lang.org/rustup/dist/x86_64-pc-windows-msvc/rustup-init.exe' -OutFile $rust
    Get-FileHash $rust -Algorithm SHA256
    # Match the accepted macOS toolchain for the initial cross-platform baseline.
    # The release toolchain/MSRV matrix remains an open planning decision.
    & $rust -y --default-host x86_64-pc-windows-msvc --default-toolchain 1.93.0 --profile minimal
    if ($LASTEXITCODE -ne 0) { throw "rustup exit $LASTEXITCODE" }
    $cargoBin = "$env:USERPROFILE\.cargo\bin"
    & "$cargoBin\rustc.exe" -Vv
    if ($LASTEXITCODE -ne 0) { throw 'rustc verification failed' }
    & "$cargoBin\cargo.exe" -V
    if ($LASTEXITCODE -ne 0) { throw 'cargo verification failed' }
    Report 'RHAI_TOOLCHAIN_READY Rust=1.93.0 Target=x86_64-pc-windows-msvc'
} catch {
    Report "RHAI_TOOLCHAIN_FAILED $($_.Exception.Message)"
    throw
} finally { Stop-Transcript }
