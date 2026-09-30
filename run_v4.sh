#!/usr/bin/env bash
# v4 analyses (reports/preregistration_v4.md).  ./run_v4.sh test a burst b3 b2 b1
# b1 downloads ~7,500 observations (~2 GB) to $XRB_EXTERNAL_RAW (default ~/xrb-pilot-data/raw), outside the repo.
set -euo pipefail
py="${XRB_PY:-$HOME/venvs/xrb-pilot/bin/python}"
cd "$(dirname "$0")/scripts"; mkdir -p ../logs/v4 ../logs/v4b1 ../logs/v4b2 ../logs/v4b3
for part in "$@"; do case $part in
  test)  "$py" test_v4lib.py > ../logs/v4_test_v4lib.log 2>&1 ;;
  a)     "$py" 16_v4a_algorithms.py > ../logs/v4/16_v4a_algorithms.log 2>&1 ;;
  burst) "$py" 17_v4_burst_detect.py > ../logs/v4/17_v4_burst_detect.log 2>&1
         "$py" 18_v4_burst_exclusion.py > ../logs/v4/18_v4_burst_exclusion.log 2>&1 ;;   # needs results/v4/burst_visual.csv
  b3)    "$py" 19_v4b3_hexte.py > ../logs/v4b3/19_v4b3_hexte.log 2>&1 ;;
  b2)    "$py" 20_v4b2_select.py > ../logs/v4b2/20_v4b2_select.log 2>&1
         XRB_VERSION=v4b2 "$py" 21_v4b2_fetch_process.py > ../logs/v4b2/21_v4b2_fetch_process.log 2>&1
         "$py" 22_v4b2_analysis.py > ../logs/v4b2/22_v4b2_analysis.log 2>&1 ;;
  b1)    "$py" 23_v4b1_candidates.py > ../logs/v4b1/23_v4b1_candidates.log 2>&1
         XRB_VERSION=v4b1 "$py" 24_v4b1_fetch_process.py > ../logs/v4b1/24_v4b1_fetch_process.log 2>&1
         "$py" 25_v4b1_analysis.py > ../logs/v4b1/25_v4b1_analysis.log 2>&1 ;;
esac; done
echo 'done; see results/v4*, figures/v4*'
