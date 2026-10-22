# DragonLab 0.15.1 · Retroceso, terreno y Camaleón

Cierra la versión anterior y abre Comprobar-Punteria.cmd. Mantiene el juego adaptativo, entrada en segundo plano y límites de 20 o 40 tiros, seis partidas y 15 minutos. Detener cancela desde el panel.

## Retroceder ante un bloqueo

Se corrigieron dos errores del movimiento. Primero, antes se prefería caminar hacia el objetivo incluso si el cañón estaba bloqueado; ahora se comparan las dos direcciones con suelo disponible y se prioriza retroceder ante terreno bloqueado. Se simula una posición y pendiente aproximadas para ordenar los pasos, pero tras caminar se leen posición y ángulo reales y se calcula de nuevo antes de cargar. Sigue habiendo un máximo de dos pasos por preparación y se exige tiempo suficiente.

Segundo, la comprobación antigua aceptaba puntos sólidos dentro de una pared como si fueran suelo. Ahora exige la frontera entre aire y terreno. Rechaza paredes y huecos donde no hay una superficie compatible. Esto no garantiza escalar cualquier pendiente ni salir de cualquier cráter.

El cálculo de la bala ahora localiza el primer choque antes de revisar los climas. Un clima situado después de ese choque no bloquea por sí solo la recuperación de posición. Un clima desconocido antes del impacto sí impide tratar ese recorrido como conocido.

## Abrir paso

Se añadió una recuperación experimental de terreno para bala 1 de Armor, Ice, Mage y Trico, con un modelo congelado comprobado en la partida. Tras no poder obtener un tiro directo mediante el movimiento disponible, puede reutilizar una trayectoria calculada cuyo primer impacto sea la obstrucción. No usa una fuerza arbitraria.

Exige avance hacia el objetivo, separaciones mínimas de 90 píxeles respecto al propio carro y aliados conocidos, y 70 píxeles horizontales respecto al propio carro. Son filtros conservadores de la política, no radios de explosión calibrados ni garantía de evitar daño o caída. Lightning y los mecanismos especiales no se habilitan para excavar sin comprobación propia. No usa DD para abrir paso.

Los intentos se guardan separados de la evaluación de aciertos. Se comprueba después si el punto previsto quedó sin terreno durante la ventana observada; esto no equivale a confirmar un impacto directo ni a demostrar que ya existe un camino transitable. Los tiros de abrir paso tampoco se reutilizan como experiencias de ataque acertado.

## Camaleón / Randomizer

La guía oficial indica que bala 1, bala 2 y SS usan proyectiles aleatorios de otros móviles: https://dragonbound.net/guia/moviles

Se conservan los datos históricos, pero sus ajustes mezclados ya no se usan ni cuentan como salida calibrada. Las observaciones nuevas atribuidas se separan por identificador del proyectil y se marcan como identificadas después de disparar. No se ha comprobado una señal fiable que revele el proyectil antes de liberar el tiro. Por eso no se autoselecciona Camaleón ni se muestra una fuerza precisa basada en un supuesto perfil fijo. Se mantiene el juego manual y el registro de variantes. Los nombres Camaleon y Chameleon se reconocen como Randomizer.

## Tiempos y diagnóstico

entrenamiento-estado.json guarda planning_ms (tiempo del planificador, incluidas comparaciones de posición) y attempt_ms (duración del intento, con lecturas y controles). Un tiro confirmado incluye además preparación previa a la carga. El panel muestra el cálculo del último intento, causas de omisión, pasos y aperturas de terreno observadas. No se presenta el tiempo de carga o espera de turno como tiempo de cálculo.

En el registro examinado de 0.15.0 había dos turnos completamente omitidos y seis modalidades rechazadas: cuatro rechazos por clima desconocido y dos por falta de modelo, sin errores de control en esa lectura. No significa que todos los turnos perdidos tengan esa misma causa.

## Validación y límites

267 pruebas Python aprobadas. Hay regresiones para un cañón bloqueado que puede despejarse retrocediendo, clima posterior a una pared, rechazo de pared como suelo, borde sin apoyo, excavación con modelo comprobado, separación de recuperación frente a precisión y aislamiento de variantes del Camaleón. Cuatro suites de navegador y comprobaciones de los ejecutables.

Las recuperaciones nuevas se comprobaron con escenarios reproducibles; todavía falta observar el retroceso y la apertura de terreno en una partida real equivalente a la captura. No se declara resuelto todo clima, todos los carros, todos los turnos ni autonomía profesional. SS/DD siguen condicionados a datos propios; minimizar la ventana y ocho cuentas simultáneas no están certificados.

Distribución local: DragonLab-Prueba-0.15.1.zip. Preparación Cloud: DragonLab-Launcher-0.15.1.zip; requiere configurar los servicios. No publiques claves privadas, sesiones ni mediciones personales.
