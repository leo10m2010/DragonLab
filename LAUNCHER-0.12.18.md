# DragonLab 0.12.18

Extrae DragonLab-Prueba-0.12.18.zip y abre DragonLab-Prueba.exe. La prueba inicia sesión automáticamente y conserva una sola pantalla: elige el juego y pulsa Jugar. Chrome o Edge son necesarios.

## Correcciones

GunBound World guarda el clima activo y las columnas por separado. Ahora se leen ambos: la guía muestra el nombre del clima y marca las posiciones de Mirror, Tornado, Fuerza, Rayo y Negro. Se normalizan los nombres del juego y las zonas de Mirror/Tornado llegan al cálculo de trayectorias. Los climas globales no reciben posiciones inventadas. Las zonas se actualizan con los datos de cada captura; desaparecen cuando el juego las elimina.

Los avisos de Q aparecen en la pantalla principal, incluyendo rechazo por falta de turno, foco o fuerza válida. Q utiliza controles de Windows, requiere turno propio y no reintenta tiros. Esc, pérdida de foco o movimiento del mouse cancelan la carga; si ya empezó, puede salir un tiro parcial. La validación real de Q sigue pendiente del usuario.

Armor tiro 1 de GunBound World conserva su salida medida con 8 tiros, fuerza 25–100 y viento 0–18. Tiro 2, SS, Ice y los otros vehículos siguen pendientes de mediciones propias. Detectar un clima no certifica la precisión de sus efectos: las interacciones y zonas móviles requieren contraste con tiros reales.

## Publicación

La prueba incluye un ejecutable y este documento; no contiene mediciones personales. Para producción usa la Release de GitHub: DragonLab-Launcher.zip, DragonLab-Cloud.exe y dragonlab-release.json, generados por el flujo de publicación. La licencia y el servidor requieren configurar Supabase y el panel HTTPS siguiendo cloud/GUIA-ACTIVACION.md. El acceso de prueba se desactiva en compilaciones de producción.

DragonLab es un programa separado con ventanas superpuestas. Lee el navegador mediante CDP y ejecuta scripts de lectura; DragonBound también instala escuchadores de atajos. No modifica archivos del juego. La prueba no envía mediciones al servidor.
