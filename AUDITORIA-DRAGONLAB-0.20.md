# Auditoría integral previa a DragonLab 0.20

Fecha: 12 de noviembre de 2026. Referencia de código: commit `a0a2cde`, más los cambios locales de presentación 0.19.1 que estaban en revisión al realizar esta lectura. Esta auditoría es anterior a implementar las correcciones de sesiones y objetivos. Las líneas citadas son las observadas entonces y pueden desplazarse con las correcciones posteriores.

## Alcance y método

Se revisaron adquisición CDP, adaptadores, selección de jugadores, captura y proyección, estados del motor, configuración, atajos, perfiles, guía nativa, launcher, diagnóstico y límites del entrenador. No se modificó Python ni Rust y no se enviaron entradas al juego. No se leyeron cookies, contraseñas, almacenamiento de cuentas ni archivos de sesión protegidos.

Se intentaron dos lecturas pasivas del adaptador DragonBound, en los endpoints locales 9223 y 9224, para recoger únicamente cantidades y tipos de campos del roster. Ambas terminaron con `TimeoutError`. Por tanto, **esta revisión no acredita haber reproducido en vivo el cambio de cuenta ni el caso de ocho o más jugadores**. Las causas confirmadas a continuación son propiedades del código; sus efectos concretos en esa partida se distinguen como inferencias.

No se ejecutó una nueva suite completa como parte de esta auditoría de solo lectura. Las pruebas históricas de una versión anterior no sustituyen la validación posterior a los cambios 0.20.

## Inventario funcional observado

| Área | Funcionalidad existente | Fuente principal | Límite relevante |
|---|---|---|---|
| Entrada del producto | Login real; prueba local; Manual y Automático separados; una instancia; versión visible | `launcher.py:65`, `launcher.py:401`, `launcher.py:414` | Abrir una versión nueva mientras la anterior sigue activa restaura la instancia previa. |
| Acceso y servidor | Sesión protegida con DPAPI; vencimiento y estado de cuenta; refresh; consentimiento; envío de mediciones numéricas | `cloud_client.py:13`, `cloud_client.py:22`, `cloud_client.py:46`, `cloud_client.py:66`, `cloud_runtime.py:12` | Tener código Cloud no prueba que el servidor de producción esté configurado o desplegado. |
| Actualizaciones | Manifest GitHub, URL del repositorio autorizada y SHA-256; handoff de proceso | `launcher.py:50`, `launcher.py:374`, `cloud_client.py:87` | La comprobación automática al abrir juego existe; el control de comprobación manual no está visible en la vista actual. |
| Juegos del launcher | DragonBound y GunBound World | `game_catalog.py:1` | El selector principal no promete compatibilidad universal con cualquier clon. |
| Conectores avanzados | DragonBound; GunBound World; clon configurable por rutas; captura manual | `adapters.py:9`, `advanced.py:45` | Una ruta o dominio registrado no equivale a física comprobada. |
| Navegador | Reutilización de pestaña; perfil gestionado; lectura loopback por CDP | `game_startup.py:5`, `app.py:401`, `cdp.py:5` | Selección automática de la primera pestaña coincidente; falta una identidad de sesión que sobreviva a las reconexiones sin mezclar estados. |
| Captura y geometría | Rectángulo DOM del juego/barra; origen físico de Chrome; DPI; imagen opcional; cámara y terreno | `automatic.py:5`, `automatic.py:36`, `automatic.py:82`, `projection.py:3`, `cdp.py:170` | Fallos transitorios de geometría o cambios de contexto pueden retirar la guía o conservar cachés sin un motivo observable detallado. |
| Jugadores y objetivo | Normalización de IDs y coordenadas; héroe; equipo/muerte; orden estable; objetivo automático y ciclo Ctrl | `targeting.py:6`, `targeting.py:30`, `targeting.py:39`, `targeting.py:44`, `app.py:573`, `app.py:635` | No hay límite de tres enemigos; sí hay pérdidas posibles antes y durante la normalización. |
| Cálculo manual | Física base y extendida; terreno; viento; climas; cancelación; un cálculo activo y una solicitud sustituible | `core.py:122`, `physics_extensions.py:300`, `latest_calculation.py:7`, `solve_control.py:4` | Un resultado debe pertenecer al contexto actual. Se necesitan más dimensiones de identidad que IDs de actor y coordenadas. |
| Rust | Aceleración de los modelos portados; cancelación atómica; dibujo pasivo; fallback Python/Tk | `native_solver.py:17`, `native_overlay.py:10`, `native/dragonlab_core/src/engine.rs`, `native/dragonlab_overlay/src/lib.rs` | La migración es parcial. Un fallback no constituye calibración de una modalidad pendiente. |
| Marca y trayectorias | Fuerza, línea recomendada/observada, enemigos fuera de vista, anotaciones de clima | `app.py:352`, `app.py:369`, `native_overlay.py:87`, `trajectories.py:24` | Hay que distinguir cuantos actores existen de cuantos rótulos pueden distinguirse visualmente. |
| Disparo manual por atajo | Q o tecla personalizada; gesto confiable; validación nativa de turno/pose/viento/objetivo; una acción | `shortcuts.py:34`, `browser_shortcuts.py:8`, `app.py:105`, `auto_fire.py:24`, `gunbound_fire.py:10` | Los eventos y planes necesitan una época de sesión explícita, incluso si el nuevo jugador reutiliza el mismo número. |
| Ajustes cotidianos | Trayectorias, marca, color, grosor, teclas y habilitación de Q; rendimiento Auto/Ligero/Normal | `simple_settings.py:10` | Diagnóstico, tamaño de texto, compacto y herramientas avanzadas se ocultan en el motor embebido del launcher. |
| Biblioteca/calibración | 22 vehículos reconocidos y 66 modalidades en manual; datos separados por clon/vehículo/tiro; biblioteca aprendida | `mobile_catalog.py:7`, `learning_library_ui.py:8`, `calibration_book.py:22`, `manual_learning.py:140` | Reconocimiento, ajuste de salida, recorrido especial y precisión de impacto son estados distintos. |
| Herramientas de laboratorio | Captura de área, imagen, posiciones, importación/exportación, calibración, búsqueda de ángulos, OCR, terreno y trayectorias | `settings_panel.py:8`, `advanced.py:13`, `vision_tools.py:15` | Se conserva código antiguo con colores propios y ventanas sin el control uniforme del launcher. Parte de la ruta no es accesible desde el producto embebido. |
| Entrenamiento | Una/dos sesiones con pestañas fijadas y carpetas separadas; límites de tiempo; evaluación; observación del rival; guías numéricas | `training_ui.py:28`, `training_group.py:21`, `training_browsers.py:9`, `training_session.py:6` | El selector implementado admite 1 o 2 sesiones, no ocho; es distinto de tener ocho enemigos en una partida. Sigue siendo experimental. |
| Diagnósticos | Estado local opcional, detalles de aprendizaje/Q, exportación acotada de casos | `app.py:777`, `diagnostics_ui.py:6`, `diagnostics_ui.py:22` | El archivo requiere `--diagnostics`; la ventana es una instantánea y no explica dónde se perdió cada jugador. |

## Observado en el código

### P1 · La identidad de sesión de juego es incompleta

1. `CDP` mantiene `game`, `renderer`, terreno y estado de vuelo en la conexión (`cdp.py:26`). `call()` consume y descarta eventos no correspondientes a la respuesta, salvo que exista un `event_handler` (`cdp.py:59`). El lector ordinario no instala un manejador que invalide referencias ante cambio de contexto/documento.
2. `discover()` deduplica handlers por su texto `description`, no por la identidad `objectId` (`cdp.py:77`). Dos closures distintas con el mismo código pueden representar objetos de juego distintos y la segunda se omite.
3. El estado DragonBound se considera `live` salvo `destructed === true` (`cdp.py:176`). A la vez se exporta `over` por `isGameOver` (`cdp.py:179`), pero ese fin de partida no invalida por sí mismo el objeto cacheado.
4. El héroe se serializa con `pick(this,["my_player","myPlayerNumber","my_player_number"])` sin normalizar el tipo (`cdp.py:179`). Si el primer alias es un objeto, prevalece sobre un número válido posterior. Además podría serializar un objeto completo donde solo debe viajar un ID acotado.
5. `PlayerTracker` se reinicia cuando el estado deja de ser `live` (`app.py:522`); no existe una época de sesión en la clave de su caché (`targeting.py:6`). Un actor con ID reutilizado puede conservar datos anteriores durante 0,8 s.
6. Al cambiar el ID del héroe se restablece el objetivo seleccionado (`app.py:575`), pero no se hace un reinicio integral de tracker, correlación de tiros, terreno, gestos, planes pendientes y resultados. Si el ID sigue siendo 0, ni siquiera cambia esa condición.
7. `fire_context()` incluye el fingerprint y las variables, pero no documento, pestaña, objeto de partida ni época de usuario de juego (`app.py:88`). La cola acepta eventos de objetivo/disparo basados principalmente en ID de héroe. El contexto nativo final es una protección importante, pero no sustituye una identidad de origen explícita.

**Consecuencia comprobada de diseño:** ningún contrato impide que un resultado o gesto de la sesión A alcance la cola de la sesión B si reutiliza sus números y condiciones. Esto no afirma que se haya enviado un tiro incorrecto en vivo; identifica la ausencia de una barrera de identidad verificable.

### P1 · La adquisición del roster puede perder jugadores antes de filtrar

- DragonBound hace `entries.slice(0,16)` antes de comprobar que cada entrada sea un jugador (`cdp.py:130`). La fuente es `Object.entries()` del primer alias disponible. Un `Map` no se enumera así; entradas auxiliares pueden consumir el cupo; `players` vacío/obsoleto puede ocultar `player_list` válido.
- El adaptador genérico también aplica el cupo de 16 antes del filtro (`adapters.py:200`). Su enumeración de objeto tiene otro límite de 64 propiedades (`adapters.py:197`). GunBound World tiene un tratamiento específico de `Map/$items`, pero otros esquemas no lo comparten.
- Los IDs repetidos se sobrescriben al normalizar (`targeting.py:36`). Faltan diagnóstico y trazabilidad de los descartes por ID ausente/duplicado, coordenadas inválidas, muerto o aliado.
- `enemies()` filtra muertos y miembros del mismo equipo (`targeting.py:44`). Esto es correcto si el esquema de equipo está bien leído, pero no existe contabilidad explícita que permita distinguir un filtro correcto de un alias mal interpretado.
- No se encontró un corte a tres enemigos en el selector, ciclo Ctrl ni renderer. El popup muestra siete filas a la vez y tiene desplazamiento (`rounded_controls.py:70`, `rounded_controls.py:95`); eso no limita la colección a siete, ni a tres. El renderer Rust acepta hasta 256 jugadores.

### P1 · Etiquetas y selección deben distinguir héroe, aliados y enemigos

`NativeTrajectory.update()` recorre todos los jugadores vivos y asigna `ENEMIGO n` a los miembros de `numbers`; a cualquier otro le asigna `TÚ` (`native_overlay.py:107`). Así un aliado puede recibir la etiqueta del héroe aunque su flag `hero` sea falso. Debe haber al menos tres roles explícitos.

Los enemigos fuera de vista se ajustan al borde del campo. Varios actores pueden caer en la misma coordenada de borde y sus rótulos se superponen. El conteo del roster y el número de etiquetas distinguibles en pantalla deben medirse por separado. Una estrategia de separación/agrupación de rótulos no debe eliminar objetivos de la lista o del ciclo Ctrl.

### P1 · Selección de pestaña y validación de dominio

La selección automática usa la primera pestaña que coincide (`adapters.py:80`, `game_startup.py:10`). `activate_existing_game()` devuelve solo un booleano; el motor no conserva como resultado el ID exacto recién activado. Con dos pestañas del mismo dominio se puede activar o leer una distinta de la que mira el usuario.

Cuando se proporciona un `target_id` explícito, `CDP.__init__` lo selecciona por ID sin exigir también el hostname esperado (`cdp.py:10`). La UI avanzada permite listar todas las páginas y elegir una. Se necesita validar que perfil, dominio y target pertenecen a la misma fuente, con una excepción explícita para perfiles genéricos configurados por el usuario.

### P1 · Hay dos esquemas de perfiles físicos con alcances diferentes

- `CalibrationBook.key()` separa clon, móvil y modalidad (`calibration_book.py:22`); `compatible_fit()` también comprueba esos tres campos y el régimen observado (`cloud_profiles.py:3`). Es un aislamiento existente que debe conservarse.
- Los ajustes manuales personalizados usan `App.profile_key() == clone + ':' + mobile` (`app.py:237`). `save_profile()` no añade la modalidad. Por ello el ajuste personalizado de un tipo de bala puede aplicarse a otro cuando no lo sustituye un perfil medido. Se requiere migración compatible y etiqueta de alcance explícito; no convertir automáticamente un perfil antiguo en tres calibraciones validadas.
- La biblioteca manual aprendida solo aplica sus perfiles a DragonBound y conserva regímenes/límites (`manual_learning.py:140`). GunBound World mantiene sus parámetros medidos propios (`gunbound_profiles.py:5`). No se debe unificar la física de ambos por compartir el nombre Armor.

### P2 · Configuración y diagnóstico existen, pero parte del producto no puede alcanzarlos

- Todo `EngineHost` crea el motor con `embedded=True` (`engine_host.py:27`). `simple_settings.py:56` oculta el botón de diagnóstico precisamente en ese caso; también oculta las opciones avanzadas (`simple_settings.py:79`). Por tanto no basta con que esos módulos existan para afirmar que el cliente tiene diagnóstico accesible.
- `diagnostics_ui.open_diagnostics()` no registra `app.diagnostics_window`, no reutiliza una ventana existente y no actualiza sus filas periódicamente (`diagnostics_ui.py:22`). El método de parada del host busca ese atributo para cerrar herramientas (`engine_host.py:42`).
- El panel de versiones se crea y sus hijos se empaquetan, pero el propio panel no se muestra con `pack/grid/place` (`launcher.py:117`). Su botón de buscar actualizaciones queda invisible; la actualización al abrir el juego sí está implementada.
- `settings_panel.py`, `advanced.py` y `diagnostics_ui.py` mantienen paletas y tamaños fijos anteriores. El launcher y `theme.py` nuevos no unifican automáticamente esas ventanas.
- El estado local incluye actores detectados y enemigos (`app.py:779`), pero no cantidad bruta, posiciones descartadas, duplicados, aliados, origen/época ni motivo de invalidación de la conexión. Sin esos campos no se puede demostrar si “solo tres” viene de lectura, filtrado o dibujo.

### P2 · Persistencia y modo de ejecución

La edición de prueba busca datos cerca del ejecutable y, si no encuentra el archivo de calibración esperado, usa `BASE/datos` (`launcher.py:309`). Ejecutar desde una extracción temporal de un archivo comprimido puede dejar datos en una ubicación volátil. La edición Cloud sí usa un directorio permanente por proyecto Supabase (`cloud_client.py:28`). Antes de cambiar las rutas hay que identificar la ubicación real y migrar solo los archivos propios autorizados; no copiar perfiles del navegador ni credenciales.

Las dos sesiones de entrenamiento ya fijan endpoint/target y usan directorios separados (`training_group.py:21`, `training_browsers.py:9`). Este mecanismo es más estricto que la elección automática del manual, y puede aportar el contrato de origen sin activar entrenamiento.

## Inferido: explicación probable de los errores comunicados

| Síntoma | Cadena causal plausible | Evidencia que todavía falta |
|---|---|---|
| Cambio de cuenta en la misma pestaña deja de detectar bien | Objeto anterior aún válido → discovery no se repite o omite closure equivalente → héroe/roster/terreno cacheados → IDs reutilizados no provocan reset integral | Capturar solo época/contexto, tipo del alias héroe, cantidades del roster y flags de cierre antes/después de un cambio real. |
| Más de ocho jugadores pero solo tres objetivos | Fuente truncada antes de filtrar, alias viejo o posiciones inválidas; después filtro de equipo/muerte o colisión de IDs | Cantidades `raw/object/valid/alive/friendly/enemy/duplicates/truncated`, con motivos, no listas de cuentas. |
| Hay enemigos pero solo se distinguen tres marcas | Varias etiquetas clamped al mismo borde, rótulos superpuestos o aliados etiquetados como héroe | Comparar conteo de enemigos con marcadores dibujados y cajas de etiquetas, en una escena sintética y una partida real. |
| Una pestaña funciona y la otra no | Se sigue leyendo la primera coincidencia del dominio; la pestaña enfocada tiene otra identidad | Mostrar target fijado, dominio y estado de foco de forma diagnóstica; no adivinar por el título. |
| Cambiar de juego o modalidad reutiliza un ajuste equivocado | El book está separado, pero perfiles personalizados o estado visual transitorio tienen un alcance más amplio | Regresión de ida/vuelta entre DB/GB y entre tiros 1/2/SS, con parámetros físicos distintos y sin perfiles nuevos inventados. |
| Botones “faltan” o estados no explican el fallo | Funciones creadas pero inaccesibles en modo embebido; diagnóstico estático sin contabilidad de filtros | Matriz de accesibilidad de acciones en login, prueba, cuenta activa/vencida, manual y automático. |

Estas son inferencias del flujo observado, no una afirmación de que todos los síntomas tengan una única causa.

## Pendiente de comprobar

1. Una reproducción pasiva del cambio de cuenta en la misma pestaña, sin reiniciar el programa, y una nueva partida con nueve o más actores. En esta auditoría los endpoints no respondieron.
2. Confirmar el esquema real actual de los campos `players/player_list`, héroe y equipos. No ampliar alias o ejecutar getters arbitrarios por conjetura.
3. Verificar etiquetas amontonadas con 8, 12, 16 y más actores sintéticos, incluyendo aliados, muertos y enemigos fuera de vista.
4. Recorrer todas las acciones del producto en las distintas etapas de acceso. Un test que comprueba solo que un botón existe no demuestra que sea visible, esté habilitado cuando corresponde o ejecute la acción correcta.
5. Contrastar GunBound World por separado. El soporte de fase/controlador/terreno no equivale a que todos sus carros, modalidades y climas estén calibrados.
6. Confirmar alineación y escala a 100/125/150/200 % de DPI, zoom del navegador, dos monitores y movimiento de ventana. La QA sintética del renderer no reemplaza la partida real.
7. Establecer la ruta de datos permanente y la política de perfiles compartidos. Datos de física comprobada pueden compartirse deliberadamente; objetivo actual, controles, terreno y correlación de tiros no deben cruzar sesiones.

## Plan de corrección priorizado

### Fase A · Contrato de fuente y sesión

- Incorporar un contexto de adquisición con endpoint canónico, target fijado, host/adapter, época de documento, identidad acotada del objeto de partida y héroe de juego. No leer cookies, contraseñas ni inventariar datos de cuenta para obtenerlo.
- Invalidar objetos CDP ante cambio de contexto, cierre de target, partida terminada o incompatibilidad de la estructura. No deduplicar funciones distintas solo por su texto.
- Unificar un reinicio atómico de la sesión: cancelar cálculo y acción pendiente; liberar controles mediante su cancelación normal; limpiar tracker/selección/fingerprint/terreno/trazas/gestos/correlación; conservar configuraciones y modelos persistidos.
- Etiquetar muestras, resultados, gestos y planes con esa época. Rechazar eventos de otra época aunque sus IDs y coordenadas coincidan.
- Normalizar héroe como ID primitivo. Una referencia a objeto solo se interpreta mediante campos de ID de jugador explícitos y acotados, nunca se exporta completa.

### Fase B · Roster completo y trazable

- Enumerar el tipo de colección observado (array, objeto, Map o MapSchema admitido), filtrar candidatos de jugador antes de aplicar un límite de seguridad y publicar `truncated` si se alcanza.
- Preservar IDs nativos estables, con tratamiento explícito de ausentes/duplicados. No inventar IDs de índice si pueden cambiar de orden entre fotogramas.
- Separar héroe, aliados, enemigos, muertos y desconocidos; conservar todos los enemigos vivos válidos para selector y Ctrl.
- Añadir contabilidad numérica de cada etapa. Una UI pequeña puede mostrar el objetivo seleccionado y el total, con detalle bajo diagnóstico.
- Resolver colisiones de rótulos o agrupar los de un mismo borde sin reducir la colección de objetivos.

### Fase C · Configuración y perfiles

- Definir ajustes globales de aspecto/atajos y ajustes de adquisición por juego; estado de sesión solo en memoria y con época.
- Hacer específicos por modalidad los perfiles personalizados nuevos. Mantener los antiguos como “perfil general de vehículo”, sin promoverlos a calibración validada.
- Mantener las claves separadas de DB/GB y los dominios de fuerza/viento/tiempo. Un móvil desconocido queda pendiente y no hereda el anterior.
- Migrar rutas de datos con respaldo y sin tocar cookies, sesiones protegidas o archivos del programa de referencia.

### Fase D · UI, atajos y observabilidad

- Dejar las acciones de uso diario simples; colocar diagnóstico y herramientas en una ruta accesible y única, sin duplicar la pantalla principal.
- Hacer dinámico el diagnóstico y deduplicar su ventana. Usar `theme.py` y medidas adaptadas en todas las herramientas que sigan expuestas.
- Explicar el estado de conexión con su causa real y edad, diferenciando “sin partida”, “cambio de sesión”, “identificando héroe”, “roster incompleto”, “sin modelo” y “sin solución”.
- Mantener Q cerrado por defecto ante datos viejos o incompatibles. Ctrl no debe reaccionar a eventos de otra sesión ni al chat; añadir al alcance del atajo un flag de edición de DOM que no lea el texto.
- El render puede tener una política visual estable, pero nunca debe convertir un valor retenido para dibujo en autorización de disparo.

## Criterios de aceptación antes de publicar 0.20

| Prueba | Resultado exigido |
|---|---|
| Navegación/relogin SPA con héroe numérico 0 reutilizado | Se crea una nueva época; no aparecen objetivo, tiro pendiente, terreno ni resultado de la anterior. |
| Objeto viejo `isGameOver=true`, `destructed=false` | Se retira como fuente de partida activa y se busca la nueva. |
| Dos closures con la misma descripción | Se examinan por identidad; no se descarta el objeto actual por compartir código. |
| `my_player` objeto y `my_player_number` válido | Se emite un ID primitivo correcto, sin serializar el objeto. |
| Roster de 9/16/32 entradas con metadatos y huecos | El número válido no depende del orden de las propiedades; cualquier truncado es explícito. |
| IDs duplicados/ausentes y coordenadas transitorias | El diagnóstico explica el descarte; no se sustituyen silenciosamente actores por otro objetivo. |
| 4v4, muertos y actores fuera de vista | Totales de héroe/aliados/enemigos correctos; ningún aliado figura como `TÚ`; todos los enemigos permanecen en Ctrl. |
| Pestañas del mismo host y hosts distintos | Target fijado sin ambigüedad; perfil y dominio compatibles; no se controla otra pestaña. |
| Cambio DB ↔ GB y tiro 1 ↔ 2 ↔ SS | No se cruzan parámetros, máximo de fuerza, marcas ni correcciones personalizadas no aplicables. |
| Cambio de sesión mientras calcula o espera Q | El trabajo anterior se cancela y jamás publica ni dispara sobre la sesión nueva. |
| Manual vs Automático | Manual no activa entrenador; la selección de actores no altera las sesiones paralelas. |
| Diagnóstico/ajustes/ayuda/actualización | Una ruta accesible, una ventana por herramienta, estado actualizado y botones sin recortes. |
| Sin conexión o esquema desconocido | Mensaje honesto; guía pendiente y Q bloqueado; no se inventan calibraciones o posiciones. |

La corrección de estas condiciones debe validarse antes de volver a afirmar autonomía, cobertura completa o precisión de todos los carros. Cantidad de tiros, catálogo reconocido, paridad entre motores y resultado competitivo miden cosas diferentes.
