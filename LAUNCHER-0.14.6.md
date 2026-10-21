# DragonLab 0.14.6 · Buscar posición cuando falta ángulo

Cierra la versión anterior y abre Comprobar-Punteria.cmd para iniciar el juego con la prueba automática activada. Abrir solo DragonLab-Prueba.exe prepara la guía; no inicia por sí solo el entrenador.

Cuando existe una hipótesis física y no se encuentra ángulo o recorrido libre, la prueba intenta hasta dos pasos de 14 píxeles. Cada paso exige soporte de terreno cercano, al menos ocho segundos disponibles y el mismo turno. Se vuelve a orientar, leer la posición y calcular después de caminar. Si un lado no avanza, se prueba otro lado con suelo seguro. Las teclas se liberan al terminar, cancelar o cambiar de turno.

El fallo anterior ocurría porque la evaluación lanzaba NoAim antes de alcanzar la rama de movimiento del entrenador. La recuperación ahora recibe explícitamente si el fallo permite buscar otra posición. Un clima desconocido, un patrón múltiple o la falta de modelo no se intentan resolver caminando. Sin una solución tras dos pasos, se omite el tiro; no se envía una carga arbitraria. No garantiza salir de todo hueco ni encontrar ángulo desde cualquier terreno.

Se mantienen los límites y las métricas separadas de 0.14.5: Armor tiro 1, calibración provisional, evaluación con copia fija del modelo, ventanas observadas de vida y resultados confirmados. No se declara aprendizaje estratégico completo ni mejora de victorias sin mediciones. Ocho cuentas simultáneas siguen pendientes; no se ha activado un control compartido entre cuentas.

Validación: 234 pruebas Python aprobadas, incluidas recuperación de ángulo, recálculo tras movimiento, falta de suelo, turno corto, cambio de turno, dirección atascada y máximo de dos pasos. Estas pruebas verifican el control; la eficacia de reposicionamiento necesita contraste en una partida real.

Distribución local: DragonLab-Prueba-0.14.6.zip. Preparación para servidor: DragonLab-Launcher-0.14.6.zip; requiere configurar los servicios Cloud. No publicar claves privadas ni sesiones de cuentas.
