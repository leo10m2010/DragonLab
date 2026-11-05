# DragonLab 0.17.0 · Aprender de lo que ocurrió

Esta versión añade preferencias que se actualizan con resultados reales. El sistema anterior ajustaba ecuaciones y seguía reglas; acumular tiros no entrenaba por sí solo una estrategia ganadora.

## Qué aprende ahora

- Guarda el daño propio y enemigo que pueda atribuir al tiro, su contexto anónimo y el resultado nativo de la partida. Los resultados dudosos, curaciones, interferencias y duplicados no actualizan las preferencias.
- Aprende a preferir modalidades y recorridos comprobados que dieron mejores resultados en situaciones similares. Conserva una exploración acotada entre opciones válidas. El cálculo y el juego siguen comprobando ángulo, fuerza, turno y disponibilidad.
- Los tiros de calibración dirigida también pueden aportar un resultado de daño comprobado. Eso no los convierte en pruebas de puntería aprobadas ni permite usar una física sin validar para decidir automáticamente una trayectoria nueva.
- Una victoria o derrota aporta un crédito pequeño, repartido entre las decisiones atribuibles de esa partida. No se cuenta una misma victoria como si cada bala hubiera ganado una partida.
- Las preferencias se conservan por cuenta en `aprendizaje-estrategia.json`. Continúan entre bloques, partidas y reinicios; no se comparten nombres, chats, capturas ni contraseñas.

## Qué deja de bloquear el aprendizaje

En distancias cortas puede ser imposible producir fuerzas separadas por 40 puntos sin tirar fuera del objetivo. Ahora se admite una ventana local después de al menos tres mediciones de ajuste y tres comprobaciones posteriores distintas. Exige errores más estrictos y una cota de incertidumbre; solo permite el rango de fuerza, tiempo y viento comprobados. No extrapola ese permiso a toda la barra ni a mecanismos especiales.

Un vuelo nativo nuevo que contradiga un modelo congelado lo retira de uso y devuelve ese contexto a calibración. Las correcciones de origen de Nak/Aduka de 0.16.7 continúan activas.

## Cómo saber si mejora

El panel separa resultados utilizados para aprender, preferencias aplicadas, cambios de tiro, modelos retirados y victorias reales. Los totales de la ejecución son distintos de los últimos 100 resultados.

Durante el entrenamiento, aproximadamente un 20 % de los episodios mantiene la elección de referencia para compararla con la selección aprendida. Ambas usan las mismas comprobaciones físicas. La asignación se fija al comenzar cada episodio; las derrotas sin decisiones útiles también cuentan si el juego confirma el resultado. El informe no declara una mejora de victorias automáticamente ni considera suficientes unas pocas partidas.

No se añadió un servicio de IA de pago ni una red neuronal grande. Es aprendizaje local de preferencias con recompensas comprobadas y un motor físico independiente. No implica dominio de todos los carros, climas, desplazamientos o ítems; esas mecánicas siguen requiriendo datos y validación propios.

## Iniciar

Usa `Entrenar-2-Sesiones.cmd` con las dos cuentas de prueba. El launcher prepara sus ventanas y establece 24 horas desde el inicio. Detener cancela ambas; deja la PC, el programa, los navegadores y la conexión disponibles.

Prueba: `DragonLab-Prueba-0.17.0.zip`. Launcher: `DragonLab-Launcher-0.17.0.zip`. Código y preparación: `DragonLabCloud-Preparacion.zip`.
