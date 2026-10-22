# DragonLab 0.15.4 · Integración de controles

Se conservan la captura, selección de objetivo, fuerza, trayectorias, atajos personalizados, perfiles separados por juego/carro/tiro y el aprendizaje con validación independiente.

- No empieza el entrenamiento mientras sigue ejecutándose un tiro manual.
- Descarta solicitudes manuales pendientes al pasar al entrenamiento; nunca las repite al salir.
- Invalida los cálculos anteriores al cambiar de modo. Al detener el entrenador, la guía vuelve a calcular desde los datos actuales.
- Escape cancela tanto la acción manual como el entrenador desde el programa. El juego conserva su protección propia de Escape.
- El launcher distingue entrenamiento, detención y asistencia. Ya no queda mostrando el estado final del entrenador mientras la guía vuelve a trabajar.
- Pausar funciona aunque el entrenador siga activo y la captura no tenga un hilo vivo.

No se atribuye un porcentaje de victorias nuevo a esta revisión. Teleport sigue pendiente de validar su trayectoria y destino.

El inicio espera hasta 60 segundos ante la pantalla conocida de carga del perfil, sin pulsar Enter ni cerrar avisos desconocidos. Si la carga no termina, se detiene con un mensaje específico.
