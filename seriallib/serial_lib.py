import threading
import struct
import json
import queue
import math
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
         
        with open(CONFIG_PATH, 'r') as f: 
            config = json.load(f)
        self.num_sensores = config["SERIAL"]["NUM_SENSOR"]
        self.direcciones_sensores = [0x41 + i for i in range(self.num_sensores)]
        
        self.escuchando_alertas = True
        
        # Evento para pausar/reanudar el hilo de alertas limpiamente
        self.evento_adquisicion = threading.Event()
        
        # Bloqueo para sincronizar accesos concurrentes al puerto serial entre hilos
        self.serial_lock = threading.Lock()
        
        threading.Thread(target=self.connect, daemon=True).start()
        
        self.hilo_alertas = threading.Thread(target=self._bucle_escucha_alertas, daemon=True)
        self.hilo_alertas.start()

    def connect(self):
        """Establece la conexión serial con el puerto configurado."""
        try:
            with self.serial_lock:
                self.serial_module = Serial(port=self.port, baudrate=self.baudrate, timeout=self.timeout)
            self.log(f"[{self.log_id}] Conectado exitosamente al puerto {self.port} a {self.baudrate} baudios.")
        except Exception as e:
            self.log(f"[{self.log_id}] [ERROR] Error al conectar con el puerto serial: {e}")

    def _bucle_escucha_alertas(self):
        """Monitorea el puerto serial buscando alertas 0x13 únicamente durante la adquisición activa."""
        while self.escuchando_alertas:
            # Si no hay adquisición activa, el hilo duerme esperando la señal de START GLOBAL
            self.evento_adquisicion.wait()
            
            try:
                if self.serial_module and self.serial_module.is_open:
                    with self.serial_lock:
                        if self.serial_module.in_waiting >= 4:
                            buffer_actual = self.serial_module.read(self.serial_module.in_waiting)
                        else:
                            buffer_actual = b""
                    
                    if buffer_actual:
                        # Analizamos el buffer en busca de tramas de alerta 0x13 (longitud fija de 4 bytes)
                        i = 0
                        while i <= len(buffer_actual) - 4:
                            r_dir = buffer_actual[i]
                            r_cmd = buffer_actual[i+1]
                            
                            if r_cmd == 0x13:
                                cuerpo = buffer_actual[i+2]
                                cks = buffer_actual[i+3]
                                cks_calc = (r_dir + r_cmd + cuerpo) & 0xFF
                                
                                if cks == cks_calc:
                                    if self.alert_callback:
                                        self.alert_callback(r_dir, cuerpo)
                                    buffer_actual = buffer_actual[:i] + buffer_actual[i+4:]
                                    continue
                            i += 1
                sleep(0.05)
            except Exception as e:
                sleep(0.1)

    def enviar_orden(self, dir_val: int, cmd: int, val_1: int, val_2: int, val_3: int, val_4: int):
        """Envía una trama de orden por RS485 calculando el checksum."""
        if not self.serial_module or not self.serial_module.is_open:
            self.log(f"[{self.log_id}] [ERROR] Puerto serial no disponible para enviar orden.")
            return

        cks = (dir_val + cmd + val_1 + val_2 + val_3 + val_4) & 0xFF
        trama = struct.pack("BBBBBBB", dir_val, cmd, val_1, val_2, val_3, val_4, cks)
        
        try:
            with self.serial_lock:
                self.serial_module.write(trama)
                self.serial_module.flush()
        except Exception as e:
            self.log(f"[{self.log_id}] [ERROR] Error al escribir en el puerto serial: {e}")

    def esperar_respuesta(self, bytes_esperados: int):
        """Espera y procesa respuestas estándar (Estado, Cantidad, Dato único)."""
        start_wait = time()
        while (time() - start_wait) < self.timeout:
            with self.serial_lock:
                in_w = self.serial_module.in_waiting if self.serial_module else 0
            if in_w >= bytes_esperados:
                with self.serial_lock:
                    datos = self.serial_module.read(bytes_esperados)
                r_dir = datos[0]
                r_cmd = datos[1]
                
                if r_cmd == 0x01:
                    st = datos[2]
                    cks = datos[3]
                    cks_calc = (r_dir + r_cmd + st) & 0xFF
                    if cks != cks_calc:
                        self.log(f"[{self.log_id}] [ERROR] Checksum inválido en Estado")
                        return None
                    estado_str = "OK" if st == 0x01 else "ERROR"
                    self.log(f"[{self.log_id}] [RESP] Nodo {chr(r_dir)} | Estado: {estado_str}")
                    return st

                elif r_cmd in (0x05, 0x06):
                    h = datos[2]
                    l = datos[3]
                    cks = datos[4]
                    cks_calc = (r_dir + r_cmd + h + l) & 0xFF
                    if cks != cks_calc:
                        self.log(f"[{self.log_id}] [ERROR] Checksum inválido en Datos")
                        return None
                    
                    val = (h << 8) | l
                    if val == 0xE001:
                        self.log(f"[{self.log_id}] [ERROR] Nodo {chr(r_dir)} | SENSOR NO RESPONDE (Timeout Hardware)")
                    elif val == 0xFFFF:
                        self.log(f"[{self.log_id}] [AVISO] Nodo {chr(r_dir)} | ÍNDICE FUERA DE RANGO O MEMORIA VACÍA")
                    else:
                        tipo_msj = "CANTIDAD" if r_cmd == 0x05 else "VALOR"
                        self.log(f"[{self.log_id}] [RESP] Nodo {chr(r_dir)} | {tipo_msj}: {val} mm")
                    return val
            sleep(0.01)

        if self.serial_module:
            with self.serial_lock:
                while self.serial_module.in_waiting:
                    self.serial_module.read()
        self.log(f"[{self.log_id}] [WARNING] >> Error: Timeout esperando respuesta")
        return None

    def recibir_rafaga(self, nodo: int):
        """Recibe una ráfaga de datos o lectura de rangos desde el esclavo."""
        start_wait = time()
        while True:
            with self.serial_lock:
                in_w = self.serial_module.in_waiting if self.serial_module else 0
            if in_w >= 4 or (time() - start_wait) >= 0.5:
                break
            sleep(0.01)

        if in_w >= 4:
            with self.serial_lock:
                cabecera = self.serial_module.read(4)
            r_dir = cabecera[0]
            r_cmd = cabecera[1]
            h_cantidad = cabecera[2]
            l_cantidad = cabecera[3]

            if r_cmd == 0x10 and h_cantidad == 0xEE:
                self.log(f"[{self.log_id}] [WARNING] >> Error: El rango solicitado no existe en el esclavo.")
                return []
            if r_cmd == 0x07 and h_cantidad == 0x00:
                self.log(f"[{self.log_id}] >> Aviso: No hay datos grabados en este nodo.")
                return []

            cantidad = (h_cantidad << 8) | l_cantidad
            resultados = []

            if (r_cmd == 0x07 or r_cmd == 0x10) and cantidad > 0:
                self.log(f"[{self.log_id}] >> Nodo {chr(r_dir)}: Descargando {cantidad} datos...")
                cks_calc = (r_dir + r_cmd + h_cantidad + l_cantidad) & 0xFF

                for i in range(cantidad):
                    byte_wait = time()
                    while True:
                        with self.serial_lock:
                            in_w_bytes = self.serial_module.in_waiting if self.serial_module else 0
                        if in_w_bytes >= 2 or (time() - byte_wait) >= self.timeout:
                            break
                        sleep(0.005)

                    if in_w_bytes >= 2:
                        with self.serial_lock:
                            par = self.serial_module.read(2)
                        h = par[0]
                        l = par[1]
                        cks_calc = (cks_calc + h + l) & 0xFF
                        val = (h << 8) | l
                        resultados.append(val)
                    else:
                        self.log(f"[{self.log_id}] [ERROR] >> Error: Timeout a mitad de la ráfaga.")
                        return []

                cks_wait = time()
                while True:
                    with self.serial_lock:
                        in_w_cks = self.serial_module.in_waiting if self.serial_module else 0
                    if in_w_cks >= 1 or (time() - cks_wait) >= self.timeout:
                        break
                    sleep(0.005)

                if in_w_cks >= 1:
                    with self.serial_lock:
                        cks_rx = self.serial_module.read(1)[0]
                    if cks_rx == cks_calc:
                        self.log(f"[{self.log_id}] >> Descarga completada con éxito (Checksum OK).")
                        return resultados
                    else:
                        self.log(f"[{self.log_id}] [ERROR] >> Error: Checksum ráfaga falló. (Calc: {cks_calc:02X}, Rx: {cks_rx:02X})")
                else:
                    self.log(f"[{self.log_id}] [ERROR] >> Error: Timeout esperando checksum de ráfaga.")
        else:
            self.log(f"[{self.log_id}] [ERROR] >> Error: Timeout esperando encabezado de ráfaga.")
        return []

    def obtener_estado(self, nodo: int):
        self.enviar_orden(nodo, 0x01, 0x00, 0x00, 0x00, 0x00)
        return self.esperar_respuesta(4)

    def borrado_local(self, nodo: int):
        self.enviar_orden(nodo, 0x02, 0x00, 0x00, 0x00, 0x00)
        self.log(f"[{self.log_id}] >> Borrado individual enviado al Nodo {chr(nodo)} (Sin respuesta)")

    def start_global(self):
        """Envía el comando START GLOBAL y activa el evento de alertas tras 1 segundo."""
        self.enviar_orden(0xFF, 0x03, 0x00, 0x00, 0x00, 0x00)
        self.log(f"[{self.log_id}] >> START GLOBAL (Esperando 1s para activar alertas...)")
        
        # Usamos un temporizador en segundo plano para no bloquear el hilo principal
        def activar_con_retraso():
            sleep(1.0)
            # Verificamos opcionalmente si no se ha hecho un stop en ese segundo
            self.evento_adquisicion.set()
            self.log(f"[{self.log_id}] >> Hilo de alertas activado tras el retraso.")

        threading.Thread(target=activar_con_retraso, daemon=True).start()

    def stop_global(self):
        self.enviar_orden(0xFF, 0x04, 0x00, 0x00, 0x00, 0x00)
        # Limpiamos el evento para pausar inmediatamente el hilo de alertas
        self.evento_adquisicion.clear()
        self.log(f"[{self.log_id}] >> STOP GLOBAL")

    def obtener_cantidad(self, nodo: int):
        self.enviar_orden(nodo, 0x05, 0x00, 0x00, 0x00, 0x00)
        return self.esperar_respuesta(5)

    def obtener_dato_unico(self, nodo: int, idx: int):
        h_idx = (idx >> 8) & 0xFF
        l_idx = idx & 0xFF
        self.enviar_orden(nodo, 0x06, h_idx, l_idx, 0x00, 0x00)
        return self.esperar_respuesta(5)

    def obtener_rafaga(self, nodo: int):
        self.enviar_orden(nodo, 0x07, 0x00, 0x00, 0x00, 0x00)
        return self.recibir_rafaga(nodo)

    def borrado_global(self):
        self.enviar_orden(0xFF, 0x08, 0x00, 0x00, 0x00, 0x00)
        self.log(f"[{self.log_id}] >> BORRADO GLOBAL")

    def reinicio_sensor(self, nodo: int):
        self.enviar_orden(nodo, 0x09, 0x00, 0x00, 0x00, 0x00)
        self.log(f"[{self.log_id}] >> Orden de RE-INIT enviada al sensor del Nodo {chr(nodo)} (Sin respuesta)")

    def leer_rango(self, nodo: int, idx: int):
        h_idx = (idx >> 8) & 0xFF
        l_idx = idx & 0xFF
        self.enviar_orden(nodo, 0x10, h_idx, l_idx, 0x00, 0x00)
        return self.recibir_rafaga(nodo)

    def enviar_config_distancia(self, nodo: int, f_val: float):
        f_bytes = struct.pack("<f", f_val)
        self.enviar_orden(nodo, 0x11, f_bytes[3], f_bytes[2], f_bytes[1], f_bytes[0])
        self.log(f"[{self.log_id}] >> Float enviado: {f_val:.4f} al Nodo {chr(nodo)}")

    def obtener_rafagas_completas(self, nodo: int, max_intentos_bloque=3):
        """Obtiene la cantidad total de datos con reintentos y descarga todos los bloques necesarios."""
        cantidad_total = None
        for intento in range(1, max_intentos_bloque + 1):
            cantidad_total = self.obtener_cantidad(nodo)
            if cantidad_total is not None and cantidad_total not in (0xFFFF, 0xE001, 0):
                break
            self.log(f"[{self.log_id}] [WARNING] Reintento {intento}/{max_intentos_bloque} para obtener cantidad del Nodo {chr(nodo)}")
            sleep(0.3)

        if cantidad_total is None or cantidad_total in (0xFFFF, 0xE001, 0):
            self.log(f"[{self.log_id}] [ERROR] No se pudo obtener una cantidad válida de datos para el nodo {hex(nodo)} tras varios intentos.")
            return []
        
        bloques = math.ceil(cantidad_total / 100)
        datos_completos = []

        for idx_bloque in range(bloques):
            bloque_exitoso = False
            for intento in range(1, max_intentos_bloque + 1):
                datos_bloque = self.leer_rango(nodo, idx_bloque)
                if datos_bloque:
                    datos_completos.extend(datos_bloque)
                    bloque_exitoso = True
                    break
                else:
                    sleep(0.2)
            if not bloque_exitoso:
                self.log(f"[{self.log_id}] [ERROR] Falló el bloque {idx_bloque} del Nodo {hex(nodo)} tras {max_intentos_bloque} intentos.")
                break
                
        return datos_completos

    def obtener_todas_las_matrices(self):
        matriz_resultados = {}
        for nodo in self.direcciones_sensores:
            valores_sensor = self.obtener_rafagas_completas(nodo)
            matriz_resultados[nodo] = valores_sensor
        return matriz_resultados

    def obtener_matriz_unificada_sensores(self, max_intentos_bloque=3):
        matriz_datos = {}
        for nodo in self.direcciones_sensores:
            matriz_datos[nodo] = self.obtener_rafagas_completas(nodo, max_intentos_bloque)

        max_longitud = max((len(valores) for valores in matriz_datos.values()), default=0)
        matriz_unificada = []
        for i in range(max_longitud):
            fila = []
            for nodo in self.direcciones_sensores:
                valores = matriz_datos.get(nodo, [])
                if i < len(valores):
                    fila.append(valores[i])
                else:
                    fila.append(float('nan'))
            matriz_unificada.append(fila)
            
        return matriz_datos, matriz_unificada, max_longitud
