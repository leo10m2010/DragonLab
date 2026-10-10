# Inspección de DragonboundGPT y reconstrucción DragonLab

Fecha: 9 de octubre de 2026.

## Identidad observada

- Instalación: `E:\db\DragonboundGPT`.
- Aplicación: DragonboundGPT Desktop, versión 0.1.14.0.
- Archivo principal: `DragonboundGPT.exe`, 170.680.320 bytes, Windows PE x64.
- SHA-256: `e11ec028464322651f61f24107ab6239be534bb683cf46bbe500752dccf36666`.
- REA `inspect_managed_artifact`: no contiene directorio CLI ni metadatos CIL; no es una aplicación .NET administrada.
- Evidencia REA: `ev_6d0c8525604818d04ec4dcbee5ff69a619ef026c229ebd6deb862fd769637d87`.

## Arquitectura y funciones

La aplicación estaba ejecutándose. La lista de módulos cargados mostró `dbai_entry.dll`, Python 3.11, PySide6/Qt, OpenCV, NumPy y bibliotecas de red. El contenedor contiene marcadores `NUITKA_ONEFILE_*`; el directorio temporal de ejecución contiene la interfaz distribuida y el HUD QML. Esto sustenta una aplicación Python compilada con Nuitka, empaquetada en un archivo.

El paquete incluye una interfaz React distribuida como JavaScript y una capa Qt Quick transparente que no toma foco ni captura los clics. La interfaz calcula recomendaciones de potencia, muestra posiciones de jugadores, perfiles por vehículo, curvas y un visor compartido. El HUD consume un estado publicado por un puente Qt.

REA `analyze_javascript_application` analizó `windvision/web_dist`. La respuesta excedió el límite del transporte MCP, pero el análisis completo quedó retenido y se exportó correctamente a un expediente local de trabajo. No se repitió el análisis para solicitar una respuesta mayor.

- Evidencia: `ev_ad771424b681fe06636b2ef4cff385db8d3bcdd0e150e4f049de2b140b63d014`.
- Grafo: `jag_ce1089ce4f076d71f9b5e0b8ea5a3bc5716736106874068a83ebf661ca8adcc7`.

La lectura directa del JavaScript distribuido mostró perfiles de 23 vehículos, potencia 0–400, compensación de salida del cañón, aceleraciones de gravedad/viento, calibración a partir de disparos observados, tratamiento de Tornado/Mirror y proyectiles especiales. Estos son hallazgos estáticos; no prueban que cada rama se ejecutara.

Las cadenas de nombres de módulos incluyen `windvision.trajectory`, `windvision.autoshot`, `windvision.cdp`, `windvision.ocr`, `windvision.terrain` y `windvision.shot_calibration`. Los nombres son evidencia de componentes, pero por sí solos no prueban su comportamiento.

Los diagnósticos locales mostraron eventos de lectura de jugadores, cálculo de trayectorias, actualización de cámara, adquisición de geometría y autodisparo. Un evento histórico registró potencia 223, error previsto 1,216 píxeles y un entorno con Tornado. No se provocó un disparo durante la investigación.

## Navegador y observación real

REA encontró una página de DragonBound en el endpoint local `http://127.0.0.1:9222` y en el origen `https://dragonbound.net`.

- Evidencia REA: `ev_2030465bf7a5b66ef8b7f7bded62bb91c0154830178cd5f2fc288972fb7f9eeb`.

El conector propio de DragonLab consulta descriptores de objetos en los cierres de los manejadores de teclado y copia campos de juego seleccionados. En una observación real devolvió seis jugadores, identificó al jugador propio y leyó coordenadas, vehículo, ángulo, dirección, cámara y campos de viento. También se comprobó la transición a «Esperando partida» cuando dejaron de estar disponibles los objetos compatibles. Esta prueba no establece compatibilidad con otras versiones del cliente ni valida la física del viento.

No se invocaron métodos de disparo, compra, chat o movimiento. Los datos de cuentas, almacenamiento, licencias y tokens del original no se reutilizan en DragonLab.

## Reconstrucción propia

DragonLab usa una interfaz Tk, un servidor HTTP para su visor y un cliente CDP implementado con la biblioteca estándar de Python. Su algoritmo balístico elimina algebraicamente la velocidad para resolver tiempo y potencia bajo aceleración constante. La interfaz y los algoritmos están escritos de nuevo. Los perfiles numéricos base proceden de los valores observados en la interfaz distribuida; los perfiles pueden ajustarse y guardarse.

La aplicación funciona en modo manual sin DragonboundGPT. La lectura automática conecta al navegador directamente. Incluye un ejecutable Windows y el código editable.

## Verificación

Se verificaron:

1. Alcance analítico simétrico a izquierda y derecha, con solución conocida.
2. Recuperación de una potencia conocida en tres configuraciones de viento.
3. Calibración de escala de velocidad a partir de potencia observada.
4. Rechazo de datos no finitos, modelos inválidos y objetivos fuera de alcance.
5. Restricción de los endpoints CDP a loopback.
6. Lectura real del navegador en partida y en espera.
7. Apertura de la interfaz sin excepciones, respuesta del visor y rechazo de una clave incorrecta.
8. Apertura y cierre del ejecutable empaquetado.

En la geometría del caso histórico mencionado, el modelo base propio devuelve 225, frente a 223 del original con clima. Se documenta esa diferencia: no se presenta una equivalencia física completa ni una precisión de juego garantizada.

## Cobertura pendiente

La clasificación del ejecutable y el análisis de la interfaz distribuida están realizados. La lógica Python compilada no se descompiló: los proveedores nativos Ghidra/Hopper/IDA no están configurados. La lógica interna recuperada no equivale al código fuente original.

El estado inicial 0.1 dejaba pendientes vehículos especiales, Tornado/Mirror, terreno, OCR y autodisparo. La ampliación siguiente implementa motores y controles propios para varias de esas funciones. La implementación no equivale a validación de precisión en juego; el análisis nativo sigue siendo parcial.

## Ampliación 0.2 y carpeta adicional

Se inventarió `C:\Users\PC-4640\AppData\Local\DragonboundGPT`. Sus directorios superiores son `BrowserData`, `Diagnosticos` y `license`. Hay diez `.tflite` y un `sentencepiece.model`; todos están bajo `BrowserData/optimization_guide_model_store`. También hay recursos de voz WebAssembly del navegador. Se revisaron nombres, rutas y tamaños; no se usaron cuentas, cookies o licencias en la reconstrucción.

**Observación:** los modelos están dentro del almacén del navegador. **Inferencia limitada:** su presencia no demuestra que el asistente los invoque para calcular tiros. **Desconocido:** no se ha descartado completamente otra lógica de inferencia en el código Python compilado ni en servicios remotos. El cálculo visible usa física, perfiles numéricos y calibración mediante observaciones. El nombre GPT o AI no prueba un modelo generativo.

La extracción temporal pasó a `onefile_24904_134360372710978496`. Se reutilizaron los hallazgos anteriores y se contrastaron constantes y ramas del JavaScript distribuido, sin copiar su interfaz ni recursos gráficos.

DragonLab 0.2 incorpora:

- Barra de fuerza con potencia, porcentaje y marca de liberación; guía transparente calibrada con los extremos de la barra real.
- Segmentos para Mirror/Tornado, con cruces, inversiones y restauración de aceleración basados en la interfaz observada. Requieren contraste con el servidor.
- Patrones para Bigfoot, Dragon, Grub, Mage, Turtle y Trico; selección de tiro y modelo explícito de backshot NAK. No cubren todos los proyectiles especiales.
- Colisiones por alturas, polígonos, máscaras y filas comprimidas; detección visual de superficie por color que requiere revisión.
- Calibración conjunta de velocidad inicial, gravedad y acoplamiento de viento; importación de muestras y medidas con cámara fija.
- OCR por plantillas locales y seguimiento por color. No se añadió un servicio externo de IA.
- Disparo asistido de una ejecución, con simulación por defecto, habilitación por disparo, comprobación de foco y caducidad. No se realizaron tiros reales durante las pruebas.
- Conectores separados, perfiles por juego y búsqueda de ángulos. El cálculo ocurre fuera del hilo de la interfaz.

## Verificación de la ampliación

Pasaron nueve comprobaciones del motor: solución analítica, Mirror, fases Tornado, representaciones de terreno, corte por impacto, seis patrones, ajuste de parámetros, inversión numérica y búsqueda de ángulos. Una solución numérica simple tomó aproximadamente 16 ms; no se extrapola a todos los entornos.

Pasaron diez comprobaciones de integración: OCR sobre un número distinto de sus ejemplos, superficie conocida, recuperación de aceleración de un proyectil renderizado, simulación sin entradas, consumo de habilitación, caducidad, cancelación, liberación de entrada con pérdida de foco usando un backend simulado, validación de adaptadores y apertura de paneles/guía. Los cálculos básicos y el visor HTTP conservaron sus comprobaciones anteriores.

El navegador de depuración no estuvo disponible en la última pasada. Las observaciones reales de partidas corresponden a la fase previa; las pruebas adicionales son analíticas, visuales, de interfaz y con datos controlados. No se presentan como validación completa de precisión o disparo en partida.

## GunBound World y compatibilidad

REA abrió `https://play.gunbound.world/` en un Chromium propio y observó la pantalla de acceso, escenario lógico 1280 × 720 y recursos JavaScript. Evidencia: `ev_7a137e6682dffa4126af5773b7c1af5fe0442506a4f88907ca371865b7c36432`. No se inició sesión ni se ejecutaron acciones de juego.

Su interfaz usa potencia 0–100, estado Colyseus y perfiles diferentes: por ejemplo, gravedad 392 para Armor, frente al perfil 73,5 de DragonboundGPT. Las unidades y escalas pertenecen a cada modelo; esos números no establecen equivalencia entre servidores.

Por petición del usuario, GunBound World queda para después. Existe un conector experimental sin validación en partida. Captura manual y perfiles facilitan adaptaciones, pero no garantizan que cualquier clon comparta física, estructura o proyectiles.

## Cobertura abierta

No se completó la descompilación nativa. Sigue pendiente probar precisión en partidas reales, ajustar vehículos/proyectiles no cubiertos, integrar calibración autoritativa por mensajes del servidor, validar viento/cámara y modelar daño y todas las interacciones subterráneas. DragonLab 0.2 es una ampliación funcional comprobada con las pruebas descritas; no se certifica una réplica completa del original.


## Actualización 0.3: automatización

Se observó una captura de una partida real por CDP. El DOM de DragonBound conserva gameScreen, powerMarkArea y powerBar. La barra de relleno cambia de anchura; powerMarkArea conserva el rango completo. DragonLab lee estos rectángulos, captura la página sin enfocar ni enviar acciones y calcula el origen físico con la ventana de renderizado de Chrome. El origen observado fue (1920,143), en el segundo monitor. La captura se actualiza cada 0,8 segundos; al fallar la conexión, el lector vuelve a intentarlo. La guía requiere jugadores identificados, objetivo, partida visible, foco y solución. Se oculta fuera de la partida y si faltan datos recientes.

Pruebas: navegador de prueba con captura real 800×600 y barra parcialmente llena; monitor secundario y DPI; actualización automática de la imagen; creación y reubicación de guía mediante sustituto de ventana; ocultación fuera de foco y en sala; recuperación después de un rechazo de conexión; conexión al navegador real en sala; nueve comprobaciones del motor; ejecutable inicia y termina correctamente en comprobación sin ventana visible. Pendiente: comprobar alineación de la guía y precisión del tiro durante un turno real. La captura visual automática no implica reconstrucción automática de todas las colisiones del terreno.


## Actualización 0.3.1

Ante movimiento vertical del juego reportado por el usuario, se eliminó el clip de Page.captureScreenshot: se captura la vista y se recorta localmente. Esto evita solicitar geometría de captura distinta del viewport. Es una corrección de una causa probable, todavía sin confirmación en la partida real. La prueba con navegador propio conserva innerWidth, innerHeight y devicePixelRatio antes y después. Se desacoplaron imágenes (1,5 s) de estado (0,25 s); fallo de imagen no interrumpe estado. La guía reutiliza ventana y elementos gráficos, se recoloca sin reconstruirse y aparece sin activación explícita. Se excluyen cambios exclusivamente de cámara del cálculo físico; se mantiene el objetivo y se respeta selección explícita. No se cambió la calibración física medida ni se afirma precisión superior sin disparos de validación.


## Actualización 0.4: proyectiles, cámara y calibración

En la partida observada, los objetos shots eran instancias Shot2. Sus coordenadas no estaban en x/y directamente: shot.s tenía seis números (origen X/Y, ángulo, velocidad, aceleración X/Y), total_elapsed_time el tiempo transcurrido, y children[0].worldTransform la posición renderizada. Se observó un inicio [1254,-4,145,672,11,439] y un tiempo de tiro de 5000 ms. Se leyó camera_container.worldTransform y original_w=800, original_h=600. No se enviaron acciones al juego.

La lectura anterior ignoraba player.body; ahora se lee. Los parámetros de salida observados fueron ICE: 58°/50 px en tiro 1 y 40°/40 px en 2/SS; GRUB: 58°/40 px en los tres. Para GRUB mirando a la izquierda con cuerpo -12°, la salida calculada es (-28,-29), consistente con el origen observado relativo al jugador (1282,25). Estos valores de salida están guardados como medidas; no implican calibración de fuerza.

La nueva capa utiliza la matriz afín del renderizador, dibuja guías previstas y estelas observadas con colores distintos, conserva la ventana y sus líneas, deja libres los controles inferiores y no acepta foco. La interfaz principal oculta controles técnicos en Ajustes. CalibrationBook separa juego/vehículo/tiro, requiere medidas reales atribuibles y muestra los estados base/medido/ajustado. Se probaron ajustes de 23 perfiles con datos de prueba que permanecen en work/, sin convertirlos en evidencia real. La observación adicional tras terminar la partida no obtuvo nuevos tiros; por tanto no se afirma que todos los carros estén calibrados.
