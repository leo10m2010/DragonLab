# Qué aprende del rival y cómo se utiliza

El observador es una fuente separada de información numérica sobre el juego. No es un modelo de lenguaje nuevo ni convierte cada tiro del enemigo en una calibración del carro propio.

| Información | Qué se guarda | Uso |
| --- | --- | --- |
| Posición | Coordenadas del mundo al observar su turno y al disparar o terminarlo | Frecuencias de desplazamiento por carro; mover la cámara no cuenta como movimiento |
| Desplazamiento | Distancia y cambio relativo al punto donde estaba el jugador propio | Acercamientos, alejamientos y ausencia de desplazamiento apreciable; los casos ambiguos quedan fuera del patrón |
| Tiro con propietario nativo | Modalidad y trayectoria inicial observables, cuando existen los metadatos | Registro separado de comportamiento y posible ventana de vida bajo condiciones estrictas |
| Tiro por turno y origen | Modalidad, salida y procedencia orientativa | Frecuencias observadas; nunca daño, exposición ni calibración propia |
| Fuerza del enemigo | Desconocida | No se inventa a partir de velocidad de lanzamiento o de la barra propia |
| Vida y escudo | Ventana de cambio observada, solo si la atribución resulta comprobable | Asociación estadística conservadora; no se etiqueta como impacto confirmado ni prueba causal |

En los datos reales inspeccionados, la propiedad del proyectil no está incluida en su carga nativa. El registro orientativo exige como máximo 150 ms de edad del proyectil, una observación previa del turno rival de hasta 350 ms, el mismo número de turno, origen dentro de 60 píxeles del rival y al menos 60 píxeles de separación respecto al siguiente candidato. También comprueba carro, equipos, viento, clima y posición propia. Esto descarta algunos tiros legítimos cuando los carros están juntos o la captura llega tarde. Esa incertidumbre se conserva incluso al guardar y recargar el archivo.

El comparador de exposición requiere al menos ocho ventanas conocidas en dos episodios observados, vehículos y contexto compatibles, duelo sin ambigüedad y un intervalo estadístico separado del de la otra posición. Actualmente los registros orientativos reales no cumplen esa procedencia más fuerte y no pueden activar el comparador. Los perfiles de desplazamiento y las frecuencias siguen disponibles como observaciones.

La caminata usa su propia evaluación del terreno y del tiro. La información rival puede desempatar posiciones seguras de igual distancia, pero no sustituye esas comprobaciones, no alarga el movimiento y no dispara. La dirección, distancia y tiempo se recalculan desde el estado actual; los pasos de prueba se refinan entre una posición bloqueada y otra comprobada.

El archivo solo contiene categorías de carro, coordenadas, contadores y claves de episodio resumidas; no nombres, contraseñas, chat ni cookies. Los datos de las dos cuentas permanecen separados y este observador no añade una subida de datos al servidor.

Validación en vivo realizada en modo pasivo: se capturaron posiciones de varios carros y una observación de Raon con alejamiento aproximado de 32 píxeles y tiro 2. No se convirtió esa observación en un acierto o mejora de puntería. La prueba del navegador valida entradas y parada contra escenarios controlados; la nueva caminata en partidas reales y su beneficio táctico siguen pendientes tras la activación.
