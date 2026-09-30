#!/usr/bin/env bash
# v6 (reports/preregistration_v6.md). ./run_v6.sh
set -euo pipefail
py="${XRB_PY:-$HOME/venvs/xrb-pilot/bin/python}"
cd "$(dirname "$0")/scripts"; mkdir -p ../logs/v6
"$py" test_v6lib.py > ../logs/v6/test_v6lib.log 2>&1
"$py" 28_v6_select.py > ../logs/v6/28_v6_select.log 2>&1
XRB_VERSION=v6 "$py" 21_v4b2_fetch_process.py > ../logs/v6/21_v6_fetch_process.log 2>&1
"$py" 29_v6_features.py > ../logs/v6/29_v6_features.log 2>&1
"$py" 30_v6_analysis.py > ../logs/v6/30_v6_analysis.log 2>&1
echo 'done; see results/v6, figures/v6'
