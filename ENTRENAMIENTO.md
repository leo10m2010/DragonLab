# DragonLab 0.16.3 · Drag con fuerza confirmada

El entrenador prefiere arrastrar dentro de su pestaña, con controles separados para cada cuenta. Comprueba espacio libre antes de empezar, lee la sensibilidad asignada al pulsar y espera movimiento nativo nuevo antes de aceptar la fuerza. Slice se conserva como respaldo previo a la carga; una tentativa iniciada no se repite. Se guardan método y duración de carga para comparar con los registros nuevos de Slice. Ver LAUNCHER-0.16.3.md.

# DragonLab 0.16.2 · Disponibilidad, modalidades y clima

SS se excluye mientras el juego lo muestra en recarga, incluso si queda seleccionado. La disponibilidad se vuelve a comprobar antes de cargar y el ángulo aprendido se guarda por modalidad. Se conservan las alternativas de bala 1/2 en el mismo turno y los mecanismos especiales no se certifican sin observaciones propias.

Las continuaciones necesitan identidad de origen; los efectos de clima no desactivan las balas normales. Se conservan las observaciones históricas ambiguas sin tratarlas como prueba. Los recorridos nativos de Mirror/Tornado distinguen cruces completos de parciales. Se puede intentar salir de una columna cercana mediante los pasos seguros disponibles, con recálculo posterior.

Si no existe una acción calculable después de comprobar las modalidades, se puede pasar el turno explícitamente con el botón real. Los controles se comprueban de nuevo antes de cada clic, los avisos durante un tiro pausan entradas y la penalización conocida de retirada se registra y espera. Ver LAUNCHER-0.16.2.md; no se ha demostrado que todas las retiradas anteriores fueran por inactividad ni que todos los climas estén resueltos.

# DragonLab 0.16.1 · Dos trabajadores y origen de lanzamiento

Un solo launcher puede dirigir dos cuentas de prueba mediante navegadores, pestañas y directorios de mediciones independientes. Usa «Partidas: 2» o `Entrenar-2-Sesiones.cmd`. Los eventos llevan procedencia y pasan primero al libro de su trabajador; el Lab compartido solo incorpora observaciones reales con identidad separada. Detener cancela ambos; Esc dentro de un juego cancela ese trabajador. Ver LAUNCHER-0.16.1.md.

El origen del entrenador usa ahora la geometría nativa del cañón por bala, con posición, pendiente y orientación recientes. Se calcula de nuevo después de movimiento y ajuste de ángulo; los registros comparan origen planeado y observado. Las comprobaciones de fuerza, clima, colisiones y excavación se conservan. El perfil del segundo navegador usa una ruta absoluta comprobada para evitar el aviso de Chrome.

# DragonLab 0.16.0 · Sesiones largas y excavación

La opción predeterminada es ahora «24 h», con plazo real que incluye pausas y reconexiones. Los límites anteriores de 20/40 tiros, seis partidas y 15 minutos siguen disponibles como pruebas cortas. La sesión larga guarda bloques de evaluación separados y continúa; conserva contexto de validación, experiencia de armas, presupuestos de clima/excavación y la reserva del turno para evitar repetir cargas ambiguas.

La excavación de balas normales 1/2 de Armor, Ice, Mage y Trico usa exclusivamente el perfil de esa modalidad, con dos comprobaciones de vuelo independientes en la partida y fuerzas variadas. No depende de haber aprobado la puntería contra el rival. Recalcula el primer impacto en el ángulo real y exige fuerza dentro del rango comprobado, separación de carros y un máximo de tres intentos por perfil y partida. Una excavación pendiente o fallida limita repetir ese punto. Las observaciones de terreno no se convierten en aciertos.

El panel distingue tiempo restante, bloque actual y tiros totales. Los avisos desconocidos y el chat pausan controles; al recuperar la conexión no se recarga el juego ni se repite el turno reservado. Requiere equipo y navegador abiertos. Ver LAUNCHER-0.16.0.md: habilitar una sesión de 24 horas no certifica haber completado una prueba real de esa duración ni demuestra mejora de victorias.

Las secciones siguientes documentan versiones anteriores.

# DragonLab 0.15.9 · Aprendizaje de la física

Se corrige el modelo del viento con evidencia histórica separada y se concentra la práctica. Ver REVISION-APRENDIZAJE-0.15.9.md para resultados y límites de la comprobación.

# DragonLab 0.15.8 · Controles y evidencia

Confirma controles nativos y vuelve a comprobar el objetivo antes de cargar. Mantiene el presupuesto de movimiento al reconectar y exige comprobaciones compatibles con el viento actual antes de validar modelos. Ver LAUNCHER-0.15.8.md.

# DragonLab 0.15.7 · Turnos y armas

Ver LAUNCHER-0.15.7.md para el análisis de la sesión y los cambios. El movimiento comparte presupuesto entre balas; la selección puede usar daño provisional sin certificar puntería. Los ensayos de clima son finitos, separados y sin DD.

# DragonLab 0.15.6 · Conexión local unificada

Corrige el fallo del ejecutable al inicializar HTTPS para una conexión local HTTP. Conserva toda la selección de bala 2/DD y la coordinación de controles anteriores.

# DragonLab 0.15.5 · Selección de armas e ítems

Bala 2 participa con su perfil propio. DD se reserva para oportunidades de terminar un objetivo con precisión y daño medidos, usando datos de la misma partida, rival y viento compatible. La última acción y la razón del ítem aparecen en el panel.

# DragonLab 0.15.4 · Inicio de sesión del juego

Espera la carga conocida del perfil hasta 60 segundos; los avisos desconocidos siguen deteniendo el entrenamiento. Incluye la coordinación de controles de 0.15.3.

# DragonLab 0.15.3 · Asistencia y entrenador coordinados

Cambiar de modo cancela solicitudes pendientes e invalida cálculos anteriores. Q no se mezcla con el entrenamiento; al detenerlo vuelve la guía con un cálculo nuevo. Escape cancela ambas formas de control. Las mediciones conservan sus validaciones independientes.

# DragonLab 0.15.2 · Corrección de salida y estados

El launcher refleja el estado del entrenador. La calibración adaptativa puede ajustar la ganancia de fuerza con una salida nativa compatible; recalcula las colisiones y nunca modifica una evaluación congelada. Revisa turnos cada 100 ms y reintenta modalidades si cambia posición o viento. Teleport continúa pendiente de medición específica.

# DragonLab 0.15.1 · Retroceso, terreno y Camaleón

Cierra la versión anterior y abre Comprobar-Punteria.cmd. Mantiene el juego adaptativo, entrada en segundo plano y límites de 20 o 40 tiros, seis partidas y 15 minutos. Detener cancela desde el panel.

## Retroceder ante un bloqueo

Se corrigieron dos errores del movimiento. Primero, antes se prefería caminar hacia el objetivo incluso si el cañón estaba bloqueado; ahora se comparan las dos direcciones con suelo disponible y se prioriza retroceder ante terreno bloqueado. Se simula una posición y pendiente aproximadas para ordenar los pasos, pero tras caminar se leen posición y ángulo reales y se calcula de nuevo antes de cargar. Sigue habiendo un máximo de dos pasos por preparación y se exige tiempo suficiente.

Segundo, la comprobación antigua aceptaba puntos sólidos dentro de una pared como si fueran suelo. Ahora exige la frontera entre aire y terreno. Rechaza paredes y huecos donde no hay una superficie compatible. Esto no garantiza escalar cualquier pendiente ni salir de cualquier cráter.

El cálculo de la bala ahora localiza el primer choque antes de revisar los climas. Un clima situado después de ese choque no bloquea por sí solo la recuperación de posición. Un clima desconocido antes del impacto sí impide tratar ese recorrido como conocido.

## Abrir paso

Se añadió una recuperación experimental de terreno para bala 1 de Armor, Ice, Mage y Trico, con un modelo congelado comprobado en la partida. Tras no poder obtener un tiro directo mediante el movimiento disponible, puede reutilizar una trayectoria calculada cuyo primer impacto sea la obstrucción. No usa una fuerza arbitraria.

Exige avance hacia el objetivo, separaciones mínimas de 90 píxeles respecto al propio carro y aliados conocidos, y 70 píxeles horizontales respecto al propio carro. Son filtros conservadores de la política, no radios de explosión calibrados ni garantía de evitar daño o caída. Lightning y los mecanismos especiales no se habilitan para excavar sin comprobación propia. No usa DD para abrir paso.

Los intentos se guardan separados de la evaluación de aciertos. Se comprueba después si el punto previsto quedó sin terreno durante la ventana observada; esto no equivale a confirmar un impacto directo ni a demostrar que ya existe un camino transitable. Los tiros de abrir paso tampoco se reutilizan como experiencias de ataque acertado.

## Camaleón / Randomizer

La guía oficial indica que bala 1, bala 2 y SS usan proyectiles aleatorios de otros móviles: https://dragonbound.net/guia/moviles

Se conservan los datos históricos, pero sus ajustes mezclados ya no se usan ni cuentan como salida calibrada. Las observaciones nuevas atribuidas se separan por identificador del proyectil y se marcan como identificadas después de disparar. No se ha comprobado una señal fiable que revele el proyectil antes de liberar el tiro. Por eso no se autoselecciona Camaleón ni se muestra una fuerza precisa basada en un supuesto perfil fijo. Se mantiene el juego manual y el registro de variantes. Los nombres Camaleon y Chameleon se reconocen como Randomizer.

## Tiempos y diagnóstico

entrenamiento-estado.json guarda planning_ms (tiempo del planificador, incluidas comparaciones de posición) y attempt_ms (duración del intento, con lecturas y controles). Un tiro confirmado incluye además preparación previa a la carga. El panel muestra el cálculo del último intento, causas de omisión, pasos y aperturas de terreno observadas. No se presenta el tiempo de carga o espera de turno como tiempo de cálculo.

En el registro examinado de 0.15.0 había dos turnos completamente omitidos y seis modalidades rechazadas: cuatro rechazos por clima desconocido y dos por falta de modelo, sin errores de control en esa lectura. No significa que todos los turnos perdidos tengan esa misma causa.

## Validación y límites

267 pruebas Python aprobadas. Hay regresiones para un cañón bloqueado que puede despejarse retrocediendo, clima posterior a una pared, rechazo de pared como suelo, borde sin apoyo, excavación con modelo comprobado, separación de recuperación frente a precisión y aislamiento de variantes del Camaleón. Cuatro suites de navegador y comprobaciones de los ejecutables.

Las recuperaciones nuevas se comprobaron con escenarios reproducibles; todavía falta observar el retroceso y la apertura de terreno en una partida real equivalente a la captura. No se declara resuelto todo clima, todos los carros, todos los turnos ni autonomía profesional. SS/DD siguen condicionados a datos propios; minimizar la ventana y ocho cuentas simultáneas no están certificados.

Distribución local: DragonLab-Prueba-0.15.1.zip. Preparación Cloud: DragonLab-Launcher-0.15.1.zip; requiere configurar los servicios. No publiques claves privadas, sesiones ni mediciones personales.

---

# DragonLab 0.15.0 · Selección adaptativa de carro y modalidad

Cierra la versión anterior y abre Comprobar-Punteria.cmd. El inicio automático del producto ahora usa Juego adaptativo, en segundo plano y con límites de 20 o 40 tiros, seis partidas y 15 minutos. Detener cancela la sesión. La evaluación fija de Armor 1 sigue disponible mediante la API interna objective=evaluation; no se ha eliminado el control de referencia.

## Decisiones por carro y bala

El entrenador puede seleccionar entre bala 1, bala 2 y SS disponibles. Si no puede preparar un tiro, marca esa modalidad como rechazada e intenta otra en el mismo turno antes de abandonarlo. Una recarga o un selector que no confirma SS no autoriza a disparar una bala distinta como si fuera SS. Las cargas liberadas o ambiguas mantienen su reserva de turno para impedir duplicados.

Cada combinación carro/modalidad tiene su propio modelo provisional, comprobaciones posteriores, copia fija de evaluación e informe evaluacion-CARRO-N.json. No copia los coeficientes de Armor a Ice, Nak u otro carro. Solo elige carros con datos aplicables; los patrones múltiples o mecanismos especiales sin un modelo completo siguen pendientes. Al terminar una partida puede elegir otro carro compatible, dando oportunidad a los menos utilizados. No elige Random para fingir cobertura.

La elección favorece modelos aplicables y, cuando hay suficientes ventanas observadas de vida, el daño medido. El daño útil se limita a la vida/escudo restante conocido; si una bala normal puede acabar con el objetivo, evita favorecer SS solo por su daño sobrante. Sigue siendo una política basada en mediciones y reglas, no un agente de aprendizaje por refuerzo profesional ni una garantía de ganar.

## Menos turnos desperdiciados

Primero intenta una solución con el ángulo actual, evitando ajustes innecesarios. Al orientar espera la confirmación real del carro hasta 0,6 segundos y libera la tecla al confirmar, cancelar o cambiar de turno. Si una flecha no modifica el ángulo, ese fallo de preparación permite probar otra modalidad antes de cargar. Las animaciones iniciales siguen esperando sin consumir un intento. Movimiento, carga, foco virtual, pausa por chat y límites de tiempo conservan sus comprobaciones.

Las modalidades rechazadas se contabilizan aparte de los turnos completamente omitidos. evaluacion-adaptativa.json muestra ambas cifras y sus causas; la interfaz conserva métricas de proximidad, vida, partidas y pasos que recuperan una trayectoria. Una causa desconocida de clima no se resuelve disparando una fuerza arbitraria: ese clima necesita su modelo y tiros de comprobación.

## DD

DD usa exclusivamente el botón real .ItemBtn.itemDual, distingue Dual+ y Teleport, y exige que el juego confirme la clase visual Pressed antes de cargar. No compra ítems. No combina DD con SS ni con otro ítem activo.

La política automática solo propone DD en una modalidad normal con evaluación fija, al menos cinco trayectorias medibles, 80% cercanas, tres ventanas con daño y suficiente vida restante para justificar otro disparo. Si no hay DD disponible sigue con el tiro normal; si una selección intentada no se confirma, no carga. Los tiros con ítem se guardan aparte y no validan ni recalibran el perfil normal. El uso de DD queda condicionado a esta evidencia; no se fuerza para completar un contador.

## Evidencia y límites

259 pruebas Python aprobadas. Cuatro suites de navegador, incluyendo aislamiento de entrada y lectura de los botones DD/Dual+. Ambos ejecutables se compilan y comprueban por separado. En el ensayo de desarrollo se eligió Lightning y se confirmaron tres tiros: bala 1, bala 2 y otra bala 1. Hubo un turno omitido tras rechazar condiciones de clima/modelo. La sesión terminó por Esc, con resultado de partida desconocido; no demuestra mejora de victorias. SS y DD no se ejecutaron en ese ensayo y requieren validación real adicional.

La mejora es la selección y el control, con aprendizaje y evaluación separados por perfil. No significa que estén calibrados todos los carros, SS, climas o ítems. La autonomía estratégica completa y las ocho cuentas simultáneas siguen pendientes. Minimizar toda la ventana tampoco está certificado.

Distribución local: DragonLab-Prueba-0.15.0.zip. Preparación de producto con servidor: DragonLab-Launcher-0.15.0.zip; requiere configurar antes los servicios Cloud. No publiques sesiones, claves privadas ni mediciones personales.

---

# DragonLab 0.14.7 · Segundo plano y diagnóstico

Abre Comprobar-Punteria.cmd para abrir el juego e iniciar la prueba limitada de Armor tiro 1. En el panel puedes elegir Segundo plano o Juego al frente antes de empezar. Segundo plano es el valor inicial del producto; las sesiones internas antiguas conservan su comportamiento al frente si no solicitan el modo nuevo.

## Segundo plano

El entrenador envía los controles a la pestaña concreta mediante el navegador, sin teclado global ni mover el cursor. Usa el foco virtual del protocolo de Chrome para mantener activa la página del juego sin pedir traerla al frente. Al cerrar la conexión se desactiva ese foco virtual. No llama funciones del juego para disparar ni modifica sus variables de partida. La apertura inicial del navegador puede mostrar la ventana; el entrenamiento posterior no pide activarla.

El chat sigue pausando la sesión y el botón Detener funciona desde el panel aunque el juego no esté visible. Esc detiene desde la propia pestaña del juego; no es un atajo global cuando estás en otra aplicación. Una pausa por chat o una reconexión conserva el límite de duración y no autoriza a repetir una carga en el mismo turno. Cerrar el navegador detiene o agota la sesión; no se asegura funcionamiento de 24 horas.

En un primer ensayo real sin foco virtual, las teclas llegaron pero el juego no cambió el ángulo. Esa variante no se considera funcional. La corrección añade la función experimental Emulation.setFocusEmulationEnabled del navegador. Las pruebas de navegador comprueban que una pestaña inicialmente sin foco recibe su tecla, otra pestaña no la recibe y conserva su foco. En la versión ejecutable se observaron cuatro disparos confirmados, sin errores de control, mientras otra pestaña permanecía seleccionada durante los tiros posteriores. La sesión llevaba dos partidas iniciadas y una derrota confirmada; no demuestra mejora de victorias. Minimizar toda la ventana y suspender pestañas siguen pendientes de comprobación.

Referencia del protocolo: https://github.com/ChromeDevTools/devtools-protocol/blob/master/pdl/domains/Emulation.pdl

## Diagnóstico y movimiento

Las omisiones guardan códigos separados: falta de modelo, patrón especial sin comprobar, clima sin comprobar, viento sin medir o fuera del ajuste, terreno bloqueado, falta de ángulo, suelo inseguro y presupuesto de calibración agotado. El panel muestra los motivos y cuántos pasos terminaron encontrando una trayectoria. Cada paso registra posición inicial/final, turno y resultado del recálculo; encontrar trayectoria no equivale a acertar.

Se conserva el máximo de dos pasos cortos sobre suelo seguro y con tiempo suficiente. Las animaciones o movimientos todavía activos al principio de un turno ya no consumen ese turno ni cuentan como fallo de control: espera y vuelve a leer antes de cargar. Las cargas liberadas o ambiguas mantienen su reserva de turno para impedir duplicados.

Un bloqueo entre procesos impide dos entrenadores sobre la misma pestaña y dos escritores sobre el mismo directorio de datos. Una segunda sesión rechazada no sobreescribe el informe de la primera. Las ocho cuentas simultáneas siguen pendientes: necesitan sesiones y datos separados, coordinación del aprendizaje y pruebas graduales de carga.

## Validación y alcance

244 pruebas Python aprobadas. Cuatro suites de navegador para atajos, controles CDP, clima y entrada en segundo plano. Se mantienen las comprobaciones futuras de modelos y la comparación del ajuste candidato con la referencia; no se declaran mejoras por acumular tiros. La prueba sigue limitada a Armor tiro 1; no es un agente estratégico profesional y no hay mejora de victorias demostrada.

Los datos se conservan en el directorio local de calibraciones. entrenamiento-estado.json incluye modo, errores, pasos y evaluación. evaluacion-punteria.json conserva las omisiones y sus códigos. Tras aplicar el paquete final se observaron dos disparos nuevos sin errores, con otra pestaña seleccionada antes de comenzar el ajuste: el primero cambió el ángulo de 12 a 54 grados y confirmó fuerza 247; el segundo mantuvo el ángulo y confirmó otra carga 247. Esto verifica ajuste y disparo en ese ensayo de segundo plano; no demuestra una mejora de precisión. También se corrigió el inicio en frío: espera a que cargue la sesión y la entrada a Avatar Off, en vez de detenerse por no encontrarla de inmediato.

Distribución de prueba: DragonLab-Prueba-0.14.7.zip. Preparación Cloud: DragonLab-Launcher-0.14.7.zip; requiere configurar previamente los servicios. No publiques claves privadas, sesiones ni mediciones personales.

---

# DragonLab 0.14.6 · Buscar posición cuando falta ángulo

Cierra la versión anterior y abre Comprobar-Punteria.cmd para iniciar el juego con la prueba automática activada. Abrir solo DragonLab-Prueba.exe prepara la guía; no inicia por sí solo el entrenador.

Cuando existe una hipótesis física y no se encuentra ángulo o recorrido libre, la prueba intenta hasta dos pasos de 14 píxeles. Cada paso exige soporte de terreno cercano, al menos ocho segundos disponibles y el mismo turno. Se vuelve a orientar, leer la posición y calcular después de caminar. Si un lado no avanza, se prueba otro lado con suelo seguro. Las teclas se liberan al terminar, cancelar o cambiar de turno.

El fallo anterior ocurría porque la evaluación lanzaba NoAim antes de alcanzar la rama de movimiento del entrenador. La recuperación ahora recibe explícitamente si el fallo permite buscar otra posición. Un clima desconocido, un patrón múltiple o la falta de modelo no se intentan resolver caminando. Sin una solución tras dos pasos, se omite el tiro; no se envía una carga arbitraria. No garantiza salir de todo hueco ni encontrar ángulo desde cualquier terreno.

Se mantienen los límites y las métricas separadas de 0.14.5: Armor tiro 1, calibración provisional, evaluación con copia fija del modelo, ventanas observadas de vida y resultados confirmados. No se declara aprendizaje estratégico completo ni mejora de victorias sin mediciones. Ocho cuentas simultáneas siguen pendientes; no se ha activado un control compartido entre cuentas.

Validación: 234 pruebas Python aprobadas, incluidas recuperación de ángulo, recálculo tras movimiento, falta de suelo, turno corto, cambio de turno, dirección atascada y máximo de dos pasos. Estas pruebas verifican el control; la eficacia de reposicionamiento necesita contraste en una partida real.

Distribución local: DragonLab-Prueba-0.14.6.zip. Preparación para servidor: DragonLab-Launcher-0.14.6.zip; requiere configurar los servicios Cloud. No publicar claves privadas ni sesiones de cuentas.

---

# DragonLab 0.14.5 · Prueba de puntería medible

Abre DragonLab-Prueba.exe. Para iniciar directamente la comprobación, usa Comprobar-Punteria.cmd. Cierra primero la ventana de la versión anterior: el launcher permite una sola instancia. Se conservan las mediciones anteriores.

## Qué cambia

El botón de aprendizaje inicia una prueba limitada de Armor tiro 1, de hasta 20 o 40 tiros, seis partidas y 15 minutos. Ya no inicia exploración indefinida de todos los carros. Esc detiene la sesión; se respetan foco, chat y turno, sin repetir una carga en el mismo turno.

La calibración intenta dirigir tiros con hipótesis provisionales calculadas de mediciones reales. Un ajuste local necesita observaciones posteriores distintas antes de pasar a evaluación. La evaluación usa una copia fija del modelo. Si falta una solución por viento, clima, terreno o geometría, se omite ese turno; seis omisiones terminan la prueba. No se usa una carga arbitraria como sustituto.

El panel separa tiros de calibración, tiros dirigidos de evaluación, distancia al objetivo, bajadas observadas de vida/escudo y resultados confirmados de partidas. Un resultado desconocido no cuenta como derrota. La bajada de vida durante la ventana del tiro no se presenta como impacto directo confirmado. Los porcentajes de cobertura siguen separados de precisión y autonomía.

Se guarda evaluacion-punteria.json y partidas-observadas.json junto al archivo de calibraciones. Cada ejecución conserva sus resultados actuales; estos dos informes se reemplazan al iniciar otra prueba. Las mediciones históricas del aprendiz se mantienen. Solo se aprueba una prueba con al menos diez recorridos medibles, 80% a 20 píxeles o menos, mediana de 15 píxeles o menos, cinco ventanas de vida conocidas y bajada en al menos el 60%. Esa aprobación no significa autonomía completa.

Cuando existe un modelo anterior comparable, ambos modelos se contrastan con los mismos tiros nuevos. No se declara una mejora de predicción antes de diez comparaciones independientes y una reducción de error de al menos el 10%.

## Fallos corregidos

- La velocidad nativa de salida ya no se expone como fuerza de la barra.
- La atribución comprueba el origen del disparo contra la posición al soltar la carga, permitiendo una caída posterior en un cráter. Rechaza modalidad incorrecta, tiros antiguos y familias ajenas.
- La conexión de control evita volver a copiar todo el terreno al preparar o confirmar cada carga; amplía la ventana de confirmación sin repetir el disparo.
- El ajuste provisional local se utiliza para dirigir la siguiente calibración, sin contarlo como evaluación ni validarse con sus propios datos de ajuste.

## Evidencia y límites

228 pruebas de código aprobadas. Dos ensayos reales iniciales no reunieron tiros dirigidos suficientes: uno registró siete tiros de calibración; el segundo, uno. No hay mejora de victorias demostrada. La prueba termina con datos insuficientes en estos casos y no muestra un porcentaje inventado de autonomía.

Esta versión corrige el controlador y la forma de evaluar. No convierte todavía el calibrador en un agente profesional que aprende estrategia, movimiento y victorias. Mirror, Tornado y los mecanismos especiales de otros carros siguen necesitando modelos y comprobaciones propios. Los perfiles de GunBound World siguen separados.

## Qué publicar

Para distribuir una prueba local: DragonLab-Prueba-0.14.5.zip. Para preparar el producto con tu servidor: DragonLab-Launcher-0.14.5.zip, configurando primero los servicios descritos en la documentación del proyecto. El launcher de producción no sustituye la configuración de Supabase ni el despliegue del servidor. No publiques claves privadas, sesiones ni archivos de mediciones personales.

---

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

---

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

---

# DragonLab 0.14.2 · Aprendizaje comprobable y conexión con el Lab

Cierra la versión anterior y abre DragonLab-Prueba.exe. Entrenar-Continuo.cmd inicia DragonBound y el aprendizaje. Esc o Detener cancelan los controles.

## Qué cambia

El entrenamiento anterior rotaba carros muy pronto: sus últimos 120 tiros registrados eran de exploración o medición, sin decisiones apuntadas con un modelo propio. Acumular tiros no demostraba mejora de puntería.

Ahora concentra hasta tres partidas en un carro antes de rotarlo, prioriza una modalidad pendiente y mantiene la elevación durante bloques de seis mediciones. Cuando dispone de una modalidad ordinaria validada, reserva dos de cada tres decisiones a reutilizarla y una a ampliar las modalidades pendientes. No genera una solución si el modelo no cubre el viento, el clima o un mecanismo especial.

Sin clima activo ni patrón múltiple, puede interpolar una fuerza entre dos tiros reales comparables de la misma partida: uno corto y otro largo. Exige viento/dirección, origen, lado, elevación y altura final próximos; no extrapola fuera de lo medido. El resultado se identifica como aproximado y se mide de nuevo. Los modelos generales continúan requiriendo comprobaciones futuras.

## El Lab recibe las mediciones

Los eventos de tiros propios confirmados también llegan al libro de calibración del Lab. Su validador mantiene candidatos separados: requiere tres tiros posteriores diversos, límites de error y una mejora del error respecto al ajuste existente antes de reemplazarlo. Conserva el ajuste previo para recuperación. Los grupos de proyectiles se almacenan como patrones y no se convierten en una bala única por conveniencia. Un tiro rival, una predicción o una salida no confirmada no obtiene crédito de calibración.

Esta comunicación es de mediciones reales hacia el Lab: el entrenador sigue sin pedirle fuerzas ni utilizar sus perfiles como profesor. No se promocionan retrospectivamente las mediciones antiguas del entrenador como si acabaran de validarse. Se conservan sus archivos. La sincronización de producción mantiene las reglas de consentimiento existentes; la prueba local no envía datos al servidor.

## Progreso visible

Ajustes → Aprender del juego muestra mediciones, modelos básicos, tiros con experiencia, tiros de exploración, perfiles del Lab y reemplazos con mejora comprobada del error de lanzamiento. entrenamiento-estado.json conserva el mismo resumen. Los contadores de casos son acotados y los casos anteriores sin etiqueta se clasifican como exploración, sin inventar decisiones aprendidas.

Un modelo de lanzamiento validado no significa que todos sus climas, impactos o proyectiles secundarios estén dominados. El informe no declara mejora global de puntería; faltan comparaciones amplias de tiros nuevos en condiciones equivalentes. Tampoco se ha certificado juego profesional o continuidad de 24 horas.

## Verificación

190 pruebas automatizadas aprobadas. Incluyen compartir observaciones confirmadas, rechazar otro jugador, no duplicar mediciones, exigir comprobación futura, conservar y reemplazar perfiles con evidencia de mejora, currículo concentrado, interpolación acotada y rechazo de viento/clima/patrón incompatibles. Esta revisión aún necesita contraste ampliado de la política nueva en partidas reales. GunBound World mantiene sus perfiles separados y no está incluido en este entrenador.

---

# DragonLab 0.14.1 · Continuidad y turnos cortos

Cierra la versión anterior y abre DragonLab-Prueba.exe. Entrenar-Continuo.cmd abre DragonBound e inicia el entrenamiento independiente. Esc o Detener lo cancelan.

## Correcciones

El entrenador lee turn_time y start_turn_time nativos para estimar los segundos disponibles. Reserva margen para cargar y confirmar la fuerza, limita el ajuste de ángulo cuando queda poco tiempo y evita desplazamientos opcionales en turnos cortos. Vuelve a comprobar el reloj antes de cargar. Si el reloj no está disponible, utiliza un presupuesto conservador y mantiene la comprobación de turno.

Un turno vencido o una salida de proyectil no confirmada conservan la reserva de una acción por turno y permiten continuar en el siguiente. No se usan tiros sin atribución confirmada para aprender. Los fallos de control se reinician al cambiar de partida. Tres fallos reales consecutivos dentro de la partida todavía detienen el entrenador; el aviso ahora incluye la última causa y entrenamiento-estado.json conserva hasta 64 incidencias con tipo, turno y motivo.

## Comprobación

183 pruebas automatizadas aprobadas. Prueba real de código fuente con Armor en una partida cuyo turn_time nativo era 10: tiros en turnos 2 y 4, fuerzas solicitadas/medidas 300/299 y 360/359, ajustes nativos 13→54° y 54→39°. La sesión terminó voluntariamente tras esos dos tiros, sin error. Esto comprueba esa partida concreta; no equivale a una prueba de 24 horas.

El registro anterior mostró 23 tiros en seis partidas antes del corte por tres fallos; no conservaba las causas individuales y por tanto no permite afirmar cuál fue el desencadenante original. El nuevo registro evita perder esa información.

## Aprendizaje

Se mantiene el aprendizaje independiente de 0.14.0: explora y mide lanzamientos reales, exige comprobaciones posteriores y no utiliza las fuerzas del Lab como profesor. Al principio puede fallar. No están aprendidos todos los vehículos, climas ni proyectiles secundarios. GunBound World conserva sus perfiles separados y no forma parte del entrenador. Las mediciones autónomas son locales y no se envían al servidor.

---

# DragonLab 0.14.0 · Aprender del juego

Cierra la versión anterior y abre DragonLab-Prueba.exe. Entrenar-Continuo.cmd abre DragonBound y comienza el aprendizaje; también puedes iniciarlo desde Ajustes → Aprender del juego. La prueba local entra automáticamente. Esc o Detener cancelan la sesión.

## Aprendizaje independiente

El entrenador ya no utiliza el cálculo de fuerza del Lab ni sus perfiles como profesor. Explora fuerzas y ángulos, mide sus propios proyectiles y ajusta un modelo numérico por carro y modalidad. Los datos antiguos solo aportan observaciones reales de lanzamiento; sus ajustes calculados no se importan. Un candidato requiere al menos cuatro observaciones variadas y tres comprobaciones posteriores independientes antes de utilizarse para apuntar. Si las mediciones posteriores contradicen un modelo, deja de usarlo. Los datos antiguos inconsistentes no impiden construir un candidato con mediciones propias nuevas.

El archivo aprendizaje-autonomo.json conserva muestras, candidatos, comprobaciones, experiencias y fases observadas. Los patrones múltiples y climas que alteran el recorrido no se dan por resueltos con una fórmula de bala única: siguen explorándose y solo se reutilizan experiencias reales compatibles repetidas. Esto no equivale a tener aprendidas todas sus mecánicas. Durante este modo la guía de fuerza del Lab se oculta y su cálculo se pausa; la captura y lectura de los tiros continúan. Al detenerlo vuelve la guía habitual.

## Control y continuidad

Reconoce turnos nativos y reserva una sola carga por oportunidad. Comprueba foco, chat, posiciones, viento, modalidad, ángulo y orientación. Aduka y Nak usan sus rangos nativos invertidos. El control observa el efecto de las flechas y cambia el sentido si detecta que una tecla mueve el ángulo al contrario. Siempre libera los controles al terminar o cancelar.

Continuo busca nuevas partidas 1v1 en Avatar Off y rota carros. Puede dar un paso corto con apoyo comprobado cuando observa un bloqueo. Espera al perder el foco o abrir el chat, intenta recuperar cortes de conexión y no confirma avisos desconocidos. No realiza compras ni escribe mensajes. Requiere equipo encendido, conexión y sesión del juego activa.

## Comprobación y límites

177 pruebas automatizadas aprobadas, incluidas independencia del cálculo del Lab, validación posterior, rechazo de modelos inconsistentes y cambio de sentido de las flechas. Prueba real con Aduka: rumbo propuesto y nativo 126° y 144°, ambos hacia la izquierda. Con Nak: 54° y 36°, ambos hacia la derecha, con ajuste real del ángulo. Las fuerzas solicitadas/medidas fueron 100/99 y 300/299 en Aduka; 100/99 y 360/360 en Nak.

Estas pruebas confirman el control y la medición, no precisión perfecta: los tiros de exploración pueden fallar bastante. Faltan cobertura amplia de vehículos, SS, vientos, climas y comportamientos secundarios y una prueba continua de 24 horas. GunBound World mantiene sus perfiles separados y todavía no participa en este entrenador. No necesita una IA grande ni un servicio de pago; este aprendizaje es local y no envía mediciones al servidor.

---

Las secciones siguientes documentan versiones anteriores; la 0.14.0 sustituye el profesor del Lab por el aprendizaje independiente descrito arriba.

# Historial de entrenamiento hasta 0.13.2

## Control de turnos y memoria persistente

La 0.13.2 sustituye consumed por un registro acotado de (partida, jugador, turn_number). El contador se lee explícitamente desde el juego; no se infiere de viento o del jugador activo. Una reserva antes de cargar impide repetir una carga ambigua tras un corte. Un número nuevo autoriza un intento aunque no se haya observado el turno rival. Al pasar por el lobby se inicia un registro nuevo para la próxima partida. Los errores transitorios de transporte reconstruyen la conexión con espera progresiva, sin robar el foco repetidamente.

La selección intenta otras modalidades antes de dar por agotado el turno. Un desplazamiento corto requiere apoyo continuo en el terreno, se confirma con la posición nativa y obliga a recalcular. Las aproximaciones y tiros para abrir paso usan una fuerza calculada por el Lab y un final que progresa hacia el objetivo, a al menos 60 píxeles del carro. Si no hay una acción calculable, espera un nuevo turno; no promete disparar en una geometría imposible.

estrategia-entrenamiento.json conserva hasta 512 configuraciones. La memoria agrupa modalidad/ángulo por carro, magnitud y dirección de viento, rango, lado y altura relativa. Aprende con cercanía de final observado al objetivo y necesita dos observaciones compatibles antes de recomendar. Una de cada tres decisiones puede reutilizar esa experiencia, conservando el resto para medir/comprobar calibraciones. Esto es memoria numérica de alcance, no aprendizaje de victorias ni daños; no representa una IA profesional. Los perfiles actuales se conservan y el libro exige mediciones futuras para activar cambios.

Validación real 0.13.2: cuatro tiros entre Armor e Ice, turnos [2,3] y [1,4] en partidas distintas, fuerzas Lab/reales 208/207, 200/199, 320/320 y 180/179. Desplazamiento confirmado [902,55] → [916,53]. No se ha hecho una prueba de 24 horas. La memoria persistente, recuperación de conexión, turnos consecutivos, ausencia de duplicados y movimiento con apoyo tienen pruebas automatizadas. Consulte LAUNCHER-0.13.2.md para las condiciones de uso continuo.

## Corrección de ángulo y juego guiado

La 0.13.0 liberaba las flechas tras 45 ms y no exigía movimiento antes de disparar. La 0.13.1 mantiene la flecha con lectura de retorno, libera en todos los caminos de salida y utiliza minang/maxang y truang_min/truang_max nativos. Los límites se aplican antes de elegir el tiro. Si no hay lectura o la flecha no produce movimiento y no se está en un límite conocido, no carga Espacio.

La aplicación entrega una copia de sus Settings al entrenador mediante la cola de la interfaz, conservando objetivo, calibraciones, terreno, viento y clima. El entrenador usa core.solve, orienta al objetivo, propone un ángulo dentro del rango del carro y vuelve a solicitar Settings tras moverlo. La fuerza se recalcula para el ángulo real; las fuerzas fijas del currículo ya no sustituyen ese cálculo en el modo guiado de la aplicación. Los tiros bloqueados esperan otra oportunidad.

Continuo es la duración predeterminada de la interfaz y desactiva los topes de tiros, búsquedas y duración. Sigue entre partidas, conserva un historial acotado a 120 entradas en memoria y disco y espera si falta foco o el chat está abierto. Esc/Detener y el cierre siguen cancelando. No se instala una tarea del sistema ni se inicia el entrenamiento al abrir el programa.

Verificación real: cambio 16° → 55°, seguido de fuerza Lab 207 y fuerza leída 206. Una sesión guiada posterior registró tres tiros y una búsqueda de nueva partida, con fuerzas Lab 204/205/98 y fuerzas reales 204/204/97. Se guardaron distancias de final al objetivo de 86.51, 139.04 y 18.05 píxeles bajo condiciones distintas; no prueban una mejora progresiva ni puntería perfecta. Las observaciones alimentan el libro existente y requieren comprobación posterior antes de activar ajustes.

## Funcionamiento

Comprobación adicional 0.13.1: bajada nativa de 54° a 47° para un objetivo de 46° (tolerancia de un grado). El modo Continuo sobrepasó los topes de un tiro y 30 segundos usados en la prueba, buscó una nueva partida, registró dos tiros y se detuvo con Esc. Fuerzas Lab/reales: 144/143 y 138/137; finales nativos a 3.38 y 5.24 píxeles del objetivo, en esos dos casos concretos. Pruebas Python: 143 aprobadas.

El usuario inicia una sesión desde Ajustes. El entrenador verifica la pestaña DragonBound y el servidor 8 Avatar Off, el foco y el chat. Usa los botones visibles de selección de carro y búsqueda 1v1; no compra objetos ni escribe mensajes. Solo confirma automáticamente el aviso conocido de ausencia. Otros avisos detienen la sesión.

El planificador prioriza modalidades que necesitan comprobación independiente, modalidades sin ajuste y cobertura de viento. Propone ángulos variados y el modo guiado busca una solución viable dentro del rango nativo. El currículo conserva fuerzas de prueba para herramientas de medición sin proveedor del Lab, pero la aplicación toma la fuerza del motor de puntería. Las fuerzas registradas son las observadas en la barra.

El control pasa a Slice, ajusta el ángulo con flechas y carga Espacio. Comprueba turno, posición, viento y modalidad durante la carga. Libera las teclas en la salida normal, cancelación o error; no repite una carga fallida dentro del mismo turno. Tres fallos consecutivos terminan la sesión. Los errores y límites se conservan en entrenamiento-estado.json junto al libro local.

Antes de cargar se registran las balas existentes; una observación nueva debe superar la atribución de jugador, posición, tiempo y fuerza. Los patrones de salida múltiple se guardan con sus lanzamientos numéricos y no se promueven como una sola bala. Las observaciones ordinarias siguen pasando por el ajuste y comprobación independiente existentes. No se separan datos de entrenamiento y validación por un simple cambio de etiqueta: los candidatos necesitan tiros posteriores.

## Comprobación realizada

- Selección visible de Armor desde el lobby y búsqueda automática 1v1.
- Primer tiro propio confirmado a fuerza 99 y segundo a 299, modalidades 1 y 2 respectivamente.
- La segunda observación contenía tres proyectiles; conserva el grupo sin introducirlo en el ajuste de bala única.
- La pérdida de foco detuvo la sesión sin seguir buscando partidas.
- Una segunda sesión completó su límite de tres tiros: SS a 99 con viento 5, tiro 2 a 99 con viento 6 y tiro 1 a 359 con viento 7. Eligió carro, buscó una partida y terminó sin error. Para el último tiro se solicitó un ángulo de 75°; el ángulo efectivo depende del límite del carro y se conserva en la salida observada.
- Pruebas automatizadas cubren selección de modalidad disponible, prioridad de comprobación, variedad de fuerza, rotación de carros, límite de sesión, rechazo de otro servidor, cancelación y grupos de balas.

## Límites pendientes

La comprobación inicial no equivale a una calibración exhaustiva. Deben medirse y contrastarse todos los carros, SS, mecanismos secundarios, climas y vientos disponibles. No fuerza condiciones del servidor ni genera mediciones sintéticas. Los modelos específicos de proyectiles múltiples y transformaciones necesitan validación propia. GunBound World no está incluido en esta primera fase autónoma.
