document.addEventListener('DOMContentLoaded', () => {
    const appContainer = document.getElementById('app');
    
    let heatmapModoProcesado = false; 
    let vehiculoSeleccionado = ''; 
    let posicionSeleccionada = 'FL';       

    appContainer.innerHTML = `
        <div class="container mt-4">
            <h1 class="text-center mb-4 fw-bold" id="app-main-title">
                Monitoreo de Neumáticos
            </h1>
            
            <div class="row g-4 justify-content-center">
                <div class="col-md-5">
                    <div class="card p-3 mb-3 shadow-sm">
                        <label for="input-vehiculo" class="form-label fw-bold">Nombre del Vehículo</label>
                        <input type="text" id="input-vehiculo" class="form-control" placeholder="Ej: CAEX-123" style="text-transform: uppercase;">
                        <small class="text-muted mt-1">Dejar vacío para usar el vehículo ya asignado en el título</small>
                    </div>

                    <div class="card p-3 mb-3 shadow-sm text-center">
                        <h5 class="card-title mb-3 fw-bold">Seleccione neumático a revisar</h5>
                        
                        <div class="d-flex flex-column align-items-center gap-4 my-2">
                            <div class="d-flex justify-content-between gap-5" style="width: 220px;">
                                <button class="btn btn-outline-secondary tire-btn py-2 w-100" data-pos="FL">FL<br><small class="text-uppercase" style="font-size:0.65rem;">Del. Izq</small></button>
                                <button class="btn btn-outline-secondary tire-btn py-2 w-100" data-pos="FR">FR<br><small class="text-uppercase" style="font-size:0.65rem;">Del. Der</small></button>
                            </div>
                            
                            <div class="d-flex justify-content-between w-100 px-2 gap-3">
                                <div class="d-flex gap-1 w-50">
                                    <button class="btn btn-outline-secondary tire-btn py-2 w-100" data-pos="RLO">RLO<br><small style="font-size:0.6rem;">Tras. Izq Ext</small></button>
                                    <button class="btn btn-outline-secondary tire-btn py-2 w-100" data-pos="RLC">RLC<br><small style="font-size:0.6rem;">Tras. Izq Int</small></button>
                                </div>
                                <div class="d-flex gap-1 w-50">
                                    <button class="btn btn-outline-secondary tire-btn py-2 w-100" data-pos="RRO">RRO<br><small style="font-size:0.6rem;">Tras. Der Int</small></button>
                                    <button class="btn btn-outline-secondary tire-btn py-2 w-100" data-pos="RRC">RRC<br><small style="font-size:0.6rem;">Tras. Der Ext</small></button>
                                </div>
                            </div>
                        </div>
                    </div>

                    <div class="mb-3">
                        <button id="btn-asignar" class="btn btn-primary btn-lg w-100 shadow-sm">
                            Asignar
                        </button>
                    </div>

                    <div class="card p-3 shadow-sm bg-light">
                        <h5 class="fw-bold mb-1">Modo Visualización de Datos</h5>
                        <p class="text-muted small mb-3" id="heatmap-status">Datos de última medición</p>
                        <button id="btn-toggle-heatmap" class="btn btn-outline-danger w-100" disabled>
                            Cambiar a Modo Procesado
                        </button>
                    </div>
                </div>

                <div class="col-md-7">
                    <div class="card p-4 h-100 shadow-sm d-flex flex-column">
                        <div class="d-flex justify-content-between align-items-center border-bottom pb-2 mb-3">
                            <h4 class="text-secondary mb-0">Visualización de Telemetría</h4>
                            <span id="db-timestamp" class="badge bg-secondary p-2" style="font-size: 0.75rem;">Sin datos</span>
                        </div>
                        
                        <div id="heatmap-canvas-container" class="border rounded bg-dark position-relative my-auto d-flex align-items-center justify-content-center text-white" style="min-height: 380px;">
                            <div class="text-center p-4" id="canvas-placeholder-text">
                                <p class="mb-1 text-warning fw-bold">Sin datos que mostrar</p>
                                <small class="text-muted">Cargando configuración inicial desde el servidor...</small>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    `;

    const btnToggle = document.getElementById('btn-toggle-heatmap');
    const btnAsignar = document.getElementById('btn-asignar'); 
    const heatmapStatus = document.getElementById('heatmap-status');
    const inputVehiculo = document.getElementById('input-vehiculo');
    const tireButtons = document.querySelectorAll('.tire-btn');
    const dbTimestamp = document.getElementById('db-timestamp');
    const heatmapCanvasContainer = document.getElementById('heatmap-canvas-container');
    const appMainTitle = document.getElementById('app-main-title');

    async function loadInitialConfig() {
        try {
            const response = await fetch('/api/config/current');
            const data = await response.json();
            if (data.status === "success" && data.vehicle) {
                vehiculoSeleccionado = data.vehicle.toUpperCase();
                posicionSeleccionada = data.position;
                
                actualizarTituloVehiculo();
                updateTireButtonsUI();
                fetchHeatmapData(); 
            } else {
                heatmapCanvasContainer.innerHTML = `
                    <div class="text-center p-4 text-muted">
                        <p class="mb-1 fw-bold">Configuración vacía en servidor</p>
                        <small>Por favor ingresa un vehículo en el campo de texto para comenzar.</small>
                    </div>
                `;
            }
        } catch (error) {
            console.error("Error al obtener la configuración inicial:", error);
        }
    }

let heatmapChartInstance = null;

async function fetchHeatmapData() {
    if (!vehiculoSeleccionado) return;

    const modoQuery = heatmapModoProcesado ? 'processed' : 'raw';
    btnToggle.disabled = false; 
    
    try {
        const url = `/api/heatmap/data?mode=${modoQuery}&vehicle=${encodeURIComponent(vehiculoSeleccionado)}&position=${posicionSeleccionada}`;
        const response = await fetch(url);
        const resData = await response.json();
        
        if (heatmapModoProcesado) {
            btnToggle.textContent = "Cambiar a Modo sin procesar";
            btnToggle.className = "btn btn-danger w-100";
            heatmapStatus.innerHTML = `<strong>Modo:</strong> Con Procesamiento`;
        } else {
            btnToggle.textContent = "Cambiar a Modo Procesado";
            btnToggle.className = "btn btn-outline-danger w-100";
            heatmapStatus.innerHTML = `<strong>Modo:</strong> Sin Procesamiento`;
        }

        if (resData.status === "empty" || !resData.data || resData.data.length === 0) {
            dbTimestamp.innerText = "Sin registros";
            heatmapCanvasContainer.innerHTML = `
                <div class="text-center p-4 text-warning">
                    <p class="mb-0 fw-bold">Sin datos en Base de Datos</p>
                    <small class="text-muted">No hay registros para la rueda <strong>${posicionSeleccionada}</strong> en el vehículo <strong>${vehiculoSeleccionado} en las últimas 24 horas</strong>.</small>
                </div>
            `;
            return;
        }

        dbTimestamp.innerText = `ID BD: ${resData.meta.id_database} | ${resData.meta.timestamp}`;

        const todasLasLlaves = Object.keys(resData.data[0]);
        const columnasAExcluir = ['id', 'vehicle', 'wheel', 'timestamp', 'datetime', 'uploaded_mining'];
        
        const sensoresList = todasLasLlaves
            .filter(key => !columnasAExcluir.includes(key))
            .sort((a, b) => {
                const numA = parseInt(a.replace(/\D/g, '')) || 0;
                const numB = parseInt(b.replace(/\D/g, '')) || 0;
                return numA - numB; 
            });

        const chartData = [];
        const medicionesLabels = [];

        resData.data.forEach((fila, indexFila) => {
            const labelMedicion = `M-${indexFila + 1}`;
            medicionesLabels.push(labelMedicion);

            sensoresList.forEach(sensor => {
                const valorNumerico = parseFloat(fila[sensor] ?? 0);
                
                chartData.push({
                    x: labelMedicion,
                    y: String(sensor),
                    v: valorNumerico
                });
            });
        });

        heatmapCanvasContainer.innerHTML = `<canvas id="heatmapChart" style="width: 100%; height: 100%; max-height: 360px;"></canvas>`;
        
        if (heatmapChartInstance) {
            heatmapChartInstance.destroy();
        }

        const MIN_VAL = 0;
        const MAX_VAL = 400;

        const ctx = document.getElementById('heatmapChart').getContext('2d');
        
        heatmapChartInstance = new Chart(ctx, {
            type: 'matrix',
            data: {
                datasets: [{
                    label: 'Telemetría de Neumático',
                    data: chartData,
                    backgroundColor(context) {
                        const item = context.dataset.data[context.dataIndex];
                        if (!item) return 'rgba(0,0,0,0)';
                        
                        const value = Math.max(MIN_VAL, Math.min(MAX_VAL, item.v));
                        const alpha = (value - MIN_VAL) / (MAX_VAL - MIN_VAL);
                        
                        const hue = (1 - alpha) * 120; 
                        return `hsl(${hue}, 90%, 50%)`;
                    },
                    width(context) {
                        const area = context.chart.chartArea;
                        if (!area) return 0;
                        return (area.right - area.left) / medicionesLabels.length - 0.5;
                    },
                    height(context) {
                        const area = context.chart.chartArea;
                        if (!area) return 0;
                        return (area.bottom - area.top) / sensoresList.length - 0.5;
                    }
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { display: false },
                    tooltip: {
                        callbacks: {
                            title() { return 'Lectura de Telemetría'; },
                            label(context) {
                                const entry = context.dataset.data[context.dataIndex];
                                return [
                                    `Muestra: ${entry.x}`,
                                    `Sensor: ${entry.y}`,
                                    `Valor obtenido: ${entry.v.toFixed(2)}`
                                ];
                            }
                        }
                    }
                },
                scales: {
                    x: {
                        type: 'category',
                        labels: medicionesLabels,
                        grid: { display: false },
                        ticks: { color: '#ffffff', font: { size: 9 } }
                    },
                    y: {
                        type: 'category',
                        labels: sensoresList, 
                        grid: { display: false },
                        ticks: { color: '#ffffff', font: { size: 11 } }
                    }
                }
            }
        });

    } catch (error) {
        console.error('Error al mapear la matriz del DataFrame de Pandas:', error);
    }
}

    function updateTireButtonsUI() {
        tireButtons.forEach(btn => {
            if (btn.getAttribute('data-pos') === posicionSeleccionada) {
                btn.className = "btn btn-primary tire-btn py-2 w-100 shadow-sm"; 
            } else {
                btn.className = "btn btn-outline-secondary tire-btn py-2 w-100"; 
            }
        });
    }

    function actualizarTituloVehiculo() {
        if (vehiculoSeleccionado) {
            appMainTitle.textContent = `Monitoreo de Neumáticos — ${vehiculoSeleccionado}`;
        } else {
            appMainTitle.textContent = `Monitoreo de Neumáticos`;
        }
    }

    btnToggle.addEventListener('click', () => {
        heatmapModoProcesado = !heatmapModoProcesado; 
        fetchHeatmapData();
    });

    btnAsignar.addEventListener('click', () => {
        const nuevoValor = inputVehiculo.value.trim().toUpperCase();
        
        if (nuevoValor) {
            vehiculoSeleccionado = nuevoValor;
            actualizarTituloVehiculo();
            inputVehiculo.value = '';
        } else if (!vehiculoSeleccionado) {
            alert("No hay ningún vehículo asignado. Por favor escribe uno.");
            return;
        }
        
        fetchHeatmapData();
    });

    inputVehiculo.addEventListener('input', (e) => {
        const start = e.target.selectionStart;
        e.target.value = e.target.value.toUpperCase();
        e.target.setSelectionRange(start, start);
    });

    tireButtons.forEach(btn => {
        btn.addEventListener('click', (e) => {
            posicionSeleccionada = e.currentTarget.getAttribute('data-pos');
            updateTireButtonsUI();
            
            const nuevoValor = inputVehiculo.value.trim().toUpperCase();
            if (nuevoValor) {
                vehiculoSeleccionado = nuevoValor;
                actualizarTituloVehiculo();
                inputVehiculo.value = '';
            }

            if (vehiculoSeleccionado) {
                fetchHeatmapData();
            }
        });
    });

    updateTireButtonsUI();
    loadInitialConfig();
});