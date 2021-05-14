import struct
from SpheroLib.bluetooth_constants import *
import time
import threading
import numpy as np
import os
import multiprocessing as mp
import gatt
"""
References:
JS Library: https://github.com/Tineyo/BoltAPP/
GATT bluetooth library https://github.com/getsenic/gatt-python
Alternative Python Lib https://github.com/EnotYoyo/pysphero
"""


def run_sphero(shared_resources, sphero_num, kill_switch):
	shared_resources.get_numpy_resources()
	manager = gatt.DeviceManager(adapter_name="hci0")
	mac_address = shared_resources.sphero_config["SPHEROMACS"][sphero_num]
	device = SpheroDevice(shared_resources, mac_address, manager, sphero_num, kill_switch)
	device.connect()
	manager.run()


class SpheroDevice(gatt.Device):
	def __init__(self, shared_resources, mac_address, manager, sphero_num, kill_switch):
		super().__init__(mac_address=mac_address, manager=manager)
		self.kill_switch = kill_switch
		self.sphero_num = sphero_num
		self.shared_resources = shared_resources
		self.status_dict = {"connected": True, "resolved": False, "notifications_enabled": True,
							"state": "init", "voltage": None, "last_battery_time": None}
		self.bluetooth_resources = {"command_queue": [], "prev_update_value": None, "active_commands": mp.Value("i"),
									"characs_dict": {}, "seqNumber": 0}
		self.log(f"Init sphero device {os.getpid()}")
		threading.Timer(1, self.heartbeat, args=("start",)).start()

	def log(self, message):
		message = f"[Sphero {self.sphero_num}] {message}"
		self.shared_resources.resources["logging_queue"].put(message)

	def heartbeat(self, tag):
		if tag == "start":
			if self.status_dict["connected"] and self.status_dict["resolved"] and \
					self.status_dict["notifications_enabled"]:
				self.log("[Heartbeat] We are connected correctly")
				self.init_characs()
				self.log("[Heartbeat] Init Characs")
				self.set_up_sphero()
				self.log("[Heartbeat] Set Up Sphero")
				self.wake_sphero()
				self.log("[Heartbeat] Sent Wake Signal")
				threading.Timer(1, self.heartbeat, args=("wake",)).start()
			else:
				self.log(f"[Heartbeat] Connection failure {self.status_dict}")
				self.signal_restart()
		elif tag == "wake":
			if self.status_dict["state"] == "awake":
				self.configure_sphero()
				threading.Timer(1, self.heartbeat, args=("voltage",)).start()
			else:
				self.log(f"[Heartbeat] Sphero did not wake up")
				self.signal_restart()
		elif tag == "voltage":
			if self.status_dict["voltage"] is not None:
				self.configure_sensor_stream()
				threading.Timer(1, self.heartbeat, args=("sensor",)).start()
			else:
				self.log(f"[Heartbeat] Sphero failed to get voltage")
				self.signal_restart()
		elif tag == "sensor":
			if time.time() - self.shared_resources.resources["np_array_timestamps"][3 + self.sphero_num] < .5:
				self.log(f"[Heartbeat] Entering Running State")
				self.status_dict["state"] = "running"
				threading.Timer(1, self.heartbeat, args=("beat",)).start()
			else:
				self.log(f"[Heartbeat] Sphero failed to start sensor stream")
				self.signal_restart()
		elif tag == "beat":
			if time.time() - self.shared_resources.resources["np_array_timestamps"][3 + self.sphero_num] > .5:
				self.log(f"[Heartbeat] Sphero lost sensor stream")
				self.signal_restart()
			if self.status_dict["voltage"] < self.shared_resources.sphero_config["SPHERO_LOW_VOLTAGE"]:
				self.log(f"[Heartbeat] Sphero battery low: {self.status_dict['voltage']}")
				self.signal_battery_low()
			else:
				if time.time() - self.status_dict["last_battery_time"] > 10:
					# self.get_battery_update()
					pass #TODO TURN BATTERY BACK ON
				threading.Timer(1, self.heartbeat, args=("beat",)).start()

	def signal_restart(self):
		self.kill_switch.value = 1
		self.disconnect()
		while True:
			time.sleep(1)

	def signal_battery_low(self):
		self.kill_switch.value = 2
		self.disconnect()
		while True:
			time.sleep(1)

	def connect_succeeded(self):
		super().connect_succeeded()

	def connect_failed(self, error):
		self.status_dict["connected"] = False
		self.log("[%s] Connection failed: %s" % (str(error)))
		super().connect_failed(error)

	def services_resolved(self):
		self.status_dict["resolved"] = True
		super().services_resolved()

	def characteristic_enable_notifications_succeeded(self, characteristic):
		self.status_dict["notifications_enabled"] = True

	def characteristic_enable_notifications_failed(self, characteristic, error):
		self.log("enable failed {} error: {}".format(characteristic.uuid, error))
		self.status_dict["notifications_enabled"] = False

	def characteristic_value_updated(self, characteristic, value):
		"""
		Called by the bluetooth library. Indicates a value we are
		subscribed to on the device (like a sensor) has changed.

		We seem to be getting duplicate messages. Ignore a value
		change if it is identical to one just recieved.

		Begin logic for figuring out what changed otherwise.
		"""
		if value == self.bluetooth_resources["prev_update_value"]:
			return
		self.bluetooth_resources["prev_update_value"] = value
		self.on_value_change(value)

	def characteristic_write_value_succeeded(self, characteristic):
		"""
		If there are more things on the queue to do, call them.
		Otherwise indicate that there are no active outgoing messages
		"""
		self.bluetooth_resources["active_commands"].value -= 1
		if self.bluetooth_resources["command_queue"]:
			(characteristic_uuid, command) = self.bluetooth_resources["command_queue"].pop(0)
			self.write_value(characteristic_uuid, command)

	def write_value(self, charac, value):
		"""
		Write a value to sphero characteristic
		"""
		self.bluetooth_resources["active_commands"].value += 1
		self.bluetooth_resources["characs_dict"][charac].write_value(value)

	def enqueue_command(self, q_command):
		"""
		If there are already 1+ commands on the queue, simply add. When
		the next message comes back, it will call the next one.
		If there are 0 and no active message, write command ourselves.
		"""
		if self.bluetooth_resources["active_commands"].value == 0:
			self.write_value(q_command[0], q_command[1])
		else:
			self.bluetooth_resources["command_queue"].append(q_command)

	def characteristic_write_value_failed(self, characteristic, error):
		"""
		Called by the bluetooth library.
		"""
		self.bluetooth_resources["active_commands"].value -= 1
		error = str(error)
		self.log(f"[Write Val Failed] {error}")

	def init_characs(self):
		"""
		Setup some services, called once on startup.
		Returns bool indicating success
		"""
		for service in self.services:
			for characteristic in service.characteristics:
				self.bluetooth_resources["characs_dict"][characteristic.uuid] = characteristic

		# Fail if we are missing the API characteristic
		if APIV2_CHARACTERISTIC not in self.bluetooth_resources["characs_dict"].keys():
			self.log("[Init Characs] The API characteristic is not found. You probably hit that button.")
			self.signal_restart()

		# Enable notifications for characteristic callbacks,
		# for characteristics I know allow notification
		for uuid, characteristic in self.bluetooth_resources["characs_dict"].items():
			if uuid in NOTIFICATION_CHARACTERISTICS:
				characteristic.enable_notifications()

	def set_up_sphero(self):
		"""
		Function called when sphero is connected.
		There is a magical force command. I am not sure what it does. The JS library had it, so I have it. It seems
		necessary.
		Finally, try to wake the sphero.
		"""
		self.write_value(ANTIDOS_CHARACTERISTIC, useTheForce)
		self.reset_incoming_buffer()

	def on_wakeup(self):
		"""
		Called when sphero is confirmed to have woken up. Turn on sensor stream. Start running actions.
		"""
		self.log("[On Wakeup] Sphero is awake")
		self.status_dict["state"] = "awake"

	def configure_sphero(self):
		"""
		Called after sphero is awake. Configure sensor stream, battery, and more.
		"""
		self.get_battery_update()
		self.set_front_back_leds(front=[255, 255, 255], back=[0, 0, 0])
		# self.set_front_back_leds(front=[0, 0, 0], back=[0, 0, 0])
		self.color_matrix(self.shared_resources.sphero_config["SPHEROCOLORASSIGNMENTS"][self.sphero_num])
		self.reset_yaw()
		self.reset_locator()
		self.reset_incoming_buffer()
		self.unset_stabilization()

	def wake_sphero(self):
		"""
		Create a command to wake up the sphero and fire it off.
		"""
		q_command = (APIV2_CHARACTERISTIC, self.create_command(
			deviceId=DeviceId["powerInfo"],
			commandId=PowerCommandIds["wake"]))
		self.enqueue_command(q_command)

	def run_action(self):
		"""
		Called once to get things started, then called again each time
		a write value to the sphero succeeds.

		Run function to get and issue roll commands
		Every second, run battery voltage and charging function
		"""
		if self.shared_resources.resources["np_array_sphero_actions"][self.sphero_num][2] == 1:
			# New action is available.
			desired_heading = int(self.shared_resources.resources["np_array_sphero_actions"][self.sphero_num][0])
			desired_speed = int(self.shared_resources.resources["np_array_sphero_actions"][self.sphero_num][1])
			# These are special characters and you cannot use them :)
			if desired_heading in [141, 171, 216]:
				desired_heading += 1
			if desired_speed in [141, 171, 216]:
				desired_speed += 1

			# With reset Yaw
			self.shared_resources.resources["np_array_sphero_actions"][self.sphero_num][2] = 2
			self.reset_yaw()
			threading.Timer(.01, self.check_yaw_reset, args=(desired_speed, desired_heading)).start()

			# Without reset yaw
			# self.shared_resources.resources["np_array_sphero_actions"][self.sphero_num][2] = 4
			# self.roll(desired_speed, desired_heading)
			# threading.Timer(.01, self.check_action, args=(desired_speed, desired_heading)).start()
		else:
			# No new action is available
			return

	def check_yaw_reset(self, desired_speed, desired_heading):
		if self.shared_resources.resources["np_array_sphero_actions"][self.sphero_num][2] not in [3, 2]:
			return

		start = time.time()
		while time.time() - start < .2:
			if self.shared_resources.resources["np_array_sphero_actions"][self.sphero_num][2] == 3:
				self.shared_resources.resources["np_array_sphero_actions"][self.sphero_num][2] = 4
				self.roll(desired_speed, desired_heading)
				threading.Timer(.01, self.check_action, args=(desired_speed, desired_heading)).start()
				return
		self.reset_yaw()
		threading.Timer(.01, self.check_yaw_reset, args=(desired_speed, desired_heading)).start()

	def check_action(self, desired_speed, desired_heading):
		if self.shared_resources.resources["np_array_sphero_actions"][self.sphero_num][2] not in [4, 5]:
			return
		start = time.time()
		while time.time() - start < .2:
			if self.shared_resources.resources["np_array_sphero_actions"][self.sphero_num][2] == 5:
				self.shared_resources.resources["np_array_sphero_actions"][self.sphero_num][2] = 0
				return
		self.roll(desired_speed, desired_heading)
		threading.Timer(.01, self.check_action, args=(desired_speed, desired_heading)).start()

	def on_reset_yaw(self):
		if self.shared_resources.resources["np_array_sphero_actions"][self.sphero_num][2] == 2:
			self.shared_resources.resources["np_array_sphero_actions"][self.sphero_num][2] = 3

	def on_roll(self):
		if self.shared_resources.resources["np_array_sphero_actions"][self.sphero_num][2] == 4:
			self.shared_resources.resources["np_array_sphero_actions"][self.sphero_num][2] = 5

	def roll(self, speed, heading):
		"""
		Roll sphero at desired heading and speed.
		Speed from 0-255, heading is relative angle from 0 to 360
	
		Sphero asks for an absolute heading angle, so we reset the yaw
		angle before applying the command.
		
		data is [speed, 2 bytes heading, direction (0-forward, 1-back)]
		"""
		q_command = (APIV2_CHARACTERISTIC, self.create_command(
			deviceId=DeviceId["driving"],
			commandId=DrivingCommandIds["driveWithHeading"],
			targetId=0x012,
			data=[speed, (heading >> 8) & 0xff, heading & 0xff, 0]))
		self.enqueue_command(q_command)

	def reset_yaw(self):
		"""
		Create command to reset the sphero yaw
		"""
		q_command = (APIV2_CHARACTERISTIC, self.create_command(
			deviceId=DeviceId["driving"],
			commandId=DrivingCommandIds["resetYaw"],
			targetId=0x012))
		self.enqueue_command(q_command)

	def color_matrix(self, rgb):
		"""
		Create a command to change the sphero led color to an rgb list
		(255, 255, 255)
		"""
		q_command = (APIV2_CHARACTERISTIC, self.create_command(
			deviceId=DeviceId["userIO"],
			commandId=UserIOCommandIds["matrixColor"],
			targetId=0x012,
			data=rgb))
		self.enqueue_command(q_command)

	def set_front_back_leds(self, front, back):
		"""
		Set front and back leds to a specific colors
		"""
		q_command = (APIV2_CHARACTERISTIC, self.create_command(
			deviceId=DeviceId["userIO"],
			commandId=UserIOCommandIds["allLEDs"],
			data=[0x3f, *front, *back]))
		self.enqueue_command(q_command)

	def unset_stabilization(self):
		q_command = (APIV2_CHARACTERISTIC, self.create_command(
			deviceId=DeviceId["driving"],
			commandId=DrivingCommandIds["stabilization"],
			targetId=0x012,
			data=[0x05]))
		self.enqueue_command(q_command)

	def reset_locator(self):
		"""
		Create command to reset the sphero locator
		"""
		q_command = (APIV2_CHARACTERISTIC, self.create_command(
			deviceId=DeviceId["sensor"],
			commandId=SensorCommandIds["resetLocator"],
			targetId=0x012))
		self.enqueue_command(q_command)

	def reset_incoming_buffer(self):
		"""
		Called with we realize a packet we are reading is fubar.
		Reset the buffer so we can try again.
		"""
		self.packet = []
		self.escaped = False

	def get_battery_update(self):
		"""
		Ask sphero for battery voltage and charging status
		"""
		q_command = (APIV2_CHARACTERISTIC, self.create_command(
			deviceId=DeviceId["powerInfo"],
			commandId=PowerCommandIds["batteryVoltage"]))
		self.enqueue_command(q_command)

		q_command = (APIV2_CHARACTERISTIC, self.create_command(
			deviceId=DeviceId["powerInfo"],
			commandId=PowerCommandIds["charging"]))
		self.enqueue_command(q_command)

	def configure_sensor_stream(self):
		"""
		Create and pass a message to sphero telling her
		we want sensor values passed to us as they update.

		There are 2 magic numbers here I just got from inspection of the
		JS library.
		"""
		mask = [SensorMaskValues["accelerometer"],
				SensorMaskValues["orientation"],
				SensorMaskValues["locator"],
				SensorMaskValues["gyro"]]
		interval = 100
		aol_num = 516216
		gyro_num = 58720256

		# This command activates the accelerometer, orientation, locator
		q_command = (APIV2_CHARACTERISTIC, self.create_command(
			deviceId=DeviceId["sensor"],
			commandId=SensorCommandIds["sensorMask"],
			targetId=0x012,
			data=[(interval >> 8) & 0xff,
				  interval & 0xff,
				  0,
				  (aol_num >> 24) & 0xff,
				  (aol_num >> 16) & 0xff,
				  (aol_num >> 8) & 0xff,
				  aol_num & 0xff]))
		self.enqueue_command(q_command)

		# This command activates the gyroscope
		q_command = (APIV2_CHARACTERISTIC, self.create_command(
			deviceId=DeviceId["sensor"],
			commandId=SensorCommandIds["sensorMaskExtended"],
			targetId=0x012,
			data=[(gyro_num >> 24) & 0xff,
				  (gyro_num >> 16) & 0xff,
				  (gyro_num >> 8) & 0xff,
				  gyro_num & 0xff]))
		self.enqueue_command(q_command)

	def create_command(self, deviceId, commandId, targetId=None, data=None):
		"""
		Generate databytes of command using input dictionary
		This protocol copied completely from JS library

		Messages are represented as:
		[start flags targetID sourceID deviceID commandID seqNum data
		checksum end]

		The flags byte indicates which fields are populated.

		The checksum is the ~sum(message[1:-2]) | 0xff.
		"""
		self.bluetooth_resources["seqNumber"] = (self.bluetooth_resources["seqNumber"] + 1) % 255
		running_sum = 0
		command = []
		command.append(APIConstants["startOfPacket"])
		if targetId is None:
			cmdflg = Flags["requestsResponse"] | \
					 Flags["resetsInactivityTimeout"] | 0
			command.append(cmdflg)
			running_sum += cmdflg
		else:
			cmdflg = Flags["requestsResponse"] | \
					 Flags["resetsInactivityTimeout"] | targetId
			command.append(cmdflg)
			running_sum += cmdflg
			command.append(targetId)
			running_sum += targetId

		command.append(deviceId)
		running_sum += deviceId
		command.append(commandId)
		running_sum += commandId
		command.append(self.bluetooth_resources["seqNumber"])
		running_sum += self.bluetooth_resources["seqNumber"]

		if data is not None:
			for datum in data:
				command.append(datum)
				running_sum += datum
		checksum = (~running_sum) & 0xff
		command.append(checksum)
		command.append(APIConstants["endOfPacket"])
		return command

	def on_value_change(self, value):
		"""
		Read bluetooth characteristic value that changed. 

		We get fragments of packets, so a running buffer 
		must be kept. When a complete fragment is recovered 
		(with correct checksum), call decode() to interpret it.

		Be on the lookout for "escape characters". My understanding
		is that if a data-byte is 171 (escape byte), the following byte
		will be a reserved byte represented as ordinary data. *Or* this
		next byte with escape mask to get the actual byte. This masked
		byte is the one the checksum is calculated for.

		I'm not entirely sure what happens if the number 171 is needed
		as a regular data-byte, but as of right now checksums are always
		passing and my "no escaped char..." message is not coming through.
		Will take another look if it does happen.

		Sorry for the long docstring, this took almost a week to work out
		and it would be a shame to loose this info.
		"""
		for val in value:
			if val == APIConstants["startOfPacket"]:
				self.reset_incoming_buffer()
				self.packet.append(val)

			elif val == APIConstants["endOfPacket"]:
				if len(self.packet) < 6:
					self.log("[on value change] packet too small")
					continue

				self.packet.append(val)

				total = sum(self.packet[1:-2])
				if (~total & 0xff) != self.packet[-2]:
					# self.log (self.packet)
					# self.log ("Bad checksum : {}".format(
					#     (~total & 0xff)))
					continue

				self.decode(self.packet)

			elif val == APIConstants["escape"]:
				self.escaped = True

			elif val == APIConstants["escapedEscape"]:
				if self.escaped:
					val = val | APIConstants["escapeMask"]
					self.escaped = False
				self.packet.append(val)

			elif val == APIConstants["escapedStartOfPacket"]:
				if self.escaped:
					val = val | APIConstants["escapeMask"]
					self.escaped = False
				self.packet.append(val)
			elif val == APIConstants["escapedEndOfPacket"]:
				if self.escaped:
					val = val | APIConstants["escapeMask"]
					self.escaped = False
				self.packet.append(val)
			else:
				if self.escaped:
					self.log("no escaped char ....{}".format(val))
				else:
					self.packet.append(val)

	def decode(self, packet):
		"""
		Break raw message up into a dictionary with relevant fields.
		Pass message on to read_command to pass to a message handler
		"""
		command = dict()
		command["packet"] = packet.copy()
		command["startOfPacket"] = packet.pop(0)
		command["flags"] = self.decode_flags(packet.pop(0))

		if command["flags"]["hasTargetId"]:
			command["targetId"] = packet.pop(0)

		if command["flags"]["hasSourceId"]:
			command["sourceId"] = packet.pop(0)

		command["deviceId"] = packet.pop(0)
		command["commandId"] = packet.pop(0)
		command["seqNumber"] = packet.pop(0)

		command["data"] = []
		for i in range(len(packet) - 2):
			command["data"].append(packet.pop(0))

		command["checksum"] = packet.pop(0)
		command["endOfPacket"] = packet.pop(0)
		self.read_command(command)

	def decode_flags(self, flags):
		"""
		Determine appropriate message flags from the flag byte
		"""
		isResponse = flags & Flags["isResponse"]
		requestsResponse = flags & Flags["requestsResponse"]
		requestOnlyErrorResponse = flags & Flags["requestsOnlyErrorResponse"]
		resetsInactivityTimeout = flags & Flags["resetsInactivityTimeout"]
		hasTargetId = flags & Flags["commandHasTargetId"]
		hasSourceId = flags & Flags["commandHasSourceId"]

		return {"isResponse": isResponse,
				"requestsResponse": requestsResponse,
				"requestOnlyErrorResponse": requestOnlyErrorResponse,
				"resetsInactivityTimeout": resetsInactivityTimeout,
				"hasTargetId": hasTargetId,
				"hasSourceId": hasSourceId}

	def read_command(self, command):
		"""
		Determine appropriate handler for message and call it.
		"""
		# Power commands
		if command["deviceId"] == DeviceId["powerInfo"]:
			if command["commandId"] == PowerCommandIds["charging"]:
				if len(command["data"]) <= 1:
					pass
				elif command["data"][1] == BatteryState["charging"]:
					pass
				elif command["data"][1] == BatteryState["notCharging"]:
					pass
				elif command["data"][1] == BatteryState["charged"]:
					pass
				else:
					self.log("Unknown Battery State")

			elif command["commandId"] == PowerCommandIds["batteryVoltage"]:
				volts = int.from_bytes(command["data"], "big") / 100
				self.status_dict["voltage"] = volts
				self.status_dict["last_battery_time"] = time.time()
				self.shared_resources.resources["np_array_sphero_battery"][self.sphero_num] = self.status_dict[
					"voltage"]
			elif command["commandId"] == PowerCommandIds["willSleepAsync"]:
				self.log("[read command] Sphero willSleepAsync do to inactivity")
			elif command["commandId"] == PowerCommandIds["sleepAsync"]:
				self.log("[read command] Sphero sleepAsync")
			elif command["commandId"] == PowerCommandIds["wake"]:
				self.on_wakeup()
			elif command["commandId"] == PowerCommandIds["unknownWake"]:
				self.log("[read command] Sphero Unknown Wake")
			elif command["commandId"] == PowerCommandIds["sleep"]:
				self.log("[read command] Sphero sleep")
			else:
				self.log("unknown event a, {}".format(command))

		# Sensor commands
		elif command["deviceId"] == DeviceId["sensor"]:
			if command["commandId"] == SensorCommandIds["collisionDetectedAsync"]:
				self.log("[read command] Collision Detected")
			elif command["commandId"] == SensorCommandIds["sensorResponse"]:
				self.handle_sensor_update(command)
				# Trigger running actions off of the sensor stream
				if self.status_dict["state"] == "running":
					self.run_action()
			elif command["commandId"] == SensorCommandIds["compassNotify"]:
				self.log("[read command] Compass Notified")
			elif command["commandId"] == SensorCommandIds["resetLocator"]:
				self.log("[read command] Locator reset")
			elif command["commandId"] == SensorCommandIds["sensorMask"]:
				self.log("[read command] SensorMask Set")
			elif command["commandId"] == SensorCommandIds["sensorMaskExtended"]:
				self.log("[read command] SensorMask Extended Set")
			else:
				self.log("unknown event b")

		# Driving commands
		elif command["deviceId"] == DeviceId["driving"]:
			if command["commandId"] == DrivingCommandIds["driveWithHeading"]:
				self.on_roll()
			elif command["commandId"] == DrivingCommandIds["resetYaw"]:
				self.on_reset_yaw()
			elif command["commandId"] == DrivingCommandIds["stabilization"]:
				pass
			else:
				self.log("unknown event c")

		# IO (LED) commands
		elif command["deviceId"] == DeviceId["userIO"]:
			if command["commandId"] == UserIOCommandIds["matrixColor"]:
				self.log("[read command] Matrix Color Set")
			elif command["commandId"] == UserIOCommandIds["allLEDs"]:
				self.log("[read command] Front+Rear Leds set")
			else:
				self.log("unknown event d")
		else:
			self.log("unknown event e")

	def handle_sensor_update(self, command):
		"""
		Read sensor data, converting to float and update sensor dict.

		Also reset control yaw to the current sensor yaw- this allows 
		roll to take in relative roll yaw angle commands, even though
		the sphero asks for absolute ones

		Theory: Sometimes the first sensor packet hasn't recognized we want
		all the sensor data, as only has components. To deal with this,
		make sure length of data is long enough to contain all sensors.

		When packet is all read and done, pickle and 
		fire it off to the server.
		"""
		if len(command["data"]) != 13 * 4:
			self.log("[Handle sensor update] Sensor data packet incomplete")
			return
		offset = 0
		data = command["data"]
		num_bytes = 4
		self.sensor_vals = dict()
		self.sensor_vals["pitch"] = \
			self.convert_binary_float(data, offset, num_bytes)
		offset += num_bytes
		self.sensor_vals["roll"] = \
			self.convert_binary_float(data, offset, num_bytes)
		offset += num_bytes
		self.sensor_vals["yaw"] = \
			self.convert_binary_float(data, offset, num_bytes)
		offset += num_bytes
		self.sensor_vals["ax"] = \
			self.convert_binary_float(data, offset, num_bytes)
		offset += num_bytes
		self.sensor_vals["ay"] = \
			self.convert_binary_float(data, offset, num_bytes)
		offset += num_bytes
		self.sensor_vals["az"] = \
			self.convert_binary_float(data, offset, num_bytes)
		offset += num_bytes
		self.sensor_vals["positionX"] = \
			self.convert_binary_float(data, offset, num_bytes) * 100.0
		offset += num_bytes
		self.sensor_vals["positionY"] = \
			self.convert_binary_float(data, offset, num_bytes) * 100.0
		offset += num_bytes
		self.sensor_vals["velocityX"] = \
			self.convert_binary_float(data, offset, num_bytes) * 100.0
		offset += num_bytes
		self.sensor_vals["velocityY"] = \
			self.convert_binary_float(data, offset, num_bytes) * 100.0
		offset += num_bytes
		self.sensor_vals["wx"] = \
			self.convert_binary_float(data, offset, num_bytes)
		offset += num_bytes
		self.sensor_vals["wy"] = \
			self.convert_binary_float(data, offset, num_bytes)
		offset += num_bytes
		self.sensor_vals["wz"] = \
			self.convert_binary_float(data, offset, num_bytes)
		offset += num_bytes

		for key, value in self.sensor_vals.items():
			if np.isnan(value):
				self.log("[handle_sensor_update] WE HAVE NANS")
				self.signal_restart()
		sphero_state = np.array(
			[self.sensor_vals[var] for var in self.shared_resources.sphero_config["SPHERO_OUTPUT_VARIABLES"]])

		self.shared_resources.resources["np_array_timestamps"][3 + self.sphero_num] = time.time()
		self.shared_resources.resources["np_array_packet_counters"][3 + self.sphero_num] += 1
		self.shared_resources.resources["np_array_sphero_states"][self.sphero_num] = np.insert(
			self.shared_resources.resources["np_array_sphero_states"][self.sphero_num],
			0, sphero_state, axis=0)[:-1]

	@staticmethod
	def convert_binary_float(data, offset, num_bytes):
		"""
		Quick conversion from (up to) 4 (big endian) bytes to a 16 bit float
		"""
		array = data[offset:offset + num_bytes]
		byte_array = bytearray(array)
		val = struct.unpack('>f', byte_array)[0]
		return val


if __name__ == "__main__":
	from SpheroLib.Lib.shared_resources import SharedResources
	import SpheroLib.Lib.config as sphero_config

	shared_resources = SharedResources(sphero_config)
	kill_switch = mp.Value('i')
	run_sphero(shared_resources, 0, kill_switch)
