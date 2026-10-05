# v8 (reports/preregistration_v8.md). Run from the repo root in PowerShell.
# Needs the v2/v4b2/v6/v7b2 data and raw files (data\raw), the v4 burst results, the v7a/v7b1/v7c outputs, curl (built into
# Windows), and HEASoft in WSL (Ubuntu-22.04, conda env henv: nh + XSPEC; see scripts\install_heasoft_wsl.sh) for v8d.
# Downloads: GS 1354-64 / SS 433 StdProd + Standard-1 (~23 obs), ~2.4 GB of RXTE event files (hard-like observations).
$ErrorActionPreference = 'Stop'
$py = 'C:\Users\User\venvs\xrb-pilot\Scripts\python.exe'
Set-Location "$PSScriptRoot\scripts"
foreach ($d in 'v8','v8b','v8c','v8d') { New-Item -ItemType Directory -Force "..\logs\$d" | Out-Null }
& $py test_v8lib.py *> '..\logs\v8c\test_v8lib.log'                         # IC3 synthetic checks (exit 1 if any fails)
& $py 41_v8b_select.py *> '..\logs\v8b\41_v8b_select.log'                   # new dynamical BHs (TAP / MissionLongData)
$env:XRB_VERSION = 'v8b'; & $py 21_v4b2_fetch_process.py *> '..\logs\v8b\21_fetch_process.log'; $env:XRB_VERSION = $null
& $py 42_v8_states_timing.py *> '..\logs\v8b\42_states_timing.log'          # external set X: MINBAR, states, v5 timing
& $py 43_v8c_events.py *> '..\logs\v8c\43_events.log'                       # survey + download + HF features; exit 3 = IC4 failed
if ($LASTEXITCODE -eq 3) { Write-Host 'IC4 failed (as in the recorded run): v8c is exploratory, see decision_log; continuing' }
& $py 44_v8_analysis.py *> '..\logs\v8\44_analysis.log'                     # v8a, v8b, v8c (exit 3 if IC1/IC2 fail)
& $py 45_v8d_nh.py *> '..\logs\v8d\45_nh.log'                               # HI4PI N_H + tbabs (WSL), MAXI models (exit 3 if IC6 fails)
& $py 46_v8_summary_figure.py *> '..\logs\v8\46_summary_figure.log'
Write-Host 'done; see results\v8*, figures\v8*'
