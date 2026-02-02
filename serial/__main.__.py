import time
import json
import sys

sys.path.append('/srv/datalogger_michelin/')
from serial_lib import SerialLib
from lib.usb_dev_node import USBDevnode

# Config
f = open('/srv/datalogger_michelin/config_michelin.json')
config:dict = json.load(f)

# Global variables
USB_SERIAL_SENSOR = config["SENSOR"]["PORT"]
CALIBRATION_LEVEL_CURVE = config["SENSOR"]["LEVEL_CURVE"] 
SERVER_IP = config["SERVER"]["IP"]
SERVER_PORT = config["SERVER"]["PORT"]

if __name__ == "__main__":
    devnode = USBDevnode(USB_SERIAL_SENSOR)
    RX = SerialLib(devnode, level_curve = CALIBRATION_LEVEL_CURVE, log_id = "SERIAL")
    RX.set_server(SERVER_IP, SERVER_PORT)
    RX.set_panic_command("systemctl restart mining-serial")
    RX.log("mining serial, initialized")