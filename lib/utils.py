import os
import datetime
import subprocess
import json
import socket
import traceback
import sys

class Utils:
    def __init__(self, log_id="UTILS"):
        self.log_id = log_id
        self.panic_cmd = "reboot" # Pretty extreme
        self.client_socket = None
        self.server_address = None

    def command(self, orden):
        orden_s=orden.split(' ')
        res=subprocess.check_output(orden_s)
        if res.decode()!='\n' or res.decode()!='':
            print(res.decode())

    def set_server(self, address, port):
        self.client_socket = socket.socket(family=socket.AF_INET, type=socket.SOCK_DGRAM)
        self.server_address = (address, port)

    def emit(self, data_type: str, data: dict)-> None:
        if self.client_socket is not None:
            dict_data = {}
            dict_data["name_id"] = data_type
            dict_data["data"] = data
            bytesToSend = str.encode(json.dumps(dict_data))
            self.client_socket.sendto(bytesToSend, self.server_address)


    def set_panic_command(self, panic_command):
        self.panic_cmd = panic_command

    # Please be careful
    def panic(self, message):
        self.log("PANIC: %s" % message)
        os.system("sync")
        os.system(self.panic_cmd)


    def online(self, host="8.8.8.8", port=53, timeout=10):
        try:
            socket.setdefaulttimeout(timeout)
            socket.socket(socket.AF_INET, socket.SOCK_STREAM).connect((host, port))
            self.log("Internet: We are online")
            return True
        except Exception as exc:
            self.log("Thing.online(): offline or failed: [%s]" % str(exc))
            return False

    def get_datetime(self):
        return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    def debug(self, message):
        if os.environ.get('DIO_DEBUG') is not None:
            self.log(message)

    def log(self,message):
        dt = self.get_datetime()
        print("[%s] %s | %s" % (self.log_id, dt, message))
        with open ("/log.txt", "a") as myfile:
            myfile.write("[%s] %s | %s\n" % (self.log_id, dt, message))

    def get_product_id(self):
        data = subprocess.check_output(["machineid"]).decode("utf-8").replace("\n", "")
        return int(data)

    def get_product_name(self):
        data = subprocess.check_output(["machinename"]).decode("utf-8").replace("\n", "")
        return data
    
    def get_location_assigned(self):
        caex = "STGO"
        try:
            f = open('/srv/live/topic.json')
            config:dict = json.load(f)
            caex = config["topic"].split("/")[2]
        except:
            self.traceback()
        return caex

    def get_faena_assigned(self):
        faena = "TallerStgo"
        try:
            f = open('/srv/live/topic.json')
            config:dict = json.load(f)
            faena = config["topic"].split("/")[0]
        except:
            self.traceback()
        return faena
    
    def get_avalaible_faenas(self):
        faenas = ["Antucoya", "Candelaria", "Centinela", "Ministro Hales"]
        return faenas

    def get_root_disk_usage(self):
        data = subprocess.check_output(["df"])
        lines = data.split("\n")
        for line in lines:
            if "/dev/root" in line:
                return line.split("%")[0].split(" ")[-1]

    def get_log_file_size(self):
        data = subprocess.check_output(["du","-sh","/log.txt"])
        return data.split("\t")[0]

    def get_uptime(self):
        data = subprocess.check_output(["uptime"])
        return data.split("up ")[1].split(",")[0].strip()

    def get_juice4halt_enabled(self):
        data = subprocess.check_output(["grep","/etc/rc.local","-e","juice4halt/bin/shutdown_script"])
        if "#" in data:
            return False
        else:
            return True

    def systemctl_status(self, service_name):
        data = "fuck"
        try:
            data = subprocess.check_output(["systemctl", "is-active", service_name])
        except:
            pass
        return data.strip()  # "active" | "inactive"
    
    def restart_service(self, service_name):
        try:
            res = subprocess.check_output(["systemctl", "restart", service_name])
            if res.decode()!='\n' or res.decode()!='':
                print(res.decode())
                print(f"Service {service_name} reiniciado correctamente")
        except:
            pass

    def get_raspberry_pi_model(self):
        model = "UNKNOWN"  # too old, newer OS versions do have this procfile
        with open("/proc/device-tree/model") as myfile:
            model = myfile.read().strip()
        return model

    def traceback(self):
        try:
            e = sys.exc_info()
            self.log("dumping traceback for [%s: %s]" % (str(e[0].__name__), str(e[1])))
            traceback.print_tb(e[2])
        except:
            foo = "bar"

    def write_file(self, filepath, contents, mode):
        if not os.path.exists(os.path.dirname(filepath)):
            os.makedirs(os.path.dirname(filepath))
        with open(filepath, mode) as f:
            f.write(contents)
