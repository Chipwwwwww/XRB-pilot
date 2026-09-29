"""Independent check of the Python background subtraction with HEASoft/XSPEC (run inside WSL Ubuntu, conda env 'henv').
For 12 fixed random v2 observations: XSPEC 'data/back/resp; ignore **-5.0 25.0-**; tclout rate' vs Python net count
rate (no deadtime, summed over PCUs) over exactly the channels XSPEC noticed. Output: results/v2/xspec_crosscheck.csv"""
import os
os.environ.setdefault('XRB_VERSION', 'v2')
from common import *
from config import *
from spectra import *
import subprocess, gzip, shutil, numpy as np, pandas as pd

obs = pd.read_csv(D/'observations.csv', dtype={'obs_id': str})
acc = obs[obs.in_dataset]
pick = acc.sample(12, random_state=SEED)
work = ROOT/'data/raw/xspec_check'; work.mkdir(parents=True, exist_ok=True)
wsl_root = '/mnt/c' + str(ROOT).replace('\\', '/')[2:]
rows = []
for r in pick.itertuples():
    o = r.obs_id.replace('-', '')
    names = {}
    for k in ['path_src', 'path_bkg', 'path_rsp']:
        src = ROOT/getattr(r, k); dst = work/src.name[:-3]            # XSPEC resolves BACKFILE by unzipped name
        with gzip.open(src, 'rb') as f, open(dst, 'wb') as g: shutil.copyfileobj(f, g)
        names[k] = dst.name
    cmd = f'''source /root/miniforge3/etc/profile.d/conda.sh && conda activate henv && cd {wsl_root}/data/raw/xspec_check && xspec <<'EOF'
query yes
chatter 0
data 1:1 {names['path_src']}
backgrnd 1 {names['path_bkg']}
response 1 {names['path_rsp']}
ignore 1:**-5.0 25.0-**
tclout rate 1
puts "RATE $xspec_tclout"
tclout noticed 1
puts "NOTICED $xspec_tclout"
exit
EOF'''
    out = subprocess.run(['wsl.exe', '-d', 'Ubuntu-22.04', '-u', 'root', '--', 'bash', '-lc', cmd],
                         capture_output=True, text=True, timeout=300).stdout
    rate = [l for l in out.splitlines() if l.startswith('RATE')]; ntc = [l for l in out.splitlines() if l.startswith('NOTICED')]
    if not rate or not ntc:
        rows.append(dict(obs_id=r.obs_id, source_id=r.source_id, error=out[-300:])); continue
    x_net, x_err = map(float, rate[0].split()[1:3])
    lo, hi = [int(v) for v in ntc[0].replace('-', ' ').split()[1:3]]       # 1-based noticed channel range
    s, b = read_pha(ROOT/r.path_src), read_pha(ROOT/r.path_bkg)
    net, err, *_ = net_spectrum(s, b, 1.0)
    m = slice(lo - 1, hi)
    p_net, p_err = net[m].sum(), np.sqrt((err[m]**2).sum())
    rows.append(dict(obs_id=r.obs_id, source_id=r.source_id, noticed=f'{lo}-{hi}', xspec_net=x_net, xspec_err=x_err,
                     python_net=p_net, python_err=p_err, ratio=p_net/x_net, err_ratio=p_err/x_err))
    print(rows[-1], flush=True)
df = pd.DataFrame(rows); df.to_csv(R/'xspec_crosscheck.csv', index=False)
print(df.to_string()); progress('xspec_crosscheck_v2', f'max |ratio-1| = {np.nanmax(abs(df.ratio-1)):.2e}')
