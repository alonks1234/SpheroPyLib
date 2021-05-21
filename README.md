# Sphero Bolt Python Library

## Compute requirements
This should work on Linux 16.04, 18.04, and 20.04. This was tested on 18.04 and 20.04. The docker image 
pulls from an 18.04 base image.

## Configure bluetooth on host machine
On host OS, run  
`sudo apt-get install blueman`  
`reboot`  

Now, open blueman. This should be an option on the top right of the menu bar. 
For each device SB-XXXX (Sphero Bolts) click "add" and then 
"proceed without pairing". Once each device is "known" to the your host machine
in this way, your computer should remember the Bolts as "friendlies" forever. 

## Plug in peripherals
Plug the realsense and Q9-1 Microphone into host usb ports. 
The microphone can use usb2.0, but the realsense needs usb3.0.

## Build the docker image
`docker build -t spheroimage:1.0 .`

## Make a dataset directory
`mkdir dataset`

## Run the docker container
`docker run --net=host --privileged --mount type=bind,source=/var/run/dbus/system_bus_socket,target=/var/run/dbus/system_bus_socket  --mount type=bind,source=/<path_to_lib>/SpheroPyLib/dataset,target=/sphero/dataset -it spheroimage:1.0`

## Populate the dataset
`python3.8 collector_manager.py dataset`  
This script will add data to the "dataset" folder up to a certain number of samples, specified
in "gather_random_dataset_sphero.py"

## Sphero Configuration
In SpheroLib/config is the configuration of the envrironment.
```
sphero_config = {
    "SIMULTANEOUS_SPHEROS": 1,
    "SPHEROMACS": [
        "D1:E3:4B:81:F3:29",
        "DA:E7:C9:C5:81:CD",
        "E1:91:60:4F:3B:27",
        "E1:91:60:4F:3B:27", 
                   ],
    "SPHEROCOLORASSIGNMENTS": [(255, 0, 0),
                               (0, 255, 0),
                               (0, 0, 255),
                               (255, 255, 255)],
    # Amount of time to maintain past state for.
    "STATE_LEN_TIME_SECS": 2,
    ...
```
The library supports multirobot setups, although the current dataset collection script is just commanding one.
When a Sphero dies, switch the order of the MAC addresses to use a different one (the library uses
the topmost MAC address/s)

## Docker Bugs
The library seems to not shutdown correctly from a ctrl + c from docker. Some processes,
including the ones controlling the robot, get orphaned. I'm sure this is a trivial fix.


## Common Errors:
###"ValueError: No input device matching 'Q9-1'"###
The microphone is not being recognized by the computer. Try rebooting and unplugging.
On your host machine, you should be able to open a python script and run:  
`import sounddevice as sd`  
`print (sd.query_devices())`

and see an entry for:  
`X Q9-1: USB Audio (hw:1,0), ALSA (1 in, 0 out)`

If not, keep rebooting. Glhf.

### Camera not connected
```Traceback (most recent call last):
  File "/usr/lib/python3.8/multiprocessing/process.py", line 313, in _bootstrap
    self.run()
  File "/usr/lib/python3.8/multiprocessing/process.py", line 108, in run
    self._target(*self._args, **self._kwargs)
  File "/sphero/SpheroLib/camera.py", line 19, in run_camera
    prof = pipeline.start(cam_config)
RuntimeError: Couldn't resolve requests
```
To fix this, on your host machine open up the realsense-viewer and ensure that the camera is visible (and that
the connection says usb 3.X, not 2.X).

###### Bluetooth Connectivity Error
```
Traceback (most recent call last):
  File "/usr/local/lib/python3.8/dist-packages/gatt/gatt_linux.py", line 293, in _connect
    self._object.Connect()
  File "/usr/local/lib/python3.8/dist-packages/dbus/proxies.py", line 72, in __call__
    return self._proxy_method(*args, **keywords)
  File "/usr/local/lib/python3.8/dist-packages/dbus/proxies.py", line 141, in __call__
    return self._connection.call_blocking(self._named_service,
  File "/usr/local/lib/python3.8/dist-packages/dbus/connection.py", line 652, in call_blocking
    reply_message = self.send_message_with_reply_and_block(
dbus.exceptions.DBusException: org.bluez.Error.Failed: Input/output error

During handling of the above exception, another exception occurred:

Traceback (most recent call last):
  File "/usr/lib/python3.8/multiprocessing/process.py", line 313, in _bootstrap
    self.run()
  File "/usr/lib/python3.8/multiprocessing/process.py", line 108, in run
    self._target(*self._args, **self._kwargs)
  File "/sphero/SpheroLib/sphero_bluetooth.py", line 22, in run_sphero
    device.connect()
  File "/usr/local/lib/python3.8/dist-packages/gatt/gatt_linux.py", line 288, in connect
    self._connect()
  File "/usr/local/lib/python3.8/dist-packages/gatt/gatt_linux.py", line 312, in _connect
    self.connect_failed(_error_from_dbus_error(e))
  File "/sphero/SpheroLib/sphero_bluetooth.py", line 110, in connect_failed
    self.log("[%s] Connection failed: %s" % (str(error)))
TypeError: not enough arguments for format string
```
This one is likely either:
* Bluetooth is not on on your host machine.
* You can't see the spheros. Pull up the bluetooth devices on your host machine.
Do you see each "SB-XXXX" device?
* You have not opened blueman and added each device. Or you need to try doing that a few more times.
I have not been thrilled with the linux bluetooth stack.

