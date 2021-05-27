"""
Things that are user specified
"""
sphero_config = {
    "SIMULTANEOUS_SPHEROS": 2,
    "SPHEROMACS": [
        "DA:E7:C9:C5:81:CD",
        "D1:E3:4B:81:F3:29",
        "E1:91:60:4F:3B:27",
                   ],
    "SPHEROCOLORASSIGNMENTS": [(255, 0, 0),
                               (0, 255, 0),
                               (0, 0, 255),
                               (255, 255, 255)],
    # Amount of time to maintain past state for.
    "STATE_LEN_TIME_SECS": 2,
    # RGB-D options. Use realsense-viewer to see options
    "RGB_WIDTH_PX": 320,
    "RGB_HEIGHT_PX": 180,
    "DEPTH_WIDTH_PX": 424,
    "DEPTH_HEIGHT_PX": 240,
    "CAMERA_FPS": 30,
    "CAMERA_TARGET_FPS": 6,  # This must be a divisor of CAMERA_FPS
    # Audio options. Some of these are determined by audio hardware
    "AUDIO_BYTES_PER_SECOND": 48000,
    "AUDIO_SECS_PER_SAMPLE": .05,
    "AUDIO_CHANNELS": 1,

    # If spheros are below this voltage, sleep and notify slack
    "SPHERO_LOW_VOLTAGE": 3.75,

    # If spheros are above this voltage (and off the charger), run library
    "SPHERO_CHARGED_VOLTAGE": 3.75,

    # Security risk. Slack token for publishing charging info to #sphero_slack.
    "SLACKTOKEN": "hello-world",

    # DONT TOUCH THESE
    "SPHERO_SENSOR_RATE": 9,  # hz, Estimate from inspection

    "SPHERO_OUTPUT_VARIABLES": [
        'positionX', 'positionY',
        'velocityX', 'velocityY',
        'roll', 'pitch', 'yaw',
        'wx', 'wy', 'wz',
        'ax', 'ay', 'az'],

}

sphero_config["CAMERA_LENGTH_STATE_FULL"] = int(sphero_config["STATE_LEN_TIME_SECS"] * sphero_config["CAMERA_FPS"])
sphero_config["CAMERA_LENGTH_STATE"] = int(sphero_config["STATE_LEN_TIME_SECS"] * sphero_config["CAMERA_TARGET_FPS"])
sphero_config["CAMERA_OUTPUT_SKIP"] = int(sphero_config["CAMERA_FPS"] / sphero_config["CAMERA_TARGET_FPS"])
sphero_config["AUDIO_STATE_SECS"] = sphero_config["STATE_LEN_TIME_SECS"]
sphero_config["AUDIO_BYTES_PER_SAMPLE"] = int(
    sphero_config["AUDIO_BYTES_PER_SECOND"] * sphero_config["AUDIO_SECS_PER_SAMPLE"])
sphero_config["AUDIO_LENGTH_STATE"] = int(sphero_config["AUDIO_STATE_SECS"] / sphero_config["AUDIO_SECS_PER_SAMPLE"])
sphero_config["AUDIO_BYTES_PER_STATE"] = int(
    sphero_config["AUDIO_BYTES_PER_SECOND"] * sphero_config["AUDIO_STATE_SECS"])
sphero_config["SPHERO_LENGTH_STATE"] = int(sphero_config["STATE_LEN_TIME_SECS"] * sphero_config["SPHERO_SENSOR_RATE"])
