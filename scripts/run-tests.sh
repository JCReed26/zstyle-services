#!/bin/bash
# Test runner script with coverage reporting
#
# Usage:
#   ./scripts/run-tests.sh              # Run all tests with coverage
#   ./scripts/run-tests.sh tests/unit   # Run specific test directory
#   ./scripts/run-tests.sh -k test_name # Run tests matching pattern

set -e  # Exit on error

# Default to running all tests if no arguments provided
TEST_PATH="${1:-tests/}"

echo "=========================================="
echo "Running pytest with coverage..."
echo "=========================================="
echo ""

# Run pytest with coverage reporting
pytest "$TEST_PATH" \
    --cov=. \
    --cov-report=html \
    --cov-report=term \
    "${@:2}"  # Pass any additional arguments to pytest

echo ""
echo "=========================================="
echo "Coverage report generated in htmlcov/"
echo "Open htmlcov/index.html in your browser"
echo "=========================================="
