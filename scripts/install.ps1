# Vault Agent Memory one-click installer for Windows (PowerShell)
# Usage: irm https://raw.githubusercontent.com/zycaskevin/Vault-Agent-Memory/main/scripts/install.ps1 | iex
# Available from main. Installs the pinned release version below.

$ErrorActionPreference = "Stop"

$VAULT_VERSION = "0.8.0"

function Write-Color($Text, $Color = "White") {
    Write-Host $Text -ForegroundColor $Color
}

Write-Color "`n╔══════════════════════════════════════════╗" Cyan
Write-Color "║   Vault Agent Memory Installer           ║" Cyan
Write-Color "╚══════════════════════════════════════════╝`n" Cyan

# --- Step 1: Check Python 3.10+ ---
Write-Color "[1/4] Checking Python version..." Yellow

try {
    $pythonCmd = $null
    $pythonArgs = @()
    $candidates = @(
        @("py", "-3.12"),
        @("py", "-3.11"),
        @("py", "-3.10"),
        @("python"),
        @("python3"),
        @("py", "-3.13"),
        @("py", "-3.14")
    )

    foreach ($candidate in $candidates) {
        $cmd = $candidate[0]
        $args = @()
        if ($candidate.Count -gt 1) {
            $args = $candidate[1..($candidate.Count - 1)]
        }
        if (-not (Get-Command $cmd -ErrorAction SilentlyContinue)) {
            continue
        }

        try {
            $versionOutput = & $cmd @args -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')"
            $versionParts = $versionOutput -split '\.'
            $major = [int]$versionParts[0]
            $minor = [int]$versionParts[1]
            if ($major -gt 3 -or ($major -eq 3 -and $minor -ge 10)) {
                $pythonCmd = $cmd
                $pythonArgs = $args
                break
            }
        } catch {
            continue
        }
    }

    if ($null -eq $pythonCmd) {
        throw "Python 3.10+ not found"
    }

    $versionOutput = & $pythonCmd @pythonArgs -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')"
    Write-Host "   ✅ Python $versionOutput found"
} catch {
    Write-Color "❌ Python 3.10+ is not installed or not in PATH." Red
    Write-Color "   Please install Python 3.10+ from: https://www.python.org/downloads/" Red
    exit 1
}

# --- Step 2: Create virtual environment ---
Write-Color "[2/4] Creating virtual environment..." Yellow

if (Test-Path ".venv") {
    Write-Host "   ℹ️  .venv already exists, reusing it"
} else {
    & $pythonCmd @pythonArgs -m venv .venv
    Write-Host "   ✅ Virtual environment created at .venv/"
}

# Activate venv
$venvPython = ".venv\Scripts\python.exe"
$venvPip = ".venv\Scripts\pip.exe"
Write-Host "   ✅ Virtual environment ready"

# --- Step 3: Install vault-for-llm ---
if ($env:VAULT_PACKAGE_SPEC) {
    $VaultPackageSpec = $env:VAULT_PACKAGE_SPEC
} else {
    $VaultPackageSpec = "vault-for-llm[mcp]==$VAULT_VERSION"
}
Write-Color "[3/4] Installing $VaultPackageSpec ..." Yellow

& $venvPip install --upgrade pip | Out-Null
& $venvPip install $VaultPackageSpec

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
