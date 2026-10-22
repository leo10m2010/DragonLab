# DragonLab 0.15.2

- El launcher refleja el entrenador activo, su pausa o finalización aunque la captura de la guía esté detenida.
- Revisión del próximo turno cada 100 ms; mantiene una sola carga por número de turno real, incluidos turnos propios consecutivos.
- Una modalidad rechazada vuelve a considerarse si cambia la posición o el viento. No se reserva un turno por un rechazo anterior a cargar.
- Calibración adaptativa: ajusta provisionalmente la relación fuerza/velocidad con la última salida nativa compatible. Una salida más rápida reduce la fuerza calculada; una más lenta la aumenta. No resta fuerza por impactos contra paredes. Recalcula el recorrido y las colisiones antes de disparar.
- La corrección exige mismo carro/modalidad, partida, postura, ángulo y viento compatible, trayectoria simple, sin clima y deriva limitada al 15 %. No modifica modelos congelados ni sus pruebas independientes.

Teleport todavía no se activa automáticamente: falta comprobar su recorrido y destino en partida. No se reutiliza una calibración de daño para simularlo. Tampoco se afirma que haya mejorado el porcentaje de victorias sin nuevas partidas medidas.
