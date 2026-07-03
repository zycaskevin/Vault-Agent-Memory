# Vault-for-LLM one-click installer for Windows (PowerShell)
# Usage: irm https://raw.githubusercontent.com/zycaskevin/Vault-for-LLM/main/scripts/install.ps1 | iex

$ErrorActionPreference = "Stop"

$VAULT_VERSION = "0.7.29"

function Write-Color($Text, $Color = "White") {
    Write-Host $Text -ForegroundColor $Color
}

Write-Color "`n╔══════════════════════════════════════════╗" Cyan
Write-Color "║   Vault-for-LLM One-Click Installer     ║" Cyan
Write-Color "╚══════════════════════════════════════════╝`n" Cyan

# --- Step 1: Check Python 3.10+ ---
Write-Color "[1/4] Checking Python version..." Yellow

try {
    $pythonCmd = $null
    if (Get-Command python -ErrorAction SilentlyContinue) {
        $pythonCmd = "python"
    } elseif (Get-Command python3 -ErrorAction SilentlyContinue) {
        $pythonCmd = "python3"
    } else {
        throw "Python not found"
    }

    $versionOutput = & $pythonCmd -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')"
    $versionParts = $versionOutput -split '\.'
    $major = [int]$versionParts[0]
    $minor = [int]$versionParts[1]

    if ($major -lt 3 -or ($major -eq 3 -and $minor -lt 10)) {
        Write-Color "❌ Python $versionOutput detected." Red
        Write-Color "   Vault-for-LLM requires Python 3.10 or later." Red
        Write-Color "   Download from: https://www.python.org/downloads/" Red
        exit 1
    }

    Write-Host "   ✅ Python $versionOutput found"
} catch {
    Write-Color "❌ Python is not installed or not in PATH." Red
    Write-Color "   Please install Python 3.10+ from: https://www.python.org/downloads/" Red
    exit 1
}

# --- Step 2: Create virtual environment ---
Write-Color "[2/4] Creating virtual environment..." Yellow

if (Test-Path ".venv") {
    Write-Host "   ℹ️  .venv already exists, reusing it"
} else {
    & $pythonCmd -m venv .venv
    Write-Host "   ✅ Virtual environment created at .venv/"
}

# Activate venv
$venvPython = ".venv\Scripts\python.exe"
$venvPip = ".venv\Scripts\pip.exe"
Write-Host "   ✅ Virtual environment ready"

# --- Step 3: Install vault-for-llm ---
Write-Color "[3/4] Installing vault-for-llm[mcp]==$VAULT_VERSION ..." Yellow

& $venvPip install --upgrade pip | Out-Null
& $venvPip install "vault-for-llm[mcp]==$VAULT_VERSION"

Write-Host "   ✅ vault-for-llm installed successfully"

# --- Step 4: Post-install instructions ---
Write-Color "`n╔══════════════════════════════════════════╗" Green
Write-Color "║   Installation Complete! 🎉              ║" Green
Write-Color "╚══════════════════════════════════════════╝`n" Green

Write-Color "📋 Next steps:" Cyan
Write-Host ""
Write-Host "   1. Activate the virtual environment:"
Write-Color "      .venv\Scripts\Activate.ps1" Yellow
Write-Host ""
Write-Host "   2. Run the quickstart wizard (asks only 4 questions):"
Write-Color "      vault quickstart" Yellow
Write-Host ""
Write-Host "   3. Try a quick smoke test:"
Write-Color "      vault demo agent-governance --json" Yellow
Write-Host ""
Write-Color "📚 Learn more:" Cyan
Write-Host "   • 5-Minute Quickstart: docs/quickstart.md"
Write-Host "   • MCP Integration: docs/mcp_memory_workflow.md"
Write-Host "   • Core Concepts: docs/core-concepts.md"
Write-Host ""
Write-Color "Happy vaulting! 🔐`n" Green
