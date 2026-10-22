# DragonLab 0.15.7 · Turnos y elección de balas

Revisión basada en la sesión real: 14 tiros provisionales, 13 turnos marcados como omitidos, 46 rechazos de modalidad y ningún error de control. El cálculo tardaba alrededor de 0,3 ms; los rechazos y reintentos dominaban el problema.

- El movimiento comparte un presupuesto de dos pasos por turno entre todas las modalidades. No vuelve a posiciones visitadas al buscar una salida.
- Una modalidad sin modelo no reserva el turno antes de cargar; puede reconsiderarse si cambian las condiciones. Si finalmente se dispara, se elimina la omisión provisional de ese turno.
- Amplía la búsqueda dentro de los ángulos legales cada 4 grados. Revalida el ángulo y recorrido reales antes de disparar.
- Revisa el comienzo del recorrido con muestras más densas: un tiro bajo y rápido ya no ignora los primeros puntos junto a una pared.
- Los resultados de daño de tiros provisionales pueden orientar la elección entre balas. Conservan la etiqueta de calibración y no autorizan DD ni cuentan como evaluación independiente.
- Concentra hasta seis tiros de una calibración iniciada, cuando no hay una opción medida mejor, para evitar alternar sin terminar de comprobar un modelo.
- En aprendizaje adaptativo puede realizar hasta tres ensayos por combinación de clima, perfil y partida usando una fuerza calculada y un recorrido base sin colisiones. Son experimentales: no se afirma que la trayectoria bajo ese clima sea correcta. Se detienen al observar una alteración del vuelo. No usan DD y se registran separados de la puntería validada.
- El panel muestra las mediciones de clima y los rechazos incluyen el número de turno.

No se ha demostrado aún una mejora de victorias con esta versión. Mirror, Tornado y otros patrones que alteran el vuelo requieren sus modelos específicos; los ensayos no los declaran resueltos. Teleport sigue pendiente.
