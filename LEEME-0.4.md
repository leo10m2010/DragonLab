# DragonLab 0.4 — Trayectorias y menú simple

Cierra las versiones anteriores antes de abrir DragonLab-0.4.exe. Conserva el navegador del juego abierto; si no conecta, pulsa Abrir juego. No es necesario instalar Python.

## Durante la partida

- La captura, las posiciones, el vehículo, el ángulo y el viento se leen automáticamente.
- La línea verde muestra una trayectoria prevista por el modelo. Si el ángulo no alcanza el objetivo, puede mostrar una vista de la última fuerza conocida, claramente indicada, sin inventar una fuerza recomendada.
- La línea azul muestra la estela de los proyectiles observados en el juego cuando el conector puede leer su posición. Incluye tiros del rival. Es una estela registrada mientras vuelan; no garantiza conocer por adelantado todos sus rebotes.
- La marca naranja sigue indicando la fuerza recomendada cuando hay una solución válida.
- Trayectorias y Marca de fuerza se pueden ocultar por separado. Las capas dejan libre la zona inferior de controles y se ocultan al cambiar de ventana o salir de la partida.
- El objetivo se mantiene estable; puedes elegir otro en la lista.

## Menú

La pantalla principal conserva Abrir juego, Pausar captura, Ajustes, las dos opciones de visualización y el objetivo. Los controles de gravedad, viento, captura manual, sesiones, conexión, visión, terreno y modelos especiales continúan funcionando dentro de Ajustes. No es necesario abrirlos para usar el modo automático.

## Calibración real

Los 23 perfiles tienen registros separados por juego, vehículo y tipo de tiro. En Ajustes → Vehículos puedes ver su estado. Un perfil base no se presenta como calibrado.

La salida del cañón de ICE y GRUB se leyó en la partida observada. También se corrigió la lectura de la inclinación y la orientación real del jugador. El conector lee los parámetros de salida de los vehículos presentes en nuevas partidas y utiliza la transformación de cámara del propio juego para colocar la guía.

La calibración automática de fuerza observa el tiro normal de tu vehículo cuando hay un solo proyectil atribuible. Requiere al menos cuatro tiros consistentes, tres fuerzas diferentes y una variación suficiente. Ajusta velocidad, gravedad y respuesta al viento si los datos permiten medirla. Guarda las muestras y el ajuste en calibraciones.json. Descarta muestras ambiguas, repetidas, tiros del rival y lanzamientos múltiples. Si solo se midió ausencia de viento, no aplica ese ajuste cuando hay viento.

**No están todos los vehículos calibrados con tiros reales.** La partida terminó antes de obtener las muestras necesarias de fuerza. ESTADO-VEHICULOS.md distingue salida medida y fuerza todavía base. Los tiros 2 y SS, y los lanzamientos múltiples, necesitan mediciones adicionales o importadas. Puedes importar datos atribuidos por vehículo y tiro desde Ajustes → Vehículos; las pruebas sintéticas de desarrollo no se incluyen como mediciones reales.

## Comprobaciones

Se comprobó la lectura de proyectiles y matrices en un navegador de prueba, la proyección e inversa, la conservación de foco y controles con capas nativas de Windows, la reutilización de líneas sin recrear ventanas, la caducidad de estelas, el guardado y la separación de calibraciones, el rechazo de tiros ajenos y duplicados, 23 ajustes independientes con datos de prueba, nueve comprobaciones físicas, y el arranque del ejecutable. Se revisó visualmente el menú nuevo.

Falta comprobar la alineación de las nuevas trayectorias y completar la calibración con tiros reales de los distintos vehículos. GunBound World sigue siendo experimental; esta versión prioriza DragonBound.
