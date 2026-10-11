# DragonLab 0.12.15 · una pantalla

El producto conserva una única pantalla principal: acceso real (o automático en la prueba), selector de juego y **Jugar**. Ajustes y ayuda son ventanas secundarias temporales; no hay otro panel de captura ni otro botón Abrir juego.

El motor de captura funciona dentro del mismo proceso y no muestra su interfaz técnica. Cerrar DragonLab o cerrar sesión detiene la captura, los atajos y la comprobación Cloud. Cambiar de juego detiene la conexión anterior y mantiene los perfiles separados por clon, vehículo y tiro. Los clics rápidos reutilizan el motor y no abren otra instancia.

## Juegos

- **DragonBound**: abre su navegador gestionado y activa la captura existente.
- **GunBound World**: abre `https://play.gunbound.world/`, utiliza su adaptador y reutiliza únicamente su pestaña. Compatibilidad experimental: se observaron posiciones, identidad, ángulo, viento y cámara en una partida real. Los tiros, terreno y climas necesitan validación y calibraciones propias. Q permanece desactivado para este juego. No se promete precisión equivalente a DragonBound.

## Prueba

Extrae `DragonLab-Prueba-0.12.15.zip` y abre `DragonLab-Prueba.exe`. El acceso de prueba es automático. Incluye un solo ejecutable, con el motor integrado. No requiere un ejecutable companion aparte. No contiene mediciones personales ni activa una licencia de producción. Chrome o Edge son necesarios. Cierra versiones antiguas antes de probar.

Los datos locales existentes se conservan al utilizar esta instalación; una extracción nueva utiliza su carpeta `datos`. La prueba no envía mediciones al servidor.

## Publicación con licencia

El flujo de GitHub genera `DragonLab-Launcher.zip`, `DragonLab-Cloud.exe` y `dragonlab-release.json`. El usuario descarga el ZIP del launcher; Cloud es el ejecutable completo de actualización, con la misma interfaz integrada. Antes de abrirlo se verifica su SHA-256 y la nueva instancia vuelve a verificar la cuenta. El traspaso cierra la instancia anterior. Mantener ambos assets en la Release no implica dos pantallas para el usuario.

Configura primero Supabase y el panel HTTPS siguiendo `cloud/GUIA-ACTIVACION.md`. El ZIP de preparación conserva solo una configuración de ejemplo. No contiene claves privadas. Las compilaciones de publicación desactivan el acceso de prueba, incluso si alguien cambia el nombre del archivo o utiliza --demo.

Validación local: pruebas de motor oculto, cierre de tareas, selección de URL, reutilización de pestañas, sesión, atajos y cálculos; revisión visual y arranque de los ejecutables sin abrir un juego ni disparar. La API Cloud de producción y la precisión de la guía de GunBound World siguen pendientes de comprobación.

Corrección 0.12.15: captura automática habilitada para GunBound World, lectura de su canvas y barra completa .pgauge, origen de contenido para Chrome con composición sin ventana hija visible. La opción interna --auto-game también inicia el motor en prueba. La guía se oculta fuera de partida y cuando el juego pierde el foco; Q de GunBound World sigue desactivado.

0.12.15: el botón y mensaje reflejan la captura, espera, cálculo, falta de calibración y guía realmente visible. Pulsar de nuevo pausa la guía. La superposición utiliza la ventana visible del producto. El lector libera el controlador al regresar a sala para localizar la siguiente partida. La versión extraída junto a DragonLab encuentra las mediciones locales existentes. Sin un perfil real de GunBound World, se muestra un aviso sobre la barra en lugar de una fuerza inventada; sus mediciones todavía están pendientes.

DragonLab es un programa separado: dibuja ventanas superpuestas y accede al navegador mediante CDP. DragonBound utiliza scripts de lectura y escuchadores de atajos. GunBound World utiliza evaluación de lectura; no instala el escuchador Q. No modifica archivos del juego. No se presenta como un programa sin ningún código ejecutado en el navegador.

0.12.15 incorpora Armor tiro 1 de GunBound World medido con 8 tiros propios, fuerzas 25–100 y viento 0–18. La velocidad por unidad de fuerza resultó 9.200075; no se aplica a otros vehículos ni a tiro 2/SS. Se corrigieron la convención de viento, inclinación y salida del cañón; el modelo utiliza el paso observado de 50 ms. Dos trayectorias reales reproducidas tuvieron errores máximos de 0.80 y 4.43 píxeles en puntos anteriores al impacto. Esto no valida choques, terreno ni otros climas. Q continúa desactivado. El perfil se incluye en el ejecutable; los datos locales válidos conservan prioridad. El lector descarta controladores destruidos y vistas de repetición para evitar datos congelados.
