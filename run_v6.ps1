# v6 (reports/preregistration_v6.md). Run from the repo root in PowerShell.
# Needs the v2 / v4b2 / v4b1 data and the v5 timing features; downloads ~180 new observations (external sources) to data\raw.
$ErrorActionPreference = 'Stop'
$py = 'C:\Users\User\venvs\xrb-pilot\Scripts\python.exe'
Set-Location "$PSScriptRoot\scripts"; New-Item -ItemType Directory -Force '..\logs\v6' | Out-Null
& $py test_v6lib.py *> '..\logs\v6\test_v6lib.log'
& $py 28_v6_select.py *> '..\logs\v6\28_v6_select.log'
$env:XRB_VERSION = 'v6'; & $py 21_v4b2_fetch_process.py *> '..\logs\v6\21_v6_fetch_process.log'; $env:XRB_VERSION = $null
& $py 29_v6_features.py *> '..\logs\v6\29_v6_features.log'
& $py 30_v6_analysis.py *> '..\logs\v6\30_v6_analysis.log'
Write-Host 'done; see results\v6, figures\v6'
