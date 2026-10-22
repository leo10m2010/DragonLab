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
