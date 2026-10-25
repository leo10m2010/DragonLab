# DragonLab 0.16.2 · SS, balas y clima

Conserva las dos cuentas, los perfiles de navegador y todas las mediciones. Cierra la versión anterior dejando Chrome abierto; inicia `Entrenar-2-Sesiones.cmd` desde la carpeta nueva.

## SS y selección de bala

El botón visible de SS no siempre estaba listo: el juego usa la clase `grayscale` durante la recarga. Ahora esa modalidad queda fuera de las opciones disponibles, incluso si todavía figura seleccionada, y se comprueba de nuevo justo antes de cargar. Una recarga no reserva el turno ni impide intentar una bala normal.

Los límites de ángulo aprendidos se separan por carro, bala, pendiente y orientación. Se leen después de confirmar la modalidad real. El rango de bala 2 no limita por error una tentativa posterior con bala 1. Cada bala conserva su modelo propio; no se inventa una fuerza al faltar datos.

## Climas y observaciones

Se corrigió una atribución que podía confundir rayos, efectos inmóviles u objetos ajenos con una continuación del proyectil. Eso marcaba permanentemente algunas balas de Ice como múltiples y desactivaba su uso. Los datos anteriores se conservan aparte; las continuaciones nuevas necesitan prueba de pertenencia. Los mecanismos especiales conocidos siguen pendientes cuando faltan datos fiables.

Mirror y Tornado guardan reconstrucciones nativas con columnas, tiempos y puntos del recorrido. Un cruce parcial o detenido por terreno no certifica que la columna deje pasar la bala sin alterarla. La posibilidad de dar un paso fuera de una columna cercana sigue exigiendo suelo, presupuesto de movimiento y recálculo real. Esto mejora la observación y recuperación; no declara completos los modelos de todas las transformaciones climáticas.

## Turnos y aviso de retirada

Después de comprobar las modalidades disponibles y agotar la recuperación, si no hay una trayectoria válida puede pulsar el botón real de pasar turno. La acción se reserva una vez y se confirma mediante el cambio nativo de turno; no se reemplaza por una carga arbitraria ni por un atajo global.

Los clics vuelven a comprobar su control concreto antes de actuar. Un punto antiguo no puede reutilizarse para pulsar otra zona. Los avisos que aparezcan durante la preparación o carga pausan las entradas; una confirmación desconocida de salir no se acepta automáticamente.

El aviso conocido «Dejaste el Juego» se registra como retirada y se respeta el tiempo indicado antes de continuar. También se reconoce el aviso informativo de regalo ya recibido. Los demás mensajes desconocidos siguen pausando el entrenador. El nuevo registro de controles ayuda a distinguir acciones del programa de una retirada por otra causa; los registros anteriores no bastan para atribuir todas las salidas a inactividad.

Validación: 440 pruebas Python y cinco suites de navegador aprobadas. No se declara puntería perfecta, mejora de victorias ni continuidad certificada de 24 horas. La activación en las dos cuentas debe comprobarse después de cerrar la versión anterior.

Para usar: `DragonLab-Prueba-0.16.2.zip`. Para código y preparación: `DragonLabCloud-Preparacion.zip`. Los informes individuales siguen dentro de `entrenamiento-paralelo/sesion-1` y `sesion-2`.
