import sys
import json
import os
import time
import subprocess

sys.path.append('/srv/datalogger_michelin/')
from lib.utils import Utils

SOURCE_CONFIG = "/srv/datalogger_michelin/config_michelin.json"

class Config(Utils):
    def __init__(self, log_id="CONFIG"):
        self.log_id = log_id
        self.machine_name = self.get_product_name()
        self.faena = self.get_faena_assigned()
        
    
    def check_exist(self, source_config):
        self.log("Checking config files...")
        
        if not os.path.isfile(source_config):
            self.log("Config_michelin.json not found")
            config_mmr = {
                "SERVER":{
                    "IP": "127.0.0.1",
                    "PORT": 20001
                },
                "AUROUPLOAD":{
                    "MINING":{
                        "ACTIVATED": 1,
                        "DATA": "",
                        "LOCATION": ""
                    }
                },
                "LOCATION": {
                    "VEHICLE": "",
                    "WHEEL": ""
                }
            }
            
            with open(source_config, "w") as f:
                json.dump(config_mmr, f, indent=4)
            self.log("Config_michelin.json created")
            return
        
        self.log("Config_michelin.json found")
        
    def  update_mining_config(self, source_config):
        print("UPDATE MINING CONFIG")
        try: 
            TOPIC_DATA = f"{self.faena}/dataloggers/{self.machine_name}"
            TOPIC_LOCATION = f"{self.faena}/dataloggers/mapa/{self.machine_name}"
            with open(source_config, "r") as f:
                config = json.load(f)
                
            if  config["AUROUPLOAD"]["MINING"]["DATA"] != TOPIC_DATA or config["AUROUPLOAD"]["MINING"]["LOCATION"] != TOPIC_LOCATION:
                config["AUROUPLOAD"]["MINING"]["DATA"] = TOPIC_DATA
                config["AUROUPLOAD"]["MINING"]["LOCATION"] = TOPIC_LOCATION
                with open(source_config, "w") as f:
                    json.dump(config, f, indent=4)
                self.log("CONFIGURACION MINING ACTUALIZADA")
                self.restart_service("mining-autoupload")
            else: 
                print("CONFIGURACION MINING YA ESTA ACTUALIZADA")
        except:
            subprocess.check_output(["sudo", "rm", SOURCE_CONFIG])
            self.check_exist(SOURCE_CONFIG)
    

if __name__ == "__main__":
    config = Config()
    print("Actualizando configuraciones")
    config.check_exist(SOURCE_CONFIG)
    config.update_mining_config(SOURCE_CONFIG)
                