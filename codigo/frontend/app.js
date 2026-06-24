/* ===================================================================
   app.js — Logica principal del dashboard
   Maneja: conexion con la API, seleccion de activos (sidebar),
   navegacion entre modulos (tabs), y orquesta las funciones de
   modulo1.js, modulo2.js, modulo3.js (definidas en archivos separados).
   =================================================================== */

// ---------------------------------------------------------------------
// ESTADO GLOBAL DE LA APLICACION
// ---------------------------------------------------------------------
const ESTADO = {
  universo: [],            // lista completa de activos (desde /api/universo)
  seleccionInicial: [],    // tickers sugeridos al cargar
  seleccionados: new Set(), // tickers actualmente seleccionados por el usuario
  moduloActivo: "1",
};

// ---------------------------------------------------------------------
// HELPERS DE RED
// ---------------------------------------------------------------------
async function llamarAPI(ruta) {
  const url = `${API_BASE_URL}${ruta}`;
  const respuesta = await fetch(url);
  if (!respuesta.ok) {
    const cuerpo = await respuesta.json().catch(() => ({ error: "Error desconocido" }));
    throw new Error(cuerpo.error || `Error HTTP ${respuesta.status}`);
  }
  return respuesta.json();
}

function tickersSeleccionadosCSV() {
  return Array.from(ESTADO.seleccionados).join(",");
}

// ---------------------------------------------------------------------
// FORMATEO
// ---------------------------------------------------------------------
function fmtPct(valor, decimales = 2) {
  if (valor === null || valor === undefined || Number.isNaN(valor)) return "—";
  const signo = valor > 0 ? "+" : "";
  return `${signo}${valor.toFixed(decimales)}%`;
}

function fmtNum(valor, decimales = 2) {
  if (valor === null || valor === undefined || Number.isNaN(valor)) return "—";
  return valor.toFixed(decimales);
}

function fmtUSD(valor) {
  if (valor === null || valor === undefined) return "N/D";
  if (valor >= 1e12) return `$${(valor / 1e12).toFixed(2)}T`;
  if (valor >= 1e9) return `$${(valor / 1e9).toFixed(2)}B`;
  if (valor >= 1e6) return `$${(valor / 1e6).toFixed(2)}M`;
  return `$${valor.toFixed(0)}`;
}

function claseSegunSigno(valor) {
  if (valor === null || valor === undefined || Number.isNaN(valor)) return "texto-secundario";
  return valor >= 0 ? "texto-positivo" : "texto-negativo";
}

// ---------------------------------------------------------------------
// ESTADO DE CONEXION (indicador en el topbar)
// ---------------------------------------------------------------------
function actualizarEstadoConexion(estado, mensaje) {
  const dot = document.getElementById("statusDot");
  const texto = document.getElementById("statusText");
  dot.className = "status-dot";
  if (estado === "ok") dot.classList.add("status-dot--ok");
  if (estado === "error") dot.classList.add("status-dot--error");
  texto.textContent = mensaje;
}

// ---------------------------------------------------------------------
// SIDEBAR: RENDERIZADO DE LA LISTA DE ACTIVOS
// ---------------------------------------------------------------------
function renderizarListaActivos(filtroTexto = "") {
  const contenedor = document.getElementById("listaActivos");
  const filtro = filtroTexto.trim().toLowerCase();

  const activosFiltrados = ESTADO.universo.filter((a) => {
    if (!filtro) return true;
    return (
      a.ticker.toLowerCase().includes(filtro) ||
      a.nombre.toLowerCase().includes(filtro) ||
      a.sector.toLowerCase().includes(filtro) ||
      a.region.toLowerCase().includes(filtro) ||
      a.tipo.toLowerCase().includes(filtro)
    );
  });

  contenedor.innerHTML = "";

  for (const activo of activosFiltrados) {
    const estaSeleccionado = ESTADO.seleccionados.has(activo.ticker);

    const item = document.createElement("div");
    item.className = "activo-item" + (estaSeleccionado ? " activo-item--seleccionado" : "");
    item.dataset.ticker = activo.ticker;

    item.innerHTML = `
      <span class="activo-item__check">${estaSeleccionado ? "✓" : ""}</span>
      <div class="activo-item__info">
        <span class="activo-item__ticker">${activo.ticker}</span>
        <span class="activo-item__meta">${activo.sector} · ${activo.region}</span>
      </div>
      <span class="activo-item__tipo">${activo.tipo}</span>
    `;

    item.addEventListener("click", () => alternarSeleccion(activo.ticker));
    contenedor.appendChild(item);
  }
}

function alternarSeleccion(ticker) {
  if (ESTADO.seleccionados.has(ticker)) {
    ESTADO.seleccionados.delete(ticker);
  } else {
    ESTADO.seleccionados.add(ticker);
  }
  renderizarListaActivos(document.getElementById("filtroActivos").value);
  actualizarContadorSeleccion();
  onCambioSeleccion(); // recalcula modulos 2 y 3 en vivo (criterio C1)
}

function actualizarContadorSeleccion() {
  document.getElementById("contadorSeleccionados").textContent = ESTADO.seleccionados.size;
}

// ---------------------------------------------------------------------
// BOTONES DE LA TOOLBAR DEL SIDEBAR
// ---------------------------------------------------------------------
function configurarBotonesToolbar() {
  document.getElementById("btnSeleccionInicial").addEventListener("click", () => {
    ESTADO.seleccionados = new Set(ESTADO.seleccionInicial);
    renderizarListaActivos(document.getElementById("filtroActivos").value);
    actualizarContadorSeleccion();
    onCambioSeleccion();
  });

  document.getElementById("btnSeleccionarTodos").addEventListener("click", () => {
    ESTADO.seleccionados = new Set(ESTADO.universo.map((a) => a.ticker));
    renderizarListaActivos(document.getElementById("filtroActivos").value);
    actualizarContadorSeleccion();
    onCambioSeleccion();
  });

  document.getElementById("btnLimpiar").addEventListener("click", () => {
    ESTADO.seleccionados.clear();
    renderizarListaActivos(document.getElementById("filtroActivos").value);
    actualizarContadorSeleccion();
    onCambioSeleccion();
  });

  document.getElementById("filtroActivos").addEventListener("input", (e) => {
    renderizarListaActivos(e.target.value);
  });
}

// ---------------------------------------------------------------------
// TABS DE NAVEGACION ENTRE MODULOS
// ---------------------------------------------------------------------
function configurarTabs() {
  const tabs = document.querySelectorAll(".tab");
  tabs.forEach((tab) => {
    tab.addEventListener("click", () => {
      const numModulo = tab.dataset.modulo;
      cambiarModuloActivo(numModulo);
    });
  });
}

function cambiarModuloActivo(numModulo) {
  ESTADO.moduloActivo = numModulo;

  document.querySelectorAll(".tab").forEach((t) => {
    t.classList.toggle("tab--activo", t.dataset.modulo === numModulo);
  });
  document.querySelectorAll(".modulo").forEach((m) => {
    m.classList.toggle("modulo--activo", m.id === `modulo${numModulo}`);
  });

  // Al entrar a un modulo, asegurar que sus graficos esten actualizados
  // con la seleccion actual (por si cambio mientras se veia otro modulo).
  if (numModulo === "1" && typeof refrescarModulo1 === "function") refrescarModulo1();
  if (numModulo === "2" && typeof refrescarModulo2 === "function") refrescarModulo2();
  if (numModulo === "3" && typeof refrescarModulo3 === "function") refrescarModulo3();
}

// ---------------------------------------------------------------------
// REACCION A CAMBIOS DE SELECCION (recalculo en vivo -- criterio C1)
// ---------------------------------------------------------------------
function onCambioSeleccion() {
  // Solo refrescamos el modulo que esta visible en este momento; los
  // demas se refrescan automaticamente al entrar a su tab (ver
  // cambiarModuloActivo). Esto evita trabajo innecesario en segundo plano.
  if (ESTADO.moduloActivo === "1" && typeof refrescarModulo1 === "function") refrescarModulo1();
  if (ESTADO.moduloActivo === "2" && typeof refrescarModulo2 === "function") refrescarModulo2();
  if (ESTADO.moduloActivo === "3" && typeof refrescarModulo3 === "function") refrescarModulo3();
}

// ---------------------------------------------------------------------
// INICIALIZACION
// ---------------------------------------------------------------------
async function inicializarApp() {
  configurarBotonesToolbar();
  configurarTabs();

  try {
    actualizarEstadoConexion("cargando", "Conectando con la API...");
    const datosUniverso = await llamarAPI("/api/universo");

    ESTADO.universo = datosUniverso.activos;
    ESTADO.seleccionInicial = datosUniverso.seleccion_inicial;
    ESTADO.seleccionados = new Set(datosUniverso.seleccion_inicial);

    renderizarListaActivos();
    actualizarContadorSeleccion();
    actualizarEstadoConexion("ok", `Conectado · ${ESTADO.universo.length} activos disponibles`);

    // Disparar la carga inicial de cada modulo
    if (typeof refrescarModulo1 === "function") refrescarModulo1();

  } catch (error) {
    console.error("Error al inicializar la app:", error);
    actualizarEstadoConexion("error", "Sin conexión con la API (¿está corriendo app.py?)");

    document.getElementById("modulo1Contenido").innerHTML = `
      <div class="mensaje-error">
        No se pudo conectar con la API en ${API_BASE_URL}.<br>
        Verifica que el servidor Flask esté corriendo:<br>
        <code>python app.py</code>
      </div>
    `;
  }
}

document.addEventListener("DOMContentLoaded", inicializarApp);
