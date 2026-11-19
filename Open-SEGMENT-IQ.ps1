param(
  [string]$InstallRoot=(Join-Path $env:USERPROFILE 'Documents/DentalLabAgent'),
  [switch]$NoBrowser
)
$ErrorActionPreference='Stop'
$segmentRoot=[IO.Path]::GetFullPath($InstallRoot)
$segmentApp=Join-Path $segmentRoot 'app'
$segmentUrl='http://127.0.0.1:8765/'
function Test-SegmentReady {
  try {
    $segmentResponse=Invoke-RestMethod -Uri ($segmentUrl+'health') -TimeoutSec 2
    return $segmentResponse.status -eq 'ok' -and $segmentResponse.service -eq 'SEGMENT IQ'
  } catch { return $false }
}
try {
  if (-not (Test-SegmentReady)) {
    $segmentStarter=Join-Path $segmentApp 'Start-Lab.ps1'
    if (-not (Test-Path -LiteralPath $segmentStarter)) {throw 'No se encuentra la instalación de SEGMENT IQ.'}
    # Windows starts this process independently of the terminal that opened the shortcut.
    $segmentStartup=New-CimInstance -ClassName Win32_ProcessStartup -ClientOnly -Property @{ShowWindow=[uint16]0}
    $segmentPowerShell=(Get-Command powershell.exe).Source
    $segmentCommand='"'+$segmentPowerShell+'" -NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File "'+$segmentStarter+'" -InstallRoot "'+$segmentRoot+'"'
    $segmentProcess=Invoke-CimMethod -ClassName Win32_Process -MethodName Create -Arguments @{CommandLine=$segmentCommand;CurrentDirectory=$segmentApp;ProcessStartupInformation=$segmentStartup}
    if ($segmentProcess.ReturnValue -ne 0) {throw ('No se pudo iniciar el servicio (código '+$segmentProcess.ReturnValue+').')}
    $segmentDeadline=[DateTime]::UtcNow.AddSeconds(35)
    while (-not (Test-SegmentReady)) {
      if ([DateTime]::UtcNow -gt $segmentDeadline) {throw 'El servicio no ha respondido. Consulta data/logs/server.err.log.'}
      Start-Sleep -Milliseconds 400
    }
  }
  if ($NoBrowser) {Write-Output 'SEGMENT IQ listo.'}
  else {Start-Process -FilePath $segmentUrl}
} catch {
  if ($NoBrowser) {throw}
  Add-Type -AssemblyName PresentationFramework
  [System.Windows.MessageBox]::Show($_.Exception.Message,'SEGMENT IQ','OK','Error') | Out-Null
  exit 1
}
