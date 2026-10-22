# DragonLab 0.15.6 · Bala 2 y DD coordinados

Incluye las correcciones de guía, estados, atajos e inicio de 0.15.4.

- Elige entre balas 1, 2 y SS disponibles usando sus perfiles propios y resultados medidos. Favorece un tiro normal si basta según el daño observado; conserva SS cuando no aporta una ventaja.
- Las decisiones de daño se limitan al mismo objetivo, partida y viento compatible. No usa daño de otro rival para decidir un DD.
- DD se considera para bala 1 o 2, con al menos cinco trayectorias evaluadas (80 % dentro de 20 px), tres ventanas de daño conocidas y vida enemiga conocida. Lo reserva si un tiro normal parece suficiente o si la oportunidad de terminar es baja. El límite de oportunidad es una heurística, no una garantía de daño doble.
- Comprueba el botón DD disponible y su selección real antes de cargar. Nunca selecciona Dual+ ni mezcla DD con SS. Si no hay DD disponible, conserva el tiro normal.
- Registra DD separado de las calibraciones y pruebas normales. El panel muestra la última modalidad y la razón de usar o reservar DD.

Si faltan datos comparables, no fuerza DD. Teleport y las modalidades sin modelo siguen pendientes de validación; esta revisión no demuestra por sí sola una mejora de victorias.

La conexión local de guía, Q, entrenador y selección de navegador usa HTTP directo exclusivamente a loopback. Evita inicializar HTTPS o usar proxies para acceder al navegador local; no modifica las verificaciones TLS del servidor. Incluye diagnóstico local de conexión sin disparar ni leer credenciales.
