set -e
cd /root
if [ ! -d /root/miniforge3 ]; then
  curl -sL -o Miniforge3.sh https://github.com/conda-forge/miniforge/releases/latest/download/Miniforge3-Linux-x86_64.sh
  bash Miniforge3.sh -b -p /root/miniforge3
fi
source /root/miniforge3/etc/profile.d/conda.sh
if [ ! -d /root/miniforge3/envs/henv ]; then
  /root/miniforge3/bin/mamba create -y -n henv heasoft -c https://heasarc.gsfc.nasa.gov/FTP/software/conda/ -c conda-forge
fi
conda activate henv
[ -n "$HEADAS" ] && source $HEADAS/headas-init.sh || true
echo HEADAS=$HEADAS
which fversion xspec pcabackest saextrct 2>&1
fversion
conda list -n henv | grep -iE "^heasoft|^xspec"