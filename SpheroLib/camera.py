import pyrealsense2 as rs
import time
import numpy as np
import cv2


def run_camera(shared_resources):
    shared_resources.get_numpy_resources()
    shared_resources.resources["logging_queue"].put("[run camera] Running the camera stream")
    # Configure depth and color streams
    pipeline = rs.pipeline()
    cam_config = rs.config()
    cam_config.enable_stream(
        rs.stream.depth, shared_resources.sphero_config["DEPTH_WIDTH_PX"], shared_resources.sphero_config["DEPTH_HEIGHT_PX"],
        rs.format.z16, shared_resources.sphero_config["CAMERA_FPS"])
    cam_config.enable_stream(
        rs.stream.color, shared_resources.sphero_config["RGB_WIDTH_PX"], shared_resources.sphero_config["RGB_HEIGHT_PX"],
        rs.format.bgr8, shared_resources.sphero_config["CAMERA_FPS"])
    prof = pipeline.start(cam_config)

    s = prof.get_device().query_sensors()[1]
    s.set_option(rs.option.exposure, 350)
    # time.sleep(4)
    frames = pipeline.wait_for_frames()

    try:
        while True:
            time.sleep(.001)
            frames = pipeline.wait_for_frames()
            depth_frame = frames.get_depth_frame()
            color_frame = frames.get_color_frame()
            timestamp = time.time()
            if color_frame:
                color_image = np.asanyarray(color_frame.get_data(),
                                            dtype=np.uint8)
                shared_resources.resources["np_array_timestamps"][0] = timestamp
                shared_resources.resources["np_array_packet_counters"][0] += 1
                with shared_resources.resources["rgbd_pointer_lock"]:
                    shared_resources.resources["np_array_rgb"][shared_resources.resources["rgb_ring_buffer_pointer"].value]\
                        = np.expand_dims(color_image, axis=0)
                    shared_resources.resources["rgb_ring_buffer_pointer"].value = \
                        (shared_resources.resources["rgb_ring_buffer_pointer"].value + 1) % \
                        shared_resources.resources["np_array_rgb"].shape[0]

            if depth_frame:
                depth_image = np.asanyarray(depth_frame.get_data(),
                                            dtype=np.uint16)
                shared_resources.resources["np_array_timestamps"][1] = timestamp
                shared_resources.resources["np_array_packet_counters"][1] += 1
                with shared_resources.resources["rgbd_pointer_lock"]:
                    shared_resources.resources["np_array_depth"][shared_resources.resources["depth_ring_buffer_pointer"].value] \
                        = np.expand_dims(depth_image, axis=0)
                    shared_resources.resources["depth_ring_buffer_pointer"].value = \
                        (shared_resources.resources["depth_ring_buffer_pointer"].value + 1) % \
                        shared_resources.resources["np_array_depth"].shape[0]
    finally:
        pipeline.stop()
