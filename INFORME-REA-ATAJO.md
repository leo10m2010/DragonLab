# Atajo de tiro de DragonboundGPT: investigación REA

10 de octubre de 2026. Alcance: instalación autorizada, atajo y carga de fuerza; sin iniciar tiros ni usar cuentas o licencias del original.

## Resultado

La documentación distribuida del original describe un programa externo que reserva un atajo de Windows, espera a que se suelte, valida el turno y la proyección, y arrastra el mouse para cargar la fuerza. Lee por CDP la sensibilidad asignada después de pulsar el botón y comprueba la barra antes de soltarlo. El juego procesa esas entradas y envía el tiro. No necesita un modelo de IA para ejecutar este atajo.

Esta es una descripción recuperada del paquete, respaldada por constantes y nombres de componentes; no equivale a una traza de ejecución ni a una descompilación completa.

## Evidencia y procedencia

- Ejecutable instalado: `E:/db/DragonboundGPT/DragonboundGPT.exe`, SHA-256 `e11ec028464322651f61f24107ab6239be534bb683cf46bbe500752dccf36666`.
- REA volvió a abrir el mismo ejecutable e identificó PE x64. Los proveedores nativos Ghidra/IDA no están configurados y Hopper no está disponible en Windows. La búsqueda nativa devolvió `provider_unavailable`; no se atribuyen llamadas ejecutadas a una descompilación inexistente.
- Recuperación estática propia del recurso PE RT_RCDATA 27, firma `KAY`, siguiendo el formato del código público de Nuitka: <https://github.com/Nuitka/Nuitka/blob/develop/nuitka/build/static_src/OnefileBootstrap.c>. No se ejecutó el original. La descompresión produjo el flujo de archivos completo hasta el nombre vacío final; el lector Zstandard informó posteriormente bytes de cola no reconocidos. No se declara verificada la integridad global del contenedor.
- DLL recuperada: `dbai_entry.dll`, 39.561.216 bytes, SHA-256 `31720363511f45460a5f5148fd7a681f28c87f71a9a2b73c0c0ef3d05c59eaec`.
- REA `inspect_managed_artifact`, evidencia `ev_f1149d952e45cf9a8a662c23bd56586b9f8281e71eb8e9567c80cdd40b4ade77`: identifica la DLL como PE x64 sin CLI/CIL. Esta evidencia acredita identidad/clasificación, no el flujo del atajo.

Lecturas directas de bytes de esa DLL, con desplazamientos de archivo:

| Ubicación | Observación | Alcance |
| --- | --- | --- |
| 35789012, sección Autoshot | La documentación indica Shift + Espacio por defecto, modo Drag, liberación del atajo, una acción por pulsación, foco y proyección vigente. | Comportamiento documentado; no prueba de ejecución. |
| 35790696 | La documentación nombra SetCursorPos, SendInput y lectura CDP de la carga. | Método declarado por el fabricante. |
| 39136295–39139159 | AutoShotController, trigger, cancel, validación del plan, bloqueo de intentos simultáneos y espera de liberación del atajo. | Constantes observadas; sus nombres sugieren separación entre solicitud y ejecución. |
| 39247107–39247885 | RegisterHotKey, UnregisterHotKey, GetMessageW, WM_HOTKEY, MOD_NOREPEAT y errores de registro. | Evidencia estática de una implementación de atajos globales; las llamadas efectivas requieren análisis nativo o traza. |
| 39414660–39415357 | Estructuras INPUT y SendInput, SetCursorPos y errores de entrada. | Evidencia estática compatible con entradas normales de Windows. |
| 39420607–39421073 | Lectura de dragSensitivity, devicePixelRatio y dragStartX; bloqueos por carga o sensibilidad inconsistente. | Compatible con el método descrito, sin reconstruir el código original. |

Se revisaron los cinco diagnósticos conservados actuales. Sus eventos no incluyen intentos Autoshot; no sirven para demostrar un disparo real del original. Los registros más antiguos mencionados en la investigación inicial ya no están en esta carpeta.

## Comparación y cambio propio

DragonLab ya usa SendInput para la acción y CDP para observar la barra. La versión 0.12.2 no registró la Q del usuario. En 0.12.3 el canal pasivo de teclado de la página registró seis pulsaciones y rechazó el tiro por no ser el turno propio; eso valida recepción y bloqueo, no el disparo.

La revisión 0.12.4 cambia el primer movimiento de Drag: espera el estado de carga y lee la sensibilidad nueva antes de ir directamente hacia la fuerza solicitada. Elimina el movimiento pequeño usado para estimarla y conserva la comprobación de la barra y la liberación en errores. Si falta la sensibilidad no la inventa ni reintenta. También cierra la conexión si falla la lectura inicial.

Se mantienen Q personalizable, Ctrl para objetivos y F8 reservado al juego. La escucha pasiva de la página acepta únicamente eventos de usuario, ignora repetición, chat y modificadores, y no llama a funciones de disparo. La entrada se envía desde el programa de Windows.

## Verificación y límite

Pasaron 14 pruebas controladas de carga, sensibilidad nueva, ausencia de sensibilidad, carga no iniciada, foco, turno, posición/ángulo y continuidad de guía. Una prueba en Chrome propio verificó Q, tecla personalizada, repetición, eventos sintéticos, chat, modificadores y salida de la partida. Son pruebas controladas, no tiros reales.

La partida conectada estaba fuera de juego al terminar esta lectura. Sigue pendiente probar Q en el turno del usuario con 0.12.4 y verificar la fuerza real liberada. No se afirma que el bug completo esté resuelto hasta esa comprobación. Esc suelta la entrada: si el arrastre ya comenzó, el juego puede lanzar una fuerza parcial.
