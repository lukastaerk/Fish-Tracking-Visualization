import json
import pandas as pd
import os
import numpy as np
import warnings
from time import gmtime, strftime
from src.config import BACK, BATCH_SIZE, FEEDING_SHAPE, FRAMES_PER_SECOND, FRONT, BLOCK, PLOTS_DIR, SERVER_FEEDING_TIMES_FILE, START_END_FEEDING_TIMES_FILE, RESULTS_PATH, FEEDINGTIME, CONFIG_DATA_PATH, TEX_DIR, sep
from src.metrics.metrics import calc_length_of_steps, num_of_spikes
from src.trajectory.feeding_shape import FeedingEllipse, FeedingRectangle
from src.utils import get_days_in_order, get_all_days_of_context, get_camera_pos_keys
from src.utils.utile import month_abbr2num
from .trajectory import Trajectory
from src.utils.transformation import pixel_to_cm

map_shape = {"rectangle":FeedingRectangle, "ellipse":FeedingEllipse}
FT_BLOCK, FT_DATE, FT_START, FT_END = "block","day","time_in_start","time_out_stop" # time_in_stop, time_out_start


class FeedingTrajectory(Trajectory):

    is_feeding = True
    dir_data_feeding = "%s/%s/feeding" % (RESULTS_PATH, BLOCK)
    dir_tex_feeding = TEX_DIR

    def __init__(self, shape=FEEDING_SHAPE, **kwargs):
        super().__init__(**kwargs)
        self.set_feeding_box(is_back=False)
        self.set_feeding_box(is_back=True)
        self.feeding_times = []
        self.visits = []
        self.num_df_feeding = []
        self.start_end_times = feeding_times_start_end_dict()
        self.reset_data()
        self.FeedingShape = map_shape[shape]()

    def reset_data(self):
        self.feeding_times = [dict() for i in range(self.N_fishes)]
        self.visits = [dict() for i in range(self.N_fishes)]
        self.num_df_feeding = [dict() for i in range(self.N_fishes)]

    def set_feeding_box(self, is_back=False):
        F = self.fig_back if is_back else self.fig_front
        _ = F.ax.plot([0, 0], [0, 0], "y--")

    def get_start_end_index(self, date, batch_number):
        if self.start_end_times is None:
            return 0, BATCH_SIZE
        (f_start, f_end) = self.start_end_times[date]
        # get start index
        if f_start * FRAMES_PER_SECOND < int(batch_number)* BATCH_SIZE:
            start_idx = 0
        elif f_start * FRAMES_PER_SECOND > (int(batch_number)+1)* BATCH_SIZE:
            start_idx = BATCH_SIZE
        else:
            start_idx = f_start * FRAMES_PER_SECOND - int(batch_number)* BATCH_SIZE
        # get end index
        if f_end * FRAMES_PER_SECOND < int(batch_number)* BATCH_SIZE:
            end_idx = 0
        elif f_end * FRAMES_PER_SECOND > (int(batch_number)+1)* BATCH_SIZE:
            end_idx = BATCH_SIZE
        else:
            end_idx = f_end * FRAMES_PER_SECOND - int(batch_number)* BATCH_SIZE
        return start_idx, end_idx

    def subplot_function(
        self,
        batch,
        date,
        directory,
        batch_number,
        fish_id,
        time_span="batch: 1,   00:00:00 - 00:30:00",
        is_back=False,
    ):
        F = self.fig_back if is_back else self.fig_front

        start_idx, end_idx = self.get_start_end_index(date, batch_number)
        F.ax.set_title(time_span, fontsize=10)
        last_frame = batch.FRAME.array[-1]
        if batch.x.array[-1] <= -1:
            batch.drop(batch.tail(1).index)

        feeding_filter = batch.FRAME.between(start_idx, end_idx)

        batchxy = pixel_to_cm(batch[["xpx", "ypx"]].to_numpy())
        F.line.set_data(*batchxy.T)

        fish_key = "%s_%s"%tuple(self.fish2camera[fish_id])
        feeding_b, box = self.FeedingShape.contains(
            batch[feeding_filter], fish_key, date
        )  # feeding_b: array of data frames that are inside the feeding box.
        feeding_size = feeding_b.shape[0]  # size of the feeding box gives us the time spent in the box in number of frames.
        # The next line identifies the indices of feeding_b array where the fish swims from in to out of the box in the next frame
        index_visits = []
        n_entries = 0
        # a case distinction has to be made: when the are no visits to the feeding box index_visits is empty.
        if feeding_size > 0:
            index_swim_in = np.where(
                feeding_b.FRAME[1:].array - feeding_b.FRAME[:-1].array != 1
            )[0]
            index_visits = [
                0,
                *(index_swim_in + 1),
                feeding_size - 1,
            ]  # The first visit to the box clearly happens at index 0 of feeding_b and the last visit ends at the last index of feeding_b
            n_entries = len(index_visits) - 1  # -1 for the last out index

        fb = pixel_to_cm(feeding_b[["xpx", "ypx"]].to_numpy()).T
        lines = F.ax.get_lines()
        # UPDATE BOX
        box_cm = pixel_to_cm(box)
        lines[1].set_data(*box_cm.T)

        lines = lines[2:]

        for i, l in enumerate(lines):
            if i < n_entries:
                s, e = index_visits[i], index_visits[i + 1]
                l.set_data(*fb[:, s:e])
            else:
                l.remove()
        for i in range(len(lines), n_entries):
            s, e = index_visits[i], index_visits[i + 1]
            _ = F.ax.plot(
                *fb[:, s:e],
                "r-",
                alpha=0.7,
                solid_capstyle="projecting",
                markersize=0.2
            )

        text_l = [
            " ",
            "#Visits: %s" % (n_entries),
            r"$\Delta$ Feeding: %s" % (strftime("%M:%S", gmtime(feeding_size / 5))),
        ]
        steps = calc_length_of_steps(batchxy)
        spikes, spike_places = num_of_spikes(steps)
        N = batchxy.shape[0]
        text_r = F.meta_text_rhs(N, last_frame - N, spikes)
        remove_text = F.meta_text_for_plot(text_l=text_l, text_r=text_r)

        # ax.draw_artist(ax.patch)
        # ax.draw_artist(line)
        self.update_feeding_and_visits(fish_id, date, feeding_size, n_entries, sum(feeding_filter))

        if self.write_fig:
            F.write_figure(directory, batch_number)
        remove_text()
        return F.fig

    def update_feeding_and_visits(self, fish_id, date, feeding_size, visits, num_df_feeding):
        if date not in self.feeding_times[fish_id]:
            self.feeding_times[fish_id][date] = 0
            self.visits[fish_id][date] = 0
            self.num_df_feeding[fish_id][date] = 0
        self.feeding_times[fish_id][date] += feeding_size
        self.visits[fish_id][date] += visits
        self.num_df_feeding[fish_id][date] += num_df_feeding

    def feeding_data_to_csv(self):
        fish_names = get_camera_pos_keys(is_feeding=self.is_feeding)
        days = get_all_days_of_context(is_feeding=self.is_feeding)
        df_feeding = pd.DataFrame(columns=[fish_names], index=days)
        df_visits = pd.DataFrame(columns=[fish_names], index=days)
        df_num_df_feeding = pd.DataFrame(columns=[fish_names], index=days)
        for i, fn in enumerate(fish_names):
            for d in days:
                if d in self.feeding_times[i]:
                    df_feeding.loc[d, fn] = self.feeding_times[i][d]
                    df_visits.loc[d, fn] = self.visits[i][d]
                    df_num_df_feeding.loc[d, fn] = self.num_df_feeding[i][d]

        os.makedirs(self.dir_data_feeding, exist_ok=True)
        df_feeding.to_csv("%s/%s.csv" % (self.dir_data_feeding, "feeding_times"))
        df_visits.to_csv("%s/%s.csv" % (self.dir_data_feeding, "visits"))
        df_num_df_feeding.to_csv("%s/%s.csv" % (self.dir_data_feeding, "num_df_feeding"))

    def feeding_data_to_tex(self):
        text = """\newcommand\ftlist{}\newcommand\setft[2]{\csdef{ft#1}{#2}}\newcommand\getft[1]{\csuse{ft#1}}""".replace(
            "\n", "\\n"
        ).replace(
            "\f", "\\f"
        )

        for i, (c, p) in enumerate(self.fish2camera):
            days = get_days_in_order(
                is_feeding=self.is_feeding, camera=c, is_back=p == BACK
            )
            for d in days:
                if d in self.feeding_times[i]:
                    text += "\setft{%s%s%s}{%s}" % (
                        c,
                        p,
                        d,
                        strftime("%H:%M:%S", gmtime(self.feeding_times[i][d] / 5)),
                    )
                    text += "\setft{%s%s%sv}{%s}" % (c, p, d, self.visits[i][d])
                    text += "\setft{%s%s%snum}{%s}" % (c,p,d,strftime("%H:%M:%S", gmtime(self.num_df_feeding[i][d] / 5)))
        text_file = open("%s/%s_feedingtime.tex" % (self.dir_tex_feeding, BLOCK), "w")
        text_file.write(text)
        text_file.close()

def feeding_times_start_end_dict():
    if os.path.exists(START_END_FEEDING_TIMES_FILE):
        return json.load(open(START_END_FEEDING_TIMES_FILE, "r"))
    else:
        if not os.path.exists(SERVER_FEEDING_TIMES_FILE):
            warnings.warn(f"File {SERVER_FEEDING_TIMES_FILE} not found, thus feeding times will be calculated over all provided batches, if this is not intended please check the path in scripts/env.sh")
            return None
        else:
            ft_df = pd.read_csv(SERVER_FEEDING_TIMES_FILE, usecols=[FT_BLOCK, FT_DATE, FT_START, FT_END], sep=sep)
            block_ft = ft_df[(ft_df[FT_BLOCK]==int(BLOCK[5:])) & ~ft_df[FT_START].isna()]
            start_end = dict([("20%s%02d%02d_%s"%(*list(map(int,reversed(d.split(".")))),FEEDINGTIME), 
                                (get_df_idx_from_time(s),get_df_idx_from_time(e))) for (d,s,e) in zip(
                block_ft[FT_DATE],
                block_ft[FT_START],
                block_ft[FT_END])
                                ])
            json.dump(start_end, open(START_END_FEEDING_TIMES_FILE, "w"))
            return start_end

def get_df_idx_from_time(time,start_time=FEEDINGTIME): 
    """
    @time hh:mm
    @start_time hhmmss 
    """
    time_sec = sum([int(t)*f for (t, f) in zip(time.split(":"),[3600, 60])])
    start_time_sec = sum([int(t)*f for (t, f) in zip([start_time[i:i+2] for i in range(0,len(start_time),2)],[3600, 60, 1])])
    return time_sec - start_time_sec