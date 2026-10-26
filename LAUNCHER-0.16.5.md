# DragonLab 0.16.5 · Rival y caminata según la situación

Para activar esta versión, cierra únicamente DragonLab y conserva las dos ventanas de Chrome. Inicia `Entrenar-2-Sesiones.cmd` desde la carpeta nueva. Las cuentas y mediciones propias se conservan.

## Caminata adaptable

El entrenador compara ambas direcciones y distintas distancias, según el obstáculo, el ángulo, la salida de una columna, el suelo y el tiempo disponible. Cuando encuentra una posición bloqueada y otra válida, afina una distancia intermedia para evitar recorrer de más. La búsqueda tiene un máximo de ocho evaluaciones y conserva tiempo para ajustar y confirmar el tiro.

Se comprueba el suelo de todo el recorrido, con margen de parada antes de un borde. La ejecución lee la posición real y adapta cuándo soltar la tecla; puede detenerse antes si pierde apoyo, se atasca, cambia el turno o aparece movimiento contrario al solicitado. Un retroceso por impacto no se aprende como avance ni como velocidad normal.

El presupuesto de recorrido se comparte entre los intentos del mismo turno y se reserva antes de pulsar. Si se pierde la conexión, esa reserva no desaparece. Después de cada paso se recalculan posición, pendiente, orientación y tiro. Si ya existe una solución válida, no se añade una caminata por rutina.

## Aprender observando al rival

El nuevo observador recoge turnos, posiciones, desplazamientos, carro y modalidad de los tiros que pueda atribuir. Resume acercamientos, alejamientos, posiciones sin desplazamiento apreciable y frecuencia de balas por carro. No conserva nombres ni usa la barra propia como fuerza del enemigo. Un cambio de posición ambiguo no se interpreta como una decisión voluntaria.

La captura real confirmó que los proyectiles de DragonBound no traen propietario explícito. Por eso existe una observación orientativa por turno y origen: exige un turno rival visto inmediatamente antes, proyectil muy reciente, mismo número de turno, origen cercano y claramente separado de los demás jugadores, y contexto estable. Los casos que no cumplen quedan sin atribuir. Se guarda esa procedencia y nunca se presenta como un propietario nativo confirmado.

Los tiros orientativos no habilitan conclusiones de daño, el modelo de exposición ni calibraciones propias. Las ventanas de daño exigen evidencia más fuerte y se invalidan ante interferencias, proyectiles ajenos o desconocidos, cambios de carro, movimientos o curaciones. Incluso con datos suficientes, la exposición observada solo puede desempatar entre dos pasos de igual distancia que ya tengan suelo seguro y trayectoria comprobada. No ordena una caminata adicional.

Cada trabajador guarda sus datos numéricos en `aprendizaje-rivales.json`, con un máximo de 256 casos de tiro y 256 posiciones recientes, contadores acumulados y escritura agrupada. El panel «Aprender del rival» distingue observaciones orientativas, patrones y evidencia utilizable. Un fallo del observador opcional no debe interrumpir los controles del entrenador. Ver `APRENDIZAJE-RIVAL-0.16.5.md` para los límites.

## Validación

564 pruebas Python y siete suites de navegador aprobadas. Incluyen caminata corta y larga con teclas reales aisladas por pestaña, suelta correcta, suelo y márgenes, refinamiento de distancia, presupuesto al reconectar, retroceso inesperado, equipos, duplicados, efectos demorados, datos anónimos y rechazo de atribución ambigua. La captura pasiva en vivo registró posiciones y un alejamiento con tiro 2 orientativo de Raon, sin enviar controles al juego.

La nueva caminata todavía necesita observarse en partidas reales después de activar esta versión. No se declara que imite perfectamente al rival, que todos sus tiros sean atribuibles ni que haya mejorado las victorias.

Para usar: `DragonLab-Prueba-0.16.5.zip`. Para preparación y código: `DragonLabCloud-Preparacion.zip`.
