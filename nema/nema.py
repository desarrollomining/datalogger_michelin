import lgpio
import time
import threading
import sys

sys.path.append('/srv/datalogger_michelin/')
from lib.utils import Utils

class Nema(Utils):
    def __init__(self, step_pin=18, dir_pin=23, sen_der=5, sen_izq=6, log_id="NEMA"):
        self.log_id = log_id
        self.STEP = step_pin
        self.DIR = dir_pin
        self.SEN_DER = sen_der
        self.SEN_IZQ = sen_izq
        
        self.FRECUENCIA_MOTOR = 800
        
        self.bloqueo_der = False
        self.bloqueo_izq = False
        self.estado_motor = "STOP"
        self.salir = False
        
        self.chip = lgpio.gpiochip_open(0)
        self._configurar_gpio()
        
        self.hilo_sensores = threading.Thread(target=self.tarea_sensores, daemon=True)
        self.hilo_sensores.start()
        
    def _configurar_gpio(self):
        lgpio.gpio_claim_output(self.chip, self.STEP)
        lgpio.gpio_claim_output(self.chip, self.DIR)

        lgpio.gpio_claim_input(self.chip, self.SEN_DER)
        lgpio.gpio_claim_input(self.chip, self.SEN_IZQ)

        lgpio.gpio_write(self.chip, self.STEP, 0)
        lgpio.gpio_write(self.chip, self.DIR, 0)
            
    def set_motor(self, nuevo_estado):
        if nuevo_estado == self.estado_motor:
            return
        self.estado_motor = nuevo_estado

        if nuevo_estado == "DER":
            lgpio.gpio_write(self.chip, self.DIR, 0)
            time.sleep(0.002)
            lgpio.tx_pwm(self.chip, self.STEP, self.FRECUENCIA_MOTOR, 50)
        elif nuevo_estado == "IZQ":
            lgpio.gpio_write(self.chip, self.DIR, 1)
            time.sleep(0.002)
            lgpio.tx_pwm(self.chip, self.STEP, self.FRECUENCIA_MOTOR, 50)
        else:
            lgpio.tx_pwm(self.chip, self.STEP, 100, 0)
            lgpio.gpio_write(self.chip, self.STEP, 0)
    
    def tarea_sensores(self):
        aviso_der, aviso_izq = False, False

        while not self.salir:
            self.bloqueo_der = bool(lgpio.gpio_read(self.chip, self.SEN_DER))
            self.bloqueo_izq = bool(lgpio.gpio_read(self.chip, self.SEN_IZQ))

            if self.bloqueo_der and not aviso_der:
                self.log("DETENIDO: sensor derecho detectó obstáculo")
                aviso_der = True
            if not self.bloqueo_der and aviso_der:
                self.log("Ruta derecha liberada")
                aviso_der = False

            if self.bloqueo_izq and not aviso_izq:
                self.log("DETENIDO: sensor izquierdo detectó obstáculo")
                aviso_izq = True
            if not self.bloqueo_izq and aviso_izq:
                self.log("Ruta izquierda liberada")
                aviso_izq = False

            time.sleep(0.08)
    
    
    def mover_der(self):
        """Mueve el motor a la derecha de forma continua hasta que el sensor derecho bloquee."""
        self.log("Iniciando movimiento automático a la DERECHA...")
        if self.bloqueo_der:
            self.log("No se puede iniciar movimiento a la derecha. El sensor derecho ya está bloqueado")
            return

        self.set_motor("DER")
        while not self.bloqueo_der and not self.salir:
            time.sleep(0.01)
        
        self.set_motor("STOP")
        self.log("Movimiento a la DERECHA finalizado por detección de obstáculo o límite.")

    def mover_izq(self):
        """Mueve el motor a la izquierda de forma continua hasta que el sensor izquierdo bloquee."""
        self.log("Iniciando movimiento automático a la IZQUIERDA...")
        if self.bloqueo_izq:
            self.log("No se puede iniciar movimiento a la izquierda. El sensor izquierdo ya está bloqueado.")
            return

        self.set_motor("IZQ")
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
    