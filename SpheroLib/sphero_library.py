from SpheroLib.sphero_manager import SpheroManager
from SpheroLib.logger import run_logger
from SpheroLib.state_machine import run_state_machine
from SpheroLib.shared_resources import SharedResources
from SpheroLib.sensor_monitor import run_sensor_monitor
from SpheroLib.camera import run_camera
from SpheroLib.microphone import run_microphone
import signal
import subprocess
import os
import multiprocessing as mp
import numpy as np
import time


class SpheroLibrary:
    def __init__(self, sphero_config):
        self.shared_resources = SharedResources(sphero_config)
        signal.signal(signal.SIGINT, self.signal_handler)
        self.eliminate_old_pids()
        self.run_processes()

    def signal_handler(self, sig, frame):
        mypid = os.getpid()
        subprocess.call(["kill", "{}".format(mypid)])

    def run_processes(self):
        """
		Run all the parallel subprocesses that control cameras, audio, and spheros.
		"""
        self.procs = []
        self.procs.append(mp.Process(target=run_logger, args=(self.shared_resources,)))
        self.procs.append(mp.Process(target=run_state_machine, args=(self.shared_resources,)))
        self.procs.append(mp.Process(target=run_sensor_monitor, args=(self.shared_resources,)))
        self.procs.append(mp.Process(target=run_camera, args=(self.shared_resources,)))
        self.procs.append(mp.Process(target=run_microphone, args=(self.shared_resources,)))
        self.procs.append(mp.Process(target=SpheroManager, args=(self.shared_resources, )))
        [proc.start() for proc in self.procs]

    def get_sphero_states(self, sphero_num=None):
        """
		User command to get the state from the server. Makes a request of
		a handling process- if the request goes through, will return the state.

		Returns: [state, timestamps] where
			state is dict with fields: "rgb", "depth", "spheros", "audio"
			timestamps is np array with time of sensor measurements 
				(rgb, depth, audio, sphero0 ... sphero N)
		
		Otherwise returns False.
		"""
        while self.shared_resources.resources["library_state"].value != 5:
            time.sleep(.001)

        with self.shared_resources.resources["rgbd_pointer_lock"]:
            rgb_pointer = self.shared_resources.resources["rgb_ring_buffer_pointer"].value
            rgb_state = np.flip(np.concatenate(
                [self.shared_resources.resources["np_array_rgb"][rgb_pointer:],
                 self.shared_resources.resources["np_array_rgb"][:rgb_pointer]])
                [::-self.shared_resources.sphero_config["CAMERA_OUTPUT_SKIP"]].copy(), axis=0)
            depth_pointer = self.shared_resources.resources["depth_ring_buffer_pointer"].value
            depth_state = np.flip(np.concatenate(
                [self.shared_resources.resources["np_array_depth"][depth_pointer:],
                 self.shared_resources.resources["np_array_depth"][:depth_pointer]])
                [::-self.shared_resources.sphero_config["CAMERA_OUTPUT_SKIP"]].copy(), axis=0)

        state = {
            "rgb": rgb_state,
            "depth": depth_state,
            "audio": self.shared_resources.resources["np_array_audio"].copy()}
        if self.shared_resources.sphero_config["SIMULTANEOUS_SPHEROS"] > 0:
            state["spheros"] = self.shared_resources.resources["np_array_sphero_states"].copy()
        timestamps = self.shared_resources.resources["np_array_timestamps"].copy()
        return state, timestamps

    def set_sphero_action(self, spheroNum, spheroHeading, spheroSpeed):
        """
		If the library is in an up-state, will send an action to a sphero.
		Action = heading (0-360), speed (0-255).

		Returns True when the message gets through.
		"""
        assert self.shared_resources.sphero_config["SIMULTANEOUS_SPHEROS"] > 0, "no spheros in this arena"
        assert type(
            isinstance(spheroNum, int)) and 0 <= spheroNum < self.shared_resources.sphero_config["SIMULTANEOUS_SPHEROS"], \
            "spheroNum must be int mapping to active sphero (0-{})".format(
                self.shared_resources.sphero_config["SIMULTANEOUS_SPHEROS"] - 1)
        assert type(isinstance(spheroHeading, int)) and 0 <= spheroHeading <= 360, \
            "spheroHeading must be int between 0, 360"
        assert type(isinstance(spheroSpeed, int)) and 0 <= spheroSpeed <= 255, "spheroSpeed must be int between 0, 255"

        while self.shared_resources.resources["library_state"].value != 5:
            time.sleep(.001)

        while self.shared_resources.resources["np_array_sphero_actions"][spheroNum][2] != 0:
            time.sleep(.001)
        self.shared_resources.resources["np_array_sphero_actions"][spheroNum][0] = spheroHeading
        self.shared_resources.resources["np_array_sphero_actions"][spheroNum][1] = spheroSpeed
        self.shared_resources.resources["np_array_sphero_actions"][spheroNum][2] = 1

        # Wait until message is taken before returning
        while self.shared_resources.resources["np_array_sphero_actions"][spheroNum][2] != 0:
            time.sleep(.001)
        return True

    def eliminate_old_pids(self):
        """
		Sometimes older versions of ourselves fail to kill the 
		spawned subprocesses. We take care of that now, so that our
		memory doesn't 'splode and sensor hardware becomes available.
		"""
        pids = [pid for pid in os.listdir('/proc') if pid.isdigit()]
        our_pid = os.getpid()
        for pid in pids:
            try:
                splitted = open(os.path.join(
                    '/proc', pid, 'cmdline'), 'r').read().split('\0')
                if len(splitted) > 1:
                    splitted = [split.lower() for split in splitted]
                    if "sphero" in splitted[0] or "sphero" in splitted[1]:
                        if int(pid) != our_pid and "collector_manager" not in splitted[1]:
                            print(splitted)
                            self.shared_resources.resources["logging_queue"].put("Killing old pids: {}".format(pid))
                            subprocess.call(["kill", pid])
            except IOError:  # proc has already terminated
                continue
