#!/bin/bash
# Run XTS core tests

cd "$(dirname "$0")"

echo "========================================="
echo "XTS Core Test Suite"
echo "========================================="
echo

# Activate venv if exists
if [ -f "../../../venv/bin/activate" ]; then
    source ../../../venv/bin/activate
fi

# Install test dependencies if needed
pip install -q pytest pytest-cov 2>/dev/null

echo "Running tests..."
echo

# Run tests with coverage
pytest test_xts_alias_enhanced.py test_xts_validator.py test_xts_allocator_client.py \
    -v \
    --tb=short \
    --cov=../src/xts_core \
    --cov-report=term-missing \
    "$@"

exit_code=$?

echo
echo "========================================="
if [ $exit_code -eq 0 ]; then
    echo "✓ All tests passed!"
else
    echo "✗ Some tests failed (exit code: $exit_code)"
fi
echo "========================================="

exit $exit_code
