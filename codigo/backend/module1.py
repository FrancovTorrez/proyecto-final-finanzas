"""
module1.py
----------
Modulo 1 del dashboard: Analisis de Riesgo y Rentabilidad (criterio B).

Combina precios, retornos, indicadores (metrics.py) y datos de mercado
(market_data.py) en estructuras listas para servir al frontend via la
API Flask. NO genera el HTML/JS -- solo prepara los datos en formato
facil de convertir a JSON.

Trabajo Final Integrador - Finanzas I - UPB La Paz - Gestion 2026
"""

import numpy as np
import pandas as pd

import data_loader as dl
import metrics as m
import market_data as md


# ---------------------------------------------------------------------------
# B1. SERIE DE TIEMPO CON FILTRO DE PERIODO
# ---------------------------------------------------------------------------
def filtrar_por_periodo(precios: pd.DataFrame, periodo: str = "5A") -> pd.DataFrame:
    """
    Filtra la tabla de precios (de frecuencia MENSUAL) a una ventana de
    tiempo reciente.

    Parametros
    ----------
    precios : pd.DataFrame
        Tabla completa de precios mensuales (indice = fechas, fin de mes).
    periodo : str
        Una de: "3M", "6M", "1A", "3A", "5A" (todo el historico disponible).
        NOTA: con datos mensuales, "1M" no aporta informacion util para un
        grafico de serie de tiempo (un solo punto), por lo que se omite esa
        opcion y el periodo minimo disponible es "3M".

    Retorna
    -------
    pd.DataFrame
        Subconjunto de precios dentro de la ventana solicitada.
    """
    mapa_meses = {
        "3M": 3,
        "6M": 6,
        "1A": 12,
        "3A": 36,
        "5A": None,  # None = no recortar, usar todo el historico (5 anios)
    }

    if periodo not in mapa_meses:
        raise ValueError(f"Periodo '{periodo}' no reconocido. Usar uno de: {list(mapa_meses.keys())}")

    meses = mapa_meses[periodo]
    if meses is None:
        return precios.copy()

    return precios.tail(meses).copy()


def serie_precios_normalizados(precios: pd.DataFrame, tickers_seleccionados: list,
                                periodo: str = "5A") -> dict:
    """
    Prepara series de precios normalizadas a base 100 para comparar
    activos de distinta escala en el mismo grafico (caracteristico de
    dashboards financieros).

    Parametros
    ----------
    precios : pd.DataFrame
        Tabla completa de precios.
    tickers_seleccionados : list[str]
        Activos elegidos por el usuario en la interfaz.
    periodo : str
        Ventana de tiempo a mostrar.

    Retorna
    -------
    dict
        {
          "fechas": [...],
          "series": {ticker: [valores normalizados base 100], ...}
        }
    """
    sub = filtrar_por_periodo(precios[tickers_seleccionados], periodo)
    sub_normalizado = sub / sub.iloc[0] * 100

    return {
        "fechas": [f.strftime("%Y-%m-%d") for f in sub_normalizado.index],
        "series": {tk: sub_normalizado[tk].round(2).tolist() for tk in tickers_seleccionados},
    }


def serie_retornos(precios: pd.DataFrame, tickers_seleccionados: list,
                    periodo: str = "5A") -> dict:
    """
    Prepara series de retornos mensuales (en %) para el periodo y activos
    seleccionados.

    Retorna
    -------
    dict
        {
          "fechas": [...],
          "series": {ticker: [retornos mensuales en %], ...}
        }
    """
    sub_precios = filtrar_por_periodo(precios[tickers_seleccionados], periodo)
    retornos = sub_precios.pct_change().dropna() * 100

    return {
        "fechas": [f.strftime("%Y-%m-%d") for f in retornos.index],
        "series": {tk: retornos[tk].round(3).tolist() for tk in tickers_seleccionados},
    }


# ---------------------------------------------------------------------------
# B1. SCATTER RIESGO-RENDIMIENTO (universo completo, con etiquetas)
# ---------------------------------------------------------------------------
def scatter_riesgo_rendimiento(tabla_indicadores: pd.DataFrame) -> list:
    """
    Prepara los puntos para el grafico de dispersion riesgo-rendimiento,
    usando la tabla ya calculada en metrics.py (criterio A2/B1).

    Retorna
    -------
    list[dict]
        Una entrada por activo: ticker, nombre, sector, region, tipo,
        retorno (eje Y), volatilidad (eje X) -- ambos ya anualizados.
    """
    puntos = []
    for ticker, fila in tabla_indicadores.iterrows():
        puntos.append({
            "ticker": ticker,
            "nombre": fila["Nombre"],
            "tipo": fila["Tipo"],
            "sector": fila["Sector"],
            "region": fila["Region"],
            "retorno_%": round(float(fila["Retorno_Anualizado_%"]), 3),
            "volatilidad_%": round(float(fila["Volatilidad_Anualizada_%"]), 3),
            "sharpe": round(float(fila["Sharpe_Ratio"]), 3) if pd.notna(fila["Sharpe_Ratio"]) else None,
        })
    return puntos


# ---------------------------------------------------------------------------
# B2. INDICADORES DE MERCADO INTEGRADOS CON LA SERIE DE TIEMPO
# ---------------------------------------------------------------------------
def serie_con_benchmark_y_volumen(precios: pd.DataFrame, benchmark: pd.Series,
                                   volumen: pd.DataFrame, ticker: str,
                                   periodo: str = "5A") -> dict:
    """
    Prepara, PARA UN SOLO ACTIVO, una estructura integrada que combina:
        - precio normalizado del activo (base 100)
        - precio normalizado del benchmark (base 100), para comparar
          directamente el desempenio del activo vs. el mercado
        - volumen de negociacion mensual del activo (suma del mes)

    Esto cumple B2 al nivel "Excelente": los indicadores de mercado se
    visualizan integrados con la serie de tiempo del activo, permitiendo
    comparar el activo con el mercado en el mismo grafico.

    Retorna
    -------
    dict con fechas, precio_normalizado, benchmark_normalizado, volumen.
    """
    precio_activo = filtrar_por_periodo(precios[[ticker]], periodo)[ticker]
    bench_alineado = benchmark.reindex(precio_activo.index).ffill()
    volumen_activo = filtrar_por_periodo(volumen[[ticker]], periodo)[ticker]

    precio_norm = precio_activo / precio_activo.iloc[0] * 100
    bench_norm = bench_alineado / bench_alineado.iloc[0] * 100

    return {
        "ticker": ticker,
        "fechas": [f.strftime("%Y-%m-%d") for f in precio_activo.index],
        "precio_normalizado": precio_norm.round(2).tolist(),
        "benchmark_normalizado": bench_norm.round(2).tolist(),
        "volumen": volumen_activo.fillna(0).astype(int).tolist(),
    }


def resumen_capitalizacion(cap_tabla: pd.DataFrame, ticker: str) -> dict:
    """
    Devuelve el dato puntual de capitalizacion de mercado (o AUM si es ETF)
    para un activo, en formato listo para mostrar como badge/tarjeta en el
    frontend (NO como serie de tiempo -- ver nota en market_data.py).
    """
    if ticker not in cap_tabla.index:
        return {"ticker": ticker, "capitalizacion_usd": None, "fuente": "N/D"}

    fila = cap_tabla.loc[ticker]
    valor = fila["Capitalizacion_USD"]
    return {
        "ticker": ticker,
        "capitalizacion_usd": None if pd.isna(valor) else float(valor),
        "fuente": fila["Fuente"],
    }


# ---------------------------------------------------------------------------
# EJECUCION DIRECTA (prueba rapida de ensamblaje)
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    precios = dl.cargar_precios_desde_csv()
    benchmark = dl.cargar_benchmark_desde_csv()
    rf_serie = dl.cargar_rf_desde_csv()
    volumen = md.cargar_volumen_desde_csv()
    cap_tabla = md.cargar_capitalizacion_desde_csv()

    tabla_ind = m.calcular_tabla_indicadores(precios, benchmark, rf_serie)

    # Prueba: serie normalizada de 3 activos en el ultimo anio
    ejemplo_serie = serie_precios_normalizados(precios, ["AAPL", "MSFT", "SPY"], periodo="1A")
    print("Ejemplo serie normalizada (primeras 3 fechas):")
    print("  Fechas:", ejemplo_serie["fechas"][:3])
    print("  AAPL:", ejemplo_serie["series"]["AAPL"][:3])

    # Prueba: scatter riesgo-rendimiento
    scatter = scatter_riesgo_rendimiento(tabla_ind)
    print(f"\nScatter riesgo-rendimiento: {len(scatter)} puntos generados.")
    print("  Ejemplo:", scatter[0])

    # Prueba: serie integrada con benchmark y volumen para un activo
    integrado = serie_con_benchmark_y_volumen(precios, benchmark, volumen, "NVDA", periodo="6M")
    print(f"\nSerie integrada NVDA (6M): {len(integrado['fechas'])} dias.")
    print("  Precio normalizado (ultimos 3):", integrado["precio_normalizado"][-3:])
    print("  Benchmark normalizado (ultimos 3):", integrado["benchmark_normalizado"][-3:])
    print("  Volumen (ultimos 3):", integrado["volumen"][-3:])

    # Prueba: capitalizacion puntual
    cap_nvda = resumen_capitalizacion(cap_tabla, "NVDA")
    print("\nCapitalizacion NVDA:", cap_nvda)