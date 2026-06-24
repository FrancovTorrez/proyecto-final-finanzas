"""
app.py
------
API Flask del Trabajo Final Integrador - Finanzas I - UPB La Paz - Gestion 2026.

Conecta todos los modulos de calculo (data_loader, metrics, market_data,
module1, portfolio, capm) y los expone como endpoints JSON para que el
frontend (HTML + JS + Plotly.js) pueda construir el dashboard interactivo.

ARQUITECTURA:
    - Al arrancar el servidor, los CSVs (precios, benchmark, rf, volumen,
      capitalizacion) se cargan UNA SOLA VEZ en memoria (variables globales).
    - En cada request, se usan esos datos en memoria para recalcular SOLO
      lo que depende de la seleccion del usuario (Markowitz, regresion OLS),
      evitando releer disco en cada llamada pero permitiendo recalculo en
      vivo cuando el usuario cambia su seleccion de activos (criterio C1).

EJECUCION:
    python app.py
    (el servidor queda escuchando en http://127.0.0.1:5000)
"""

from flask import Flask, jsonify, request
from flask_cors import CORS

import data_loader as dl
import metrics as m
import market_data as md
import module1 as mod1
import portfolio as p
import capm as c

app = Flask(__name__)
CORS(app)  # permite que el frontend HTML (servido por separado) consulte esta API

# ---------------------------------------------------------------------------
# CARGA EN MEMORIA AL ARRANCAR EL SERVIDOR (una sola vez)
# ---------------------------------------------------------------------------
print("Cargando datos en memoria...")
PRECIOS = dl.cargar_precios_desde_csv()
BENCHMARK = dl.cargar_benchmark_desde_csv()
RF_SERIE = dl.cargar_rf_desde_csv()
RF_PROMEDIO = RF_SERIE.mean()
VOLUMEN = md.cargar_volumen_desde_csv()
CAP_TABLA = md.cargar_capitalizacion_desde_csv()
RETORNOS_BENCHMARK = BENCHMARK.pct_change().dropna()
RETORNO_MERCADO_ESPERADO = c.retorno_anualizado_de_serie(RETORNOS_BENCHMARK)
TABLA_INDICADORES = m.calcular_tabla_indicadores(PRECIOS, BENCHMARK, RF_SERIE)
print(f"Datos cargados: {PRECIOS.shape[1]} activos, {PRECIOS.shape[0]} meses de historia.")
print(f"Tasa libre de riesgo: {RF_PROMEDIO*100:.2f}% | Retorno mercado esperado: {RETORNO_MERCADO_ESPERADO*100:.2f}%")


def _manejar_error(mensaje: str, codigo: int = 400):
    """Helper para devolver errores en formato JSON consistente."""
    return jsonify({"error": mensaje}), codigo


# ---------------------------------------------------------------------------
# ENDPOINTS GENERALES
# ---------------------------------------------------------------------------
@app.route("/api/universo", methods=["GET"])
def universo_activos():
    """
    Devuelve el universo completo de activos disponibles (criterio A1),
    con su metadata (nombre, tipo, sector, region), para poblar los
    checkboxes/selectores del frontend.
    """
    activos_lista = []
    for ticker, info in dl.ACTIVOS.items():
        activos_lista.append({
            "ticker": ticker,
            "nombre": info["nombre"],
            "tipo": info["tipo"],
            "sector": info["sector"],
            "region": info["region"],
        })
    return jsonify({
        "activos": activos_lista,
        "benchmark": dl.BENCHMARK_NOMBRE,
        "seleccion_inicial": p.SELECCION_INICIAL,
        "rf_promedio_%": round(RF_PROMEDIO * 100, 3),
    })


@app.route("/api/indicadores", methods=["GET"])
def indicadores_riesgo_rentabilidad():
    """
    Devuelve la tabla de los 7 indicadores de riesgo/rentabilidad (criterio
    A2) para TODOS los activos del universo (no depende de la seleccion
    del usuario, por eso no recibe parametros).
    """
    tabla = TABLA_INDICADORES.reset_index().to_dict(orient="records")
    return jsonify({"indicadores": tabla})


# ---------------------------------------------------------------------------
# MODULO 1 -- ENDPOINTS (criterio B)
# ---------------------------------------------------------------------------
@app.route("/api/modulo1/series", methods=["GET"])
def modulo1_series():
    """
    Query params:
        tickers   : lista separada por comas, ej. ?tickers=AAPL,MSFT,SPY
        periodo   : uno de 3M, 6M, 1A, 3A, 5A (default: 5A)
        tipo      : 'precio' o 'retorno' (default: precio)
    """
    tickers_param = request.args.get("tickers", "")
    periodo = request.args.get("periodo", "5A")
    tipo = request.args.get("tipo", "precio")

    tickers = [t.strip() for t in tickers_param.split(",") if t.strip()]
    if not tickers:
        return _manejar_error("Debe especificar al menos un ticker en el parametro 'tickers'.")

    no_validos = [t for t in tickers if t not in PRECIOS.columns]
    if no_validos:
        return _manejar_error(f"Tickers no reconocidos: {no_validos}")

    try:
        if tipo == "retorno":
            resultado = mod1.serie_retornos(PRECIOS, tickers, periodo)
        else:
            resultado = mod1.serie_precios_normalizados(PRECIOS, tickers, periodo)
    except ValueError as e:
        return _manejar_error(str(e))

    return jsonify(resultado)


@app.route("/api/modulo1/scatter", methods=["GET"])
def modulo1_scatter():
    """Scatter riesgo-rendimiento del universo completo (criterio B1/C3)."""
    puntos = mod1.scatter_riesgo_rendimiento(TABLA_INDICADORES)
    return jsonify({"puntos": puntos})


@app.route("/api/modulo1/mercado/<ticker>", methods=["GET"])
def modulo1_mercado_integrado(ticker):
    """
    Indicadores de mercado integrados con la serie de tiempo de UN activo
    (criterio B2): precio normalizado + benchmark normalizado + volumen.

    Query params:
        periodo : uno de 3M, 6M, 1A, 3A, 5A (default: 5A)
    """
    periodo = request.args.get("periodo", "5A")

    if ticker not in PRECIOS.columns:
        return _manejar_error(f"Ticker '{ticker}' no reconocido.", 404)

    try:
        integrado = mod1.serie_con_benchmark_y_volumen(PRECIOS, BENCHMARK, VOLUMEN, ticker, periodo)
    except ValueError as e:
        return _manejar_error(str(e))

    cap = mod1.resumen_capitalizacion(CAP_TABLA, ticker)
    integrado["capitalizacion"] = cap

    return jsonify(integrado)


# ---------------------------------------------------------------------------
# MODULO 2 -- ENDPOINTS (criterio C: Optimizacion de Portafolios)
# ---------------------------------------------------------------------------
@app.route("/api/modulo2/correlaciones", methods=["GET"])
def modulo2_correlaciones():
    """
    Matriz de correlaciones (criterio C2) para los activos seleccionados.

    Query params:
        tickers : lista separada por comas
    """
    tickers_param = request.args.get("tickers", "")
    tickers = [t.strip() for t in tickers_param.split(",") if t.strip()]

    try:
        p.validar_seleccion(tickers)
    except ValueError as e:
        return _manejar_error(str(e))

    corr = p.matriz_correlaciones(PRECIOS, tickers)
    return jsonify({
        "tickers": tickers,
        "matriz": corr.round(4).values.tolist(),
    })


@app.route("/api/modulo2/optimizacion", methods=["GET"])
def modulo2_optimizacion():
    """
    Endpoint PRINCIPAL del Modulo 2 (criterio C1, C4, C5). Calcula, para
    los activos seleccionados por el usuario:
        - Portafolio de minima varianza
        - Portafolio tangente (maximo Sharpe)
        - Frontera Eficiente
        - Linea del Mercado de Capitales (CML)
        - Tabla de pesos optimos

    Esto es lo que se re-ejecuta en vivo cada vez que el usuario cambia
    su seleccion de activos en la interfaz (criterio C1: "la herramienta
    recalcula todos los resultados del modulo al cambiar la seleccion").

    Query params:
        tickers   : lista separada por comas (minimo 2 activos)
        n_puntos  : cantidad de puntos en la Frontera Eficiente (default 40)
    """
    tickers_param = request.args.get("tickers", "")
    tickers = [t.strip() for t in tickers_param.split(",") if t.strip()]
    n_puntos = int(request.args.get("n_puntos", 40))

    try:
        p.validar_seleccion(tickers)
    except ValueError as e:
        return _manejar_error(str(e))

    mu, cov, tk = p.preparar_insumos(PRECIOS, tickers)

    try:
        minvar = p.optimizar_minima_varianza(mu, cov)
        tangente = p.optimizar_portafolio_tangente(mu, cov, RF_PROMEDIO)
        frontera = p.calcular_frontera_eficiente(mu, cov, n_puntos=n_puntos)
        cml = p.calcular_cml(RF_PROMEDIO, tangente)
        tabla_pesos = p.tabla_pesos_optimos(tk, minvar, tangente)
    except RuntimeError as e:
        return _manejar_error(f"Error de optimizacion: {e}", 500)

    return jsonify({
        "tickers": tk,
        "minima_varianza": {
            "retorno_%": round(minvar["retorno_esperado"] * 100, 3),
            "volatilidad_%": round(minvar["volatilidad"] * 100, 3),
            "pesos_%": [round(w * 100, 3) for w in minvar["pesos"]],
        },
        "tangente": {
            "retorno_%": round(tangente["retorno_esperado"] * 100, 3),
            "volatilidad_%": round(tangente["volatilidad"] * 100, 3),
            "sharpe": round(tangente["sharpe"], 4),
            "pesos_%": [round(w * 100, 3) for w in tangente["pesos"]],
        },
        "frontera_eficiente": {
            "retornos_%": (frontera["retornos"] * 100).round(3).tolist(),
            "volatilidades_%": (frontera["volatilidades"] * 100).round(3).tolist(),
        },
        "cml": {
            "volatilidades_%": (cml["volatilidades"] * 100).round(3).tolist(),
            "retornos_%": (cml["retornos"] * 100).round(3).tolist(),
            "rf_%": round(cml["rf"] * 100, 3),
        },
        "tabla_pesos": tabla_pesos.reset_index().to_dict(orient="records"),
    })


# ---------------------------------------------------------------------------
# MODULO 3 -- ENDPOINTS (criterio D: CAPM)
# ---------------------------------------------------------------------------
@app.route("/api/modulo3/regresion/<ticker>", methods=["GET"])
def modulo3_regresion(ticker):
    """
    Regresion OLS de beta para UN activo (criterio D1): beta, alfa, R^2,
    p-value, y puntos para el scatter + recta de regresion.
    """
    if ticker not in PRECIOS.columns:
        return _manejar_error(f"Ticker '{ticker}' no reconocido.", 404)

    retornos = PRECIOS[ticker].pct_change().dropna()
    reg = c.regresion_beta(retornos, RETORNOS_BENCHMARK)
    dispersion = c.datos_dispersion_regresion(retornos, RETORNOS_BENCHMARK, reg)

    return jsonify({
        "ticker": ticker,
        "beta": round(reg["beta"], 4),
        "alfa_regresion_mensual": round(reg["alfa_regresion_mensual"], 6),
        "r_cuadrado": round(reg["r_cuadrado"], 4),
        "n_observaciones": reg["n_observaciones"],
        "p_value_beta": reg["p_value_beta"],
        "dispersion": dispersion,
    })


@app.route("/api/modulo3/sml", methods=["GET"])
def modulo3_sml():
    """
    Linea del Mercado de Titulos (criterio D2) para los activos
    seleccionados, con su posicion (alfa de Jensen) respecto a la SML.

    Query params:
        tickers : lista separada por comas
    """
    tickers_param = request.args.get("tickers", "")
    tickers = [t.strip() for t in tickers_param.split(",") if t.strip()]
    if not tickers:
        return _manejar_error("Debe especificar al menos un ticker en el parametro 'tickers'.")

    no_validos = [t for t in tickers if t not in PRECIOS.columns]
    if no_validos:
        return _manejar_error(f"Tickers no reconocidos: {no_validos}")

    betas = []
    retornos_reales = []
    for tk in tickers:
        r = PRECIOS[tk].pct_change().dropna()
        reg = c.regresion_beta(r, RETORNOS_BENCHMARK)
        betas.append(reg["beta"])
        retornos_reales.append(c.retorno_anualizado_de_serie(r))

    sml = c.calcular_sml(RF_PROMEDIO, RETORNO_MERCADO_ESPERADO)
    tabla_posicion = c.posicion_respecto_sml(tickers, betas, retornos_reales,
                                              RF_PROMEDIO, RETORNO_MERCADO_ESPERADO)

    return jsonify({
        "sml": {
            "betas": sml["betas"].round(3).tolist(),
            "retornos_esperados_%": (sml["retornos_esperados"] * 100).round(3).tolist(),
        },
        "rf_%": round(RF_PROMEDIO * 100, 3),
        "retorno_mercado_esperado_%": round(RETORNO_MERCADO_ESPERADO * 100, 3),
        "prima_riesgo_mercado_%": round(sml["prima_riesgo_mercado"] * 100, 3),
        "activos": tabla_posicion.reset_index().to_dict(orient="records"),
    })


@app.route("/api/modulo3/comparativa", methods=["GET"])
def modulo3_comparativa():
    """
    Tabla comparativa CAPM vs. rendimiento historico (criterio D3) para
    los activos seleccionados.

    Query params:
        tickers : lista separada por comas
    """
    tickers_param = request.args.get("tickers", "")
    tickers = [t.strip() for t in tickers_param.split(",") if t.strip()]
    if not tickers:
        return _manejar_error("Debe especificar al menos un ticker en el parametro 'tickers'.")

    no_validos = [t for t in tickers if t not in PRECIOS.columns]
    if no_validos:
        return _manejar_error(f"Tickers no reconocidos: {no_validos}")

    tabla = c.tabla_comparativa_capm_historico(PRECIOS, BENCHMARK, RF_SERIE, tickers)
    return jsonify({"comparativa": tabla.reset_index().to_dict(orient="records")})


# ---------------------------------------------------------------------------
# HEALTH CHECK (util para verificar que el servidor esta vivo)
# ---------------------------------------------------------------------------
@app.route("/api/health", methods=["GET"])
def health():
    return jsonify({
        "status": "ok",
        "activos_cargados": PRECIOS.shape[1],
        "meses_historia": PRECIOS.shape[0],
    })


if __name__ == "__main__":
    app.run(debug=True, port=5000)