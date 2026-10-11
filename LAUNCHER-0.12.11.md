# DragonLab Launcher 0.12.11

Una acción principal: **Jugar DragonBound**. Prepara el auxiliar minimizado, abre el navegador gestionado y conecta la captura. El launcher se oculta mientras el auxiliar está abierto y regresa cuando se cierra. El auxiliar queda accesible en la barra de tareas para ajustes o salida. Cerrar el navegador por sí solo no detiene el auxiliar.

El marco nativo blanco se sustituye por controles propios de minimizar y cerrar; la cabecera permite arrastrar la ventana. Fondo azul oscuro, acento cian, paneles y controles redondeados. La ayuda integrada explica el flujo y los atajos iniciales sin pedir iniciar dos veces.

Protecciones: clics repetidos no crean más procesos; cada distribución del auxiliar permite una sola instancia; reabrir el launcher restaura la instancia existente. Se reutiliza la pestaña de DragonBound del navegador gestionado. Si falla el arranque, se permite reintentar. La sesión guardada se verifica antes de mostrar el panel y los accesos vencidos bloquean el juego.

## Prueba local

Extrae `DragonLab-Prueba-0.12.11.zip` y abre `Iniciar-Prueba.cmd`. La prueba entra automáticamente y utiliza el auxiliar local 0.12.8. No inicia sesión en Supabase, concede licencias Cloud, descarga actualizaciones ni envía mediciones. El ZIP incluye perfiles básicos; no contiene tus mediciones personales. Chrome o Edge son necesarios para el juego. Cierra versiones anteriores del auxiliar antes de probar el nuevo flujo.

## Qué publicar para los usuarios con licencia

El trabajo **Publish Cloud release** genera juntos:

- `DragonLab-Launcher.zip`: launcher y configuración pública real.
- `DragonLab-Cloud.exe`: auxiliar que verifica el acceso en el servidor.
- `dragonlab-release.json`: versión, enlace y SHA-256 necesarios para actualizar.

Antes configura Supabase y la URL HTTPS del panel siguiendo `cloud/GUIA-ACTIVACION.md`. No añadas claves privadas. No reutilices una versión para archivos diferentes.

`DragonLab-Launcher-0.12.11.zip` es de preparación y contiene solo un ejemplo de configuración; no es la distribución de producción. `DragonLabCloud-Preparacion.zip` contiene el proyecto para preparar el servidor. La prueba local no sustituye el sistema de licencias.

Validación: pruebas de launcher, entrada, aprendizaje, ventanas, exclusión de instancias y reutilización de pestañas; revisión visual de login, panel y ayuda; arranque de ejecutables con `--check`, sin abrir el juego ni disparar. La conexión real con Supabase sigue pendiente de configuración. El flujo nuevo de apertura del juego requiere comprobarse en la PC del usuario.
