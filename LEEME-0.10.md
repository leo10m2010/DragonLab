# DragonLab 0.10

Abre DragonLab-0.10.exe y entra a una partida desde **Abrir juego**. Ctrl cambia al siguiente enemigo vivo; Q solicita un tiro con la fuerza recomendada. Cada pulsación dispara una vez, exige tu turno y el juego en primer plano y conserva tu ángulo. Ambos atajos se pueden cambiar en Ajustes. F8 conserva su función del juego.

## Mejoras

- **Nak:** fase subterránea ajustable desde continuaciones nativas comprobadas; marcas de entrada/salida; ángulos envueltos correctamente; SS atraviesa terreno y considera al primer jugador interceptado, incluido un aliado. La forma de colisión es una aproximación del cuerpo.
- **Kalsiddon:** distingue tiro 1 con dos misiles, tiro 2 con cuatro y SS con primera división en cuatro y segunda en ocho. La fuerza usa la trayectoria de la guía y una calibración propia por modalidad. Los recorridos observados de los misiles conservan sus caminos nativos, retardos y pausas de transformación. La predicción previa de los seguidores sigue siendo aproximada: no se presentan misiles simulados como mediciones reales.
- **Calibración automática:** perfiles por carro/tiro, comparación con muestras reservadas, suspensión al detectar cambios y ajustes provisionales claramente identificados cuando todavía faltan tiros. No se aplica una muestra de viento distinto como si fuera equivalente.
- **Confianza:** indica Calibrado, Salida calibrada, Aproximado, Faltan datos o Recalibrando. Una salida calibrada no garantiza un impacto exacto de proyectiles especiales.
- **Comparación:** la pantalla puede mostrar la diferencia del último tiro respecto al extremo de su recorrido nativo. Los registros quedan en revision-tiros.json; no se convierten automáticamente en calibraciones.
- **Detección:** conserva identidad/posición durante hasta 0,8 segundos de lecturas incompletas y marca el dato como antiguo. El autotiro espera una posición confirmada. Los jugadores muertos dejan de conservarse; las marcas fuera de pantalla incluyen a tu jugador.
- **Rendimiento:** Ligero reduce capturas; Normal ofrece mayor frecuencia; Auto adapta la frecuencia a la carga de CPU medida de DragonLab. El mapa oculto no captura imágenes.
- **UI:** ventana compacta, texto grande, líneas Menta/Azul y grosor ajustable, ajustes desplazables y controles redondeados.

Se observaron tus tiros de las tres modalidades de Kalsiddon. El tiro 2 tiene cinco muestras consistentes sin viento; los tiros 1 y SS tienen una cada uno y usan ajustes provisionales. Nak conserva cinco continuaciones subterráneas verificadas; su calibración de lanzamiento reciente queda separada del perfil anterior que mostró diferencias.

Siguen pendientes la validación de Kalsiddon con viento, la predicción completa de sus seguidores, pruebas más amplias de Nak SS/collisiones y rendimiento en equipos antiguos. GunBound World sigue pendiente. Al interrumpir una carga de autotiro, liberar Space o el ratón puede disparar la fuerza parcial acumulada.
