# v4 analyses (reports/preregistration_v4.md). Run from the repo root in PowerShell.
#   .\run_v4.ps1 -test   unit/smoke tests of scripts\v4lib.py (bootstrap vs v3a, LR/RF vs v2, all models)
#   .\run_v4.ps1 -a      v4a algorithm comparison (no downloads; ~20 min on 16 cores)
#   .\run_v4.ps1 -burst  type-I burst detection + exclusion check (uses data\raw\std1 of the v2 observations)
#   .\run_v4.ps1 -b3     v4b3 HEXTE cluster B colours (downloads ~2 small files per observation)
#   .\run_v4.ps1 -b2     v4b2 earlier gain epochs (position-verified source list; downloads ~220 observations)
#   .\run_v4.ps1 -b1     v4b1 every eligible epoch-5 pointing (~7,500 observations, ~2 GB, ~3-4 h; raw files go to
#                        $env:XRB_EXTERNAL_RAW or ~\xrb-pilot-data\raw, outside the repo)
param([switch]$test, [switch]$a, [switch]$burst, [switch]$b3, [switch]$b2, [switch]$b1)
$ErrorActionPreference = 'Stop'
$py = 'C:\Users\User\venvs\xrb-pilot\Scripts\python.exe'
Set-Location "$PSScriptRoot\scripts"
foreach ($d in 'v4','v4b1','v4b2','v4b3') { New-Item -ItemType Directory -Force "..\logs\$d" | Out-Null }
if ($test)  { & $py test_v4lib.py *> '..\logs\v4_test_v4lib.log' }
if ($a)     { & $py 16_v4a_algorithms.py *> '..\logs\v4\16_v4a_algorithms.log' }
if ($burst) { & $py 17_v4_burst_detect.py *> '..\logs\v4\17_v4_burst_detect.log'
              & $py 18_v4_burst_exclusion.py *> '..\logs\v4\18_v4_burst_exclusion.log' }   # needs results\v4\burst_visual.csv
if ($b3)    { & $py 19_v4b3_hexte.py *> '..\logs\v4b3\19_v4b3_hexte.log' }
if ($b2)    { & $py 20_v4b2_select.py *> '..\logs\v4b2\20_v4b2_select.log'
              $env:XRB_VERSION = 'v4b2'; & $py 21_v4b2_fetch_process.py *> '..\logs\v4b2\21_v4b2_fetch_process.log'; Remove-Item Env:XRB_VERSION
              & $py 22_v4b2_analysis.py *> '..\logs\v4b2\22_v4b2_analysis.log' }
if ($b1)    { & $py 23_v4b1_candidates.py *> '..\logs\v4b1\23_v4b1_candidates.log'
              $env:XRB_VERSION = 'v4b1'; & $py 24_v4b1_fetch_process.py *> '..\logs\v4b1\24_v4b1_fetch_process.log'; Remove-Item Env:XRB_VERSION
              & $py 25_v4b1_analysis.py *> '..\logs\v4b1\25_v4b1_analysis.log' }
Write-Host 'done; see results\v4*, figures\v4*'
