param([switch]$NoBrowser)
$ErrorActionPreference = 'Stop'
$port = 8080
$url = "http://127.0.0.1:$port/"
$healthUrl = "${url}api/health"
$drive = $PSScriptRoot.Substring(0, 1).ToLowerInvariant()
$remainder = $PSScriptRoot.Substring(2).Replace('\', '/')
$linuxRoot = "/mnt/$drive$remainder"

try {
    $health = Invoke-RestMethod -Uri $healthUrl -TimeoutSec 2
    if ($health.ok) {
        Write-Host "MotionBricks is already running at $url. Use its existing browser tab."
        return
    }
} catch { }

$state = Join-Path $PSScriptRoot '.state'
New-Item -ItemType Directory -Path $state -Force | Out-Null
$log = Join-Path $state 'demo-8080.log'
$argumentLine = "-d Ubuntu -- bash `"$linuxRoot/run-demo.sh`" $port"
$process = Start-Process -FilePath wsl.exe -ArgumentList $argumentLine -WindowStyle Hidden -PassThru

for ($attempt = 0; $attempt -lt 60; $attempt++) {
    Start-Sleep -Seconds 1
    try {
        $health = Invoke-RestMethod -Uri $healthUrl -TimeoutSec 2
        if ($health.ok) {
            Write-Host "MotionBricks is running at $url"
            Write-Host 'Use W/A/S/D or the on-screen controls to move; choose a style from the menu.'
            if (-not $NoBrowser) { Start-Process $url }
            return
        }
    } catch { }
    if ($process.HasExited) { break }
}

$details = if (Test-Path $log) { Get-Content $log -Tail 20 | Out-String } else { '' }
throw "MotionBricks did not start. $details"
