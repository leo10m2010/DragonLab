# DragonboundGPT 0.1.21.0: novedades frente a 0.1.14.0

Revisión: 4 de noviembre de 2026. Comparación local con REA y lectura estática de los recursos distribuidos. No se ejecutó el original para provocar tiros. No se leyeron cuentas, cookies, contraseñas ni archivos de licencia.

## Versiones identificadas

| Archivo | Versión | Bytes | SHA-256 |
| --- | --- | ---: | --- |
| Ejecutable analizado anteriormente | 0.1.14.0 | 170.680.320 | `e11ec028464322651f61f24107ab6239be534bb683cf46bbe500752dccf36666` |
| `E:/db/DragonboundGPT/DragonboundGPT.exe` actual | 0.1.21.0 | 173.122.560 | `71fb0655ae1d1008fe2b6da51a441c636005a4cd3d8704c4bb5ca663fef5d889` |

El componente compilado actual está en la carpeta local versionada `0.1.21.0/9d96e04e967447069955d3698fc4dbc9`. Su ejecutable interno tiene 39.934.976 bytes y SHA-256 `b4d15c6de4eed697663a9f9ef824e9f4da19356b38dfe2cbe5980bc06bd65924`. REA confirma PE x64 sin metadatos CLI/CIL: no es una aplicación .NET que permita recuperar sus métodos mediante CIL.

## Cambios observados y alcance

| Área | Novedad respecto a la referencia | Qué permite concluir |
| --- | --- | --- |
| Grub bala 2 | El JavaScript añade reconocimiento específico de cuatro proyectiles con diferencias asimétricas de ángulo y velocidad. Requiere una salva completa coherente antes de escoger el lanzamiento de referencia. | Hay una corrección concreta del tratamiento de esta bala. No demuestra calibración completa de todos los carros. |
| Velocidad de las bolas de Grub | La nueva simulación expresa el desfase en velocidad directamente. La anterior lo convertía mediante una escala fija de fuerza. | Cambiar la calibración de fuerza ya no debería alterar accidentalmente la separación de velocidades de esta salva. Es una inferencia del cálculo distribuido. |
| Dirección y tiro de vuelta | El cálculo nuevo considera la dirección nativa del jugador y puede probar la dirección hacia el objetivo si la primera propuesta no alcanza una tolerancia de 35 unidades. Conserva excepciones para Boomer y determinados climas. | Cambió la elección entre direcciones; no se midió una mejora de puntería en partida. La tolerancia pertenece al original y no se traslada como precisión aprobada a DragonLab. |
| Drag | Nuevo módulo `cursor_guard`, documentación y constantes de protección temporal del cursor, con liberación por plazo, ESC, pérdida de foco y errores. | Declara protección frente al movimiento físico durante el arrastre. No se trazaron sus llamadas nativas ni se comprobó cada fallo. |
| Q y Ctrl | Nueva implementación documentada por sondeo al soltar, contexto de juego/chat, descarte de combinaciones, repetición y teclas pulsadas antes de comenzar. | La documentación específica indica que esas dos teclas no se reservan globalmente. El README general conserva una descripción anterior más amplia. |
| Guía que queda vacía | Nuevo control de disponibilidad de datos e invalidación de la caché al recuperarlos, incluso si la última firma balística completa no cambió. | Describe una corrección directamente relacionada con curvas que desaparecen tras una lectura incompleta. Falta medir su efecto en ejecución. |
| Viento | El JavaScript embebido conserva una lectura ausente como `null` y comprueba el tipo numérico. Añade una lectura del renderizador con límites y valores finitos. | Evita que una lectura ausente se convierta en viento cero en esas expresiones. No acredita todas las rutas de lectura. |
| Escenario ancho | Ajustes para el escenario nativo de 800 × 600, el lienzo ampliado y desplazamientos horizontales independientes. | Hay cambios de geometría para lectura y Drag; requieren validación por tamaño de ventana. |
| Pantallas y capturas | Nuevos textos y constantes para escoger el monitor que contiene mayor parte del juego y controlar visibilidad del HUD en capturas. | Evidencia de opciones y lógica declarada; no se probaron todos los monitores o grabadores. |
| Arranque y launcher | Documentación de pantalla ligera antes de importar el launcher, identidad estable de Windows y nuevos componentes de progreso/uso/recursos. | Hay cambios de estructura e interfaz. No se midieron memoria, CPU ni segundos de arranque. |

El HUD QML conservado y la hoja CSS web son **idénticos byte por byte** entre las dos muestras. Esto no incluye toda la interfaz del launcher, que tiene partes compiladas. Los recursos gráficos presentes en la instalación actual no pueden declararse nuevos solo porque la extracción antigua no los conservó.

## Ideas aplicadas y pendientes en DragonLab

- Corregido el desfase de velocidad de Grub 2 en el motor propio; cuatro pruebas verifican distintas calibraciones y ambas direcciones. Esto no aprueba automáticamente un perfil de juego ni habilita una bala especial sin datos propios.
- La lectura actual de DragonLab ya distingue números finitos de datos ausentes; no se sustituyó viento desconocido por cero.
- El entrenador conserva entradas dirigidas a cada navegador. La protección global del cursor del original no se traslada a las dos sesiones, porque podría interferir con el uso simultáneo del equipo.
- Continúa la integración propia de Armor 2 por tramo observado, DD con comprobaciones independientes y Nak 1 para abrir terreno. Los impactos de las dos ojivas, Thor, recorridos subterráneos y despliegues especiales necesitan sus propias mediciones antes de declararlos completos.
- La recuperación de guías tras datos incompletos y la geometría de ventanas son candidatos para nuevas pruebas de regresión. No se presentan como una mejora ya comprobada en partidas por esta inspección.

## Evidencia y límites

REA analizó una vez cada árbol JavaScript y comparó sus grafos. Ambos análisis completos excedieron el tamaño de transporte y se conservaron mediante referencias de evidencia; se exportaron sin repetirlos. La comparación cubre completamente esos dos árboles, pero muchos módulos minificados quedan sin emparejamiento semántico. Por ello, los recuentos de nodos añadidos/retirados no equivalen a funciones nuevas/eliminadas.

- JavaScript antiguo: `ev_a74581dca248cf05e6eed7378e69791535668262d155a155eed860ef5544560a`.
- JavaScript actual: `ev_1f66b70ed41b5610e07b07e99791ab84df6c73c26c6b3fac04d06da75c7329da`.
- Comparación: `ev_f487f94c218c450dfe3538d6ee7af2fe53865209c9ab0ee3f527b7642111399b`.
- Clasificación del componente compilado actual: `ev_e434f351e870b4dfdc2767f4a84685cb03ba1b73dba35bf780d4002f1532e3ac`.

El expediente local está en `work/rea-0121-evidence.json`; hashes de recursos, diferencias léxicas y observaciones de constantes están en `work/rea-0121/`. El informe `backend-report.md` de esa carpeta da los offsets de archivo de cada hallazgo nativo. Las ubicaciones léxicas del JavaScript corresponden a posiciones UTF-16 de Babel, no a offsets binarios.

Ghidra e IDA no están configurados y Hopper no está disponible en Windows. La búsqueda nativa de REA respondió `provider_unavailable`: las observaciones del componente compilado proceden de sus constantes, documentación y JavaScript embebido, no de una descompilación completa ni de una traza de ejecución. No hay evidencia suficiente en esta revisión para afirmar que se añadió una IA nueva, autonomía de 24 horas, mejores resultados medidos o calibración de todos los vehículos.
