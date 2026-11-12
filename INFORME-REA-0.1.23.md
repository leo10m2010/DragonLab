# Comparación estática de DragonboundGPT 0.1.21–0.1.23

## Identidad y alcance

Se compararon los artefactos instalados por el usuario, excluyendo BrowserData, licencia y credenciales. No se ejecutó el programa ni se modificó su protección. El MCP de REA no está disponible en esta sesión; el diagnóstico CLI indicó registro desalineado, una versión de Node inferior al requisito del paquete actual y ausencia de motores nativos Ghidra/IDA. No se reparó configuración ni se instalaron motores. Por ello esta revisión usa estructura PE, módulos de constantes y recursos distribuidos, con evidencia conservada localmente; no equivale a una decompilación funcional completa.

| Versión | Bytes del ejecutable | SHA-256 |
|---|---:|---|
| 0.1.21.0 | 39 934 976 | b4d15c6de4eed697663a9f9ef824e9f4da19356b38dfe2cbe5980bc06bd65924 |
| 0.1.22.0 | 40 019 968 | a46593c999f91714413ba3042084c7ac420b784d1f127fc0e87459936bf02540 |
| 0.1.23.0 | 40 047 616 | ba7c538234ebcfeaaba9003d09d8912f2ef25835af4ad8c880df25861af014a0 |

## Hallazgos observados

- En 0.1.22 aparecen el archivo `boomer-calibration-v1.json`, nuevos datos de calibración y referencias de un modelo aerodinámico de Boomer. Sus propias constantes distinguen una validación retrospectiva de una prueba prospectiva independiente. Esto no acredita precisión general ni todos los climas.
- En 0.1.23 aparece el módulo `windvision.games` y selección de DragonBound, iGunsFire y ShotBound. Estos dos últimos se identifican como experimentales. Son juegos nuevos en la selección, no evidencia de carros nuevos.
- Los recursos JavaScript de 0.1.22 y 0.1.23 son idénticos byte por byte. El catálogo inspeccionado en 0.1.21, 0.1.22 y 0.1.23 conserva los mismos 23 nombres/IDs, de 0 a 22. No se observó una ampliación en ese recurso.
- Fox, Knight, Dragon, Electrico y Dragon2 ya estaban reconocidos por los perfiles de DragonLab, pero el catálogo visible del aprendizaje solo mostraba 17 vehículos. La nueva interfaz manual expone también los especiales sin declarar calibradas sus balas.

La [guía oficial de DragonBound](https://dragonbound.net/guide/mobiles) enumera vehículos seleccionables y especiales, incluidas variantes estacionales de Barney. Esa página no establece sus IDs internos ni una fecha de alta. No se asignó Barney a Dragon2 ni se inventaron IDs nuevos sin una prueba nativa.

## Límites y reconstrucción propia

No se midió la latencia del otro programa en ejecución, por lo que esta revisión no demuestra por qué se siente más fluido ni permite prometer paridad. DragonLab optimizó su propio pipeline: cancelación de trabajos obsoletos, cola limitada, lectura manual más rápida y caché del dibujo. La precisión se contrastó con regresiones propias, sin copiar constantes de calibración retrospectiva como si fueran evidencia independiente de nuestro modelo.

La evidencia local está en `work/rea-0123/identities.json`, `resource-hashes.json`, `constant-deltas.json`, `focused-native-literals.json`, `javascript-token-delta.json` y `mobile-catalogs.json`. Contiene hashes, módulos, offsets y bloques distribuidos. Se mantienen como desconocidos los flujos nativos no decompilados, la precisión real de Boomer y cualquier catálogo diferente de un juego o cliente posterior.
