# DragonLab 0.9

Abre **DragonLab-0.9.exe**. Si necesitas el navegador conectado, pulsa **Abrir juego**. Al entrar en una partida aparecen la guía de fuerza, las trayectorias y los enemigos numerados sobre el juego. Puedes minimizar DragonLab.

- **Ctrl**, pulsar y soltar: siguiente enemigo vivo. F8 conserva su función del juego.
- **Q**: ejecuta un tiro con la fuerza recomendada. Requiere una solución válida, tu turno y la ventana del juego en primer plano. Detecta Slice o Drag y mide la carga real. Cada pulsación solicita un solo tiro; no ajusta automáticamente tu ángulo.
- **Ajustes**: cambia ambas teclas, activa o desactiva las marcas y el tiro por atajo, y elige rendimiento Ligero o Normal. Se excluyen teclas reservadas por el juego.
- **Ver mapa**: abre la vista adicional. Oculta el mapa para reducir la carga de capturas.

La captura, las posiciones, el vehículo, el tipo de tiro, el viento y la calibración se leen automáticamente. Las mediciones se guardan en calibraciones.json. Las herramientas manuales y los detalles técnicos están en una ventana secundaria.

Nak tiro 2 incluye el recorrido bajo tierra y calcula el impacto al volver a la superficie. Se corrigió el límite de simulación para mapas profundos y jugadores en posiciones bajas. Nak tiro 2 cuenta con siete mediciones de lanzamiento y cinco pares observados de entrada/salida; Nak tiro 1 tiene una medición. Nak SS y los vehículos sin suficientes datos mantienen aproximaciones pendientes de comprobación real. GunBound World continúa pendiente de validación.

El modo Ligero viene seleccionado. Evita capturar imágenes cuando la vista está oculta y espacia la lectura del terreno, manteniendo una actualización al cambiar el turno. El ejecutable incluye su entorno para funcionar sin instalar Python; pesa aproximadamente 19 MB. El rendimiento en un PC antiguo requiere una prueba en ese equipo.

El tiro por atajo se verificó con entradas simuladas en Slice y Drag. Queda pendiente comprobar su precisión completa dentro de una partida real. Al soltar Space o el ratón, el juego dispara la fuerza acumulada; si se interrumpe una carga, liberar la entrada puede disparar esa fuerza parcial.
