#!/usr/bin/env bash
# v13 (reports/preregistration_v13.md). ./run_v13.sh  (after ./run_v12.sh)
set -euo pipefail
py="${XRB_PY:-$HOME/venvs/xrb-pilot/bin/python}"
cd "$(dirname "$0")/scripts"; mkdir -p ../logs/v13
"$py" 60_v13_select.py > ../logs/v13/60_select.log 2>&1
"$py" 61_v13_fetch.py > ../logs/v13/61_fetch.log 2>&1
"$py" 62_v13_bkg.py > ../logs/v13/62_bkg.log 2>&1
"$py" 63_v13_analysis.py > ../logs/v13/63_analysis.log 2>&1
echo 'done; see results/v13, figures/v13'
