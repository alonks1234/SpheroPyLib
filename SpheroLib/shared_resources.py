import multiprocessing as mp
import numpy as np
import ctypes


class SharedResources:
    """
    Class for creating all the shared arrays, values, and queues used in library processes.
    """

    def __init__(self, sphero_config):
        self.sphero_config = sphero_config
        self.resources = dict()

        # State of the library
        lib_state = mp.Value('i')
        lib_state.value = 0
        self.resources["library_state"] = lib_state

        # Pointer to which index in the rgb-d buffers we are up to
        self.resources["rgbd_pointer_lock"] = mp.Lock()
        rgb_ring_buffer_pointer = mp.Value('i')
        rgb_ring_buffer_pointer.value = 0
        self.resources["rgb_ring_buffer_pointer"] = rgb_ring_buffer_pointer
        depth_ring_buffer_pointer = mp.Value('i')
        depth_ring_buffer_pointer.value = 0
        self.resources["depth_ring_buffer_pointer"] = depth_ring_buffer_pointer

        # Queues for passing information
        self.resources["rgb_queue"] = mp.Queue(maxsize=2)
        self.resources["depth_queue"] = mp.Queue(maxsize=2)
        if sphero_config["SIMULTANEOUS_SPHEROS"] > 0:
            self.resources["sphero_queue"] = mp.Queue(
                maxsize=sphero_config["SIMULTANEOUS_SPHEROS"] * 2)
        self.resources["audio_queue"] = mp.Queue(maxsize=2)

        self.resources["state_machine_queue"] = mp.Queue()
        self.resources["battery_queue"] = mp.Queue()
        self.resources["logging_queue"] = mp.Queue(maxsize=10)

        # Shared Arrays
        self.resources["mp_array_rgb"] = mp.Array(ctypes.c_uint8,
                                sphero_config["CAMERA_LENGTH_STATE_FULL"] * \
                                sphero_config["RGB_HEIGHT_PX"] * \
                                sphero_config["RGB_WIDTH_PX"] * \
                                3)

        self.resources["mp_array_depth"] = mp.Array(ctypes.c_uint16,
                                  sphero_config["CAMERA_LENGTH_STATE_FULL"] * \
                                  sphero_config["DEPTH_HEIGHT_PX"] * \
                                  sphero_config["DEPTH_WIDTH_PX"])

        self.resources["mp_array_audio"] = mp.Array(ctypes.c_float,
                                                    sphero_config["AUDIO_BYTES_PER_STATE"])

        if sphero_config["SIMULTANEOUS_SPHEROS"] > 0:
            self.resources["mp_array_sphero_states"] = mp.Array(ctypes.c_float,
                                                                sphero_config["SIMULTANEOUS_SPHEROS"] * \
                                                                sphero_config["SPHERO_LENGTH_STATE"] * \
                                                                len(sphero_config["SPHERO_OUTPUT_VARIABLES"]))

            self.resources["mp_array_sphero_actions"] = mp.Array(ctypes.c_int16,
                                                                 sphero_config["SIMULTANEOUS_SPHEROS"] * 3)

            self.resources["mp_array_sphero_sleep"] = mp.Array(ctypes.c_uint8,
                                                               sphero_config["SIMULTANEOUS_SPHEROS"])

            self.resources["mp_array_sphero_battery"] = mp.Array(ctypes.c_float,
                                                                 sphero_config["SIMULTANEOUS_SPHEROS"])

        self.resources["mp_array_timestamps"] = mp.Array(ctypes.c_double,
                                                         3 + sphero_config["SIMULTANEOUS_SPHEROS"])

        self.resources["mp_array_packet_counters"] = mp.Array(
            ctypes.c_int32, 3 + sphero_config["SIMULTANEOUS_SPHEROS"])
        self.get_numpy_resources()

    def get_numpy_resources(self):
        np_array_rgb = np.frombuffer(
            self.resources["mp_array_rgb"].get_obj(), dtype=np.uint8)

        self.resources["np_array_rgb"] = np_array_rgb.reshape([
            self.sphero_config["CAMERA_LENGTH_STATE_FULL"],
            self.sphero_config["RGB_HEIGHT_PX"],
            self.sphero_config["RGB_WIDTH_PX"],
            3])

        np_array_depth = np.frombuffer(
            self.resources["mp_array_depth"].get_obj(), dtype=np.uint16)
        self.resources["np_array_depth"] = np_array_depth.reshape([
            self.sphero_config["CAMERA_LENGTH_STATE_FULL"],
            self.sphero_config["DEPTH_HEIGHT_PX"],
            self.sphero_config["DEPTH_WIDTH_PX"]])

        np_array_audio = np.frombuffer(self.resources["mp_array_audio"].get_obj(),
                                       dtype=np.float32)
        self.resources["np_array_audio"] = np_array_audio.reshape(
            self.sphero_config["AUDIO_BYTES_PER_STATE"], 1)

        if self.sphero_config["SIMULTANEOUS_SPHEROS"] > 0:
            np_array_sphero_states = np.frombuffer(self.resources["mp_array_sphero_states"].get_obj(),
                                                   dtype=np.float32)
            self.resources["np_array_sphero_states"] = np_array_sphero_states.reshape(
                [self.sphero_config["SIMULTANEOUS_SPHEROS"],
                 self.sphero_config["SPHERO_LENGTH_STATE"],
                 len(self.sphero_config["SPHERO_OUTPUT_VARIABLES"])])

            np_array_sphero_actions = np.frombuffer(self.resources["mp_array_sphero_actions"].get_obj(), dtype=np.int16)
            self.resources["np_array_sphero_actions"] = np_array_sphero_actions.reshape(
                [self.sphero_config["SIMULTANEOUS_SPHEROS"], 3])
            self.resources["np_array_sphero_actions"][:, 2] = 0

            self.resources["np_array_sphero_sleep"] = np.frombuffer(
                self.resources["mp_array_sphero_sleep"].get_obj(), dtype=np.int8)

            np_array_sphero_battery = np.frombuffer(self.resources["mp_array_sphero_battery"].get_obj(),
                                                    dtype=np.float32)
            self.resources["np_array_sphero_battery"] = np_array_sphero_battery.reshape(
                self.sphero_config["SIMULTANEOUS_SPHEROS"])

        np_array_packet_counters = np.frombuffer(
            self.resources["mp_array_packet_counters"].get_obj(),
            dtype=np.int32)
        self.resources["np_array_packet_counters"] = np_array_packet_counters.reshape(
            [3 + self.sphero_config["SIMULTANEOUS_SPHEROS"]])

        np_array_timestamps = np.frombuffer(self.resources["mp_array_timestamps"].get_obj(),
                                            dtype=np.float64)
        self.resources["np_array_timestamps"] = np_array_timestamps.reshape(
            [3 + self.sphero_config["SIMULTANEOUS_SPHEROS"]])
