# DragonLab 0.14.4 · Revisión de 226 tiros

Cierra la versión anterior y abre DragonLab-Prueba.exe. Entrenar-Continuo.cmd inicia el entrenador. Se conservan las mediciones y el panel de porcentajes de 0.14.3.

## Hallazgos observados

La sesión examinada tenía 226 tiros en 43 partidas. Entre sus últimos 120, 82 eran medición de clima/patrón, 16 usaban un modelo propio, 12 exploraban fuerzas y ángulos y 10 comprobaban modelos. Había tiros cercanos y fallos grandes; no demuestra mejora general. El porcentaje de cobertura de modelos de salida no es un porcentaje de aciertos.

El currículo podía preferir repetidamente una fuerza por la diferencia de un punto entre carga solicitada y medida. Algunos modelos históricos seguían siendo admitidos pese a no tener confirmación de las condiciones de la partida actual. Un cambio por clima podía marcar permanentemente una modalidad como patrón múltiple. La comprobación de salida no limitaba cuánto crecía el error durante un vuelo largo.

## Correcciones

Las fuerzas se agrupan con tolerancia y se priorizan las menos medidas. Al entrar en otra partida, se concentra primero un conjunto variado de observaciones de la modalidad inicial, sin dejar que las cargas antiguas saturen la selección. Los datos se identifican por partida.

Un modelo histórico necesita una observación simple de la partida actual que concuerde tanto en parámetros de salida como en recorrido, con viento/dirección próximos. Un ajuste local puede usar dos tiros variados para ajustar y dos posteriores distintos para comprobarse, siempre dentro de la misma partida y del rango de viento medido. Debe pasar error de salida y error de recorrido; no reemplaza la certificación general de cada carro. Si no pasa, sigue midiendo y no etiqueta la decisión como apuntada.

Las modificaciones temporales del clima se separan de grupos de balas, órbitas, ondas y fases posteriores. Se conserva la marca de mecanismo especial cuando existe evidencia de esos patrones. Los tiros especiales sin modelo completo siguen pendientes.

Los nuevos tiros simples guardan duración y datos para comprobar el error proyectado durante el vuelo. La comprobación del Lab rechaza candidatos cuyo error de trayectoria excede 12 píxeles en esa prueba, aunque el error de aceleración parezca pequeño. Los registros nuevos guardan también la separación mínima del recorrido nativo al objetivo inicial, separada de la distancia del punto final. Ninguna de esas distancias equivale por sí sola a un impacto confirmado o a daño.

Se corrigió además el resumen del porcentaje disponible en el Lab para que no aparezca como cero por mezclar dos fuentes de estado.

## Validación y límites

208 pruebas aprobadas, incluidas repetición de fuerzas por redondeo, modelo histórico fuera de contexto, ajuste local con mediciones posteriores separadas, rechazo de trayectoria alta incompatible, separación clima/patrón y comprobación de recorrido en el Lab. La versión conserva las correcciones de menús y porcentajes de 0.14.3. Falta contrastar en vivo esta política y demostrar mejora de impactos; no se declaran aprendidos todos los carros ni climas ni autonomía profesional.
