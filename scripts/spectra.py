"""Reading RXTE/PCA Standard-Product (StdProd) Std2 spectra without HEASoft.

What the files are (verified from headers, see logs/*headers.txt):
  xp<obs>_s2.pha : total (source+background) Std2 spectrum, COUNTS [count], STAT_ERR [count],
                   POISSERR=F, SYS_ERR=0, 129 channels, summed over the PCUs in ROWIDn (all layers).
  xp<obs>_b2.pha : pcabackest MODEL background spectrum for the same PCUs/GTIs, COUNTS + STAT_ERR.
  xp<obs>.rsp    : RMF*ARF combined response (SPECRESP MATRIX + EBOUNDS) for that PCU combination.
Net count rate (OGIP convention, same as XSPEC):
  r_net = C_s/(t_s*AREASCAL_s) - (BACKSCAL_s/BACKSCAL_b) * C_b/(t_b*AREASCAL_b)
StdProd spectra are NOT deadtime corrected (RXTE GOF deadtime page).
"""
import gzip, io
import numpy as np
from astropy.io import fits


def _open(path):
    return fits.open(path, memmap=False)


def read_pha(path):
    with _open(path) as h:
        sp = h['SPECTRUM']
        hd = sp.header
        d = sp.data
        pcus = sorted({hd[k][-1] for k in hd if k.startswith('ROWID')})
        gti = h['STDGTI'].data if 'STDGTI' in h else None
        out = dict(channel=np.asarray(d['CHANNEL'], int), counts=np.asarray(d['COUNTS'], float),
                   stat_err=np.asarray(d['STAT_ERR'], float),
                   exposure=float(hd['EXPOSURE']), backscal=float(hd.get('BACKSCAL', 1.0)),
                   areascal=float(hd.get('AREASCAL', 1.0)), poisserr=hd.get('POISSERR'),
                   sys_err=hd.get('SYS_ERR', 0), quality=hd.get('QUALITY', 0), grouping=hd.get('GROUPING', 0),
                   hduclas2=hd.get('HDUCLAS2'), hduclas3=hd.get('HDUCLAS3'), unit=sp.columns['COUNTS'].unit,
                   object=hd.get('OBJECT'), ra=hd.get('RA_OBJ'), dec=hd.get('DEC_OBJ'),
                   date_obs=hd.get('DATE-OBS'), tstart=hd.get('TSTART'), tstop=hd.get('TSTOP'),
                   mjdref=hd.get('MJDREFI', 0) + hd.get('MJDREFF', 0.0), pcus=''.join(pcus), npcu=len(pcus),
                   backfile=hd.get('BACKFILE'), respfile=hd.get('RESPFILE'), cpix=hd.get('CPIX1'),
                   ngti=0 if gti is None else len(gti), creator=hd.get('CREATOR'))
    return out


def read_rsp(path):
    """Return EBOUNDS (E_MIN,E_MAX per channel) and dense matrix R[energy, channel] in cm^2 counts/photon."""
    with _open(path) as h:
        eb = h['EBOUNDS'].data
        m = h['SPECRESP MATRIX'] if 'SPECRESP MATRIX' in h else h['MATRIX']
        md = m.data
        nch = len(eb)
        tlmin = int(m.header.get('TLMIN4', 0))
        R = np.zeros((len(md), nch))
        for i, row in enumerate(md):
            fch = np.atleast_1d(row['F_CHAN']); nc = np.atleast_1d(row['N_CHAN']); mat = np.asarray(row['MATRIX'])
            k = 0
            for f, n in zip(fch, nc):
                f, n = int(f) - tlmin, int(n)
                R[i, f:f+n] = mat[k:k+n]; k += n
        return dict(e_lo=np.asarray(md['ENERG_LO'], float), e_hi=np.asarray(md['ENERG_HI'], float), R=R,
                    ch_lo=np.asarray(eb['E_MIN'], float), ch_hi=np.asarray(eb['E_MAX'], float),
                    detnam=m.header.get('DETNAM'), hduclas3=m.header.get('HDUCLAS3'))


def overlap_matrix(src_lo, src_hi, dst_edges):
    """W[j, k] = fraction of source channel k that falls in destination bin j (uniform-within-channel assumption)."""
    W = np.zeros((len(dst_edges) - 1, len(src_lo)))
    for j in range(len(dst_edges) - 1):
        a, b = dst_edges[j], dst_edges[j+1]
        ov = np.clip(np.minimum(src_hi, b) - np.maximum(src_lo, a), 0, None)
        W[j] = ov / (src_hi - src_lo)
    return W


def net_spectrum(src, bkg, dcor=1.0):
    """Net count rate per channel [count/s] and 1-sigma statistical error (source Poisson + bkg-model stat)."""
    ts = src['exposure'] * src['areascal']; tb = bkg['exposure'] * bkg['areascal']
    scale = src['backscal'] / bkg['backscal']
    rs, es = src['counts'] / ts, src['stat_err'] / ts
    rb, eb = scale * bkg['counts'] / tb, scale * bkg['stat_err'] / tb
    # GOF recipe: the XSPEC source model is multiplied by DCOR = 1/(1-DTF), fitted to (source - background)
    # -> deadtime-corrected net rate = DCOR * (r_s - r_b)
    net = dcor * (rs - rb)
    err = dcor * np.sqrt(es ** 2 + eb ** 2)
    return net, err, rs, es, rb, eb


def powerlaw_folded(rsp, gamma=2.0):
    """Predicted count rate per channel for photon spectrum N(E)=E^-gamma (norm 1 ph/cm2/s/keV at 1 keV)."""
    lo, hi = rsp['e_lo'], rsp['e_hi']
    if gamma == 1: flux = np.log(hi/lo)
    else: flux = (hi**(1-gamma) - lo**(1-gamma)) / (1-gamma)
    return flux @ rsp['R']
