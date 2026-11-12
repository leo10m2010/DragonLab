# DragonLab 0.19.0 · Manual con motor y guía nativos

## Usar

Abre `DragonLab-Manual.exe` y pulsa **Abrir juego**. Se conservan la interfaz Matrix, las posiciones, los perfiles y los atajos personalizados. Ctrl cambia el objetivo y Q sigue aplicando un único tiro con las verificaciones actuales del juego. No se activa entrenamiento al abrir Manual.

`DragonLab-Automatico.exe` conserva el entrenador experimental separado. Usa un modo a la vez. La migración no modifica las cuentas, licencias, consentimiento, perfiles ni el protocolo del servidor.

## Qué utiliza Rust

El cálculo manual usa una DLL Rust para los modelos de un proyectil portados: geometría de salida, viento, búsqueda de fuerza, colisión con terreno, Mirror/Tornado y límites aprendidos. La llamada libera el intérprete Python durante el trabajo nativo. Al cambiar las condiciones, una señal atómica cancela el cálculo; no se crea un hilo de sondeo por tiro.

Los comportamientos todavía no portados usan automáticamente el motor Python existente: Nak, Kalsiddon, Bigfoot, Dragon, Camaleón/Randomizer; las variantes especiales del tiro 2 de Grub, Mage, Turtle, Trico y Boomer; proyectiles personalizados y GunBound World. Esto conserva su funcionamiento anterior y no los declara calibrados. La elección no mezcla parámetros entre vehículos.

La guía sobre el juego usa Rust/Win32: una ventana transparente que no recibe foco ni clics, con un hilo de mensajes que espera trabajo. Conserva una sola escena pendiente, reutiliza su bitmap y evita repintar escenas idénticas. Dibuja trayectorias continuas, enemigos fuera de vista, avisos de clima y la marca de fuerza. Si un componente nativo no está disponible o falla, se activa el dibujo compatible. `DRAGONLAB_DISABLE_RUST=1` permite desactivarlos para diagnóstico; no hace falta configurarlo para jugar.

La interfaz del launcher y los modelos pendientes **todavía utilizan Python**. Esta es una migración funcional por componentes, no un cliente completamente reescrito en Rust. El navegador y la frecuencia de lectura siguen formando parte del tiempo total.

## Mediciones locales

Comparación de medianas de 15 ejecuciones por caso, tras calentamiento, contra el motor Python de referencia en la misma PC. El tiempo Rust incluye serialización JSON y la llamada de ida y vuelta; no incluye lectura del navegador ni representa FPS del juego.

| Caso | Python | Rust integrado |
|---|---:|---:|
| Normal | 2,787 ms | 0,396 ms |
| Tiro alto | 6,967 ms | 0,821 ms |
| Terreno bloqueado | 5,185 ms | 0,220 ms |
| Varios jugadores | 2,820 ms | 0,419 ms |
| Mirror | 40,455 ms | 0,981 ms |
| Tornado | 51,210 ms | 1,441 ms |

El ejecutable local pasó de 20.955.384 a aproximadamente 17.000.000 bytes (19 % menos). Además de incorporar Rust, se excluyó el códec AVIF que no ofrece el selector de archivos. PNG, JPEG y BMP se comprueban dentro del ejecutable empaquetado. No se atribuye toda la reducción a Rust ni se garantiza el mismo ahorro en builds futuros.

## Comprobaciones

- 762 pruebas de Python, con una matriz persistente de 120 casos de paridad nativa y los seis casos completos de referencia. Se comparan fuerza, contactos, estados, cada campo y cada vértice, con tolerancia numérica de 1e-7 absoluta / 1e-10 relativa.
- 14 pruebas de Rust, incluyendo cancelación durante búsqueda, redondeo, límites y manejo de recursos gráficos. Clippy pasa sin advertencias en ambos componentes.
- El ejecutable empaquetado carga las dos DLL, calcula la fuerza de referencia 205 y abre PNG/JPEG/BMP sin AVIF.
- La escena gráfica de QA se renderizó en un bitmap privado, sin capturar el escritorio. Las pruebas verifican que la ventana no roba foco y libera los recursos GDI. Falta contrastar la alineación en una partida real nueva; no se presenta esta QA como una prueba de precisión de todos los carros.

Los fuentes, locks, specs y pasos reproducibles están en `native/README.md`. Los paquetes para distribuir son `DragonLab-Manual-0.19.0.zip` y, por separado, `DragonLab-Automatico-0.19.0.zip`.
