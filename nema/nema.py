import lgpio
import time
import threading
import sys

sys.path.append('/srv/datalogger_michelin/')
from lib.utils import Utils

class Nema(Utils):
    def __init__(self, serial_lib, step_pin=18, dir_pin=23, log_id="NEMA"):
        self.log_id = log_id
        self.STEP = step_pin
        self.DIR = dir_pin
        
        self.serial_bus = serial_lib
        self.serial_bus.alert_callback = self.handle_alert
        
        self.bloqueo_der = False
        self.bloqueo_izq = False
        
        self.tiempo_ultimo_e1 = 0
        self.tiempo_ultimo_e2 = 0
        self.TIMEOUT_ALERTA = 5.0 
        
        self.estado_motor = "STOP"
        self.salir = False
        
        self.chip = lgpio.gpiochip_open(0)
        self._configurar_gpio()
        
        self.hilo_sensores = threading.Thread(target=self.tarea_sensores, daemon=True)
        self.hilo_sensores.start()
        
    def _configurar_gpio(self):
        lgpio.gpio_claim_output(self.chip, self.STEP)
        lgpio.gpio_claim_output(self.chip, self.DIR)
        lgpio.gpio_write(self.chip, self.STEP, 0)
        lgpio.gpio_write(self.chip, self.DIR, 0)
            
    def set_motor(self, nuevo_estado, frecuencia_motor = 800):
        if nuevo_estado == self.estado_motor:
            return
        self.estado_motor = nuevo_estado

        if nuevo_estado == "DER":
            lgpio.gpio_write(self.chip, self.DIR, 0)
            time.sleep(0.002)
            lgpio.tx_pwm(self.chip, self.STEP, frecuencia_motor, 50)
        elif nuevo_estado == "IZQ":
            lgpio.gpio_write(self.chip, self.DIR, 1)
            time.sleep(0.002)
            lgpio.tx_pwm(self.chip, self.STEP, frecuencia_motor, 50)
        else:
            lgpio.tx_pwm(self.chip, self.STEP, 100, 0)
            lgpio.gpio_write(self.chip, self.STEP, 0)
    
    def handle_alert(self, direccion, cuerpo):
        print(f"¡Alerta recibida en sensor {hex(direccion)}! Bytes: {cuerpo}")
        tiempo_actual = time.time()
        
        if direccion == 0xe2:
            self.tiempo_ultimo_e2 = tiempo_actual
            self.bloqueo_izq = True
        elif direccion == 0xe1:
            self.tiempo_ultimo_e1 = tiempo_actual
            self.bloqueo_der = True
    
    def tarea_sensores(self):
        aviso_der, aviso_izq = False, False

        while not self.salir:
            tiempo_actual = time.time()

            if self.bloqueo_der and (tiempo_actual - self.tiempo_ultimo_e1) > self.TIMEOUT_ALERTA:
                self.bloqueo_der = False

            if self.bloqueo_izq and (tiempo_actual - self.tiempo_ultimo_e2) > self.TIMEOUT_ALERTA:
                self.bloqueo_izq = False

            if self.bloqueo_der and not aviso_der:
                self.log("DETENIDO: sensor derecho detectó obstáculo")
                aviso_der = True
            elif not self.bloqueo_der and aviso_der:
                self.log("Ruta derecha liberada")
                aviso_der = False

            if self.bloqueo_izq and not aviso_izq:
                self.log("DETENIDO: sensor izquierdo detectó obstáculo")
                aviso_izq = True
            elif not self.bloqueo_izq and aviso_izq:
                self.log("Ruta izquierda liberada")
                aviso_izq = False

            time.sleep(0.1)
    
    def mover_der(self, frecuencia_motor=800):
        self.log("Iniciando movimiento automático a la DERECHA...")
        if self.bloqueo_der:
            self.log("No se puede iniciar movimiento a la derecha. El sensor derecho ya está bloqueado")
            return

        self.set_motor("DER", frecuencia_motor)
        while not self.bloqueo_der and not self.salir:
            time.sleep(0.01)
        
        self.set_motor("STOP")
        self.log("Movimiento a la DERECHA finalizado por detección de obstáculo o límite.")

    def mover_izq(self, frecuencia_motor=800): 
        self.log("Iniciando movimiento automático a la IZQUIERDA...")
        if self.bloqueo_izq:
            self.log("No se puede iniciar movimiento a la izquierda. El sensor izquierdo ya está bloqueado.")
            return

        self.set_motor("IZQ", frecuencia_motor)
        while not self.bloqueo_izq and not self.salir:
            time.sleep(0.01)
        
        self.set_motor("STOP")
        self.log("Movimiento a la IZQUIERDA finalizado por detección de obstáculo o límite.")

    def limpiar(self):
        self.salir = True
        self.set_motor("STOP")
        time.sleep(0.1)
        lgpio.gpiochip_close(self.chip)
        self.log("Proceso terminado correctamente")