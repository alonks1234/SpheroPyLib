import numpy as np


def run_microphone(shared_resources):
    shared_resources.get_numpy_resources()
    import sounddevice as sd
    import time as pytime

    shared_resources.resources["logging_queue"].put("[run microphone] Running the audio stream")

    # Assign the nice microphone to be default input
    sd.default.device = ['Q9-1', 'default']
    devices = sd.query_devices()
    shared_resources.resources["logging_queue"].put(f"audio devices: {devices}")
    i = 0

    def audio_callback(outdata, frames, time, status, special=None):
        timestamp = pytime.time()

        shared_resources.resources["np_array_audio"][:] = np.insert(
            outdata, 0,
            shared_resources.resources["np_array_audio"][:],
            axis=0)[shared_resources.sphero_config["AUDIO_BYTES_PER_SAMPLE"]:]
        shared_resources.resources["np_array_timestamps"][2] = timestamp
        shared_resources.resources["np_array_packet_counters"][2] += 1

    with sd.InputStream(channels=1,
                        callback=audio_callback,
                        blocksize=shared_resources.sphero_config["AUDIO_BYTES_PER_SAMPLE"],
                        samplerate=shared_resources.sphero_config["AUDIO_BYTES_PER_SECOND"],
                        latency=.01):
        while True:
            pytime.sleep(.001)

