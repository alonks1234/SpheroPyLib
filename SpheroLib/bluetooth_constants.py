UUID_SPHERO_SERVICE = '00010001-574f-4f20-5370-6865726f2121'
UUID_SPHERO_SERVICE_INITIALIZE = '00020001-574f-4f20-5370-6865726f2121'

APIV2_CHARACTERISTIC = '00010002-574f-4f20-5370-6865726f2121'
ANTIDOS_CHARACTERISTIC = '00020005-574f-4f20-5370-6865726f2121'
DFU_CONTROL_CHARACTERISTIC = '00020002-574f-4f20-5370-6865726f2121'
DFU_INFO_CHARACTERISTIC = '00020004-574f-4f20-5370-6865726f2121'
SUBS_CHARACTERISTIC = '00020003-574f-4f20-5370-6865726f2121'

NOTIFICATION_CHARACTERISTICS = [
	APIV2_CHARACTERISTIC,
	"00010003-574f-4f20-5370-6865726f2121",
	DFU_CONTROL_CHARACTERISTIC,
	"00002a05-0000-1000-8000-00805f9b34fb",
]

useTheForce = [0x75, 0x73, 0x65, 0x74, 0x68, 0x65, 
              0x66, 0x6f, 0x72, 0x63, 0x65, 0x2e, 
              0x2e, 0x2e, 0x62, 0x61, 0x6e, 0x64]


APIConstants = {
    "escape" : 171,
    "startOfPacket" : 141,
    "endOfPacket" : 216,
    "escapeMask" : 136,
    "escapedEscape" : 35,
    "escapedStartOfPacket" : 5,
    "escapedEndOfPacket" : 80
}

BatteryState = {
    "notCharging": 1,
    "charging": 2,
    "charged": 3
}

ApiErrors = {
    "success": 0,
    "badDeviceId": 1,
    "badCommandId": 2,
    "notYetImplemented": 3,
    "commandIsRestricted": 4,
    "badDataLength": 5,
    "commandFailed": 6,
    "badParameterValue": 7,
    "busy": 8,
    "badTargetId": 9,
    "targetUnavailable": 10,
    "unknown": 255
}

Flags = {
    "isResponse" : 1,
    "requestsResponse" : 2,
    "requestsOnlyErrorResponse" : 4,
    "resetsInactivityTimeout" : 8,
    "commandHasTargetId" : 16,
    "commandHasSourceId" : 32
}

DeviceId = {
    "apiProcessor" : 16,
    "systemInfo" : 17,
    "powerInfo" : 19,
    "driving" : 22,
    "sensor" : 24,
    "userIO" : 26
}

DrivingCommandIds = {
    "rawMotor" : 1,
    "driveAsRc" : 2,
    "driveAsSphero" : 4,
    "resetYaw" : 6,
    "driveWithHeading" : 7,
    "tankDrive" : 8,
    "stabilization" : 12
}

PowerCommandIds = {
    "deepSleep" : 0,
    "sleep" : 1,
    "batteryVoltage" : 3,
    "inform":5,
    "wake" : 13,
    "unknownWake":17,
    "willSleepAsync" : 25,
    "sleepAsync" : 26,
    "batteryStateChange" : 33,
    "charging":31

}

UserIOCommandIds = {
    "playAudioFile" : 7,
    "audioVolume" : 8,
    "stopAudio" : 10,
    "testSound" : 24,
    "allLEDs" : 28,
    "setUserProfile" : 35,
    "matrixPixel" :45,
    "matrixColor" : 47,
    "clearMatrix" : 56, 
    "matrixRotation" : 58,
    "matrixScrollText" : 59,
    "matrixScrollNotification": 60,
    "matrixLine" : 61,
    "matrixFill" : 62,
    "printChar" : 66
}

SensorCommandIds = {
    "sensorMask" : 0,
    "sensorResponse" : 2,
    "configureCollision" : 17,
    "collisionDetectedAsync" : 18,
    "resetLocator" : 19,
    "enableCollisionAsync" : 20,
    "sensor1" : 15,
    "sensor2" : 23,
    "sensorMaskExtended" : 12,
    "calibrateToNorth": 37,
    "compassNotify": 38,
}

SensorMaskValues = {
  "off" : 0,
  "locator" : 1,
  "gyro" : 2,
  "orientation" : 3,
  "accelerometer" : 4
}

SensorMask = {

  "off" : 0,
  "velocityY" : 1 << 3,
  "velocityX" : 1 << 4,
  "locatorY" : 1 << 5,
  "locatorX" : 1 << 6,

  "gyroZFiltered" : 1 << 23,
  "gyroYFiltered" : 1 << 24,
  "gyroXFiltered" : 1 << 25,

  "accelerometerZFiltered" : 1 << 13,
  "accelerometerYFiltered" : 1 << 14,
  "accelerometerXFiltered" : 1 << 15,
  "imuYawAngleFiltered" : 1 << 16,
  "imuRollAngleFiltered" : 1 << 17,
  "imuPitchAngleFiltered" : 1 << 18,

  "gyroFilteredAll" : 58720256,
  "orientationFilteredAll" : 458752,
  "accelerometerFilteredAll" : 57344,
  "locatorFilteredAll" : 120,
}