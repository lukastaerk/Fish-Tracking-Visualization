#!/bin/bash
# src/utile.py imports the paths of this file and the bash scripts in tex/ to generate the pdfs do the same

N_BATCHES=15 # SPECIFY THE NUMBER OF BATCHES TO RUN THE SCRIPT ON
# 15 for 8 hours and 8 for feeding f.e. 
MIN_BATCH_IDX=0 # SPECIFY THE MINIMUM BATCH-INDEX OF THE DAY TO INCLUDE IN THE PDF
MAX_BATCH_IDX=$((N_BATCHES - 1)) # SPECIFY THE MAXIMUM BATCH-INDEX OF THE DAY TO INCLUDE IN THE PDF
HOURS_PER_DAY=8 # SPECIFY THE NUMBER OF HOURS TRACKED PER DAY
BATCH_SIZE=10000  # Number of data frames per batch
FRAMES_PER_SECOND=5 # Number of frames per second
# --- BLOCK -------
BLOCK="block1" # SPICIFY THE BLOCK TO RUN THE SCRIPT ON (block1, block2,...)
# -----------------
RECORDINGTIME="060000" # START TIME FOR THE EXPERIMENT
FEEDINGTIME="140000" # START TIME FOR THE FEEDING SETUP
STIME=$RECORDINGTIME 
# rootserver is the path to the data on the server and the directory where the data is stored
rootserver="/Volumes/data/loopbio_data/FE_(fingerprint_experiment)_SepDec2021"  # On MocOS the path to the root of the data
path_recordings="$rootserver/FE_recordings/FE_recordings_$BLOCK/FE_${BLOCK}_recordings_*" # path to the recordings, will allway be on the server

# --- The Path to the local data ------------
root_local="/Volumes/Extreme_SSD" # ".." "/Users/lukastaerk/fish" #
path="FE_tracks"
#path_original="FE_tracks_original/FE_tracks_${STIME}/FE_tracks_${STIME}_$BLOCK"
# --------------------------------------

# TRAJECTORY PATHS
path_csv="$rootserver/$path"
path_csv_local="$root_local/$path"
POSITION_STR_FRONT="FE_${BLOCK}_${STIME}_front_final"
POSITION_STR_BACK="FE_${BLOCK}_${STIME}_back_final"
dir_front=$path_csv_local/$POSITION_STR_FRONT
dir_back=$path_csv_local/$POSITION_STR_BACK

# FEEDING PATHS
path_csv_feeding="$rootserver/FE_tracks_original/FE_tracks_${FEEDINGTIME}/FE_tracks_${FEEDINGTIME}_$BLOCK"
path_csv_feeding_local="$root_local/FE_tracks_original/FE_tracks_${FEEDINGTIME}/FE_tracks_${FEEDINGTIME}_$BLOCK"
POSITION_STR_FRONT_FEEDING="FE_${FEEDINGTIME}_tracks_${BLOCK}_front"
POSITION_STR_BACK_FEEDING="FE_${FEEDINGTIME}_tracks_${BLOCK}_back"

dir_feeding_front="${path_csv_feeding_local}/$POSITION_STR_FRONT_FEEDING"
dir_feeding_back="${path_csv_feeding_local}/$POSITION_STR_BACK_FEEDING"

export BLOCK
export STIME
export FEEDINGTIME
export rootserver
export root_local
export path_csv
export path_csv_local
export path_recordings
export POSITION_STR_BACK
export POSITION_STR_FRONT
export POSITION_STR_FRONT_FEEDING
export POSITION_STR_BACK_FEEDING
export dir_back
export dir_front
export dir_feeding_back
export dir_feeding_front
