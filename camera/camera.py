import subprocess
import sys
import threading
import time

sys.path.append('/srv/datalogger_michelin/')
from lib.utils import Utils

class Camera(Utils):
    def __init__(self, wheel, log_id = "CAMERA"):
        self.log_id = log_id
        self.wheel = wheel
        self.process = None
        self.max_duration = 300
        
    def start_recording(self):
        self.log(f"Starting recording for wheel: {self.wheel}")
        output_file = f"/srv/datalogger_michelin/web-server/static/videos/{self.wheel}.mp4"
        try:
            command = [
                'ffmpeg',
                '-y',                     
                '-f', 'v4l2',
                '-video_size', '640x480',
                '-i', '/dev/video0',
                '-c:v', 'libx264',
                '-preset', 'ultrafast',
                output_file
            ]
            self.process = subprocess.Popen(command, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            self.safety_thread = threading.Thread(target=self.safety_timeout, daemon=True)
            self.safety_thread.start()
        except:
            self.traceback()
            
    def safety_timeout(self):
        start_time = time.time()
        while self.process and self.process.poll() is None:
            elapsed_time = time.time() - start_time
            if elapsed_time > self.max_duration:
                self.log("Max duration reached. Safety stop in progress.")
                self.stop_recording()
                break
            time.sleep(1)
    
    def stop_recording(self):
        if self.process and self.process.poll() is None:
            self.log("Stopping recording...")
            try:
                self.process.communicate(input=b'q', timeout=5)
            except subprocess.TimeoutExpired:
                self.log("Process did not terminate in time. Killing it.")
                self.process.kill()
            self.process = None
        else:
            self.log("Stop requested but no active recording process found.")
