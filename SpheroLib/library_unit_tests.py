"""
A script to test functionality of the robot system via unit tests.
"""
from SpheroLib.Lib.config import sphero_config
from SpheroLib.Lib.sphero_library import SpheroLibrary
import time
import cv2
import numpy as np
from scipy.io.wavfile import write
import random
import os
import subprocess
from pathlib import Path
import shutil
import json
import matplotlib.pyplot as plt


def sensor_latency_test():
    """
    Listen for 30 seconds and calculate the average latency per sensor.
    """
    sphero_lib = SpheroLibrary(sphero_config)
    output = sphero_lib.get_sphero_states()
    print("Connected, beginning unit tests.")
    print(f"[Latency Test] Listening to sensor packets for {30} seconds.")
    start_time = time.time()
    counter = 0
    while time.time() - start_time < 30:
        [state, timestamps] = sphero_lib.get_sphero_states()
        time_ellapsed = time.time() - timestamps
        if counter == 0:
            running_avg_time_ellapsed = time_ellapsed
        else:
            running_avg_time_ellapsed += time_ellapsed
        counter += 1
    running_avg_time_ellapsed /= counter
    print(f"[Latency Test] Got {counter} packets in {30} seconds. ")
    print(f"Average latencies: {running_avg_time_ellapsed}")
    print("-" * 50)


def audio_test():
    """
    Produce a 30 second audio clip. It helps to play music near the arena, to tell if the output sounds about right.
    """
    sphero_lib = SpheroLibrary(sphero_config)
    output = sphero_lib.get_sphero_states()
    print("Connected, beginning unit tests.")
    start_time = time.time()
    sample_length = sphero_config["STATE_LEN_TIME_SECS"]
    print(f"[Audio Test] Recording {sample_length} second audio sample in {5} seconds")
    while time.time() - start_time < 5:
        time.sleep(.01)
    record_start_time = time.time()
    print(f"[Audio Test] Recording Sound Sample {sample_length} seconds")
    while time.time() - record_start_time < sample_length:
        time.sleep(.01)
    [state, timestamps] = sphero_lib.get_sphero_states()
    write('../output.wav', sphero_config["AUDIO_BYTES_PER_SECOND"], state["audio"])  # Save as WAV file
    print(f"[Audio Test] Saved {sample_length} second audio to ../output.wav")
    print("-" * 50)


def rgb_stream_test():
    """
    Stream the output of the rgb camera as fast as we can. Useful for checking latency and for
    figuring out image slicing to fit arena to image.
    """
    sphero_lib = SpheroLibrary(sphero_config)
    output = sphero_lib.get_sphero_states()
    print("Connected, beginning unit tests.")
    start_time = time.time()
    while time.time() - start_time < 100:
        [state, timestamps] = sphero_lib.get_sphero_states()
        print (state["depth"][-1])
        # cv2.imshow("RGB STREAM", state["rgb"][-1][:, 60:240])
        # cv2.waitKey(1)
        plt.imshow(state["depth"][-1], cmap="gray")
        plt.show()
        # cv2.imshow("Depth STREAM", cv2.cvtColor(state["depth"][-1], cv2.COLOR_GRAY2BGR))
    # cv2.destroyAllWindows()


def yaw_consistency_test():
    """
    Command the robot to spin in a circle in 90 degree increments. Print out the internal yaw sensor
    data before/after each action.
    """
    sphero_lib = SpheroLibrary(sphero_config)
    output = sphero_lib.get_sphero_states()
    print("Connected, beginning unit tests.")
    start_time = time.time()
    headings = [0, 90, 180, 270]
    heading_idx = 0
    while True:
        heading = headings[heading_idx]
        heading_idx = (heading_idx + 1) % len(headings)
        sphero_lib.set_sphero_action(0, heading, 0)
        [state, timestamps] = sphero_lib.get_sphero_states()
        sensor_heading = (-state["spheros"][0, -1, 6] + 180) % 360
        print (f"Desired Heading: {heading}    Sensor Heading: {sensor_heading}")
        time.sleep(1)
    print("-" * 50)


def action_latency_test():
    """
    Try to set the N spheros to do actions as quickly as we can.
    Record average time between successive actions for each sphero.
    """
    sphero_lib = SpheroLibrary(sphero_config)
    output = sphero_lib.get_sphero_states()
    print("Connected, beginning unit tests.")
    start_time = time.time()
    num_spheros = sphero_config["SIMULTANEOUS_SPHEROS"]
    action_response_times = [[] for sphero_num in range(num_spheros)]
    start_times = [time.time() for sphero_num in range(num_spheros)]

    while time.time() - start_time < 30:
        for sphero_num in range(num_spheros):
            random_heading = random.random() * 360
            random_speed = random.random() * 255
            sphero_lib.set_sphero_action(sphero_num, random_heading, random_speed)
            latency = time.time() - start_times[sphero_num]
            action_response_times[sphero_num].append(latency)
            start_times[sphero_num] = time.time()
    num_actions = [len(action_response_times[sphero_num]) for sphero_num in range(num_spheros)]
    average_latencies = [np.mean(action_response_times[sphero_num]) for sphero_num in range(num_spheros)]
    print(f"[Action Latency Test] Ran for {30} seconds on {num_actions} actions.")
    print(f"[Action Latency Test] Latency Average: {average_latencies}")
    print("-" * 50)


def audio_visual_robot_test():
    """
    Generate a movie with synced audio + video of robots doing random actions.
    """
    sphero_lib = SpheroLibrary(sphero_config)
    output = sphero_lib.get_sphero_states()
    print("Connected, beginning unit tests.")
    start_time = time.time()
    print(f"[Audio Visual Robot Test] running random actions for {sphero_config['STATE_LEN_TIME_SECS']} seconds")
    while time.time() - start_time < sphero_config["STATE_LEN_TIME_SECS"]:
        random_heading = random.random() * 360
        sphero_lib.set_sphero_action(0, random_heading, 0)
        time.sleep(1)
        # random_speed = random.random() * 255
        sphero_lib.set_sphero_action(0, random_heading, 255)
        time.sleep(2)
        sphero_lib.set_sphero_action(0, random_heading, 0)
        time.sleep(1)

    [state, timestamps] = sphero_lib.get_sphero_states()
    if os.path.exists("../movie.mp4"):
        os.remove("../movie.mp4")
    if os.path.exists("../temp.mp4"):
        os.remove("../temp.mp4")
    if os.path.exists("../temp.mp4"):
        os.remove("../temp.mp4")

    out = cv2.VideoWriter('../temp.mp4', cv2.VideoWriter_fourcc(*'mp4v'), sphero_config["CAMERA_TARGET_FPS"],
                          (sphero_config["RGB_WIDTH_PX"], sphero_config['RGB_HEIGHT_PX']))
    for img_elt, image in enumerate(state["rgb"]):
        out.write(image)
    out.release()
    write('../temp.wav', sphero_config["AUDIO_BYTES_PER_SECOND"], state["audio"])  # Save as WAV file

    process = subprocess.Popen(['ffmpeg', '-i', '../temp.mp4', '-i', '../temp.wav', '-c:v', 'copy', '-c:a',
                                'aac', '../movie.mp4'],
                               stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    process.communicate()
    print(f"[Audio Visual Robot Test] Robot movie saved to ../movie.mp4")
    print("-" * 50)


def robot_pushing_dataset_test(num_pushes, dataset_path):
    """
    Unit test of using the robots to do "pushing" actions. Rather than spamming the robot is actions,
    actions are "turn" then "drive straight"
    """
    sphero_lib = SpheroLibrary(sphero_config)
    output = sphero_lib.get_sphero_states()
    print("Connected, beginning unit tests.")
    start_time = time.time()
    # Delete the dataset if it exists
    print(f"[Robot Pushing Test] recording dataset to {dataset_path}")
    dirpath = Path(f"{dataset_path}")
    if dirpath.exists() and dirpath.is_dir():
        shutil.rmtree(dirpath)
    os.mkdir(f"{dataset_path}")

    # Run the pushing actions
    print(f"[Robot Pushing Test] running {num_pushes} pushing actions")
    for push_elt in range(num_pushes):
        push_path = f"{dataset_path}/{push_elt}"
        os.mkdir(f"{push_path}")
        for sphero_num in range(1):
            # Turn to a random angle
            [state, timestamps] = sphero_lib.get_sphero_states()
            initial_rgb_image = state["rgb"][-1]
            initial_depth_image = state["depth"][-1]
            random_heading = random.random() * 360
            sphero_lib.set_sphero_action(sphero_num, random_heading, 0)
            time.sleep(1)

            # Drive forwards at speed
            sphero_lib.set_sphero_action(sphero_num, 0, 255)
            time.sleep(2)

            # Record the robot state
            [state, timestamps] = sphero_lib.get_sphero_states()
            audio_file = f"{push_path}/audio.wav"
            audio = state["audio"].flatten()
            write(audio_file, sphero_config["AUDIO_BYTES_PER_SECOND"], audio)
            rgb_file = f"{push_path}/initial_rgb.jpg"
            cv2.imwrite(rgb_file, initial_rgb_image)
            for elt, rgb in enumerate(state["rgb"]):
                rgb_file = f"{push_path}/rgb{elt}.jpg"
                cv2.imwrite(rgb_file, rgb)
            depth_file = f"{push_path}/initial_depth.jpg"
            cv2.imwrite(depth_file, initial_depth_image)
            for elt, depth in enumerate(state["depth"]):
                depth_file = f"{push_path}/depth{elt}.jpg"
                cv2.imwrite(depth_file, depth)
            sphero_data = {sensor: list(state["spheros"][sphero_num][:, sensor_elt]) for sensor_elt, sensor in
                           enumerate(sphero_config["SPHERO_OUTPUT_VARIABLES"])}
            with open(f"{push_path}/sphero_sensors.json", 'w') as pkl_file:
                json.dump(str(sphero_data), pkl_file)
            action_data = {"angle": random_heading}
            with open(f"{push_path}/action_data.json", 'w') as pkl_file:
                json.dump(str(action_data), pkl_file)
            plt.title("Audio Sound Wave.")
            plt.plot(audio)
            plt.savefig(f"{push_path}/audio_waveform.jpg")
            # Settle Down
            sphero_lib.set_sphero_action(sphero_num, 0, 0)
            time.sleep(2)
            calm = False
            calm_start = time.time()
            while not calm:
                [state, timestamps] = sphero_lib.get_sphero_states()
                current_state = state["spheros"][sphero_num][0]
                speed = (current_state[3] ** 2 + current_state[4] ** 2) ** .5
                rotation = (current_state[5] ** 2 + current_state[6] ** 2 + current_state[7] ** 2) ** .5
                if (rotation < 15 and speed < 10) or time.time() - calm_start > 5:
                    calm = True


def robot_trajectory_test():
    sphero_lib = SpheroLibrary(sphero_config)
    output = sphero_lib.get_sphero_states()
    print("Connected, beginning unit tests.")
    start_time = time.time()
    while time.time()-start_time < sphero_config["STATE_LEN_TIME_SECS"]:
        heading_trajectory = np.random.uniform([0, 0, 0, 0, 0], [360, 360, 360, 360, 360])
        speed_trajectory = np.random.uniform([0, 0, 0, 0, 0], [255, 255, 255, 255, 255])
        traj_start = time.time()
        for elt in range(5):
            action_start = time.time()
            sphero_lib.set_sphero_action(0, heading_trajectory[elt], speed_trajectory[elt])
            time.sleep(max([.4 - (time.time() - action_start), 0]))
        print (time.time()-traj_start)
        sphero_lib.set_sphero_action(0, heading_trajectory[-1], 0)
        time.sleep(1)
        calm = False
        calm_start = time.time()
        # while not calm:
        #     [state, timestamps] = sphero_lib.get_sphero_states()
        #     current_state = state["spheros"][0][0]
        #     speed = (current_state[3] ** 2 + current_state[4] ** 2) ** .5
        #     rotation = (current_state[5] ** 2 + current_state[6] ** 2 + current_state[7] ** 2) ** .5
        #     if (rotation < 15 and speed < 10) or time.time() - calm_start > 3:
        #         calm = True
    [state, timestamps] = sphero_lib.get_sphero_states()
    if os.path.exists("../movie.mp4"):
        os.remove("../movie.mp4")
    if os.path.exists("../temp.mp4"):
        os.remove("../temp.mp4")
    if os.path.exists("../temp.mp4"):
        os.remove("../temp.mp4")
    out = cv2.VideoWriter('../temp.mp4', cv2.VideoWriter_fourcc(*'mp4v'), sphero_config["CAMERA_TARGET_FPS"],
                          (sphero_config["RGB_WIDTH_PX"], sphero_config["RGB_HEIGHT_PX"]))
    for img_elt, image in enumerate(state["rgb"]):
        out.write(image)
    out.release()
    write('../temp.wav', sphero_config["AUDIO_BYTES_PER_SECOND"], state["audio"])  # Save as WAV file
    process = subprocess.Popen(['ffmpeg', '-i', '../temp.mp4', '-i', '../temp.wav', '-c:v', 'copy', '-c:a',
                                'aac', '../movie.mp4'],
                               stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    process.communicate()
    print(f"[Audio Visual Robot Test] Robot movie saved to ../movie.mp4")
    print("-" * 50)

if __name__ == "__main__":
    # import multiprocessing as mp
    # mp.set_start_method("spawn")
    # sensor_latency_test()
    # audio_test()
    # action_latency_test()
    # rgb_stream_test()
    # audio_visual_robot_test()
    # robot_pushing_dataset_test(num_pushes=100, dataset_path="../test_dataset")
    # yaw_consistency_test()
    # robot_trajectory_test()