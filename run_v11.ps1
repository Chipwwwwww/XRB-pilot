# v11 (reports/preregistration_v11.md). Run from the repo root in PowerShell after run_v10.ps1 (needs data\v9, data\v10 and
# results\v10a, and the cached NICER TAP tables in data\raw\catalogs\nicer). Streams ~50 GB of never-used NICER event files from
# the HEASARC AWS mirror straight into the frozen feature pipeline; raw bytes are not stored (URL, bytes, SHA256 in logs\downloads.jsonl).
$ErrorActionPreference = 'Stop'
$py = 'C:\Users\User\venvs\xrb-pilot\Scripts\python.exe'
Set-Location "$PSScriptRoot\scripts"
New-Item -ItemType Directory -Force '..\logs\v11' | Out-Null
& $py test_v11lib.py *> '..\logs\v11\test_v11lib.log'                       # Lorentzian checks + streaming == v10 parse
& $py 55_v11_select.py *> '..\logs\v11\55_select.log'                       # never-used observations (IC3)
& $py 56_v11_fetch.py *> '..\logs\v11\56_fetch.log'                         # streamed features (~1 h; resumable)
& $py 57_v11_analysis.py *> '..\logs\v11\57_analysis.log'                   # IC1, IC2, v11a-d
Write-Host 'done; see results\v11, figures\v11'
