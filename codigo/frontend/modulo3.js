/* ===================================================================
   modulo3.js — Modulo 3: Modelos de Valoracion de Activos (criterio D)
   =================================================================== */

   const ESTADO_MOD3 = {
    tickerRegresion: null, // activo elegido para ver su regresion OLS individual
  };
  
  // ---------------------------------------------------------------------
  // PUNTO DE ENTRADA
  // ---------------------------------------------------------------------
  async function refrescarModulo3() {
    const contenedor = document.getElementById("modulo3Contenido");
  
    if (ESTADO.seleccionados.size === 0) {
      contenedor.innerHTML = `<div class="modulo__placeholder">Selecciona al menos un activo en la barra lateral.</div>`;
      return;
    }
  
    if (!ESTADO_MOD3.tickerRegresion || !ESTADO.seleccionados.has(ESTADO_MOD3.tickerRegresion)) {
      ESTADO_MOD3.tickerRegresion = Array.from(ESTADO.seleccionados)[0];
    }
  
    construirEsqueletoModulo3(contenedor);
  
    await Promise.all([
      cargarRegresionBeta(),
      cargarSML(),
      cargarTablaComparativa(),
    ]);
  }
  
  // ---------------------------------------------------------------------
  // ESQUELETO HTML
  // ---------------------------------------------------------------------
  function construirEsqueletoModulo3(contenedor) {
    contenedor.innerHTML = `
      <div class="panel">
        <h3 class="panel__titulo">D1 · Estimación de Beta por Regresión OLS</h3>
        <p class="panel__subtitulo">Retorno del activo vs. retorno del benchmark (S&P 500), con recta de regresión ajustada.</p>
        <div class="fila-controles" id="selectorTickerRegresion"></div>
        <div class="grid-metricas" id="tarjetasRegresion"></div>
        <div id="graficoRegresion" style="height:420px;"></div>
      </div>
  
      <div class="panel">
        <h3 class="panel__titulo">D2 · Línea del Mercado de Títulos (SML) y Alfa de Jensen</h3>
        <p class="panel__subtitulo">Posición de los activos seleccionados respecto al CAPM (sobre la SML = subvalorado, bajo la SML = sobrevalorado).</p>
        <div id="datosSML" style="margin-bottom:12px;"></div>
        <div id="graficoSML" style="height:440px;"></div>
      </div>
  
      <div class="panel">
        <h3 class="panel__titulo">D3 · Tabla Comparativa: CAPM vs. Rendimiento Histórico</h3>
        <p class="panel__subtitulo">Rendimiento esperado según CAPM vs. histórico observado, con indicadores de riesgo histórico.</p>
        <div style="overflow-x:auto;">
          <table class="tabla-datos" id="tablaComparativa"></table>
        </div>
      </div>
    `;
  
    renderizarSelectorTickerRegresion();
  }
  
  function renderizarSelectorTickerRegresion() {
    const contenedor = document.getElementById("selectorTickerRegresion");
    if (!contenedor) return;
    const tickers = Array.from(ESTADO.seleccionados);
  
    contenedor.innerHTML =
      `<span class="texto-secundario" style="font-size:11.5px;margin-right:6px;align-self:center;">Activo:</span>` +
      tickers
        .map(
          (tk) =>
            `<button class="btn-periodo ${tk === ESTADO_MOD3.tickerRegresion ? "btn-periodo--activo" : ""}" data-ticker="${tk}">${tk}</button>`
        )
        .join("");
  
    contenedor.querySelectorAll("button[data-ticker]").forEach((btn) => {
      btn.addEventListener("click", () => {
        ESTADO_MOD3.tickerRegresion = btn.dataset.ticker;
        contenedor.querySelectorAll("button[data-ticker]").forEach((b) => b.classList.remove("btn-periodo--activo"));
        btn.classList.add("btn-periodo--activo");
        cargarRegresionBeta();
      });
    });
  }
  
  // ---------------------------------------------------------------------
  // D1: REGRESION OLS — BETA, R^2, SCATTER + RECTA
  // ---------------------------------------------------------------------
  async function cargarRegresionBeta() {
    renderizarSelectorTickerRegresion();
  
    const div = document.getElementById("graficoRegresion");
    const divTarjetas = document.getElementById("tarjetasRegresion");
    if (!div || !ESTADO_MOD3.tickerRegresion) return;
  
    div.innerHTML = `<div class="spinner-carga"><span class="spinner-carga__icono"></span>Estimando regresión OLS...</div>`;
    divTarjetas.innerHTML = "";
  
    try {
      const datos = await llamarAPI(`/api/modulo3/regresion/${ESTADO_MOD3.tickerRegresion}`);
  
      const significativo = datos.p_value_beta < 0.05;
      divTarjetas.innerHTML = `
        <div class="tarjeta-metrica">
          <div class="tarjeta-metrica__label">Beta (OLS)</div>
          <div class="tarjeta-metrica__valor tarjeta-metrica__valor--destacado">${fmtNum(datos.beta, 3)}</div>
        </div>
        <div class="tarjeta-metrica">
          <div class="tarjeta-metrica__label">R² (bondad de ajuste)</div>
          <div class="tarjeta-metrica__valor">${fmtNum(datos.r_cuadrado * 100, 1)}%</div>
        </div>
        <div class="tarjeta-metrica">
          <div class="tarjeta-metrica__label">N observaciones</div>
          <div class="tarjeta-metrica__valor">${datos.n_observaciones}</div>
        </div>
        <div class="tarjeta-metrica">
          <div class="tarjeta-metrica__label">Significancia del Beta</div>
          <div class="tarjeta-metrica__valor" style="font-size:14px;">
            <span class="badge ${significativo ? "badge--verde" : "badge--rojo"}">
              ${significativo ? "Significativo (p < 0.05)" : "No significativo"}
            </span>
          </div>
        </div>
      `;
  
      const trazaPuntos = {
        x: datos.dispersion.puntos_x,
        y: datos.dispersion.puntos_y,
        mode: "markers",
        type: "scatter",
        name: "Retornos mensuales",
        marker: { size: 4, color: "rgba(77,158,255,0.45)" },
        hovertemplate: "Benchmark: %{x:.2f}%<br>Activo: %{y:.2f}%<extra></extra>",
      };
  
      const trazaRecta = {
        x: datos.dispersion.recta_x,
        y: datos.dispersion.recta_y,
        mode: "lines",
        type: "scatter",
        name: `Recta OLS (β = ${fmtNum(datos.beta, 3)})`,
        line: { color: "#F0B429", width: 2.5 },
      };
  
      div.innerHTML = "";
      Plotly.newPlot(div, [trazaPuntos, trazaRecta], layoutBase({
        xaxis: { title: "Retorno mensual del benchmark (%)" },
        yaxis: { title: `Retorno mensual de ${ESTADO_MOD3.tickerRegresion} (%)` },
        legend: { orientation: "h", y: -0.18 },
      }), opcionesPlotly());
    } catch (error) {
      div.innerHTML = `<div class="mensaje-error">Error al calcular regresión: ${error.message}</div>`;
    }
  }
  
  // ---------------------------------------------------------------------
  // D2: SML Y ALFA DE JENSEN
  // ---------------------------------------------------------------------
  async function cargarSML() {
    const div = document.getElementById("graficoSML");
    const divDatos = document.getElementById("datosSML");
    if (!div) return;
  
    div.innerHTML = `<div class="spinner-carga"><span class="spinner-carga__icono"></span>Calculando SML...</div>`;
  
    try {
      const tickers = Array.from(ESTADO.seleccionados);
      const datos = await llamarAPI(`/api/modulo3/sml?tickers=${tickers.join(",")}`);
  
      divDatos.innerHTML = `
        <span class="badge badge--azul">rf: ${fmtNum(datos["rf_%"])}%</span>
        <span class="badge badge--azul" style="margin-left:6px;">Retorno mercado esperado: ${fmtNum(datos["retorno_mercado_esperado_%"])}%</span>
        <span class="badge badge--ambar" style="margin-left:6px;">Prima de riesgo: ${fmtNum(datos["prima_riesgo_mercado_%"])}%</span>
      `;
  
      const trazaSML = {
        x: datos.sml.betas,
        y: datos.sml["retornos_esperados_%"],
        type: "scatter",
        mode: "lines",
        name: "SML (CAPM)",
        line: { color: "#4D9EFF", width: 2.5 },
      };
  
      const activos = datos.activos;
      const sobreSML = activos.filter((a) => a["Alfa_Jensen_%"] > 0);
      const bajoSML = activos.filter((a) => a["Alfa_Jensen_%"] <= 0);
  
      const trazaSobre = {
        x: sobreSML.map((a) => a.Beta),
        y: sobreSML.map((a) => a["Retorno_Real_%"]),
        text: sobreSML.map((a) => a.Ticker),
        mode: "markers+text",
        type: "scatter",
        name: "Sobre la SML (subvalorado)",
        textposition: "top center",
        textfont: { size: 10.5, color: "#00D964", family: "IBM Plex Mono" },
        marker: { size: 11, color: "#00D964", line: { width: 1.5, color: "#0B0E14" } },
        hovertemplate: "%{text}<br>Beta: %{x:.3f}<br>Retorno real: %{y:.2f}%<extra></extra>",
      };
  
      const trazaBajo = {
        x: bajoSML.map((a) => a.Beta),
        y: bajoSML.map((a) => a["Retorno_Real_%"]),
        text: bajoSML.map((a) => a.Ticker),
        mode: "markers+text",
        type: "scatter",
        name: "Bajo la SML (sobrevalorado)",
        textposition: "bottom center",
        textfont: { size: 10.5, color: "#FF5C5C", family: "IBM Plex Mono" },
        marker: { size: 11, color: "#FF5C5C", line: { width: 1.5, color: "#0B0E14" } },
        hovertemplate: "%{text}<br>Beta: %{x:.3f}<br>Retorno real: %{y:.2f}%<extra></extra>",
      };
  
      div.innerHTML = "";
      Plotly.newPlot(div, [trazaSML, trazaSobre, trazaBajo], layoutBase({
        xaxis: { title: "Beta" },
        yaxis: { title: "Retorno (%)" },
        legend: { orientation: "h", y: -0.18 },
      }), opcionesPlotly());
    } catch (error) {
      div.innerHTML = `<div class="mensaje-error">Error al calcular SML: ${error.message}</div>`;
    }
  }
  
  // ---------------------------------------------------------------------
  // D3: TABLA COMPARATIVA CAPM VS. HISTORICO
  // ---------------------------------------------------------------------
  async function cargarTablaComparativa() {
    const tabla = document.getElementById("tablaComparativa");
    if (!tabla) return;
    tabla.innerHTML = `<tr><td><div class="spinner-carga"><span class="spinner-carga__icono"></span>Cargando comparativa...</div></td></tr>`;
  
    try {
      const tickers = Array.from(ESTADO.seleccionados);
      const datos = await llamarAPI(`/api/modulo3/comparativa?tickers=${tickers.join(",")}`);
      const filas = datos.comparativa;
  
      const encabezado = `
        <thead>
          <tr>
            <th>Ticker</th><th>Beta OLS</th><th>R²</th>
            <th>Retorno Histórico %</th><th>Retorno CAPM %</th><th>Diferencia %</th>
            <th>Volatilidad %</th><th>Max Drawdown %</th>
          </tr>
        </thead>
      `;
  
      const cuerpo = filas
        .map(
          (f) => `
          <tr>
            <td><strong style="color:#F0B429;">${f.Ticker}</strong></td>
            <td>${fmtNum(f.Beta_OLS, 3)}</td>
            <td>${fmtNum(f.R2 * 100, 1)}%</td>
            <td class="${claseSegunSigno(f["Retorno_Historico_%"])}">${fmtPct(f["Retorno_Historico_%"])}</td>
            <td>${fmtPct(f["Retorno_CAPM_%"])}</td>
            <td class="${claseSegunSigno(f["Diferencia_%"])}"><strong>${fmtPct(f["Diferencia_%"])}</strong></td>
            <td>${fmtNum(f["Volatilidad_%"])}%</td>
            <td class="texto-negativo">${fmtNum(f["Max_Drawdown_%"])}%</td>
          </tr>
        `
        )
        .join("");
  
      tabla.innerHTML = encabezado + `<tbody>${cuerpo}</tbody>`;
    } catch (error) {
      tabla.innerHTML = `<tr><td><div class="mensaje-error">Error al cargar comparativa: ${error.message}</div></td></tr>`;
    }
  }