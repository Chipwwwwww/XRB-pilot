# v5 Standard-1 timing analysis (reports/preregistration_v5.md). Run from the repo root in PowerShell.
# Needs the Standard-1 and Standard-2 background files of v2 / v4b2 (data\raw) and v4b1 ($env:XRB_EXTERNAL_RAW or ~\xrb-pilot-data\raw).
$ErrorActionPreference = 'Stop'
$py = 'C:\Users\User\venvs\xrb-pilot\Scripts\python.exe'
Set-Location "$PSScriptRoot\scripts"; New-Item -ItemType Directory -Force '..\logs\v5' | Out-Null
& $py test_v5lib.py *> '..\logs\v5\test_v5lib.log'
& $py 26_v5_timing_features.py *> '..\logs\v5\26_v5_timing_features.log'     # stops (exit 3) if an implementation check fails
& $py 27_v5_analysis.py *> '..\logs\v5\27_v5_analysis.log'
Write-Host 'done; see results\v5, figures\v5'
