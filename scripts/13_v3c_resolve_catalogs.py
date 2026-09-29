"""v3c step 1 (local): check which candidate MissionLongData catalogues exist on HEASARC.
Run with XRB_VERSION=v3c AFTER verifying the candidate list in config.py. Writes data/v3c/candidate_catalogs.csv."""
import os, sys, urllib.error
from pathlib import Path
os.environ['XRB_VERSION'] = 'v3c'
sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import ROOT, ARCHIVE, download, progress
import config, csv
rows = []
for sid, cat, name, *_ in config.V3C_CANDIDATES:
    try:
        download(ARCHIVE + 'MissionLongData/' + cat + '.fits.gz', 'data/raw/catalogs/' + cat + '.fits.gz'); ok, why = True, ''
    except urllib.error.HTTPError as e:
        ok, why = False, f'HTTP {e.code} (catalogue name may differ; check HEASARC MissionLongData listing)'
    rows.append(dict(source_id=sid, catalog_name=cat, name=name, found=ok, note=why)); print(sid, ok, why, flush=True)
out = ROOT/'data/v3c/candidate_catalogs.csv'; out.parent.mkdir(parents=True, exist_ok=True)
with open(out, 'w', newline='', encoding='utf-8') as f:
    w = csv.DictWriter(f, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
progress('v3c_resolve', f'{sum(r["found"] for r in rows)}/{len(rows)} candidate catalogues found')
