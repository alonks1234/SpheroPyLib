from SpheroLib.config import sphero_config
from SpheroLib.sphero_library import SpheroLibrary
import numpy as np
import os
import cv2
import json
from pathlib import Path
import shutil
import time
from scipy.io.wavfile import write
import matplotlib.pyplot as plt
import sys

if __name__ == "__main__":
    print(sys.argv)
    import multiprocessing as mp
    mp.set_start_method("spawn")
    dataset_name = "dataset"
    num_samples = 40000
    dir_path = Path(f"{dataset_name}")
    if dir_path.exists() and dir_path.is_dir():
        start_num = len(os.listdir(dataset_name))
    else:
        start_num = 0
        os.mkdir(dataset_name)
    sphero_lib = SpheroLibrary(sphero_config)
    output = sphero_lib.get_sphero_states()

    # angles = [60, 0, 300]
    # speeds = [0, 100]
    # single_actions = [(x, y) for x in angles for y in speeds]
    # possible_actions = [(x, y) for x in single_actions for y in single_actions]

    for sample in range(start_num, num_samples + start_num):
        print(f"\rGathering Sample {sample}/{num_samples}", end=' ')
        sample_path = f"{dataset_name}/{sample}"
        [initial_state, _] = sphero_lib.get_sphero_states()
        # action_selection = np.random.randint(0, len(possible_actions))
        # action = possible_actions[action_selection]
        # heading_trajectory = [action[0][0], action[1][0]]
        # speed_trajectory = [action[0][1], action[1][1]]
        heading_trajectory = np.random.randint([0] * 4, [360] * 4)
        speed_trajectory = np.random.randint([0] * 4, [255] * 4)
        traj_start_time = time.time()
        for elt in range(4):
            action_start = time.time()
            sphero_lib.set_sphero_action(0, heading_trajectory[elt], speed_trajectory[elt])
            sphero_lib.set_sphero_action(1, heading_trajectory[elt], speed_trajectory[elt])
            time.sleep(max([.5 - (time.time() - action_start), 0]))
        [state, _] = sphero_lib.get_sphero_states()
        sphero_lib.set_sphero_action(0, heading_trajectory[-1], 0)
        time.sleep(1)
        """
        Save the data
        """
        os.mkdir(sample_path)
        cv2.imwrite(f"{sample_path}/rgb0.jpg", initial_state["rgb"][-1][:, 60:240])
        cv2.imwrite(f"{sample_path}/depth0.jpg", initial_state["depth"][-1][:, 70:310] / 64)
        write(f"{sample_path}/audio.wav", sphero_config["AUDIO_BYTES_PER_SECOND"], state["audio"].flatten())
        [cv2.imwrite(f"{sample_path}/rgb{rgb_elt + 1}.jpg", rgb[:, 60:240]) for rgb_elt, rgb in enumerate(state["rgb"])]
        [cv2.imwrite(f"{sample_path}/depth{d_elt + 1}.jpg", depth[:, 70:310] / 64) for d_elt, depth in
         enumerate(state["depth"])]
        sphero_data = {sensor: list(state["spheros"][0][:, sensor_elt]) for sensor_elt, sensor in
                       enumerate(sphero_config["SPHERO_OUTPUT_VARIABLES"])}
        sphero_data["angle_traj"] = list(heading_trajectory)
        sphero_data["speed_traj"] = list(speed_trajectory)
        with open(f"{sample_path}/data.json", 'w') as pkl_file:
            json.dump(repr(sphero_data), pkl_file)
        calm = False
        calm_start = time.time()
        while not calm:
            [state, timestamps] = sphero_lib.get_sphero_states()
            current_state = state["spheros"][0][0]
            speed = (current_state[3] ** 2 + current_state[4] ** 2) ** .5
            rotation = (current_state[5] ** 2 + current_state[6] ** 2 + current_state[7] ** 2) ** .5
            if (rotation < 15 and speed < 10) or time.time() - calm_start > 3:
                calm = True
        random_heading = np.random.randint(0, 360)
        sphero_lib.set_sphero_action(0, random_heading, 0)
        time.sleep(1)

