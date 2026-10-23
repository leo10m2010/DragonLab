# Análisis de aprendizaje 0.15.9

## Evidencia

La sesión observada tenía 8 tiros en 5 partidas: 4 provisionales, 4 ensayos de clima, 7 perfiles abiertos y cero tiros de evaluación independiente. Los registros conservados no permitían afirmar aprendizaje de puntería. Revisar solo teclas y tiempos no resolvía el error físico.

Se compararon componentes continuos, redondeo hacia abajo, truncamiento y redondeo al entero. Se eligió el tipo usando 24 episodios anteriores y se comprobó en 25 posteriores. Se excluyeron patrones variables y múltiples y trayectorias modificadas conocidas. Se ajustaron parámetros con los primeros tres tiros de cada grupo, reservando los siguientes para comprobarlos.

| Medida de reproducción histórica | Continuo | Componentes aprendidos |
|---|---:|---:|
| Error de aceleración, RMSE en 126 tiros posteriores | 3,964 | 0,898 |
| Error medio máximo de trayectoria en 97 tiros posteriores | 5,348 px | 1,404 px |
| Trayectorias posteriores sobre 12 px | 13 | 0 |

La trayectoria se reconstruye usando el ángulo y duración reales del proyectil. Esto comprueba la física de lanzamiento, no la capacidad de escoger un tiro ni la tasa de victorias. La selección de tipo se mantuvo separada de los episodios posteriores.

## Cambios

El cálculo compartido selecciona el tipo a partir de residuos medidos. Ajustes locales conservan su partida, candidatos y tiros posteriores separados. La cobertura del viento se expresa mediante los componentes observados: cambiar el viento dentro de ella no cambia los parámetros congelados. Se concentra la práctica por carro/modalidad y se conserva la separación de la calibración de la guía.

La prueba reproducible usa tests/fixtures/wind_component_replay.json y tests/test_learned_wind.py. La comprobación con partidas nuevas sigue siendo necesaria.
