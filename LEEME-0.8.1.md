# DragonLab 0.8.1

Abre DragonLab-0.8.1.exe y entra a la partida desde el navegador conectado. Puedes dejar DragonLab minimizado: mantiene la detección y las marcas sobre el juego.

Pulsa y suelta Ctrl para pasar al siguiente enemigo vivo. Ahora funciona también mientras ajustas el ángulo con las flechas o mantienes la barra espaciadora. El cambio de objetivo usa solo Ctrl; F8 conserva su función dentro del juego. El encabezado sobre el juego muestra el objetivo elegido y cuántos enemigos vivos hay. Con un único enemigo no hay otro al que pasar.

El atajo utiliza los eventos del teclado y la ventana del navegador identificada por la captura. No necesita consultar continuamente todas las teclas, ni que la página informe que tiene el foco. Solo actúa en la ventana del juego con datos recientes. No bloquea ni envía teclas, ni registra su contenido. Ctrl+C y otras combinaciones con letras se descartan al soltar Ctrl.

Se redujo la carga de dibujo de recorridos observados: menos puntos de representación, conservando su extremo y los cambios nativos de dirección; estados repetidos reutilizan el recorrido. La vista previa toma una imagen cada tres segundos y deja de hacerlo al minimizar. Se elimina un dibujo duplicado por muestra. Estas reducciones no alteran el cálculo de fuerza ni sus mediciones de calibración.

El archivo ejecutable sigue ocupando aproximadamente 19 MB; el principal ahorro de esta versión está en la carga de trabajo. El rendimiento en equipos antiguos sigue pendiente de una prueba real.

Trico tiro 2 prioriza las tres bolas, pero sus órbitas siguen necesitando contraste real. Los vehículos sin suficientes mediciones siguen siendo aproximados. GunBound World sigue pendiente de validación. La aplicación no dispara automáticamente.
