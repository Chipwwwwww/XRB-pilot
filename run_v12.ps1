# v12 (reports/preregistration_v12.md). After run_v11.ps1. Needs HEASoft in WSL (nibackgen3C50) and the NICER CALDB in
# ~\xrb-pilot-data\caldb (goodfiles_nicer_xti.tar.gz + software\tools\caldb.config, alias_config.fits from HEASARC).
$ErrorActionPreference = 'Stop'
$py = 'C:\Users\User\venvs\xrb-pilot\Scripts\python.exe'
Set-Location "$PSScriptRoot\scripts"
New-Item -ItemType Directory -Force '..\logs\v12' | Out-Null
& $py 58_v12_bkg.py *> '..\logs\v12\58_bkg.log'                             # 3C50 for 503 observations (~1 h; resumable)
& $py 59_v12_analysis.py *> '..\logs\v12\59_analysis.log'                   # IC1-IC3, v12a, v12b
Write-Host 'done; see results\v12, figures\v12'
