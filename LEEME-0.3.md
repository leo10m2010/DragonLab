# DragonLab 0.3 — Captura automática

Abre DragonLab-0.3.exe. Busca automáticamente DragonBound en el navegador conectado. Al empezar una partida, captura el área del juego y actualiza el mapa, los jugadores, la cámara, el ángulo y el viento. No hay que marcar manualmente el área ni los extremos de la barra.

Si no detecta el navegador, pulsa **Abrir DragonBound** e inicia sesión en la ventana que abre. Este navegador utiliza un perfil propio de DragonLab: no copia la sesión ni la licencia del programa original. Con esa ventana abierta, la conexión se mantiene y vuelve a intentarlo si se interrumpe.

La marca de fuerza aparece sobre la barra cuando hay datos del jugador, una solución de potencia y el juego está en primer plano. Se oculta en la sala, al cambiar de ventana o cuando faltan datos recientes. La marca permite seguir usando el ratón y el teclado del juego. Se ajusta al tamaño de la página y busca la posición real del navegador, incluso en otro monitor. Si no puede determinar la posición de la ventana, conserva la captura en DragonLab y evita colocar una marca en un lugar incorrecto.

**La potencia sigue siendo una estimación.** Los perfiles, tiros especiales y climas necesitan calibración y comprobación con disparos reales. Capturar el mapa automáticamente no significa haber identificado automáticamente todas sus colisiones de terreno: esa parte del modelo mantiene las herramientas de medición y configuración anteriores.

Puedes escoger otro rival en Objetivo. Pausar captura automática vuelve al uso manual. Las herramientas avanzadas siguen disponibles para calibrar perfiles, clima y terreno.

Esta versión prioriza DragonBound. GunBound World sigue siendo experimental y no se ha validado en una partida. No se garantiza funcionamiento automático en cualquier clon.

Validación: conexión real al navegador y detección de sala; comprobación de captura, lectura de imagen, escalado, monitor secundario, ocultación sin partida y actualización de la interfaz; nueve comprobaciones del motor de trayectorias. También se comprobó en el navegador real su posición en el segundo monitor y en una página de prueba la captura exacta del mapa y la detección de la barra con relleno parcial. La aparición y precisión de la marca durante un turno real aún requieren validación.
