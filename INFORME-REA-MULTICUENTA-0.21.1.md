# Pestañas y cuentas: revisión de DragonboundGPT y DragonLab

14 de noviembre de 2026. Investigación acotada al artefacto instalado y a la pérdida de detección; no se leyeron perfiles del navegador, cookies, licencias ni credenciales. No se enviaron tiros reales.

## Artefacto y evidencia

`E:/db/DragonboundGPT/DragonboundGPT.exe`, versión 0.1.26.0, 40.235.008 bytes, SHA-256 `42af2996db786c6b76478ee4721f757cc9f5b57359fbf19058db69c5704df97d`. El hash se volvió a comprobar: coincide con la auditoría anterior.

REA MCP no está disponible en esta sesión. El CLI actual 6.9.0 rechaza Node 24.12.0; se utilizó el CLI 6.1.0 ya instalado, compatible con ese Node, sin modificar la configuración de Codex. Su diagnóstico informa que no hay motor nativo configurado. No se instaló software ni se atribuye descompilación nativa completa a este análisis.

Se ejecutó `analyze-javascript-application` sobre los recursos distribuidos `windvision/web_dist`. Evidencia REA `ev_c33e08cb11d64c1891a0565c28caa9601617c2dd4dcd59dc0a2ccf28126d5736`, identidad de contenedor `de31119d6c87e5fdb27a29dbd47aa5101f613bba0937e8092ec76abab14389ab`: cinco archivos relevantes, cuatro JavaScript analizados, cero errores de análisis y cero ámbitos truncados. El analizador leyó texto inerte; no ejecutó el programa. Su grafo no establece el comportamiento del host nativo PySide ni prueba soporte simultáneo de cuentas.

Los extractos de constantes nativas de la auditoría 0.1.26 se verificaron nuevamente contra los bytes del ejecutable. El registro privado `work/rea-multicuenta-native-evidence.json` conserva 15 coincidencias exactas. Hallazgos:

| Observación estática | Ubicación en el ejecutable | Alcance |
|---|---|---|
| `_find_target`, `targets`, URL de juego y `webSocketDebuggerUrl` | 39778329, 39778685, 39778710 | Existe descubrimiento de páginas CDP. No determina por sí solo cuál elige cuando hay varias. |
| `_poll_target(session, target)` y retorno `dict[str, Any] / None` de descubrimiento | 39780143, 39811261–39811334 | Sugiere selección de un target para cada lector; no prueba varios lectores simultáneos. |
| `_generation_identity`, `_session_hero_name`, `_stamp_game_generation` | 39777849, 39784008, 39811137 | Indicios de invalidación al cambiar partida/jugador; el flujo nativo exacto no fue recuperado. |
| Comprobación de foco de juego/chat para Q/Ctrl | 39901452, 40031233 | El recurso documenta evitar atajos globales indiscriminados. No prueba su ejecución correcta en varias ventanas. |

No está verificado que DragonboundGPT calcule varias cuentas a la vez. Cambiar entre cuentas y procesar varias sesiones simultáneamente son pruebas distintas. No se deduce una capacidad completa a partir de nombres de funciones o de la interfaz.

## Corrección propia en DragonLab 0.21.1

La causa comprobada de pérdida de guía era que el lector rechazaba más de una página del mismo juego sin una selección explícita, y ocultaba ese error con un aviso genérico. Ahora resuelve la pestaña por presencia de partida, foco y visibilidad, conserva la anterior si ambas quedan en segundo plano y vuelve a descubrirla al cerrarse. Una selección explícita permanece fijada.

El modo manual mantiene una guía y un cálculo activos: sigue la pestaña elegida dentro del navegador CDP conectado. Puede volver a descubrir el juego tras un cambio de cuenta en la misma página. Cada lectura y solicitud de Q incluye la identidad de pestaña y partida; los datos previos se invalidan al cambiar. No se anuncia que este parche mantenga ocho cuentas o lectores manuales simultáneos, ni que siga automáticamente otros puertos/perfiles de Chrome. El entrenador de sesiones múltiples sigue separado y experimental.

## Validación

- 876 pruebas Python aprobadas, incluidas geometría recortada, ciclo de sesión, identidad de entrada, perfiles y reconexión.
- Nueve escenarios de navegador aprobados: Q, atajo personalizado, chat/modificadores, clima, entrada aislada en segundo plano, Drag, movimiento, ciclo de sesión y selección de pestañas.
- La prueba nueva abre un Chrome aislado sin las modificaciones de foco de Playwright: dos páginas del mismo host, única partida frente a sala, cambio a otra partida y recuperación al cerrar esa pestaña. No toca las cuentas del usuario.
- El escenario de sesión existente comprueba SPA, recarga, reutilización de ID de jugador y 32 actores, con lector independiente. Esto no sustituye una prueba de cambios de cuenta en un servidor real.
- En el navegador real se observaron dos pestañas de DragonBound y se pudo conectar sin la antigua excepción. Durante la comprobación estaban fuera de partida; la aparición real de la marca de fuerza en esta nueva ejecución queda pendiente de una partida visible. No se declara recuperada por una prueba visual simulada.

Los JSON completos de análisis, sus extractos y los registros de ejecución quedan en `work/`; no se distribuye código extraído del otro programa.
