# DragonLab 0.1

Aplicación propia para Windows, creada después de inspeccionar DragonboundGPT 0.1.14 con REA.

## Abrir

Haz doble clic en **DragonLab.exe**. El ejecutable incluye Python, la interfaz y sus dependencias. No necesita que DragonboundGPT esté ejecutándose.

## Uso manual

1. Selecciona el vehículo y ajusta el ángulo y el viento.
2. Pulsa **Tu posición** y marca al jugador; después marca el objetivo.
3. Lee la potencia de 0 a 400 y la curva calculada.
4. Usa **Capturar área** para seleccionar con el ratón el rectángulo completo de juego. Selecciona solo el campo, conservando su proporción 800 × 600.
5. **Capa sobre el juego** muestra la curva sobre esa área; vuelve a pulsarlo para ocultarla. La capa deja pasar los clics.

También puedes abrir una captura guardada, ajustar gravedad/velocidad/viento, calibrar con la potencia observada de un disparo y guardar perfiles y sesiones.

El viento manual usa grados matemáticos: 0° este, 90° norte, 180° oeste y 270° sur. El ángulo de tiro es local a la orientación elegida hacia el objetivo.

## Lectura automática experimental

Con el navegador del juego ya disponible en `http://127.0.0.1:9222`, pulsa **Conectar lectura experimental**. En una partida compatible se leen jugador, enemigos, posiciones, vehículos, ángulos y campos de viento. El menú superior permite seleccionar un enemigo concreto.

La conexión consulta el navegador directamente; no consume el servicio de DragonboundGPT. La inspección real detectó seis jugadores y distinguió al jugador propio. También leyó cámara y campos de viento. Si el juego cambia de estructura o está en una sala sin partida, aparece «Esperando partida» y sigue disponible el modo manual. La dirección del viento y la alineación de la cámara todavía requieren comparación en partida. Si capturaste el campo antes de conectarte, vuelve a comprobar su ubicación.

## Visor de celular

Pulsa **Visor de celular** y copia el enlace en un dispositivo conectado a la misma red Wi-Fi. Windows puede pedir acceso de red para el servidor local. El enlace contiene una clave temporal; el visor muestra los datos y la curva. El servidor termina al cerrar DragonLab.

## Límites de esta versión

- Los 23 vehículos tienen perfiles base editables. Un perfil no garantiza que sus disparos especiales estén modelados.
- Tornado, Mirror y otros climas se marcan como aproximaciones; seleccionar un clima **no aplica todavía su física**.
- No hay colisiones con terreno, OCR, autodisparo, compensación avanzada de proyectiles ni calibración a partir del protocolo del servidor.
- La precisión real requiere calibrar y probar. El indicador de error mide solo el redondeo de potencia dentro del modelo, no el error frente al juego.
- La aplicación no reproduce el sistema de licencias, recursos gráficos ni servicios remotos del original.

Consulta **INFORME-REA.md** para la evidencia y la cobertura del análisis. El código propio está incluido en `app.py`, `core.py`, `cdp.py` y `viewer.html`.
