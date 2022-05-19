import time
import sys, os, inspect
import matplotlib.pyplot as plt
import numpy as np
from src.utile import get_camera_names, DIR_CSV_LOCAL, MEAN_GLOBAL, get_fish_ids, print_tex_table, get_fish2camera_map,get_camera_pos_keys, N_FISHES, N_SECONDS_PER_HOUR
from src.visualisation import Trajectory
from src.metrics import activity_per_interval, turning_angle_per_interval, tortuosity_per_interval, entropy_per_interval, metric_per_hour_csv, distance_to_wall_per_interval, absolute_angle_per_interval
from src.activity_plotting import sliding_window, sliding_window_figures_for_tex
from src.feeding import FeedingTrajectory
TRAJECTORY="trajectory"
FEEDING="feeding"
ACTIVITY="activity"
TURNING_ANGLE="turning_angle"
ABS_ANGLE="abs_angle"
TORTUOSITY="tortuosity"
ENTROPY="entropy"
WALL_DISTANCE="wall_distance"
ALL_METRICS="all"
programs = [TRAJECTORY,FEEDING, ACTIVITY, TURNING_ANGLE, ABS_ANGLE, TORTUOSITY, ENTROPY, WALL_DISTANCE]
metric_names = [ACTIVITY, TURNING_ANGLE, ABS_ANGLE, TORTUOSITY, ENTROPY, WALL_DISTANCE]
#time_intervals = [100,100,100,200]

def map_r_to_idx(results, fish_idx):
    return [results[i] for i in fish_idx]

def plotting_odd_even(results, time_interval=None, metric_name=None, name=None, ylabel=None, sw=10, visualize=None, **kwargs):
    ###
    if visualize is None:
        return None
    fish_keys = list(results.keys())
    fk_len = len(fish_keys)
    batch_size = 6
    fish_batches = []
    for start in range(0,fk_len,batch_size):
        end = min (start+batch_size, fk_len)
        fish_batches.append(list(range(start, end)))
    kwargs["write_fig"]=True

    fish_labels = get_fish_ids()
    positions = ["front_1", "front_2", "back_1", "back_2"]
    names = ["%s_%s"%(name, p) for p in positions]

    for i, batch in enumerate(fish_batches):
        print("Plotting %s %s"%(names[i], batch))
        print_tex_table(batch, positions[i])
        batch_keys = [fish_keys[i] for i in batch]
        #select_data = map_r_to_idx(results,batch_keys)
        f_ = sliding_window(results, time_interval, sw=sw, fish_keys=batch_keys, fish_labels=fish_labels[batch], ylabel=ylabel, name=names[i], **kwargs)
        plt.close(f_)
        sliding_window_figures_for_tex(results, time_interval, sw=sw, fish_keys=batch_keys, fish_labels=fish_labels[batch], ylabel=ylabel, name=names[i], **kwargs)

def main(program=None, test=0, time_interval=100, sw=10, fish_id=None, visualize=None):
    """param:   test, 0,1 when test==1 run test mode
                program: trajectory, activity, turning_angle
                time_interval: kwarg for the programs activity, turning_angle
    """
    if not os.path.isdir(DIR_CSV_LOCAL):
        print("TERMINATED: Please connect to external hard drive with path %s or edit path in scripts/env.sh"%DIR_CSV_LOCAL)
        return None
    is_feeding = program==FEEDING
    cameras = get_camera_names(is_feeding=is_feeding)
    fish2camera = get_fish2camera_map(is_feeding=is_feeding)
    fish_keys = get_camera_pos_keys(is_feeding=is_feeding)
    N_FISHES = len(fish2camera)
    if time_interval == "hour": # change of parameters when computing metrics by hour
        time_interval=N_SECONDS_PER_HOUR
        sw=1
    else:
        time_interval=int(time_interval)
    file_name = "%s_%s"%(time_interval, program)

    fish_ids = np.arange(N_FISHES)
    if fish_id != None:
        if fish_id.isnumeric():
            fish_ids=np.array([int(fish_id)])
        elif fish_id in fish_keys:
            fish_ids=np.array([fish_keys.index(fish_id)])
        else:
            raise ValueError("fish_id=%s does not appear in the data, please provid the fish_id as camera_position or index integer in [0 to %s]. \n\n The following ids are valid: %s"%(fish_id, N_FISHES-1, fish_keys))

    if int(test) == 1:
        print("Test RUN ", program)
        fish_ids=fish_ids[8:9]
        print("For fish indices: %s"%(fish_ids))

    kwargs_metrics=dict(fish_ids=fish_ids, time_interval=time_interval, write_to_csv=True)
    kwargs_plotting=dict(name=file_name, sw=sw, visualize=visualize)

    if program == TRAJECTORY:
        T = Trajectory()
        T.plots_for_tex(fish_ids)

    elif program == FEEDING:
        FT = FeedingTrajectory()
        FT.plots_for_tex(fish_ids)
        FT.feeding_data_to_csv()
        FT.feeding_data_to_tex()

    elif program == ACTIVITY:
        results = activity_per_interval(**kwargs_metrics)
        plotting_odd_even(**results, name=file_name, ylabel="activity", set_title=True, set_legend=True, baseline=MEAN_GLOBAL, sw=sw)

    elif program == TORTUOSITY:
        results = tortuosity_per_interval(**kwargs_metrics)
        plotting_odd_even(**results, ylabel="tortuosity", logscale=True, baseline=1, **kwargs_plotting)

    elif program == TURNING_ANGLE:
        results = turning_angle_per_interval(**kwargs_metrics)
        plotting_odd_even(**results, ylabel="turning angle", baseline=0, **kwargs_plotting)

    elif program == ABS_ANGLE:
        results = absolute_angle_per_interval(**kwargs_metrics)
        plotting_odd_even(**results, ylabel="absolute angle", **kwargs_plotting)

    elif program == ENTROPY:
        results = entropy_per_interval(**kwargs_metrics)
        plotting_odd_even(**results, ylabel="entropy", **kwargs_plotting)

    elif program == WALL_DISTANCE:
        results = distance_to_wall_per_interval(**kwargs_metrics)
        plotting_odd_even(**results, ylabel="distance to the wall", baseline=0, **kwargs_plotting)

    elif program == ALL_METRICS:
        for p in metric_names:
            main(p, time_interval=time_interval, fish_id=fish_id, sw=sw)
    else:
        print("Please provide the program name which you want to run. One of: ", programs)


    if program in metric_names and time_interval == N_SECONDS_PER_HOUR:
        metric_per_hour_csv(**results)
        print("wrote hourly metrics to CSV file")
    print("Done!")
    return None

if __name__ == '__main__':
    tstart = time.time()
    main_kwargs=dict(inspect.signature(main).parameters)
    try:
        kwargs = dict(arg.split('=') for arg in sys.argv[1:])
    except Exception as e:
        raise ValueError("Please supply the keyword arguments as follows: kwarg1=value ... ")
    for k in kwargs.keys():
        if k not in main_kwargs:
            raise ValueError("Please use the following keyword arguments %s"%main_kwargs.keys())
    main(**kwargs)
    tend = time.time()
    print("Running time:", tend-tstart, "sec.")
