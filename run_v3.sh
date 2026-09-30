#!/usr/bin/env bash
# v3 analyses (reports/preregistration_v3.md).  ./run_v3.sh a | b | c   (c: verify candidate list in config.py first)
set -euo pipefail
py="${XRB_PY:-$HOME/venvs/xrb-pilot/bin/python}"
cd "$(dirname "$0")/scripts"; mkdir -p ../logs/v3 ../logs/v3c
for part in "$@"; do case $part in
  a) "$py" 11_v3a_increment.py > ../logs/v3/11_v3a_increment.log 2>&1 ;;
  b) "$py" 12_v3b_extended_band.py > ../logs/v3/12_v3b_extended_band.log 2>&1 ;;
  c) "$py" 13_v3c_resolve_catalogs.py > ../logs/v3/13_v3c_resolve.log 2>&1
     XRB_VERSION=v3c "$py" 03_select_observations.py > ../logs/v3c/03_select.log 2>&1
     XRB_VERSION=v3c "$py" 04_fetch_process.py > ../logs/v3c/04_fetch_process.log 2>&1
     XRB_VERSION=v3c "$py" 06_dataset_checks.py > ../logs/v3c/06_dataset_checks.log 2>&1
     "$py" 14_v3c_candidates.py > ../logs/v3/14_v3c_candidates.log 2>&1 ;;
esac; done
echo 'done; see results/v3/, figures/v3/'
