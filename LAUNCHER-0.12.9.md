# Launcher 0.12.9

Primero se muestra únicamente el inicio de sesión. Tras verificar la cuenta aparece el panel de uso, con acceso, tiempo restante, programa y calibraciones. Cerrar sesión devuelve a la pantalla de entrada. La sesión guardada se verifica antes de mostrar el panel.

Launcher nativo oscuro, paneles y campos redondeados, licencia y tiempo restante separados del botón principal, consentimiento opcional y ayuda accesible. La pantalla muestra la versión del launcher, el programa realmente instalado y la revisión del conjunto de calibraciones descargado. La revisión es una huella del conjunto, no una promesa de calibración completa. Si no hay un conjunto descargado indica «Sin sincronizar».

La versión del programa se guarda después de descargar, verificar SHA-256 y abrir el ejecutable. No se presenta como «actualizado» antes de comprobar la Release. El trabajo de publicación estampa la versión elegida en el launcher y el cliente antes de compilar.

## Qué subir

Para una GitHub Release Cloud se publican juntos:

- `DragonLab-Launcher.zip`: descarga para tus usuarios; launcher y configuración pública real.
- `DragonLab-Cloud.exe`: cliente con comprobación de licencia que descarga el launcher.
- `dragonlab-release.json`: versión, enlace y SHA-256 del cliente; necesario para las actualizaciones.

El trabajo **Publish Cloud release** genera los tres archivos. Antes configura las variables públicas de Supabase y la URL HTTPS del panel siguiendo `cloud/GUIA-ACTIVACION.md`. Nunca añadas claves privadas al ZIP. No reutilices una versión para archivos distintos.

El archivo local `DragonLab-Launcher-0.12.9.zip` es de preparación: contiene el launcher, un ejemplo de configuración y estas instrucciones. Todavía no conecta a un servidor real. No es el ZIP final para entregar a clientes con licencia.

Los cambios de código están en la rama `codex/cloud-accounts`, PR #1. El paquete `DragonLabCloud-Preparacion.zip` conserva el proyecto completo para preparar el servidor; no es la descarga ligera de los clientes.

Validación local: 57 pruebas de entrada, aprendizaje, launcher y UI; 5 pruebas del backend; arranque del launcher y revisión visual. El login y las licencias reales requieren configurar el servidor.

