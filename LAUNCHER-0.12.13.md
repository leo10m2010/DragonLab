# DragonLab 0.12.13 · una pantalla

El producto conserva una única pantalla principal: acceso real (o automático en la prueba), selector de juego y **Jugar**. Ajustes y ayuda son ventanas secundarias temporales; no hay otro panel de captura ni otro botón Abrir juego.

El motor de captura funciona dentro del mismo proceso y no muestra su interfaz técnica. Cerrar DragonLab o cerrar sesión detiene la captura, los atajos y la comprobación Cloud. Cambiar de juego detiene la conexión anterior y mantiene los perfiles separados por clon, vehículo y tiro. Los clics rápidos reutilizan el motor y no abren otra instancia.

## Juegos

- **DragonBound**: abre su navegador gestionado y activa la captura existente.
- **GunBound World**: abre `https://play.gunbound.world/`, utiliza su adaptador y reutiliza únicamente su pestaña. Compatibilidad experimental: se observaron posiciones, identidad, ángulo, viento y cámara en una partida real. Los tiros, terreno y climas necesitan validación y calibraciones propias. Q permanece desactivado para este juego. No se promete precisión equivalente a DragonBound.

## Prueba

Extrae `DragonLab-Prueba-0.12.13.zip` y abre `DragonLab-Prueba.exe`. El acceso de prueba es automático. Incluye un solo ejecutable, con el motor integrado. No requiere un ejecutable companion aparte. No contiene mediciones personales ni activa una licencia de producción. Chrome o Edge son necesarios. Cierra versiones antiguas antes de probar.

Los datos locales existentes se conservan al utilizar esta instalación; una extracción nueva utiliza su carpeta `datos`. La prueba no envía mediciones al servidor.

## Publicación con licencia

El flujo de GitHub genera `DragonLab-Launcher.zip`, `DragonLab-Cloud.exe` y `dragonlab-release.json`. El usuario descarga el ZIP del launcher; Cloud es el ejecutable completo de actualización, con la misma interfaz integrada. Antes de abrirlo se verifica su SHA-256 y la nueva instancia vuelve a verificar la cuenta. El traspaso cierra la instancia anterior. Mantener ambos assets en la Release no implica dos pantallas para el usuario.

Configura primero Supabase y el panel HTTPS siguiendo `cloud/GUIA-ACTIVACION.md`. El ZIP de preparación conserva solo una configuración de ejemplo. No contiene claves privadas. Las compilaciones de publicación desactivan el acceso de prueba, incluso si alguien cambia el nombre del archivo o utiliza --demo.

Validación local: pruebas de motor oculto, cierre de tareas, selección de URL, reutilización de pestañas, sesión, atajos y cálculos; revisión visual y arranque de los ejecutables sin abrir un juego ni disparar. La API Cloud de producción y la precisión de la guía de GunBound World siguen pendientes de comprobación.

Corrección 0.12.13: captura automática habilitada para GunBound World, lectura de su canvas y barra completa .pgauge, origen de contenido para Chrome con composición sin ventana hija visible. La opción interna --auto-game también inicia el motor en prueba. La guía se oculta fuera de partida y cuando el juego pierde el foco; Q de GunBound World sigue desactivado.
