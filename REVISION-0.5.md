# Revisión y evidencia de DragonLab 0.5

## Fallos encontrados y correcciones

1. El lector usaba `game.weather`, una previsión numérica, y el cálculo no recibía ese resultado. Ahora utiliza las columnas renderizadas, su tipo resuelto y su posición. Se observó el formato nativo `[tipo, x, tamaño, tipo resuelto opcional]` y se verificaron los identificadores 7 (Mirror), 8 (Tornado) y 6 (Random).
2. `renderer.view` describe el área de cámara, no el lienzo. Las dimensiones reales están en `renderer.renderer.width/height`. La matriz visible se normaliza con esas dimensiones. También se corrigió la transformación alternativa de cámara.
3. La orientación y la pendiente del vehículo se aplicaban incorrectamente. Se contrastó la fórmula del ángulo con funciones del cliente y salidas reales de balas. El lector entrega un ángulo relativo coherente con la dirección que usa el motor propio.
4. Se buscaban mapas de alturas que el juego no exponía. Ahora se lee la máscara alfa del terreno existente y se transmite como filas comprimidas, con actualización periódica y al cambiar de turno. La comprobación de colisión recorre los píxeles entre muestras.
5. El lector podía retener un juego destruido al cambiar de partida. Descarta los objetos, el terreno y la cámara y descubre la nueva partida.
6. Se acumulaban cálculos simultáneos. La nueva versión permite un solo cálculo y descarta resultados que quedaron desactualizados.
7. Se descartaban tiros dobles aun cuando ambas balas tenían exactamente la misma salida. Ahora se permite medir ese caso, con separación por vehículo y modalidad y comprobación al retirar cada muestra del ajuste.
8. El seguimiento de balas suponía que el primer hijo visual siempre era el proyectil. Se utilizan la posición de la animación o sus puntos de traza; los datos del servidor permiten reconstruir las curvas observadas sin invocar funciones de disparo.

## Validación realizada

- Comparación de curvas numéricas con posiciones renderizadas de 85 proyectiles observados. Se excluyeron matrices que todavía no habían sido dibujadas en el primer fotograma. El error numérico máximo en los casos comparados fue inferior a 0,000001 píxeles. Esta prueba valida la reconstrucción de una bala ya recibida, no la predicción de su fuerza antes de disparar.
- Se compararon 28 transiciones de Tornado, correspondientes a siete balas que contienen secuencias de cuatro cambios. Los tiempos coinciden y la diferencia máxima de posición es 0,67 píxeles con la velocidad y aceleración iniciales reales. Las balas dobles no cuentan como tiros de calibración independientes.
- Armor, tiro 2: nueve salidas reales con distintas fuerzas; escala de velocidad 2,269787, error medio cuadrático de velocidad 0,234 y error máximo al retirar una muestra 0,471. Se conserva la evidencia separada. Durante la ejecución posterior se observaron salidas con otra escala; el control de cambios suspendió el ajuste y comenzó a recalibrar. No se declara universal para todas las partidas.
- Catorce casos de ángulos horizontales, altos, verticales, hacia atrás y negativos en ambas direcciones. Estas pruebas usan datos controlados y no se guardan como calibraciones reales.
- Lectura de Mirror, Tornado, terreno y cambio de partida en un navegador de pruebas; máscara con agujeros y dimensiones físicas reales del renderizador.
- Captura sin cambiar el tamaño del juego; continuidad de la marca de fuerza; capas persistentes sin tomar el foco; prueba de colisión con una plataforma de un píxel.
- Ejecución del programa sobre un estado vivo con terreno y Tornado: cálculo de aproximadamente 0,25 segundos en el caso medido. El tiempo depende del mapa, vehículo y número de proyectiles.

Mirror se detectó en partidas reales. La inversión y la entrada desde arriba tienen pruebas numéricas; hasta completar un tiro que atraviese Mirror no se declara una comprobación real de su rebote. La precisión de los perfiles no medidos y de proyectiles especiales sigue pendiente de calibración.

## Investigación en GitHub

Se revisó código, no solo las promesas de los README. No se ejecutaron programas descargados ni se incorporó código de terceros al producto.

- [SanjoSolutions/gunbound-aimbot](https://github.com/SanjoSolutions/gunbound-aimbot), revisión `cab943ce0a6a9fbe1e038d361b9daf91ac331a54`: el propio repositorio aclara que publica una implementación básica y que su versión reciente es cerrada. Su cálculo muestra cuantización del viento y coordenadas propias de GunBound para Windows. No demuestra compatibilidad actual con DragonBound ni aporta el motor moderno de climas.
- [RxFaX/Aimbot-DragonBound](https://github.com/RxFaX/Aimbot-DragonBound), revisión `f9b8769a439d516ec80dc02ed8862af6b312a1b2`: se contrastaron las transformaciones de orientación, pendiente y salida, y el cálculo histórico de potencia. Usa mecanismos antiguos como `Object.observe`; no se instaló su extensión ni se trasladaron sus controles de juego.
- [fsbertelli/gunbound-advanced-aimbot](https://github.com/fsbertelli/gunbound-advanced-aimbot), revisión `001f507907e0910df2f5b35dfd0fcde3e0131d06`: contiene entrenamiento con muestras etiquetadas y un arco ilustrativo que usa gravedad 9,81 y escalas visuales. Ese arco no constituye un modelo verificado de DragonBound. Se priorizaron los datos medidos del juego frente a esas escalas.
- [DragonBot Js, fuente histórica](https://gist.github.com/hschmitt/3530953): útil para contrastar convenciones antiguas, sin asumir que sus constantes siguen vigentes.

Las decisiones finales se basan en el cliente actual observado, la aplicación previa inspeccionada y comprobaciones del código independiente. No se promete compatibilidad universal entre clones.
