#!/usr/bin/env bash
# v12 (reports/preregistration_v12.md). ./run_v12.sh  (after ./run_v11.sh; 3C50 runs through WSL/HEASoft on Windows)
set -euo pipefail
py="${XRB_PY:-$HOME/venvs/xrb-pilot/bin/python}"
cd "$(dirname "$0")/scripts"; mkdir -p ../logs/v12
"$py" 58_v12_bkg.py > ../logs/v12/58_bkg.log 2>&1
"$py" 59_v12_analysis.py > ../logs/v12/59_analysis.log 2>&1
echo 'done; see results/v12, figures/v12'
