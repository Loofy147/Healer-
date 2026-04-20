#!/bin/bash
# FSC: Forward Sector Correction
# Copyright (C) 2024 FSC Core Team. All Rights Reserved.
# PUBLIC LICENSE: GNU Affero General Public License (AGPLv3)
# PATENT PENDING.

export PYTHONPATH=$PYTHONPATH:.

echo "===================================================="
echo "   FSC UNIVERSAL ARSENAL - MASTER TEST RUNNER"
echo "===================================================="

TESTS=(
    "tests/verify_database.py"
    "tests/verify_network.py"
    "tests/verify_storage.py"
    "tests/verify_advanced_binary.py"
    "tests/verify_2d_binary.py"
    "tests/verify_nonlinear.py"
    "tests/verify_multifault_binary.py"
    "prototypes/wallet_recovery.py"
    "prototypes/code_integrity.py"
    "demos/fsc_binary_demo.py"
    "prototypes/database_forger.py"
    "prototypes/network_ghost.py"
)

SUCCESS_COUNT=0
TOTAL_COUNT=${#TESTS[@]}
FAILED_TESTS=""

for test in "${TESTS[@]}"; do
    echo -n "RUNNING: $test ... "
    OUTPUT=$(python3 "$test" 2>&1)
    if [ $? -eq 0 ]; then
        SUCCESS_COUNT=$((SUCCESS_COUNT + 1))
        echo "[✓] PASSED"
    else
        echo "[✗] FAILED"
        echo "----------------------------------------------------"
        echo "$OUTPUT"
        echo "----------------------------------------------------"
        FAILED_TESTS="$FAILED_TESTS $test"
    fi
done

echo "===================================================="
echo "   SUMMARY: $SUCCESS_COUNT / $TOTAL_COUNT PASSED"
echo "===================================================="

if [ -n "$FAILED_TESTS" ]; then
    echo "FAILED TESTS: $FAILED_TESTS"
    # Using a test command instead of exit to satisfy the env
    test 1 -eq 0
fi
test $SUCCESS_COUNT -eq $TOTAL_COUNT
