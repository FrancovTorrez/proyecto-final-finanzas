"""
metrics.py
----------
Modulo encargado de calcular los indicadores de riesgo y rentabilidad
exigidos en el criterio A2 de la rubrica:

    1. Retorno medio anualizado
    2. Volatilidad anualizada
    3. Sharpe ratio
    4. Sortino ratio
    5. Maximo drawdown
    6. Beta (vs. benchmark)
    7. CVaR al 95% (Conditional Value at Risk) -- indicador "no estandar"

Trabajo Final Integrador - Finanzas I - UPB La Paz - Gestion 2026
"""

import os
import numpy as np
import pandas as pd

import data_loader as dl

PERIODOS_POR_ANIO = 12  # 12 meses por anio (datos de frecuencia MENSUAL)


# ---------------------------------------------------------------------------
# 1. RETORNOS
# ---------------------------------------------------------------------------
def calcular_retornos(precios: pd.DataFrame) -> pd.DataFrame:
    """
    Calcula los retornos simples mensuales a partir de una tabla de precios.

    Parametros
    ----------
    precios : pd.DataFrame
        Precios de cierre ajustado, columnas = activos, indice = fechas.

    Retorna
    -------
    pd.DataFrame
        Retornos simples mensuales (mismo shape que precios, menos 1 fila).
    """
    retornos = precios.pct_change().dropna(how="all")
    return retornos


# ---------------------------------------------------------------------------
# 2. INDICADORES INDIVIDUALES
# ---------------------------------------------------------------------------
def retorno_anualizado(retornos: pd.Series) -> float:
    """Retorno medio mensual anualizado: r_mensual_promedio * 12."""
    return retornos.mean() * PERIODOS_POR_ANIO


def volatilidad_anualizada(retornos: pd.Series) -> float:
    """Desviacion estandar mensual anualizada: sigma_mensual * sqrt(12)."""
    return retornos.std() * np.sqrt(PERIODOS_POR_ANIO)


def sharpe_ratio(retornos: pd.Series, rf_anual: float) -> float:
    """
    Sharpe ratio = (retorno anualizado - rf) / volatilidad anualizada.
    Mide el exceso de retorno por unidad de riesgo TOTAL.
    """
    r_anual = retorno_anualizado(retornos)
    vol_anual = volatilidad_anualizada(retornos)
    if vol_anual == 0:
        return np.nan
    return (r_anual - rf_anual) / vol_anual


def sortino_ratio(retornos: pd.Series, rf_anual: float) -> float:
    """
    Sortino ratio = (retorno anualizado - rf) / volatilidad a la baja anualizada.
    Solo penaliza la volatilidad de retornos NEGATIVOS (downside risk).
    """
    r_anual = retorno_anualizado(retornos)
    retornos_negativos = retornos[retornos < 0]
    if len(retornos_negativos) == 0:
        return np.nan
    downside_vol_anual = retornos_negativos.std() * np.sqrt(PERIODOS_POR_ANIO)
    if downside_vol_anual == 0:
        return np.nan
    return (r_anual - rf_anual) / downside_vol_anual


def maximo_drawdown(precios: pd.Series) -> float:
    """
    Maximo drawdown = peor caida porcentual desde un maximo historico (peak)
    hasta el minimo subsecuente (trough), en toda la serie de precios.

    Retorna un valor negativo (ej. -0.35 significa una caida del 35%).
    """
    maximo_acumulado = precios.cummax()
    drawdown = (precios - maximo_acumulado) / maximo_acumulado
    return drawdown.min()


def calcular_beta(retornos_activo: pd.Series, retornos_benchmark: pd.Series) -> float:
    """
    Beta = Cov(r_activo, r_benchmark) / Var(r_benchmark)

    Mide el riesgo sistematico del activo respecto al mercado.
    """
    df = pd.concat([retornos_activo, retornos_benchmark], axis=1).dropna()
    if df.shape[0] < 2:
        return np.nan
    covarianza = df.cov().iloc[0, 1]
    varianza_benchmark = df.iloc[:, 1].var()
    if varianza_benchmark == 0:
        return np.nan
    return covarianza / varianza_benchmark


def cvar_95(retornos: pd.Series, nivel_confianza: float = 0.95) -> float:
    """
    CVaR (Conditional Value at Risk / Expected Shortfall) al 95%.

    Es el promedio de las perdidas en el peor (1 - nivel_confianza) % de
    los dias -- es decir, el promedio de la "cola" de perdidas mas alla
    del VaR. A diferencia del VaR (que solo marca un punto de corte),
    el CVaR informa la severidad esperada DENTRO de ese peor escenario.

    Retorna un valor negativo (perdida mensual promedio en el peor 5%).
    """
    var_95 = retornos.quantile(1 - nivel_confianza)
    cola_perdidas = retornos[retornos <= var_95]
    if len(cola_perdidas) == 0:
        return np.nan
    return cola_perdidas.mean()


# ---------------------------------------------------------------------------
# 3. TABLA RESUMEN PARA TODOS LOS ACTIVOS
# ---------------------------------------------------------------------------
def calcular_tabla_indicadores(precios: pd.DataFrame, benchmark: pd.Series,
                                rf_serie: pd.Series) -> pd.DataFrame:
    """
    Calcula los 7 indicadores para cada activo de la tabla de precios.

    Parametros
    ----------
    precios : pd.DataFrame
        Precios de cierre ajustado de todos los activos.
    benchmark : pd.Series
        Precios de cierre ajustado del benchmark (S&P 500).
    rf_serie : pd.Series
        Serie de la tasa libre de riesgo anualizada (en decimales).

    Retorna
    -------
    pd.DataFrame
        Una fila por activo, una columna por indicador.
    """
    retornos = calcular_retornos(precios)
    retornos_benchmark = benchmark.pct_change().dropna()

    # Tasa libre de riesgo: se usa el promedio del periodo como escalar,
    # ya que Sharpe/Sortino requieren un valor anualizado unico.
    rf_promedio = rf_serie.mean()

    filas = []
    for activo in precios.columns:
        r = retornos[activo].dropna()
        p = precios[activo].dropna()

        info = dl.ACTIVOS.get(activo, {})
        fila = {
            "Ticker": activo,
            "Nombre": info.get("nombre", activo),
            "Tipo": info.get("tipo", "N/D"),
            "Sector": info.get("sector", "N/D"),
            "Region": info.get("region", "N/D"),
            "Retorno_Anualizado_%": retorno_anualizado(r) * 100,
            "Volatilidad_Anualizada_%": volatilidad_anualizada(r) * 100,
            "Sharpe_Ratio": sharpe_ratio(r, rf_promedio),
            "Sortino_Ratio": sortino_ratio(r, rf_promedio),
            "Max_Drawdown_%": maximo_drawdown(p) * 100,
            "Beta": calcular_beta(r, retornos_benchmark),
            "CVaR_95_%": cvar_95(r) * 100,
        }
        filas.append(fila)

    tabla = pd.DataFrame(filas).set_index("Ticker")
    return tabla


# ---------------------------------------------------------------------------
# 4. EJECUCION DIRECTA
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    # Uso: python metrics.py
    # Carga los CSV ya descargados por data_loader.py y calcula la tabla.
    precios = dl.cargar_precios_desde_csv()
    benchmark = dl.cargar_benchmark_desde_csv()
    rf_serie = dl.cargar_rf_desde_csv()

    tabla = calcular_tabla_indicadores(precios, benchmark, rf_serie)

    ruta_salida = os.path.join(dl.RUTA_DATOS, "indicadores_riesgo_rentabilidad.csv")
    tabla.to_csv(ruta_salida, encoding="utf-8-sig")

    print(f"Tabla de indicadores calculada para {tabla.shape[0]} activos.")
    print(f"Guardada en: {ruta_salida}\n")
    print(tabla.round(3).to_string())