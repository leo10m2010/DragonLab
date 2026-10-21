# DragonLab 0.14.5 · Prueba de puntería medible

Abre DragonLab-Prueba.exe. Para iniciar directamente la comprobación, usa Comprobar-Punteria.cmd. Cierra primero la ventana de la versión anterior: el launcher permite una sola instancia. Se conservan las mediciones anteriores.

## Qué cambia

El botón de aprendizaje inicia una prueba limitada de Armor tiro 1, de hasta 20 o 40 tiros, seis partidas y 15 minutos. Ya no inicia exploración indefinida de todos los carros. Esc detiene la sesión; se respetan foco, chat y turno, sin repetir una carga en el mismo turno.

La calibración intenta dirigir tiros con hipótesis provisionales calculadas de mediciones reales. Un ajuste local necesita observaciones posteriores distintas antes de pasar a evaluación. La evaluación usa una copia fija del modelo. Si falta una solución por viento, clima, terreno o geometría, se omite ese turno; seis omisiones terminan la prueba. No se usa una carga arbitraria como sustituto.

El panel separa tiros de calibración, tiros dirigidos de evaluación, distancia al objetivo, bajadas observadas de vida/escudo y resultados confirmados de partidas. Un resultado desconocido no cuenta como derrota. La bajada de vida durante la ventana del tiro no se presenta como impacto directo confirmado. Los porcentajes de cobertura siguen separados de precisión y autonomía.

Se guarda evaluacion-punteria.json y partidas-observadas.json junto al archivo de calibraciones. Cada ejecución conserva sus resultados actuales; estos dos informes se reemplazan al iniciar otra prueba. Las mediciones históricas del aprendiz se mantienen. Solo se aprueba una prueba con al menos diez recorridos medibles, 80% a 20 píxeles o menos, mediana de 15 píxeles o menos, cinco ventanas de vida conocidas y bajada en al menos el 60%. Esa aprobación no significa autonomía completa.

Cuando existe un modelo anterior comparable, ambos modelos se contrastan con los mismos tiros nuevos. No se declara una mejora de predicción antes de diez comparaciones independientes y una reducción de error de al menos el 10%.

## Fallos corregidos

- La velocidad nativa de salida ya no se expone como fuerza de la barra.
- La atribución comprueba el origen del disparo contra la posición al soltar la carga, permitiendo una caída posterior en un cráter. Rechaza modalidad incorrecta, tiros antiguos y familias ajenas.
- La conexión de control evita volver a copiar todo el terreno al preparar o confirmar cada carga; amplía la ventana de confirmación sin repetir el disparo.
- El ajuste provisional local se utiliza para dirigir la siguiente calibración, sin contarlo como evaluación ni validarse con sus propios datos de ajuste.

## Evidencia y límites

228 pruebas de código aprobadas. Dos ensayos reales iniciales no reunieron tiros dirigidos suficientes: uno registró siete tiros de calibración; el segundo, uno. No hay mejora de victorias demostrada. La prueba termina con datos insuficientes en estos casos y no muestra un porcentaje inventado de autonomía.

Esta versión corrige el controlador y la forma de evaluar. No convierte todavía el calibrador en un agente profesional que aprende estrategia, movimiento y victorias. Mirror, Tornado y los mecanismos especiales de otros carros siguen necesitando modelos y comprobaciones propios. Los perfiles de GunBound World siguen separados.

## Qué publicar

Para distribuir una prueba local: DragonLab-Prueba-0.14.5.zip. Para preparar el producto con tu servidor: DragonLab-Launcher-0.14.5.zip, configurando primero los servicios descritos en la documentación del proyecto. El launcher de producción no sustituye la configuración de Supabase ni el despliegue del servidor. No publiques claves privadas, sesiones ni archivos de mediciones personales.
