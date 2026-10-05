# v13 (reports/preregistration_v13.md). After run_v12.ps1 (needs data\v12\processed\nicer_corrected_screened.csv, WSL HEASoft, NICER CALDB).
$ErrorActionPreference = 'Stop'
$py = 'C:\Users\User\venvs\xrb-pilot\Scripts\python.exe'
Set-Location "$PSScriptRoot\scripts"
New-Item -ItemType Directory -Force '..\logs\v13' | Out-Null
& $py 60_v13_select.py *> '..\logs\v13\60_select.log'
& $py 61_v13_fetch.py *> '..\logs\v13\61_fetch.log'                         # streamed features (~40 min; resumable)
& $py 62_v13_bkg.py *> '..\logs\v13\62_bkg.log'                             # 3C50 (~30 min; resumable; keeps faint cl files)
& $py 63_v13_analysis.py *> '..\logs\v13\63_analysis.log'
Write-Host 'done; see results\v13, figures\v13'
