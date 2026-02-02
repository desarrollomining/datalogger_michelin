import sys
import os
from os.path import join

sys.path.append('/srv/datalogger_michelin/')
from lib.utils import Utils


class USBDevnode(Utils):
    def __init__(self, port, hwversion = "3B+"):
        self.hwversion = self.autodetect_hardware_version() #hwversion
        self.log_id = "USB"
        self.port = port
        print("USBDevNode: Autodetected HW version [%s]" % self.hwversion)

    def autodetect_hardware_version(self) -> str:
        """
        This function detects the hardware version of the Raspberry Pi based on the model name obtained from the system.

        Returns:
        str: The hardware version of the Raspberry Pi. It can be either "3B+", "3B", or "4B".
        """
        hardwareVersion = self.get_raspberry_pi_model()
        if "Raspberry Pi 3 Model B Plus" in hardwareVersion:
            return "3B+"
        elif "Raspberry Pi 3 Model B" in hardwareVersion:
            return "3B"
        elif "Raspberry Pi 4 Model B" in hardwareVersion:
            return "4B"

    def scan_path(self, path: str) -> str:
        """
        This function scans a given path for specific files and returns the first found device node.

        Parameters:
        path (str): The path to be scanned.

        Returns:
        str: The first found device node (e.g., "/dev/ttyUSB0") or None if no device node is found.
        """
        try:
            print("Scanning path %s" % path)
            files = os.listdir(path)
            for file in files:
                if file.startswith("ttyUSB"):
                    fullpath = f"/dev/{file}"
                    print(f"Device node found: {fullpath}")
                    return fullpath
                elif file.startswith("ttyACM"):
                    fullpath = f"/dev/{file}"
                    print(f"Device node found: {fullpath}")
                    return fullpath
        except Exception as e:
            self.log(f"Error scanning path: {e}")
        return None


    def get_devnode(self) -> str:
        """
        This function determines the device node (e.g., "/dev/ttyUSB0") for a given port and hardware version.
        It handles different cases based on the port and hardware version, and uses the `scan_path` function to find the device node.

        Parameters:
        - hwversion (str): The hardware version of the Raspberry Pi. It can be either "3B+", "3B", or "4B".
        - port (str or int): The port for which the device node needs to be determined. It can be a string ("GPS", "nano") or an integer (2, 3, 4, 5).

        Returns:
        str: The device node (e.g., "/dev/ttyUSB0") or None if no device node is found.
        """
        hwversion = self.hwversion
        port = self.port
        if type(port)== str:
            port = port.lower()
            if (port == "gps"):
                gps_ids = ["1546/1a7", "1546/1a8"]
                for gps_id in gps_ids:
                     port = self.find_tty_usb(gps_id, hwversion)
                     if port:
                         self.log("Found GPS device node: %s" % port)
                         return port
                return "/dev/ttyACM0"

            elif (port == "nano"):
                nano_ids = ["1a86/7523", "403/6001"]
                for nano_id in nano_ids:
                     port = self.find_tty_usb(nano_id, hwversion)
                     if port:
                         self.log("Found NANO device node: %s" % port)
                         return port
                return "/dev/ttyUSB0"

            elif (port == "esp32"):
                esp32_id = "10c4/ea60"
                port = self.find_tty_usb(esp32_id, hwversion)
                if port:
                    self.log("Found ESP32 device node: %s" % port)
                    return port
                return "/dev/ttyUSB0"
            
            elif (port == "rs485"):
                nano_ids = ["0403/6001"]
                for nano_id in nano_ids:
                     port = self.find_tty_usb(nano_id, hwversion)
                     if port:
                         self.log("Found RS485 device node: %s" % port)
                         return port
                return "/dev/ttyUSB0"
            
            else:
                self.log("Unknown port: %s" % port)
                return None
        
        else:

            path = self.get_port_path(hwversion, port)
            devnode = self.scan_path(path)
            if devnode is None:
                path = "%s/tty" % path
                devnode = self.scan_path(path)
            print("scanPath returned [%s]" % devnode)
            return devnode

    def get_port_path(self, hwversion, port):
        if (port == 2):
            if hwversion == "3B+":  #RPi3B+
                path = "/sys/devices/platform/soc/3f980000.usb/usb1/1-1/1-1.1/1-1.1.%d/1-1.1.%d:1.0/" % (port, port)
            elif hwversion == "4B":
                path = "/sys/devices/platform/scb/fd500000.pcie/pci0000:00/0000:00:00.0/0000:01:00.0/usb1/1-1/1-1.3/1-1.3:1.0"
            else:
                path = "/sys/devices/platform/soc/3f980000.usb/usb1/1-1/1-1.%d/1-1.%d:1.0/" % (port, port)

        if (port == 3):
            if hwversion == "3B+":  #RPi3B+
                path = "/sys/devices/platform/soc/3f980000.usb/usb1/1-1/1-1.1/1-1.1.%d/1-1.1.%d:1.0/" % (port, port)
            elif hwversion == "4B":
                path = "/sys/devices/platform/scb/fd500000.pcie/pci0000:00/0000:00:00.0/0000:01:00.0/usb1/1-1/1-1.4/1-1.4:1.0"
            else:
                path = "/sys/devices/platform/soc/3f980000.usb/usb1/1-1/1-1.%d/1-1.%d:1.0/" % (port, port)

        if (port == 4):
            if hwversion == "3B+":  #RPi3B+
                port = 3
                path = "/sys/devices/platform/soc/3f980000.usb/usb1/1-1/1-1.%d/1-1.%d:1.0" % (port, port)
            elif hwversion == "4B":
                path = "/sys/devices/platform/scb/fd500000.pcie/pci0000:00/0000:00:00.0/0000:01:00.0/usb1/1-1/1-1.1/1-1.1:1.0"
            else:
                path = "/sys/devices/platform/soc/3f980000.usb/usb1/1-1/1-1.%d/1-1.%d:1.0/" % (port, port)

        if (port == 5):                #path = "/sys/devices/platform/soc/3f980000.usb/usb1/1-1/1-1.1/1-1.1.3/1-1.1.3.4/1-1.1.3.4:1.0/tty/"
            #path = "/sys/devices/platform/soc/3f980000.usb/usb1/1-1/1-1.2/1-1.2:1.0/tty/"
            if hwversion == "3B+":  #RPi3B+
                port = 2
                path = "/sys/devices/platform/soc/3f980000.usb/usb1/1-1/1-1.%d/1-1.%d:1.0" % (port, port)
            elif hwversion == "4B":
                path = "/sys/devices/platform/scb/fd500000.pcie/pci0000:00/0000:00:00.0/0000:01:00.0/usb1/1-1/1-1.2/1-1.2:1.0"
            else:
                path = "/sys/devices/platform/soc/3f980000.usb/usb1/1-1/1-1.%d/1-1.%d:1.0/" % (port, port)

        return path

    def find_tty_usb(self, id, hw):
        dig_port = None
        for port in range(2,6):
            path = self.get_port_path(hw, port)
            try:
                path_e=path+"/uevent"
                archivo=open(path_e,"r")
                out1=archivo.read()
                if id in out1:
                    condition=0
                    while condition==0:
                        files = os.listdir(path)
                        dig_port="Libre"
                        for file in files:
                            if file.strip() == "tty":
                                files2 = os.listdir("%s/tty" % path)
                                for file2 in files2:
                                    if file2[:3] == "tty":
                                        dig_port="/dev/%s" % file2
                                        print("Device node found: %s" % dig_port)
                                        return dig_port
                            if file[:3] == "tty":
                                fullpath = "%s%s" % (path, file[:3])
                                dig_port= "/dev/%s" % file
                                print("Device node found: %s" % dig_port)
                                return dig_port
                        
                        if dig_port=="/dev/tty":
                            path=path+"/tty"
                        else:
                            condition=1
            except:
                pass
