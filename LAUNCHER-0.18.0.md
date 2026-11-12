# DragonLab 0.18.0 · Manual Matrix

## Abrir

`DragonLab-Manual.exe` abre la guía manual. Pulsa **Abrir juego** y entra en una partida. El programa muestra fuerza, objetivo y trayectorias continuas. Ctrl cambia de objetivo y Q aplica una sola fuerza calculada cuando está disponible; los atajos siguen siendo personalizables.

`DragonLab-Automatico.exe` es la entrada separada del entrenador experimental. Abrirla no inicia partidas: exige pulsar su botón. Usa un modo a la vez; la protección de instancia evita dos programas dando controles a la misma sesión. Las mediciones comprobadas siguen compartiéndose con la biblioteca manual.

## Fluidez

El manual mantiene un solo cálculo activo y una sola solicitud pendiente. Cuando cambias ángulo, posición, objetivo o condiciones, cancela el cálculo obsoleto y sustituye la solicitud pendiente. Los resultados antiguos no pueden reemplazar una guía nueva ni autorizar el atajo de tiro. La lectura manual busca intervalos de 80–180 ms según modo y carga; las capturas de imagen y terreno mantienen frecuencias moderadas.

El solver evita trazados y cálculos repetidos. Las seis regresiones medidas mantuvieron exactamente el mismo resultado completo: mediana del tiro alto 15,7→8,5 ms, Mirror 61,8→53,6 ms y Tornado 81,4→68,9 ms en esta PC. Son mediciones locales del cálculo, no un límite garantizado del tiempo total de la guía.

## Interfaz

Launcher y controles comparten verde Matrix y fondo oscuro, con una sola acción principal y estado separado. Las trayectorias son continuas, con extremos redondeados y todos los vértices conservados. Los puntos inválidos separan los tramos; no se suaviza la geometría física. Se evitan redibujos y operaciones de fuente que no cambian nada.

El catálogo manual ahora muestra 22 vehículos reconocidos y sus 66 modalidades, incluidos especiales que antes no aparecían. Reconocerlos no equivale a calibrarlos. Un ID desconocido se indica como pendiente y no reutiliza la física del vehículo anterior.

Se corrigieron el estado «Calculando» que podía quedar retenido después de un cálculo manual y la repetición continua de una entrada numérica inválida. Si falta el ángulo, viento o modalidad nativos, se retira la recomendación hasta recibir un fotograma completo; no se aprovechan los valores anteriores como si fueran actuales. La vista con cuenta reserva espacio para Ayuda, Ajustes y la explicación del envío opcional de mediciones.

## Validación

Pasan 751 pruebas de Python y siete suites de navegador. Las pruebas cubren cancelación, sustitución de solicitudes, ausencia de datos y recuperación, separación de entradas, geometría de las líneas, Q, Drag, aislamiento de sesiones y controles visibles del launcher. Si falta identificar o calibrar un vehículo, tampoco se dibuja una curva de referencia usando la física anterior. Los seis casos de física conservan la salida completa de la versión anterior. La comprobación de límites de controles se ejecutó con Tk en esta PC; la herramienta de capturas de Windows falló al iniciar, por lo que no se presenta una comparación visual en vivo ni una prueba de precisión en una partida nueva.

## Actualización revisada

La comparación local del otro programa encontró cambios de calibración de Boomer en 0.1.22 y juegos experimentales en 0.1.23. Su catálogo distribuido conserva los mismos 23 IDs que en 0.1.21; no confirma nuevos carros. Los detalles y límites de la revisión están en `INFORME-REA-0.1.23.md`.

Paquete manual: `DragonLab-Manual-0.18.0.zip`. Paquete automático separado: `DragonLab-Automatico-0.18.0.zip`. El ZIP de prueba mantiene los accesos de compatibilidad.
