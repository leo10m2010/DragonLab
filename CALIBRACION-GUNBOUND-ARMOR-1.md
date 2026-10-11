# Armor tiro 1 · GunBound World

Se utilizaron 8 tiros propios observados en la partida, entre fuerza 25 y 100 y viento 0 a 18. Se excluyó un tiro que utilizó Teleport y no se mezclaron tiros del bot. Las observaciones de callbacks fueron temporales y se restauraron al terminar; no se enviaron controles al juego.

El ajuste de salida pasó validación independiente al retirar una muestra cada vez: error máximo de velocidad 0.058 y de aceleración 4.605. La conversión de fuerza observada es 9.200075 por unidad; desplazamiento de velocidad -0.062106, gravedad ajustada 391.065246 y factor de viento 3.814801. La trayectoria reproduce el primer paso observado de 50 ms sin aplicar aceleración de un paso completo antes de salir.

Dos trayectorias reales se reprodujeron con máximos de 0.80 y 4.43 píxeles de error antes del impacto, usando su fuerza, ángulo y viento registrados. No se incluyó el punto terminal de impacto porque el terreno ajusta ese punto.

Se corrigieron: viento girado 90° incorrectamente, ángulo local sin compensar inclinación y selección de un controlador destruido que aún conservaba datos. Armor utiliza la salida observada del cliente, ángulo 52° y radio 33, girada con el cuerpo y la orientación.

Alcance: Armor tiro 1, viento observado 0–18. Tiro 2, SS, otros vehículos, terreno, climas y autotiro todavía no están calibrados ni validados para este clon. El perfil de salida queda incorporado al programa; no implica precisión perfecta ni certificación de cada impacto.

Comprobación posterior en una partida nueva con 0.12.15: dos jugadores y barra detectados, guía realmente visible, fuerza calculada 54 en el estado de diagnóstico y 59 en la captura posterior mientras cambiaban los datos de la partida. No hubo errores del motor.
