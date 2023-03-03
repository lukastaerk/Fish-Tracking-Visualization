import shutil
import time
import sys, os, inspect
import matplotlib.pyplot as plt
import numpy as np
import argparse
from fishproviz.metrics.exploration_trials import exploration_trials
from fishproviz.utils import get_camera_pos_keys
from fishproviz.config import (
    DIR_CSV_LOCAL,
    HOURS_PER_DAY,
    MEAN_GLOBAL,
    N_SECONDS_PER_HOUR,
    dir_back,
    PLOTS_DIR,
    RESULTS_PATH,
    create_directories
)
from fishproviz.trajectory import Trajectory, FeedingTrajectory
from fishproviz.metrics import (
    activity_per_interval,
    turning_angle_per_interval,
    tortuosity_per_interval,
    entropy_per_interval,
    metric_per_hour_csv,
    distance_to_wall_per_interval,
    absolute_angle_per_interval,
)
from fishproviz.visualizations.activity_plotting import (
    sliding_window,
    sliding_window_figures_for_tex,
)
from fishproviz.utils import is_valid_dir

TRAJECTORY = "trajectory"
FEEDING = "feeding"
TRIAL_TIMES = "trial_times"
ACTIVITY = "activity"
TURNING_ANGLE = "turning_angle"
ABS_ANGLE = "abs_angle"
TORTUOSITY = "tortuosity"
ENTROPY = "entropy"
WALL_DISTANCE = "wall_distance"
ALL_METRICS = "all"
CLEAR = "clear"
metric_names = [ACTIVITY, TURNING_ANGLE, ABS_ANGLE, TORTUOSITY, ENTROPY, WALL_DISTANCE]
programs = [TRAJECTORY,FEEDING, TRIAL_TIMES, *metric_names, ALL_METRICS, CLEAR]

def main_metrics(program, time_interval=100, include_median=None, **kwargs_metrics):
    if time_interval in ["hour", "day"]:
        time_interval = {"hour": N_SECONDS_PER_HOUR, "day": N_SECONDS_PER_HOUR * HOURS_PER_DAY}[time_interval]
    else:
        time_interval = int(time_interval)

    if include_median and program != ACTIVITY:
        raise ValueError("include_median is only valid for activity")

    kwargs_metrics.update(time_interval=time_interval)

    metric_functions = {
        ACTIVITY: activity_per_interval,
        TORTUOSITY: tortuosity_per_interval,
        TURNING_ANGLE: turning_angle_per_interval,
        ABS_ANGLE: absolute_angle_per_interval,
        ENTROPY: entropy_per_interval,
        WALL_DISTANCE: distance_to_wall_per_interval,
    }

    if program not in metric_functions:
        print("TERMINATED: Invalid program")
        return

    results = metric_functions[program](include_median=include_median, **kwargs_metrics)

    if time_interval in [N_SECONDS_PER_HOUR, N_SECONDS_PER_HOUR * HOURS_PER_DAY]:
        metric_per_hour_csv(**results)


def get_fish_ids_to_run(program, fish_id):
    fish_keys = get_camera_pos_keys()
    n_fishes = len(fish_keys)

    fish_ids = np.arange(n_fishes)
    if fish_id is not None:
        if fish_id.isnumeric():
            fish_ids = np.array([int(fish_id)])
        elif fish_id in fish_keys:
            fish_ids = np.array([fish_keys.index(fish_id)])
        else:
            raise ValueError(
                "fish_id=%s does not appear in the data, please provid the fish_id as camera_position or index integer in [0 to %s]. \n\n The following ids are valid: %s"
                % (fish_id, n_fishes - 1, fish_keys)
            )
        print("program", program, "will run for fish:", fish_keys[fish_ids[0]])
    return fish_ids


def main(
    program=None,
    time_interval=100,
    fish_id=None,
    include_median=None,
):
    """param:   test, 0,1 when test==1 run test mode
    program: trajectory, activity, turning_angle
    time_interval: kwarg for the programs activity, turning_angle
    """
    fish_ids = get_fish_ids_to_run(program, fish_id)
    kwargs_metrics = dict(
        fish_ids=fish_ids,
        time_interval=time_interval,
        write_to_csv=True,
        include_median=include_median,
    )
    # PROGRAM METRICS or TRAJECTORY or CLEAR
    if program == TRAJECTORY:
        T = Trajectory()
        T.plots_for_tex(fish_ids)
    elif program == FEEDING:
        FT = FeedingTrajectory()
        FT.plots_for_tex(fish_ids)
        FT.feeding_data_to_csv()
        FT.feeding_data_to_tex()
    elif program == TRIAL_TIMES:
        exploration_trials()
    elif program in metric_names:
        main_metrics(program, **kwargs_metrics)
    elif program == ALL_METRICS:
        for p in metric_names:
            main_metrics(p, **kwargs_metrics)
    elif program == CLEAR:  # clear all data remove directories DANGEROUS!
        for path in [PLOTS_DIR, RESULTS_PATH]:  # VIS_DIR
            if os.path.isdir(path):
                shutil.rmtree(path)
                print("Removed directory: %s" % path)
    return None

def set_args():
    parser = argparse.ArgumentParser(prog = 'fishproviz',
        description = 'What the program does',
        epilog = 'Text at the bottom of help')
    parser.add_argument("program", help="Select the program you want to execute", type=str, choices=programs)
    parser.add_argument("-ti","--time_interval", help="Choose a time interval to compute averages of metrics", type=int, default=100)
    parser.add_argument("-fid","--fish_id", help="Fish id to run")
    parser.add_argument("--include_median", help="Include median or not for activity", action="store_true")
    args = parser.parse_args()
    return args

if __name__ == "__main__":
    args = set_args()
    tstart = time.time()
    create_directories()
    main_kwargs = dict(inspect.signature(main).parameters)
   
    main(**args.__dict__)
    tend = time.time()
    print("Running time:", tend - tstart, "sec.")
