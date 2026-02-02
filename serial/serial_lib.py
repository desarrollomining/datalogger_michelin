import threading
import json
from serial import Serial
from time import time, sleep
from lib.utils import Utils
import re

class SerialLib(Utils):
    def __init__(self, usbdevnode, level_curve, baudrate: int = 115200, log_id = "SERIAL") -> None:
        self.usbdevnode = usbdevnode
        self.baudrate = baudrate
        self.timeout = 0.5
        self.log_id = log_id
        self.v_min, self.v_max = level_curve 
        self.last_timestamp = time()
        
        threading.Thread(target = self.connect).start()
        
    def connect(self) -> None:
        """
        This function attempts to establish a serial connection with the specified USB device node.

        """

        try:
            self.log(f"Try to connect serial port: {self.usbdevnode.get_devnode()}")
            self.serial_module = Serial(self.usbdevnode.get_devnode(), self.baudrate, timeout=self.timeout)
            self.read()

        except Exception as Ex:
            self.log(Ex)
            
    def read(self) -> None:
        """
        This function continuously reads lines from the serial module and processes them.
        If the line is empty, the function skips it.

        """
        self.log("Reading line from serial")
        while True:
            try:
                raw_line = self.serial_module.readline().decode("utf-8")
                line = raw_line.strip()
                if line =="":
                    pass
                else:
                    self.log(f"GOT: {line}")
                    self.process_line(line)
                sleep(0.01)
            except:
                self.log("Error decoding line")
                
    def process_line(self, line: str):
        try: 
            pattern = re.compile(r"\*(?P<data>[^:]+):(?P<values>(?:\d+:)*\d+)\*")

            match = pattern.match(line)
            if not match:
                return 
            data = match.group(1)
            values = list(map(int, match.group(2).split(":")))
            data_dict = {data: values}
            self.log(f"Data dict: {data_dict}")
            self.emit(data_type=self.log_id, data=data_dict)
        except Exception:
            self.traceback()