import threading
import struct
import json
import queue
from serial import Serial
from time import time, sleep
from lib.utils import Utils

CONFIG_PATH = "/srv/datalogger_michelin/config_michelin.json"

class SerialLib(Utils):
    def __init__(self, baudrate: int = 4800, port: str = "/dev/ttyUSB0", log_id: str = "SERIAL", alert_callback = None) -> None:
        self.baudrate = baudrate
        self.port = port
        self.timeout = 0.5
        self.log_id = log_id
        self.alert_callback = alert_callback
        self.last_timestamp = time()
        self.serial_module = None
        self.response_queue = queue.Queue()
        
        self.bus_lock = threading.Lock()
        
        with open(CONFIG_PATH, 'r') as f: 
            config = json.load(f)
        self.num_sensores = config["SERIAL"]["NUM_SENSOR"]
        self.direcciones_sensores = [0x41 + i for i in range(self.num_sensores)]
        
        self.ultimo_comando_enviado = None 
        self.ultima_respuesta = None
        self.evento_respuesta = threading.Event()
        
        threading.Thread(target=self.connect, daemon=True).start()
        
    def connect(self) -> None:
        """Establece la conexión serial con el dispositivo."""
        try:
            self.log(f"Intentando conectar al puerto serial: {self.port}")
            self.serial_module = Serial(self.port, self.baudrate, timeout=self.timeout)
            
            self.serial_module.reset_input_buffer()
            self.serial_module.reset_output_buffer()
            
            self.read_loop()
        except Exception as Ex:
            self.log(f"Error de conexión: {Ex}")
            
    def _calcular_cks(self, trama: bytearray) -> int:
        return sum(trama) & 0xFF

    def enviar_comando(self, direccion: int, comando: int, val1: int = 0, val2: int = 0, val3: int = 0, val4: int = 0) -> None:
        """Envía la trama física de 7 bytes al bus."""
        if not self.serial_module or not self.serial_module.is_open:
            self.log("Error: Puerto serial no está abierto.")
            return

        trama = bytearray([direccion, comando, val1, val2, val3, val4])
        cks = self._calcular_cks(trama)
        trama.append(cks)
        
        try:
            self.serial_module.reset_input_buffer()
            self.evento_respuesta.clear()
            self.ultima_respuesta = None
            self.ultimo_comando_enviado = comando    
            
            self.serial_module.write(trama)
            self.log(f"-> MAESTRO [{hex(direccion)}]: {hex(comando)} -> {[hex(b) for b in trama]}")
            
            if direccion == 0xFF or comando in [0x02, 0x03, 0x04, 0x08, 0x09]:
                self.ultimo_comando_enviado = None
                self.evento_respuesta.set()
                
        except Exception as Ex:
            self.log(f"Error al enviar comando: {Ex}")

    def revisar_estado_sensores(self) -> dict:
        """Consulta el estado (0x01) de cada sensor registrado en el sistema."""
        estados = {}
        with self.bus_lock:
            for dir_sensor in self.direcciones_sensores:
                self.enviar_comando(dir_sensor, 0x01)
                if self.evento_respuesta.wait(timeout=0.6) and self.ultima_respuesta:
                    estados[hex(dir_sensor)] = "OK" if self.ultima_respuesta.get("estado") == 0x01 else "FALLA"
                else:
                    estados[hex(dir_sensor)] = "TIMEOUT/DESCONECTADO"
        return estados
    
    def borrar_datos_local(self, direccion_sensor: int) -> None:
        """Comando 0x02: Borra la EEPROM local de un nodo."""
        with self.bus_lock:
            self.log(f"Borrando datos locales del sensor {hex(direccion_sensor)}...")
            self.enviar_comando(direccion_sensor, 0x02)
            sleep(0.05)
            
    def iniciar_monitoreo_global(self) -> None:
        """Arranca las mediciones en todos los sensores de forma secuencial."""
        with self.bus_lock:
            self.log("Iniciando monitoreo en todos los sensores...")
            for dir_sensor in self.direcciones_sensores:
                self.enviar_comando(dir_sensor, 0x03)
                sleep(0.05)
                
    def detener_monitoreo_global(self) -> None:
        """Pausa las mediciones en todos los sensores de forma secuencial."""
        with self.bus_lock:
            self.log("Deteniendo monitoreo en todos los sensores...")
            for dir_sensor in self.direcciones_sensores:
                self.enviar_comando(dir_sensor, 0x04)
                sleep(0.05)

    def consultar_cantidad_datos(self, direccion_sensor: int) -> int:
        """Pregunta a un sensor específico cuántos datos tiene guardados (uint16)."""
        with self.bus_lock:
            self.enviar_comando(direccion_sensor, 0x05)
            if self.evento_respuesta.wait(timeout=0.6) and self.ultima_respuesta:
                return self.ultima_respuesta.get("cantidad_datos", 0)
            return 0
    
    def leer_dato_especifico(self, direccion_sensor: int, indice: int) -> int:
        """Comando 0x06: Lee una posición específica. Devuelve valor o código de error (0xFFFF / 0xE001)."""
        h_idx = (indice >> 8) & 0xFF
        l_idx = indice & 0xFF
        with self.bus_lock:
            self.enviar_comando(direccion_sensor, 0x06, h_idx, l_idx)
            if self.evento_respuesta.wait(timeout=0.6) and self.ultima_respuesta:
                return self.ultima_respuesta.get("distancia_mm", 0xFFFF)
            return 0xFFFF
    
    def borrar_datos_global(self) -> None:
        """Borra los datos de todos los sensores al mismo tiempo usando Broadcast (0xFF)."""
        with self.bus_lock:
            self.log("Enviando orden de borrado global (Broadcast)...")
            self.enviar_comando(0xFF, 0x08)
            sleep(0.2)

    def reiniciar_sensor(self, direccion_sensor: int) -> None:
        """Realiza un Soft Reset (0x09) a un sensor específico."""
        with self.bus_lock:
            self.log(f"Reiniciando sensor {hex(direccion_sensor)}...")
            self.enviar_comando(direccion_sensor, 0x09)
            sleep(0.3)

    def obtener_rafagas_completas(self, direccion_sensor: int) -> list:
        """
        Descarga TODOS los datos de un sensor utilizando bloques de 100 en 100 (Comando 0x10).
        """
        todos_los_datos = []
        
        with self.bus_lock:
            sleep(0.15)
            self.enviar_comando(direccion_sensor, 0x05)
            if self.evento_respuesta.wait(timeout=4.0) and self.ultima_respuesta:
                total_datos = self.ultima_respuesta.get("cantidad_datos", 0)
            else:
                self.log(f"❌ Error: No se pudo obtener la cantidad de datos del sensor {hex(direccion_sensor)}")
                return todos_los_datos
                
            self.log(f"Sensor {hex(direccion_sensor)} reporta un total de {total_datos} datos.")
            if total_datos == 0:
                return todos_los_datos

            num_bloques = (total_datos + 99) // 100 

            for bloque in range(num_bloques):
                h_rango = (bloque >> 8) & 0xFF
                l_rango = bloque & 0xFF
                
                exito_bloque = False
                intentos = 3
                
                for intento in range(intentos):
                    self.log(f"Solicitando bloque {bloque} al sensor {hex(direccion_sensor)} (Intento {intento + 1}/{intentos})...")
                    self.enviar_comando(direccion_sensor, 0x10, h_rango, l_rango)
                    
                    if self.evento_respuesta.wait(timeout=4.0) and self.ultima_respuesta:
                        valores_bloque = self.ultima_respuesta.get("valores", [])
                        if valores_bloque or self.ultima_respuesta.get("cantidad", 0) == 0:
                            todos_los_datos.extend(valores_bloque)
                            exito_bloque = True
                            break
                    
                    sleep(0.05) 
                
                if not exito_bloque:
                    self.log(f"❌ Error crítico: Fallo definitivo al leer el bloque {bloque} del sensor {hex(direccion_sensor)}")
                    break
                    
                sleep(0.02)
                
        return todos_los_datos
    
    def configurar_umbral_float(self, direccion_sensor: int, valor_float: float) -> bool:
        """Comando 0x11: Configura umbral de distancia para sensores ultrasónicos."""
        bytes_float = struct.pack('>f', valor_float)
        b3, b2, b1, b0 = bytes_float[0], bytes_float[1], bytes_float[2], bytes_float[3]
        
        with self.bus_lock:
            self.enviar_comando(direccion_sensor, 0x11, b3, b2, b1, b0)
            if self.evento_respuesta.wait(timeout=0.6) and self.ultima_respuesta:
                return self.ultima_respuesta.get("estado") == 0x01
            return False
        
    def consultar_distancia_actual(self, direccion_sensor: int):
        """Comando 0x12: Consulta la medición actual en vivo en formato float (cm ultrasónico / mm ToF)."""
        with self.bus_lock:
            self.enviar_comando(direccion_sensor, 0x12)
            if self.evento_respuesta.wait(timeout=0.6) and self.ultima_respuesta:
                return self.ultima_respuesta.get("distancia_float")
            return None

    def read_loop(self) -> None:
        while True:
            try:
                if not self.serial_module or not self.serial_module.is_open:
                    sleep(0.1)
                    continue

                with self.bus_lock:
                    if self.serial_module.in_waiting < 2:
                        continue
                    header = self.serial_module.read(2)
                
                if len(header) < 2:
                    continue
                
                dir_res, cmd_res = header[0], header[1]
                self.procesar_respuesta(header, cmd_res)
                
            except Exception:
                self.traceback()
            sleep(0.01)

    def procesar_respuesta(self, header: bytes, cmd_res: int) -> None:
        try:
            if cmd_res in [0x01, 0x11]:
                cuerpo = self.serial_module.read(2)
                trama_completa = header + cuerpo
                if self._verificar_cks(trama_completa):
                    self.ultima_respuesta = {"estado": cuerpo[0]}

            elif cmd_res in [0x05, 0x06]:
                cuerpo = self.serial_module.read(3)
                trama_completa = header + cuerpo
                if self._verificar_cks(trama_completa):
                    valor = (cuerpo[0] << 8) | cuerpo[1]
                    key = "cantidad_datos" if cmd_res == 0x05 else "distancia_mm"
                    self.ultima_respuesta = {key: valor}

            elif cmd_res == 0x10:
                primer_byte = self.serial_module.read(1)
                if len(primer_byte) < 1: return

                if primer_byte[0] == 0xEE:
                    cks = self.serial_module.read(1)
                    trama_completa = header + primer_byte + cks
                    if self._verificar_cks(trama_completa):
                        self.ultima_respuesta = {"error": 0xEE, "valores": []}
                else:
                    segundo_byte = self.serial_module.read(1)
                    if len(segundo_byte) < 1: return

                    cant_bytes = primer_byte + segundo_byte
                    cantidad_datos = (cant_bytes[0] << 8) | cant_bytes[1]
                    bytes_restantes = (cantidad_datos * 2) + 1
                    
                    datos_raw = bytearray()
                    tiempo_limite = time() + 3.0  
                    while len(datos_raw) < bytes_restantes and time() < tiempo_limite:
                        chunk = self.serial_module.read(bytes_restantes - len(datos_raw))
                        if chunk:
                            datos_raw.extend(chunk)

                    trama_completa = header + cant_bytes + bytes(datos_raw)
                    if self._verificar_cks(trama_completa):
                        lista_valores = [(datos_raw[i] << 8) | datos_raw[i+1] for i in range(0, cantidad_datos * 2, 2)]
                        self.ultima_respuesta = {"cantidad": cantidad_datos, "valores": lista_valores}
            
            elif cmd_res == 0x12:
                cuerpo = self.serial_module.read(5)
                trama_completa = header + cuerpo
                if self._verificar_cks(trama_completa):
                    val_float = struct.unpack('>f', cuerpo[0:4])[0]
                    self.ultima_respuesta = {"distancia_float": val_float}
            
            elif cmd_res == 0x13:
                cuerpo = self.serial_module.read(2)
                if len(cuerpo) < 2:
                    return
                
                trama_completa = header + cuerpo
                if self._verificar_cks(trama_completa):
                    self.ultima_respuesta = {"alerta_limite": cuerpo}
                    
                    if self.alert_callback:
                        try:
                            self.alert_callback(header[0], cuerpo)
                        except Exception as e:
                            self.log(f"Error en callback de alerta: {e}")
                return

        finally:
            self.ultimo_comando_enviado = None
            self.evento_respuesta.set()

    def _verificar_cks(self, trama: bytes) -> bool:
        if len(trama) < 3: return False
        cks_recibido = trama[-1]
        if cks_recibido == self._calcular_cks(trama[:-1]):
            return True
        self.log(f"❌ Checksum incorrecto.")
        return False