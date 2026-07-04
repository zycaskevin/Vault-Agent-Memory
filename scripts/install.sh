#!/usr/bin/env bash
# Vault Agent Memory one-click installer for macOS/Linux
# Usage: curl -sSL https://raw.githubusercontent.com/zycaskevin/Vault-Agent-Memory/main/scripts/install.sh | bash
# Available from main. Installs the pinned release version below.

set -e

VAULT_VERSION="0.7.31"
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}╔══════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║   Vault Agent Memory Installer           ║${NC}"
echo -e "${BLUE}╚══════════════════════════════════════════╝${NC}"
echo ""

# --- Step 1: Check Python 3.10+ ---
echo -e "${YELLOW}[1/4] Checking Python version...${NC}"

PYTHON_CMD=""
for candidate in python3.12 python3.11 python3.10 python3 python3.13 python3.14; do
    if command -v "$candidate" > /dev/null 2>&1 && "$candidate" -c 'import sys; raise SystemExit(0 if sys.version_info >= (3, 10) else 1)' > /dev/null 2>&1; then
        PYTHON_CMD="$candidate"
        break
    fi
done

if [ -z "$PYTHON_CMD" ]; then
    echo "❌ Python 3.10+ is not installed or not in PATH."
    echo "   Install Python 3.10 or later from https://www.python.org/downloads/"
    echo "   macOS with Homebrew: brew install python"
    exit 1
fi

PYTHON_VERSION=$("$PYTHON_CMD" -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
PYTHON_PATH=$(command -v "$PYTHON_CMD")
echo -e "   ✅ Python $PYTHON_VERSION found at $PYTHON_PATH"

# --- Step 2: Create virtual environment ---
echo -e "${YELLOW}[2/4] Creating virtual environment...${NC}"

if [ -d ".venv" ]; then
    echo "   ℹ️  .venv already exists, reusing it"
else
    "$PYTHON_CMD" -m venv .venv
    echo "   ✅ Virtual environment created at .venv/"
fi

# Activate venv
source .venv/bin/activate
echo "   ✅ Virtual environment activated"

# --- Step 3: Install vault-for-llm ---
VAULT_PACKAGE_SPEC="${VAULT_PACKAGE_SPEC:-vault-for-llm[mcp]==$VAULT_VERSION}"
echo -e "${YELLOW}[3/4] Installing $VAULT_PACKAGE_SPEC ...${NC}"
pip install --upgrade pip > /dev/null 2>&1
pip install "$VAULT_PACKAGE_SPEC"

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
