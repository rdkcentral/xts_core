#!/bin/bash
# xts_core test runner
# Usage: ./test.sh

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "${SCRIPT_DIR}"

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${GREEN}Running xts_core tests...${NC}\n"

# Check for pytest
if ! python3 -c "import pytest" 2>/dev/null; then
    echo -e "${YELLOW}pytest not found, installing...${NC}"
    python3 -m pip install pytest --quiet --user
fi

# Run tests
echo -e "${YELLOW}Running test suite...${NC}"
python3 -m pytest test/ -v

echo -e "\n${GREEN}✓ All tests completed${NC}"
