from common import *
from astropy.io import fits
from astropy.table import Table
import pandas as pd
import numpy as np

NAMES=['GROJ1655-40','GRS1915+105','XTEJ1550-564','4U1543-47','4U1636-53','4U1608-52','4U1728-34','AQLX1']
def catalogs():
    allrows=[]
    for name in NAMES:
        p=download(ARCHIVE+'MissionLongData/'+name+'.fits.gz','data/raw/catalogs/'+name+'.fits.gz')
        with fits.open(p) as h:
            df=Table(h[1].data).to_pandas()
            df['OBSID']=[v.decode().strip() if isinstance(v,bytes) else v.strip() for v in df.OBSID]
            df['mjd']=df.TIME.astype(float)+h[1].header['MJDREFI']+h[1].header['MJDREFF']
        df['source_id']=name
        allrows.append(df)
        d=df[(df.mjd>=51677)&(df.mjd<54094)&(df.EXPOSURE>=500)&(df.STD1RATE>=5)]
        print(name,'eligible',len(d),'NPCU',d.NPCU.value_counts().sort_index().to_dict(),flush=True)
    out=pd.concat(allrows,ignore_index=True)
    out.to_csv(ROOT/'data/catalog_observations.csv',index=False)
    return out
if __name__=='__main__': catalogs()
