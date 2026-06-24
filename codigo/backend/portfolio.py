"""
portfolio.py
------------
Modulo 2 del dashboard: Optimizacion de Portafolios (criterio C).

Implementa la teoria de Markowitz mediante optimizacion formal
(scipy.optimize.minimize) con restriccion long-only (pesos entre 0% y 100%,
suma = 100%):

    - Matriz de correlaciones (C2)
    - Frontera Eficiente (C4)
    - Portafolio de minima varianza (C4)
    - Portafolio tangente / maximo Sharpe (C4)
    - Linea del Mercado de Capitales -- CML (C4)
    - Pesos optimos de ambos portafolios (C5)

Trabajo Final Integrador - Finanzas I - UPB La Paz - Gestion 2026
"""

import numpy as np
import pandas as pd
from scipy.optimize import minimize

import data_loader as dl
import metrics as m

PERIODOS_POR_ANIO = 12  # 12 meses por anio (datos de frecuencia MENSUAL)

# Subconjunto inicial que se muestra al abrir el dashboard por primera vez
# (el usuario puede agregar o quitar activos libremente desde la interfaz).
# Elegido para mostrar diversificacion sectorial y geografica completa desde
# el primer momento, sin que el usuario tenga que tocar nada.
SELECCION_INICIAL = [
    "AAPL",  # Tecnologia - EE.UU.
    "JPM",   # Financiero - EE.UU.
    "JNJ",   # Salud - EE.UU.
    "KO",    # Consumo - EE.UU.
    "XOM",   # Energia - EE.UU.
    "CAT",   # Industrial - EE.UU.
    "TSM",   # Tecnologia - Asia
    "NVO",   # Salud - Europa
    "VALE",  # Materiales - Latam (Brasil)
    "ITUB",  # Financiero - Latam (Brasil)
    "AGG",   # Renta Fija (diversificador clave para minima varianza)
    "GLD",   # Materias Primas / Oro (diversificador clave para tangente)
]


def validar_seleccion(tickers_seleccionados: list):
    """
    Valida que la seleccion de activos sea apta para optimizacion de
    Markowitz. Lanza ValueError con un mensaje claro si no lo es -- esto
    se usa en la API para devolver un error legible al frontend en vez
    de un traceback crudo.
    """
    if len(tickers_seleccionados) < 2:
        raise ValueError(
            "Se necesitan al menos 2 activos seleccionados para calcular "
            "la Frontera Eficiente. Selecciona mas activos."
        )
    no_reconocidos = [tk for tk in tickers_seleccionados if tk not in dl.ACTIVOS]
    if no_reconocidos:
        raise ValueError(f"Tickers no reconocidos en el universo: {no_reconocidos}")


# ---------------------------------------------------------------------------
# 1. INSUMOS BASICOS: RETORNOS ESPERADOS Y MATRIZ DE COVARIANZAS
# ---------------------------------------------------------------------------
def preparar_insumos(precios: pd.DataFrame, tickers_seleccionados: list):
    """
    A partir de la tabla de precios, calcula:
        - mu: vector de retornos esperados anualizados (uno por activo)
        - cov: matriz de covarianzas anualizada (N x N)

    Estos son los dos insumos que necesita CUALQUIER calculo de Markowitz.

    Retorna
    -------
    tuple (mu: np.ndarray, cov: np.ndarray, tickers: list)
    """
    sub_precios = precios[tickers_seleccionados]
    retornos = sub_precios.pct_change().dropna()

    mu = retornos.mean().values * PERIODOS_POR_ANIO
    cov = retornos.cov().values * PERIODOS_POR_ANIO

    return mu, cov, tickers_seleccionados


# ---------------------------------------------------------------------------
# 2. MATRIZ DE CORRELACIONES (criterio C2)
# ---------------------------------------------------------------------------
def matriz_correlaciones(precios: pd.DataFrame, tickers_seleccionados: list) -> pd.DataFrame:
    """
    Calcula la matriz de correlaciones entre los retornos mensuales de los
    activos seleccionados. Los valores van de -1 (correlacion perfecta
    negativa) a +1 (correlacion perfecta positiva).
    """
    retornos = precios[tickers_seleccionados].pct_change().dropna()
    return retornos.corr()


# ---------------------------------------------------------------------------
# 3. FUNCIONES OBJETIVO PARA LA OPTIMIZACION
# ---------------------------------------------------------------------------
def _varianza_portafolio(pesos: np.ndarray, cov: np.ndarray) -> float:
    """Varianza del portafolio: w' * Cov * w"""
    return pesos @ cov @ pesos


def _retorno_portafolio(pesos: np.ndarray, mu: np.ndarray) -> float:
    """Retorno esperado del portafolio: w' * mu"""
    return pesos @ mu


def _sharpe_negativo(pesos: np.ndarray, mu: np.ndarray, cov: np.ndarray, rf: float) -> float:
    """
    Negativo del Sharpe ratio del portafolio (para minimizar, ya que
    scipy.optimize.minimize busca minimos, y queremos MAXIMIZAR el Sharpe).
    """
    retorno = _retorno_portafolio(pesos, mu)
    riesgo = np.sqrt(_varianza_portafolio(pesos, cov))
    if riesgo == 0:
        return 1e6  # penalizacion fuerte si el riesgo es cero (caso degenerado)
    return -(retorno - rf) / riesgo


# ---------------------------------------------------------------------------
# 4. OPTIMIZACION: PORTAFOLIO DE MINIMA VARIANZA (criterio C4)
# ---------------------------------------------------------------------------
def optimizar_minima_varianza(mu: np.ndarray, cov: np.ndarray) -> dict:
    """
    Encuentra los pesos que minimizan la varianza del portafolio, sujeto a:
        - suma de pesos = 1 (100% invertido)
        - cada peso >= 0 (long-only, sin posiciones cortas)

    Retorna
    -------
    dict con pesos, retorno esperado y volatilidad del portafolio resultante.
    """
    n = len(mu)
    pesos_iniciales = np.repeat(1 / n, n)  # punto de partida: equiponderado

    restricciones = [{"type": "eq", "fun": lambda w: np.sum(w) - 1}]
    limites = [(0.0, 1.0) for _ in range(n)]

    resultado = minimize(
        _varianza_portafolio,
        pesos_iniciales,
        args=(cov,),
        method="SLSQP",
        bounds=limites,
        constraints=restricciones,
        options={"maxiter": 1000, "ftol": 1e-12},
    )

    if not resultado.success:
        raise RuntimeError(f"La optimizacion de minima varianza no convergio: {resultado.message}")

    pesos = resultado.x
    return {
        "pesos": pesos,
        "retorno_esperado": _retorno_portafolio(pesos, mu),
        "volatilidad": np.sqrt(_varianza_portafolio(pesos, cov)),
    }


# ---------------------------------------------------------------------------
# 5. OPTIMIZACION: PORTAFOLIO TANGENTE / MAXIMO SHARPE (criterio C4)
# ---------------------------------------------------------------------------
def optimizar_portafolio_tangente(mu: np.ndarray, cov: np.ndarray, rf: float) -> dict:
    """
    Encuentra los pesos que maximizan el Sharpe ratio del portafolio
    (equivalente al "portafolio tangente" en la teoria de Markowitz: el
    punto donde la Linea del Mercado de Capitales toca la Frontera
    Eficiente), sujeto a las mismas restricciones long-only.

    Retorna
    -------
    dict con pesos, retorno esperado, volatilidad y Sharpe del portafolio.
    """
    n = len(mu)
    pesos_iniciales = np.repeat(1 / n, n)

    restricciones = [{"type": "eq", "fun": lambda w: np.sum(w) - 1}]
    limites = [(0.0, 1.0) for _ in range(n)]

    resultado = minimize(
        _sharpe_negativo,
        pesos_iniciales,
        args=(mu, cov, rf),
        method="SLSQP",
        bounds=limites,
        constraints=restricciones,
        options={"maxiter": 1000, "ftol": 1e-12},
    )

    if not resultado.success:
        raise RuntimeError(f"La optimizacion del portafolio tangente no convergio: {resultado.message}")

    pesos = resultado.x
    retorno = _retorno_portafolio(pesos, mu)
    volatilidad = np.sqrt(_varianza_portafolio(pesos, cov))
    sharpe = (retorno - rf) / volatilidad

    return {
        "pesos": pesos,
        "retorno_esperado": retorno,
        "volatilidad": volatilidad,
        "sharpe": sharpe,
    }


# ---------------------------------------------------------------------------
# 6. FRONTERA EFICIENTE COMPLETA (criterio C4)
# ---------------------------------------------------------------------------
def calcular_frontera_eficiente(mu: np.ndarray, cov: np.ndarray, n_puntos: int = 50) -> dict:
    """
    Traza la Frontera Eficiente resolviendo, para una grilla de niveles
    de retorno objetivo, el problema:

        minimizar  w' * Cov * w
        sujeto a   w' * mu = retorno_objetivo
                   sum(w) = 1
                   w >= 0  (long-only)

    Esto es optimizacion formal punto por punto (no fuerza bruta ni
    simulacion aleatoria), que es lo que exige la rubrica para el 100%.

    Parametros
    ----------
    mu, cov : insumos de preparar_insumos()
    n_puntos : int
        Cantidad de puntos a calcular en la frontera (resolucion del grafico).

    Retorna
    -------
    dict con listas paralelas: retornos, volatilidades, y pesos (uno por punto).
    """
    n = len(mu)
    limites = [(0.0, 1.0) for _ in range(n)]
    pesos_iniciales = np.repeat(1 / n, n)

    # El rango de retornos objetivo va desde el retorno minimo posible
    # (portafolio de minima varianza) hasta el retorno del activo individual
    # mas rentable del universo seleccionado.
    minvar = optimizar_minima_varianza(mu, cov)
    retorno_min = minvar["retorno_esperado"]
    retorno_max = mu.max()

    grilla_retornos = np.linspace(retorno_min, retorno_max, n_puntos)

    retornos_frontera = []
    volatilidades_frontera = []
    pesos_frontera = []

    for r_objetivo in grilla_retornos:
        restricciones = [
            {"type": "eq", "fun": lambda w: np.sum(w) - 1},
            {"type": "eq", "fun": lambda w, r=r_objetivo: w @ mu - r},
        ]
        resultado = minimize(
            _varianza_portafolio,
            pesos_iniciales,
            args=(cov,),
            method="SLSQP",
            bounds=limites,
            constraints=restricciones,
            options={"maxiter": 1000, "ftol": 1e-12},
        )
        if resultado.success:
            pesos = resultado.x
            retornos_frontera.append(r_objetivo)
            volatilidades_frontera.append(np.sqrt(_varianza_portafolio(pesos, cov)))
            pesos_frontera.append(pesos)

    return {
        "retornos": np.array(retornos_frontera),
        "volatilidades": np.array(volatilidades_frontera),
        "pesos": pesos_frontera,
    }


# ---------------------------------------------------------------------------
# 7. LINEA DEL MERCADO DE CAPITALES -- CML (criterio C4)
# ---------------------------------------------------------------------------
def calcular_cml(rf: float, portafolio_tangente: dict, n_puntos: int = 50,
                  volatilidad_maxima: float = None) -> dict:
    """
    Calcula la Linea del Mercado de Capitales (CML), que va desde el activo
    libre de riesgo (volatilidad = 0, retorno = rf) hasta y mas alla del
    portafolio tangente, con pendiente = Sharpe ratio del tangente.

        E(R) = rf + Sharpe_tangente * sigma

    Retorna
    -------
    dict con listas de volatilidades y retornos sobre la CML.
    """
    sharpe_tangente = portafolio_tangente["sharpe"]

    if volatilidad_maxima is None:
        # Extender la CML un 50% mas alla de la volatilidad del tangente,
        # para visualizar el tramo de "apalancamiento" (prestar a tasa rf
        # para invertir mas del 100% en el portafolio tangente).
        volatilidad_maxima = portafolio_tangente["volatilidad"] * 1.5

    volatilidades_cml = np.linspace(0, volatilidad_maxima, n_puntos)
    retornos_cml = rf + sharpe_tangente * volatilidades_cml

    return {
        "volatilidades": volatilidades_cml,
        "retornos": retornos_cml,
        "rf": rf,
        "sharpe_tangente": sharpe_tangente,
    }


# ---------------------------------------------------------------------------
# 8. TABLA DE PESOS OPTIMOS (criterio C5)
# ---------------------------------------------------------------------------
def tabla_pesos_optimos(tickers: list, minvar: dict, tangente: dict) -> pd.DataFrame:
    """
    Construye una tabla comparativa de pesos para ambos portafolios optimos,
    lista para mostrar como tabla y como insumo del grafico de barras/torta
    del criterio C5.
    """
    tabla = pd.DataFrame({
        "Ticker": tickers,
        "Peso_Minima_Varianza_%": (minvar["pesos"] * 100).round(2),
        "Peso_Tangente_%": (tangente["pesos"] * 100).round(2),
    }).set_index("Ticker")

    # Verificacion de que los pesos suman 100% (control de calidad interno)
    suma_minvar = tabla["Peso_Minima_Varianza_%"].sum()
    suma_tangente = tabla["Peso_Tangente_%"].sum()
    assert abs(suma_minvar - 100) < 0.5, f"Pesos de minima varianza no suman 100%: {suma_minvar}"
    assert abs(suma_tangente - 100) < 0.5, f"Pesos de tangente no suman 100%: {suma_tangente}"

    return tabla


# ---------------------------------------------------------------------------
# EJECUCION DIRECTA (prueba de ensamblaje completo del Modulo 2)
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    precios = dl.cargar_precios_desde_csv()
    rf_serie = dl.cargar_rf_desde_csv()
    rf_promedio = rf_serie.mean()

    # Ejemplo: portafolio con 8 activos diversificados del universo
    tickers_ejemplo = ["AAPL", "MSFT", "JNJ", "JPM", "KO", "XOM", "AGG", "GLD"]
    mu, cov, tickers = preparar_insumos(precios, tickers_ejemplo)

    print(f"Retornos esperados anualizados (mu):\n{dict(zip(tickers, mu.round(3)))}\n")

    corr = matriz_correlaciones(precios, tickers_ejemplo)
    print("Matriz de correlaciones:")
    print(corr.round(2).to_string())

    minvar = optimizar_minima_varianza(mu, cov)
    print(f"\nPortafolio de Minima Varianza:")
    print(f"  Retorno esperado: {minvar['retorno_esperado']*100:.2f}%")
    print(f"  Volatilidad: {minvar['volatilidad']*100:.2f}%")
    print(f"  Pesos: {dict(zip(tickers, (minvar['pesos']*100).round(2)))}")

    tangente = optimizar_portafolio_tangente(mu, cov, rf_promedio)
    print(f"\nPortafolio Tangente (Maximo Sharpe):")
    print(f"  Retorno esperado: {tangente['retorno_esperado']*100:.2f}%")
    print(f"  Volatilidad: {tangente['volatilidad']*100:.2f}%")
    print(f"  Sharpe: {tangente['sharpe']:.3f}")
    print(f"  Pesos: {dict(zip(tickers, (tangente['pesos']*100).round(2)))}")

    frontera = calcular_frontera_eficiente(mu, cov, n_puntos=20)
    print(f"\nFrontera Eficiente calculada con {len(frontera['retornos'])} puntos.")
    print(f"  Rango de retornos: {frontera['retornos'].min()*100:.2f}% a {frontera['retornos'].max()*100:.2f}%")
    print(f"  Rango de volatilidades: {frontera['volatilidades'].min()*100:.2f}% a {frontera['volatilidades'].max()*100:.2f}%")

    cml = calcular_cml(rf_promedio, tangente, n_puntos=20)
    print(f"\nCML calculada. Pendiente (Sharpe tangente): {cml['sharpe_tangente']:.3f}")
    print(f"  rf: {cml['rf']*100:.2f}%")

    tabla_pesos = tabla_pesos_optimos(tickers, minvar, tangente)
    print(f"\nTabla de pesos optimos:")
    print(tabla_pesos.to_string())