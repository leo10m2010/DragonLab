# DragonLab 0.12.22

Extrae DragonLab-Prueba-0.12.22.zip y abre DragonLab-Prueba.exe. La prueba inicia sesión automáticamente. Elige el juego y pulsa Jugar; el motor y la guía forman parte del mismo programa. Chrome o Edge son necesarios.

## Armor en GunBound World

Los tres modos tienen perfiles propios de salida medidos: tiro 1 con 8 tiros (viento 0–18); tiro 2 con 4 tiros de ajuste y 3 de comprobación independiente (viento 0–22); SS con 6 tiros de ajuste y 3 de comprobación independiente (viento 2–24). Fuerzas observadas 25–100. SS se identifica por el disparo enviado, aunque el juego vuelva después al tiro normal. El rango comprobado incluye las mediciones independientes aprobadas.

La guía muestra salida medida dentro del rango de viento comprobado. Fuera de él solicita ampliar mediciones. Estos perfiles calibran la salida del proyectil principal; no certifican los choques, efectos especiales ni todos los climas. Ice y otros carros siguen pendientes de datos propios.

## Captura y aprendizaje

Tus disparos manuales se registran automáticamente por carro y modalidad. Se conservan entre partidas y al cerrar; SS respeta su recarga. Las trayectorias iniciales alteradas, demasiado cortas o con ítems se descartan. Un ajuste nuevo necesita fuerzas variadas y tres tiros futuros independientes antes de activarse. Un observador temporal de callbacks conserva los originales y se retira al detener captura; no dispara ni registra datos de cuenta.

La guía detecta el nombre del clima y las columnas de Mirror, Tornado, Fuerza, Rayo y Negro. Los jugadores mantienen marcadores detrás del terreno o fuera de vista. Q usa controles de Windows y requiere turno, foco y datos vigentes; no reintenta. Esc, pérdida de foco o movimiento del mouse cancelan la carga, aunque puede salir un tiro parcial si ya empezó. El tiro real mediante Q sigue pendiente de contraste.

## Producción

El ZIP de prueba contiene un único ejecutable y este documento, sin mediciones personales. No envía mediciones al servidor. La publicación con licencia requiere configurar Supabase y el panel HTTPS siguiendo cloud/GUIA-ACTIVACION.md. La Release genera DragonLab-Launcher.zip, DragonLab-Cloud.exe y dragonlab-release.json; el acceso de prueba se desactiva en producción.

DragonLab usa ventanas superpuestas y lee el navegador mediante CDP. Ejecuta scripts de lectura y observación; DragonBound también utiliza escuchadores de atajos. No modifica archivos del juego.

## Climas y Q

GunBound World tiene un recorrido de columnas separado del motor DragonBound: Mirror produce una reflexión; Tornado muestra entrada, dos giros y salida. Se eliminan las cuantizaciones y el retroceso propios del modelo DragonBound para este clon. Fuerza, Rayo y Negro reciben señales de cruce sin inventar una desviación balística. Las columnas móviles y los tiempos de interacción con el servidor siguen pendientes de contraste; el recorrido se presenta como aproximado. La captura conserva localmente hasta doce trayectorias propias con clima para comprobarlo y muestra temporalmente la trayectoria real en azul.

Q se recibe también desde un escuchador de la tecla elegida en la pestaña del juego; solo acepta pulsaciones reales, sin repetición, chat ni modificadores. Se deduplica entre la conexión de eventos y la captura. No modifica eventos ni llama funciones de disparo del juego. La carga utiliza controles nativos de Windows. Los avisos aparecen encima de la barra y en el launcher. Se admiten fuerzas válidas desde 1, y se comprueba una liberación nueva con su fuerza real; una fuerza anterior coincidente no confirma otro tiro. No hay reintentos automáticos. Falta validar el disparo mediante Q en una partida real del usuario.

Los perfiles por clon y el recorrido existente de DragonBound se conservan. Las pruebas locales no sustituyen la comprobación en partidas reales de ambos juegos.
