# DragonLab 0.12

Abre DragonLab-0.12.exe. La detección, la lectura del mapa y los perfiles por vehículo/tiro se actualizan automáticamente. Ctrl cambia al siguiente enemigo vivo; Q solicita un solo tiro con la fuerza recomendada. Los atajos se pueden cambiar en Ajustes. El juego debe estar en primer plano y debe ser tu turno; F8 conserva su función del juego.

## Interfaz

Selectores en cápsulas con menús redondeados, interruptores, campos, pestañas, listas, tarjetas, botones y barra de fuerza redondeados. Tab recorre los controles; Enter/Espacio abre o activa; las flechas cambian la opción de un menú y Escape lo cierra. Si los enemigos cambian mientras un menú está abierto, se cierra para evitar elegir una posición antigua. Ajustes se adapta a la altura de pantalla y conserva los botones de guardar fuera de la zona desplazable. Compacto, texto grande, color y grosor se mantienen. No se añaden animaciones ni capturas al abrir un selector.

## Precisión

El viento se ajusta conjuntamente en los ejes horizontal y vertical. Gravedad y respuesta a un viento vertical constante no se pueden separar sin variar las condiciones: ese caso permanece provisional. Cada ajuste exige fuerzas distintas y validación dejando fuera cada muestra; se comprueban velocidad y aceleración. Si las mediciones pertenecen a regímenes distintos, se puede archivar un bloque histórico solo después de seis tiros recientes consecutivos que pasen esa validación. Los registros anteriores se conservan en calibraciones.json.

Nak mantiene entrada/salida bajo tierra a 25 ms, aceleración subterránea medida y refresco tras cráteres. Los datos recientes permiten ajustar los lanzamientos de tiro 1 y tiro 2 sin viento. Kalsiddon conserva la apertura estimada de 2/4 misiles y SS de 4 a 8; el lanzamiento del tiro 2 tiene un ajuste reciente sin viento. Las ramas son una estimación visual a partir de tiros registrados; no garantizan impacto. El informe CALIBRACION-0.12.json indica el alcance real de las mediciones.

La calibración general de todos los carros queda para la siguiente sesión. Faltan pruebas completas de viento, SS, persecución, clima y contacto con jugadores/terreno. Un lanzamiento calibrado no garantiza un impacto perfecto. No se disparó por el usuario durante las pruebas de esta versión.
