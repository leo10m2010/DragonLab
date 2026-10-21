# DragonLab 0.14.3 · Menús y progreso medible

Cierra la versión anterior y abre DragonLab-Prueba.exe. Entrenar-Continuo.cmd inicia el aprendizaje. El panel está en Ajustes → Entrenamiento automático.

## Controles corregidos

Los botones y switches requieren una pulsación propia antes de ejecutar al soltar: arrastrar desde otro control ya no los activa. Los botones deshabilitados rechazan clics y teclado y salen del recorrido con Tab. Las activaciones por teclado detienen la propagación del evento. Los desplegables cierran su lista al deshabilitarse, rechazan elegir opciones deshabilitadas y permiten salir con Tab o Mayús+Tab. Su posición se limita al borde de pantalla.

El panel de aprendizaje mantiene Empezar, Detener y Duración fuera del área de desplazamiento. Su contenido puede desplazarse en pantallas pequeñas. Empezar y Duración se deshabilitan durante una sesión; Detener solo se habilita cuando hay una sesión activa. No se recalculan estados de controles que no han cambiado.

## Qué significa el porcentaje

Calibración de salida = modelos de lanzamiento validados / 51 modalidades: 17 carros visibles del catálogo de entrenamiento por tiro 1, 2 y SS. Los candidatos y modelos en recalibración no cuentan como validados. Disponible en el Lab tiene su propio porcentaje, calculado con sus perfiles activos. No son porcentajes de autonomía, porcentaje de impactos ni estimaciones de tiempo restante.

Al seleccionar un carro aparecen sus tres modalidades, los tiros posteriores comprobados de cada candidato (hasta 3/3) y los patrones especiales pendientes. Una salida inicial validada no certifica el recorrido completo de un proyectil especial o todos sus climas. Puntería y autonomía completa se muestran pendientes de evaluación; sus porcentajes permanecen sin definir.

Se mantienen los contadores de mediciones, tiros con experiencia, exploración y reemplazos del Lab con menor error de lanzamiento comprobado. El aprendizaje sigue independiente del solver del Lab y solo comparte mediciones reales confirmadas.

## Comprobación

201 pruebas aprobadas. Se verifican controles Tk nativos, clic sin pulsación previa, estado deshabilitado, propagación de teclado, cierre de desplegables, switches, creación del panel sin sesión y porcentajes sin inflar por candidatos o datos de otro juego. La herramienta de control visual de Windows no pudo iniciarse por un error de su entorno; no se afirma una inspección visual interactiva de todos los menús. Los paquetes se compilan y pasan la comprobación de arranque con motor integrado.
