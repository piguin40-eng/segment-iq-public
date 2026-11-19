param([string]$InstallRoot=(Join-Path $env:USERPROFILE 'Documents/DentalLabAgent'))
$ErrorActionPreference='Stop'
$ollamaRoot=Join-Path $InstallRoot 'runtime/ollama'
New-Item -ItemType Directory -Force $ollamaRoot | Out-Null
if (-not (Test-Path -LiteralPath (Join-Path $ollamaRoot 'ollama.exe'))) {
  $version='v0.33.3'
  $baseUrl='https://github.com/ollama/ollama/releases/download/'+$version+'/'
  $archive=Join-Path $InstallRoot 'runtime/ollama-windows-amd64.zip'
  Invoke-WebRequest -UseBasicParsing -Uri ($baseUrl+'ollama-windows-amd64.zip') -OutFile $archive
  $sums=(Invoke-WebRequest -UseBasicParsing -Uri ($baseUrl+'sha256sum.txt')).Content
  $expected=(($sums -split "`n" | Where-Object { $_.Trim().EndsWith('ollama-windows-amd64.zip') }) -split '\s+')[0]
  if ((Get-FileHash -LiteralPath $archive -Algorithm SHA256).Hash.ToLowerInvariant() -ne $expected.ToLowerInvariant()) { throw 'SHA256 de Ollama incorrecto' }
  Expand-Archive -LiteralPath $archive -DestinationPath $ollamaRoot -Force
}
& (Join-Path $InstallRoot 'app/Start-Lab.ps1') -InstallRoot $InstallRoot
$env:DENTAL_LAB_DATA=Join-Path $InstallRoot 'data'
& (Join-Path $InstallRoot 'runtime/python/Scripts/python.exe') (Join-Path $PSScriptRoot 'scripts/prepare_models.py')
if ($LASTEXITCODE -ne 0) { throw 'Fallo al preparar modelos' }
