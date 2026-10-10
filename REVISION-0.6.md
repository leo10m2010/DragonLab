# Revisión 0.6

## Trico

El selector anterior minimizaba la distancia de una sola bola. El tiro 2 ahora busca toda la escala de fuerzas y prioriza el número de bolas próximas al objetivo, después la separación del grupo. Las doce mejores opciones se recalculan con mayor resolución. Se mantienen la colisión con el terreno y los efectos de Mirror/Tornado. El número de contactos es una estimación geométrica: no reproduce todavía cajas de daño, defensas ni cráteres producidos entre impactos.

La descripción oficial confirma una bola central y dos que orbitan en tiro 2: [guía de móviles](https://dragonbound.net/guia/moviles). No se afirma haber calibrado sus órbitas con nuevas partidas reales.

## Climas

La [guía oficial](https://dragonbound.net/guia/comojugar) describe Black Force como reducción de daño. La inspección previa del cliente mostró cambios de textura para black_at y no una etapa adicional de gravedad. Se muestra el aviso sin alterar la trayectoria por una hipótesis de mayor peso. No se calcula el porcentaje de reducción de daño.

## Objetivos

Numeración estable por identificador entre enemigos vivos; aliados y muertos quedan fuera del ciclo. Objetivo naranja con flecha, resto numerado. Ctrl solo, al soltar, pasa al siguiente y recalcula la fuerza. La lectura es pasiva, sin inyección de teclas ni registro de pulsaciones. Se descarta el ciclo si cambia la ventana, se usan combinaciones, el juego pierde foco o los datos caducan. Los enemigos fuera de pantalla se pueden seleccionar desde el menú, pero no llevan flecha fuera de pantalla.

## Verificación

Pruebas de selección con dos enemigos, un aliado y un muerto; vuelta al primero, combinaciones Ctrl, cambio de foco y desactivación. Caso controlado de Trico: tres contactos próximos prevalecen frente a uno exacto y dos fallidos. Curva idéntica al añadir clima negro. Etiquetas persistentes y eliminación al desaparecer el jugador/clima. Regresiones de cámara, terreno y 14 ángulos; 85 posiciones nativas y 28 transiciones de Tornado conservan los resultados previos (máximo 0,67 píxeles para Tornado, usando el arranque nativo de las balas). Un caso sintético de Trico alto calculó tres contactos en menos de un segundo, antes del refinamiento adicional. Estas verificaciones no equivalen a calibrar todos los vehículos con tiros reales.
