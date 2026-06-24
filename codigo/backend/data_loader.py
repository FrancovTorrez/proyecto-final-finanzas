"""
data_loader.py
----------------
Modulo encargado de descargar y cachear los precios historicos de los
activos del universo de inversion, asi como del benchmark, usando
Yahoo Finance (libreria yfinance).

Trabajo Final Integrador - Finanzas I - UPB La Paz - Gestion 2026
"""

import os
import pandas as pd
import yfinance as yf

# ---------------------------------------------------------------------------
# 1. UNIVERSO DE ACTIVOS
# ---------------------------------------------------------------------------
# 34 instrumentos en total:
#   - 24 acciones EE.UU. / internacionales desarrolladas (8 sectores)
#   - 4 ADRs Latam (Brasil x2, Mexico x2)
#   - 6 ETFs (renta variable global, renta fija, oro, sector energia)
# Todos cotizan en USD en bolsas de EE.UU., por lo que yfinance los
# descarga sin problemas de tipo de cambio ni series incompletas.

ACTIVOS = {
    # --- Tecnologia ---
    "AAPL": {"nombre": "Apple Inc.",              "tipo": "Accion", "sector": "Tecnologia",  "region": "EE.UU."},
    "MSFT": {"nombre": "Microsoft Corp.",          "tipo": "Accion", "sector": "Tecnologia",  "region": "EE.UU."},
    "GOOGL": {"nombre": "Alphabet Inc.",           "tipo": "Accion", "sector": "Tecnologia",  "region": "EE.UU."},
    "NVDA": {"nombre": "NVIDIA Corp.",             "tipo": "Accion", "sector": "Tecnologia",  "region": "EE.UU."},
    "META": {"nombre": "Meta Platforms Inc.",      "tipo": "Accion", "sector": "Tecnologia",  "region": "EE.UU."},

    # --- Salud ---
    "JNJ":  {"nombre": "Johnson & Johnson",        "tipo": "Accion", "sector": "Salud",       "region": "EE.UU."},
    "PFE":  {"nombre": "Pfizer Inc.",              "tipo": "Accion", "sector": "Salud",       "region": "EE.UU."},
    "UNH":  {"nombre": "UnitedHealth Group",       "tipo": "Accion", "sector": "Salud",       "region": "EE.UU."},

    # --- Financiero ---
    "JPM":  {"nombre": "JPMorgan Chase & Co.",     "tipo": "Accion", "sector": "Financiero",  "region": "EE.UU."},
    "BAC":  {"nombre": "Bank of America Corp.",    "tipo": "Accion", "sector": "Financiero",  "region": "EE.UU."},
    "V":    {"nombre": "Visa Inc.",                "tipo": "Accion", "sector": "Financiero",  "region": "EE.UU."},

    # --- Consumo ---
    "KO":   {"nombre": "Coca-Cola Co.",            "tipo": "Accion", "sector": "Consumo",     "region": "EE.UU."},
    "PG":   {"nombre": "Procter & Gamble Co.",     "tipo": "Accion", "sector": "Consumo",     "region": "EE.UU."},
    "MCD":  {"nombre": "McDonald's Corp.",         "tipo": "Accion", "sector": "Consumo",     "region": "EE.UU."},
    "AMZN": {"nombre": "Amazon.com Inc.",          "tipo": "Accion", "sector": "Consumo",     "region": "EE.UU."},

    # --- Energia ---
    "XOM":  {"nombre": "Exxon Mobil Corp.",        "tipo": "Accion", "sector": "Energia",     "region": "EE.UU."},
    "CVX":  {"nombre": "Chevron Corp.",            "tipo": "Accion", "sector": "Energia",     "region": "EE.UU."},

    # --- Industrial ---
    "CAT":  {"nombre": "Caterpillar Inc.",         "tipo": "Accion", "sector": "Industrial",  "region": "EE.UU."},
    "HON":  {"nombre": "Honeywell International",  "tipo": "Accion", "sector": "Industrial",  "region": "EE.UU."},

    # --- Telecomunicaciones ---
    "T":    {"nombre": "AT&T Inc.",                "tipo": "Accion", "sector": "Telecom",     "region": "EE.UU."},
    "VZ":   {"nombre": "Verizon Communications",   "tipo": "Accion", "sector": "Telecom",     "region": "EE.UU."},

    # --- Internacional desarrollado / emergente (no Latam) ---
    "TSM":  {"nombre": "Taiwan Semiconductor",     "tipo": "Accion", "sector": "Tecnologia",  "region": "Asia"},
    "BABA": {"nombre": "Alibaba Group",            "tipo": "Accion", "sector": "Consumo",     "region": "Asia"},
    "NVO":  {"nombre": "Novo Nordisk",             "tipo": "Accion", "sector": "Salud",       "region": "Europa"},
    "SHEL": {"nombre": "Shell plc",                "tipo": "Accion", "sector": "Energia",     "region": "Europa"},

    # --- Latam (ADRs en NYSE) ---
    "VALE": {"nombre": "Vale S.A.",                "tipo": "ADR",    "sector": "Materiales",  "region": "Latam (Brasil)"},
    "ITUB": {"nombre": "Itau Unibanco Holding",    "tipo": "ADR",    "sector": "Financiero",  "region": "Latam (Brasil)"},
    "AMX":  {"nombre": "America Movil",            "tipo": "ADR",    "sector": "Telecom",     "region": "Latam (Mexico)"},
    "FMX":  {"nombre": "Fomento Economico Mexicano","tipo": "ADR",   "sector": "Consumo",     "region": "Latam (Mexico)"},

    # --- ETFs ---
    "SPY":  {"nombre": "SPDR S&P 500 ETF",         "tipo": "ETF",    "sector": "Renta Variable Global", "region": "EE.UU."},
    "EFA":  {"nombre": "iShares MSCI EAFE ETF",    "tipo": "ETF",    "sector": "Renta Variable Global", "region": "Desarrollado ex-US"},
    "EEM":  {"nombre": "iShares MSCI Emerging Mkts","tipo": "ETF",   "sector": "Renta Variable Global", "region": "Emergente"},
    "AGG":  {"nombre": "iShares Core US Agg Bond", "tipo": "ETF",    "sector": "Renta Fija",            "region": "EE.UU."},
    "GLD":  {"nombre": "SPDR Gold Shares",         "tipo": "ETF",    "sector": "Materias Primas",        "region": "Global"},
    "XLE":  {"nombre": "Energy Select Sector SPDR","tipo": "ETF",    "sector": "Energia",                "region": "EE.UU."},
}

# Benchmark de referencia: S&P 500
BENCHMARK_TICKER = "^GSPC"
BENCHMARK_NOMBRE = "S&P 500"

# Tasa libre de riesgo: rendimiento de las T-Bills a 3 meses de EE.UU.
# (se usa como proxy estandar en finanzas para activos en USD)
RF_TICKER = "^IRX"  # 13 Week Treasury Bill (cotiza en puntos porcentuales anuales)

# ---------------------------------------------------------------------------
# 2. PARAMETROS DE DESCARGA
# ---------------------------------------------------------------------------
PERIODO_ANIOS = 5  # 5 anios de historia (2022-2026), por encima del minimo de 3 exigido
RUTA_DATOS = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "datos")


def _asegurar_carpeta_datos():
    os.makedirs(RUTA_DATOS, exist_ok=True)


def descargar_precios(tickers=None, anios=PERIODO_ANIOS, guardar_csv=True):
    """
    Descarga precios de cierre ajustado para una lista de tickers.

    Parametros
    ----------
    tickers : list[str] | None
        Lista de tickers a descargar. Si es None, descarga todos los
        activos del universo definido en ACTIVOS (sin el benchmark).
    anios : int
        Cantidad de anios de historia a descargar (minimo 3 segun consigna).
    guardar_csv : bool
        Si True, guarda el resultado en /datos/precios_historicos.csv

    Retorna
    -------
    pd.DataFrame
        Precios de cierre ajustado, columnas = tickers, indice = fechas.
    """
    if tickers is None:
        tickers = list(ACTIVOS.keys())

    periodo_str = f"{anios}y"

    print(f"Descargando {len(tickers)} activos desde Yahoo Finance ({periodo_str} de historia)...")
    datos_crudos = yf.download(
        tickers,
        period=periodo_str,
        auto_adjust=True,   # precios ya ajustados por dividendos/splits
        progress=False,
        group_by="ticker",
    )

    # yf.download con multiples tickers devuelve columnas multinivel
    # (ticker, campo). Extraemos solo "Close" (ya ajustado) por activo.
    precios = pd.DataFrame()
    for tk in tickers:
        try:
            precios[tk] = datos_crudos[tk]["Close"]
        except KeyError:
            print(f"  [AVISO] No se pudo descargar el ticker '{tk}'. Se omite.")

    precios = precios.dropna(how="all")

    # Resampleo a frecuencia MENSUAL: se toma el precio de cierre del
    # ULTIMO dia de cotizacion de cada mes (estandar para construir series
    # mensuales a partir de datos diarios, evita distorsionar los retornos
    # compuestos como ocurriria con un promedio mensual).
    precios.index = pd.to_datetime(precios.index)
    precios = precios.resample("ME").last()

    if guardar_csv:
        _asegurar_carpeta_datos()
        ruta_csv = os.path.join(RUTA_DATOS, "precios_historicos.csv")
        precios.to_csv(ruta_csv)
        print(f"Precios guardados en: {ruta_csv}")

    return precios


def descargar_benchmark(anios=PERIODO_ANIOS, guardar_csv=True):
    """
    Descarga la serie de precios del benchmark (S&P 500).

    Retorna
    -------
    pd.Series
        Precios de cierre ajustado del benchmark, indexado por fecha.
    """
    periodo_str = f"{anios}y"
    print(f"Descargando benchmark ({BENCHMARK_NOMBRE})...")
    data = yf.download(BENCHMARK_TICKER, period=periodo_str, auto_adjust=True, progress=False)
    serie = data["Close"]
    # Si viene como DataFrame de 1 columna (comportamiento de algunas
    # versiones de yfinance/pandas), aplanar a Serie ANTES de renombrar.
    if isinstance(serie, pd.DataFrame):
        serie = serie.iloc[:, 0]
    serie = serie.rename(BENCHMARK_NOMBRE)

    # Misma logica de resampleo mensual que en descargar_precios().
    serie.index = pd.to_datetime(serie.index)
    serie = serie.resample("ME").last()

    if guardar_csv:
        _asegurar_carpeta_datos()
        ruta_csv = os.path.join(RUTA_DATOS, "benchmark_sp500.csv")
        serie.to_csv(ruta_csv)
        print(f"Benchmark guardado en: {ruta_csv}")

    return serie


def descargar_tasa_libre_riesgo(anios=PERIODO_ANIOS, guardar_csv=True):
    """
    Descarga la serie de la tasa libre de riesgo (T-Bill 13 semanas, ^IRX).
    El ticker ^IRX cotiza en puntos porcentuales anuales (ej. 4.85 = 4.85%).

    Retorna
    -------
    pd.Series
        Tasa libre de riesgo anualizada (en decimales, ej. 0.0485), por fecha.
    """
    periodo_str = f"{anios}y"
    print("Descargando tasa libre de riesgo (^IRX, T-Bill 13 semanas)...")
    data = yf.download(RF_TICKER, period=periodo_str, auto_adjust=True, progress=False)
    serie = data["Close"]
    if isinstance(serie, pd.DataFrame):
        serie = serie.iloc[:, 0]
    serie = serie.rename("rf_anual")
    serie = serie / 100.0  # de puntos porcentuales a decimal

    if guardar_csv:
        _asegurar_carpeta_datos()
        ruta_csv = os.path.join(RUTA_DATOS, "tasa_libre_riesgo.csv")
        serie.to_csv(ruta_csv)
        print(f"Tasa libre de riesgo guardada en: {ruta_csv}")

    return serie


def cargar_precios_desde_csv():
    """Carga los precios ya descargados desde /datos/precios_historicos.csv"""
    ruta_csv = os.path.join(RUTA_DATOS, "precios_historicos.csv")
    return pd.read_csv(ruta_csv, index_col=0, parse_dates=True)


def cargar_benchmark_desde_csv():
    """Carga el benchmark ya descargado desde /datos/benchmark_sp500.csv"""
    ruta_csv = os.path.join(RUTA_DATOS, "benchmark_sp500.csv")
    df = pd.read_csv(ruta_csv, index_col=0, parse_dates=True)
    return df.iloc[:, 0]


def cargar_rf_desde_csv():
    """Carga la tasa libre de riesgo ya descargada desde /datos/tasa_libre_riesgo.csv"""
    ruta_csv = os.path.join(RUTA_DATOS, "tasa_libre_riesgo.csv")
    df = pd.read_csv(ruta_csv, index_col=0, parse_dates=True)
    return df.iloc[:, 0]


if __name__ == "__main__":
    # Ejecutar este archivo directamente descarga y guarda todo el dataset.
    # Uso: python data_loader.py
    precios = descargar_precios()
    benchmark = descargar_benchmark()
    rf = descargar_tasa_libre_riesgo()

    print("\nResumen de la descarga:")
    print(f"  - Activos descargados: {precios.shape[1]} / {len(ACTIVOS)}")
    print(f"  - Meses de historia: {precios.shape[0]}")
    print(f"  - Rango de fechas: {precios.index.min().date()} a {precios.index.max().date()}")
    print(f"  - Benchmark: {BENCHMARK_NOMBRE} ({benchmark.shape[0]} meses)")
    print(f"  - Tasa libre de riesgo promedio del periodo: {rf.mean()*100:.2f}% anual")