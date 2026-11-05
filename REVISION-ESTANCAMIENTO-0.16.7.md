# Por qué las horas de entrenamiento no se traducían en mejores tiros

Revisión del 5 de noviembre de 2026. Fuentes: archivos numéricos de ambas sesiones del recorrido 0.16.6, observaciones nativas archivadas y código propio. Los contadores se tomaron mientras las sesiones seguían trabajando, por lo que varían ligeramente entre capturas.

| Métrica observada, aproximadamente 11,2 horas | Sesión 1 | Sesión 2 |
| --- | ---: | ---: |
| Tiros confirmados | 1.310 | 1.417 |
| Calibración | 1.205 | 1.298 |
| Evaluación dirigida | 92 | 92 |
| Cerca del objetivo en evaluación | 30/92 | 45/92 |
| Turnos omitidos | 1.776 | 1.644 |
| Últimos 100 resultados retenidos | 14 ganados, 86 perdidos | 22 ganados, 73 perdidos, 5 desconocidos |

Los intentos de búsqueda de partida no se cuentan aquí como partidas completadas. No puede establecerse si ambas cuentas se enfrentaron entre sí mediante los identificadores locales conservados. El informe numérico de trabajo está en `work/stagnation-0166.json`.

## Causa comprobada: el origen de Nak y Aduka

En las observaciones archivadas, los carros ordinarios tenían error de origen cero; los tiros de Nak y Aduka tenían aproximadamente 51,5 píxeles de diferencia sistemática. Afectaba 229 tiros de Aduka 1, 156 de Nak 1 y 32 de Aduka 2 entre ambas sesiones analizadas.

La transformación aplicaba una inversión adicional por pertenecer al grupo de carros de salida trasera. Sus definiciones nativas ya incluyen esa orientación. `launch_geometry.py` ahora transforma esas definiciones con la dirección y pendiente reales, sin invertirlas otra vez. Se conservó el comportamiento de los perfiles base antiguos, que son otra representación.

Seis muestras anónimas propias cubren ambas direcciones y pendientes de −7°, +1°, +3°, +12° y +16°. La fórmula anterior se desviaba más de 50 píxeles; la corregida reproduce el origen nativo exactamente. Una prueba inversa adicional recupera una fuerza conocida con esa geometría. Esto valida esos ejemplos y la transformación, no todos los tiros del juego.

El modelo físico de Nak ya había reducido el error mediano de predicción de vuelo a aproximadamente 1,09 píxeles frente a 10,83 del modelo de referencia, pero su distancia al objetivo seguía alrededor de 45,76 píxeles. Aprender mejor la ecuación no compensaba una salida desplazada.

## Calibración poco informativa

Había diversidad global de ángulos; no es correcto afirmar que todos los tiros se hacían con un ángulo fijo. El problema del planificador era elegir la primera trayectoria libre aunque la propuesta de investigación pidiera otra fuerza. En un caso controlado, pedir 100 o 360 terminaba en la misma solución de 219.

La búsqueda de calibración ahora compara un conjunto acotado de trayectorias ya aceptables. Favorece separación respecto a fuerzas nativas observadas en esa partida y contexto de viento, y después proximidad a la fuerza de investigación. En ese caso devuelve soluciones de 212 y 363. La geometría puede impedir una fuerza baja concreta; no se fuerza un tiro arbitrario para completar la tabla.

El modo de evaluación congelada conserva su elección normal. La comprobación final usa solo el ángulo real y vuelve a calcular la fuerza. Terreno, climas desconocidos y límites de un tramo parcial se comprueban antes de ordenar los candidatos.

## Referencias de partidas distintas

Los parámetros ajustados difieren entre episodios; reutilizar ciertos modelos históricos daba errores medianos de vuelo de unos 9–48 píxeles. Todavía no se ha determinado cuánto procede de condiciones físicas, lectura o unidades. No se atribuye a una aleatoriedad del servidor sin evidencia.

La selección anterior de referencias podía juntar muestras de varias partidas cuando ninguna tenía suficientes observaciones. Se eliminó ese recurso. Además, la referencia provisional se actualiza entre partidas cuando hay un grupo coherente más reciente, y se mantiene fija durante las comprobaciones de ese contexto. Las observaciones utilizadas para ajustar siguen excluidas de sus pruebas futuras.

## Cómo juzgar la próxima sesión

Comprobar primero el error de origen en Nak/Aduka, la variedad real de fuerzas y el paso de calibración a evaluación. Después contrastar distancia al objetivo, ventanas de daño, turnos omitidos y resultados sobre ventanas comparables. El número total de tiros o el porcentaje del catálogo de carros no acreditan mejor puntería.

Las pruebas controladas no demuestran una mejora de victorias. La activación siguiente conserva los archivos anteriores como referencia y comienza un recorrido identificable para medir estos cambios.
