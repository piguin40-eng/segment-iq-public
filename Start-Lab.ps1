param([string]$InstallRoot=(Join-Path $env:USERPROFILE 'Documents/DentalLabAgent'))
$ErrorActionPreference='Stop'
$appRoot=Join-Path $InstallRoot 'app';$dataRoot=Join-Path $InstallRoot 'data'
New-Item -ItemType Directory -Force (Join-Path $dataRoot 'logs') | Out-Null
$env:DENTAL_LAB_DATA=$dataRoot;$env:OLLAMA_HOST='127.0.0.1:11434';$env:OLLAMA_MODELS=Join-Path $dataRoot 'models/ollama'
try { $llmRunning=(Invoke-WebRequest -UseBasicParsing -Uri 'http://127.0.0.1:11434/api/tags' -TimeoutSec 2).StatusCode -eq 200 } catch { $llmRunning=$false }
$ollama=Join-Path $InstallRoot 'runtime/ollama/ollama.exe'
if (-not $llmRunning -and (Test-Path -LiteralPath $ollama)) {
  Start-Process -FilePath $ollama -ArgumentList 'serve' -WindowStyle Hidden -RedirectStandardOutput (Join-Path $dataRoot 'logs/ollama.log') -RedirectStandardError (Join-Path $dataRoot 'logs/ollama.err.log')
}
try { $webRunning=(Invoke-WebRequest -UseBasicParsing -Uri 'http://127.0.0.1:8765/health' -TimeoutSec 2).StatusCode -eq 200 } catch { $webRunning=$false }
if (-not $webRunning) {
  $segmentTask=Get-ScheduledTask -TaskName 'SEGMENT IQ - Servidor del laboratorio' -ErrorAction SilentlyContinue
  if ($segmentTask) {Start-ScheduledTask -TaskName $segmentTask.TaskName}
  else {
    $appPython=Join-Path $InstallRoot 'runtime/python/Scripts/python.exe'
    Start-Process -FilePath $appPython -ArgumentList '-m dental_lab.cli serve --host 0.0.0.0 --port 8765' -WorkingDirectory $appRoot -WindowStyle Hidden -RedirectStandardOutput (Join-Path $dataRoot 'logs/server.log') -RedirectStandardError (Join-Path $dataRoot 'logs/server.err.log')
  }
}
