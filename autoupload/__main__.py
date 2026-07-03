from time import sleep 
import traceback
import json
import sys

CONFIG_SOURCE = "/srv/datalogger_michelin/config_michelin.json"
sys.path.append('/srv/datalogger_michelin/')
from lib import mqtt
from lib.utils import Utils
from database.models import Database

class Upload(Utils):
    def __init__(self, config_path):
        self.log_id = "UPLOAD"
        self.config_path = config_path
        self.machine_id = self.get_product_id()
        self.machine_name = self.get_product_name()
        self.location = self.get_location_assigned()
        self.faena = self.get_faena_assigned()
        self.database = Database()
        self.update_topic()
        
    def update_topic(self):
        try: 
            f = open(self.config_path)
            config:dict = json.load(f)
            
            self.activated_mining = config["AUTOUPLOAD"]["MINING"]["ACTIVATED"]
            self.topic = config["AUTOUPLOAD"]["MINING"]["DATA"]
        
        except:
            self.activated_mining = 0
            self.topic = ""
            
            self.traceback()
            
    def check_data(self):
        try:
            print(f"Check data {self.get_datetime()}")
            if self.activated_mining:
                print("CHECK DATA MINING")
                data, _ = self.database.get_raw_data(condition_column= "uploaded_mining")
                data2, _ = self.database.get_processed_data(condition_column= "uploaded_mining")
                if data and self.topic:
                    ids_success = self.upload_mqtt(data, self.topic)
                    if ids_success: self.database.update_value(table="raw_data", column_name= "uploaded_mining", ids = ids_success)
                else: 
                    print("No raw data to upload to Mining") 
                if data2 and self.topic:
                    ids_success = self.upload_mqtt(data2, self.topic)
                    if ids_success: self.database.update_value(table="processed_data", column_name = "uploaded_mining", ids = ids_success)
                else: 
                    print("No processed data to upload to Mining")
        except:
            self.traceback()
            
    def upload_mqtt(self, data, topic):
        print(f"Try to upload data to {topic}")
        ids = []
        client = mqtt.connect()
        try: 
            if client.is_connected():
                sub_topic = f"acks/{topic}"
                client.subscribe(sub_topic)
                for row in data:
                    packet = []
                    for microdata in eval(row[1]):
                        null_key = []
                        for key in microdata.keys():
                            if microdata[key] is None:
                                null_key.append(key)
                        for key in null_key: microdata.pop(key, None)
                            
                        dict_microdata = {
                            "measurement": microdata
                        }
                        packet.append(dict_microdata)
                        
                    dict_data = {
                        "packet": packet,
                        "id": row[0],
                        "vehicle": row[2],
                        "wheel": row[3],
                        "name": self.machine_name, 
                        "machineid": int(self.machine_id)
                    }
                    print(f"Data to upload: {dict_data}")
                        
                    result = mqtt.publish(client= client, topic=topic, dict_data=dict_data)
                    if result:
                        print(f"Data uploaded Success to {topic}")
                        res = mqtt.get_response(wait=2)
                        if res:
                            if row[0] == res.get("id", -1) and res.get("status", "error") == "success": ids.append(row[0])
                            else: print("Error al escribir en la base de datos del server")
                        else: print("No hay respuesta del server")
                    
                client.loop_stop()
                client.disconnect()
                return ids
            else: 
                print("No se logró conectar a MQTT")        
        except:
            self.traceback()
        return ids
            
if __name__ == "__main__":
    print("---")
    print("INIT AUTOUPLOAD")
    upload = Upload(CONFIG_SOURCE)
    while True:
        try:
            upload.check_data()
        except:
            print("error")
            e = sys.exc_info()
            print("dumping traceback for [%s: %s]" % (str(e[0].__name__), str(e[1])))
            traceback.print_tb(e[2])
            foo = "bar"
        sleep(10)