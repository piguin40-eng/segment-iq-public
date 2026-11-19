param([string]$InstallRoot=(Join-Path $env:USERPROFILE 'Documents/DentalLabAgent'))
$ErrorActionPreference='Stop'
$segmentRoot=[IO.Path]::GetFullPath($InstallRoot)
$segmentApp=Join-Path $segmentRoot 'app'
$segmentData=Join-Path $segmentRoot 'data'
$segmentPython=Join-Path $segmentRoot 'runtime/python/Scripts/pythonw.exe'
if (-not (Test-Path -LiteralPath $segmentPython)) {throw 'No se encuentra Python en la instalación de SEGMENT IQ.'}
if (-not (Test-Path -LiteralPath (Join-Path $segmentData 'config.local.json'))) {throw 'Falta la configuración privada del laboratorio.'}
$segmentUser=[Security.Principal.WindowsIdentity]::GetCurrent().Name
$segmentTask='SEGMENT IQ - Servidor del laboratorio'
$segmentArguments='-m dental_lab.service --data "'+$segmentData+'" --host 0.0.0.0 --port 8765'
$segmentAction=New-ScheduledTaskAction -Execute $segmentPython -Argument $segmentArguments -WorkingDirectory $segmentApp
$segmentTrigger=New-ScheduledTaskTrigger -AtLogOn -User $segmentUser
$segmentPrincipal=New-ScheduledTaskPrincipal -UserId $segmentUser -LogonType Interactive -RunLevel Limited
$segmentSettings=New-ScheduledTaskSettingsSet -ExecutionTimeLimit ([TimeSpan]::Zero) -RestartCount 10 -RestartInterval (New-TimeSpan -Minutes 1) -MultipleInstances IgnoreNew -StartWhenAvailable -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries
$segmentDefinition=New-ScheduledTask -Action $segmentAction -Trigger $segmentTrigger -Principal $segmentPrincipal -Settings $segmentSettings -Description 'Servidor local de SEGMENT IQ. Inicio al entrar en Windows y recuperación si el proceso falla. Datos privados del laboratorio; no requiere guardar contraseñas de Windows.'
Register-ScheduledTask -TaskName $segmentTask -InputObject $segmentDefinition -Force | Out-Null
Start-ScheduledTask -TaskName $segmentTask
Write-Output 'SEGMENT IQ: servidor registrado e iniciado con recuperación automática.'
