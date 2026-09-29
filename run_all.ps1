# Re-run the pilot in order. Downloads are cached (existing files are not re-downloaded).
#   .\run_all.ps1          -> v1 (8 sources)
#   .\run_all.ps1 -v2      -> v2 (31 sources, Standard-1 deadtime, hardness baselines)
param([switch]$v2)
$ErrorActionPreference = 'Stop'
$py = 'C:\Users\User\venvs\xrb-pilot\Scripts\python.exe'
Set-Location "$PSScriptRoot\scripts"
if ($v2) { $env:XRB_VERSION = 'v2'; $log = '..\logs\v2' } else { $env:XRB_VERSION = 'v1'; $log = '..\logs' }
New-Item -ItemType Directory -Force $log | Out-Null
& $py 03_select_observations.py *> "$log\03_select.log"
& $py 04_fetch_process.py       *> "$log\04_fetch_process.log"
if (-not $v2) { & $py 05_two_source_check.py *> "$log\05_two_source.log" }
& $py 06_dataset_checks.py      *> "$log\06_dataset_checks.log"
& $py 07_train_eval.py          *> "$log\07_train_eval.log"
& $py 08_error_analysis.py      *> "$log\08_error_analysis.log"
& $py 09_bootstrap_sources.py   *> "$log\09_bootstrap.log"
# XSPEC cross-check needs WSL Ubuntu-22.04 with the 'henv' conda env (scripts\install_heasoft_wsl.sh)
if ($v2) { & $py 10_xspec_crosscheck.py *> "$log\10_xspec_crosscheck.log" }
Write-Host 'done; see results\, figures\, reports\'
