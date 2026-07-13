import lgpio
import time
import threading
import sys

sys.path.append('/srv/datalogger_michelin/')
from lib.utils import Utils

class Nema(Utils):
    def __init__(self, step_pin=18, dir_pin=23, trig_der=5, echo_der=6, trig_izq=13, echo_izq=19, log_id="NEMA"):
        self.log_id = log_id
        self.STEP = step_pin
        self.DIR = dir_pin
        self.TRIG_DER = trig_der
        self.ECHO_DER = echo_der
        self.TRIG_IZQ = trig_izq
        self.ECHO_IZQ = echo_izq
        
        self.DIST_BLOQUEO = 6
        self.DIST_LIBRE = 10
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
        lgpio.gpio_claim_output(self.chip, self.TRIG_DER)
        lgpio.gpio_claim_input(self.chip, self.ECHO_DER)
        lgpio.gpio_claim_output(self.chip, self.TRIG_IZQ)
        lgpio.gpio_claim_input(self.chip, self.ECHO_IZQ)

        lgpio.gpio_write(self.chip, self.STEP, 0)
        lgpio.gpio_write(self.chip, self.DIR, 0)
        lgpio.gpio_write(self.chip, self.TRIG_DER, 0)
        lgpio.gpio_write(self.chip, self.TRIG_IZQ, 0)
            
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
            
    def medir_distancia(self, trig, echo):
        lgpio.gpio_write(self.chip, trig, 0)
        time.sleep(0.000003)
        lgpio.gpio_write(self.chip, trig, 1)
        time.sleep(0.00001)
        lgpio.gpio_write(self.chip, trig, 0)

        timeout = time.time() + 0.03
        while lgpio.gpio_read(self.chip, echo) == 0:
            if time.time() > timeout: return 999

        inicio = time.time()
        timeout = time.time() + 0.03
        while lgpio.gpio_read(self.chip, echo) == 1:
            if time.time() > timeout: return 999

        fin = time.time()
        return (fin - inicio) * 34300 / 2
    
    def _actualizar_bloqueo(self, distancia, bloqueo_actual, cont_bloq, cont_libre):
        if distancia == 999:
            cont_bloq = 0
            if bloqueo_actual:
                cont_libre += 1
                if cont_libre >= 8: bloqueo_actual = False
            return bloqueo_actual, cont_bloq, cont_libre

        if 0 < distancia <= self.DIST_BLOQUEO:
            cont_bloq += 1
            cont_libre = 0
            if cont_bloq >= 2: bloqueo_actual = True
        elif distancia > self.DIST_LIBRE:
            cont_libre += 1
            cont_bloq = 0
            if cont_libre >= 5: bloqueo_actual = False
        else:
            cont_bloq = 0

        return bloqueo_actual, cont_bloq, cont_libre
    
    def tarea_sensores(self):
        cont_bloq_der, cont_libre_der = 0, 0
        cont_bloq_izq, cont_libre_izq = 0, 0
        aviso_der, aviso_izq = False, False

        while not self.salir:
            der = self.medir_distancia(self.TRIG_DER, self.ECHO_DER)
            time.sleep(0.03)
            izq = self.medir_distancia(self.TRIG_IZQ, self.ECHO_IZQ)

            self.bloqueo_der, cont_bloq_der, cont_libre_der = self._actualizar_bloqueo(
                der, self.bloqueo_der, cont_bloq_der, cont_libre_der
            )
            self.bloqueo_izq, cont_bloq_izq, cont_libre_izq = self._actualizar_bloqueo(
                izq, self.bloqueo_izq, cont_bloq_izq, cont_libre_izq
            )

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
    