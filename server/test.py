import json
import socket
import threading
from time import sleep, time
import sys
import numpy as np
from queue import Queue, Empty
import pandas as pd

sys.path.append('/srv/datalogger_michelin/')
from lib.utils import Utils
from database.models import Database

class Server(Utils):
    def __init__(self, ip, port, vehicle, wheel, log_id="SERVER"):
        self.log_id = log_id
        self.vehicle = vehicle
        self.wheel = wheel

        self.local_ip = ip
        self.local_port = port
        self.buffer_size = 65536

        self.prof_min = 0
        self.prof_max = 400

        self.accumulated_data = {}      
        self.last_received_time = None  
        self.timeout_seconds = 5.0      
        self.lock = threading.Lock()   

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

        threading.Thread(target=self.read_client_data, daemon=True).start()
        threading.Thread(target=self.timeout_watcher, daemon=True).start()
        threading.Thread(target=self.serial_worker, daemon=True).start()

    def read_client_data(self):
        """Recibe paquetes UDP de cualquier sensor y actualiza el buffer de acumulación"""
        while True:
            try:
                bytesAddressPair = self.UDPServerSocket.recvfrom(self.buffer_size)
                message = bytesAddressPair[0].decode('utf-8')
                payload = json.loads(message)

                if payload.get("name_id") == "SERIAL":
                    sensor_id = payload.get("sensor_id")  
                    buffer_data = payload.get("data")     
                    
                    if sensor_id is None or not isinstance(buffer_data, list):
                        continue

                    with self.lock:
                        if sensor_id not in self.accumulated_data:
                            self.accumulated_data[sensor_id] = []
                        
                        self.accumulated_data[sensor_id].extend(buffer_data)
                        self.last_received_time = time() 

            except Exception:
                self.traceback()
                sleep(0.001)

    def timeout_watcher(self):
        """Monitorea el tiempo de inactividad. Si se cumple el timeout, cierra la matriz."""
        while True:
            try:
                sleep(0.5) 
                
                if self.last_received_time is None:
                    continue
                
                if (time() - self.last_received_time) >= self.timeout_seconds:
                    with self.lock:
                        if self.accumulated_data:
                            lengths = [len(v) for v in self.accumulated_data.values()]
                            
                            if len(set(lengths)) == 1 and lengths[0] > 0:
                                self.log(f"Timeout de {self.timeout_seconds}s alcanzado. "
                                         f"Estructura uniforme detectada ({len(lengths)} sensores con {lengths[0]} datos). "
                                         f"Enviando a cola de procesamiento...")
                                
                                final_matrix = {k: v for k, v in self.accumulated_data.items()}
                                self.serial_queue.put((time(), final_matrix), block=False)
                            else:
                                self.log(f"Lectura descartada tras timeout: Datos asimétricos entre sensores. Largos: {lengths}")
                            
                            self.accumulated_data.clear()
                            self.last_received_time = None

            except Exception:
                self.traceback()

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
        """Procesa de manera puntual el diccionario de sensores convertido en DataFrame"""
        try:
            df_raw = pd.DataFrame(raw_matrix_data)
            
            if df_raw.empty:
                self.log("Matriz recibida vacía")
                return

            raw_json_str = json.dumps(df_raw.to_dict(orient='records'))
            self.database.insert_raw_data(raw_json_str, self.vehicle, self.wheel)
            
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
            self.database.insert_processed_data(processed_json_str, self.vehicle, self.wheel)

            self.log(f"Matriz procesada y guardada con éxito en DB (Filas: {df_processed.shape[0]}, Columnas/Sensores: {df_processed.shape[1]})")

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
        vehicle=config["LOCATION"]["VEHICLE"],
        wheel=config["LOCATION"]["WHEEL"]
    )