docker run --net=host --privileged --mount  \
  type=bind,source=/var/run/dbus/system_bus_socket,target=/var/run/dbus/system_bus_socket  \
  --mount type=bind,source=/home/alon/SpheroPyLib/dataset,target=/sphero/dataset -it spheroimage:1.0