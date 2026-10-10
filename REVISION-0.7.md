# Revisión 0.7

## Detección y objetivos múltiples

Se contrastó la lectura con una partida real de cuatro jugadores: jugador propio 2, aliado 0 y enemigos 1 y 3. Se verificó el ciclo 3 → 1 → 3 sobre esa captura. Una prueba de ocho jugadores derivada de la estructura capturada recorrió cuatro enemigos, sin incluir aliados. No se presenta esa prueba sintética como una partida real de ocho personas.

Identificadores y equipos numéricos se normalizan aunque lleguen como texto. Se descartan posiciones no finitas y duplicados, se conserva el índice original de listas con huecos y se reconocen indicadores booleanos/numéricos del jugador propio y de jugadores muertos. Si no se identifica el jugador propio, la fuerza se oculta hasta recuperar la identificación. Una selección eliminada o muerta pasa a un enemigo vivo. Las marcas de enemigos fuera de pantalla se proyectan al borde con flechas.

## Ctrl

Antes se consultaba cada 50 ms mediante un temporizador de la interfaz. La consulta ahora corre cada 8 ms en un hilo independiente, con lectura adicional de pulsaciones muy breves. Se eliminó la dependencia de eventos antiguos de otras teclas al empezar a pulsar Ctrl y se excluyen botones del ratón. Las combinaciones y cambios de ventana se descartan. Solo actúa con el juego enfocado y datos recientes; no inyecta ni bloquea teclas, y no guarda su contenido.

## Rendimiento y continuidad

La decisión de recalcular se basa en el jugador propio, el objetivo elegido, viento, tiro, terreno y climas. Se dejó de serializar el estado completo y de invalidar cálculos al moverse un jugador ajeno o cambiar la cámara. Veinte cambios ajenos consecutivos en la prueba no provocaron nuevos cálculos. Se consumen los datos más recientes de la cola antes de aplicar resultados, evitando reproducir cuadros atrasados. Si ocurre un error en el ciclo, este continúa y conserva un diagnóstico local.

Al minimizar la ventana se suspenden las capturas de imagen y el dibujo de su vista previa. La lectura de posiciones, el atajo, los recorridos observados y las marcas del juego continúan. Se observó una consulta real de fuerza de 0,216 segundos en el equipo actual (Intel i7-13700KF); no equivale a una prueba de fluidez en equipos antiguos ni garantiza el mismo tiempo en todos los tiros.

## Verificación y límites

Pruebas de ciclo con varios enemigos, desaparición del seleccionado, tipos mezclados de identificadores/equipos, cambio de cámara/aliado sin recalcular, recuperación del ciclo tras un error controlado y etiquetas persistentes. El navegador de prueba verificó cámara, terreno, proyectiles y lectura de datos nativos. Se conservaron las pruebas de agrupación de Trico y descarte de combinaciones Ctrl. Tras instalar la versión, el usuario confirmó que Ctrl cambia el objetivo en cada pulsación, incluyendo las pulsaciones rápidas solicitadas. La lectura en vivo mostró cuatro jugadores, dos enemigos y ningún error registrado antes de que la aplicación se volviera a abrir sin diagnósticos.

La detección de jugadores corregida no convierte en exactos los perfiles balísticos todavía sin calibrar. Las órbitas de Trico, cajas de daño, perforación y cambios de terreno entre impactos necesitan validación adicional específica. Referencias de comportamiento: [móviles](https://dragonbound.net/guia/moviles) y [climas](https://dragonbound.net/guia/comojugar).
