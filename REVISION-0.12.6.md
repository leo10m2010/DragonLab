# DragonLab 0.12.6

Q avisa al programa mediante un canal local de eventos, independiente de la lectura del mapa. Se conserva la consulta anterior como respaldo y se eliminan duplicados. Las teclas personalizadas, el chat, las recargas y las pequeñas diferencias entre relojes están cubiertos por pruebas.

En Drag se usa la sensibilidad nueva de cada arrastre. La barra anterior no se acepta hasta que el juego confirma el movimiento enviado. Se exige la fuerza entera indicada por la guía y se suelta sin devolver el cursor: moverlo inmediatamente después de soltar podía modificar una carga que Chrome todavía estaba procesando. No hay repetición automática del intento. Slice mantiene lectura de carga; su precisión depende de la frecuencia de actualización del juego.

Cuando la roca bloquea una trayectoria posible, la marca conserva una fuerza de referencia y dice «TERRENO BLOQUEA». La línea termina en el terreno y Q no ejecuta esa referencia. Se leen las filas completas del mapa para conservar huecos y techos, en vez de tratar toda la roca como una superficie superior.

La búsqueda ordinaria utiliza una solución analítica que se comprueba con la misma simulación y colisiones. Los vehículos y climas especiales mantienen la búsqueda completa. En cinco repeticiones de escenarios controlados en esta PC, la mediana pasó de 40,81 a 4,84 ms para un tiro normal y de 38,59 a 6,36 ms para uno alto. Estas cifras no representan todos los carros ni garantizan impactos en modelos pendientes de calibración.

Validación: 21 pruebas de lógica/entrada y dos pruebas con Chrome real aislado. El evento navegador→Python llegó en aproximadamente 0,2–0,7 ms; esto mide el aviso, no el tiempo total hasta disparar. La confirmación de un tiro Q en la partida del usuario queda pendiente. Cada intento real guarda `ultimo-autotiro.json` para contrastar fuerza solicitada y confirmada sin registrar cuentas ni conversaciones.

Referencias investigadas: [CDP Runtime.addBinding](https://chromedevtools.github.io/devtools-protocol/tot/Runtime/#method-addBinding) y [SanjoSolutions/gunbound-aimbot](https://github.com/SanjoSolutions/gunbound-aimbot). No se instalaron controladores de entrada adicionales.
