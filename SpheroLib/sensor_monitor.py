import time


def run_sensor_monitor(shared_resources):
    """
    When Library is starting up/resetting, indicates when all sensors are online.
    While running, triggers state machine if we haven't gotten sensor data recently.
    """
    shared_resources.get_numpy_resources()
    while True:
        time.sleep(.001)
        if shared_resources.resources["library_state"].value == 0:
            for i in range(3 + shared_resources.sphero_config["SIMULTANEOUS_SPHEROS"]):
                shared_resources.resources["np_array_timestamps"][i] = 0
                shared_resources.resources["np_array_packet_counters"][i] = 0

            shared_resources.resources["state_machine_queue"].put("RESETSTATEVARS")
            reset_state_time = time.time()
            published_waiting = False
            time.sleep(.5)

        if shared_resources.resources["library_state"].value == 1:

            if time.time() - reset_state_time > 20 + shared_resources.sphero_config["STATE_LEN_TIME_SECS"] and not published_waiting:
                shared_resources.resources["logging_queue"].put(
                    f"We are waiting on sensors: {shared_resources.resources['np_array_packet_counters']}")
                published_waiting = True

            sensors_connected = True
            # RGB IS GO
            if shared_resources.resources["np_array_packet_counters"][0] < \
                    shared_resources.sphero_config["CAMERA_LENGTH_STATE"]:
                sensors_connected = False
            # DEPTH IS GO
            if shared_resources.resources["np_array_packet_counters"][1] < \
                    shared_resources.sphero_config["CAMERA_LENGTH_STATE"]:
                sensors_connected = False
            # AUDIO IS GO
            if shared_resources.resources["np_array_packet_counters"][2] < \
                    shared_resources.sphero_config["AUDIO_LENGTH_STATE"]:
                sensors_connected = False
            # SPHEROS ARE GO
            for sphero_elt in range(shared_resources.sphero_config["SIMULTANEOUS_SPHEROS"]):
                if shared_resources.resources["np_array_packet_counters"][3 + sphero_elt] < \
                        shared_resources.sphero_config["SPHERO_LENGTH_STATE"]:
                    sensors_connected = False
            # LETS GO!
            if sensors_connected:
                shared_resources.resources["state_machine_queue"].put("ALLSENSORSGO")
                time.sleep(.5)

        if shared_resources.resources["library_state"].value == 5:
            for elt, timestamp in enumerate(shared_resources.resources["np_array_timestamps"]):
                if time.time() - timestamp > 2:
                    if elt == 0:
                        shared_resources.resources["state_machine_queue"].put("RGBLOST")
                    elif elt == 1:
                        shared_resources.resources["state_machine_queue"].put("DEPTHLOST")
                    elif elt == 2:
                        shared_resources.resources["state_machine_queue"].put("AUDIOLOST")
                    else:
                        shared_resources.resources["logging_queue"].put(
                            "[Sensor Monitor] Lost Sphero {}".format(elt - 3))
                        shared_resources.resources["state_machine_queue"].put("SPHEROLOST")
            time.sleep(1)