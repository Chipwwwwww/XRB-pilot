# Re-run the whole pilot in order. Downloads are cached (existing files are not re-downloaded).
$ErrorActionPreference = 'Stop'
$py = 'C:\Users\User\venvs\xrb-pilot\Scripts\python.exe'
Set-Location "$PSScriptRoot\scripts"
& $py 03_select_observations.py *> ..\logs\03_select.log
& $py 04_fetch_process.py       *> ..\logs\04_fetch_process.log
& $py 05_two_source_check.py    *> ..\logs\05_two_source.log
& $py 06_dataset_checks.py      *> ..\logs\06_dataset_checks.log
& $py 07_train_eval.py          *> ..\logs\07_train_eval.log
& $py 08_error_analysis.py      *> ..\logs\08_error_analysis.log
Write-Host 'done; see results\, figures\, reports\'
