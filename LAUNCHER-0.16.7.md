# DragonLab 0.16.7 · Corregir el tiro antes de acumular intentos

Esta versión corrige fallos identificados en las mediciones de la sesión prolongada de 0.16.6. Conserva las dos cuentas de prueba y los archivos de aprendizaje.

## Correcciones

- Al iniciar con dos sesiones, el launcher prepara la segunda ventana si está cerrada y espera de forma acotada a que ambas estén conectadas. No envía contraseñas ni realiza autenticaciones.

- **Nak y Aduka:** la definición nativa del cañón ya incluye que dispara hacia atrás. Se invertía de nuevo y desplazaba el origen aproximadamente 51 píxeles. Ahora usa directamente la orientación nativa. Seis tiros guardados, con distintas pendientes y direcciones, coinciden exactamente con el origen real después de corregirlo.
- **Calibración con información nueva:** se comparan las soluciones que ya cumplen terreno, clima, ángulo y fuerza. Se favorecen fuerzas suficientemente distintas de las ya observadas en la partida y cercanas al objetivo de investigación. La fuerza de investigación no se envía directamente: siempre se resuelve un tiro hacia el objetivo y se vuelve a verificar con el ángulo real.
- **Hipótesis por contexto:** si ninguna partida tiene muestras suficientes, ya no se juntan varias partidas incompletas para inventar un único régimen. Al pasar a otra partida se toma la referencia coherente más reciente disponible, sin cambiar el modelo durante sus comprobaciones independientes.

Los límites de fuerza/tiempo, comprobaciones de vuelo, exclusión de trayectorias parciales para DD, reserva de turno, caminata, controles por navegador y archivos separados continúan activos. No se redujeron los requisitos de validación para elevar los porcentajes.

## Qué demostraron las horas anteriores

La revisión de aproximadamente 11 horas encontró más de 2.700 tiros confirmados, pero solo alrededor del 7 % en evaluación dirigida y más de 3.400 turnos omitidos. En los últimos 100 resultados guardados por cuenta había 14 y 22 victorias respectivamente. Esos resultados son una ventana limitada, no el total histórico.

El vuelo de algunos modelos sí mejoraba: en Nak había aproximadamente 1,09 píxeles de error de predicción de vuelo frente a 10,83 del modelo de referencia, pero el error de origen anulaba esa mejora al apuntar. Más horas no corregían esa transformación del cañón.

Ver `REVISION-ESTANCAMIENTO-0.16.7.md` para evidencia, límites y comparación posterior. La nueva versión todavía necesita evaluación en partidas; no se declara una mejora de victorias por haber superado pruebas controladas.

## Usar

Abre `DragonLab-Prueba.exe`. Para las dos sesiones, conserva sus Chrome y usa `Entrenar-2-Sesiones.cmd`. El plazo es de 24 horas desde el nuevo inicio; Detener cancela las dos sesiones. Deja el programa, los navegadores y la PC encendidos y con conexión.

Distribución de prueba: `DragonLab-Prueba-0.16.7.zip`. Launcher: `DragonLab-Launcher-0.16.7.zip`. Preparación y código: `DragonLabCloud-Preparacion.zip`.
