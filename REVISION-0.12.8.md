# DragonLab 0.12.8

El argumento `--open-game` permite abrir el navegador gestionado y conectar la captura al iniciar el auxiliar, sin pedir un segundo clic. Si ya existe una pestaña DragonBound en el puerto gestionado se activa esa pestaña. La distribución local evita varias instancias mediante un mutex de Windows. La distribución Cloud mantiene su comprobación de cuenta y una instancia independiente.

Si falta Chrome/Edge o no se puede iniciar, el auxiliar se muestra con un mensaje para corregirlo. No se cambian las calibraciones, preferencias ni la acción de tiro. El arranque de prueba no abre el juego. Versiones anteriores a 0.12.8 no participan en la protección de instancia: deben cerrarse antes de probar el nuevo flujo.
