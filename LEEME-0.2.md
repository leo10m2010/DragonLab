# DragonLab 0.2 · DragonBound

Abre **DragonLab-0.2.exe**. Incluye Python y las dependencias. Añade barra de fuerza, guía sobre el juego, motores de climas y varios proyectiles, terreno, OCR calibrado, seguimiento visual, búsqueda de ángulos y disparo asistido.

## Barra de fuerza: dónde soltar

La barra verde bajo el resultado muestra la potencia recomendada. La marca naranja dice **SUELTA AQUÍ** e indica fuerza y porcentaje. Ejemplo: **193 / 400 = 48,2 %**. Depende de que posiciones, ángulo, viento y calibración sean correctos.

Para colocar la marca sobre la barra de DragonBound:

1. Pulsa **Marcar barra del juego**.
2. Haz clic en el inicio de la barra (0) y después en su extremo final (400).
3. La guía muestra dónde soltar y deja pasar los clics al juego.
4. **Mostrar / ocultar marca** alterna la guía. Si cambias tamaño o posición de la ventana, vuelve a marcar los extremos.

## Posiciones y navegador

En modo manual, selecciona vehículo, ángulo y viento; marca **Tu posición** y **Objetivo** sobre una captura del área de juego. **Capturar área** ubica la ventana para la capa de trayectoria. **Capa sobre el juego** alterna esa curva.

En **Motor / juegos / ángulos → Juego y navegador**, elige DragonBound. Puedes usar un navegador que exponga `http://127.0.0.1:9222` o pulsar **Abrir navegador del juego**. Este último abre un perfil propio: debes iniciar sesión tú. Busca páginas, aplica la página del juego y pulsa **Conectar lectura experimental** en la pantalla principal.

La lectura de DragonBound se comprobó antes en partidas reales: posiciones, identificación del jugador, vehículo, ángulo y campos de viento/cámara. Si no hay partida compatible, sigue disponible el modo manual. La versión ampliada requiere todavía una prueba completa de precisión dentro del juego. El viento manual usa 0° este, 90° norte, 180° oeste y 270° sur.

## Proyectiles, clima y terreno

En **Motor / juegos / ángulos → Proyectiles y clima**:

- Disparo `0` significa tiro 1; `1`, tiro 2; `2`, SS.
- Configura orientación, límites, correcciones de velocidad/ángulo y cuantización.
- **Añadir Mirror** y **Añadir Tornado** piden ubicación en coordenadas del mapa. Pulsa **Aplicar motor** después. Elegir solo el nombre del clima en la pantalla principal no informa su posición ni aplica su interacción.
- El entorno JSON permite `activeWeathers`, terreno y variantes personalizadas. Mirror usa `typeId: 7`; Tornado usa `typeId: 8`, `x` y `size`.
- El modelo NAK de backshot debe habilitarse expresamente y no reproduce todas las interacciones subterráneas.

Los modelos de varios proyectiles incluyen Bigfoot, Dragon, Grub, Mage, Turtle y Trico. Son estimaciones: no se garantizan todos los comportamientos especiales, daño o decisiones del servidor.

**Visión / terreno / disparo → Terreno** permite seleccionar un color del suelo sobre una captura y revisar la superficie detectada. El motor corta la trayectoria al encontrarla. El color puede confundirse con personajes o fondos y no reconstruye todas las cuevas; revisa la línea y renueva el terreno al cambiar de mapa.

## Calibración y OCR

Los perfiles se guardan por juego y vehículo. Puedes calibrar con una potencia observada o importar medidas con campos `power`, `vx`, `vy`, `ax`, `ay`, `wind`, `wind_angle`. El ajuste requiere al menos dos potencias distintas y muestra residuos antes de aplicarlo.

El seguimiento visual mide un proyectil por color. Requiere cámara fija, escala conocida y un origen temporal de lanzamiento conocido para convertir velocidad medida en velocidad inicial.

El OCR es local: enseña recortes de números conocidos y después lee los números de la captura. Necesita ejemplos suficientes y recalibración al cambiar fuente, tema o tamaño. No es una IA universal ni llama a servicios externos.

## Disparo asistido

En **Visión / terreno / disparo → Disparo**, selecciona la ventana y calibra duración máxima de carga o extremos de la barra. Ajusta en el juego el ángulo y tipo de tiro que estás simulando. Cada ejecución requiere **Habilitar UN disparo**; **Simulación** viene activada.

La simulación no envía entradas. El modo real ejecuta una sola carga con Espacio o arrastre. La cuenta regresiva permite enfocar el juego. Datos caducados o pérdida de foco bloquean el inicio; Esc interrumpe la secuencia. Si la carga ya comenzó, liberar tecla o ratón puede producir un disparo según el juego. No se probaron entradas reales en una partida durante la construcción.

## Visor y archivos

**Visor de celular** ofrece un enlace temporal para la misma red Wi-Fi e incluye potencia, barra de fuerza, viento y curvas. El servidor se cierra con la aplicación. Windows puede solicitar acceso de red.

Puedes guardar sesiones, perfiles y plantillas OCR. El código editable está incluido. **INFORME-REA.md** detalla la evidencia y cobertura.

## Otros clones e IA del original

GunBound World queda para después, según lo solicitado. Su página pública carga y usa dimensiones y potencia diferentes; el conector experimental no está validado en partida. No se promete compatibilidad automática con cualquier clon.

`AppData/Local/DragonboundGPT` contiene diagnósticos, licencias y datos del navegador. Sus modelos `.tflite` están bajo el almacén de modelos de Chrome. No se encontró evidencia suficiente para atribuirlos al cálculo de tiros de DragonboundGPT. Lo comprobado en su interfaz es física, calibración y lectura del juego; la lógica nativa no está completamente descompilada.
