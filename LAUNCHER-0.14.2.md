# DragonLab 0.14.2 · Aprendizaje comprobable y conexión con el Lab

Cierra la versión anterior y abre DragonLab-Prueba.exe. Entrenar-Continuo.cmd inicia DragonBound y el aprendizaje. Esc o Detener cancelan los controles.

## Qué cambia

El entrenamiento anterior rotaba carros muy pronto: sus últimos 120 tiros registrados eran de exploración o medición, sin decisiones apuntadas con un modelo propio. Acumular tiros no demostraba mejora de puntería.

Ahora concentra hasta tres partidas en un carro antes de rotarlo, prioriza una modalidad pendiente y mantiene la elevación durante bloques de seis mediciones. Cuando dispone de una modalidad ordinaria validada, reserva dos de cada tres decisiones a reutilizarla y una a ampliar las modalidades pendientes. No genera una solución si el modelo no cubre el viento, el clima o un mecanismo especial.

Sin clima activo ni patrón múltiple, puede interpolar una fuerza entre dos tiros reales comparables de la misma partida: uno corto y otro largo. Exige viento/dirección, origen, lado, elevación y altura final próximos; no extrapola fuera de lo medido. El resultado se identifica como aproximado y se mide de nuevo. Los modelos generales continúan requiriendo comprobaciones futuras.

## El Lab recibe las mediciones

Los eventos de tiros propios confirmados también llegan al libro de calibración del Lab. Su validador mantiene candidatos separados: requiere tres tiros posteriores diversos, límites de error y una mejora del error respecto al ajuste existente antes de reemplazarlo. Conserva el ajuste previo para recuperación. Los grupos de proyectiles se almacenan como patrones y no se convierten en una bala única por conveniencia. Un tiro rival, una predicción o una salida no confirmada no obtiene crédito de calibración.

Esta comunicación es de mediciones reales hacia el Lab: el entrenador sigue sin pedirle fuerzas ni utilizar sus perfiles como profesor. No se promocionan retrospectivamente las mediciones antiguas del entrenador como si acabaran de validarse. Se conservan sus archivos. La sincronización de producción mantiene las reglas de consentimiento existentes; la prueba local no envía datos al servidor.

## Progreso visible

Ajustes → Aprender del juego muestra mediciones, modelos básicos, tiros con experiencia, tiros de exploración, perfiles del Lab y reemplazos con mejora comprobada del error de lanzamiento. entrenamiento-estado.json conserva el mismo resumen. Los contadores de casos son acotados y los casos anteriores sin etiqueta se clasifican como exploración, sin inventar decisiones aprendidas.

Un modelo de lanzamiento validado no significa que todos sus climas, impactos o proyectiles secundarios estén dominados. El informe no declara mejora global de puntería; faltan comparaciones amplias de tiros nuevos en condiciones equivalentes. Tampoco se ha certificado juego profesional o continuidad de 24 horas.

## Verificación

190 pruebas automatizadas aprobadas. Incluyen compartir observaciones confirmadas, rechazar otro jugador, no duplicar mediciones, exigir comprobación futura, conservar y reemplazar perfiles con evidencia de mejora, currículo concentrado, interpolación acotada y rechazo de viento/clima/patrón incompatibles. Esta revisión aún necesita contraste ampliado de la política nueva en partidas reales. GunBound World mantiene sus perfiles separados y no está incluido en este entrenador.
