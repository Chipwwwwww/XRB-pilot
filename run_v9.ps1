# v9 (reports/preregistration_v9.md). Run from the repo root in PowerShell.
# Needs MINBAR (data\raw\minbar, from v7), data\v7c (Sesame positions, MAXI points), results\v8d (MAXI OOF) and curl.
# Downloads: the start of ~500 NICER cleaned event files (HEASARC AWS mirror, range requests; ~30-40 GB) into
# $env:XRB_EXTERNAL_RAW\nicer (default ~\xrb-pilot-data\raw\nicer, outside the OneDrive repo).
$ErrorActionPreference = 'Stop'
$py = 'C:\Users\User\venvs\xrb-pilot\Scripts\python.exe'
Set-Location "$PSScriptRoot\scripts"
New-Item -ItemType Directory -Force '..\logs\v9' | Out-Null
& $py test_v9lib.py *> '..\logs\v9\test_v9lib.log'                          # IC1/IC2 (exit 1 if any fails)
& $py 47_v9_select.py *> '..\logs\v9\47_select.log'                          # NICER sources and ranked candidates (TAP)
& $py 48_v9_nicer.py *> '..\logs\v9\48_nicer.log'                            # streamed prefixes + features (~40 min)
& $py 49_v9_analysis.py *> '..\logs\v9\49_analysis.log'                      # v9a / v9b (exit 3 if the Z-source sanity check fails)
& $py 50_v9c_maxi_strata.py *> '..\logs\v9\50_v9c.log'                       # v9c (descriptive)
& $py 51_v9_summary_figure.py *> '..\logs\v9\51_summary_figure.log'
Write-Host 'done; see results\v9*, figures\v9'
