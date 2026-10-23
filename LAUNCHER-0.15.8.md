# DragonLab 0.15.8 · Revisión antes de jugar

Incluye todas las mejoras de 0.15.7 y corrige casos reproducidos durante una revisión independiente de controles y aprendizaje.

- Confirma el cambio real de bala y Slice en lugar de suponer que terminó tras una pausa fija de 80 ms. Puede confirmar inmediatamente o esperar hasta 450 ms; vuelve a comprobar el turno durante la espera.
- Justo antes de reservar el turno y pulsar Espacio, comprueba modalidad, ángulo, postura, viento, posiciones y objetivo. Si cambiaron durante el cálculo o al seleccionar un ítem, vuelve a calcular sin gastar un tiro.
- Registra que el DD fue seleccionado por el entrenador desde el primer clic. Si falla su confirmación antes de cargar, intenta quitar ese DD en el mismo turno para que no bloquee las demás balas. No desactiva un ítem elegido previamente por el usuario.
- Conserva el presupuesto de movimiento al reconectar, usando sala, jugador y turno real. Cuenta también un paso cuyo resultado quedó incierto por una desconexión.
- Comprueba de nuevo la reserva de tiempo después de simular posiciones. Elimina un camino adicional que podía mover fuera del presupuesto compartido.
- Un rechazo después de moverse queda asociado a la posición final: cambiar de bala ya no reinicia inmediatamente el mismo intento fallido.
- Exige mediciones futuras del viento actual y fuerzas variadas antes de promover un modelo. Rechaza candidatos que fallan incluso si las fuerzas de comprobación fueron iguales.
- Durante calibración alterna algunos arcos dirigidos calculados, buscando fuerzas distintas sin enviar cargas arbitrarias. Cada arco sigue pasando la comprobación del terreno.
- Las observaciones de clima incluyen el recorrido completo y el ancho de la columna, también cerca del lanzamiento y del impacto. Conserva los límites de ensayos y las restricciones para DD.

La revisión corrige fallos reproducidos y conserva la separación de datos provisionales, evaluación y tiros con ítems. No demuestra por sí sola una mejora en victorias ni una calibración completa de todos los carros y climas. Teleport sigue pendiente.
