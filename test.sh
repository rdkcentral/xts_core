#!/bin/bash
# xts_core test runner
# Usage: ./test.sh [OPTIONS]
#
# OPTIONS:
#   --remote    Run only remote/HTTP tests
#   --proxy     Run only proxy tests
#   --alias     Run only alias tests
#   --all       Run all tests (default)

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "${SCRIPT_DIR}"

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Parse arguments
TEST_FILTER=""
case "${1:-}" in
    --remote)
        TEST_FILTER="test/test_xts_alias_remote.py"
        ;;
    --proxy)
        TEST_FILTER="test/test_xts_alias_remote.py::TestProxySupport test/test_xts_alias_remote.py::TestProxyFeature"
        ;;
    --alias)
        TEST_FILTER="test/test_xts_alias*.py"
        ;;
    --all|"")
        TEST_FILTER="test/"
        ;;
    *)
        echo -e "${RED}Unknown option: $1${NC}"
        echo "Usage: ./test.sh [--remote|--proxy|--alias|--all]"
        exit 1
        ;;
esac

echo -e "${GREEN}Running xts_core tests...${NC}\n"

# Setup virtual environment if not exists
VENV_DIR="${SCRIPT_DIR}/.venv"
if [ ! -d "$VENV_DIR" ]; then
    echo -e "${YELLOW}Creating virtual environment...${NC}"
    python3 -m venv "$VENV_DIR"
fi

# Activate virtual environment
source "${VENV_DIR}/bin/activate"

# Install dependencies
echo -e "${YELLOW}Checking dependencies...${NC}"
pip install --quiet --upgrade pip
pip install --quiet pytest
pip install --quiet -r requirements.txt 2>/dev/null || true

# Run tests
echo -e "${YELLOW}Running test suite...${NC}"
python3 -m pytest ${TEST_FILTER} -v

echo -e "\n${GREEN}✓ All tests completed${NC}"

# Deactivate virtual environment
deactivate
