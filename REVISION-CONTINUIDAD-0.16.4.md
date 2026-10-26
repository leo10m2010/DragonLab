# Revisión de continuidad y aprendizaje

La revisión se centró en el fallo observado de una cuenta, la recuperación de controles, los cambios entre partidas/bloques, la separación de sesiones y el uso de las mediciones. No equivale a certificar cada carro y clima ni a una auditoría de seguridad completa de todos los servicios del producto.

## Lo observado en 0.16.3

La primera sesión se detuvo tras 288 tiros y 90 búsquedas de partida. Su motivo final era «Tres fallos de control; último: El juego no inició el arrastre». La segunda seguía activa; el estado general del grupo era activo porque representaba al menos un trabajador en ejecución. El monitor no distinguía suficientemente ese funcionamiento parcial.

En la inspección del aprendizaje de la primera sesión había 271 calibraciones, 14 tiros de evaluación y tres prácticas de clima. La mediana del error al reconstruir el vuelo nativo de los tiros evaluados era aproximadamente 0,94 píxeles, pero la mayoría de las acciones seguía sin convertirse en evaluaciones independientes. La segunda sesión mostraba la misma concentración en calibración. Son señales de ajuste físico útil y de un proceso de comprobación estancado, no evidencia de autonomía completa.

La distancia al centro o anclaje del rival no debe interpretarse por sí sola como acierto o fallo: el proyectil puede terminar al tocar su zona de colisión. Las ventanas de vida/escudo y las victorias se guardan por separado. Los datos inspeccionados no permiten prometer un porcentaje de victorias ni puntería perfecta.

## Causas corregidas

- Un fallo de inicio de Drag conocido podía terminar permanentemente un trabajador tras tres intentos. Ahora activa recuperación específica sin borrar la reserva del turno ni crear un controlador nuevo.
- La geometría aceptaba capas de chat que el controlador nativo ignora al pulsar. Esas capas y la ayuda quedan excluidas del entrenador y del arrastre manual de Q.
- Una transición de bloque podía esperar al juego antes de atender un aviso conocido. Los avisos se procesan primero y la desaparición prolongada del juego tiene vigilancia de conexión.
- El carro de foco se devolvía indefinidamente. Ahora los periodos de foco son limitados y se rotan perfiles compatibles.
- La variedad de ángulos terminaba después de las primeras calibraciones. Ahora continúa mientras el modelo no esté comprobado.
- Se dispersaban turnos escasos en SS aunque una bala normal estuviera cerca de completar comprobaciones. El selector prioriza ese progreso, manteniendo una SS letal respaldada por datos.

## Cómo comprobar la siguiente sesión

El estado general debe mostrar dos sesiones activas y actualizar sus contadores separados. Un fallo de entrada conocido debe registrar una recuperación, conservar el turno consumido y permitir continuar en otro turno. Los contadores de tiros dirigidos y de comprobaciones independientes deben crecer; no basta con acumular muestras. La ampliación a otro carro debe respetar su propio perfil y sus modalidades especiales.

La prueba automatizada de mil turnos comprueba reservas y recuperación durante un plazo simulado; no reproduce el servidor real, la red ni todos los diálogos posibles. No se declara una ejecución real de 24 horas completada por esta versión. Mirror, Tornado, Camaleón y otros mecanismos especiales mantienen las restricciones derivadas de sus observaciones propias.
