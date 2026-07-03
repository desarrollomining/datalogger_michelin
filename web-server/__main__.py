import os
import sys
import json
from flask import Flask, render_template, jsonify, request

sys.path.append('/srv/datalogger_michelin/')
from database.models import Database

app = Flask(__name__)

db = Database(log_id="FLASK_BACKEND")

CONFIG_PATH = "/srv/datalogger_michelin/config_michelin.json"

def update_michelin_config(vehicle, wheel):
    """
    Lee el archivo config_michelin.json, modifica los parámetros 
    VEHICLE y WHEEL bajo el nodo LOCATION, y vuelve a guardar el archivo.
    """
    try:
        if os.path.exists(CONFIG_PATH):
            with open(CONFIG_PATH, 'r') as f:
                config_data = json.load(f)
            
            if "LOCATION" not in config_data:
                config_data["LOCATION"] = {}
                
            config_data["LOCATION"]["VEHICLE"] = vehicle
            config_data["LOCATION"]["WHEEL"] = wheel
            
            with open(CONFIG_PATH, 'w') as f:
                json.dump(config_data, f, indent=4)
                
            print(f"[CONFIG] Archivo json actualizado con Éxito. VEHICLE: {vehicle}, WHEEL: {wheel}")
        else:
            print(f"[ERROR CONFIG] No se encontró el archivo en {CONFIG_PATH}")
    except Exception as e:
        print(f"[ERROR CONFIG] Falló la actualización del archivo JSON: {str(e)}")


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/api/heatmap/data')
def get_heatmap_data():
    """
    Recupera directamente el último dato de las últimas 24h filtrado por SQL,
    sincroniza la configuración y devuelve el mapa de calor.
    """
    mode = request.args.get('mode', 'raw')
    vehicle = request.args.get('vehicle', '').strip()
    position = request.args.get('position', '').strip()  

    if vehicle and position:
        update_michelin_config(vehicle, position)
    else:
        return jsonify({
            "status": "error",
            "message": "Faltan parámetros requeridos: vehicle y position."
        }), 400

    try:
        rows, col_names = db.get_latest_wheel_data(table_type=mode, vehicle=vehicle, wheel=position)

        if not rows:
            return jsonify({
                "status": "empty",
                "meta": {"mode": mode, "vehicle": vehicle, "position": position},
                "message": f"No se tomaron datos recientes (últimas 24h) para el camión {vehicle} en la rueda {position}."
            })

        target_record = dict(zip(col_names, rows[0]))

        raw_packet = target_record.get('packet_data', '[]')
        try:
            heatmap_points = json.loads(raw_packet)
        except (json.JSONDecodeError, TypeError):
            heatmap_points = [{"info": raw_packet, "note": "Formato de celda antiguo o inválido"}]

        return jsonify({
            "status": "success",
            "meta": {
                "id_database": target_record.get('id'),
                "vehicle": target_record.get('vehicle'),
                "position": target_record.get('wheel'),
                "timestamp": target_record.get('datetime'),
                "mode": "Con Procesamiento" if mode == 'processed' else "Sin Procesamiento (Raw)"
            },
            "data": heatmap_points
        })

    except Exception as e:
        return jsonify({
            "status": "error",
            "message": f"Error interno del servidor backend: {str(e)}"
        }), 500

@app.route('/api/config/current')
def get_current_config():
    """Devuelve la configuración actual de VEHICLE y WHEEL desde el JSON."""
    try:
        if os.path.exists(CONFIG_PATH):
            with open(CONFIG_PATH, 'r') as f:
                config_data = json.load(f)
            location = config_data.get("LOCATION", {})
            return jsonify({
                "status": "success",
                "vehicle": location.get("VEHICLE", ""),
                "position": location.get("WHEEL", "FL")
            })
        return jsonify({"status": "error", "message": "Archivo no encontrado"}), 404
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)