# DragonLab 0.12.2

La versión Cloud quedó preparada en el PR #1. Crear Supabase y el alojamiento siguen siendo necesarios para activar cuentas reales. Este cambio corrige el cliente de partida y es independiente del despliegue.

## Q / autotiro

Pulsa y suelta Q una vez en tu turno, con DragonBound en primer plano y sin mantener controles de movimiento, ángulo, Espacio o el mouse. Puedes cambiar la tecla en Ajustes. F8 sigue perteneciendo al juego.

- Lee Slice / Drag desde el botón del juego en cada consulta; no depende de una variable de un cierre JavaScript concreto.
- Drag comienza sobre una zona libre del campo. La marca de fuerza es un control de interfaz y puede interceptar el arrastre.
- Sigue la fuerza visible y espera a confirmar una carga nueva; la sensibilidad y la velocidad de carga varían en el juego.
- Usa SendInput de Windows y comprueba que la entrada fue aceptada. No modifica el estado del juego ni llama a sus funciones de disparo.
- Si el cálculo está terminando, conserva la solicitud hasta 0,8 segundos y solo para ese ángulo y objetivo. Cambios posteriores o vencimiento la descartan. No repite automáticamente una carga que falló.
- Rechaza chat, otro turno, movimiento, datos incompatibles y fuerza inválida. Comprueba foco y posición de la ventana también después de leer datos.
- Libera la entrada al terminar o fallar. Si pierdes foco o mueves el mouse manualmente, no devuelve el cursor sobre otra aplicación.

**Esc libera la entrada. Si ya comenzó la carga, el juego puede disparar con fuerza parcial al soltar. No se garantiza anular un disparo iniciado.** Windows puede rechazar entrada entre procesos con niveles de permisos distintos: abre normalmente ambos programas.

## Guía estable

Al cambiar el ángulo, la trayectoria anterior se conserva hasta 1,5 segundos mientras calcula, en color atenuado y con la marca «Actualizando». No se puede disparar con ella. Se elimina al cambiar el objetivo, posición, carro, modalidad o terreno. Las líneas con puntos inválidos tampoco dejan una trayectoria anterior visible.

## Validación

12 pruebas locales cubren carga Slice/Drag, sensibilidad variable, fuerza anterior, chat, turno ajeno, cambio de ángulo, pérdida de foco durante una lectura, solicitud única pendiente y continuidad/invalidación de trayectorias. El arranque de Windows y las lecturas del navegador se comprueban por separado. Se pudo leer en la partida la modalidad Drag y confirmar que el juego varía sensibilidad y duración; el tiro real con Q requiere la prueba del jugador en la nueva versión.

Referencia de la entrada nativa: https://learn.microsoft.com/en-us/windows/win32/api/winuser/nf-winuser-sendinput
