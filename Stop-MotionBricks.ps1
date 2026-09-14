$ErrorActionPreference = 'Stop'
$drive = $PSScriptRoot.Substring(0, 1).ToLowerInvariant()
$remainder = $PSScriptRoot.Substring(2).Replace('\', '/')
$linuxRoot = "/mnt/$drive$remainder"
& wsl.exe -d Ubuntu -- bash "$linuxRoot/stop-demo.sh" 8080
if ($LASTEXITCODE -ne 0) { throw 'The demo could not be stopped safely.' }
