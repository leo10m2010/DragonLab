# DragonLab 0.20.0

El modo Manual es la entrada principal. Abre `DragonLab-Manual.exe`; la prueba local entra sin correo. El launcher con servidor mantiene el inicio de sesión y comprueba el acceso antes de abrir el juego. El modo Automático conserva su ejecutable independiente y sigue siendo experimental; esta versión no acredita autonomía ni calibración completa.

## Cambios integrados

- Ventana nativa oscura de Windows: arrastre, bordes de tamaño, minimizar, maximizar, restaurar y Snap. Se eliminó la modificación de estilos detrás de Tk que desajustaba el área cliente. DPI se inicializa antes de crear ventanas y los ejecutables incluyen manifiesto PerMonitorV2. El contenido tiene ancho máximo y desplazamiento en ventanas pequeñas.
- Nueva interfaz de tarjetas neutras, acento lima, mascota vectorial ligera con cuatro estados, versión visible, selector de juego, una sola acción principal y accesos Atajos, Cómo usarlo, Rendimiento y Soporte. Cuenta y actualizaciones se despliegan bajo demanda.
- Ciclo de sesión: identidad opaca compartida entre lectores, invalidación por cambio de documento, ruta, partida o jugador. Se cancelan entradas pendientes, cálculos y posiciones antiguas, incluso al reutilizar el ID del jugador. Q verifica la misma identidad antes y durante la carga; los eventos antiguos no se reasignan a una cuenta nueva.
- Roster dinámico: arrays, objetos y Map; sin recortar las primeras 16 entradas. Se ignoran getters, metadatos y posiciones inválidas. Los IDs duplicados quedan descartados y diagnosticados. El dibujo distingue TÚ, aliados, enemigos y equipo desconocido; separa etiquetas y agrupa excedentes conservando todos sus miembros. No se mezclan sesiones.
- Overlay Rust actualizado en una sola presentación por fotograma, con geometría persistente y texto compacto de fuerza. La falta momentánea de geometría suspende el dibujo y bloquea Q hasta confirmarla; no se utiliza una barra obsoleta. Se conservan las trayectorias continuas.
- Registro modular de juegos y catálogo versionado: DragonBound y GunBound World tienen espacios de física separados, incluidos parámetros por bala 1/2/SS. iGunsFire, ShotBound y WorldBound son metadatos experimentales, no conectores habilitados.
- Catálogo consultable con búsqueda, filtros y revisión pasiva de mediciones. Las recomendaciones exigen datos de entrenamiento y comprobaciones independientes; un nombre de móvil reconocido no significa que todas sus balas estén calibradas. Las configuraciones antiguas generales permanecen como compatibilidad; los nuevos perfiles personalizados se guardan por juego, móvil y bala.
- Rendimiento funcional: CPU equivalente a un núcleo, RAM del proceso, tiempos de lectura y cálculo y presentaciones del overlay, muestreados cada dos segundos. No son FPS del juego ni RAM de Chrome. Exportación numérica y registro local acotado, sin credenciales ni nombres.
- Datos numéricos estables fuera de carpetas temporales: usa datos existentes o `%LOCALAPPDATA%/DragonLab/Manual`. La migración conserva originales, no sobrescribe destinos y excluye perfiles del navegador, cookies, licencias y configuración de cuentas.

## Referencia DragonboundGPT 0.1.26

La auditoría está en `INFORME-REA-0.1.26.md`, con comparaciones técnicas en `AUDITORIA-DRAGONLAB-0.20.md` y `AUDITORIA-VENTANA-UX-0.20.md`. Se examinó el ejecutable instalado y sus recursos estáticos; no se ejecutó el programa de referencia ni se recuperaron sus credenciales.

Se incorporaron equivalentes propios de organización, estado, catálogo, atajos y diagnóstico. No se copiaron coeficientes retrospectivos de Boomer/Tornado como si fueran fórmulas verificadas. La inspección no acreditó nuevos IDs de carros respecto de 0.1.23. El núcleo Rust existente se conserva.

## Verificación y límites

La entrega incluye pruebas de regresión Python, Rust y navegador sintético. Cubren cambio de cuenta con ID reutilizado, objeto de partida antiguo aún accesible, Map, 32 jugadores con metadatos delante, navegación SPA, recarga, dos lectores independientes, rechazo de Q obsoleto y dibujo de hasta 300 actores. La prueba no equivale a calibrar 300 jugadores reales.

La validación de ventana incluye tamaños mínimos, controles, maximizar/restaurar/minimizar y paneles. Los monitores con distintos DPI y todos los tiros/climas requieren pruebas físicas adicionales. No se declara una calibración completa ni una mejora nueva de FPS sin mediciones. Los datos propios de GunBound World no se aplican a DragonBound.

## Archivos para distribución

- Usuarios del manual: `DragonLab-Manual-0.20.0.zip`.
- Automático experimental: `DragonLab-Automatico-0.20.0.zip`.
- Launcher conectado al servidor: `DragonLab-Launcher-0.20.0.zip`; configura el servidor según la guía existente antes de distribuirlo.
- Fuentes y preparación del servidor: `DragonLabCloud-Preparacion.zip`. Nunca publiques datos locales de cuentas, navegador o claves privadas.

Las rutas de salida están en la carpeta `outputs` del proyecto. La activación del servicio cloud requiere configurar los servicios externos; este parche no crea cuentas ni publica un servidor nuevo.
