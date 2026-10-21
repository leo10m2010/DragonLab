# DragonLab 0.14.0 · Aprender del juego

Cierra la versión anterior y abre DragonLab-Prueba.exe. Entrenar-Continuo.cmd abre DragonBound y comienza el aprendizaje; también puedes iniciarlo desde Ajustes → Aprender del juego. La prueba local entra automáticamente. Esc o Detener cancelan la sesión.

## Aprendizaje independiente

El entrenador ya no utiliza el cálculo de fuerza del Lab ni sus perfiles como profesor. Explora fuerzas y ángulos, mide sus propios proyectiles y ajusta un modelo numérico por carro y modalidad. Los datos antiguos solo aportan observaciones reales de lanzamiento; sus ajustes calculados no se importan. Un candidato requiere al menos cuatro observaciones variadas y tres comprobaciones posteriores independientes antes de utilizarse para apuntar. Si las mediciones posteriores contradicen un modelo, deja de usarlo. Los datos antiguos inconsistentes no impiden construir un candidato con mediciones propias nuevas.

El archivo aprendizaje-autonomo.json conserva muestras, candidatos, comprobaciones, experiencias y fases observadas. Los patrones múltiples y climas que alteran el recorrido no se dan por resueltos con una fórmula de bala única: siguen explorándose y solo se reutilizan experiencias reales compatibles repetidas. Esto no equivale a tener aprendidas todas sus mecánicas. Durante este modo la guía de fuerza del Lab se oculta y su cálculo se pausa; la captura y lectura de los tiros continúan. Al detenerlo vuelve la guía habitual.

## Control y continuidad

Reconoce turnos nativos y reserva una sola carga por oportunidad. Comprueba foco, chat, posiciones, viento, modalidad, ángulo y orientación. Aduka y Nak usan sus rangos nativos invertidos. El control observa el efecto de las flechas y cambia el sentido si detecta que una tecla mueve el ángulo al contrario. Siempre libera los controles al terminar o cancelar.

Continuo busca nuevas partidas 1v1 en Avatar Off y rota carros. Puede dar un paso corto con apoyo comprobado cuando observa un bloqueo. Espera al perder el foco o abrir el chat, intenta recuperar cortes de conexión y no confirma avisos desconocidos. No realiza compras ni escribe mensajes. Requiere equipo encendido, conexión y sesión del juego activa.

## Comprobación y límites

177 pruebas automatizadas aprobadas, incluidas independencia del cálculo del Lab, validación posterior, rechazo de modelos inconsistentes y cambio de sentido de las flechas. Prueba real con Aduka: rumbo propuesto y nativo 126° y 144°, ambos hacia la izquierda. Con Nak: 54° y 36°, ambos hacia la derecha, con ajuste real del ángulo. Las fuerzas solicitadas/medidas fueron 100/99 y 300/299 en Aduka; 100/99 y 360/360 en Nak.

Estas pruebas confirman el control y la medición, no precisión perfecta: los tiros de exploración pueden fallar bastante. Faltan cobertura amplia de vehículos, SS, vientos, climas y comportamientos secundarios y una prueba continua de 24 horas. GunBound World mantiene sus perfiles separados y todavía no participa en este entrenador. No necesita una IA grande ni un servicio de pago; este aprendizaje es local y no envía mediciones al servidor.
