# Transferencia del aprendizaje a la guía manual

## Problema corregido

Los tiros nuevos ya se enviaban al libro de calibración manual, pero la guía no consultaba `aprendizaje-autonomo.json`. El libro global conservaba solo 48 muestras por modalidad y mezclaba cuentas y partidas con parámetros distintos. Por eso podía mantenerse en revisión aunque existieran secuencias coherentes en los datos nativos del entrenador.

## Nuevo flujo

`manual_learning.py` lee exclusivamente los archivos numéricos de aprendizaje de la carpeta del programa y de las dos sesiones independientes. Agrupa cada modalidad por episodio y fuente, sin sumar dos mitades de cuentas diferentes para fabricar una validación. Deduplica copias del mismo certificado.

Se ajusta una hipótesis con al menos cuatro lanzamientos nativos variados y se contrasta con al menos tres lanzamientos posteriores distintos. La alternativa de ventana local mantiene las comprobaciones más estrictas de 0.17.0. Solo se conservan fuerzas dentro de la intersección del rango de ajuste y el de comprobación, el viento comprobado y el menor horizonte futuro de vuelo. No se importan modelos guardados sin recalcular evidencia, muestras sintéticas, semillas, mecanismos especiales pendientes ni familias de balas múltiples como si fueran tiros ordinarios.

La biblioteca `perfiles-aprendidos.json` conserva hasta seis regímenes por modalidad. La aplicación actualiza las fuentes en segundo plano cada 30 segundos, con comprobación previa de cambios en los archivos. Un reinicio puede usar inmediatamente los certificados guardados. No se alteran los archivos originales del entrenador ni se mezclan DragonBound y GunBound World.

La guía aplica esos parámetros a su cálculo habitual, conservando detección, geometría nativa, selección de objetivo, clima, colisiones y atajos. El buscador y la vista previa del terreno respetan los límites del certificado; una fuerza fuera de su rango no puede autorizar Q. Un tiro manual atribuible que contradiga un régimen lo excluye en la partida actual. La biblioteca también registra lanzamientos normales del usuario y crea un certificado cuando reúne comprobaciones suficientes, sin abrir ni iniciar un entrenador.

## Alcance y límites

La primera revisión recuperó 11 modalidades comprobadas de los archivos existentes, no 11 carros completos. Un certificado histórico representa su régimen medido; no garantiza que los parámetros sigan iguales en cualquier partida futura. La observación manual puede invalidarlo. El catálogo informa modalidades pendientes incluso si acumularon disparos que no identifican correctamente el mecanismo.

SS suele disponer de menos muestras, y otras modalidades necesitan modelar túneles, múltiples orbes, satélites, transformaciones o variantes. Se conservan los motores especiales existentes, pero esta transferencia no los declara validados ni convierte un lanzamiento inicial en un recorrido completo aprendido. Las preferencias de estrategia de 0.17.0 siguen separadas de la calibración física; no sustituyen la fuerza calculada.

## Verificación

Las pruebas cubren separación por cuenta y episodio, comprobaciones futuras disjuntas, duplicados y contradicciones, rechazo de semillas y familias especiales, persistencia, fuentes ilegibles, aprendizaje con tiros manuales, invalidación en la partida actual, cambio de bala, límites del solver y catálogo de 51 modalidades sin crear una sesión de entrenamiento. La revisión numérica inicial reconstruyó 55 certificados en 11 modalidades a partir de las fuentes reales en aproximadamente 0,2 segundos. Esto comprueba transferencia y cálculo limitado, no una tasa de aciertos o victorias garantizada.

Pasaron 716 pruebas de Python, siete suites de navegador y tres comprobaciones de ejecutables. Se abrió el paquete 0.17.1 sobre los datos existentes: la captura estuvo conectada, sin error del motor ni de la biblioteca, con el entrenador detenido. Se comprobó visualmente Ajustes → Ver carros y balas aprendidas y sus estados. La disponibilidad de un ajuste en una partida concreta sigue dependiendo del viento y de la ventana de vuelo; la prueba visual del catálogo no es una validación de impactos de todas las modalidades.

Los contadores del catálogo indican observaciones conservadas en las fuentes actuales, no el total histórico de disparos. Las copias entre cuentas no se suman para aparentar más evidencia. Un conjunto grande repartido entre muchas partidas breves puede seguir careciendo de comprobaciones posteriores coherentes.
