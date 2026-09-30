#!/usr/bin/env bash
# v5 Standard-1 timing analysis (reports/preregistration_v5.md). ./run_v5.sh
set -euo pipefail
py="${XRB_PY:-$HOME/venvs/xrb-pilot/bin/python}"
cd "$(dirname "$0")/scripts"; mkdir -p ../logs/v5
"$py" test_v5lib.py > ../logs/v5/test_v5lib.log 2>&1
"$py" 26_v5_timing_features.py > ../logs/v5/26_v5_timing_features.log 2>&1   # exit 3 if an implementation check fails
"$py" 27_v5_analysis.py > ../logs/v5/27_v5_analysis.log 2>&1
echo 'done; see results/v5, figures/v5'