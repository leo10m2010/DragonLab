# DragonLab 0.14.7 · Segundo plano y diagnóstico

Abre Comprobar-Punteria.cmd para abrir el juego e iniciar la prueba limitada de Armor tiro 1. En el panel puedes elegir Segundo plano o Juego al frente antes de empezar. Segundo plano es el valor inicial del producto; las sesiones internas antiguas conservan su comportamiento al frente si no solicitan el modo nuevo.

## Segundo plano

El entrenador envía los controles a la pestaña concreta mediante el navegador, sin teclado global ni mover el cursor. Usa el foco virtual del protocolo de Chrome para mantener activa la página del juego sin pedir traerla al frente. Al cerrar la conexión se desactiva ese foco virtual. No llama funciones del juego para disparar ni modifica sus variables de partida. La apertura inicial del navegador puede mostrar la ventana; el entrenamiento posterior no pide activarla.

El chat sigue pausando la sesión y el botón Detener funciona desde el panel aunque el juego no esté visible. Esc detiene desde la propia pestaña del juego; no es un atajo global cuando estás en otra aplicación. Una pausa por chat o una reconexión conserva el límite de duración y no autoriza a repetir una carga en el mismo turno. Cerrar el navegador detiene o agota la sesión; no se asegura funcionamiento de 24 horas.

En un primer ensayo real sin foco virtual, las teclas llegaron pero el juego no cambió el ángulo. Esa variante no se considera funcional. La corrección añade la función experimental Emulation.setFocusEmulationEnabled del navegador. Las pruebas de navegador comprueban que una pestaña inicialmente sin foco recibe su tecla, otra pestaña no la recibe y conserva su foco. En la versión ejecutable se observaron cuatro disparos confirmados, sin errores de control, mientras otra pestaña permanecía seleccionada durante los tiros posteriores. La sesión llevaba dos partidas iniciadas y una derrota confirmada; no demuestra mejora de victorias. Minimizar toda la ventana y suspender pestañas siguen pendientes de comprobación.

Referencia del protocolo: https://github.com/ChromeDevTools/devtools-protocol/blob/master/pdl/domains/Emulation.pdl

## Diagnóstico y movimiento

Las omisiones guardan códigos separados: falta de modelo, patrón especial sin comprobar, clima sin comprobar, viento sin medir o fuera del ajuste, terreno bloqueado, falta de ángulo, suelo inseguro y presupuesto de calibración agotado. El panel muestra los motivos y cuántos pasos terminaron encontrando una trayectoria. Cada paso registra posición inicial/final, turno y resultado del recálculo; encontrar trayectoria no equivale a acertar.

Se conserva el máximo de dos pasos cortos sobre suelo seguro y con tiempo suficiente. Las animaciones o movimientos todavía activos al principio de un turno ya no consumen ese turno ni cuentan como fallo de control: espera y vuelve a leer antes de cargar. Las cargas liberadas o ambiguas mantienen su reserva de turno para impedir duplicados.

Un bloqueo entre procesos impide dos entrenadores sobre la misma pestaña y dos escritores sobre el mismo directorio de datos. Una segunda sesión rechazada no sobreescribe el informe de la primera. Las ocho cuentas simultáneas siguen pendientes: necesitan sesiones y datos separados, coordinación del aprendizaje y pruebas graduales de carga.

## Validación y alcance

244 pruebas Python aprobadas. Cuatro suites de navegador para atajos, controles CDP, clima y entrada en segundo plano. Se mantienen las comprobaciones futuras de modelos y la comparación del ajuste candidato con la referencia; no se declaran mejoras por acumular tiros. La prueba sigue limitada a Armor tiro 1; no es un agente estratégico profesional y no hay mejora de victorias demostrada.

Los datos se conservan en el directorio local de calibraciones. entrenamiento-estado.json incluye modo, errores, pasos y evaluación. evaluacion-punteria.json conserva las omisiones y sus códigos. El control de disparo con otra pestaña seleccionada quedó observado. El cambio de ángulo 18→54 se registró al inicio de la sesión; los tiros posteriores mantuvieron ese ángulo. Aún falta observar un cambio de ángulo nuevo después de pasar a otra pestaña. También se corrigió el inicio en frío: espera a que cargue la sesión y la entrada a Avatar Off, en vez de detenerse por no encontrarla de inmediato.

Distribución de prueba: DragonLab-Prueba-0.14.7.zip. Preparación Cloud: DragonLab-Launcher-0.14.7.zip; requiere configurar previamente los servicios. No publiques claves privadas, sesiones ni mediciones personales.
