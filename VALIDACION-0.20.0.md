# Validación de DragonLab 0.20.0

## Ejecutado

| Comprobación | Resultado |
|---|---|
| `python -B -m unittest discover -s tests -p 'test_*.py'` | 837 pruebas, sin fallos |
| Rust core `cargo test --offline` | 8 pruebas |
| Rust overlay `cargo test --offline`, formato y Clippy | 10 pruebas, sin advertencias de Clippy |
| `npm run test:browser --prefix tests` | 8 suites, correctas |
| Ejecutables Manual, Automático, Launcher y Cloud | `--check --engine-check`: salida 0 |
| Los cuatro ejecutables, `--native-check` | Ambas DLL cargan; fuerza 205; PNG/JPEG/BMP correctos |
| Archivo de preparación | 340 fuentes coinciden byte por byte |
| ZIP Manual y Automático | Coinciden con el ejecutable y el LEEME actuales |
| DLL incluidas en el ejecutable | SHA-256 coincide con el manifiesto 0.20.0 |
| Windows, ejecutable Manual real | Arrastre cambia posición 100×40 píxeles, conserva 722×782; maximizar y restaurar conservan estructura; tarjetas centradas con límite de ancho |

El ajuste final de liberación del identificador CDP del controlador también pasó las 3 pruebas de adaptador GunBound y las 10 de ciclo de sesión. No se realizaron disparos ni acciones de entrenamiento durante estas verificaciones.

Las suites de navegador usan páginas sintéticas aisladas. Comprueban atajos confiables, modificadores, chat, recarga, sesión anterior rechazada, viento y columnas, entrada independiente por pestaña, SS disponible, Drag, movimiento y cambio de cuenta/partida. La prueba de sesión incluye 32 jugadores detrás de 25 entradas de metadatos, Map, reutilización de ID 0, cambio de objeto, cierre, SPA, recarga y primer muestreo desde un segundo lector CDP. Los dibujos Rust/Tk se prueban con grupos numerosos y hasta 300 actores sintéticos. Esto acredita el procesamiento, no la precisión de tiros de todos los carros.

## Medición local del cálculo

Se repitió el mismo benchmark de seis casos, con 3 calentamientos y 15 repeticiones por función. Medianas en esta PC; Rust incluye serialización y llamada FFI:

| Caso | Python, ms | Rust, ms |
|---|---:|---:|
| Normal | 2.888 | 0.421 |
| Alto | 7.472 | 0.880 |
| Corto | 5.129 | 0.215 |
| Variante normal | 2.909 | 0.413 |
| Mirror | 41.229 | 1.013 |
| Tornado | 52.551 | 1.497 |

Este es un contraste entre motores en la versión actual. No demuestra una mejora nueva de 0.20 frente a 0.19, ni mide FPS, latencia completa de pantalla, puntería real o el consumo de Chrome. El ejecutable actual ocupa 17,116,770 bytes; añade catálogo, diagnósticos y controles sobre la versión anterior.

## Pendiente de contraste físico

- Relogin real, varios monitores con DPI diferentes y más de ocho jugadores en una partida real.
- Precisión de cada móvil/bala/viento y transformaciones especiales de Nak, Kalsiddon, Trico, Mirror y Tornado. No se declaran perfectos sin observaciones independientes.
- Carga prolongada y funcionamiento del modo automático durante 24 horas; permanece experimental y separado del manual.
- Activación de un servidor cloud real; no se crearon servicios ni se cambiaron credenciales.

Para comprobarlo, abre el Manual, elige el juego y pulsa Abrir juego. Cambia de cuenta en la misma pestaña y comprueba que desaparece la guía antigua antes de mostrarse la nueva; el catálogo y Rendimiento permiten ver cobertura y conteos. Prueba Q únicamente en tu turno con una fuerza vigente. Comprueba DPI moviendo la ventana entre tus monitores y restaurando su tamaño.
