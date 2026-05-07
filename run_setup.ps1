# ImportYeti MCP — PowerShell Setup
# Right-click this file > Run with PowerShell
# This patches claude_desktop_config.json and installs Python packages.

$ErrorActionPreference = "Stop"

# ── Paths ──────────────────────────────────────────────────────────────────────
$scriptDir   = Split-Path -Parent $MyInvocation.MyCommand.Path
$mcpServer   = Join-Path $scriptDir "importyeti_mcp.py"
$configPath  = Join-Path $env:APPDATA "Claude\claude_desktop_config.json"

# ── CONFIGURE THESE TWO VALUES BEFORE RUNNING ──────────────────────────────────
# Find your Python path by running: (Get-Command python).Source
$pythonExe   = "C:\Path\To\Your\python.exe"  # <-- UPDATE THIS

# Get your API key from importyeti.com/yeti-api
$apiKey      = $env:IMPORTYETI_API_KEY        # Set as env var, or replace with your key string
if (-not $apiKey) {
    Write-Host "ERROR: IMPORTYETI_API_KEY environment variable is not set." -ForegroundColor Red
    Write-Host "Run: `$env:IMPORTYETI_API_KEY = 'your_key_here'  then re-run this script."
    Read-Host "Press Enter to exit"
    exit 1
}
# ───────────────────────────────────────────────────────────────────────────────

Write-Host ""
Write-Host "=== ImportYeti MCP Setup ===" -ForegroundColor Cyan

# ── Verify importyeti_mcp.py exists ────────────────────────────────────────────
if (-not (Test-Path $mcpServer)) {
    Write-Host "ERROR: importyeti_mcp.py not found at $mcpServer" -ForegroundColor Red
    Write-Host "Make sure this script is in the same folder as importyeti_mcp.py."
    Read-Host "Press Enter to exit"
    exit 1
}

# ── Verify Python exists ────────────────────────────────────────────────────────
if (-not (Test-Path $pythonExe)) {
    Write-Host "ERROR: Python not found at $pythonExe" -ForegroundColor Red
    Write-Host "Update the `$pythonExe path in this script to match your Python install."
    Read-Host "Press Enter to exit"
    exit 1
}

$pythonVersion = & $pythonExe --version 2>&1
Write-Host "Python found: $pythonVersion at $pythonExe" -ForegroundColor Green

# ── Install Python dependencies ─────────────────────────────────────────────────
Write-Host ""
Write-Host "Installing Python packages (mcp[cli], httpx, pydantic)..." -ForegroundColor Yellow
& $pythonExe -m pip install "mcp[cli]" httpx pydantic --quiet
if ($LASTEXITCODE -eq 0) {
    Write-Host "Packages installed successfully." -ForegroundColor Green
} else {
    Write-Host "Package install returned a non-zero exit code. Continuing anyway (may already be installed)." -ForegroundColor Yellow
}

# ── Backup and read existing config ─────────────────────────────────────────────
$configDir = Split-Path -Parent $configPath
if (-not (Test-Path $configDir)) {
    New-Item -ItemType Directory -Path $configDir | Out-Null
}

if (Test-Path $configPath) {
    $timestamp  = Get-Date -Format "yyyyMMdd_HHmmss"
    $backupPath = Join-Path $configDir "claude_desktop_config.backup_$timestamp.json"
    Copy-Item $configPath $backupPath
    Write-Host ""
    Write-Host "Backup saved: $backupPath" -ForegroundColor Gray

    try {
        $config = Get-Content $configPath -Raw | ConvertFrom-Json
    } catch {
        Write-Host "Existing config has invalid JSON. Starting fresh." -ForegroundColor Yellow
        $config = [PSCustomObject]@{}
    }
} else {
    Write-Host "No existing config found. Creating new one." -ForegroundColor Yellow
    $config = [PSCustomObject]@{}
}

# ── Inject ImportYeti server entry ──────────────────────────────────────────────
if (-not ($config.PSObject.Properties.Name -contains "mcpServers")) {
    $config | Add-Member -MemberType NoteProperty -Name "mcpServers" -Value ([PSCustomObject]@{})
}

$importyetiEntry = [PSCustomObject]@{
    command = $pythonExe
    args    = @($mcpServer)
    env     = [PSCustomObject]@{
        IMPORTYETI_API_KEY = $apiKey
    }
}

if ($config.mcpServers.PSObject.Properties.Name -contains "importyeti") {
    $config.mcpServers.importyeti = $importyetiEntry
    Write-Host ""
    Write-Host "Updated existing importyeti entry in config." -ForegroundColor Green
} else {
    $config.mcpServers | Add-Member -MemberType NoteProperty -Name "importyeti" -Value $importyetiEntry
    Write-Host ""
    Write-Host "Added importyeti entry to config." -ForegroundColor Green
}

# ── Write updated config ─────────────────────────────────────────────────────────
$config | ConvertTo-Json -Depth 10 | Set-Content $configPath -Encoding UTF8
Write-Host "Config written to: $configPath" -ForegroundColor Green

# ── Verify the written config is valid JSON ──────────────────────────────────────
try {
    $verify = Get-Content $configPath -Raw | ConvertFrom-Json
    Write-Host "Config validation: PASSED (valid JSON)" -ForegroundColor Green
} catch {
    Write-Host "Config validation: FAILED — JSON is invalid after write." -ForegroundColor Red
    Write-Host "Restoring backup..."
    Copy-Item $backupPath $configPath
    Write-Host "Backup restored. Check the config manually."
    Read-Host "Press Enter to exit"
    exit 1
}

# ── Summary ──────────────────────────────────────────────────────────────────────
Write-Host ""
Write-Host "=== Setup Complete ===" -ForegroundColor Cyan
Write-Host "  MCP server : $mcpServer"
Write-Host "  Config file: $configPath"
Write-Host "  Python     : $pythonExe"
Write-Host "  API key    : $($apiKey.Substring(0,12))..."
Write-Host ""
Write-Host "Next step: Fully quit Claude Desktop (check system tray), then relaunch it." -ForegroundColor Yellow
Write-Host "The ImportYeti tools will appear once Claude restarts." -ForegroundColor Yellow
Write-Host ""
Read-Host "Press Enter to exit"
