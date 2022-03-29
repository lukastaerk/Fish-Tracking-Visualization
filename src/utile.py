from datetime import datetime
from time import gmtime, strftime
import pandas as pd
import numpy as np
import os
import re
import glob
from itertools import product
from envbash import load_envbash
load_envbash('scripts/env.sh')

# Calculated MEAN and SD for the data set filtered for erroneous frames 
MEAN_GLOBAL = 0.22746102241709162
SD_GLOBAL = 1.0044248513034164
S_LIMIT = MEAN_GLOBAL + 3 * SD_GLOBAL
BATCH_SIZE = 9999
ROOT=os.environ["rootserver"]
DIR_CSV=os.environ["path_csv"] # 
BLOCK = os.environ["BLOCK"] # block1 or block2
DIR_CSV_LOCAL = os.environ["path_csv_local"] # 
POS_STR_FRONT = os.environ["POSITION_STR_FRONT"]
POS_STR_BACK = os.environ["POSITION_STR_BACK"]
STIME = os.environ["STIME"]
FEEDINGTIME = os.environ["FEEDINGTIME"]
dir_front = "%s/%s"%(DIR_CSV_LOCAL, POS_STR_FRONT)
dir_back  = "%s/%s"%(DIR_CSV_LOCAL, POS_STR_BACK)
FRONT, BACK = "front", "back"
ROOT_img = "plots"

# FEEDING 
dir_feeding_front = os.environ["dir_feeding_front"]
dir_feeding_back = os.environ["dir_feeding_back"]

N_FISHES = 24
N_SECONDS_OF_DAY = 24*3600

def get_camera_names(is_feeding=False):
    dir_ = dir_feeding_front if is_feeding else dir_front
    return sorted([name for name in os.listdir(dir_) if len(name)==8 and name.isnumeric()])

def get_fish2camera_map(is_feeding=False):
    return np.array(list(product(get_camera_names(is_feeding), [FRONT, BACK])))

#fish2camera=np.array(list(product(get_camera_names(), [FRONT, BACK])))

def get_fish_ids():
    """
    Return the fish ids defined in ...livehistory.csv corresponding to the indices in fish2camera
    """
    # %ROOT
    info_df = pd.read_csv("data/DevEx_fingerprint_activity_lifehistory.csv", delimiter=";")
    #info_df = pd.read_csv("data/DevEx_fingerprint_activity_lifehistory.csv", delimiter=";")
    info_df1=info_df[info_df["block"]==int(BLOCK[-1])]
    info_df1[["fish_id", "camera", "block", "tank"]],
    fishIDs_order = list()
    FB_char = np.array(list(map(lambda x: str(x[-1]),info_df1["tank"])))
    fish2camera = get_fish2camera_map()
    for i, (c,p) in enumerate(fish2camera):
        f1 = info_df1["camera"] == int(c[-2:])
        f2 = FB_char == p[0].upper()
        ids = info_df1[f1 & f2]["fish_id"].array
        fishIDs_order.append(ids[0])
        
    return np.array(fishIDs_order)

def print_tex_table(fish_ids, filename):
    tex_dir = "tex/tables"
    os.makedirs(tex_dir, exist_ok=True)
    f = open("%s/%s.tex"%(tex_dir,filename), "w+")
    fids = get_fish_ids()
    fish2camera = get_fish2camera_map()
    for fid in fish_ids:
        camera, position = fish2camera[fid]
        f.write("%d & %s & %s & %s\\\ \n"%(fid, camera, position, fids[fid].replace("_","\_")))
    f.close()

def get_days_in_order(interval=None, is_feeding=False):
    cameras = get_camera_names(is_feeding)
    dir_ = dir_feeding_front if is_feeding else dir_front
    days = [name[:13] for name in os.listdir(dir_+"/"+cameras[0]) if name[:8].isnumeric()]
    days.sort()
    if interval:
        return days[interval[0]: interval[1]]
    return days

def get_time_for_day(day, nrF):
    # dateiso = "{}-{}-{}T{}:{}:{}+02:00".format(day[:4],day[4:6],day[6:8],day[9:11],day[11:13],day[13:15])
    hours, minutes, seconds = int(day[9:11]),int(day[11:13]), nrF/5
    seconds = seconds + minutes*60 + hours * 3600
    return strftime("%H:%M:%S", gmtime(seconds))

def get_seconds_from_day(day):
    """Retuns the time of the day in seconds from 0=:00 am on"""
    hours, minutes = int(day[9:11]),int(day[11:13])
    return minutes*60 + hours * 3600

def get_date(day):
    return day[:8]

def get_date_string(day):
    return "%s/%s/%s"%(day[:4], day[4:6], day[6:8])

def get_full_date(day):
    dateiso = "{}-{}-{}T{}:{}:{}+00:00".format(day[:4],day[4:6],day[6:8],day[9:11],day[11:13], day[13:15])
    return datetime.fromisoformat(dateiso).strftime("%A, %B %d, %Y %H:%M")
    
def get_position_string(is_back):
    if is_back:
        return BACK
    else:
        return FRONT
    
def read_batch_csv(filename, drop_errors):
    df = pd.read_csv(filename,skiprows=3, delimiter=';', on_bad_lines=False, usecols=["x", "y", "FRAME", "time", "xpx", "ypx"])
    df.dropna(axis="rows", how="any", inplace=True)
    if drop_errors:
        indexNames = df[:-1][ df[:-1].x.array <= -1].index # exept the last index for time recording
        df = df.drop(index=indexNames)
    df.reset_index(drop=True, inplace=True)
    return df

def merge_files(filenames, drop_errors):
    batches = []
    for f in filenames:
        df = read_batch_csv(f, drop_errors)
        batches.append(df)
    return batches


def csv_of_the_day(camera, day, is_back=False, drop_out_of_scope=False, is_feeding=False):
    """
    @params: camera, day, is_back, drop_out_of_scope
    returns csv of the day for camera: front or back
    """
    dir_ = dir_back if is_back else dir_front
    if is_feeding:
        dir_ = dir_feeding_back if is_back else dir_feeding_front

    filenames_f = [f for f in glob.glob("{}/{}/{}*/{}_{}*.csv".format(dir_, camera, day, camera, day), recursive=True) if re.search(r'[0-9].*\.csv$', f[-6:])]
    
    filtered_files = filter_filenames(filenames_f) # filters for dublicates in the batches for a day. It takes the FIRST one!!!

    return merge_files(filtered_files, drop_out_of_scope)

def filter_filenames(filenames_f):
    filenames_f.sort()
    i = 0 #"{:02d}".format(number)
    filtered_files = list()
    while len(filenames_f)!=0:
        f = filenames_f.pop(0)
        if "{:06d}".format(i) in f:
            filtered_files.append(f)
            i=i+1
    return filtered_files      
    
def activity_for_day_hist(fish_id, day_idx=1):
    fish2camera=get_fish2camera_map()
    camera_id, is_back = fish2camera[fish_id,0], fish2camera[fish_id,1]=="back"
    mu_sd = list()
    all_days = get_days_in_order()
    day = all_days[day_idx]
    df = pd.concat(csv_of_the_day(camera_id, day, is_back=is_back, drop_out_of_scope=True))
    c = calc_steps(df[["x", "y"]].to_numpy())
    p = plt.hist(c, bins=50,range=[0, 5], density=True, alpha=0.75)
    plt.ylim(0, 3)
    plt.xlabel('cm')
    plt.ylabel('Probability')
    plt.title('Histogram of step lengh per Frame')
    mu, om = np.mean(c), np.std(c)
    plt.text(mu, om, r'$\mu=\ $'+ "%.2f, "%mu + r'$\sigma=$'+"%.2f"%om)
    plt.show()