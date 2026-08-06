import json
import socket
import threading
from time import sleep, time
import sys
import os
import numpy as np
from queue import Queue, Empty
import pandas as pd

sys.path.append('/srv/datalogger_michelin/')
from lib.utils import Utils
from database.models import Database

CONFIG_PATH = "/srv/datalogger_michelin/config_michelin.json"

class Server(Utils):
    def __init__(self, ip, port, log_id="SERVER"):
        self.log_id = log_id

        self.local_ip = ip
        self.local_port = port
        self.buffer_size = 65536

        self.prof_min = 0
        self.prof_max = 400


        self.serial_queue = Queue(maxsize=20000)

        self.UDPServerSocket = socket.socket(
            family=socket.AF_INET,
            type=socket.SOCK_DGRAM
        )
        self.UDPServerSocket.setsockopt(
            socket.SOL_SOCKET,
            socket.SO_REUSEADDR,
            1
        )
        self.UDPServerSocket.bind((self.local_ip, self.local_port))

        self.log(f"Server listening on {self.local_ip}:{self.local_port}")
        
        self.database = Database()

        threading.Thread(target=self.read_client_data).start()
        threading.Thread(target=self.serial_worker).start()
        
    def get_location(self):
        """Obtiene valores de vehicle y wheel dinámicamente"""
        try: 
            if os.path.exists(CONFIG_PATH):
                with open(CONFIG_PATH, 'r') as f:
                    config = json.load(f)
                    return config["LOCATION"]["VEHICLE"], config["LOCATION"]["WHEEL"]
        except:
            self.traceback()

    def read_client_data(self):
        """Recibe mensajes UDP y los mete en la cola"""
        while True:
            try:
                bytesAddressPair = self.UDPServerSocket.recvfrom(self.buffer_size)
                message = bytesAddressPair[0].decode('utf-8')
                payload = json.loads(message)

                if payload.get("name_id") == "SERIAL":
                    self.serial_queue.put(
                        (time(), payload.get("data")),
                        block=False
                    )

            except Exception:
                self.traceback()
                sleep(0.001)

    def serial_worker(self):
        """Consume las matrices de la cola y las procesa de forma puntual"""
        while True:
            try:
                _, data = self.serial_queue.get(timeout=0.5)
                self.process_pandas_matrix(data)

            except Empty:
                pass
            except Exception:
                self.traceback()

    def process_pandas_matrix(self, raw_matrix_data):
        """Procesa de manera puntual la matriz de pandas recibida"""
        try:
            df_raw = pd.DataFrame(raw_matrix_data)
            
            if df_raw.empty:
                self.log("Matriz recibida vacía")
                return

            vehicle, wheel = self.get_location()

            raw_json_str = json.dumps(df_raw.to_dict(orient='records'))
            self.database.insert_raw_data(raw_json_str, vehicle, wheel)
            
            df_processed = df_raw.copy()
            sensor_cols = [col for col in df_processed.columns]
            
            cols_to_keep = []

            for col in sensor_cols:
                col_mean = df_processed[col].mean()
                if self.prof_min <= col_mean <= self.prof_max:
                    cols_to_keep.append(col)
                else:
                    self.log(f"Columna '{col}' descartada. Promedio ({col_mean:.2f}) fuera de rango [{self.prof_min}, {self.prof_max}]")

            df_processed = df_processed[cols_to_keep]
            
            window_size = 5
            for col in cols_to_keep:
                df_processed[col] = self.moving_average(df_processed[col].values, window_size)

            processed_json_str = json.dumps(df_processed.to_dict(orient='records'))
            self.database.insert_processed_data(processed_json_str, vehicle, wheel)

            self.log(f"Matriz procesada y guardada con éxito en DB (Filas: {df_processed.shape[0]})")

        except Exception:
            self.traceback()


    def moving_average(self, data, window_size):
        """Media móvil causal con misma longitud que data"""
        if window_size <= 1:
            return data

        kernel = np.ones(window_size) / window_size
        filtered = np.convolve(data, kernel, mode='full')[:len(data)]
        return filtered



if __name__ == "__main__":
    with open('/srv/datalogger_michelin/config_michelin.json') as f:
        config = json.load(f)

    Server(
        ip=config["SERVER"]["IP"],
        port=config["SERVER"]["PORT"],
    )
