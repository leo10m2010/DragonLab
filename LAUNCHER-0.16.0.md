# DragonLab 0.16.0

## Sesiones de 24 horas

En Aprendizaje, elige «24 h» y pulsa «Empezar», o abre `Entrenar-24-Horas.cmd`. Las pruebas de 20 y 40 tiros siguen disponibles. El programa muestra tiempo restante, bloque actual y tiros totales; Detener y Escape cancelan los controles. Cerrar solo el panel de aprendizaje conserva la sesión; cerrar el programa sí la detiene.

La sesión larga conserva los modelos, el turno reservado, los límites de movimiento y la experiencia entre bloques. Guarda cada evaluación aparte y continúa buscando partidas en Avatar Off; llegar al límite de un bloque ya no termina toda la sesión. Las pausas y reconexiones consumen el mismo plazo de 24 horas. No repite un disparo cuyo resultado sea ambiguo.

El equipo y el navegador deben permanecer abiertos, con conexión y una sesión válida del juego. Un chat abierto o un aviso desconocido pausa las acciones. No cierra avisos desconocidos, no resuelve accesos y no reinicia una partida recargando la página. La protección temporal contra suspensión se libera al detener el entrenador. Una sesión larga habilitada no equivale a haber comprobado 24 horas de funcionamiento real.

## Cuando el terreno bloquea el tiro

Primero intenta una trayectoria libre y desplazamientos cortos con apoyo en el terreno. Para abrir paso usa un tiro calculado con mediciones independientes de esa bala y de la partida actual, dentro del rango de fuerzas comprobado. No necesita haber aprobado la puntería contra el enemigo para evaluar la física del vuelo.

Los intentos de excavación se reservan antes de cargar, incluso si después se pierde la confirmación del tiro. Se comprueba después si el punto de terreno quedó abierto; una excavación no cuenta como acierto ni como prueba de autonomía. Existen límites por partida y por obstáculo, además de separación respecto al propio carro y aliados. Los patrones especiales o climas sin comprobar pueden impedir una excavación; esos casos siguen pendientes de medición.

## Archivos

- Para usar la prueba local: `DragonLab-Prueba-0.16.0.zip`.
- Para guardar o subir el código al repositorio: `DragonLabCloud-Preparacion.zip`.
- `DragonLab-Launcher-0.16.0.zip` prepara el launcher; el acceso Cloud real necesita configurar los servicios y publicar una versión con su manifiesto.

Las mediciones existentes se conservan. Los informes de los bloques de la sesión larga se guardan en `evaluaciones-continuas`, junto a los datos locales. Cada sesión incluye `observaciones-nativas.jsonl` con los lanzamientos propios confirmados, sin datos de acceso ni nombres de jugadores; el archivo conserva estas mediciones aunque rote el historial de trabajo. Si el disco no permite guardarlas, el entrenador se detiene con un aviso.

Validación: 373 pruebas Python, cuatro suites de navegador y comprobación de inicio de ambos ejecutables con salida 0. Esta revisión no declara puntería perfecta, mejora de victorias ni disponibilidad de 24 horas ya demostradas.
