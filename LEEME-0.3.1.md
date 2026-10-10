# DragonLab 0.3.1 — Captura y guía más estables

Cierra DragonLab 0.3 antes de abrir DragonLab-0.3.1.exe. Mantén abierto el navegador del juego. Esta versión busca la conexión original y también el navegador propio de DragonLab; si hace falta, pulsa Abrir DragonBound.

Cambios:
- La captura toma la vista completa del navegador y recorta el mapa dentro de DragonLab. No envía un recorte de página ni cambia el tamaño del navegador.
- Los datos de posiciones se consultan cada 0,25 segundos; las imágenes se capturan cada 1,5 segundos para reducir carga.
- Si falla una imagen, la lectura de posiciones sigue funcionando.
- La marca conserva su ventana y sus dibujos. Al mover el navegador se recoloca; no se destruye y crea de nuevo.
- Mover la cámara actualiza la posición dibujada sin borrar y recalcular la fuerza.
- El objetivo automático se conserva hasta que deja de estar disponible. Puedes cambiarlo en Objetivo; los jugadores identificados como muertos se excluyen.

La potencia calculada sigue dependiendo del perfil del vehículo, ángulo, viento y precisión del modelo. Estas mejoras evitan cambios de objetivo y cálculos causados solo por la cámara; no demuestran mayor precisión de los tiros especiales ni de todos los climas. Si observas una diferencia repetida, utiliza Calibrar con un disparo y Guarda perfil para ese vehículo.

Validación: captura real en navegador de prueba con tamaño de ventana y escala idénticos antes y después; recorte 800×600 y rango completo de barra; frecuencia de captura limitada; lectura conservada ante fallo de imagen; marca persistente; cambios de cámara; objetivo estable y elección explícita; nueve comprobaciones del motor de trayectorias; comprobación de arranque del ejecutable. Pendiente: confirmar que desaparece el movimiento reportado durante tu partida real y calibrar la precisión de fuerza con tiros observados.
