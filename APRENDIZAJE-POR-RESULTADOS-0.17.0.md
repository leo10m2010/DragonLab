# Aprendizaje por resultados y evaluación prospectiva

## Problema observado

El recorrido 0.16.6 tuvo aproximadamente un 92 % de tiros en calibración y tasas recientes de victoria bajas. Ajustar velocidades y gravedad no entrenaba una política de decisión con esas victorias. Además, el error determinista de origen de Nak/Aduka anulaba mejoras reales de predicción de vuelo. La revisión y su corrección se conservan en `REVISION-ESTANCAMIENTO-0.16.7.md`.

## Separación de responsabilidades

`outcome_policy.py` aprende preferencias empíricas entre acciones, no suministra fuerzas ni valida física. El planificador calcula primero trayectorias, comprueba terreno, clima y límites, y solo permite elegir entre sus opciones válidas. Una propuesta que altere fuerza, origen, objetivo, dirección o alcance fuera de esas opciones se descarta. La verificación final vuelve a usar el ángulo real.

La política usa carro propio, modalidad, tramo de ángulo, ítem normal/DD y un contexto anónimo de distancia, desnivel, viento, apoyo del objetivo, carro rival y vida propia. Conserva hasta 512 resultados y 64 ventanas pendientes por trabajador, con estimaciones locales, reducción del peso de evidencia escasa y una búsqueda compatible de contextos cercanos. No transfiere libremente resultados entre carros o entre un tiro normal y DD. Los datos antiguos sin procedencia suficiente no se convierten retrospectivamente en recompensas.

Las opciones comprobadas reciben una estimación de recompensa e incertidumbre. Como máximo una de cada diez decisiones confirmadas puede explorar una alternativa comprobada; replantear muchas veces el mismo turno no crea créditos de exploración. Una preferencia negativa de DD puede conservar el ítem cuando el tiro normal funcionó mejor en condiciones parecidas, pero un resultado aprendido no salta sus comprobaciones de disponibilidad o trayectoria.

## Qué datos actualizan una preferencia

Solo una liberación propia confirmada, con geometría coincidente a tres píxeles o menos y una ventana de vida atribuible, puede aportar recompensa. La recompensa principal es el cambio neto observado entre daño enemigo y propio, acotado para evitar que un valor extremo domine el historial. Las curaciones, ventanas solapadas y proyectiles extranjeros o no resueltos quedan excluidos.

Un tiro de calibración dirigida puede enseñar su resultado efectivo sin aprobar la hipótesis física que lo propuso. Solo las trayectorias ya comprobadas se someten a la selección aprendida. Se conservan el contexto anterior al tiro y la geometría nativa posterior: un remate rápido no desaparece del aprendizaje simplemente porque el enemigo ya esté marcado muerto en la primera captura.

Al terminar una partida 1v1 con resultado de supervivencia nativo, se reparte un crédito terminal total de +0,15 o −0,15 entre sus resultados de daño atribuibles. El resultado se aplica una sola vez. Una partida desconocida no se transforma en derrota y una victoria no se multiplica por el número de tiros.

## Ventana física local

`local_launch_window.py` evita un bloqueo específico de corto alcance. Requiere por lo menos tres fuerzas distintas en el conjunto de ajuste, con amplitud de al menos 12 puntos, y tres lanzamientos posteriores separados para comprobarlo. Exige error de parámetros no superior a dos unidades y error de vuelo no superior a cinco píxeles. Una cota de sensibilidad del ajuste incorpora residuos observados y una unidad de cuantización.

El permiso queda limitado al intervalo cerrado de fuerzas comprobadas dentro del dominio de entrenamiento, al menor tiempo de vuelo de las comprobaciones futuras y al viento admitido. Se recalcula cuando cambia el contexto. No cambia los requisitos del modelo global de toda la barra. La integración excluye expresamente los proyectiles con mecanismos especiales conocidos, aunque un registro carezca de su bandera. Una validación local no certifica Thor, túneles, órbitas o transformaciones.

Un lanzamiento posterior que contradiga un modelo congelado lo invalida para seguir apuntando y vuelve a calibración. El informe registra esa retirada en lugar de conservar el modelo solo porque antes había pasado una prueba.

## Comparación prospectiva

Una asignación determinista mediante el hash del episodio reserva aproximadamente un 20 % de partidas a la elección de referencia. En ellas se omite el reordenamiento aprendido de modalidades y recorridos; las restantes usan las preferencias cuando hay evidencia suficiente. Las comprobaciones físicas se aplican a ambas. La exploración aprendida tampoco se aplica al grupo de referencia.

Los resultados nativos de todas las partidas identificadas se asignan al grupo correspondiente, incluidas derrotas sin resultados de daño utilizables. Eso evita excluir precisamente los episodios donde no hubo tiros útiles. Los resultados son descriptivos: el informe mantiene `win_improvement_proven: false`; ni unas pocas victorias ni mirar repetidamente una tasa creciente constituyen una prueba estadística de superioridad.

La comparación mide esta política adaptativa durante el recorrido, no una réplica exacta de un ejecutable anterior ni una garantía de superioridad con cualquier rival. Deben contrastarse las tasas, número de partidas, turnos omitidos y calidad de atribución antes de concluir una mejora. El informe muestra por separado los últimos 100 resultados, los totales de esta ejecución y las comparaciones conservadas de la política.

## Validación de implementación

Las pruebas incluyen preferencia inducida por daño real conocido, penalización de daño propio, crédito terminal una sola vez, persistencia y aislamiento por cuenta, resultados desconocidos, remates rápidos, datos de calibración sin falsa aprobación, ventanas limitadas, rechazo de cambios en la fuerza de una opción, controles de modalidades disponibles, retirada de modelos contradictorios y comparación que cuenta derrotas sin tiros útiles. Pasar estas pruebas acredita el mecanismo; no demuestra todavía una mejora de victorias en juego.

El filtro de modalidades admite una ventana local válida en el estado actual aunque no exista un modelo amplio. La prueba de integración atraviesa `AdaptiveTrial.probe` y verifica que cambiar el viento o el episodio vuelva a rechazar ese permiso limitado.

## Comprobación de la entrega

El 5 de noviembre de 2026 pasaron 701 pruebas de Python, siete suites de navegador y tres comprobaciones de los ejecutables empaquetados. La prueba en vivo abrió ambas sesiones independientes con el ejecutable 0.17.0 y un límite de 24 horas. En la primera captura de validación había cuatro y dos tiros confirmados respectivamente, cuatro y dos recompensas de daño guardadas, cero ventanas rechazadas y cero errores de la política. Los seis casos coincidían con el origen nativo a cero píxeles.

Esta comprobación confirma disparos y realimentación persistente en ambas cuentas. Aún no había una comparación de victorias suficiente ni preferencias aplicadas con evidencia suficiente; no acredita superioridad competitiva ni continuidad ya observada durante 24 horas.
