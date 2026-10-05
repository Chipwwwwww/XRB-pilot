#!/bin/bash
# v8d (preregistration_v8.md sec. 6): HEASoft in WSL. Usage: bash v8d_heasoft.sh <positions.csv> <nh_out.csv> <grid.txt> <trans_out.csv>
# positions.csv: name,ra,dec (header line). nh: HI4PI map (refdata/h1_nh_HI4PI.fits), disio 0.1 deg -> avnh, avwnh.
# XSPEC: tbabs (abund wilm, xsect vern) * powerlaw(Gamma) photon fluxes in the three MAXI bands for every N_H of grid.txt.
source /root/miniforge3/etc/profile.d/conda.sh
conda activate henv
[ -n "$HEADAS" ] && source $HEADAS/headas-init.sh > /dev/null 2>&1
export PFILES="/tmp/pf_v8d;$HEADAS/syspfiles"; mkdir -p /tmp/pf_v8d
POS=$1; NHOUT=$2; GRID=$3; TOUT=$4; GAMMA=${5:-2.0}
echo "name,ra,dec,avnh,avwnh,map" > "$NHOUT"
tail -n +2 "$POS" | tr -d '\r' | while IFS=, read -r name ra dec; do
  nh equinox=2000 ra=$ra dec=$dec size=1 disio=0.1 usemap=0 tchat=0 > /dev/null 2>&1
  a=$(pget nh avnh); w=$(pget nh avwnh); m=$(pget nh map)
  echo "\"$name\",$ra,$dec,$a,$w,$(basename $m)" >> "$NHOUT"
done
TCL=/tmp/v8d_trans.tcl
{
  echo "query yes"; echo "chatter 0"; echo "abund wilm"; echo "xsect vern"
  echo "dummyrsp 0.5 30.0 5000 lin"
  echo "model tbabs*powerlaw & 0.0 & $GAMMA & 1.0"
  echo "set fo [open $TOUT w]"
  echo "puts \$fo \"nh_1e22,L,M,H\""
  while read -r nh; do
    echo "newpar 1 $nh"
    echo "flux 2.0 4.0"; echo "tclout flux"; echo "set fl [lindex \$xspec_tclout 3]"
    echo "flux 4.0 10.0"; echo "tclout flux"; echo "set fm [lindex \$xspec_tclout 3]"
    echo "flux 10.0 20.0"; echo "tclout flux"; echo "set fh [lindex \$xspec_tclout 3]"
    echo "puts \$fo \"$nh,\$fl,\$fm,\$fh\""
  done < <(tr -d '\r' < "$GRID")
  echo "close \$fo"; echo "exit"
} > $TCL
xspec - $TCL > /tmp/v8d_xspec.log 2>&1
echo "xspec exit $?"; xspec_version=$(grep -m1 -i "XSPEC version" /tmp/v8d_xspec.log); echo "$xspec_version"
