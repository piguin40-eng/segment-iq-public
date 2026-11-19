param(
  [string]$InstallRoot = (Join-Path $env:USERPROFILE 'Documents/DentalLabAgent'),
  [string]$Python = 'python',
  [string]$Blender = 'C:/Program Files/Blender Foundation/Blender 3.6/blender.exe',
  [switch]$EnableNetwork,
  [switch]$StartAtLogin,
  [switch]$NoDesktopShortcut
)
$ErrorActionPreference = 'Stop'
$packageRoot = $PSScriptRoot
$installAbsolute = [IO.Path]::GetFullPath($InstallRoot)
$appRoot = Join-Path $installAbsolute 'app'
$dataRoot = Join-Path $installAbsolute 'data'
$runtimeRoot = Join-Path $installAbsolute 'runtime'
New-Item -ItemType Directory -Force $appRoot,$dataRoot,$runtimeRoot | Out-Null
foreach ($entryName in @('dental_lab','engine','openclaw','docs','tests','scripts','assets','pyproject.toml','requirements-lock.txt','requirements-geometry.txt','README.md','Start-Lab.ps1','Install-Service.ps1','Open-SEGMENT-IQ.ps1','Create-DesktopShortcut.ps1','Setup-Models.ps1','Habilitar-Red.ps1')) {
  $entryPath = Join-Path $packageRoot $entryName
  if (Test-Path -LiteralPath $entryPath) { Copy-Item -LiteralPath $entryPath -Destination $appRoot -Recurse -Force }
}
$pythonEnv = Join-Path $runtimeRoot 'python'
$geometryEnv = Join-Path $runtimeRoot 'geometry-python'
if (-not (Test-Path -LiteralPath (Join-Path $pythonEnv 'Scripts/python.exe'))) { & $Python -m venv $pythonEnv; if ($LASTEXITCODE -ne 0) { throw 'No se pudo crear el entorno Python' } }
if (-not (Test-Path -LiteralPath (Join-Path $geometryEnv 'Scripts/python.exe'))) { & $Python -m venv $geometryEnv; if ($LASTEXITCODE -ne 0) { throw 'No se pudo crear el entorno de geometria' } }
$appPython = Join-Path $pythonEnv 'Scripts/python.exe'
$geomPython = Join-Path $geometryEnv 'Scripts/python.exe'
& $appPython -m pip install -r (Join-Path $appRoot 'requirements-lock.txt')
if ($LASTEXITCODE -ne 0) { throw 'Fallo al instalar dependencias del agente' }
& $geomPython -m pip install -r (Join-Path $appRoot 'requirements-geometry.txt')
if ($LASTEXITCODE -ne 0) { throw 'Fallo al instalar dependencias de geometria' }
$env:DENTAL_LAB_DATA=$dataRoot
Push-Location $appRoot
try { & $appPython -m dental_lab.cli status } finally { Pop-Location }
$configPath=Join-Path $dataRoot 'config.local.json'
$config=Get-Content -LiteralPath $configPath -Raw | ConvertFrom-Json
$config | Add-Member -NotePropertyName geometry_python -NotePropertyValue $geomPython -Force
$config | Add-Member -NotePropertyName blender -NotePropertyValue $Blender -Force
$config | ConvertTo-Json | Set-Content -LiteralPath $configPath -Encoding utf8
$starter=Join-Path $appRoot 'Start-Lab.ps1'
if ($EnableNetwork) {
  try {
    if (-not (Get-NetFirewallRule -DisplayName 'SEGMENT IQ red local' -ErrorAction SilentlyContinue)) {
      New-NetFirewallRule -DisplayName 'SEGMENT IQ red local' -Direction Inbound -Action Allow -Protocol TCP -LocalPort 8765 -RemoteAddress LocalSubnet -Profile Private,Domain | Out-Null
    }
  } catch { Write-Warning ('Regla de red pendiente: '+$_.Exception.Message) }
}
if ($StartAtLogin) {
  & (Join-Path $appRoot 'Install-Service.ps1') -InstallRoot $installAbsolute
  $startup=[Environment]::GetFolderPath('Startup')
  $shell=New-Object -ComObject WScript.Shell
  $shortcut=$shell.CreateShortcut((Join-Path $startup 'SEGMENT IQ.lnk'))
  $shortcut.TargetPath=(Get-Command powershell.exe).Source
  $shortcut.Arguments='-NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File "'+$starter+'" -InstallRoot "'+$installAbsolute+'"'
  $shortcut.WindowStyle=7;$shortcut.Save()
}
$access=Join-Path $installAbsolute 'ACCESO_LAB.txt'
if (-not $NoDesktopShortcut) {& (Join-Path $appRoot 'Create-DesktopShortcut.ps1') -InstallRoot $installAbsolute}
@("SEGMENT IQ",'Equipo: '+$env:COMPUTERNAME,'URL local: http://localhost:8765','URL red: http://'+$env:COMPUTERNAME+':8765','Usuario: '+$config.username,'Contrasena web: la configurada para este usuario. En una instalacion nueva, clave inicial de config.local.json (campo password).','Clave API: config.local.json (campo password).','Carpeta de entrada: '+(Join-Path $dataRoot 'inbox'),'No subir este archivo ni data/ a GitHub.') | Set-Content -LiteralPath $access -Encoding utf8
Write-Output ('Instalado: '+$installAbsolute)
Write-Output ('Datos de acceso: '+$access)
& $starter -InstallRoot $installAbsolute
