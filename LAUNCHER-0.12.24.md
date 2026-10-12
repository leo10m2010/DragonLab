# DragonLab 0.12.24

Extrae DragonLab-Prueba-0.12.24.zip y abre DragonLab-Prueba.exe. La prueba inicia sesión automáticamente. Elige el juego y pulsa Jugar. La captura, la guía y los atajos forman parte del mismo programa; Chrome o Edge son necesarios.

## Climas y recorrido de GunBound World

Las columnas se decodifican desde el texto JSON transmitido por el juego, conservando posiciones y tamaños. Mirror refleja una vez; Tornado entra, gira dos veces y sale. La línea marca esos contactos. Fuerza, Rayo y Negro muestran su cruce sin inventar una desviación de la bala. Thor y los climas globales muestran su nombre; sus daños adicionales no se predicen como otra trayectoria balística.

Se corrigieron los pasos observados: tramo balístico de 50 ms, detección de contactos de 1/60 s y recorrido dentro de Tornado de 1/30 s. Al tocar un borde se conserva la velocidad y se descarta la fracción restante de ese paso. La comparación de un tiro real por clima reprodujo 55 puntos regulares de Tornado y 75 de Mirror usando sus condiciones iniciales medidas. Esto valida esos tiempos de interacción, no la precisión total de puntería ni los impactos con el terreno. Faltan más casos, dirección opuesta y columnas móviles.

Los tiros se clasifican como sin cruce, cruce parcial o cruce completo. Los puntos de impacto intercalados no certifican un rebote. Aleatorio utiliza su variante únicamente cuando el juego la revela; antes se señala como sin revelar, y Q avisa si el recorrido atraviesa esa zona desconocida.

La captura conserva hasta doce trayectorias propias con clima y muestra temporalmente la trayectoria real en azul. Los datos locales no se envían al servidor en la prueba.

## Armor y Q

Armor conserva perfiles propios de salida: tiro 1 medido con 8 tiros (viento 0–18); tiro 2 con 4 de ajuste y 3 de comprobación independiente (0–22); SS con 6 de ajuste y 3 de comprobación independiente (2–24). Fuerzas observadas 25–100. Otros vehículos requieren datos propios, registrados automáticamente al jugar.

Q fue comprobada en una partida real: fuerza solicitada 9, liberación confirmada 9 y una pulsación, sin reintento. La tecla elegida se escucha en la pestaña, acepta solo pulsaciones reales sin repetición, chat ni modificadores, y se deduplica con la captura. La carga usa controles de Windows y confirma una liberación nueva. Los avisos aparecen sobre la barra y en el launcher. Esc, pérdida de foco o movimiento del mouse cancelan la carga; puede salir un tiro parcial si ya empezó.

Los perfiles por clon y el recorrido existente de DragonBound se conservan separados del modelo de GunBound World. Las pruebas de regresión no sustituyen una partida real de DragonBound.

## Publicación

El ZIP de prueba incluye un único ejecutable y este documento, sin mediciones personales. La producción requiere configurar Supabase y el panel HTTPS siguiendo cloud/GUIA-ACTIVACION.md. La Release genera DragonLab-Launcher.zip, DragonLab-Cloud.exe y dragonlab-release.json; las compilaciones de producción desactivan el acceso de prueba.

DragonLab usa ventanas superpuestas y lee el navegador mediante CDP. Ejecuta scripts de lectura, escuchadores y observadores temporales de eventos; no modifica archivos del juego.
