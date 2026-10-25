# DragonLab 0.16.3 · Arrastre medido por sesión

El entrenador de DragonBound prefiere Drag cuando hay espacio libre dentro del juego. Envía controles normales de ratón a su pestaña concreta mediante la conexión local del navegador. Las dos cuentas pueden cargar simultáneamente sin mover el cursor del escritorio ni enviar Espacio a otra aplicación. No se llama a funciones del juego para disparar.

Antes de empezar comprueba una franja libre suficiente para todo el rango de sensibilidad observado en DragonBound. Si no cabe, selecciona y confirma Slice antes de reservar el tiro. Después de pulsar lee la sensibilidad nueva del juego; no reutiliza la del disparo anterior.

La fuerza solo se acepta después de que el juego registre un movimiento nuevo y su posición esperada. Se comprueba la barra real y, si hace falta, se corrige el desplazamiento con un número limitado de ajustes. La fuerza registrada es la observada, con tolerancia de una unidad. Cada carga conserva modalidad, ángulo, posición, orientación, viento y turno.

Se suelta en la última posición de arrastre, incluso ante cancelación, cambio de turno, aviso o error de conexión. Una tentativa ya iniciada nunca vuelve a disparar con Espacio: conserva la reserva del turno. Una carga ambigua tampoco se usa como medición válida sin confirmar la salida propia del proyectil.

Los registros nuevos incluyen método, fuerza solicitada y real, sensibilidad, correcciones y duración de carga separada de la preparación. Esto permite comparar velocidad sin confundirla con el tiempo de apuntar. No se ha medido todavía la mejora de velocidad en las partidas reales de esta versión.

Se conservan las dos sesiones, sus mediciones, SS, bala 1/2, selección de ítems, movimiento, límites de ángulo por modalidad, clima y las comprobaciones del aprendizaje. La guía manual con Q mantiene su comportamiento independiente; esta versión cambia el modo de carga del entrenador.

Validación: 457 pruebas Python y seis suites de navegador aprobadas. La nueva suite verifica dos arrastres simultáneos con eventos reales del navegador, sensibilidad renovada y una fuerza antigua que coincide con la pedida pero debe esperar al movimiento nuevo. La tercera pestaña conserva el foco y no recibe controles. Comprobación de lectura en una partida real: sensibilidad 1,30–1,70 y espacio suficiente para 400. Estas comprobaciones no sustituyen una comparación en vivo de cargas, puntería o victorias.

Para activarlo, cierra solo DragonLab y conserva abiertas las dos ventanas de Chrome. Inicia `Entrenar-2-Sesiones.cmd` desde la carpeta 0.16.3. El programa permite una sola instancia; abrir la nueva mientras sigue ejecutándose la anterior no sustituye su código.

Para usar: `DragonLab-Prueba-0.16.3.zip`. Para preparación y código: `DragonLabCloud-Preparacion.zip`.
