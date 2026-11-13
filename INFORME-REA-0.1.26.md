# DragonboundGPT 0.1.26: auditoría estática previa a DragonLab 0.20

Fecha: 12 de noviembre de 2026. Se complementa con AUDITORIA-DRAGONLAB-0.20.md y AUDITORIA-VENTANA-UX-0.20.md, elaboradas antes de implementar las correcciones integrales.

El artefacto E:/db/DragonboundGPT/DragonboundGPT.exe declara ProductVersion/FileVersion 0.1.26.0; 40.235.008 bytes; SHA-256 42af2996db786c6b76478ee4721f757cc9f5b57359fbf19058db69c5704df97d. La comparación usa 0.1.23.0, 40.047.616 bytes, SHA-256 ba7c538234ebcfeaaba9003d09d8912f2ef25835af4ad8c880df25861af014a0.

Se leyeron estructura PE, recursos distribuidos, constantes y QML; no BrowserData, licencia, credenciales ni almacenamiento de cuentas. No se ejecutó el programa ni se enviaron tiros. REA MCP no ofrece herramientas en esta sesión; el doctor CLI 6.9.0 rechazó Node 24.12.0 antes de establecer el estado de los proveedores. No se cambió configuración ni se instalaron motores. Las constantes no equivalen a recuperar control de flujo nativo o verificar funcionamiento y precisión en vivo.

## Evidencia observada y decisiones

| Área | Evidencia 0.1.26 | Decisión para DragonLab |
|---|---|---|
| UI | JS/CSS/HTML web idénticos byte a byte a 0.1.23; launcher/startup nativos sí cambiaron. | Conservar interfaz propia; integrar acciones reales y organización, sin copiar apariencia o asumir funcionalidad por un botón. |
| Inicio/recuperación | Nuevos módulos windows_ipc/windows_startup; reserva temprana de ventana, feedback y restauración. REA26-STARTUP. | Mantener instancia única, marco Windows correcto y recuperación de conexión. No copiar mecanismos de licencia. |
| Juegos | WorldBound experimental y URL personalizada; referencias anteriores a iGunsFire/ShotBound. REA26-GAMES. | Registro extensible, con DragonBound/GunBound World separados y estado experimental explícito para lo no comprobado. |
| Barra con Rankings | Código distribuido valida coordenadas de navegador, no mundo 0..800; axisLeft/ancho escalado/innerWidth. REA26-CDP-POWER, offsets 39793491–39793846. | Completar pruebas y validación de viewport/sidebar/zoom del lector DOM propio. |
| Calibración pendiente | calibration_indicator distingue primer tiro local por generación/móvil; QML añade calibrationPending/barX/barWidth con animación condicionada. REA26-CALIBRATION-INDICATOR y REA26-QML-PENDING. | Estado pendiente claro y época de sesión; indicador ligero sin animación permanente. |
| Boomer/Tornado | Ángulo balístico frente a mostrado, fuerza dinámica y reloj de corte; su documentación dice que constantes y offset -7 proceden de diarios retrospectivos, no fórmula del servidor. REA26-BOOMER, offsets 40096607–40104260. | No promover parámetros ajenos a calibración propia. Conservar perfiles comprobados y validar mecanismos especiales con tiros independientes. |
| Móviles | Mismo catálogo de 23 IDs 0..22 que 0.1.23. REA26-CATALOG. | No inventar IDs ni calibraciones; 22 móviles consultables excluyendo la selección Random, con metadatos versionados. |
| Detección/atajos | Regiones de constantes de players, detection, hotkey, autoshot, hero_angle, projection y terrain permanecen idénticas. Esto no prueba identidad del código máquina. REA26-UNCHANGED-CONSTANTS. | Corregir causas propias observadas: caché SPA, ID héroe no primitivo, truncado previo al filtro, rótulos y perfiles personalizados sin modalidad. |

DragonLab ya aporta lectura CDP local, cámara/terreno, Ctrl/Q con comprobaciones, calibración por juego/móvil/tiro, biblioteca aprendida, comparación prevista/observada, respaldo de modelos especiales y componentes Rust. Se conservan estas capacidades y su evidencia; no se declara que la lista recomendada de otra aplicación valide nuestros tiros.

La evidencia local está en work/rea-0126: identities.json, resource-hashes.json, constant-deltas.json, evidence-ledger.json, hud.qml.diff.txt y mobile-catalog.json. Las extracciones completas no se publican. Quedan desconocidos el flujo nativo completo, la ejecución real de cada acción, la precisión y compatibilidad efectiva de juegos experimentales y una comparación equivalente CPU/RAM con DragonboundGPT. Las implementaciones propias deben validarse por separado.
