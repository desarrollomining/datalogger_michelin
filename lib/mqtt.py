import paho.mqtt.client as mqtt
import json
import sys
from time import sleep, time

sys.path.append('/srv/datalogger_michelin/')
from lib.utils import Utils

utils = Utils()
RECV_MSG = ""

def get_credentials():
    credentials = None
    # Try 5 times
    for i in range(5):
        try:
            
            with open('/dev/shm/credentials.json') as f:
                config = json.load(f)
            credentials = {}
            for x in config["data"]:
                attr = x.get("attributes", {})
                value = attr["Value"]
                
                if attr["Name"] == "MQTT username":
                    credentials["username"] = value
                elif attr["Name"] == "MQTT password":
                    credentials["password"] = value
                elif attr["Name"] == "MQTT broker":
                    credentials["broker"] = value
                elif attr["Name"] == "MQTT port":
                    credentials["port"] = int(value)
                    
            required_keys = ["username", "password", "broker", "port"]
            if all(k in credentials and credentials[k] is not None for k in required_keys):
                print(f"Credenciales cargadas exitosamente en el intento {i+1}")
                return credentials
            else:
                print(f"Intento {i+1}: JSON leído pero faltan campos requeridos.")
        except:
            utils.traceback()
            
        sleep(1)

    return credentials

# Metodo para conectarse al broker
def connect():
    try:
        credentials = get_credentials()
        if credentials:
            # Inicializar cliente MQTT
            client = mqtt.Client()
            client.username_pw_set(credentials.get("username"), credentials.get("password"))
            client.on_connect = on_connect
            client.on_message = on_message

            # Conectar al broker MQTT
            client.connect(credentials.get("broker"), credentials.get("port"), 60)

            # Bucle de espera de mensajes
            client.loop_start()
            sleep(1)

            return client

    except:
        utils.traceback()
    return None


# Metodo para puclicar al topico
def publish(client, topic, dict_data):
    success = False
    try:
        (rc, mid) = client.publish(topic, json.dumps(dict_data), qos=1)
        if rc != 0:
            print(f"Error al enviar mensaje con codigo de error {rc}")
        else:
            print("Mensaje enviado")
            success = True
            
    except Exception as Ex:
        utils.traceback()
    
    return success


# Metodo de callback cuando se recibe un mensaje MQTT
def on_message(client, userdata, msg):
    global RECV_MSG
    try:
        topic = msg.topic
        payload = msg.payload.decode()
        print(f"Mensaje recibido en {topic}: {payload}")
        RECV_MSG = payload
    except Exception as e:
        print(f"Error en el procesamiento del mensaje MQTT: {e}")


# Metodo de conexión MQTT
def on_connect(client, userdata, flags, rc):
    if rc == 0:
        print("Conexión exitosa al broker MQTT")
    else:
        print(f"Error al conectar, código de error: {rc}")


# Metodo para obtener la respuesta del server al publicar un dato    
def get_response(wait = 5):
    global RECV_MSG
    try:
        ts = time()
        while time()-ts<wait:
            if RECV_MSG:
                msg = json.loads(RECV_MSG)
                RECV_MSG = ""
                return msg
    except Exception as e:
        print(f"Error al obtener la respuesta: {e}")
    return RECV_MSG

# Metodo para hacer un check si mqtt aun sigue conectado         
def is_alive(client):
    if client:
        if client.is_connected(): return True
    return False