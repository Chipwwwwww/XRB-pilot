#!/usr/bin/env bash
# v11 (reports/preregistration_v11.md). ./run_v11.sh  (after ./run_v10.sh; streams ~50 GB, raw bytes not stored)
set -euo pipefail
py="${XRB_PY:-$HOME/venvs/xrb-pilot/bin/python}"
cd "$(dirname "$0")/scripts"; mkdir -p ../logs/v11
"$py" test_v11lib.py > ../logs/v11/test_v11lib.log 2>&1
"$py" 55_v11_select.py > ../logs/v11/55_select.log 2>&1
"$py" 56_v11_fetch.py > ../logs/v11/56_fetch.log 2>&1
"$py" 57_v11_analysis.py > ../logs/v11/57_analysis.log 2>&1
echo 'done; see results/v11, figures/v11'
