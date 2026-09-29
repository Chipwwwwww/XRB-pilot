from pathlib import Path
import urllib.request, hashlib, json, datetime, time, threading
_LOCK = threading.Lock()

ROOT = Path(__file__).resolve().parents[1]
ARCHIVE = 'https://heasarc.gsfc.nasa.gov/FTP/xte/data/archive/'
for folder in ['data/raw','data/cache','data/processed','results','reports','figures','logs']:
    (ROOT/folder).mkdir(parents=True, exist_ok=True)

def download(url, relative):
    path = ROOT/relative
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists():
        for attempt in range(3):
            try:
                with urllib.request.urlopen(url, timeout=45) as r:
                    data = r.read()
                tmp = path.with_name(path.name+'.part')
                tmp.write_bytes(data)
                tmp.replace(path)
                break
            except Exception as e:
                if attempt == 2 or getattr(e, 'code', None) == 404: raise
                time.sleep(2)
        with _LOCK, (ROOT/'logs/downloads.jsonl').open('a',encoding='utf-8') as f:
            f.write(json.dumps(dict(url=url,path=relative,bytes=path.stat().st_size,
                sha256=hashlib.sha256(path.read_bytes()).hexdigest(),utc=datetime.datetime.now(datetime.UTC).isoformat()))+'\n')
    return path

def progress(stage, details):
    entry = dict(utc=datetime.datetime.now(datetime.UTC).isoformat(),stage=stage,details=details)
    with (ROOT/'logs/progress.jsonl').open('a',encoding='utf-8') as f:
        f.write(json.dumps(entry,ensure_ascii=False)+'\n')
    (ROOT/'reports/progress.json').write_text(json.dumps(entry,ensure_ascii=False,indent=2),encoding='utf-8')

import os
VERSION = os.environ.get('XRB_VERSION', 'v1')
if VERSION == 'v1':
    D, R, FG = ROOT/'data', ROOT/'results', ROOT/'figures'
else:
    D, R, FG = ROOT/'data'/VERSION, ROOT/'results'/VERSION, ROOT/'figures'/VERSION
for _p in [D/'processed', R, FG]:
    _p.mkdir(parents=True, exist_ok=True)
