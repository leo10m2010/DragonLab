# DragonLab 0.17.1 · La práctica mejora tu guía manual

El Lab consulta automáticamente las mediciones de ambas sesiones de entrenamiento y conserva ajustes comprobados por carro y bala en `perfiles-aprendidos.json`. No hace falta ejecutar el entrenador para aprovecharlos. Los tiros normales que haces al jugar también se registran y pueden crear nuevos ajustes después de sus comprobaciones.

Los datos de distintas partidas y cuentas se ajustan por separado. Un modelo guardado no se copia como si fuera una prueba: se vuelven a revisar sus lanzamientos y las mediciones posteriores. Cada ajuste conserva los límites de fuerza, viento y tiempo de vuelo comprobados. La guía los respeta; un tiro propio incompatible deja de utilizar ese ajuste en la partida actual.

En Ajustes → Ver carros y balas aprendidas puedes consultar las 51 modalidades del catálogo. El estado distingue ajustes aprendidos, comprobaciones pendientes y mecanismos especiales. Haber usado una bala no demuestra que esté calibrada: SS con pocas muestras, proyectiles variables, túneles y grupos de balas siguen necesitando sus propios datos y modelos.

En la revisión inicial de los datos existentes se recuperaron 11 modalidades ordinarias: Armor 1, Ice 1 y 2, Aduka 1, Nak 1, Trico 1, Mage 1, Turtle 1, J.D 1 y 2, y Grub 1. Su disponibilidad depende del viento y del rango comprobado; no significa que esos carros completos o todos sus climas estén dominados.

Abre `DragonLab-Prueba.exe` y pulsa Jugar para usar la guía manual. El entrenamiento de dos cuentas continúa disponible por separado en `Entrenar-2-Sesiones.cmd`. La guía manual aprende de tus observaciones, sin iniciar un entrenador ni programar disparos por sí misma.

Paquete de prueba: `DragonLab-Prueba-0.17.1.zip`. Launcher: `DragonLab-Launcher-0.17.1.zip`. Código y preparación: `DragonLabCloud-Preparacion.zip`.
