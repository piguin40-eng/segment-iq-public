# Ejecutar una vez como administrador para permitir el panel en la LAN del laboratorio.
$ErrorActionPreference='Stop'
$identity=[Security.Principal.WindowsIdentity]::GetCurrent()
$principal=New-Object Security.Principal.WindowsPrincipal($identity)
if (-not $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) { throw 'Windows exige administrador para crear esta regla del firewall. Abrir PowerShell como administrador y ejecutar este archivo.' }
if (-not (Get-NetFirewallRule -DisplayName 'SEGMENT IQ red local' -ErrorAction SilentlyContinue)) {
  New-NetFirewallRule -DisplayName 'SEGMENT IQ red local' -Direction Inbound -Action Allow -Protocol TCP -LocalPort 8765 -RemoteAddress LocalSubnet -Profile Private,Domain | Out-Null
}
Get-NetFirewallRule -DisplayName 'SEGMENT IQ red local' | Select-Object DisplayName,Enabled,Profile
