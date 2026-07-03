#!/usr/bin/env bash
# Vault-for-LLM one-click installer for macOS/Linux
# Usage: curl -sSL https://raw.githubusercontent.com/zycaskevin/Vault-for-LLM/main/scripts/install.sh | bash

set -e

VAULT_VERSION="0.7.29"
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}╔══════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║   Vault-for-LLM One-Click Installer     ║${NC}"
echo -e "${BLUE}╚══════════════════════════════════════════╝${NC}"
echo ""

# --- Step 1: Check Python 3.10+ ---
echo -e "${YELLOW}[1/4] Checking Python version...${NC}"

if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is not installed."
    echo "   Please install Python 3.10 or later from https://www.python.org/downloads/"
    exit 1
fi

PYTHON_VERSION=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
PYTHON_MAJOR=$(python3 -c 'import sys; print(sys.version_info.major)')
PYTHON_MINOR=$(python3 -c 'import sys; print(sys.version_info.minor)')

if [ "$PYTHON_MAJOR" -lt 3 ] || ([ "$PYTHON_MAJOR" -eq 3 ] && [ "$PYTHON_MINOR" -lt 10 ]); then
    echo "❌ Python $PYTHON_VERSION detected."
    echo "   Vault-for-LLM requires Python 3.10 or later."
    echo "   Please upgrade Python: https://www.python.org/downloads/"
    exit 1
fi

echo -e "   ✅ Python $PYTHON_VERSION found"

# --- Step 2: Create virtual environment ---
echo -e "${YELLOW}[2/4] Creating virtual environment...${NC}"

if [ -d ".venv" ]; then
    echo "   ℹ️  .venv already exists, reusing it"
else
    python3 -m venv .venv
    echo "   ✅ Virtual environment created at .venv/"
fi

# Activate venv
source .venv/bin/activate
echo "   ✅ Virtual environment activated"

# --- Step 3: Install vault-for-llm ---
echo -e "${YELLOW}[3/4] Installing vault-for-llm[mcp]==$VAULT_VERSION ...${NC}"
pip install --upgrade pip > /dev/null 2>&1
pip install "vault-for-llm[mcp]==$VAULT_VERSION"

echo -e "   ✅ vault-for-llm installed successfully"

# --- Step 4: Post-install instructions ---
echo ""
echo -e "${GREEN}╔══════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║   Installation Complete! 🎉              ║${NC}"
echo -e "${GREEN}╚══════════════════════════════════════════╝${NC}"
echo ""
echo -e "📋 ${BLUE}Next steps:${NC}"
echo ""
echo -e "   1. Activate the virtual environment:"
echo -e "      ${YELLOW}source .venv/bin/activate${NC}"
echo ""
echo -e "   2. Run the quickstart wizard (asks only 4 questions):"
echo -e "      ${YELLOW}vault quickstart${NC}"
echo ""
echo -e "   3. Try a quick smoke test:"
echo -e "      ${YELLOW}vault demo agent-governance --json${NC}"
echo ""
echo -e "📚 ${BLUE}Learn more:${NC}"
echo -e "   • 5-Minute Quickstart: docs/quickstart.md"
echo -e "   • MCP Integration: docs/mcp_memory_workflow.md"
echo -e "   • Core Concepts: docs/core-concepts.md"
echo ""
echo -e "${GREEN}Happy vaulting! 🔐${NC}"
