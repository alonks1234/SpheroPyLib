import os
import subprocess
import time
import signal
import sys

dataset_dir = sys.argv[1]
if not os.path.exists(dataset_dir):
    os.makedirs(dataset_dir)
num_collected = len(os.listdir(dataset_dir))

process = subprocess.Popen(['python3.8', 'gather_random_dataset_sphero.py'],
                           # stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                           preexec_fn=os.setsid)
start = time.time()
while True:
    time.sleep(1)
    if time.time()-start > 30:
        if num_collected == len(os.listdir(dataset_dir)):
            print("Restarting Lib")
            os.killpg(os.getpgid(process.pid), signal.SIGTERM)
            process = subprocess.Popen(['python3.8', 'gather_random_dataset_sphero.py', dataset_dir],
                                       stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                       preexec_fn=os.setsid)
        else:
            num_collected = len(os.listdir(dataset_dir))
        start = time.time()
