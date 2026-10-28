param(
    [string]$InstallDir = "C:\agent-work"
)

$ErrorActionPreference = "Stop"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path

Write-Host "=== Hermes Operator Kit Installer ===" -ForegroundColor Cyan

# Ensure target directories
$libDir = Join-Path $InstallDir "lib"
$rulesDir = Join-Path $InstallDir "rules"
$configDir = Join-Path $InstallDir "config"
$policiesDir = Join-Path $InstallDir "policies"
$memoryDir = Join-Path $InstallDir "memory"
foreach ($d in @($libDir, $rulesDir, $configDir, $policiesDir, $memoryDir)) {
    if (-not (Test-Path $d)) { New-Item -ItemType Directory -Path $d -Force | Out-Null }
}

# Copy kit files (idempotent) — repository layout is kit/lib, kit/rules, kit/config, kit/policies
Copy-Item -Path (Join-Path $ScriptDir "kit\lib\*") -Destination $libDir -Recurse -Force
Copy-Item -Path (Join-Path $ScriptDir "kit\rules\*") -Destination $rulesDir -Recurse -Force
Copy-Item -Path (Join-Path $ScriptDir "kit\config\*") -Destination $configDir -Recurse -Force
Copy-Item -Path (Join-Path $ScriptDir "kit\policies\*") -Destination $policiesDir -Recurse -Force
Copy-Item -Path (Join-Path $ScriptDir "memory\HANDOFF.md") -Destination $memoryDir -Force

Write-Host "Installation complete." -ForegroundColor Green
Write-Host "Lib: $libDir"
Write-Host "Rules: $rulesDir"
Write-Host "Config: $configDir"
Write-Host "Policies: $policiesDir"
Write-Host "Memory: $memoryDir"
Write-Host "Run: python C:\agent-work\lib\safe_gui_ctl.py test winver"
