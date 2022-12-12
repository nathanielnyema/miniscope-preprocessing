#!/bin/bash

#SBATCH --mail-user=nnyema@caltech.edu
#SBATCH --mail-type=BEGIN,END
#SBATCH --nodes=1
#SBATCH --cpus-per-task=56
#SBATCH --ntasks=1
#SBATCH --mem-per-cpu=6g
#SBATCH --output=logfiles/R-%x.%j.out
#SBATCH --error=logfiles/R-%x.%j.err


source ~/.bashrc
source activate caiman
echo "attempting to filter data"
finalfile=$(/bin/bash filter.sh "$fpath"| tail -n 1)
echo "processing $finalfile"
python preprocess.py run_pipeline_online -f "$finalfile"
cnmffile="$(dirname $finalfile)/cnmf.hdf5"
echo "applying shifts from $cnmffile"
python preprocess.py apply_shifts_online_cust -f "$finalfile" -c "$cnmffile"
