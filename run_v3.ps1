# v3 analyses (reports/preregistration_v3.md). Run from the repo root in PowerShell.
#   .\run_v3.ps1 -a        v3a: nested H vs H+B on existing v2 features (no downloads; ~5-10 min CPU)
#   .\run_v3.ps1 -b        v3b: 3-25 keV grid from the v2 raw FITS already in data\raw (no downloads)
#   .\run_v3.ps1 -c        v3c: BH candidates -- EDIT/VERIFY the candidate list in scripts\config.py FIRST (downloads)
param([switch]$a, [switch]$b, [switch]$c)
$ErrorActionPreference = 'Stop'
$py = 'C:\Users\User\venvs\xrb-pilot\Scripts\python.exe'
Set-Location "$PSScriptRoot\scripts"
New-Item -ItemType Directory -Force '..\logs\v3' | Out-Null
if ($a) { & $py 11_v3a_increment.py *> '..\logs\v3\11_v3a_increment.log' }
if ($b) { & $py 12_v3b_extended_band.py *> '..\logs\v3\12_v3b_extended_band.log' }
if ($c) {
  & $py 13_v3c_resolve_catalogs.py *> '..\logs\v3\13_v3c_resolve.log'
  $env:XRB_VERSION = 'v3c'
  New-Item -ItemType Directory -Force '..\logs\v3c' | Out-Null
  & $py 03_select_observations.py *> '..\logs\v3c\03_select.log'
  & $py 04_fetch_process.py       *> '..\logs\v3c\04_fetch_process.log'
  & $py 06_dataset_checks.py      *> '..\logs\v3c\06_dataset_checks.log'
  Remove-Item Env:XRB_VERSION
  & $py 14_v3c_candidates.py *> '..\logs\v3\14_v3c_candidates.log'
}
Write-Host 'done; see results\v3\, figures\v3\'
