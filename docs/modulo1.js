/* ===================================================================
   modulo1.js — Modulo 1: Analisis de Riesgo y Rentabilidad (criterio B)
   =================================================================== */

const ESTADO_MOD1 = {
  periodoSeries: "5A",
  periodoMercado: "1A",
  tickerMercado: null, // se asigna al primer ticker seleccionado
};

const COLORES_SERIE = ["#F0B429", "#4D9EFF", "#00D964", "#FF5C5C", "#B47CFF", "#FF9E4D", "#4DDCFF", "#FF4DA6"];

// ---------------------------------------------------------------------
// PUNTO DE ENTRADA: se llama cuando el modulo se vuelve visible o
// cuando cambia la seleccion de activos (ver app.js -> onCambioSeleccion).
// ---------------------------------------------------------------------
async function refrescarModulo1() {
  const contenedor = document.getElementById("modulo1Contenido");

  if (ESTADO.seleccionados.size === 0) {
    contenedor.innerHTML = `<div class="modulo__placeholder">Selecciona al menos un activo en la barra lateral.</div>`;
    return;
  }

  // Si el ticker elegido para la vista de mercado ya no esta seleccionado,
  // usar el primero de la seleccion actual.
  if (!ESTADO_MOD1.tickerMercado || !ESTADO.seleccionados.has(ESTADO_MOD1.tickerMercado)) {
    ESTADO_MOD1.tickerMercado = Array.from(ESTADO.seleccionados)[0];
  }

  construirEsqueletoModulo1(contenedor);

  await Promise.all([
    cargarSeriesPrecios(),
    cargarScatterRiesgoRendimiento(),
    cargarVistaMercado(),
    cargarTablaIndicadores(),
  ]);
}

// ---------------------------------------------------------------------
// ESQUELETO HTML (se construye una vez; los datos se llenan despues)
// ---------------------------------------------------------------------
function construirEsqueletoModulo1(contenedor) {
  contenedor.innerHTML = `
    <div class="panel">
      <h3 class="panel__titulo">Serie de precios normalizada (base 100)</h3>
      <p class="panel__subtitulo">Compara el desempeño relativo de los activos seleccionados en el período elegido.</p>
      <div class="fila-controles" id="controlesPeriodoSeries"></div>
      <div id="graficoSeries" style="height:380px;"></div>
    </div>

    <div class="panel">
      <h3 class="panel__titulo">Dispersión riesgo-rendimiento (universo completo)</h3>
      <p class="panel__subtitulo">Retorno anualizado vs. volatilidad anualizada · 35 activos, etiquetados por ticker.</p>
      <div id="graficoScatter" style="height:440px;"></div>
    </div>

    <div class="panel">
      <h3 class="panel__titulo">Indicadores de mercado integrados</h3>
      <p class="panel__subtitulo">Precio normalizado vs. benchmark (S&P 500) y volumen de negociación, para un activo a la vez.</p>
      <div class="fila-controles" id="selectorTickerMercado"></div>
      <div class="fila-controles" id="controlesPeriodoMercado"></div>
      <div id="badgeCapitalizacion" style="margin-bottom:12px;"></div>
      <div id="graficoMercado" style="height:420px;"></div>
    </div>

    <div class="panel">
      <h3 class="panel__titulo">Tabla de indicadores de riesgo y rentabilidad</h3>
      <p class="panel__subtitulo">7 indicadores por activo · universo completo (35 activos).</p>
      <div style="overflow-x:auto;">
        <table class="tabla-datos" id="tablaIndicadores"></table>
      </div>
    </div>
  `;

  renderizarBotonesPeriodo("controlesPeriodoSeries", ESTADO_MOD1.periodoSeries, (p) => {
    ESTADO_MOD1.periodoSeries = p;
    cargarSeriesPrecios();
  });

  renderizarBotonesPeriodo("controlesPeriodoMercado", ESTADO_MOD1.periodoMercado, (p) => {
    ESTADO_MOD1.periodoMercado = p;
    cargarVistaMercado();
  });

  renderizarSelectorTickerMercado();
}

function renderizarBotonesPeriodo(idContenedor, periodoActivo, onClick) {
  const periodos = ["3M", "6M", "1A", "3A", "5A"];
  const contenedor = document.getElementById(idContenedor);
  contenedor.innerHTML = periodos
    .map(
      (p) => `<button class="btn-periodo ${p === periodoActivo ? "btn-periodo--activo" : ""}" data-periodo="${p}">${p}</button>`
    )
    .join("");

  contenedor.querySelectorAll(".btn-periodo").forEach((btn) => {
    btn.addEventListener("click", () => {
      contenedor.querySelectorAll(".btn-periodo").forEach((b) => b.classList.remove("btn-periodo--activo"));
      btn.classList.add("btn-periodo--activo");
      onClick(btn.dataset.periodo);
    });
  });
}

function renderizarSelectorTickerMercado() {
  const contenedor = document.getElementById("selectorTickerMercado");
  if (!contenedor) return;
  const tickers = Array.from(ESTADO.seleccionados);

  contenedor.innerHTML =
    `<span class="texto-secundario" style="font-size:11.5px;margin-right:6px;align-self:center;">Activo:</span>` +
    tickers
      .map(
        (tk) =>
          `<button class="btn-periodo ${tk === ESTADO_MOD1.tickerMercado ? "btn-periodo--activo" : ""}" data-ticker="${tk}">${tk}</button>`
      )
      .join("");

  contenedor.querySelectorAll("button[data-ticker]").forEach((btn) => {
    btn.addEventListener("click", () => {
      ESTADO_MOD1.tickerMercado = btn.dataset.ticker;
      contenedor.querySelectorAll("button[data-ticker]").forEach((b) => b.classList.remove("btn-periodo--activo"));
      btn.classList.add("btn-periodo--activo");
      cargarVistaMercado();
    });
  });
}

// ---------------------------------------------------------------------
// GRAFICO 1: SERIES DE PRECIOS NORMALIZADAS
// ---------------------------------------------------------------------
async function cargarSeriesPrecios() {
  const div = document.getElementById("graficoSeries");
  if (!div) return;
  div.innerHTML = `<div class="spinner-carga"><span class="spinner-carga__icono"></span>Calculando series...</div>`;

  try {
    const tickers = Array.from(ESTADO.seleccionados);
    const datos = await llamarAPI(
      `/api/modulo1/series?tickers=${tickers.join(",")}&periodo=${ESTADO_MOD1.periodoSeries}&tipo=precio`
    );

    const trazas = tickers.map((tk, i) => ({
      x: datos.fechas,
      y: datos.series[tk],
      type: "scatter",
      mode: "lines",
      name: tk,
      line: { color: COLORES_SERIE[i % COLORES_SERIE.length], width: 1.8 },
    }));

    div.innerHTML = ""; // limpiar el spinner antes de dibujar el grafico
    Plotly.newPlot(div, trazas, layoutBase({
      yaxis: { title: "Precio normalizado (base 100)" },
      hovermode: "x unified",
    }), opcionesPlotly());
  } catch (error) {
    div.innerHTML = `<div class="mensaje-error">Error al cargar series: ${error.message}</div>`;
  }
}

// ---------------------------------------------------------------------
// GRAFICO 2: SCATTER RIESGO-RENDIMIENTO (universo completo)
// ---------------------------------------------------------------------
async function cargarScatterRiesgoRendimiento() {
  const div = document.getElementById("graficoScatter");
  if (!div) return;
  div.innerHTML = `<div class="spinner-carga"><span class="spinner-carga__icono"></span>Calculando dispersión...</div>`;

  try {
    const datos = await llamarAPI("/api/modulo1/scatter");
    const puntos = datos.puntos;

    const seleccionados = puntos.filter((p) => ESTADO.seleccionados.has(p.ticker));
    const noSeleccionados = puntos.filter((p) => !ESTADO.seleccionados.has(p.ticker));

    const trazaNoSel = {
      x: noSeleccionados.map((p) => p["volatilidad_%"]),
      y: noSeleccionados.map((p) => p["retorno_%"]),
      text: noSeleccionados.map((p) => `${p.ticker} — ${p.nombre}<br>Sector: ${p.sector}`),
      mode: "markers",
      type: "scatter",
      name: "No seleccionados",
      marker: { size: 8, color: "#303850", line: { width: 1, color: "#5C6478" } },
      hovertemplate: "%{text}<br>Vol: %{x:.2f}%<br>Retorno: %{y:.2f}%<extra></extra>",
    };

    const trazaSel = {
      x: seleccionados.map((p) => p["volatilidad_%"]),
      y: seleccionados.map((p) => p["retorno_%"]),
      text: seleccionados.map((p) => p.ticker),
      mode: "markers+text",
      type: "scatter",
      name: "Seleccionados",
      textposition: "top center",
      textfont: { size: 10.5, color: "#F0B429", family: "IBM Plex Mono" },
      marker: { size: 12, color: "#F0B429", line: { width: 1.5, color: "#0B0E14" } },
      hovertemplate: "%{text}<br>Vol: %{x:.2f}%<br>Retorno: %{y:.2f}%<extra></extra>",
    };

    div.innerHTML = "";
    Plotly.newPlot(div, [trazaNoSel, trazaSel], layoutBase({
      xaxis: { title: "Volatilidad anualizada (%)" },
      yaxis: { title: "Retorno anualizado (%)" },
      showlegend: false,
    }), opcionesPlotly());
  } catch (error) {
    div.innerHTML = `<div class="mensaje-error">Error al cargar scatter: ${error.message}</div>`;
  }
}

// ---------------------------------------------------------------------
// GRAFICO 3: INDICADORES DE MERCADO INTEGRADOS (precio + benchmark + volumen)
// ---------------------------------------------------------------------
async function cargarVistaMercado() {
  renderizarSelectorTickerMercado();

  const div = document.getElementById("graficoMercado");
  const badgeDiv = document.getElementById("badgeCapitalizacion");
  if (!div || !ESTADO_MOD1.tickerMercado) return;

  div.innerHTML = `<div class="spinner-carga"><span class="spinner-carga__icono"></span>Cargando datos de mercado...</div>`;

  try {
    const datos = await llamarAPI(
      `/api/modulo1/mercado/${ESTADO_MOD1.tickerMercado}?periodo=${ESTADO_MOD1.periodoMercado}`
    );

    // Badge de capitalizacion (dato puntual, no serie de tiempo)
    const cap = datos.capitalizacion;
    const capTexto = cap.capitalizacion_usd ? fmtUSD(cap.capitalizacion_usd) : "N/D";
    badgeDiv.innerHTML = `
      <span class="badge badge--ambar">${ESTADO_MOD1.tickerMercado}</span>
      <span class="texto-secundario" style="margin-left:8px;font-size:12px;">
        Capitalización / AUM actual: <strong style="color:#E8EAED;">${capTexto}</strong>
        <span style="color:#5C6478;">(${cap.fuente})</span>
      </span>
    `;

    const trazaPrecio = {
      x: datos.fechas,
      y: datos.precio_normalizado,
      type: "scatter",
      mode: "lines",
      name: ESTADO_MOD1.tickerMercado,
      yaxis: "y",
      line: { color: "#F0B429", width: 2 },
    };

    const trazaBenchmark = {
      x: datos.fechas,
      y: datos.benchmark_normalizado,
      type: "scatter",
      mode: "lines",
      name: "S&P 500",
      yaxis: "y",
      line: { color: "#4D9EFF", width: 1.5, dash: "dot" },
    };

    const trazaVolumen = {
      x: datos.fechas,
      y: datos.volumen,
      type: "bar",
      name: "Volumen",
      yaxis: "y2",
      marker: { color: "rgba(139,146,168,0.35)" },
    };

    const layout = layoutBase({
      yaxis: { title: "Precio normalizado (base 100)", domain: [0.32, 1] },
      yaxis2: { title: "Volumen", domain: [0, 0.22], showgrid: false },
      hovermode: "x unified",
      legend: { orientation: "h", y: 1.12 },
    });

    div.innerHTML = "";
    Plotly.newPlot(div, [trazaPrecio, trazaBenchmark, trazaVolumen], layout, opcionesPlotly());
  } catch (error) {
    div.innerHTML = `<div class="mensaje-error">Error al cargar vista de mercado: ${error.message}</div>`;
  }
}

// ---------------------------------------------------------------------
// TABLA DE INDICADORES (criterio A2 / B1)
// ---------------------------------------------------------------------
async function cargarTablaIndicadores() {
  const tabla = document.getElementById("tablaIndicadores");
  if (!tabla) return;
  tabla.innerHTML = `<tr><td><div class="spinner-carga"><span class="spinner-carga__icono"></span>Cargando tabla...</div></td></tr>`;

  try {
    const datos = await llamarAPI("/api/indicadores");
    const filas = datos.indicadores;

    const encabezado = `
      <thead>
        <tr>
          <th>Ticker</th><th>Nombre</th><th>Sector</th>
          <th>Retorno %</th><th>Vol. %</th><th>Sharpe</th><th>Sortino</th>
          <th>Max DD %</th><th>Beta</th><th>CVaR 95%</th>
        </tr>
      </thead>
    `;

    const cuerpo = filas
      .map((f) => {
        const esSeleccionado = ESTADO.seleccionados.has(f.Ticker);
        return `
        <tr style="${esSeleccionado ? "background:rgba(240,180,41,0.06);" : ""}">
          <td><strong style="color:${esSeleccionado ? "#F0B429" : "#E8EAED"};">${f.Ticker}</strong></td>
          <td style="font-family:Inter;font-size:11.5px;color:#8B92A8;">${f.Nombre}</td>
          <td style="font-family:Inter;font-size:11.5px;color:#8B92A8;">${f.Sector}</td>
          <td class="${claseSegunSigno(f["Retorno_Anualizado_%"])}">${fmtPct(f["Retorno_Anualizado_%"])}</td>
          <td>${fmtNum(f["Volatilidad_Anualizada_%"])}%</td>
          <td class="${claseSegunSigno(f["Sharpe_Ratio"])}">${fmtNum(f["Sharpe_Ratio"], 3)}</td>
          <td class="${claseSegunSigno(f["Sortino_Ratio"])}">${fmtNum(f["Sortino_Ratio"], 3)}</td>
          <td class="texto-negativo">${fmtNum(f["Max_Drawdown_%"])}%</td>
          <td>${fmtNum(f["Beta"], 3)}</td>
          <td class="texto-negativo">${fmtNum(f["CVaR_95_%"])}%</td>
        </tr>
      `;
      })
      .join("");

    tabla.innerHTML = encabezado + `<tbody>${cuerpo}</tbody>`;
  } catch (error) {
    tabla.innerHTML = `<tr><td><div class="mensaje-error">Error al cargar tabla: ${error.message}</div></td></tr>`;
  }
}

// ---------------------------------------------------------------------
// HELPERS DE PLOTLY (estilo consistente con el tema oscuro)
// ---------------------------------------------------------------------
function layoutBase(overrides = {}) {
  return Object.assign(
    {
      paper_bgcolor: "transparent",
      plot_bgcolor: "transparent",
      font: { family: "Inter, sans-serif", color: "#8B92A8", size: 11 },
      margin: { l: 55, r: 20, t: 20, b: 45 },
      xaxis: { gridcolor: "#1C2233", zerolinecolor: "#303850" },
      yaxis: { gridcolor: "#1C2233", zerolinecolor: "#303850" },
      legend: { font: { color: "#8B92A8" } },
    },
    overrides
  );
}

function opcionesPlotly() {
  return { responsive: true, displayModeBar: false };
}
