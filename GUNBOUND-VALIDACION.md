# GunBound World · comprobación de lectura, 11 de octubre de 2026

La interfaz utiliza una sola pantalla y un único botón Jugar. La compatibilidad con GunBound World sigue siendo experimental y Q está desactivado.

Se observó una partida real en estado RESOLVING, turno 4: dos jugadores Armor, jugador local identificado, ángulo local 45°, viento 16 y transformación de cámara. Las posiciones observadas fueron (377, 1090) y (467, 1108). Se leyeron sus equipos, orientación, inclinación y estado de vida. La lectura se limita a datos de combate: no se leen credenciales ni almacenamiento de cuentas, ni se envían acciones al juego.

Correcciones: habilitar temporalmente el dominio de inspección para obtener referencias de listeners; localizar instancias del controlador de combate cuando sus funciones de clase no exponen una clausura local; usar los identificadores reales de jugadores; leer el ángulo local del controlador; interpretar shot1/shot2/ss; distinguir LOBBY, PLACEMENT y GAME_OVER de TURN/RESOLVING. El dominio de inspección se desactiva incluso si falla la búsqueda.

REA confirmó el objetivo abierto https://play.gunbound.world/ (Evidence ev_588750a11521ad5a4efcc2de6dcc913ea60281fe7bd99d459954af3021c2060a). Las posiciones y campos anteriores proceden de lecturas adicionales del adaptador local durante la partida; el inventario REA por sí solo no demuestra esos valores.

Pendiente: captura de trayectorias reales, terreno, climas y calibración de cada vehículo/tiro de este clon. No se ha validado precisión de impacto ni equivalencia física con DragonBound. La lectura de cámara se observó; todavía falta contrastar visualmente la superposición en distintos tamaños de ventana.
