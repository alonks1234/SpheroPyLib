import time


def run_state_machine(shared_resources):
    """
    Function to handle switching server states when connections
    are made or broken, or batteries lose charge, etc.

    Other processes should use library_state to
    conduct business. They should never change it.
    """
    shared_resources.get_numpy_resources()
    while True:
        time.sleep(.001)
        if not shared_resources.resources["state_machine_queue"].empty():
            data = shared_resources.resources["state_machine_queue"].get()
            old_state = shared_resources.resources["library_state"].value

            # Failures no matter what state we are in
            if data in ["AUDIOLOST", "RGBLOST", "DEPTHLOST"]:
                shared_resources.resources["library_state"].value = -1

            # Disconnected
            if shared_resources.resources["library_state"].value == 0:
                if data == "RESETSTATEVARS":
                    shared_resources.resources["library_state"].value = 1

            # Waiting for spheros (all sensors)
            elif shared_resources.resources["library_state"].value == 1:
                if data == "ALLSENSORSGO":
                    shared_resources.resources["library_state"].value = 5

                elif data == "SPHEROLOST":
                    shared_resources.resources["library_state"].value = 0

            # Running action on sphero
            elif shared_resources.resources["library_state"].value == 5:
                if data == "SPHEROLOST":
                    shared_resources.resources["library_state"].value = 0
                elif data == "BATTERIESLOW":
                    shared_resources.resources["library_state"].value = 2

            # Unrecoverable failure state
            elif shared_resources.resources["library_state"].value == -1:
                pass

            # Log State Changes
            if old_state != shared_resources.resources["library_state"].value:
                shared_resources.resources["logging_queue"].put(
                    f"State Machine: Old State={old_state}, "
                    f"New State={shared_resources.resources['library_state'].value}, "
                    f"msg={data}")
