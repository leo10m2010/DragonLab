# Entrenamiento autónomo · 0.13.2

## Control de turnos y memoria persistente

La 0.13.2 sustituye consumed por un registro acotado de (partida, jugador, turn_number). El contador se lee explícitamente desde el juego; no se infiere de viento o del jugador activo. Una reserva antes de cargar impide repetir una carga ambigua tras un corte. Un número nuevo autoriza un intento aunque no se haya observado el turno rival. Al pasar por el lobby se inicia un registro nuevo para la próxima partida. Los errores transitorios de transporte reconstruyen la conexión con espera progresiva, sin robar el foco repetidamente.

La selección intenta otras modalidades antes de dar por agotado el turno. Un desplazamiento corto requiere apoyo continuo en el terreno, se confirma con la posición nativa y obliga a recalcular. Las aproximaciones y tiros para abrir paso usan una fuerza calculada por el Lab y un final que progresa hacia el objetivo, a al menos 60 píxeles del carro. Si no hay una acción calculable, espera un nuevo turno; no promete disparar en una geometría imposible.

estrategia-entrenamiento.json conserva hasta 512 configuraciones. La memoria agrupa modalidad/ángulo por carro, magnitud y dirección de viento, rango, lado y altura relativa. Aprende con cercanía de final observado al objetivo y necesita dos observaciones compatibles antes de recomendar. Una de cada tres decisiones puede reutilizar esa experiencia, conservando el resto para medir/comprobar calibraciones. Esto es memoria numérica de alcance, no aprendizaje de victorias ni daños; no representa una IA profesional. Los perfiles actuales se conservan y el libro exige mediciones futuras para activar cambios.

Validación real 0.13.2: cuatro tiros entre Armor e Ice, turnos [2,3] y [1,4] en partidas distintas, fuerzas Lab/reales 208/207, 200/199, 320/320 y 180/179. Desplazamiento confirmado [902,55] → [916,53]. No se ha hecho una prueba de 24 horas. La memoria persistente, recuperación de conexión, turnos consecutivos, ausencia de duplicados y movimiento con apoyo tienen pruebas automatizadas. Consulte LAUNCHER-0.13.2.md para las condiciones de uso continuo.

## Corrección de ángulo y juego guiado

La 0.13.0 liberaba las flechas tras 45 ms y no exigía movimiento antes de disparar. La 0.13.1 mantiene la flecha con lectura de retorno, libera en todos los caminos de salida y utiliza minang/maxang y truang_min/truang_max nativos. Los límites se aplican antes de elegir el tiro. Si no hay lectura o la flecha no produce movimiento y no se está en un límite conocido, no carga Espacio.

La aplicación entrega una copia de sus Settings al entrenador mediante la cola de la interfaz, conservando objetivo, calibraciones, terreno, viento y clima. El entrenador usa core.solve, orienta al objetivo, propone un ángulo dentro del rango del carro y vuelve a solicitar Settings tras moverlo. La fuerza se recalcula para el ángulo real; las fuerzas fijas del currículo ya no sustituyen ese cálculo en el modo guiado de la aplicación. Los tiros bloqueados esperan otra oportunidad.

Continuo es la duración predeterminada de la interfaz y desactiva los topes de tiros, búsquedas y duración. Sigue entre partidas, conserva un historial acotado a 120 entradas en memoria y disco y espera si falta foco o el chat está abierto. Esc/Detener y el cierre siguen cancelando. No se instala una tarea del sistema ni se inicia el entrenamiento al abrir el programa.

Verificación real: cambio 16° → 55°, seguido de fuerza Lab 207 y fuerza leída 206. Una sesión guiada posterior registró tres tiros y una búsqueda de nueva partida, con fuerzas Lab 204/205/98 y fuerzas reales 204/204/97. Se guardaron distancias de final al objetivo de 86.51, 139.04 y 18.05 píxeles bajo condiciones distintas; no prueban una mejora progresiva ni puntería perfecta. Las observaciones alimentan el libro existente y requieren comprobación posterior antes de activar ajustes.

## Funcionamiento

Comprobación adicional 0.13.1: bajada nativa de 54° a 47° para un objetivo de 46° (tolerancia de un grado). El modo Continuo sobrepasó los topes de un tiro y 30 segundos usados en la prueba, buscó una nueva partida, registró dos tiros y se detuvo con Esc. Fuerzas Lab/reales: 144/143 y 138/137; finales nativos a 3.38 y 5.24 píxeles del objetivo, en esos dos casos concretos. Pruebas Python: 143 aprobadas.

El usuario inicia una sesión desde Ajustes. El entrenador verifica la pestaña DragonBound y el servidor 8 Avatar Off, el foco y el chat. Usa los botones visibles de selección de carro y búsqueda 1v1; no compra objetos ni escribe mensajes. Solo confirma automáticamente el aviso conocido de ausencia. Otros avisos detienen la sesión.

El planificador prioriza modalidades que necesitan comprobación independiente, modalidades sin ajuste y cobertura de viento. Propone ángulos variados y el modo guiado busca una solución viable dentro del rango nativo. El currículo conserva fuerzas de prueba para herramientas de medición sin proveedor del Lab, pero la aplicación toma la fuerza del motor de puntería. Las fuerzas registradas son las observadas en la barra.

El control pasa a Slice, ajusta el ángulo con flechas y carga Espacio. Comprueba turno, posición, viento y modalidad durante la carga. Libera las teclas en la salida normal, cancelación o error; no repite una carga fallida dentro del mismo turno. Tres fallos consecutivos terminan la sesión. Los errores y límites se conservan en entrenamiento-estado.json junto al libro local.

Antes de cargar se registran las balas existentes; una observación nueva debe superar la atribución de jugador, posición, tiempo y fuerza. Los patrones de salida múltiple se guardan con sus lanzamientos numéricos y no se promueven como una sola bala. Las observaciones ordinarias siguen pasando por el ajuste y comprobación independiente existentes. No se separan datos de entrenamiento y validación por un simple cambio de etiqueta: los candidatos necesitan tiros posteriores.

## Comprobación realizada

- Selección visible de Armor desde el lobby y búsqueda automática 1v1.
- Primer tiro propio confirmado a fuerza 99 y segundo a 299, modalidades 1 y 2 respectivamente.
- La segunda observación contenía tres proyectiles; conserva el grupo sin introducirlo en el ajuste de bala única.
- La pérdida de foco detuvo la sesión sin seguir buscando partidas.
- Una segunda sesión completó su límite de tres tiros: SS a 99 con viento 5, tiro 2 a 99 con viento 6 y tiro 1 a 359 con viento 7. Eligió carro, buscó una partida y terminó sin error. Para el último tiro se solicitó un ángulo de 75°; el ángulo efectivo depende del límite del carro y se conserva en la salida observada.
- Pruebas automatizadas cubren selección de modalidad disponible, prioridad de comprobación, variedad de fuerza, rotación de carros, límite de sesión, rechazo de otro servidor, cancelación y grupos de balas.

## Límites pendientes

La comprobación inicial no equivale a una calibración exhaustiva. Deben medirse y contrastarse todos los carros, SS, mecanismos secundarios, climas y vientos disponibles. No fuerza condiciones del servidor ni genera mediciones sintéticas. Los modelos específicos de proyectiles múltiples y transformaciones necesitan validación propia. GunBound World no está incluido en esta primera fase autónoma.
