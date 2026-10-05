#!/usr/bin/env bash
# v8 (reports/preregistration_v8.md). ./run_v8.sh
# v8d calls HEASoft through WSL (scripts/v8d_heasoft.sh); on Linux run that script directly with a HEASoft install.
set -euo pipefail
py="${XRB_PY:-$HOME/venvs/xrb-pilot/bin/python}"
cd "$(dirname "$0")/scripts"; mkdir -p ../logs/v8 ../logs/v8b ../logs/v8c ../logs/v8d
"$py" test_v8lib.py > ../logs/v8c/test_v8lib.log 2>&1
"$py" 41_v8b_select.py > ../logs/v8b/41_v8b_select.log 2>&1
XRB_VERSION=v8b "$py" 21_v4b2_fetch_process.py > ../logs/v8b/21_fetch_process.log 2>&1
"$py" 42_v8_states_timing.py > ../logs/v8b/42_states_timing.log 2>&1
"$py" 43_v8c_events.py > ../logs/v8c/43_events.log 2>&1 || echo "43 exited with $? (IC4 failed in the recorded run: v8c is exploratory, see decision_log); continuing"
"$py" 44_v8_analysis.py > ../logs/v8/44_analysis.log 2>&1              # exit 3 if IC1 / IC2 fail
"$py" 45_v8d_nh.py > ../logs/v8d/45_nh.log 2>&1                        # exit 3 if IC6 fails
"$py" 46_v8_summary_figure.py > ../logs/v8/46_summary_figure.log 2>&1
echo 'done; see results/v8*, figures/v8*'
