$ErrorActionPreference = "Stop"

Set-ItemProperty -Path HKLM:\SYSTEM\CurrentControlSet\Control\FileSystem -Name LongPathsEnabled -Value 1

Add-WindowsCapability -Online -Name OpenSSH.Server~~~~0.0.1.0
Set-Service -Name sshd -StartupType Automatic
Start-Service -Name sshd
if (-not (Get-NetFirewallRule -Name OpenSSH-Server-In-TCP -ErrorAction SilentlyContinue)) {
    New-NetFirewallRule -Name OpenSSH-Server-In-TCP -DisplayName "OpenSSH Server" -Protocol TCP -LocalPort 22 `
        -Action Allow -Direction Inbound
}
New-ItemProperty -Path HKLM:\SOFTWARE\OpenSSH -Name DefaultShell -PropertyType String -Force `
    -Value "$env:SystemRoot\System32\WindowsPowerShell\v1.0\powershell.exe"
# sshd ignores ~\.ssh\authorized_keys for administrators and rejects this file if anyone else can write it
$keys = "$env:ProgramData\ssh\administrators_authorized_keys"
Copy-Item -Path "$PSScriptRoot\authorized_keys" -Destination $keys
icacls.exe $keys /inheritance:r /grant "*S-1-5-32-544:F" /grant "*S-1-5-18:F"

Invoke-RestMethod https://astral.sh/uv/install.ps1 | Invoke-Expression
$uv = "$env:USERPROFILE\.local\bin\uv.exe"
& $uv python install 3.11 3.12 3.13 3.14 3.15
& $uv tool install tox --with tox-uv

winget install --id Git.Git --exact --silent --accept-source-agreements --accept-package-agreements
# sshd started before the installers changed PATH, and SSH sessions inherit its environment
Restart-Service -Name sshd
