// Configuración
const REFRESH_INTERVAL_MS = 1000; // 1 segundo
const IMAGE_ENDPOINT = "/grafico";

// Contenedor
const app = document.getElementById("app");

// Crear imagen dinámicamente
const img = document.createElement("img");
img.id = "grafico";
img.alt = "Gráfico en tiempo real";
img.className = "img-fluid border rounded shadow";
img.style.maxWidth = "100%";

// Insertar imagen en el DOM
app.appendChild(img);

// Función de actualización
function refreshImage() {
    const timestamp = new Date().getTime();
    img.src = `${IMAGE_ENDPOINT}?t=${timestamp}`;
}

// Primera carga
refreshImage();

// Refresco periódico
setInterval(refreshImage, REFRESH_INTERVAL_MS);
