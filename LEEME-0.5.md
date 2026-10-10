# DragonLab 0.5

Abre **DragonLab-0.5.exe**. La captura busca la partida automáticamente. Si no encuentra un navegador conectado, usa **Abrir juego** y entra a DragonBound desde esa ventana.

La pantalla principal conserva tres controles: abrir el juego, pausar la captura y ajustes. Detecta los jugadores vivos, mantiene un objetivo, sigue la cámara y coloca la marca de fuerza sobre la barra del juego. Las líneas verdes son una predicción; las azules siguen las balas observadas. Las marcas naranjas señalan el objetivo y las líneas verticales señalan Mirror y Tornado.

## Cambios de esta versión

- Cámara con tamaño real del dibujo y transformación del juego: corrige desplazamientos al cambiar tamaño, mover la cámara y seguir tiros altos.
- Ángulo corregido por orientación e inclinación del terreno, conservando los tiros hacia atrás y los ángulos negativos.
- Lectura del terreno real y sus agujeros. Una bala rápida ya no salta una plataforma fina entre dos puntos de cálculo.
- Mirror y Tornado se leen de las columnas activas del juego. El clima de la siguiente ronda no se confunde con el actual.
- Búsqueda de todas las fuerzas enteras cuando hay Mirror o Tornado. Corrección de las entradas a Mirror desde arriba.
- Reconstrucción de las curvas observadas con cambios de velocidad, aceleración, ondas y órbitas enviados por el servidor. Cuando una bala tiene otro comportamiento, se conservan sus posiciones visibles medidas.
- Cambio automático de mapa y conexión al comenzar otra partida.
- Un solo cálculo a la vez para evitar acumular trabajo durante el movimiento.
- Mediciones automáticas por vehículo y tiro, incluidas balas simultáneas con la misma salida. Rayos auxiliares, balas retrasadas y salidas distintas no se mezclan en un ajuste de fuerza.

## Calibración automática

Juega y dispara normalmente. Se guardan las salidas del cañón y las muestras que pueden atribuirse al jugador. El programa necesita al menos cuatro muestras consistentes, varias fuerzas y suficiente diferencia entre ellas antes de aplicar un ajuste. Comprueba cada muestra con un ajuste calculado sin esa muestra. Para un viento ya medido también utiliza la aceleración nativa observada. Si cambian las mediciones, suspende el ajuste y vuelve a calibrar.

Se comprobó un ajuste de **Armor, tiro 2**, con nueve tiros reales. Esa medición queda conservada en `calibracion-validada-Armor-tiro2.json`. Posteriormente se detectaron salidas con otra escala y el programa suspendió el ajuste anterior para medirlas de nuevo: un ajuste observado en una sesión no garantiza todas las partidas. Los demás perfiles se miden al usarlos; no se presentan como calibrados solo por existir en la lista. No hace falta instalar ni entrenar una IA externa.

## Alcance

La validación de esta versión corresponde a DragonBound. GunBound World sigue siendo experimental y pendiente de prueba en partida. Los tiros especiales con homing, cambios o rebotes propios necesitan mediciones de su comportamiento para una predicción completa antes del disparo. La curva azul observada no equivale a una garantía de acierto de la curva verde.

No ejecutes simultáneamente varias versiones: dibujarían varias capas sobre el mismo juego. La compilación es independiente de DragonboundGPT.
