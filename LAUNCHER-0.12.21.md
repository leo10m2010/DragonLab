# DragonLab 0.12.21

Extrae DragonLab-Prueba-0.12.21.zip y abre DragonLab-Prueba.exe. La prueba inicia sesión automáticamente. Elige el juego y pulsa Jugar; el motor y la guía forman parte del mismo programa. Chrome o Edge son necesarios.

## Armor en GunBound World

Los tres modos tienen perfiles propios de salida medidos: tiro 1 con 8 tiros (viento 0–18); tiro 2 con 4 tiros de ajuste y 3 de comprobación independiente (viento 0–22); SS con 6 tiros de ajuste y 3 de comprobación independiente (viento 2–24). Fuerzas observadas 25–100. SS se identifica por el disparo enviado, aunque el juego vuelva después al tiro normal. El rango comprobado incluye las mediciones independientes aprobadas.

La guía muestra salida medida dentro del rango de viento comprobado. Fuera de él solicita ampliar mediciones. Estos perfiles calibran la salida del proyectil principal; no certifican los choques, efectos especiales ni todos los climas. Ice y otros carros siguen pendientes de datos propios.

## Captura y aprendizaje

Tus disparos manuales se registran automáticamente por carro y modalidad. Se conservan entre partidas y al cerrar; SS respeta su recarga. Las trayectorias iniciales alteradas, demasiado cortas o con ítems se descartan. Un ajuste nuevo necesita fuerzas variadas y tres tiros futuros independientes antes de activarse. Un observador temporal de callbacks conserva los originales y se retira al detener captura; no dispara ni registra datos de cuenta.

La guía detecta el nombre del clima y las columnas de Mirror, Tornado, Fuerza, Rayo y Negro. Los jugadores mantienen marcadores detrás del terreno o fuera de vista. Q usa controles de Windows y requiere turno, foco y datos vigentes; no reintenta. Esc, pérdida de foco o movimiento del mouse cancelan la carga, aunque puede salir un tiro parcial si ya empezó. El tiro real mediante Q sigue pendiente de contraste.

## Producción

El ZIP de prueba contiene un único ejecutable y este documento, sin mediciones personales. No envía mediciones al servidor. La publicación con licencia requiere configurar Supabase y el panel HTTPS siguiendo cloud/GUIA-ACTIVACION.md. La Release genera DragonLab-Launcher.zip, DragonLab-Cloud.exe y dragonlab-release.json; el acceso de prueba se desactiva en producción.

DragonLab usa ventanas superpuestas y lee el navegador mediante CDP. Ejecuta scripts de lectura y observación; DragonBound también utiliza escuchadores de atajos. No modifica archivos del juego.
