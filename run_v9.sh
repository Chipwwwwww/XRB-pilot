#!/usr/bin/env bash
# v9 (reports/preregistration_v9.md). ./run_v9.sh   (NICER prefixes go to ${XRB_EXTERNAL_RAW:-~/xrb-pilot-data/raw}/nicer)
set -euo pipefail
py="${XRB_PY:-$HOME/venvs/xrb-pilot/bin/python}"
cd "$(dirname "$0")/scripts"; mkdir -p ../logs/v9
"$py" test_v9lib.py > ../logs/v9/test_v9lib.log 2>&1
"$py" 47_v9_select.py > ../logs/v9/47_select.log 2>&1
"$py" 48_v9_nicer.py > ../logs/v9/48_nicer.log 2>&1
"$py" 49_v9_analysis.py > ../logs/v9/49_analysis.log 2>&1              # exit 3 if the Z-source sanity check fails
"$py" 50_v9c_maxi_strata.py > ../logs/v9/50_v9c.log 2>&1
"$py" 51_v9_summary_figure.py > ../logs/v9/51_summary_figure.log 2>&1
echo 'done; see results/v9*, figures/v9'
