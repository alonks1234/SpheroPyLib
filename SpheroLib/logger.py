import os
import time


def run_logger(shared_resources):
    """
    Log the library comings and goings to a log file
    """
    shared_resources.get_numpy_resources()
    log_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../Logs/"))
    if not os.path.exists(log_dir):
        os.mkdir(log_dir)
    sphero_log_path = f"{log_dir}/Spheros.txt"
    library_log_path = f"{log_dir}/Library.txt"
    sphero_log_file = open(sphero_log_path, "w+")
    library_log_file = open(library_log_path, "w+")
    while True:
        time.sleep(.001)
        message = shared_resources.resources["logging_queue"].get()
        human_time = time.ctime(time.time())
        if message[:7] == "[Sphero":
            sphero_log_file.write("{} | {} \n".format(
                human_time, message))
            sphero_log_file.flush()
        else:
            library_log_file.write("{} | {} \n".format(
                human_time, message))
            library_log_file.flush()
