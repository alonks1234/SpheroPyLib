import numpy as np
from SpheroLib.shared_resources import SharedResources


class SpheroLibrary:
    def __init__(self, sphero_config):
        self.config = sphero_config
        self.shared_resources = SharedResources(sphero_config)
        self.shared_resources.get_numpy_resources()

    def get_sphero_states(self):
        rgb_state = np.random.randint(0, 255, self.shared_resources.resources["np_array_rgb"].shape).astype(np.uint8)
        depth_state = np.random.randint(0, 255, self.shared_resources.resources["np_array_depth"].shape).astype(np.uint16)
        audio_state = np.random.uniform(0, 1, self.shared_resources.resources["np_array_audio"].shape)
        rgb_state = rgb_state[::-self.shared_resources.sphero_config["CAMERA_OUTPUT_SKIP"]]
        depth_state = depth_state[::-self.shared_resources.sphero_config["CAMERA_OUTPUT_SKIP"]]
        state = {
            "rgb": rgb_state,
            "depth": depth_state,
            "audio": audio_state}
        if self.shared_resources.sphero_config["SIMULTANEOUS_SPHEROS"] > 0:
            state["spheros"] = np.random.uniform(0, 1, self.shared_resources.resources["np_array_sphero_states"].shape)
        timestamps = self.shared_resources.resources["np_array_timestamps"].copy()
        return state, timestamps

    def set_sphero_action(self, spheroNum, spheroHeading, spheroSpeed):
        return True
