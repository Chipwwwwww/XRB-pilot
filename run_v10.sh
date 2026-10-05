#!/usr/bin/env bash
# v10 (reports/preregistration_v10.md). ./run_v10.sh  (after ./run_v9.sh; NICER tails go to ${XRB_EXTERNAL_RAW:-~/xrb-pilot-data/raw}/nicer_tail)
set -euo pipefail
py="${XRB_PY:-$HOME/venvs/xrb-pilot/bin/python}"
cd "$(dirname "$0")/scripts"; mkdir -p ../logs/v10
"$py" test_v10lib.py > ../logs/v10/test_v10lib.log 2>&1
"$py" 52_v10_nicer_full.py > ../logs/v10/52_nicer_full.log 2>&1
"$py" 53_v10_rxte_nuc.py > ../logs/v10/53_rxte_nuc.log 2>&1
"$py" 54_v10_pooled.py > ../logs/v10/54_pooled.log 2>&1
echo 'done; see results/v10*, figures/v10'
