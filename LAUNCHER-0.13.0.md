# DragonLab 0.13.0

La prueba inicia sesión automáticamente. Elige DragonBound y pulsa Jugar. En Ajustes → Entrenamiento automático puedes iniciar una sesión de 12, 30, 60 o 120 tiros. Deja el juego en primer plano, en el servidor 8 Avatar Off. Esc o Detener finalizan la sesión; pausar la guía, cerrar sesión o cerrar el programa también detienen el entrenador. Si cancelas mientras carga, el juego puede liberar un tiro parcial.

El entrenador elige carros disponibles, busca partidas 1v1, espera su turno y prueba fuerzas, ángulos y modalidades 1/2/SS. Lee la barra durante la carga y exige una salida propia nueva antes de registrar el tiro. SS se utiliza cuando está disponible; si no está cargado, prueba otra modalidad. Cada sesión tiene un límite adicional de 10 búsquedas y 30 minutos. Perder el foco o abrir el chat detiene la sesión y requiere volver a empezarla. No se inicia solo al abrir el programa.

Usa un planificador ligero y ajustes numéricos locales, sin descargar un modelo grande ni consumir una API de IA. Las mediciones se conservan entre partidas y la comprobación de los ajustes requiere tiros nuevos. Los grupos de proyectiles se guardan separados del ajuste de bala única. Los mecanismos especiales de Nak, Trico y Kalsiddon, así como todos los climas y rangos de viento, no se consideran completos solo por ejecutar el entrenador. El servidor 8 anuncia viento máximo 26: esta sesión no certifica vientos superiores.

Verificación real inicial: elección automática de Armor y búsqueda 1v1 confirmadas. Se observaron tiros propios de Armor 1 a fuerza 99 y Armor 2 a fuerza 299. La pérdida de foco detuvo la sesión. Una segunda sesión terminó por su límite de tres tiros, con fuerzas 99 (SS), 99 (tiro 2) y 359 (tiro 1), sin error. Estos datos comprueban el flujo de entrada y registro; no certifican todos los carros ni la precisión total de puntería. Consulta ENTRENAMIENTO.md para conocer el alcance de la validación.

GunBound World conserva sus perfiles y su recorrido separados de DragonBound. Este entrenador está habilitado solamente para DragonBound Avatar Off. Se conservan los ajustes anteriores de Q y los climas GunBound de la 0.12.24.

La prueba local no envía mediciones al servidor. El ejecutable se entrega sin mediciones personales. Para producción configura Supabase y el panel HTTPS según cloud/GUIA-ACTIVACION.md; GitHub Releases genera los archivos de actualización y desactiva el acceso de prueba.

DragonLab lee el estado del navegador mediante CDP y usa ventanas superpuestas. El entrenador utiliza eventos normales de teclado y mouse del navegador y escuchadores temporales para detenerse con Esc; no llama a métodos del juego para imponer fuerzas, alterar viento o fabricar tiros.
