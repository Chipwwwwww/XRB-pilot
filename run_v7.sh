#!/usr/bin/env bash
# v7 (reports/preregistration_v7.md). ./run_v7.sh
set -euo pipefail
py="${XRB_PY:-$HOME/venvs/xrb-pilot/bin/python}"
cd "$(dirname "$0")/scripts"; mkdir -p ../logs/v7a ../logs/v7b1 ../logs/v7b2 ../logs/v7c
"$py" test_v7lib.py > ../logs/v7a/test_v7lib.log 2>&1
"$py" 31_v7b1_minbar.py > ../logs/v7b1/31_v7b1_minbar.log 2>&1
"$py" 32_v7b1_replace.py > ../logs/v7b1/32_v7b1_replace.log 2>&1
"$py" 33_v7b1_exclusion.py > ../logs/v7b1/33_v7b1_exclusion.log 2>&1
"$py" 34_v7a_states.py > ../logs/v7a/34_v7a_states.log 2>&1             # exit 3 if the sanity check fails
"$py" 35_v7b2_select.py > ../logs/v7b2/35_v7b2_select.log 2>&1
XRB_VERSION=v7b2 "$py" 04_fetch_process.py > ../logs/v7b2/04_fetch_process.log 2>&1
"$py" 31_v7b1_minbar.py --sample v7b2 > ../logs/v7b2/31_minbar_v7b2.log 2>&1
"$py" 36_v7b2_analysis.py > ../logs/v7b2/36_v7b2_analysis.log 2>&1
"$py" 37_v7c1_repro.py > ../logs/v7c/37_v7c1_repro.log 2>&1              # exit 3 if the reproduction fails
"$py" 38_v7c2_select.py > ../logs/v7c/38_v7c2_select.log 2>&1
"$py" 39_v7c2_analysis.py > ../logs/v7c/39_v7c2_analysis.log 2>&1        # ~2 h (nested SVM)
"$py" 40_v7_summary_figure.py > ../logs/v7c/40_v7_summary_figure.log 2>&1
echo 'done; see results/v7*, figures/v7*'
