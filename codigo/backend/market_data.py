"""
market_data.py
--------------
Modulo complementario a data_loader.py. Descarga indicadores de mercado
adicionales exigidos en el criterio B2 de la rubrica:

    - Volumen de negociacion mensual (serie de tiempo, por activo).
    - Capitalizacion de mercado actual (snapshot, por activo).
    - Serie de precios del benchmark (ya disponible via data_loader).

Trabajo Final Integrador - Finanzas I - UPB La Paz - Gestion 2026
"""

import os
import time
import pandas as pd
import yfinance as yf

import data_loader as dl

RUTA_DATOS = dl.RUTA_DATOS


# ---------------------------------------------------------------------------
# 1. VOLUMEN DE NEGOCIACION (serie de tiempo)
# ---------------------------------------------------------------------------
def descargar_volumen(tickers=None, anios=dl.PERIODO_ANIOS, guardar_csv=True):
    """
    Descarga el volumen de negociacion mensual (suma del mes) para una lista de tickers.

    Retorna
    -------
    pd.DataFrame
        Volumen mensual, columnas = tickers, indice = fechas (fin de mes).
    """
    if tickers is None:
        tickers = list(dl.ACTIVOS.keys())

    periodo_str = f"{anios}y"
    print(f"Descargando volumen de negociacion para {len(tickers)} activos...")
    datos_crudos = yf.download(
        tickers,
        period=periodo_str,
        auto_adjust=True,
        progress=False,
        group_by="ticker",
    )

    volumen = pd.DataFrame()
    for tk in tickers:
        try:
            volumen[tk] = datos_crudos[tk]["Volume"]
        except KeyError:
            print(f"  [AVISO] No se pudo obtener volumen de '{tk}'. Se omite.")

    volumen = volumen.dropna(how="all")

    # Resampleo a frecuencia MENSUAL: a diferencia del precio (que se toma
    # como el ultimo valor del mes, un "nivel"), el volumen es un FLUJO que
    # se acumula dia a dia, por lo que el resampleo correcto es la SUMA de
    # todo el volumen negociado durante el mes, no el volumen de un solo dia.
    volumen.index = pd.to_datetime(volumen.index)
    volumen = volumen.resample("ME").sum()

    if guardar_csv:
        os.makedirs(RUTA_DATOS, exist_ok=True)
        ruta_csv = os.path.join(RUTA_DATOS, "volumen_historico.csv")
        volumen.to_csv(ruta_csv)
        print(f"Volumen guardado en: {ruta_csv}")

    return volumen


# ---------------------------------------------------------------------------
# 2. CAPITALIZACION DE MERCADO (snapshot actual)
# ---------------------------------------------------------------------------
def descargar_capitalizacion(tickers=None, guardar_csv=True, pausa_seg=0.3):
    """
    Descarga la capitalizacion de mercado ACTUAL (snapshot) para cada ticker
    usando yf.Ticker(...).info, que consulta datos fundamentales (no series
    historicas). Algunos ETFs no tienen "marketCap" sino "totalAssets" o
    "netAssets"; se maneja ese caso por separado.

    NOTA: yfinance hace una request por cada ticker en este metodo, por lo
    que se incluye una pequenia pausa entre consultas para evitar bloqueos
    por exceso de requests (rate limiting) de Yahoo Finance.

    Retorna
    -------
    pd.DataFrame
        Una fila por activo con columnas: Ticker, Tipo, Capitalizacion_USD,
        Fuente (indica si el valor es marketCap o totalAssets/netAssets).
    """
    if tickers is None:
        tickers = list(dl.ACTIVOS.keys())

    print(f"Descargando capitalizacion de mercado actual para {len(tickers)} activos...")
    filas = []
    for tk in tickers:
        info_local = dl.ACTIVOS.get(tk, {})
        tipo = info_local.get("tipo", "N/D")
        try:
            info_yf = yf.Ticker(tk).info
        except Exception as e:
            print(f"  [AVISO] No se pudo obtener info de '{tk}': {e}")
            filas.append({"Ticker": tk, "Tipo": tipo, "Capitalizacion_USD": None, "Fuente": "N/D"})
            time.sleep(pausa_seg)
            continue

        if tipo == "ETF":
            # Los ETFs no tienen "marketCap"; usan activos totales bajo gestion.
            valor = info_yf.get("totalAssets") or info_yf.get("netAssets")
            fuente = "totalAssets (AUM)"
        else:
            valor = info_yf.get("marketCap")
            fuente = "marketCap"

        filas.append({
            "Ticker": tk,
            "Tipo": tipo,
            "Capitalizacion_USD": valor,
            "Fuente": fuente,
        })
        time.sleep(pausa_seg)  # evitar rate limiting de Yahoo Finance

    tabla = pd.DataFrame(filas).set_index("Ticker")

    if guardar_csv:
        os.makedirs(RUTA_DATOS, exist_ok=True)
        ruta_csv = os.path.join(RUTA_DATOS, "capitalizacion_mercado.csv")
        tabla.to_csv(ruta_csv, encoding="utf-8-sig")
        print(f"Capitalizacion guardada en: {ruta_csv}")

    return tabla


# ---------------------------------------------------------------------------
# 3. CARGA DESDE CSV (para uso posterior sin re-descargar)
# ---------------------------------------------------------------------------
def cargar_volumen_desde_csv():
    ruta_csv = os.path.join(RUTA_DATOS, "volumen_historico.csv")
    return pd.read_csv(ruta_csv, index_col=0, parse_dates=True)


def cargar_capitalizacion_desde_csv():
    ruta_csv = os.path.join(RUTA_DATOS, "capitalizacion_mercado.csv")
    return pd.read_csv(ruta_csv, index_col=0)


# ---------------------------------------------------------------------------
# 4. EJECUCION DIRECTA
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    # Uso: python market_data.py
    volumen = descargar_volumen()
    cap = descargar_capitalizacion()

    print("\nResumen:")
    print(f"  - Volumen: {volumen.shape[0]} meses x {volumen.shape[1]} activos")
    print(f"  - Capitalizacion: {cap.shape[0]} activos con datos")
    print("\nTop 5 por capitalizacion de mercado:")
    print(cap.dropna().sort_values("Capitalizacion_USD", ascending=False).head(5).to_string())