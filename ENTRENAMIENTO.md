# Entrenamiento autónomo · 0.13.0

## Funcionamiento

El usuario inicia una sesión desde Ajustes. El entrenador verifica la pestaña DragonBound y el servidor 8 Avatar Off, el foco y el chat. Usa los botones visibles de selección de carro y búsqueda 1v1; no compra objetos ni escribe mensajes. Solo confirma automáticamente el aviso conocido de ausencia. Otros avisos detienen la sesión.

El planificador prioriza modalidades que necesitan comprobación independiente, modalidades sin ajuste y cobertura de viento. Alterna fuerzas 100, 300, 180, 360, 120, 320 y 220 y ángulos solicitados 55°, 35° y 75°; cuando hay datos busca fuerzas alejadas de las ya medidas. El ángulo real queda limitado por los controles del carro y el tiempo del turno. Las fuerzas registradas son las observadas en la barra, no las solicitadas.

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
