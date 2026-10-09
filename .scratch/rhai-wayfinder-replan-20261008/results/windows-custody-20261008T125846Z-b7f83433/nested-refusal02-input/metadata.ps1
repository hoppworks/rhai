$ErrorActionPreference='Stop'
$driver=Join-Path $env:USERPROFILE '.local\share\agent-builds\rhai\driver-wh02-af46729dd10c\run\monitor-source-af46729dd10c4493afc2264f240c8992\build\MonitorAcceptanceDriver.exe'
if((Get-FileHash -LiteralPath $driver).Hash.ToLowerInvariant() -cne 'caf4afaa2f604fb47fc554c82d9493854be0959c8d329bff7a88fd7fe9e827cb'){throw 'Retained Driver changed.'}
$a=[Reflection.Assembly]::LoadFile($driver)
$t=$a.GetType('MonitorAcceptanceDriver',$true)
$m=[Runtime.InteropServices.Marshal].GetMethod('SizeOf',[Type[]]@([Type]))
$sizes=@{int32=$m.Invoke($null,[object[]]@([int]))}
foreach($name in @('JobExtendedLimitInformation','JobBasicAccountingInformation')){
 $type=$t.GetNestedType($name,[Reflection.BindingFlags]'NonPublic')
 $sizes[$name]=$m.Invoke($null,[object[]]@($type))
}
if($sizes.int32 -ne 4 -or $sizes.JobExtendedLimitInformation -ne 144 -or $sizes.JobBasicAccountingInformation -ne 48){throw 'Unexpected native layout; no Driver or Job launched.'}
$sizes|ConvertTo-Json -Compress
