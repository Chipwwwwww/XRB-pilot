"""Download official index products; inspect two real spectral triplets."""
from common import *
from astropy.io import fits
import re

names = ['GROJ1655-40','GRS1915+105','XTEJ1550-564','4U1543-47','4U1636-53','4U1608-52','4U1728-34','AqlX-1']
listing=download(ARCHIVE+'MissionLongData/','data/cache/mission_index.html').read_text()
links=re.findall(r'href="([^"]+\.fits\.gz)"',listing)
print('Relevant available names:',[x for x in links if any(s in x.upper() for s in ['1655','1915','1550','1543','1636','1608','1728','AQL'])])
for name in names[:1]+names[4:5]:
    p=download(ARCHIVE+'MissionLongData/'+name+'.fits.gz','data/raw/catalogs/'+name+'.fits.gz')
    with fits.open(p) as h:
        print(name,[(x.name,len(x.data) if x.data is not None else 0) for x in h])
        print(h[1].columns)
        print(str(h[1].data[0]))

progress('1_environment_and_archive','Existing folders and incomplete venv reused; official archive reachable; inspecting catalog structure.')
