# Auditoría de ventana y UX · preparación de 0.20

## Alcance y conclusión

Esta revisión es de lectura del código actual y de las mediciones de geometría ya realizadas; no aplica una nueva corrección ni presenta una reproducción visual del último defecto. La nueva evidencia del usuario —ventana fragmentada al arrastrarla— exige reparar primero el contrato de ventana. No basta con recolorear tarjetas o retocar el motor balístico.

La decisión recomendada es **usar la ventana nativa de Windows, con barra de título oscura, redimensionable y con los controles normales de minimizar, maximizar y restaurar**. Se elimina la modificación que retira el marco a espaldas de Tk. El movimiento, Snap, los bordes de redimensionado y los límites de maximización pasan al gestor de ventanas. La superficie cliente conserva el diseño carbón; el lima será únicamente un acento.

El hero lima introducido en la iteración anterior no cumple la nueva indicación explícita del usuario. Debe volver a carbón. El estado seleccionado, los iconos puntuales y la acción principal pueden emplear lima; no se mantendrán grandes fondos verdes.

## Hallazgos de ventana

| Prioridad | Evidencia del código | Consecuencia y decisión |
|---|---|---|
| P1 | `desktop_shell.py:14` quita `WS_CAPTION` y `WS_THICKFRAME` directamente; `:16` fuerza recálculo no cliente con `SetWindowPos`. | Tk continúa siendo el dueño de la geometría, pero otro código cambia su marco nativo. En la QA anterior, pedir `660x650` acabó en un cliente de `676x690`. Esta discrepancia medida es compatible con un desacuerdo entre geometría cliente y marco; no prueba por sí sola todos los píxeles del último fragmentado. Conservar los estilos del marco normal y oscurecerlo mediante DWM, sin quitarlos. |
| P1 | `desktop_shell.py:23–30` implementa el arrastre con una llamada a `root.geometry()` por cada movimiento del ratón. No utiliza el ciclo nativo de mover/redimensionar. | El desplazamiento manual multiplica las actualizaciones de posición de la ventana mientras sus Canvas y ventanas hijas se componen por separado. Es una causa plausible adicional del artefacto, que debe contrastarse con la misma maniobra después de la corrección. Retirar este bucle y usar el arrastre normal de la barra nativa. Si se conserva una zona cliente de arrastre, delegar un único inicio de movimiento a Windows. |
| P1 | `desktop_shell.py:27–28` limita la posición a `winfo_screenwidth/height`, impide `y<0` y usa el tamaño de una pantalla como si fuera todo el escritorio. | No admite correctamente monitores a la izquierda o encima del principal. Windows debe gestionar el movimiento; para posiciones iniciales/restauradas se usará el área de trabajo del monitor pertinente, incluyendo coordenadas negativas. |
| P1 | `launcher.py:68` desactiva ambos ejes de redimensionado. No hay control de maximizar/restaurar; solo botones propios de cerrar/minimizar en `:78–79`. | El cliente no ofrece las capacidades solicitadas y no puede adaptarse a pantallas pequeñas o ventanas maximizadas. Habilitar redimensionado, tamaño mínimo funcional, maximización/restauración nativas y un contenido que se adapte al cliente real. |
| P1 | `launcher.py:143–150` hace hasta tres rondas de medir, ejecutar tareas de layout y escribir geometría; `:155`, `:161` y `:424` vuelven a aplicar `style_window`. | La solución actual persigue el tamaño de un marco que también está cambiando. Sus mediciones no constituyen un layout adaptable. Cambiar a un tamaño inicial elegido una sola vez, más `minsize`, distribución flexible y desplazamiento en vistas que excedan el alto disponible. No forzar de nuevo el tamaño elegido por el usuario durante cambios de juego/estado. |
| P1 | `app.py:59` llama a `SetProcessDpiAwareness(2)` cuando el motor se construye, después de que el launcher ya haya creado su `Tk`. No hay una política de DPI de arranque en `launcher.main`. | Microsoft exige establecer el DPI de proceso antes de crear cualquier HWND; esta llamada tardía no es una base válida para una estrategia de escala. Configurar la conciencia DPI en el manifiesto del EXE —preferido— y una inicialización de respaldo previa a `Tk` para ejecución desde fuente. La conversión CSS/píxeles físicos de captura y el overlay deben seguir una política común. |
| P2 | `desktop_shell.py:21` silencia los errores de estilo y de DWM. | La UI no distingue entre el modo previsto y una decoración parcialmente aplicada. Un fallo cosmético debe dejar una ventana nativa utilizable, con un diagnóstico cerrado, no una mutación parcial que luego se sigue redimensionando. |

La documentación de [estilos de ventana de Microsoft](https://learn.microsoft.com/en-us/windows/win32/winmsg/window-styles) define `WS_CAPTION`, el borde de tamaño y los botones del marco normal. La [guía oficial de DPI de proceso](https://learn.microsoft.com/en-us/windows/win32/hidpi/setting-the-default-dpi-awareness-for-a-process) recomienda el manifiesto y establece el orden respecto a la creación de HWND. Estas fuentes sustentan la decisión de integración; la causa exacta de cada región del defecto visual requiere la prueba comparativa en la PC.

## Composición de controles y layout

`RoundedPanel` combina un Canvas que dibuja la forma con un Frame hijo incrustado (`rounded_widgets.py:21–39`). Al cambiar dimensiones, modifica el alto del Canvas y el ancho de la ventana hija desde dos eventos `Configure`. Esto no es una presentación atómica de toda la aplicación. El patrón puede permanecer para tarjetas decorativas, pero debe tener un único ajuste diferido por tamaño efectivo, evitar trabajo si las dimensiones no cambian y no utilizar el alto solicitado de un hijo como mecanismo para perseguir el tamaño exterior durante el arrastre.

La referencia del usuario se traduce a fondo `#0B0B0B`, superficies `#1B1B1B`/`#252525`, texto claro, bordes sutiles, radios coherentes y **lima `#BBFF00` solo en pequeños acentos**. No necesita gradientes, sombras animadas ni un hero de color. La mascota posterior debe dibujarse con geometría propia en Canvas, ser discreta y no introducir un bucle permanente de animación.

Los tamaños de fuente por píxel añadidos al launcher evitan el crecimiento accidental del texto respecto a sus cajas, pero no sustituyen una estrategia de DPI coherente ni un layout adaptable. Ajustes, biblioteca y popups todavía mezclan fuentes en puntos, altos fijos y longitudes de texto. Unificar sus tokens y medir con los estilos reales forma parte de la próxima implementación.

## Auditoría funcional de acciones

| Acción | Estado observado | Corrección o prueba requerida |
|---|---|---|
| Login real | `launcher.py:220–225` valida campos, borra la contraseña del widget y ejecuta la llamada fuera del hilo UI. `show_login` mantiene el panel autenticado oculto. | Conservar esta separación. Comprobar correo inválido, contraseña rechazada, red interrumpida, reintento y Enter. No convertir el login real en acceso simulado. |
| Acceso de prueba | `enter_demo` activa el acceso local sin credenciales y deja el motor detenido hasta la acción principal. | Conservarlo. El acceso demo sigue condicionado por `DEMO_ALLOWED`; no mostrar correo/contraseña innecesarios. |
| Abrir/Pausar juego | Existe una acción principal y protección frente a aperturas repetidas. Manual conserva el bloqueo de arranque del entrenador. | Mantener una sola acción visible y estados claros. Revisar cierre del motor, fallo de conexión, cambio de juego y reanudación. El texto del estado no debe alterar la geometría exterior. |
| Actualizaciones | `versions_panel` y `update_button` se construyen en `launcher.py:117–122`, pero ese panel nunca se empaqueta en ninguna vista. El botón existe en los tests, pero es inaccesible para el usuario. | P1: exponer la acción en un menú/cuenta/diálogo apropiado, con versión actual, comprobando, disponible y fallo. No llenar la vista principal con detalles de calibraciones. |
| Abrir juego con GitHub sin conexión | `play`, en `launcher.py:376–391`, combina comprobación de licencia y obtención del manifiesto. Si GitHub falla, tampoco inicia el motor integrado aunque el acceso sea válido. | P1: separar comprobación de acceso —que debe conservarse— de la actualización opcional. Un fallo del servicio de releases no debe bloquear un cliente ya disponible y compatible. Nunca omitir la comprobación de licencia para compensarlo. |
| Controles durante una operación | `run` deshabilita Login, Jugar, Actualización y Consentimiento, pero deja otros botones aparentemente activos. `open_settings` y `logout` retornan durante `busy` sin un feedback equivalente. El selector de juego también permanece habilitado. | P2: expresar disponibilidad con un estado centralizado; los controles que no pueden actuar no deben parecer operativos. Ayuda puede seguir accesible. Definir si el selector se bloquea o si el cambio queda pendiente. |
| Mi cuenta/soporte | `open_account` abre `panelUrl` HTTPS si existe; en caso contrario muestra un aviso de configuración pendiente. No existe un flujo de soporte independiente implementado. | Hacer que la acción refleje la disponibilidad real. Soporte debe llevar a instrucciones o a un destino configurado; no inventar un enlace ni afirmar que se envió un mensaje. |
| Consentimiento | `change_consent` envía el valor elegido y restaura el valor conocido si falla la operación. | Conservar carácter opcional, rollback y explicación visible. No guardar preferencias visuales como sustituto de aceptación del servidor. |
| Rendimiento | `simple_settings.py:54–60` ofrece Auto/Ligero/Normal. Guardar aplica el valor en `:68–75`. | Es una función real; necesita presentarse con el mismo sistema visual y una descripción breve. Probar persistencia, cancelar sin guardar y estado del modo activo. |
| Atajos | La selección usa `validate_bindings`; Ctrl no puede ser el disparo. `shortcuts.py` restringe las entradas al contexto del juego y conserva cancelación. | Conservar estos límites y el atajo real personalizado en la UI. Probar colisión de teclas, Q deshabilitado, chat, modificadores, foco ajeno y cambio de perfil. F8 no vuelve a introducirse. |
| Biblioteca | `RoundedTable.column` es un `pass` (`rounded_controls.py:224`), y cada fila concatena sus campos en un botón (`:230`). | P2: la apariencia de tabla no representa columnas que puedan adaptarse. Sustituir ese contrato por una tabla real o filas con celdas medidas; probar textos largos, teclado, selección, scroll y alto DPI. |
| Menús desplegables | `RoundedChoice` coloca su popup usando el tamaño de una pantalla (`rounded_controls.py:72–74`), con alto de fila fijo y un `grab`. | P1/P2: misma limitación multimonitor; cerrar/reubicar al mover/minimizar la ventana y garantizar que el grab se libere en cualquier ruta de cierre. Mantener teclado/Enter/Esc/Tab existentes. |

## Decisión de implementación y orden

1. Ventana nativa oscura, DPI de arranque y eliminación del arrastre por geometría. Eliminar los botones que dupliquen los controles nativos.
2. Layout adaptable: ancho útil, tamaño mínimo, maximización y restauración; desplazamiento de contenido en alturas pequeñas. No redimensionar la ventana por un nuevo mensaje de estado.
3. Hero carbón y lima de acento. Mascota Canvas propia, estática por defecto. Jerarquía breve: cuenta/sesión, juego, acción principal y estado.
4. Estado central de botones y acciones de actualización/soporte accesibles. Unificar Ajustes/biblioteca y popups con el mismo lenguaje visual.
5. Validar el conjunto en la PC y en ejecutable empaquetado. No se modifica la física para resolver un defecto del marco o de la composición visual.

## Criterios de aceptación

- Arrastrar despacio y rápido no deja regiones en la posición anterior ni recorta tarjetas. Mover la ventana no inicia cálculos ni cambia el tamaño cliente.
- Redimensionar desde los cuatro bordes y esquinas, maximizar, restaurar y minimizar repetidamente conserva contenido y acción principal. Alt+Tab, Alt+F4 y el menú de sistema funcionan.
- Probar el monitor principal y, si está disponible, otro con escala distinta, situado a izquierda/derecha/arriba. Las coordenadas negativas son válidas. Se registra lo efectivamente probado; simular DPI en Tk no equivale a esa prueba física.
- Capturas antes/después a 100/125/150 %, ventana normal, estrecha y maximizada. No hay texto o consentimiento cortado ni colores lima en grandes superficies.
- Cada botón visible tiene una acción comprobable o un estado deshabilitado comprensible. La versión y la comprobación de actualización son accesibles; no se muestran controles inertes.
- Pruebas de red y autenticación conservan los límites actuales. La actualización opcional no sustituye ni salta el acceso del servidor.
- La prueba anterior que exige eliminar `WS_CAPTION` (`tests/test_launcher.py:123–134`) debe cambiar de contrato: comprobar capacidades nativas y modo oscuro en lugar de fijar la ausencia de marco. Los tests actuales de límites de widgets no prueban arrastre, composición ni multimonitor.

## Límites de esta auditoría

No se tomaron credenciales, cookies, chats ni datos de jugadores. No se ejecutaron tiros ni entrenamiento. No se presenta el arrastre defectuoso como reproducido mediante una nueva captura en esta revisión. Las rutas de código y la discrepancia de geometría permiten priorizar la corrección del marco; la verificación visual de su reparación sigue siendo obligatoria.
