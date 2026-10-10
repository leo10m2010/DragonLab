# Revisión 0.8.1

## Atajo

Se sustituyó la consulta cada 8 ms por eventos pasivos de teclado Windows en un hilo con cola de mensajes. La ventana del juego se obtiene del navegador conectado y se compara con la ventana en primer plano. Se eliminó la dependencia del título consultado en cada pulsación y del indicador de foco de la página. Las ventanas con el mismo título se resuelven dando prioridad a la que está en primer plano.

Ctrl cambia al soltarse. Las flechas y la barra espaciadora de apuntado no cancelan la pulsación. Las combinaciones con otras teclas, cambios de ventana/jugador e inyección de teclas se descartan. Se retiró F8 del atajo y de todas las indicaciones, porque el usuario confirmó que salta el turno en el juego. Todos los eventos se pasan a Windows sin alteración y no se guarda el contenido de las teclas. Los diagnósticos opcionales muestran solo disponibilidad, errores y número de cambios de objetivo.

## Carga

Se eliminó el sondeo continuo del teclado. Los recorridos observados utilizan muestreo de 40 ms con límite de 400 intervalos, más los tiempos exactos de saltos nativos; se conserva el extremo. Los estados repetidos reutilizan el recorrido calculado. El caso de prueba pasó de 601 a 376 puntos (37,4% menos), sin cambiar el extremo ni las posiciones de saltos. Esto mide puntos de dibujo de ese caso, no un porcentaje general de ahorro de CPU.

La vista previa captura cada tres segundos en vez de cada 1,5 segundos y continúa suspendida al minimizar. Se elimina una actualización duplicada de la vista/overlay por muestra. La búsqueda de fuerza y los datos de calibración conservan su resolución anterior. El tamaño del ejecutable permanece cerca de 19 MB porque conserva el entorno independiente y la interfaz.

## Validación

Treinta pulsaciones rápidas simuladas como eventos, Ctrl con flechas, descarte de Ctrl+C, cambio de ventana, pérdida de autorización, dos teclas Ctrl simultáneas y confirmación de que F8 no cambia el objetivo de DragonLab. Instalación y retirada real del receptor de eventos Windows; consumo de CPU medido en una espera de medio segundo: 0,0 segundos, sujeto a la resolución de esa medición. Reutilización de recorridos repetidos y preservación de extremo/saltos.

Regresiones de selección con datos reales de cuatro jugadores y fixture de ocho, cámara/terreno/proyectiles en navegador de prueba y ventana de trayectorias sin tomar el foco. Las 85 comparaciones de posiciones nativas, las 28 transiciones de Tornado y las 14 pruebas de ángulos conservan sus resultados previos. No equivale a calibrar vehículos pendientes ni a probar rendimiento en un PC antiguo.
