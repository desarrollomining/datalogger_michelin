import json
import sys

sys.path.append('/srv/datalogger_michelin/')
from serial_lib import SerialLib

# Config
f = open('/srv/datalogger_michelin/config_michelin.json')
config:dict = json.load(f)

# Global variables
SERVER_IP = config["SERVER"]["IP"]
SERVER_PORT = config["SERVER"]["PORT"]
NUM_SENSORS = config["SERIAL"]["NUM_SENSOR"]

if __name__ == "__main__":
    RX = SerialLib(num_sensores=NUM_SENSORS, log_id = "SERIAL")
    RX.set_server(SERVER_IP, SERVER_PORT)
    RX.set_panic_command("systemctl restart mining-serial")
    RX.log("mining serial, initialized")