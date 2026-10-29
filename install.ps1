param(
    [string]$InstallDir = "C:\\agent-work"
)

$ErrorActionPreference = "Stop"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path

Write-Host "=== Hermes Operator Kit Installer ===" -ForegroundColor Cyan

# Ensure target directories
$libDir      = Join-Path $InstallDir "lib"
$rulesDir    = Join-Path $InstallDir "rules"
$configDir   = Join-Path $InstallDir "config"
$policiesDir = Join-Path $InstallDir "policies"
$memoryDir   = Join-Path $InstallDir "memory"
$logsDir     = Join-Path $InstallDir "logs"
$tmpDir      = Join-Path $InstallDir "tmp"

foreach ($d in @($libDir, $rulesDir, $configDir, $policiesDir, $memoryDir, $logsDir, $tmpDir)) {
    if (-not (Test-Path $d)) { New-Item -ItemType Directory -Path $d -Force | Out-Null }
}

# Copy kit files (idempotent) - repository layout is kit/lib, kit/rules, kit/config, kit/policies
Copy-Item -Path (Join-Path $ScriptDir "kit\\lib\\*")      -Destination $libDir      -Recurse -Force
Copy-Item -Path (Join-Path $ScriptDir "kit\\rules\\*")    -Destination $rulesDir    -Recurse -Force
Copy-Item -Path (Join-Path $ScriptDir "kit\\config\\*")   -Destination $configDir   -Recurse -Force
Copy-Item -Path (Join-Path $ScriptDir "kit\\policies\\*") -Destination $policiesDir -Recurse -Force

# Copy template files for personal data - ONLY if not already present (preserve user data)
$templateDir = Join-Path $ScriptDir "kit\\templates"

# Memory templates
$handOffTemplate = Join-Path $templateDir "memory\\HANDOFF.template.md"
$handOffTarget   = Join-Path $memoryDir   "HANDOFF.md"
if (-not (Test-Path $handOffTarget)) {
    Copy-Item -Path $handOffTemplate -Destination $handOffTarget -Force
    Write-Host "Created: $handOffTarget (from template)" -ForegroundColor Yellow
}

$lastLaunchedTemplate = Join-Path $templateDir "memory\\last_launched_apps.template.txt"
$lastLaunchedTarget   = Join-Path $memoryDir   "last_launched_apps.txt"
if (-not (Test-Path $lastLaunchedTarget)) {
    Copy-Item -Path $lastLaunchedTemplate -Destination $lastLaunchedTarget -Force
    Write-Host "Created: $lastLaunchedTarget (from template)" -ForegroundColor Yellow
}

# Environment template
$envExample = Join-Path $templateDir ".env.example"
$envTarget  = Join-Path $InstallDir ".env"
if (-not (Test-Path $envTarget)) {
    Copy-Item -Path $envExample -Destination $envTarget -Force
    Write-Host "Created: $envTarget (from .env.example) - EDIT TO ADD YOUR API KEYS" -ForegroundColor Yellow
}

# Logs and tmp directories (with .gitkeep)
Copy-Item -Path (Join-Path $templateDir "logs\\*") -Destination $logsDir -Recurse -Force
Copy-Item -Path (Join-Path $templateDir "tmp\\*")  -Destination $tmpDir  -Recurse -Force

Write-Host "`nInstallation complete." -ForegroundColor Green
Write-Host "Lib:      $libDir"
Write-Host "Rules:    $rulesDir"
Write-Host "Config:   $configDir"
Write-Host "Policies: $policiesDir"
Write-Host "Memory:   $memoryDir (templates copied, your data preserved)"
Write-Host "Logs:     $logsDir"
Write-Host "Tmp:      $tmpDir"
Write-Host "`nNext steps:"
Write-Host "  1. Edit $envTarget and add your API keys (NVIDIA_API_KEY, etc.)"
Write-Host "  2. Run: python C:\\agent-work\\lib\\safe_gui_ctl.py test winver"
