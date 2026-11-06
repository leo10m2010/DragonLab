# Archivo de guías del entrenamiento automático

## Qué se conserva

El registro de lanzamientos existente conservaba parámetros nativos, pero el planificador descartaba el modelo previo y el recorrido calculado. `training_guides.py` añade un archivo local por trabajador, independiente de las ocho regresiones del uso manual y de los informes por bloques.

El plan almacena una copia pequeña de los coeficientes y del tiempo de vuelo antes de liberar. Tras confirmar el lanzamiento se reconstruye esa predicción exclusivamente con la copia, la fuerza y la geometría preparadas. No se elige un modelo nuevo después de observar la bala ni se fabrica una predicción a partir de la trayectoria nativa. Cuando el plan no tenía modelo, la predicción se conserva como ausente.

Por cada caso se almacenan puntos de la predicción y del recorrido nativo, contexto numérico, fase de calibración/evaluación, alcance limitado o inicial, fuerza prevista/real y viento/clima. La comparación de recorridos identifica su origen y nunca certifica puntería. Las fases posteriores se anexan únicamente cuando el observador independiente acredita su dueño y padre.

El registro se enlaza mediante el token del tiro a la ventana de vida y la partida. Los callbacks del controlador consultan el ensayo actual y se mantienen durante los cambios de bloque. Un resultado desconocido no se transforma en derrota; una notificación desconocida posterior tampoco borra una victoria o derrota ya confirmada.

## Reutilización y límites

La biblioteca manual lee el archivo sin escribirlo y utiliza solo muestras nativas atribuibles. Los cálculos previstos no entrenan la física. Se mantienen la separación por cuenta y episodio, las comprobaciones futuras y los límites de fuerza, viento y vuelo. Una familia truncada, múltiple, con continuación o que solo acredita el lanzamiento inicial no se presenta como un tiro ordinario completo.

El archivo es SQLite con transacciones atómicas, hasta 16 casos por modalidad y 816 globales por trabajador. Cada caso está limitado a 32 KiB, con hasta ocho reconstrucciones y 65 puntos por recorrido; se reserva espacio para el resultado posterior. Se impone un límite de 12 288 páginas, aproximadamente 48 MiB con el tamaño de página predeterminado. Las escrituras y la comparación se hacen después de liberar el tiro. La copia previa del modelo evita añadir miles de puntos a cada opción del planificador.

Solo se guardan campos numéricos y etiquetas cerradas. No se incluyen nombres, cuentas, chats, capturas, cookies, rutas del navegador ni comandos. El archivo de una cuenta no se publica en GitHub. Los fallos de archivo se muestran como un problema de guardado y no autorizan a repetir controles.

El archivo empieza a guardar los tiros confirmados de esta versión. No se atribuyen a los tiros antiguos predicciones que nunca se conservaron.

## Verificación de la entrega

Pasaron 730 pruebas de Python, siete suites de navegador y tres comprobaciones de ejecutables. Las pruebas incluyen privacidad de campos, separación de predicción y observación, ausencia explícita de modelo previo, duplicados, límites de retención, resultados desconocidos, fases verificadas, fallo de disco y reutilización de observaciones por la guía manual sin aprobar predicciones.

En la prueba del ejecutable 0.17.2 se guardaron cinco guías reales: dos de la primera sesión y tres de la segunda. Las cinco tenían copia de la predicción previa, recorrido nativo y ventana de vida registrada; ninguna se declaró aprobada por archivarse. No se registraron errores del archivo. Las bases ocupaban 40 960 y 49 152 bytes en esa captura de validación. Se comprobó visualmente el contador del panel y se detuvo después el entrenamiento para conservar el modo manual del usuario.
