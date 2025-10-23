# Hansard MCP STDIO Quickstart Script (Windows)
# Purpose: Automated local setup for Gemini CLI + Hansard MCP server
# Platform: Windows 10+, PowerShell 5.1+
# Usage: PowerShell.exe -ExecutionPolicy Bypass -File stdio-quickstart.ps1

param(
    [switch]$SkipDatabaseInit = $false
)

$ErrorActionPreference = "Stop"

Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "Hansard MCP STDIO Quickstart (Windows)" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host ""

# Detect project directory
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectRoot = (Resolve-Path "$ScriptDir\..\..\..").Path
$ProjectRoot = $ProjectRoot -replace '\\', '/'  # Convert to forward slashes for JSON

Write-Host "Project directory: $ProjectRoot"
Write-Host ""

# Step 1: Check prerequisites
Write-Host "[1/6] Checking prerequisites..." -ForegroundColor Yellow

# Check Gemini CLI
$GeminiPath = Get-Command gemini -ErrorAction SilentlyContinue
if (-not $GeminiPath) {
    Write-Host "ERROR: Gemini CLI not found. Install with: npm install -g @google/gemini-cli" -ForegroundColor Red
    exit 1
}
$GeminiVersion = & gemini --version 2>&1
Write-Host "  ✓ Gemini CLI found: $GeminiVersion" -ForegroundColor Green

# Check Python
$PythonPath = Get-Command python -ErrorAction SilentlyContinue
if (-not $PythonPath) {
    $PythonPath = Get-Command python3 -ErrorAction SilentlyContinue
}
if (-not $PythonPath) {
    Write-Host "ERROR: Python not found. Install Python 3.11+ from python.org" -ForegroundColor Red
    exit 1
}
$PythonVersion = & python --version 2>&1
Write-Host "  ✓ Python found: $PythonVersion" -ForegroundColor Green

# Check FastMCP
$FastMCPPath = Get-Command fastmcp -ErrorAction SilentlyContinue
if (-not $FastMCPPath) {
    Write-Host "ERROR: FastMCP not found. Run 'uv sync' in project directory" -ForegroundColor Red
    exit 1
}
$FastMCPFullPath = $FastMCPPath.Source -replace '\\', '/'
Write-Host "  ✓ FastMCP found: $FastMCPFullPath" -ForegroundColor Green

# Check uv
$UvPath = Get-Command uv -ErrorAction SilentlyContinue
if (-not $UvPath) {
    Write-Host "  WARNING: uv package manager not found. Install from https://astral.sh/uv" -ForegroundColor Yellow
} else {
    $UvVersion = & uv --version 2>&1
    Write-Host "  ✓ uv found: $UvVersion" -ForegroundColor Green
}

Write-Host ""

# Step 2: Initialize database (optional)
Write-Host "[2/6] Database setup..." -ForegroundColor Yellow

$DatabasePath = "$ProjectRoot/data/hansard.db" -replace '/', '\'
if (Test-Path $DatabasePath) {
    Write-Host "  ✓ Database already exists at: $DatabasePath" -ForegroundColor Green
    # Try to count speeches (requires sqlite3 CLI)
    $SqlitePath = Get-Command sqlite3 -ErrorAction SilentlyContinue
    if ($SqlitePath) {
        try {
            $SpeechCount = & sqlite3 $DatabasePath "SELECT COUNT(*) FROM speeches;" 2>$null
            Write-Host "  ✓ Database contains $SpeechCount speeches" -ForegroundColor Green
        } catch {
            Write-Host "  ! Could not query database" -ForegroundColor Yellow
        }
    }
} else {
    Write-Host "  ! Database not found. Creating directory..." -ForegroundColor Yellow
    New-Item -Path "$ProjectRoot/data" -ItemType Directory -Force | Out-Null

    if (-not $SkipDatabaseInit) {
        $InitScript = "$ProjectRoot/scripts/init_database.py" -replace '/', '\'
        if (Test-Path $InitScript) {
            Write-Host "  ! Initializing local database..." -ForegroundColor Yellow
            Push-Location $ProjectRoot
            try {
                & python $InitScript --local
            } catch {
                Write-Host "  WARNING: Database initialization failed: $_" -ForegroundColor Yellow
            }
            Pop-Location
        }
    }
}

Write-Host ""

# Step 3: Detect config path
Write-Host "[3/6] Detecting Gemini CLI configuration path..." -ForegroundColor Yellow

$ConfigDir = "$env:APPDATA\gemini-cli"
$ConfigFile = "$ConfigDir\config.json"

Write-Host "  ✓ Platform: Windows" -ForegroundColor Green
Write-Host "  ✓ Config file: $ConfigFile" -ForegroundColor Green

# Create config directory if needed
if (-not (Test-Path $ConfigDir)) {
    New-Item -Path $ConfigDir -ItemType Directory -Force | Out-Null
}

Write-Host ""

# Step 4: Backup existing config
Write-Host "[4/6] Backing up existing configuration..." -ForegroundColor Yellow

if (Test-Path $ConfigFile) {
    $Timestamp = Get-Date -Format "yyyyMMdd-HHmmss"
    $BackupFile = "$ConfigDir\config.json.backup.$Timestamp"
    Copy-Item $ConfigFile $BackupFile
    Write-Host "  ✓ Backed up to: $BackupFile" -ForegroundColor Green
} else {
    Write-Host "  ! No existing config found. Creating new config..." -ForegroundColor Yellow
}

Write-Host ""

# Step 5: Generate configuration
Write-Host "[5/6] Generating Hansard MCP configuration..." -ForegroundColor Yellow

# Create Hansard server configuration
$HansardConfig = @{
    mcpServers = @{
        hansard = @{
            command = "fastmcp"
            args = @("run", "src/server.py")
            env = @{
                DANGEROUSLY_OMIT_AUTH = "true"
                DATABASE_URL = "sqlite:///$ProjectRoot/data/hansard.db"
                PYTHONPATH = $ProjectRoot
                LOG_LEVEL = "INFO"
            }
            timeout = 30
            description = "Australian Hansard parliamentary speech search (local development)"
        }
    }
}

# Read existing config or create empty
if (Test-Path $ConfigFile) {
    try {
        $ExistingConfig = Get-Content $ConfigFile -Raw | ConvertFrom-Json

        # Check if mcpServers exists
        if ($ExistingConfig.mcpServers) {
            # Add hansard to existing mcpServers
            $ExistingConfig.mcpServers | Add-Member -MemberType NoteProperty -Name "hansard" -Value $HansardConfig.mcpServers.hansard -Force
            $FinalConfig = $ExistingConfig
            Write-Host "  ✓ Merged with existing mcpServers configuration" -ForegroundColor Green
        } else {
            # Add mcpServers section
            $ExistingConfig | Add-Member -MemberType NoteProperty -Name "mcpServers" -Value $HansardConfig.mcpServers
            $FinalConfig = $ExistingConfig
            Write-Host "  ✓ Added mcpServers section to existing config" -ForegroundColor Green
        }
    } catch {
        Write-Host "  WARNING: Could not parse existing config. Using new config..." -ForegroundColor Yellow
        $FinalConfig = $HansardConfig
    }
} else {
    $FinalConfig = $HansardConfig
    Write-Host "  ✓ Created new configuration" -ForegroundColor Green
}

# Write configuration
$FinalConfig | ConvertTo-Json -Depth 10 | Set-Content $ConfigFile -Encoding UTF8
Write-Host "  ✓ Configuration written to: $ConfigFile" -ForegroundColor Green

Write-Host ""

# Step 6: Verify setup
Write-Host "[6/6] Verifying setup..." -ForegroundColor Yellow

# Test server manually
Write-Host "  ! Testing server startup..." -ForegroundColor Yellow
Push-Location $ProjectRoot
try {
    $env:DANGEROUSLY_OMIT_AUTH = "true"
    $TestOutput = & fastmcp dev src/server.py 2>&1
    Start-Sleep -Seconds 2

    if ($TestOutput -match "error|Error") {
        Write-Host "  WARNING: Server test showed errors" -ForegroundColor Yellow
    } else {
        Write-Host "  ✓ Server starts successfully" -ForegroundColor Green
    }
} catch {
    Write-Host "  WARNING: Could not test server: $_" -ForegroundColor Yellow
} finally {
    Pop-Location
}

Write-Host ""
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "Setup Complete!" -ForegroundColor Green
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Next steps:" -ForegroundColor Yellow
Write-Host "  1. Restart Gemini CLI: gemini restart"
Write-Host "  2. Verify tools: Ask Gemini 'What Hansard tools are available?'"
Write-Host "  3. Test search: Ask Gemini 'Search Hansard for speeches about climate change'"
Write-Host ""
Write-Host "Configuration file: $ConfigFile"
Write-Host "Project directory: $ProjectRoot"
Write-Host ""
Write-Host "For troubleshooting, see: $ProjectRoot/docs/gemini-cli/troubleshooting.md"
Write-Host ""

# Check PowerShell execution policy
$ExecutionPolicy = Get-ExecutionPolicy
if ($ExecutionPolicy -eq "Restricted") {
    Write-Host "NOTE: PowerShell execution policy is Restricted." -ForegroundColor Yellow
    Write-Host "To run scripts in the future, run: Set-ExecutionPolicy RemoteSigned -Scope CurrentUser" -ForegroundColor Yellow
    Write-Host ""
}
