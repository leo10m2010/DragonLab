# DragonLab 0.17.2 · Guías guardadas del entrenamiento

Cada tiro propio confirmado del entrenador guarda una guía numérica local: carro y bala, fuerza y ángulo, viento, columnas del clima, posiciones del cálculo, modelo previo y recorrido observado. El resultado de vida y el resultado de partida se añaden cuando el juego permite confirmarlos. El panel de aprendizaje muestra cuántas guías se guardaron durante la ejecución.

Las guías permiten revisar errores y conservar mediciones que alimentan la biblioteca manual. Se guardan por cuenta en `guias-entrenamiento.sqlite3`. La biblioteca vuelve a comprobar sus datos nativos por partida; archivar un tiro no lo convierte en calibración válida.

La predicción conserva el modelo preparado antes de disparar. El recorrido real se reconstruye aparte desde datos nativos. Si no existía una predicción guardada, se indica que falta. Las continuaciones solo se añaden si se pudo comprobar su procedencia. Las partidas y ventanas de daño desconocidas permanecen desconocidas.

El archivo conserva hasta 16 guías por modalidad y 816 en total, con trayectorias resumidas y un límite de almacenamiento de aproximadamente 48 MiB por cuenta. No guarda capturas, nombres, chats ni contraseñas. Un fallo del archivo se informa sin repetir el disparo ni detener por sí solo el control.

La grabación se activa al iniciar el entrenamiento. Abrir `DragonLab-Prueba.exe` mantiene el uso manual; `Entrenar-2-Sesiones.cmd` inicia el entrenamiento de las dos cuentas. Las calibraciones y guías manuales de 0.17.1 se conservan.

Paquete: `DragonLab-Prueba-0.17.2.zip`. Launcher: `DragonLab-Launcher-0.17.2.zip`. Código: `DragonLabCloud-Preparacion.zip`.
