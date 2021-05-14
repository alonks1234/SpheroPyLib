FROM ubuntu:18.04

RUN apt-get update && apt-get install -q -y python3-pip python3.8-dev python3-dbus libdbus-1-dev libdbus-glib-1-dev \
    libcairo2-dev pkg-config libgirepository1.0-dev libusb-1.0 ffmpeg libsm6 libxext6 libportaudio2

RUN apt-get install -q -y bluez bluetooth

RUN python3.8 -m pip install --upgrade pip
RUN python3.8 -m pip install --ignore-installed PyGObject
WORKDIR /sphero/

COPY requirements.txt .
RUN pip3 install -r requirements.txt
COPY SpheroLib/ ./SpheroLib
COPY collector_manager.py .
COPY gather_random_dataset_sphero.py .

