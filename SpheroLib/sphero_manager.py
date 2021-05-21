from SpheroLib.sphero_bluetooth import run_sphero
import multiprocessing as mp
import time
# from slackclient import SlackClient
import subprocess


class SpheroManager:
    def __init__(self, shared_resources):
        """
        Spin up the sphero processes. Monitor them for good health. If they die, restart them. TODO: Alert State Machine
        """
        shared_resources.get_numpy_resources()
        self.shared_resources = shared_resources
        self.process_data = {sphero_num: {"pid": None, "proc": None, "kill_switch": None, "reboot_status": None} for \
                             sphero_num in range(shared_resources.sphero_config["SIMULTANEOUS_SPHEROS"])}
        [self.start_sphero_process(sphero_num) for sphero_num in
         range(shared_resources.sphero_config["SIMULTANEOUS_SPHEROS"])]
        self.monitor_sphero_processes()

    def start_sphero_process(self, sphero_num):
        self.shared_resources.resources["logging_queue"].put_nowait(
            f"[Sphero Manager] Starting sphero {sphero_num} process.")
        kill_switch = mp.Value('i')
        kill_switch.value = 0
        sphero_proc = mp.Process(target=run_sphero, args=(self.shared_resources, sphero_num, kill_switch))
        # print (sphero_proc.daemon)
        sphero_proc.daemon = True
        sphero_proc.start()
        self.process_data[sphero_num]["pid"] = sphero_proc.pid
        self.process_data[sphero_num]["proc"] = sphero_proc
        self.process_data[sphero_num]["kill_switch"] = kill_switch
        self.process_data[sphero_num]["reboot_status"] = "ongoing"

    def monitor_sphero_processes(self):
        """
        If a sphero process goes down, restart it.
        """
        while True:
            time.sleep(.001)
            for sphero_num in self.process_data.keys():
                if self.process_data[sphero_num]["kill_switch"].value == 2:  # Low Battery
                    if self.process_data[sphero_num]["reboot_status"] == "stopped":
                        continue
                    self.shared_resources.resources["logging_queue"].put_nowait(
                        f"[Sphero Manager] sphero{sphero_num} is low on charge. Alerting slack.")
                    self.process_data[sphero_num]["proc"].terminate()
                    # slackclient = SlackClient(self.shared_resources.sphero_config["SLACKTOKEN"])
                    # slackclient.api_call("chat.postMessage", channel="sphero_slack",
                    #                      text=f"Sphero {sphero_num} low battery. "
                    #                           f"Volts= {self.shared_resources.resources['np_array_sphero_battery']}")
                    self.process_data[sphero_num]["reboot_status"] = "stopped"
                elif self.process_data[sphero_num]["kill_switch"].value == 1:  # Kill Switch
                    self.shared_resources.resources["logging_queue"].put_nowait(
                        f"[Sphero Manager] sphero{sphero_num} process has pulled kill switch")
                    self.process_data[sphero_num]["proc"].terminate()
                    while self.process_data[sphero_num]["proc"].exitcode is None:
                        time.sleep(.01)
                    self.process_data[sphero_num]["proc"].join()
                    self.start_sphero_process(sphero_num)

                elif not self.process_data[sphero_num]["proc"].is_alive():
                    self.shared_resources.resources["logging_queue"].put_nowait(
                        f"[Sphero Manager] sphero{sphero_num} process has died")
                    self.process_data[sphero_num]["proc"].join()
                    print(self.process_data[sphero_num])
                    time.sleep(30)
                    self.start_sphero_process(sphero_num)
