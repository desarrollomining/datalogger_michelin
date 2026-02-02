from flask import Flask, send_file
import os

app = Flask(__name__)
IMAGE_PATH = "/srv/datalogger_michelin/fig.jpg"

@app.route("/")
def index():
    # Devuelve la imagen más reciente
    if os.path.exists(IMAGE_PATH):
        return send_file(IMAGE_PATH, mimetype='image/jpeg')
    else:
        return "Imagen no disponible", 404

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)
