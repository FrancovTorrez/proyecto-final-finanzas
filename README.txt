================================================================================
 TRABAJO FINAL INTEGRADOR - FINANZAS I
 Herramienta de Visualizacion Financiera Interactiva
 UPB La Paz - Gestion 2026
================================================================================

GRUPO: [completar con el numero/nombre de grupo]
INTEGRANTES: [completar con los nombres de los integrantes]


--------------------------------------------------------------------------------
1. DESCRIPCION DEL PROYECTO
--------------------------------------------------------------------------------

Esta herramienta es un dashboard interactivo (estilo terminal financiero) que
integra los tres ejes del curso de Finanzas I:

  - Modulo 1: Analisis de Riesgo y Rentabilidad
  - Modulo 2: Optimizacion de Portafolios (Teoria de Markowitz)
  - Modulo 3: Modelos de Valoracion de Activos (CAPM)

Universo de datos: 35 instrumentos financieros (acciones, ADRs y ETFs) mas
el benchmark S&P 500, con 5 anios de historia diaria descargados desde
Yahoo Finance (libreria yfinance).

Arquitectura: backend en Python (Flask) que realiza todos los calculos
financieros, y frontend en HTML/CSS/JavaScript (con Plotly.js) que consume
esos calculos via una API REST local y los visualiza de forma interactiva.


--------------------------------------------------------------------------------
2. REQUISITOS PREVIOS
--------------------------------------------------------------------------------

  - Python 3.11 (recomendado). Tambien funciona con Python 3.9, 3.10 o 3.12.
    NO usar Python 2.7 (viene preinstalado en macOS como "python" del sistema,
    pero no es compatible con este proyecto).

  - Conexion a internet (la primera vez, para descargar los datos historicos
    desde Yahoo Finance). Una vez descargados los CSV en /datos/, el dashboard
    funciona sin conexion.

  - Un navegador web moderno (Chrome, Safari, Firefox, Edge).

  - macOS, Windows o Linux. Las instrucciones de abajo usan sintaxis de
    macOS/Linux (Terminal); en Windows, reemplazar los comandos segun se
    indica en cada paso.

  Como verificar que tienes Python 3.11+ instalado:

      python3 --version

  Si no lo tienes, descargalo desde https://www.python.org/downloads/
  (no usar el Python que viene preinstalado en macOS).


--------------------------------------------------------------------------------
3. ESTRUCTURA DE CARPETAS
--------------------------------------------------------------------------------

  proyecto_final_finanzas/
  |
  |-- codigo/
  |   |-- backend/
  |   |   |-- data_loader.py      -> descarga precios, benchmark, tasa libre de riesgo
  |   |   |-- market_data.py      -> descarga volumen y capitalizacion de mercado
  |   |   |-- metrics.py          -> calcula los 7 indicadores de riesgo/rentabilidad
  |   |   |-- module1.py          -> prepara datos para el Modulo 1 (series, scatter)
  |   |   |-- portfolio.py        -> optimizacion de Markowitz (Modulo 2)
  |   |   |-- capm.py             -> regresion OLS y CAPM (Modulo 3)
  |   |   |-- app.py              -> servidor Flask (API) que conecta todo
  |   |
  |   |-- frontend/
  |       |-- index.html          -> pagina principal del dashboard
  |       |-- style.css           -> estilos visuales
  |       |-- config.js           -> configuracion de la API
  |       |-- app.js              -> logica principal (seleccion de activos, tabs)
  |       |-- modulo1.js          -> graficos del Modulo 1
  |       |-- modulo2.js          -> graficos del Modulo 2
  |       |-- modulo3.js          -> graficos del Modulo 3
  |
  |-- datos/
  |   |-- precios_historicos.csv
  |   |-- benchmark_sp500.csv
  |   |-- tasa_libre_riesgo.csv
  |   |-- volumen_historico.csv
  |   |-- capitalizacion_mercado.csv
  |   |-- indicadores_riesgo_rentabilidad.csv
  |
  |-- requirements.txt
  |-- README.txt                  (este archivo)
  |-- Reporte_GrupoXX.pdf


--------------------------------------------------------------------------------
4. INSTALACION (PASO A PASO)
--------------------------------------------------------------------------------

Todos los comandos se ejecutan desde la Terminal (macOS/Linux) o desde
PowerShell/CMD (Windows), ubicado dentro de la carpeta "proyecto_final_finanzas".

  PASO 4.1 - Crear un entorno virtual de Python
  -----------------------------------------------
  Esto aisla las librerias del proyecto del resto del sistema, evitando
  conflictos de versiones.

  macOS / Linux:
      python3 -m venv venv
      source venv/bin/activate

  Windows:
      python -m venv venv
      venv\Scripts\activate

  Si funciono correctamente, el prompt de la terminal debe mostrar "(venv)"
  al inicio de la linea.

  PASO 4.2 - Instalar las librerias necesarias
  -----------------------------------------------
      pip install -r requirements.txt

  Este paso puede tardar 1-2 minutos. Al finalizar, no debe mostrar ningun
  mensaje de error en rojo.


--------------------------------------------------------------------------------
5. DESCARGA DE DATOS (PRIMERA VEZ UNICAMENTE)
--------------------------------------------------------------------------------

Los archivos CSV en /datos/ YA ESTAN INCLUIDOS en esta entrega, por lo que
este paso es OPCIONAL (solo es necesario si se quiere refrescar los datos
con cotizaciones mas recientes).

Para volver a descargar los datos desde Yahoo Finance:

      cd codigo/backend
      python data_loader.py
      python market_data.py
      cd ../..

Cada comando imprime un resumen al finalizar (cantidad de activos
descargados, rango de fechas, etc.). Si algun ticker no se pudo descargar,
se muestra un aviso pero el proceso continua con el resto.


--------------------------------------------------------------------------------
6. EJECUCION DE LA HERRAMIENTA
--------------------------------------------------------------------------------

  PASO 6.1 - Iniciar el servidor backend (API)
  -----------------------------------------------
  Con el entorno virtual activado (ver Paso 4.1), ejecutar:

      python codigo/backend/app.py

  Debe aparecer en la terminal:

      Cargando datos en memoria...
      Datos cargados: 35 activos, ~1255 dias de historia.
      Tasa libre de riesgo: X.XX% | Retorno mercado esperado: X.XX%
       * Running on http://127.0.0.1:5000

  IMPORTANTE: dejar esta terminal abierta y corriendo. El servidor debe
  seguir activo mientras se usa el dashboard. Para detenerlo al finalizar,
  presionar Ctrl+C en esa misma terminal.

  PASO 6.2 - Abrir el dashboard
  -----------------------------------------------
  Sin cerrar la terminal del Paso 6.1, abrir el archivo:

      codigo/frontend/index.html

  haciendo doble clic sobre el (se abrira en el navegador predeterminado).

  En la esquina superior derecha del dashboard debe aparecer un indicador
  verde que dice "Conectado · 35 activos disponibles". Si aparece en rojo
  o no carga la lista de activos, verificar que el servidor del Paso 6.1
  siga corriendo sin errores.


--------------------------------------------------------------------------------
7. USO DEL DASHBOARD
--------------------------------------------------------------------------------

  - Barra lateral izquierda: seleccionar los activos para el analisis.
    El boton "Seleccion inicial" carga una canasta de 12 activos
    diversificados sugerida por defecto.

  - Pestanias superiores (01, 02, 03): cambian entre los tres modulos.
    Los Modulos 2 y 3 recalculan automaticamente sus graficos cada vez
    que se cambia la seleccion de activos en la barra lateral, sin
    necesidad de recargar la pagina ni reiniciar el servidor.

  - Modulo 1: series de precios normalizadas, dispersion riesgo-rendimiento
    del universo completo, indicadores de mercado integrados (benchmark y
    volumen) y tabla de los 7 indicadores de riesgo/rentabilidad.

  - Modulo 2: matriz de correlaciones, Frontera Eficiente y CML, portafolio
    de minima varianza y portafolio tangente (con sus pesos optimos).

  - Modulo 3: regresion OLS para estimar beta, Linea del Mercado de
    Titulos (SML) con posicionamiento segun el alfa de Jensen, y tabla
    comparativa CAPM vs. rendimiento historico.


--------------------------------------------------------------------------------
8. SOLUCION DE PROBLEMAS COMUNES
--------------------------------------------------------------------------------

  Problema: "command not found: python3" o similar
  Solucion: instalar Python desde https://www.python.org/downloads/
            (version 3.11 o superior).

  Problema: El dashboard muestra el indicador en rojo ("Sin conexion con
            la API")
  Solucion: verificar que la terminal del Paso 6.1 (python app.py) siga
            abierta y sin errores. Si se cerro, volver a ejecutar el
            Paso 6.1 y luego recargar la pagina del navegador (Cmd+R o F5).

  Problema: Error al instalar librerias con pip
  Solucion: verificar que el entorno virtual este activado (el prompt debe
            mostrar "(venv)"). Si el error persiste, actualizar pip con:
                pip install --upgrade pip
            y volver a intentar el Paso 4.2.

  Problema: yfinance no descarga los datos / "rate limit" de Yahoo Finance
  Solucion: esperar unos minutos y reintentar. Como alternativa, usar los
            archivos CSV ya incluidos en /datos/ (Paso 5 es opcional).

  Problema: El puerto 5000 ya esta en uso
  Solucion: cerrar cualquier otro proceso de Flask que pueda estar
            corriendo, o modificar el numero de puerto en la ultima linea
            de codigo/backend/app.py (app.run(debug=True, port=5000)) y
            en codigo/frontend/config.js (API_BASE_URL).


--------------------------------------------------------------------------------
9. NOTAS METODOLOGICAS
--------------------------------------------------------------------------------

  - Fuente de datos: Yahoo Finance (libreria yfinance), con autorizacion
    verbal del docente para su uso como alternativa a Refinitiv Workspace.

  - Periodo de analisis: 5 anios de historia diaria (2022-2026), precios
    ajustados por dividendos y splits (por encima del minimo de 3 anios
    exigido en la consigna).

  - Tasa libre de riesgo: rendimiento de las T-Bills a 3 meses de EE.UU.
    (ticker ^IRX), promedio del periodo de analisis.

  - Benchmark: S&P 500 (ticker ^GSPC).

  - Restriccion de optimizacion: long-only (no se permiten posiciones
    cortas; los pesos de cada activo estan entre 0% y 100%).

  - El uso de inteligencia artificial generativa en el desarrollo de este
    proyecto esta documentado en el Reporte_GrupoXX.pdf, incluyendo los
    prompts utilizados y una evaluacion critica de las respuestas obtenidas.

================================================================================
 FIN DEL README
================================================================================
