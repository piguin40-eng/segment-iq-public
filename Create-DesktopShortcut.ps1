param([string]$InstallRoot=(Join-Path $env:USERPROFILE 'Documents/DentalLabAgent'))
$ErrorActionPreference='Stop'
$segmentRoot=[IO.Path]::GetFullPath($InstallRoot)
$segmentLauncher=Join-Path $segmentRoot 'app/Open-SEGMENT-IQ.ps1'
if (-not (Test-Path -LiteralPath $segmentLauncher)) {throw 'Instala SEGMENT IQ antes de crear el acceso directo.'}
$segmentDesktop=[Environment]::GetFolderPath('Desktop')
$segmentShortcutPath=Join-Path $segmentDesktop 'SEGMENT IQ.lnk'
$segmentShell=New-Object -ComObject WScript.Shell
$segmentShortcut=$segmentShell.CreateShortcut($segmentShortcutPath)
$segmentShortcut.TargetPath=(Get-Command powershell.exe).Source
$segmentShortcut.Arguments='-NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File "'+$segmentLauncher+'" -InstallRoot "'+$segmentRoot+'"'
$segmentShortcut.WorkingDirectory=Join-Path $segmentRoot 'app'
$segmentShortcut.Description='SEGMENT IQ · Segmentación Blender, aprendizaje y correcciones del laboratorio'
$segmentIcon=Join-Path $segmentRoot 'app/assets/segment-iq.ico'
if (Test-Path -LiteralPath $segmentIcon) {$segmentShortcut.IconLocation=$segmentIcon+',0'}
$segmentShortcut.WindowStyle=7
$segmentShortcut.Save()
Write-Output $segmentShortcutPath
