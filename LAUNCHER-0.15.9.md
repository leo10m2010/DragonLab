# DragonLab 0.15.9 · Corrección del aprendizaje físico

La revisión detectó un error de modelo: los datos nativos encajan mucho mejor con componentes de viento redondeadas hacia abajo antes de aplicar su escala. El ajuste continuo anterior acumulaba errores en vuelos altos y dificultaba validar modelos.

- Ajusta el tipo de respuesta del viento usando mediciones, conserva el modo continuo para perfiles anteriores y para datos que lo justifiquen. Entrenador, validación y guía usan el mismo cálculo.
- Separa candidatos por partida: no promedia gravedad ni velocidad de salas con parámetros diferentes. Mantiene los datos históricos como hipótesis sin declararlos válidos en una partida nueva.
- Valida tiros posteriores con fuerzas variadas. En modelos de componentes aprendidos permite cambios de viento dentro de la cobertura medida sin cambiar los parámetros congelados; rechaza regiones no observadas.
- Mantiene un carro y una modalidad ordinaria como foco hasta conseguir comprobaciones, en lugar de repartir unos pocos tiros entre muchos perfiles. Puede usar otra bala si la modalidad foco no está disponible o hay una opción medida mejor.
- Renueva el presupuesto de calibración para una partida distinta, conservando el límite global de la sesión.
- La guía recibe el modo físico de cada ajuste validado y sigue validando sus propias mediciones antes de sustituir perfiles.

Reproducción histórica separada por episodios: 97 tiros posteriores, error medio de predicción de trayectoria 5,35 → 1,40 px; 13 → 0 casos sobre 12 px. Usa ángulos y duraciones nativos ya observados. No mide aciertos elegidos por el entrenador, terreno, daño ni victorias. Ver REVISION-APRENDIZAJE-0.15.9.md.

Mirror, Tornado, proyectiles múltiples y Teleport no quedan completos por este cambio. No se promete dominio autónomo de todos los carros.
