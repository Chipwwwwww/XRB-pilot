#!/bin/bash
# v12 (preregistration_v12.md sec. 2): 3C50 background for one NICER observation, run inside WSL on the native file system.
# Usage: bash v12_bkg3c50.sh <obsid> <cl_url> <ufa_url> <outdir (/mnt/c/...)> <caldb dir (/mnt/c/...)>
# Prints "SHA256 <file> <hash> <bytes>" for both downloads, then "DONE <exit code>". Event files are deleted afterwards.
O=$1; CL=$2; UFA=$3; OUT=$4; CAL=$5
source /root/miniforge3/etc/profile.d/conda.sh
conda activate henv
[ -n "$HEADAS" ] && source $HEADAS/headas-init.sh > /dev/null 2>&1
export CALDB=$CAL CALDBCONFIG=$CAL/software/tools/caldb.config CALDBALIAS=$CAL/software/tools/alias_config.fits
export PFILES="/tmp/pf_$O;$HEADAS/syspfiles"; mkdir -p /tmp/pf_$O
W=/tmp/bkg3c50; D=$W/$O/xti/event_cl; rm -rf $W/$O; mkdir -p $D $OUT
ok=1
for u in "$CL" "$UFA"; do
  f=$D/$(basename $u)
  for k in 1 2 3; do curl -sS -f -L --connect-timeout 30 -o $f "$u" && break; sleep 5; done
  [ -s $f ] || ok=0
  echo "SHA256 $(basename $u) $(sha256sum $f | cut -c1-64) $(stat -c %s $f)"
done
if [ $ok = 1 ]; then
  gunzip -f $D/*.gz
  cd $W/$O && nibackgen3C50 rootdir=$W obsid=$O bkgidxdir=CALDB bkglibdir=CALDB gainepoch=AUTO clobber=yes chatter=1 totspec=tot_$O bkgspec=bkg_$O > $OUT/nibackgen3C50.log 2>&1
  rc=$?
  cp -f $W/$O/tot_$O.pi $W/$O/bkg_$O.pi $OUT/ 2>/dev/null
else
  rc=99
fi
rm -rf $W/$O /tmp/pf_$O
echo "DONE $rc"
