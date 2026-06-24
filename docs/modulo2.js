/* ===================================================================
   modulo2.js — Modulo 2: Optimizacion de Portafolios (criterio C)
   =================================================================== */

// ---------------------------------------------------------------------
// PUNTO DE ENTRADA
// ---------------------------------------------------------------------
async function refrescarModulo2() {
  const contenedor = document.getElementById("modulo2Contenido");

  if (ESTADO.seleccionados.size < 2) {
    contenedor.innerHTML = `
      <div class="modulo__placeholder">
        Selecciona al menos 2 activos en la barra lateral para calcular la
        Frontera Eficiente (criterio C1: la herramienta recalcula todo en vivo).
      </div>`;
    return;
  }

  construirEsqueletoModulo2(contenedor);

  // Las llamadas son independientes entre si y corren en paralelo para
  // minimizar el tiempo de espera al cambiar la seleccion (criterio C1).
  await Promise.all([
    cargarCorrelaciones(),
    cargarOptimizacionCompleta(), // alimenta frontera, CML, tarjetas y tabla de pesos
  ]);
}

// ---------------------------------------------------------------------
// ESQUELETO HTML
// ---------------------------------------------------------------------
function construirEsqueletoModulo2(contenedor) {
  contenedor.innerHTML = `
    <div class="grid-metricas" id="tarjetasPortafolios"></div>

    <div class="panel">
      <h3 class="panel__titulo">Matriz de correlaciones</h3>
      <p class="panel__subtitulo">Correlación entre los retornos diarios de los activos seleccionados. Pasa el cursor para ver el valor exacto.</p>
      <div id="graficoHeatmap" style="height:440px;"></div>
    </div>

    <div class="panel">
      <h3 class="panel__titulo">Frontera Eficiente y Línea del Mercado de Capitales (CML)</h3>
      <p class="panel__subtitulo">Optimización formal (scipy.optimize, restricción long-only) · mínima varianza y portafolio tangente marcados.</p>
      <div id="graficoFrontera" style="height:480px;"></div>
    </div>

    <div class="panel">
      <h3 class="panel__titulo">Pesos óptimos de asignación</h3>
      <p class="panel__subtitulo">Comparación de pesos entre el portafolio de mínima varianza y el portafolio tangente (máximo Sharpe).</p>
      <div id="graficoPesos" style="height:380px; margin-bottom: 20px;"></div>
      <div style="overflow-x:auto;">
        <table class="tabla-datos" id="tablaPesos"></table>
      </div>
    </div>
  `;
}

// ---------------------------------------------------------------------
// HEATMAP DE CORRELACIONES (criterio C2)
// ---------------------------------------------------------------------
async function cargarCorrelaciones() {
  const div = document.getElementById("graficoHeatmap");
  if (!div) return;
  div.innerHTML = `<div class="spinner-carga"><span class="spinner-carga__icono"></span>Calculando correlaciones...</div>`;

  try {
    const tickers = Array.from(ESTADO.seleccionados);
    const datos = await llamarAPI(`/api/modulo2/correlaciones?tickers=${tickers.join(",")}`);
    const n = datos.tickers.length;

    // Con pocos activos, las etiquetas inclinadas a -45 se leen bien.
    // Con muchos activos (universo completo, 30+), el espacio por columna
    // se reduce demasiado y el texto rotado se superpone; en ese caso usamos
    // rotacion vertical (-90) y fuente mas pequenia para mantener legibilidad.
    const muchosActivos = n > 18;
    const anguloEtiquetas = muchosActivos ? -90 : -45;
    const tamanioFuente = muchosActivos ? 9 : 11;
    const margenSuperior = muchosActivos ? 90 : 60;
    const alturaGrafico = Math.max(440, n * 24);

    div.style.height = `${alturaGrafico}px`;

    const traza = {
      x: datos.tickers,
      y: datos.tickers,
      z: datos.matriz,
      type: "heatmap",
      colorscale: [
        [0, "#FF5C5C"],
        [0.5, "#161B28"],
        [1, "#00D964"],
      ],
      zmin: -1,
      zmax: 1,
      hovertemplate: "%{y} vs %{x}<br>Correlación: %{z:.3f}<extra></extra>",
      colorbar: { title: "Correlación", titlefont: { color: "#8B92A8" }, tickfont: { color: "#8B92A8" } },
    };

    div.innerHTML = "";
    Plotly.newPlot(div, [traza], layoutBase({
      margin: { l: 70, r: 20, t: margenSuperior, b: 20 },
      xaxis: {
        side: "top",
        tickangle: anguloEtiquetas,
        tickfont: { size: tamanioFuente, family: "IBM Plex Mono" },
        automargin: true,
      },
      yaxis: {
        autorange: "reversed",
        tickfont: { size: tamanioFuente, family: "IBM Plex Mono" },
        automargin: true,
      },
    }), opcionesPlotly());
  } catch (error) {
    div.innerHTML = `<div class="mensaje-error">Error al cargar correlaciones: ${error.message}</div>`;
  }
}

// ---------------------------------------------------------------------
// OPTIMIZACION COMPLETA: tarjetas + frontera + CML + tabla/grafico pesos
// (criterios C1, C4, C5)
// ---------------------------------------------------------------------
async function cargarOptimizacionCompleta() {
  const divFrontera = document.getElementById("graficoFrontera");
  const divTarjetas = document.getElementById("tarjetasPortafolios");
  if (!divFrontera) return;

  divFrontera.innerHTML = `<div class="spinner-carga"><span class="spinner-carga__icono"></span>Optimizando portafolio (Markowitz)...</div>`;
  divTarjetas.innerHTML = "";

  try {
    const tickers = Array.from(ESTADO.seleccionados);
    const datos = await llamarAPI(`/api/modulo2/optimizacion?tickers=${tickers.join(",")}&n_puntos=40`);

    renderizarTarjetasPortafolios(datos);
    renderizarGraficoFrontera(datos);
    renderizarGraficoPesos(datos);
    renderizarTablaPesos(datos);
  } catch (error) {
    divFrontera.innerHTML = `<div class="mensaje-error">Error al optimizar portafolio: ${error.message}</div>`;
  }
}

function renderizarTarjetasPortafolios(datos) {
  const div = document.getElementById("tarjetasPortafolios");
  const mv = datos.minima_varianza;
  const tg = datos.tangente;

  div.innerHTML = `
    <div class="tarjeta-metrica">
      <div class="tarjeta-metrica__label">Mín. Varianza · Retorno</div>
      <div class="tarjeta-metrica__valor ${claseSegunSigno(mv["retorno_%"])}">${fmtPct(mv["retorno_%"])}</div>
    </div>
    <div class="tarjeta-metrica">
      <div class="tarjeta-metrica__label">Mín. Varianza · Volatilidad</div>
      <div class="tarjeta-metrica__valor">${fmtNum(mv["volatilidad_%"])}%</div>
    </div>
    <div class="tarjeta-metrica">
      <div class="tarjeta-metrica__label">Tangente · Retorno</div>
      <div class="tarjeta-metrica__valor tarjeta-metrica__valor--destacado">${fmtPct(tg["retorno_%"])}</div>
    </div>
    <div class="tarjeta-metrica">
      <div class="tarjeta-metrica__label">Tangente · Volatilidad</div>
      <div class="tarjeta-metrica__valor">${fmtNum(tg["volatilidad_%"])}%</div>
    </div>
    <div class="tarjeta-metrica">
      <div class="tarjeta-metrica__label">Sharpe del Tangente</div>
      <div class="tarjeta-metrica__valor tarjeta-metrica__valor--destacado">${fmtNum(tg["sharpe"], 3)}</div>
    </div>
  `;
}

function renderizarGraficoFrontera(datos) {
  const div = document.getElementById("graficoFrontera");
  const mv = datos.minima_varianza;
  const tg = datos.tangente;

  const trazaFrontera = {
    x: datos.frontera_eficiente["volatilidades_%"],
    y: datos.frontera_eficiente["retornos_%"],
    type: "scatter",
    mode: "lines",
    name: "Frontera Eficiente",
    line: { color: "#4D9EFF", width: 2.5 },
    hovertemplate: "Vol: %{x:.2f}%<br>Retorno: %{y:.2f}%<extra>Frontera</extra>",
  };

  const trazaCML = {
    x: datos.cml["volatilidades_%"],
    y: datos.cml["retornos_%"],
    type: "scatter",
    mode: "lines",
    name: "CML",
    line: { color: "#B47CFF", width: 2, dash: "dash" },
    hovertemplate: "Vol: %{x:.2f}%<br>Retorno: %{y:.2f}%<extra>CML</extra>",
  };

  const trazaMinVar = {
    x: [mv["volatilidad_%"]],
    y: [mv["retorno_%"]],
    type: "scatter",
    mode: "markers+text",
    name: "Mínima Varianza",
    text: ["Mín. Varianza"],
    textposition: "bottom center",
    textfont: { size: 11, color: "#00D964", family: "IBM Plex Mono" },
    marker: { size: 14, color: "#00D964", symbol: "diamond", line: { width: 1.5, color: "#0B0E14" } },
    hovertemplate: "Mín. Varianza<br>Vol: %{x:.2f}%<br>Retorno: %{y:.2f}%<extra></extra>",
  };

  const trazaTangente = {
    x: [tg["volatilidad_%"]],
    y: [tg["retorno_%"]],
    type: "scatter",
    mode: "markers+text",
    name: "Tangente (Máx. Sharpe)",
    text: ["Tangente"],
    textposition: "top center",
    textfont: { size: 11, color: "#F0B429", family: "IBM Plex Mono" },
    marker: { size: 14, color: "#F0B429", symbol: "star", line: { width: 1.5, color: "#0B0E14" } },
    hovertemplate: `Tangente (Máx. Sharpe)<br>Vol: %{x:.2f}%<br>Retorno: %{y:.2f}%<br>Sharpe: ${fmtNum(tg.sharpe, 3)}<extra></extra>`,
  };

  const trazaRf = {
    x: [0],
    y: [datos.cml["rf_%"]],
    type: "scatter",
    mode: "markers+text",
    name: "Tasa libre de riesgo",
    text: ["rf"],
    textposition: "middle left",
    textfont: { size: 10, color: "#8B92A8" },
    marker: { size: 9, color: "#8B92A8", symbol: "circle" },
    hovertemplate: `Tasa libre de riesgo: ${fmtNum(datos.cml["rf_%"])}%<extra></extra>`,
  };

  div.innerHTML = "";
  Plotly.newPlot(
    div,
    [trazaFrontera, trazaCML, trazaRf, trazaMinVar, trazaTangente],
    layoutBase({
      xaxis: { title: "Volatilidad anualizada (%)", rangemode: "tozero" },
      yaxis: { title: "Retorno esperado anualizado (%)" },
      legend: { orientation: "h", y: -0.18 },
    }),
    opcionesPlotly()
  );
}

function renderizarGraficoPesos(datos) {
  const div = document.getElementById("graficoPesos");
  const tabla = datos.tabla_pesos;

  const tickers = tabla.map((f) => f.Ticker);
  const pesosMV = tabla.map((f) => f["Peso_Minima_Varianza_%"]);
  const pesosTg = tabla.map((f) => f["Peso_Tangente_%"]);

  const trazaMV = {
    x: tickers,
    y: pesosMV,
    type: "bar",
    name: "Mínima Varianza",
    marker: { color: "#00D964" },
  };

  const trazaTg = {
    x: tickers,
    y: pesosTg,
    type: "bar",
    name: "Tangente",
    marker: { color: "#F0B429" },
  };

  div.innerHTML = "";
  Plotly.newPlot(div, [trazaMV, trazaTg], layoutBase({
    barmode: "group",
    yaxis: { title: "Peso asignado (%)" },
    legend: { orientation: "h", y: -0.2 },
  }), opcionesPlotly());
}

function renderizarTablaPesos(datos) {
  const tabla = document.getElementById("tablaPesos");
  const filas = datos.tabla_pesos;

  const encabezado = `
    <thead>
      <tr>
        <th>Ticker</th>
        <th>Peso Mín. Varianza %</th>
        <th>Peso Tangente %</th>
      </tr>
    </thead>
  `;

  const cuerpo = filas
    .map(
      (f) => `
      <tr>
        <td><strong style="color:#F0B429;">${f.Ticker}</strong></td>
        <td class="${f["Peso_Minima_Varianza_%"] > 0 ? "texto-positivo" : "texto-secundario"}">${fmtNum(f["Peso_Minima_Varianza_%"])}%</td>
        <td class="${f["Peso_Tangente_%"] > 0 ? "texto-destacado" : "texto-secundario"}">${fmtNum(f["Peso_Tangente_%"])}%</td>
      </tr>
    `
    )
    .join("");

  // Fila de totales (control de calidad visible para el usuario / evaluador)
  const sumaMV = filas.reduce((acc, f) => acc + f["Peso_Minima_Varianza_%"], 0);
  const sumaTg = filas.reduce((acc, f) => acc + f["Peso_Tangente_%"], 0);
  const filaTotal = `
    <tr style="border-top: 2px solid #303850;">
      <td><strong>TOTAL</strong></td>
      <td><strong>${fmtNum(sumaMV)}%</strong></td>
      <td><strong>${fmtNum(sumaTg)}%</strong></td>
    </tr>
  `;

  tabla.innerHTML = encabezado + `<tbody>${cuerpo}${filaTotal}</tbody>`;
}
