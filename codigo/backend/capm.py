"""
capm.py
-------
Modulo 3 del dashboard: Modelos de Valoracion de Activos (criterio D).

Implementa el Modelo de Indice Unico (regresion OLS de retornos del
activo vs. retornos del benchmark) y el CAPM:

    - Estimacion de beta por regresion OLS, con R^2 (D1)
    - Linea del Mercado de Titulos (SML) y Alfa de Jensen (D2)
    - Tabla comparativa: rendimiento esperado CAPM vs. historico (D3)

Trabajo Final Integrador - Finanzas I - UPB La Paz - Gestion 2026
"""

import numpy as np
import pandas as pd
import statsmodels.api as sm 

import data_loader as dl
import metrics as m

PERIODOS_POR_ANIO = 12  # 12 meses por anio (datos de frecuencia MENSUAL)


# ---------------------------------------------------------------------------
# D1. REGRESION OLS: BETA Y R^2
# ---------------------------------------------------------------------------
def regresion_beta(retornos_activo: pd.Series, retornos_benchmark: pd.Series) -> dict:
    """
    Estima el Modelo de Indice Unico mediante regresion OLS:

        r_activo = alfa_regresion + beta * r_benchmark + error

    Esto es DISTINTO al beta de A2 (que se calculaba como Cov/Var directo
    sin pasar por una regresion formal). Aqui usamos statsmodels.OLS para
    obtener, ademas del beta, el R^2 y el alfa de la regresion -- ambos
    exigidos explicitamente por el criterio D1.

    Parametros
    ----------
    retornos_activo : pd.Series
        Retornos mensuales del activo.
    retornos_benchmark : pd.Series
        Retornos mensuales del benchmark (indice de referencia).

    Retorna
    -------
    dict con: beta, alfa_regresion_mensual, r_cuadrado, n_observaciones,
              p_value_beta, retornos_activo_alineados (para graficar),
              retornos_benchmark_alineados (para graficar).
    """
    df = pd.concat([retornos_activo, retornos_benchmark], axis=1).dropna()
    df.columns = ["activo", "benchmark"]

    X = sm.add_constant(df["benchmark"])  # agrega columna de 1's para el intercepto (alfa)
    y = df["activo"]

    modelo = sm.OLS(y, X).fit()

    alfa_regresion_mensual = modelo.params["const"]
    beta = modelo.params["benchmark"]
    r_cuadrado = modelo.rsquared
    p_value_beta = modelo.pvalues["benchmark"]

    return {
        "beta": beta,
        "alfa_regresion_mensual": alfa_regresion_mensual,
        "r_cuadrado": r_cuadrado,
        "n_observaciones": int(modelo.nobs),
        "p_value_beta": p_value_beta,
        "retornos_activo_alineados": df["activo"],
        "retornos_benchmark_alineados": df["benchmark"],
    }


def datos_dispersion_regresion(retornos_activo: pd.Series, retornos_benchmark: pd.Series,
                                resultado_regresion: dict) -> dict:
    """
    Prepara los puntos (x, y) del scatter retorno activo vs. retorno
    benchmark, mas la recta de regresion ajustada, listos para graficar
    (criterio D1: "Grafico de dispersion ... con recta de regresion").
    """
    x = resultado_regresion["retornos_benchmark_alineados"]
    y = resultado_regresion["retornos_activo_alineados"]

    x_min, x_max = x.min(), x.max()
    x_recta = np.linspace(x_min, x_max, 50)
    y_recta = resultado_regresion["alfa_regresion_mensual"] + resultado_regresion["beta"] * x_recta

    return {
        "puntos_x": (x * 100).round(3).tolist(),       # retorno benchmark, en %
        "puntos_y": (y * 100).round(3).tolist(),       # retorno activo, en %
        "recta_x": (x_recta * 100).round(3).tolist(),
        "recta_y": (y_recta * 100).round(3).tolist(),
    }


# ---------------------------------------------------------------------------
# D2. LINEA DEL MERCADO DE TITULOS (SML) Y ALFA DE JENSEN
# ---------------------------------------------------------------------------
def calcular_sml(rf: float, retorno_mercado_esperado: float, betas_rango: tuple = (-0.5, 2.5),
                  n_puntos: int = 50) -> dict:
    """
    Calcula la Linea del Mercado de Titulos (SML), segun el CAPM:

        E(R_i) = rf + beta_i * (E(R_m) - rf)

    La SML se grafica como una recta en el espacio (beta, retorno esperado).

    Parametros
    ----------
    rf : float
        Tasa libre de riesgo anualizada.
    retorno_mercado_esperado : float
        Retorno esperado del mercado (benchmark), anualizado.
        Tipicamente se usa el retorno historico promedio del benchmark
        en el periodo de analisis, como proxy del retorno esperado.
    betas_rango : tuple
        Rango de betas a graficar en el eje X.

    Retorna
    -------
    dict con betas (eje X) y retornos_esperados (eje Y) de la SML,
    ademas de la prima de riesgo de mercado usada.
    """
    prima_riesgo_mercado = retorno_mercado_esperado - rf

    betas_sml = np.linspace(betas_rango[0], betas_rango[1], n_puntos)
    retornos_sml = rf + betas_sml * prima_riesgo_mercado

    return {
        "betas": betas_sml,
        "retornos_esperados": retornos_sml,
        "rf": rf,
        "retorno_mercado_esperado": retorno_mercado_esperado,
        "prima_riesgo_mercado": prima_riesgo_mercado,
    }


def alfa_de_jensen(retorno_real_anualizado: float, beta: float, rf: float,
                    retorno_mercado_esperado: float) -> float:
    """
    Alfa de Jensen = Retorno real del activo - Retorno esperado segun CAPM

        alfa_jensen = R_real - [rf + beta * (R_mercado - rf)]

    Interpretacion:
        alfa > 0  -> el activo rindio MAS de lo que el CAPM predecia
                     dado su riesgo sistematico (subvalorado / desempenio
                     superior al esperado).
        alfa < 0  -> el activo rindio MENOS de lo esperado por el CAPM
                     (sobrevalorado / desempenio inferior al esperado).
        alfa = 0  -> el activo rindio exactamente lo que el CAPM predecia.
    """
    retorno_esperado_capm = rf + beta * (retorno_mercado_esperado - rf)
    return retorno_real_anualizado - retorno_esperado_capm


def posicion_respecto_sml(tickers: list, betas: list, retornos_reales: list,
                           rf: float, retorno_mercado_esperado: float) -> pd.DataFrame:
    """
    Para una lista de activos, calcula su retorno esperado segun CAPM y
    su alfa de Jensen, indicando si estan sobre o bajo la SML.

    Retorna
    -------
    pd.DataFrame con columnas: Beta, Retorno_Real_%, Retorno_CAPM_%,
    Alfa_Jensen_%, Posicion (texto interpretativo).
    """
    filas = []
    for tk, beta, r_real in zip(tickers, betas, retornos_reales):
        r_capm = rf + beta * (retorno_mercado_esperado - rf)
        alfa = r_real - r_capm
        posicion = "Sobre la SML (subvalorado)" if alfa > 0 else (
            "Bajo la SML (sobrevalorado)" if alfa < 0 else "Sobre la SML exactamente"
        )
        filas.append({
            "Ticker": tk,
            "Beta": round(beta, 3),
            "Retorno_Real_%": round(r_real * 100, 3),
            "Retorno_CAPM_%": round(r_capm * 100, 3),
            "Alfa_Jensen_%": round(alfa * 100, 3),
            "Posicion": posicion,
        })

    return pd.DataFrame(filas).set_index("Ticker")


# ---------------------------------------------------------------------------
# D3. TABLA COMPARATIVA: CAPM VS. INDICADORES HISTORICOS
# ---------------------------------------------------------------------------
def tabla_comparativa_capm_historico(precios: pd.DataFrame, benchmark: pd.Series,
                                      rf_serie: pd.Series, tickers: list) -> pd.DataFrame:
    """
    Construye la tabla comparativa exigida en el criterio D3: para cada
    activo, compara el rendimiento esperado segun CAPM contra el
    rendimiento historico observado, junto con al menos 2 indicadores
    de riesgo historico (volatilidad y maximo drawdown, ya calculados
    en metrics.py).

    Retorna
    -------
    pd.DataFrame con: Beta_OLS, R2, Retorno_Historico_%, Retorno_CAPM_%,
    Diferencia_%, Volatilidad_%, Max_Drawdown_%.
    """
    retornos = precios.pct_change().dropna()
    retornos_benchmark = benchmark.pct_change().dropna()

    rf_promedio = rf_serie.mean()
    retorno_mercado_esperado = retorno_anualizado_de_serie(retornos_benchmark)

    filas = []
    for tk in tickers:
        r_activo = retornos[tk].dropna()
        p_activo = precios[tk].dropna()

        reg = regresion_beta(r_activo, retornos_benchmark)
        beta = reg["beta"]
        r2 = reg["r_cuadrado"]

        retorno_historico = retorno_anualizado_de_serie(r_activo)
        retorno_capm = rf_promedio + beta * (retorno_mercado_esperado - rf_promedio)
        diferencia = retorno_historico - retorno_capm

        vol_anual = m.volatilidad_anualizada(r_activo)
        max_dd = m.maximo_drawdown(p_activo)

        filas.append({
            "Ticker": tk,
            "Beta_OLS": round(beta, 3),
            "R2": round(r2, 3),
            "Retorno_Historico_%": round(retorno_historico * 100, 3),
            "Retorno_CAPM_%": round(retorno_capm * 100, 3),
            "Diferencia_%": round(diferencia * 100, 3),
            "Volatilidad_%": round(vol_anual * 100, 3),
            "Max_Drawdown_%": round(max_dd * 100, 3),
        })

    return pd.DataFrame(filas).set_index("Ticker")


def retorno_anualizado_de_serie(retornos: pd.Series) -> float:
    """Helper: retorno medio mensual anualizado (igual formula que metrics.py)."""
    return retornos.mean() * PERIODOS_POR_ANIO


# ---------------------------------------------------------------------------
# EJECUCION DIRECTA (prueba de ensamblaje del Modulo 3)
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    precios = dl.cargar_precios_desde_csv()
    benchmark = dl.cargar_benchmark_desde_csv()
    rf_serie = dl.cargar_rf_desde_csv()

    rf_promedio = rf_serie.mean()
    retornos_benchmark = benchmark.pct_change().dropna()
    retorno_mercado_esperado = retorno_anualizado_de_serie(retornos_benchmark)

    print(f"Tasa libre de riesgo promedio: {rf_promedio*100:.2f}%")
    print(f"Retorno esperado del mercado (historico benchmark): {retorno_mercado_esperado*100:.2f}%")
    print(f"Prima de riesgo de mercado: {(retorno_mercado_esperado - rf_promedio)*100:.2f}%\n")

    # --- D1: regresion para un activo de ejemplo ---
    ticker_ejemplo = "NVDA"
    retornos = precios.pct_change().dropna()
    reg = regresion_beta(retornos[ticker_ejemplo], retornos_benchmark)
    print(f"D1 - Regresion OLS para {ticker_ejemplo}:")
    print(f"  Beta: {reg['beta']:.3f}")
    print(f"  Alfa de la regresion (mensual): {reg['alfa_regresion_mensual']:.5f}")
    print(f"  R^2: {reg['r_cuadrado']:.3f}")
    print(f"  N observaciones: {reg['n_observaciones']}")
    print(f"  p-value del beta: {reg['p_value_beta']:.5f}\n")

    dispersion = datos_dispersion_regresion(retornos[ticker_ejemplo], retornos_benchmark, reg)
    print(f"  Puntos para scatter: {len(dispersion['puntos_x'])} | "
          f"Puntos para recta: {len(dispersion['recta_x'])}\n")

    # --- D2: SML y alfa de Jensen para varios activos ---
    tickers_ejemplo = ["AAPL", "NVDA", "JNJ", "AGG", "GLD"]
    betas_ejemplo = []
    retornos_reales_ejemplo = []
    for tk in tickers_ejemplo:
        r = regresion_beta(retornos[tk], retornos_benchmark)
        betas_ejemplo.append(r["beta"])
        retornos_reales_ejemplo.append(retorno_anualizado_de_serie(retornos[tk]))

    sml = calcular_sml(rf_promedio, retorno_mercado_esperado)
    print(f"D2 - SML calculada: {len(sml['betas'])} puntos. "
          f"Prima de riesgo: {sml['prima_riesgo_mercado']*100:.2f}%\n")

    tabla_sml = posicion_respecto_sml(tickers_ejemplo, betas_ejemplo, retornos_reales_ejemplo,
                                        rf_promedio, retorno_mercado_esperado)
    print("Posicion respecto a la SML:")
    print(tabla_sml.to_string())
    print()

    # --- D3: tabla comparativa CAPM vs. historico ---
    tabla_d3 = tabla_comparativa_capm_historico(precios, benchmark, rf_serie, tickers_ejemplo)
    print("D3 - Tabla comparativa CAPM vs. Historico:")
    print(tabla_d3.to_string())