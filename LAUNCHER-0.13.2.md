# DragonLab 0.13.2

Cierra versiones anteriores y abre DragonLab-Prueba.exe. En DragonBound pulsa Jugar → Ajustes → Entrenamiento automático → Continuo. También puedes abrir Entrenar-Continuo.cmd para iniciar el juego y el entrenador directamente. La prueba local entra automáticamente; la producción requiere una cuenta con acceso activo.

## Aprender con los datos existentes

Los perfiles actuales son el punto de partida. Cada salida propia nueva puede ampliar o comprobar la calibración; las propuestas necesitan tiros posteriores independientes para reemplazar ajustes. Repetir solo datos antiguos no aporta evidencia nueva. La memoria de acciones conserva hasta 512 configuraciones por carro, modalidad, rango de viento, dirección de viento, distancia y altura relativa. Requiere al menos dos observaciones compatibles antes de sugerir una configuración y reserva dos de cada tres decisiones al currículo de calibración. La fuerza siempre se vuelve a calcular con el Lab y el estado actual.

La recompensa de esa memoria es la cercanía del final nativo del proyectil al objetivo; no equivale a daño, una victoria o una política profesional. Los tiros para abrir terreno no se califican como aciertos. Los patrones de balas múltiples siguen separados del ajuste de bala única. No utiliza un modelo de IA grande ni un servicio de pago.

## Cada turno y decisiones

Se usa turn_number nativo, independiente del jugador activo, para reconocer cada oportunidad. Esto evita quedarse esperando si no se observó el turno rival o si al mismo jugador le tocan turnos seguidos. Se reserva una sola carga por turno antes de enviar Espacio; una reconexión no repite una carga ambigua.

Antes de cargar se actualizan posiciones, viento, clima, orientación y ángulo. Si no encuentra tiro directo, prueba otras modalidades y un paso corto de hasta 14 píxeles con terreno de apoyo. Si no avanza, puede probar el otro lado, también con apoyo comprobado. Se vuelve a leer la posición y se recalcula. Un impacto calculado lejos del propio carro y que avance hacia el objetivo puede usarse para abrir paso; una aproximación se identifica como tal. No se fuerza un tiro cercano peligroso ni se inventa una solución si el Lab no puede calcularla. En ese caso, espera el próximo turno y vuelve a intentar.

## Sesiones largas

Continuo no tiene el límite de tiros, partidas o duración de las sesiones acotadas. Intenta recuperar errores transitorios de conexión al navegador con espera progresiva. Si aparece la selección de servidores con Avatar Off visible, puede volver a entrar allí; no inicia sesión en DragonBound ni confirma avisos desconocidos.

Mientras juega en primer plano solicita a Windows mantener el sistema despierto, sin cambiar el plan de energía. Al pausar por foco/chat, reconectar o terminar libera esa solicitud. Esc, Detener, pausar la guía, cerrar sesión o cerrar el programa detienen el entrenador. Si interrumpes una carga, puede salir un tiro parcial. Tres fallos consecutivos de control detienen la sesión; una geometría sin tiro no se trata como un fallo de conexión.

El historial, la memoria de acciones y el registro de turnos tienen límites; los estados idénticos se escriben como máximo cada cinco segundos para reducir disco. Los archivos de calibración y estrategia se conservan entre sesiones. La prueba no los envía al servidor.

## Validación y límites

La prueba real, iniciada con una copia de las calibraciones existentes, registró cuatro tiros: Armor SS y tiro 1 en los turnos 2 y 3, seguido de Ice SS y tiro 2 en los turnos 1 y 4 de otra partida. Fuerzas Lab/reales: 208/207, 200/199, 320/320 y 180/179. La selección cambió de Armor a Ice y el modo continuo superó los límites de un tiro y una partida usados en la prueba. Un desplazamiento independiente confirmado fue de [902,55] a [916,53]. Las distancias de final al objetivo fueron 27.65, 17.69, 24.43 y 39.96 píxeles bajo condiciones distintas; no se afirma una mejora monotónica ni precisión perfecta.

Todavía no se ha completado una prueba de resistencia de 24 horas. La recuperación, los límites y la memoria tienen pruebas automatizadas, pero eso no certifica disponibilidad permanente, todos los climas, todos los vehículos ni nivel profesional. Requiere equipo encendido, conexión, cuenta del juego activa y el navegador en primer plano; al perder el foco espera sin enviar controles a otra ventana. GunBound World conserva sus perfiles y no está incluido en este entrenador autónomo.
