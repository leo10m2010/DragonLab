# DragonLab 0.16.1 · Dos sesiones de prueba

Abre `Entrenar-2-Sesiones.cmd` para iniciar dos entrenadores desde un solo DragonLab. La primera cuenta usa el navegador habitual del programa. El botón «Segunda cuenta» abre otra ventana con un perfil independiente; entra allí con la otra cuenta y elige Avatar Off, servidor 8.

El perfil de la segunda ventana se abre con una ruta absoluta y se comprueba que la carpeta admita escritura. Se corrigió el aviso de Chrome que aparecía con una ruta relativa. No se copian contraseñas ni cookies de la primera cuenta. Deja una sola pestaña de DragonBound en cada ventana para que la conexión sea inequívoca.

En Aprendizaje, «Partidas» permite elegir 1 o 2; «Sesión 1 / Sesión 2» cambia los datos mostrados. Con dos partidas se usa el modo de segundo plano. Los controles se dirigen a la pestaña fijada de cada navegador. Detener cancela ambos entrenadores; Esc dentro de un juego detiene ese trabajador. Cerrar el panel mantiene las sesiones; cerrar DragonLab las detiene.

Cada trabajador conserva su propio aprendizaje, calibraciones, turnos y evaluaciones. Las observaciones reales se incorporan al Lab con procedencia separada y pasan sus comprobaciones; no se copian ajustes entre trabajadores. Los archivos originales se conservan. El inicio copia solo calibraciones y mediciones existentes cuando aún no hay archivos para ese trabajador.

## Corrección de puntería

El entrenador utiliza ahora el cañón nativo específico de cada bala, con la posición, pendiente y orientación confirmadas. La búsqueda de fuerza y las colisiones parten de ese origen; se vuelve a calcular después de caminar o ajustar el tiro. El registro compara origen previsto y observado para verificar los tiros siguientes. Los lectores antiguos mantienen una alternativa explícita cuando faltan estos datos.

Esta corrección aborda la diferencia detectada al revisar la sesión de 113 tiros. Las pruebas de código no demuestran por sí solas una mejora de impactos o victorias: falta comprobar la nueva versión jugando con ambas cuentas.

## Archivos y duración

- `DragonLab-Prueba-0.16.1.zip`: paquete local para usar.
- `DragonLabCloud-Preparacion.zip`: código y preparación para el repositorio.
- `Entrenar-24-Horas.cmd`: conserva la sesión individual.
- `Entrenar-2-Sesiones.cmd`: dos trabajadores con plazo de 24 horas cada uno.

Cada navegador y el programa deben permanecer abiertos. Los avisos desconocidos y el chat pausan controles. No se ha certificado continuidad durante 24 horas ni mejora de victorias. El entrenamiento de GunBound World continúa separado y no participa en estas dos sesiones de DragonBound.

El resumen conjunto está en `entrenamiento-paralelo-estado.json`. Los datos individuales están en `entrenamiento-paralelo/sesion-1` y `entrenamiento-paralelo/sesion-2`, con informes y observaciones nativas propios. El estado individual identifica si el cierre fue solicitado, por límite de tiempo o por error.

Validación de código: 412 pruebas Python y cuatro suites de navegador aprobadas. La separación y el progreso real de los dos trabajadores deben comprobarse en las cuentas abiertas; estos controles no equivalen a una prueba completa de 24 horas ni a puntería perfecta.
