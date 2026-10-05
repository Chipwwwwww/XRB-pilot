# v10 (reports/preregistration_v10.md). Run from the repo root in PowerShell after run_v9.ps1 (needs the v9 NICER prefixes in
# $env:XRB_EXTERNAL_RAW\nicer and data\v9), and the v2 / v5 / v6 / v7a / v8b outputs. Downloads ~24 GB of NICER event-file
# tails (HEASARC AWS mirror) into $env:XRB_EXTERNAL_RAW\nicer_tail (default ~\xrb-pilot-data\raw).
$ErrorActionPreference = 'Stop'
$py = 'C:\Users\User\venvs\xrb-pilot\Scripts\python.exe'
Set-Location "$PSScriptRoot\scripts"
New-Item -ItemType Directory -Force '..\logs\v10' | Out-Null
& $py test_v10lib.py *> '..\logs\v10\test_v10lib.log'                       # pooled statistics: synthetic checks
& $py 52_v10_nicer_full.py *> '..\logs\v10\52_nicer_full.log'               # IC1, tails, full-data features, IC4 (~1-1.5 h)
& $py 53_v10_rxte_nuc.py *> '..\logs\v10\53_rxte_nuc.log'                   # RXTE hard-like nu_c table
& $py 54_v10_pooled.py *> '..\logs\v10\54_pooled.log'                       # IC2, IC3, v10a / v10b
Write-Host 'done; see results\v10*, figures\v10'
