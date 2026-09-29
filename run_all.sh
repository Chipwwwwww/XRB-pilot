#!/usr/bin/env bash
# Re-run the pilot in order on macOS/Linux (counterpart of run_all.ps1). Downloads are cached.
#   ./run_all.sh               -> v1 (8 sources)
#   ./run_all.sh --v2          -> v2 (31 sources, Standard-1 deadtime, hardness baselines)
#   ./run_all.sh --v2 --xspec  -> v2 + XSPEC cross-check (currently needs Windows + WSL; see README)
# Python: $XRB_PY, default ~/venvs/xrb-pilot/bin/python
set -euo pipefail
v2=0; xspec=0
for a in "$@"; do
  case "$a" in
    --v2) v2=1 ;;
    --xspec) xspec=1 ;;
    *) echo "unknown option: $a" >&2; exit 2 ;;
  esac
done
py="${XRB_PY:-$HOME/venvs/xrb-pilot/bin/python}"
cd "$(dirname "$0")/scripts"
if [ $v2 = 1 ]; then export XRB_VERSION=v2; log=../logs/v2; else export XRB_VERSION=v1; log=../logs; fi
mkdir -p "$log"
"$py" 03_select_observations.py > "$log/03_select.log" 2>&1
"$py" 04_fetch_process.py       > "$log/04_fetch_process.log" 2>&1
if [ $v2 = 0 ]; then "$py" 05_two_source_check.py > "$log/05_two_source.log" 2>&1; fi
"$py" 06_dataset_checks.py      > "$log/06_dataset_checks.log" 2>&1
"$py" 07_train_eval.py          > "$log/07_train_eval.log" 2>&1
"$py" 08_error_analysis.py      > "$log/08_error_analysis.log" 2>&1
"$py" 09_bootstrap_sources.py   > "$log/09_bootstrap.log" 2>&1
# XSPEC cross-check calls wsl.exe (scripts/10_xspec_crosscheck.py); skipped unless --xspec
if [ $v2 = 1 ] && [ $xspec = 1 ]; then "$py" 10_xspec_crosscheck.py > "$log/10_xspec_crosscheck.log" 2>&1; fi
echo 'done; see results/, figures/, reports/'
