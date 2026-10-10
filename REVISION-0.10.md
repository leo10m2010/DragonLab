# Revisión 0.10

## Evidencia

REA list_browser_targets seleccionó únicamente el origen https://dragonbound.net y la página del navegador conectado. Evidencia: ev_e074a6ce694c0e689a4bcf75977e9e13a087850e3877187dd564553756b3b7b6. La captura numérica pasiva posterior registró 1011 estados de la partida, sin ejecutar acciones del juego ni guardar nombres en la investigación. También se reutilizaron lecturas históricas de Shot2/ZotataPhysics y las continuaciones reales de Nak.

Kalsiddon: 731 comparaciones de posiciones de 36 proyectiles frente a las posiciones mostradas; máximo error numérico 3,24e-13. Se comprobaron familias 2, 4 y 4→8. La modalidad SS observada tuvo una segunda división 700 ms después de la primera; esto describe esa muestra y no certifica todos los escenarios. El tiro 2 tiene cinco lanzamientos a viento cero, escala 2,487187, offset 0,331905 y gravedad 396. RMS de velocidad 0,332346, error de muestra reservada máximo 0,980057. No se deduce respuesta al viento a partir de tiros sin viento.

Nak: cinco continuaciones verificadas por correspondencia de ID de proyectil, retardo y velocidad del primario; aceleración secundaria [0,-1440]. Se conservan las muestras recientes de lanzamiento después de la suspensión por deriva, incorporando del histórico únicamente las continuaciones. Los perfiles antiguos no se mezclan silenciosamente con los recientes. SS termina en la primera colisión corporal estimada y recalcula si cambia cualquier jugador que pueda bloquearlo. Se retira la antigua inversión especial de aceleración sin evidencia para el backshot.

## Implementación y verificación

Reconstrucción de pausas change.at/dur en caminos nativos. Seguimiento de IDs con caducidad 0,8 s y rechazo de autotiro cuando hero/target están antiguos. Cambio de ángulo normalizado a [-180,180]. Ajustes provisionales usan solo viento compatible; confianza separa calibración de salida y comportamiento especial.

Registro de diferencia de extremo entre predicción y camino nativo con fuente explícita native-shot-path. Se registra como revisión, no como muestra de calibración. Gobernador de frecuencia usa CPU del propio proceso con umbrales e histéresis; no mide GPU ni toda la carga del navegador. Colores, grosor, texto grande, modo compacto y desplazamiento de ajustes.

Pruebas nuevas: identidad conservada al faltar coordenadas, muerte/caducidad, Nak SS bloqueado por jugador anterior, familias reales Kalsiddon, pausa de transformación, confianza/provisional por viento. Regresiones: 85 posiciones previas, 28 transiciones Tornado, 14 casos de ángulos, mapas profundos, Nak subterráneo, feedback Slice/Drag simulado, cuatro jugadores reales/ocho sintéticos, treinta taps Ctrl, deriva y persistencia de calibración, navegador fixture y overlay sin foco. Interfaz normal, compacta con texto grande y ajustes renderizados e inspeccionados.

Estas pruebas no certifican impactos perfectos en todos los mapas, modalidades, vientos, clones o equipos. Los seguidores de Kalsiddon antes de disparar y la colisión corporal de Nak SS requieren contraste adicional; el autotiro conserva su validación en fixture y necesita más pruebas dentro del juego.
