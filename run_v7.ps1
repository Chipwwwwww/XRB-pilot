# v7 (reports/preregistration_v7.md). Run from the repo root in PowerShell.
# Needs the v2 data and raw files (data\raw), the v4 burst results and the v6 timing code. Downloads: MINBAR (~54 MB),
# same-bin replacements (~100 candidates), 45 persistent-BH observations, de Beurs repo files (~16 MB), ~130 MAXI light curves.
$ErrorActionPreference = 'Stop'
$py = 'C:\Users\User\venvs\xrb-pilot\Scripts\python.exe'
Set-Location "$PSScriptRoot\scripts"
foreach ($d in 'v7a','v7b1','v7b2','v7c') { New-Item -ItemType Directory -Force "..\logs\$d" | Out-Null }
& $py test_v7lib.py *> '..\logs\v7a\test_v7lib.log'
& $py 31_v7b1_minbar.py *> '..\logs\v7b1\31_v7b1_minbar.log'                 # MINBAR download + matching (v2 sample)
& $py 32_v7b1_replace.py *> '..\logs\v7b1\32_v7b1_replace.log'               # same-time-bin replacements (runs 04 with XRB_VERSION=v7b1)
& $py 33_v7b1_exclusion.py *> '..\logs\v7b1\33_v7b1_exclusion.log'
& $py 34_v7a_states.py *> '..\logs\v7a\34_v7a_states.log'                    # stops (exit 3) if the sanity check fails
& $py 35_v7b2_select.py *> '..\logs\v7b2\35_v7b2_select.log'
$env:XRB_VERSION = 'v7b2'; & $py 04_fetch_process.py *> '..\logs\v7b2\04_fetch_process.log'; $env:XRB_VERSION = $null
& $py 31_v7b1_minbar.py --sample v7b2 *> '..\logs\v7b2\31_minbar_v7b2.log'
& $py 36_v7b2_analysis.py *> '..\logs\v7b2\36_v7b2_analysis.log'
& $py 37_v7c1_repro.py *> '..\logs\v7c\37_v7c1_repro.log'                    # stops (exit 3) if the reproduction fails
& $py 38_v7c2_select.py *> '..\logs\v7c\38_v7c2_select.log'
& $py 39_v7c2_analysis.py *> '..\logs\v7c\39_v7c2_analysis.log'              # ~2 h (nested SVM)
& $py 40_v7_summary_figure.py *> '..\logs\v7c\40_v7_summary_figure.log'
Write-Host 'done; see results\v7*, figures\v7*'
