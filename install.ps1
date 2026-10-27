param(
    [string]$RepoUrl = "https://codeload.github.com/Masoudalk/hermes-operator-kit/zip/refs/tags/v1.0.0",
    [string]$InstallDir = "C:\agent-work"
)

$ErrorActionPreference = "Stop"

# Self-discovery: if kit\lib not beside this script, download and re-run
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$KitLib = Join-Path $ScriptDir "kit\lib"
if (-not (Test-Path $KitLib)) {
    Write-Host "Kit not found locally. Downloading from $RepoUrl ..."
    $tmp = Join-Path $env:TEMP "hermes-operator-kit-download"
    if (Test-Path $tmp) { Remove-Item -Recurse -Force $tmp }
    New-Item -ItemType Directory -Path $tmp | Out-Null
    $zipPath = Join-Path $tmp "kit.zip"
    Invoke-WebRequest -Uri $RepoUrl -OutFile $zipPath -UseBasicParsing
    Expand-Archive -Path $zipPath -DestinationPath $tmp -Force
    $inner = Get-ChildItem -Path $tmp -Directory | Where-Object { $_.Name -like "hermes-operator-kit*" } | Select-Object -First 1
    if (-not $inner) { $inner = Get-ChildItem -Path $tmp -Directory | Select-Object -First 1 }
    $innerScript = Join-Path $inner.FullName "install.ps1"
    if (Test-Path $innerScript) {
        & $innerScript -RepoUrl $RepoUrl -InstallDir $InstallDir
        exit $LASTEXITCODE
    } else {
        Write-Error "install.ps1 not found in downloaded archive"
        exit 1
    }
}

Write-Host "=== Hermes Operator Kit Installer ===" -ForegroundColor Cyan

# Ensure target directories
$libDir = Join-Path $InstallDir "lib"
$rulesDir = Join-Path $InstallDir "rules"
$configDir = Join-Path $InstallDir "config"
$skillsDir = Join-Path $InstallDir "skills\desktop\safe-gui-launcher"
foreach ($d in @($libDir, $rulesDir, $configDir, $skillsDir)) {
    if (-not (Test-Path $d)) { New-Item -ItemType Directory -Path $d -Force | Out-Null }
}

# Copy kit files (idempotent)
$kitRoot = Join-Path $ScriptDir "kit"
Copy-Item -Path (Join-Path $kitRoot "lib\*") -Destination $libDir -Recurse -Force
Copy-Item -Path (Join-Path $kitRoot "rules\*") -Destination $rulesDir -Recurse -Force
Copy-Item -Path (Join-Path $kitRoot "config\*") -Destination $configDir -Recurse -Force
if (Test-Path (Join-Path $kitRoot "skills\safe-gui-launcher\SKILL.md")) {
    Copy-Item -Path (Join-Path $kitRoot "skills\safe-gui-launcher\SKILL.md") -Destination $skillsDir -Force
}

Write-Host "Installation complete." -ForegroundColor Green
Write-Host "Lib: $libDir"
Write-Host "Rules: $rulesDir"