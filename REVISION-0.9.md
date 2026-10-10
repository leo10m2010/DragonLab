# Revisión 0.9

## Cambios

Interfaz compacta con fuerza destacada, objetivo, estado y accesos esenciales. Vista del mapa opcional; ajustes simples de marcas, rendimiento y teclas. Herramientas técnicas conservadas en una ventana secundaria. Vista y ajustes renderizados e inspeccionados.

Atajo predeterminado Q para un solo tiro solicitado por el usuario. Lectura de fuerza en vivo, detección del modo Slice/Drag desde la variable propia de su controlador, ajuste del arrastre según su ganancia real y liberación de entrada al alcanzar la fuerza. Rechaza chat abierto, otro turno, jugador muerto, cambios de viento, posición, ángulo, modo de tiro o foco. No se invocan funciones de disparo del juego mediante CDP. Los eventos inyectados, la repetición de tecla y las combinaciones con modificadores no generan nuevas solicitudes. Ctrl sigue cambiando objetivo al soltarse. Sin atajos F8 ni otras teclas de función.

Se eliminan copias profundas del terreno al preparar cálculos y serializaciones completas para un visor que no está activo. En Ligero, lecturas cada 350 ms, terreno cada cinco segundos o cambio de turno, capturas de vista cada tres segundos únicamente cuando se abre el mapa. La calibración y la resolución de búsqueda se conservan.

El límite inferior de trayectoria deriva de la altura/origen del mapa y las posiciones de ambos jugadores. La lectura acepta mapas de hasta doce millones de píxeles. Nak tiro 2 detecta entrada en terreno, conserva la velocidad instantánea al siguiente tick nativo de 25 ms, usa aceleración subterránea [0,-1440] y detecta su retorno a aire mediante recorrido de píxeles. Solo la salida cuenta como impacto de tiro 2; un paso cercano en la fase aérea no se presenta como acierto. Nak SS atraviesa el terreno en este modelo.

## Evidencia y pruebas

Cinco pares reales de proyectiles Nak 35/36: velocidad secundaria coincide con la velocidad terminal de su proyectil primario; aceleración secundaria [0,-1440] en los cinco casos. Siete lanzamientos Nak tiro 2 en el libro de calibración: escala 2,027218, gravedad 365,853830 y respuesta al viento 3,976087. Error RMS de velocidad 0,321 y error de muestra reservada 0,676. No se transforman pruebas sintéticas en calibraciones reales.

Pruebas de retorno subterráneo, paso SS, solución con jugador a y=2100 y objetivo aún más bajo, feedback Slice/Drag con fuerza medida, rechazo de chat y teclas reservadas. Regresiones: 85 posiciones nativas, 28 transiciones de Tornado (máximo error de posición 0,662 unidades), 14 casos de ángulos, terreno fino, selección con cuatro jugadores reales y ocho de prueba, treinta pulsaciones Ctrl rápidas, instalación/retirada del receptor de teclado Windows y lectura en navegador de prueba.

Estas comprobaciones no constituyen validación de todos los vehículos, todas las topografías, todos los climas, todas las máquinas ni todos los clones. El tiro por atajo aún necesita contraste en una partida real; durante la última revisión la página conectada estaba fuera de una partida activa.
