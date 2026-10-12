# DragonLab 0.12.20

Extrae DragonLab-Prueba-0.12.20.zip y abre DragonLab-Prueba.exe. La prueba inicia sesión automáticamente y conserva una sola pantalla: elige el juego y pulsa Jugar. Chrome o Edge son necesarios.

## Correcciones

GunBound World guarda el clima activo y las columnas por separado. Ahora se leen ambos: la guía muestra el nombre del clima y marca las posiciones de Mirror, Tornado, Fuerza, Rayo y Negro. Se normalizan los nombres del juego y las zonas de Mirror/Tornado llegan al cálculo de trayectorias. Los climas globales no reciben posiciones inventadas. Las zonas se actualizan con los datos de cada captura; desaparecen cuando el juego las elimina.

Los avisos de Q aparecen en la pantalla principal, incluyendo rechazo por falta de turno, foco o fuerza válida. Q utiliza controles de Windows, requiere turno propio y no reintenta tiros. Esc, pérdida de foco o movimiento del mouse cancelan la carga; si ya empezó, puede salir un tiro parcial. La validación real de Q sigue pendiente del usuario.

Armor tiro 1 de GunBound World conserva su salida medida con 8 tiros, fuerza 25–100 y viento 0–18. Armor tiro 2 también dispone de salida medida; SS, Ice y los otros vehículos siguen pendientes de mediciones propias. Detectar un clima no certifica la precisión de sus efectos: las interacciones y zonas móviles requieren contraste con tiros reales.

## Publicación

La prueba incluye un ejecutable y este documento; no contiene mediciones personales. Para producción usa la Release de GitHub: DragonLab-Launcher.zip, DragonLab-Cloud.exe y dragonlab-release.json, generados por el flujo de publicación. La licencia y el servidor requieren configurar Supabase y el panel HTTPS siguiendo cloud/GUIA-ACTIVACION.md. El acceso de prueba se desactiva en compilaciones de producción.

DragonLab es un programa separado con ventanas superpuestas. Lee el navegador mediante CDP y ejecuta scripts de lectura; DragonBound también instala escuchadores de atajos. No modifica archivos del juego. La prueba no envía mediciones al servidor.

## Aprendizaje automático 0.12.20

El programa registra automáticamente las trayectorias de tus tiros manuales en GunBound World, separadas por carro y tiro 1/2/SS. Conserva las mediciones entre partidas y al cerrar. Un observador temporal de eventos conserva los callbacks originales y se retira al detener captura; no dispara ni envía datos de cuenta. No recoge tiros de bots ni tiros con ítems.

Se mide la salida del proyectil principal a partir de los primeros puntos regulares de 50 ms; trayectorias cortas, alteradas o no balísticas se descartan. Los proyectiles hijos y efectos especiales no quedan calibrados con esa sola medición. El ajuste exige al menos cuatro tiros, tres fuerzas distintas y una amplitud de 40 puntos; luego necesita tres tiros nuevos, dos fuerzas distintas y amplitud de 40 para validarse. Usa aproximadamente un cuarto, mitad, tres cuartos y casi toda la barra, sin necesidad de acertar al enemigo. SS se registra cuando esté disponible, respetando su recarga.

La pantalla distingue modalidad sin datos, comprobación y viento fuera del rango medido. Un perfil se activa únicamente después de validarse; no se inventan perfiles para llenar los tiros pendientes. Las calibraciones de todos los carros y sus mecanismos especiales necesitan tiros reales. La prueba guarda datos localmente sin enviarlos al servidor.

## Armor 2 medido

Armor tiro 2 incluye salida medida con cuatro tiros de ajuste y tres de comprobación independiente. Fuerzas 25–100, viento comprobado 0–22. Se corrigió el rango para incluir los tiros de validación aprobados. SS y los demás vehículos todavía necesitan mediciones propias. Esto calibra la salida, no certifica todos los choques o mecanismos especiales.
