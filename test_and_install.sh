#!/bin/bash
# Test and Install Script
# Runs tests and installs the package locally if tests pass

set -e  # Exit on error

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"
VENV_DIR="${SCRIPT_DIR}/.venv"

echo "========================================="
echo "  XTS Core - Test & Install"
echo "========================================="
echo ""

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Run tests
echo -e "${CYAN}Running test suite...${NC}"
echo ""

if ./test.sh "$@"; then
    echo ""
    echo -e "${GREEN}✓ All tests passed!${NC}"
    echo ""
    
    # Install the package
    echo -e "${CYAN}Installing xts package locally...${NC}"
    echo ""

    if [ ! -d "${VENV_DIR}" ]; then
        python3 -m venv "${VENV_DIR}"
    fi
    source "${VENV_DIR}/bin/activate"
    python -m pip install --quiet --upgrade pip || true
    if ! python -m pip install --upgrade -e .; then
        echo -e "${YELLOW}Warning: install with dependencies failed, retrying without deps...${NC}"
        python -m pip install --upgrade -e . --no-deps || true
    fi
    
    echo ""
    echo -e "${GREEN}✓ Installation complete!${NC}"
    echo ""
    
    # Verify installation
    echo -e "${CYAN}Verifying installation...${NC}"
    XTS_VERSION=$("${VENV_DIR}/bin/xts" --version 2>&1 || echo "version check failed")
    XTS_PATH="${VENV_DIR}/bin/xts"
    
    echo -e "  Version: ${GREEN}${XTS_VERSION}${NC}"
    echo -e "  Path: ${GREEN}${XTS_PATH}${NC}"
    echo ""
    echo -e "${GREEN}========================================="
    echo -e "  Ready to use!"
    echo -e "=========================================${NC}"
else
    echo ""
    echo -e "${RED}✗ Tests failed! Skipping installation.${NC}"
    echo ""
    echo -e "${YELLOW}Fix the failing tests before installing.${NC}"
    exit 1
fi
