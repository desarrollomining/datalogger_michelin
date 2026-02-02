import json
import socket
import threading
from time import sleep, time
import sys
import serial
import numpy as np
import matplotlib.pyplot as plt
import matplotlib
from matplotlib.ticker import MultipleLocator
import os
from queue import Queue, Empty
import csv 

matplotlib.use('Agg')

sys.path.append('/srv/datalogger_michelin/')
from lib.utils import Utils



class Server(Utils):
    def __init__(self, ip, port, seconds_microdata, log_id="SERVER"):
        self.log_id = log_id
        self.seconds_microdata = seconds_microdata
        self.timer_microdata = serial.serialutil.Timeout(self.seconds_microdata)

        self.local_ip = ip
        self.local_port = port
        self.buffer_size = 1024
        
        self.csv_path = "/srv/datalogger_michelin/data.csv"
        self.csv_file = open(self.csv_path, "a", newline="")
        self.csv_writer = None
        self.csv_header_written = False

        self.now = time()

        self.time = np.array([])
        self.matrix = None
        self.last_serial_data = {}
        self.prof_min = 0
        self.prof_max = 300


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

        threading.Thread(
            target=self.read_client_data
        ).start()

        threading.Thread(
            target=self.serial_worker
        ).start()

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
        """Consume datos del serial y los procesa en batches"""
        batch = []
        BATCH_SIZE = 50

        while True:
            try:
                ts, data = self.serial_queue.get(timeout=0.5)
                batch.append((ts, data))

                if len(batch) >= BATCH_SIZE:
                    self.process_serial_batch(batch)
                    batch.clear()

            except Empty:
                if batch:
                    self.process_serial_batch(batch)
                    batch.clear()

    def process_serial_batch(self, batch):
        rows = []
        times = []

        for ts, data in batch:
            for k, v in data.items():
                self.last_serial_data[k] = v

            row = np.array(
                [self.last_serial_data[k] for k in sorted(self.last_serial_data.keys())],
                dtype=float
            ).reshape(-1)

            rows.append(row)
            times.append(ts - self.now)

        rows = np.vstack(rows)
        times = np.array(times)

        window_size = 5  
        smoothed_rows = []

        for i in range(rows.shape[1]): 
            smoothed_column = self.moving_average(rows[:, i], window_size)
            smoothed_rows.append(smoothed_column)

        smoothed_rows = np.vstack(smoothed_rows).T  

        if not self.csv_header_written:
            header = ["timestamp"] + [
                f"sensor_{k}" for k in sorted(self.last_serial_data.keys())
            ]
            import csv
            self.csv_writer = csv.writer(self.csv_file)
            self.csv_writer.writerow(header)
            self.csv_header_written = True

        for t, row in zip(times, smoothed_rows):
            self.csv_writer.writerow([t] + row.tolist())

        self.csv_file.flush()

        if self.matrix is None:
            self.matrix = smoothed_rows
            self.time = times
        else:
            self.matrix = np.vstack((self.matrix, smoothed_rows))
            self.time = np.hstack((self.time, times))

        self.log(f"Tamaño matriz: {self.matrix.shape}")
        self.log(f"Tamaño tiempo: {self.time.shape}")
        if self.matrix.shape[0] > 3000:
            self.matrix = self.matrix[-3000:, :]
            self.time = self.time[-3000:]
            print("AAAA")
        self.render_image()



    def render_image(self):
        if self.matrix is None or self.matrix.size == 0:
            return

        fig, ax = plt.subplots(figsize=(12, 6))

        im = ax.imshow(
            self.matrix.T,
            aspect='auto',
            origin='lower',
            interpolation='nearest',
            cmap='viridis',
            vmin=self.prof_min,
            vmax=self.prof_max,
            extent=[
                self.time[0],
                self.time[-1],
                0.5,
                self.matrix.shape[1] + 0.5
            ]
        )

        ax.set_xlabel("Tiempo (s)")
        ax.set_ylabel("Sensor")
        ax.xaxis.set_major_locator(MultipleLocator(5))
        ax.set_yticks(np.arange(1, self.matrix.shape[1] + 1))

        cbar = fig.colorbar(im, ax=ax)
        cbar.set_label("Profundidad (mm)")

        fig.tight_layout()

        tmp_path = "/srv/datalogger_michelin/fig_tmp.jpg"
        final_path = "/srv/datalogger_michelin/fig.jpg"

        fig.savefig(tmp_path, dpi=150)
        plt.close(fig)

        os.replace(tmp_path, final_path)

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
        seconds_microdata=config["SERVER"]["SECONDS_MICRODATA"]
    )
