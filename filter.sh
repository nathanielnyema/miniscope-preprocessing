#!/bin/bash

if [ $# -eq 0 ];
then
  echo "$0: Missing arguments"
  exit 1
elif [ $# -gt 1 ];
then
  echo "$0: Too many arguments: $@"
  exit 1
else
  source ~/.bashrc
  source activate caiman 
  newfold="$(dirname $1)/ds"
  newfile="$newfold/$(basename -s ".${1##*.}" $1)_ds.avi"
  if [ -d "$newfold" -a ! -h "$newfold" ];
  then
    printf 'WARNING: data has already been downsampled...\n'
  else
    mkdir $newfold
    framerate=$(python preprocess.py print_fr -f $1)
    ffmpeg -n -i $1 -vf "tblend=average,framestep=2,tblend=average,framestep=2,setpts=0.25*PTS" -c:v libx264 -preset medium -qp 0 -pix_fmt yuv420p -crf 0 -r $framerate $newfile
  fi
  echo $newfile
  exit 0
fi