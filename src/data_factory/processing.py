import os, glob
import pandas as pd
from src.methods import turning_directions, calc_steps
from src.utils.tank_area_config import get_area_functions
from src.utils.error_filter import all_error_filters
from src.utils.transformation import px2cm, normalize_origin_of_compartment
from src.metrics.metrics import update_filter_three_points
from src.config import BACK, BLOCK
import numpy as np
import hdf5storage
import motionmapperpy as mmpy
from motionmapperpy.motionmapper import mm_findWavelets

from src.utils import csv_of_the_day
from src.utils.utile import get_camera_pos_keys, get_days_in_order

projectRoot = 'content'
projectPath = '%s/Fish_moves'%projectRoot
WAVELET = 'wavelet'

def transform_to_traces_high_dim(data, filter_index, area_tuple):
    L = data.shape[0]
    fk, area = area_tuple
    data, new_area = normalize_origin_of_compartment(data, area, BACK in fk)
    steps = px2cm(calc_steps(data))
    xy_steps = px2cm(data[:-1]-data[1:])
    t_a = turning_directions(data)
    #wall = px2cm(distance_to_wall_chunk(data, new_area))
    f3 = update_filter_three_points(steps, filter_index)
    X = np.array((np.arange(1,L-1),xy_steps[:-1,0],xy_steps[:-1,1], t_a, data[1:-1,0], data[1:-1,1])).T 
    return X[~f3], new_area

def compute_projections(fish_key, day, area_tuple):
    cam, pos = fish_key.split("_")
    is_back = pos==BACK
    data_in_batches = csv_of_the_day(cam,day, is_back=is_back)[1]
    if len(data_in_batches)==0:
        print("%s for day %s is empty! "%(fish_key,day))
        return None,None
    data = pd.concat(data_in_batches)
    data_px = data[["xpx", "ypx"]].to_numpy()
    filter_index = all_error_filters(data_px, area_tuple)
    X, new_area = transform_to_traces_high_dim(data_px, filter_index, area_tuple)
    return X, new_area

def compute_all_projections(fish_keys=None, recompute=False):
    area_f = get_area_functions()
    if fish_keys is None:
        fish_keys = get_camera_pos_keys()
    for fk in fish_keys:
        days = get_days_in_order(camera=fk.split("_")[0], is_back=fk.split("_")[1]==BACK)
        for day in days:
            filename = projectPath + f'/Projections/{BLOCK}_{fk}_{day}_pcaModes.mat'
            if not recompute and os.path.exists(filename):
                continue
            area_tuple = (fk, area_f(fk,day))
            X, new_area = compute_projections(fk, day, area_tuple)
            if X is None: continue
            print(f"{fk} {fish_keys.index(fk)} {day} {days.index(day)} {X.shape}", flush=True)
            if X.shape[0]<1000:
                print("Skipe number of datapoints to small")
                continue
            hdf5storage.write(data={'projections': X[:,1:4], 
                                    'positions': X[:,4:], 
                                    'area':new_area, 
                                    'index':X[:,0]},
                              path='/', truncate_existing=True,
                        filename=filename,
                        store_python_metadata=False, matlab_compatible=True)
            

def subsample_train_dataset(parameters, fish_keys=None):
    area_f = get_area_functions()
    train_list = []
    if fish_keys is None:
        fish_keys = get_camera_pos_keys()
    for fk in fish_keys:
        days = get_days_in_order(camera=fk.split("_")[0], is_back=fk.split("_")[1]==BACK)
        for day in days:
            area_tuple = (fk, area_f(fk,day))
            X = compute_projections(fk, day, area_tuple, write_file=True)
            print(f"{fk} {fish_keys.index(fk)} {day} {days.index(day)} {X.shape}", flush=True)
            wlets, _ = mm_findWavelets(X[:,1:], parameters.pcaModes, parameters)
            select = np.random.choice(wlets.shape[0], parameters.training_points_of_day, replace=False)
            train_list.append((fk, day, wlets[select]))
    return train_list

def subsample_wavelet_and_embeddings(parameters, fish_keys=None):
    training_data_file = f"{parameters.projectPath}/{parameters.method}/{BLOCK}_{WAVELET}_"
    if not os.path.exists(training_data_file):
        train_list = subsample_train_dataset(parameters, fish_keys)
        trainingSetData = np.concatenate([w[2] for w in train_list])
        if parameters.method == "TSNE":
            X_em = mmpy.run_tSne(trainingSetData, parameters)
        elif parameters.method == "UMAP":
            X_em = mmpy.run_UMAP(trainingSetData, parameters)
        else:
            raise NotImplementedError("use TSNE or UMAP")
        hdf5storage.write(data={'trainingSetData': trainingSetData}, path='/', truncate_existing=True,
                          filename=training_data_file + 'training_data.mat', store_python_metadata=False,
                          matlab_compatible=True)

def load_trajectory_data(fk, parameters):
    data_by_day = []
    pfile = glob.glob(parameters.projectPath+f'/Projections/{BLOCK}_{fk}_*_pcaModes.mat')
    for f in pfile: 
        data = hdf5storage.loadmat(f)
        data_by_day.append(data)
    return data_by_day

def load_zVals(fk, parameters):
    data_by_day = []
    zValstr = get_zValues_str(parameters)
    pfile = glob.glob(parameters.projectPath+f'/Projections/{BLOCK}_{fk}_*_pcaModes_{zValstr}.mat')
    for f in pfile: 
        data = hdf5storage.loadmat(f)
        data_by_day.append(data)
    return data_by_day

def get_zValues_str(parameters):
    if parameters.method == 'TSNE':
        zValstr = 'zVals'
    else:
        zValstr = 'uVals'
    return zValstr





