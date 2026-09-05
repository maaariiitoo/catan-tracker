"""
El "diccionario" del tablero de Catan: qué vértices y aristas existen, y
qué casillas toca cada uno. Es geometría PURA -- no mira ningún píxel, solo
las 19 posiciones de centro de casilla ya calibradas -- así que es exacta
y no hace falta "detectarla" en cada partida, solo calcularla una vez.

El tablero de Catan es topológicamente un "hexágono de hexágonos" de radio
2 (1 casilla central + 6 en el primer anillo + 12 en el segundo = 19), una
figura muy estudiada en programación de rejillas hexagonales. Se usan
coordenadas axiales (q, r) estándar: https://www.redblobgames.com/grids/hexagons/

Cada casilla tiene 6 vértices (esquinas) y 6 aristas (lados). Un vértice
lo comparten 2 o 3 casillas; una arista, 1 o 2. En vez de derivar a mano
qué casillas comparten qué vértice/arista (fácil de equivocarse en los
bordes del tablero), se calculan las 6 esquinas de las 19 casillas por
separado (19*6 = 114 esquinas) y se agrupan las que caen en el mismo sitio
-- ese agrupamiento por posición ES la relación de qué casillas comparten
cada vértice, gratis y sin margen de error de índices.

Resultado esperado (y verificado en las pruebas): 54 vértices, 72 aristas
-- son los números de siempre en un tablero estándar de Catan.
"""

import math
from collections import defaultdict


# Las 19 casillas en coordenadas axiales (q, r): todas las que están a
# distancia <= 2 del centro. Se listan en el mismo orden fila por fila
# (3-4-5-4-3, de arriba a abajo y de izquierda a derecha) que usa
# vision/calibration.py, para poder emparejar 1 a 1 con la lista de
# casillas ya calibradas (screen_x, screen_y) sin ambigüedad.
def _generate_axial_order():
    rows = []
    for r in range(-2, 3):
        q_lo, q_hi = max(-2, -2 - r), min(2, 2 - r)
        rows.append([(q, r) for q in range(q_lo, q_hi + 1)])
    return [tile for row in rows for tile in row]


TILE_AXIAL = _generate_axial_order()
assert len(TILE_AXIAL) == 19, f"se esperaban 19 casillas, salieron {len(TILE_AXIAL)}"


# EL TABLERO DE 5-6 JUGADORES: 30 casillas en filas de 3-4-5-6-5-4-3.
#
# No es un hexagono mas grande. Uno de radio 3 tendria 37 en filas de
# 4-5-6-7-6-5-4, y este no quita el anillo de fuera: es otra forma, mas alta
# que ancha, con SIETE filas en vez de cinco.
#
# Las coordenadas no estan inventadas: son las que apunta el propio juego en
# las partidas grabadas de 5-6, comprobadas contra la base. Se dejan tal cual
# vienen (q de 0 a 5, r de 0 a 6) y solo se desplaza el origen para que el
# centro caiga cerca del (0,0), como en el de 19. Con `axial_to_pixel` las
# siete filas salen centradas en el mismo eje X -- comprobado fila a fila --
# que es lo que hace que la reticula valga para dibujar y para emparejar.
_FILAS_30 = {0: (3, 5), 1: (2, 5), 2: (1, 5), 3: (0, 5),
             4: (0, 4), 5: (0, 3), 6: (0, 2)}


def _generate_axial_order_30():
    orden = []
    for r in range(0, 7):
        lo, hi = _FILAS_30[r]
        orden.extend((q - 3, r - 3) for q in range(lo, hi + 1))
    return orden


TILE_AXIAL_30 = _generate_axial_order_30()
assert len(TILE_AXIAL_30) == 30, f"se esperaban 30, salieron {len(TILE_AXIAL_30)}"

# Los tableros que hay, por numero de casillas. Se pide por aqui y no se
# escribe `TILE_AXIAL` a pelo: durante semanas el 19 estuvo repetido en media
# docena de ficheros y el tablero grande no pasaba de la primera comprobacion.
TABLEROS = {19: TILE_AXIAL, 30: TILE_AXIAL_30}


def axial_de(cuantas):
    """La reticula del tablero de `cuantas` casillas, en orden fila a fila."""
    if cuantas not in TABLEROS:
        raise ValueError("no hay tablero de %d casillas; hay de %s"
                         % (cuantas, " y ".join(str(k) for k in sorted(TABLEROS))))
    return TABLEROS[cuantas]


def axial_to_pixel(q, r, size, origin=(0.0, 0.0)):
    """Centro en píxeles de la casilla (q,r), hexágonos 'pointy-top'
    (vértice arriba y abajo, como los del tablero real -- así es como
    encajan filas de distinto tamaño compartiendo el mismo eje X)."""
    ox, oy = origin
    x = size * (math.sqrt(3) * q + math.sqrt(3) / 2 * r)
    y = size * (1.5 * r)
    return (ox + x, oy + y)


def hex_corners(cx, cy, size):
    """Los 6 vértices de un hexágono 'pointy-top' centrado en (cx,cy),
    en orden (para poder recorrerlos y sacar las 6 aristas como pares
    consecutivos)."""
    return [
        (cx + size * math.cos(math.radians(60 * i - 30)),
         cy + size * math.sin(math.radians(60 * i - 30)))
        for i in range(6)
    ]


# La topología se calcula en el tablero IDEAL, donde las esquinas de dos
# casillas vecinas caen en el mismo punto exacto y agruparlas no tiene
# ningún margen de error. Esta tolerancia es solo para el error de coma
# flotante, no para el del tablero de verdad.
_MERGE_TOLERANCE = 1e-6


def _round_key(pt, tol=_MERGE_TOLERANCE):
    return (round(pt[0] / tol), round(pt[1] / tol))


class BoardGraph:
    """vertices: {vertex_id: {'xy': (x,y), 'tiles': [indices en tile_centers]}}
    edges:    {edge_id: {'xy': (mx,my), 'vertices': (va,vb), 'tiles': [...]}}
    tile_id aquí es el ÍNDICE (0-18) dentro de la lista tile_centers que se
    pasó a build_board_graph -- quien llama es responsable de mapearlo a su
    propio tile_id de base de datos."""

    def __init__(self, vertices, edges):
        self.vertices = vertices
        self.edges = edges

    def vertex_tiles(self, vertex_id):
        return self.vertices[vertex_id]["tiles"]

    def edge_tiles(self, edge_id):
        return self.edges[edge_id]["tiles"]


def _topologia_ideal(casillas=None):
    """Vértices y aristas del tablero PERFECTO, en coordenadas de tablero
    (radio 1). Aquí las esquinas compartidas caen en el mismo punto exacto,
    así que agruparlas da la topología correcta -- 54 vértices y 72 aristas
    en el tablero base -- sin ningún margen de error.

    `casillas` son las axiales del tablero; por defecto las 19 de siempre.
    Se puede pasar otro conjunto y sale su topología: no hay nada aquí que
    dependa de que sean 19 ni de la forma que tengan. Es lo que permite el
    tablero de 5-6 jugadores (30 casillas, filas 3-4-5-6-5-4-3) sin escribir
    su forma en ningún sitio -- basta con darle las casillas que apuntó el
    mod."""
    if casillas is None:
        casillas = TILE_AXIAL
    centros = [axial_to_pixel(q, r, 1.0) for (q, r) in casillas]
    grupos = defaultdict(list)
    esquinas_por_casilla = []
    for idx, (cx, cy) in enumerate(centros):
        claves = []
        for pt in hex_corners(cx, cy, 1.0):
            k = _round_key(pt)
            grupos[k].append((idx, pt))
            claves.append(k)
        esquinas_por_casilla.append(claves)

    clave_a_vid = {k: i for i, k in enumerate(grupos)}
    vertices = {}
    for k, entradas in grupos.items():
        vertices[clave_a_vid[k]] = {
            "xy": entradas[0][1],
            "tiles": sorted({t for t, _pt in entradas}),
        }

    aristas = defaultdict(set)
    for idx, claves in enumerate(esquinas_por_casilla):
        for i in range(6):
            va = clave_a_vid[claves[i]]
            vb = clave_a_vid[claves[(i + 1) % 6]]
            aristas[frozenset((va, vb))].add(idx)
    return vertices, aristas


_VERTICES_IDEALES, _ARISTAS_IDEALES = _topologia_ideal()

# La misma topologia para cada tablero, calculada una vez. `_topologia_ideal`
# ya sabia hacerlo con cualquier conjunto de casillas; lo que faltaba era que
# alguien se la pidiera para el de 30.
_TOPOLOGIAS = {19: (_VERTICES_IDEALES, _ARISTAS_IDEALES)}


def topologia_de(cuantas):
    """Los vertices y aristas ideales del tablero de `cuantas` casillas."""
    if cuantas not in _TOPOLOGIAS:
        _TOPOLOGIAS[cuantas] = _topologia_ideal(axial_de(cuantas))
    return _TOPOLOGIAS[cuantas]


def _homografia(origen, destino):
    """Transformación que lleva el tablero ideal al de la pantalla. Se
    ajusta con las 19 casillas a la vez (mínimos cuadrados), así que un
    centro mal detectado no descoloca el tablero entero."""
    import numpy as np
    a = np.array(origen, dtype=np.float64).reshape(-1, 1, 2)
    b = np.array(destino, dtype=np.float64).reshape(-1, 1, 2)
    try:
        import cv2
        h, _ = cv2.findHomography(a, b, method=0)
    except Exception:
        h = None
    if h is None:
        raise ValueError("no se pudo ajustar el tablero a la pantalla")
    return h


def _aplicar(h, punto):
    x, y = punto
    d = h[2, 0] * x + h[2, 1] * y + h[2, 2]
    if abs(d) < 1e-12:
        raise ValueError("transformación degenerada")
    return ((h[0, 0] * x + h[0, 1] * y + h[0, 2]) / d,
            (h[1, 0] * x + h[1, 1] * y + h[1, 2]) / d)


def build_board_graph(tile_centers, size):
    """tile_centers: 19 (x,y) en el MISMO orden que TILE_AXIAL (el que
    produce vision.calibration, fila por fila 3-4-5-4-3).
    size: se acepta por compatibilidad; ya no hace falta para la geometría,
    que sale de ajustar el tablero ideal a esos 19 centros.

    Antes esto calculaba las 6 esquinas de cada casilla con un radio fijo y
    agrupaba las que caían a menos de 3 px. En el tablero sintético salía
    perfecto (las esquinas coinciden al píxel) y la autoprueba pasaba, pero
    en el tablero REAL de Mario daba 114 vértices en vez de 54: NINGUNO
    compartido. Consecuencia directa: cada poblado se anotaba tocando una
    sola casilla en vez de sus dos o tres, así que la producción salía corta
    para todo el mundo.

    La causa no era la tolerancia. Medido sobre la partida 49: dos esquinas
    que son el mismo vértice se separan hasta 34 px (mediana 14) con un
    radio de 95, y dos vértices distintos llegan a estar a 33 px -- o sea
    que NO hay ninguna tolerancia que sirva. El juego dibuja el tablero en
    perspectiva, los hexágonos de arriba salen más pequeños que los de
    abajo, y un radio único no encaja en los 19.

    Así que la topología (qué vértices hay y qué casillas toca cada uno) se
    saca del tablero ideal, donde es exacta, y solo las POSICIONES se
    traen a la pantalla con la transformación que mejor ajusta las 19
    casillas medidas. La perspectiva deja de ser un problema: una homografía
    es justo lo que describe una vista en perspectiva de un plano."""
    # 19 o 30. El tablero de 5-6 usa la misma maquinaria: lo unico que cambia
    # son las casillas de las que se saca la topologia y la homografia.
    cuantas = len(tile_centers)
    if cuantas not in TABLEROS:
        raise ValueError("se esperaban 19 o 30 centros de casilla, llegaron %d"
                         % cuantas)
    vertices_ideales, aristas_ideales = topologia_de(cuantas)

    ideales = [axial_to_pixel(q, r, 1.0) for (q, r) in axial_de(cuantas)]
    h = _homografia(ideales, [tuple(float(c) for c in p) for p in tile_centers])

    # "ideal" es la posición en el tablero perfecto, en radios de hexágono.
    # Es exacta y siempre la misma, así que sirve de nombre permanente del
    # sitio: quien guarda edificios y carreteras la usa como clave y no
    # necesita deducirla otra vez de unas coordenadas de pantalla que llevan
    # el error de la calibración encima.
    vertices = {}
    for vid, v in vertices_ideales.items():
        vertices[vid] = {
            "xy": _aplicar(h, v["xy"]),
            "tiles": list(v["tiles"]),
            "ideal": (round(v["xy"][0], 3), round(v["xy"][1], 3)),
        }

    edges = {}
    for eid, (par, tiles) in enumerate(aristas_ideales.items()):
        va, vb = tuple(par)
        (xa, ya), (xb, yb) = vertices[va]["xy"], vertices[vb]["xy"]
        (ia, ja), (ib, jb) = vertices[va]["ideal"], vertices[vb]["ideal"]
        edges[eid] = {
            "xy": ((xa + xb) / 2, (ya + yb) / 2),
            "vertices": (va, vb),
            "tiles": sorted(tiles),
            "ideal": (round((ia + ib) / 2, 3), round((ja + jb) / 2, 3)),
        }
    return BoardGraph(vertices, edges)


if __name__ == "__main__":
    # Autoprueba: genera las 19 casillas ideales (sin distorsión, tablero
    # perfecto) y comprueba los invariantes conocidos de un tablero real
    # de Catan -- 54 vertices, 72 aristas, y que cada esquina de cada
    # casilla (19*6=114 en total) se reparte entre esos vertices/aristas
    # sin perderse ninguna.
    SIZE = 60.0
    centers = [axial_to_pixel(q, r, SIZE) for (q, r) in TILE_AXIAL]
    graph = build_board_graph(centers, SIZE)

    print(f"vertices: {len(graph.vertices)} (esperados 54)")
    print(f"aristas:  {len(graph.edges)} (esperados 72)")
    assert len(graph.vertices) == 54
    assert len(graph.edges) == 72

    total_vertex_touches = sum(len(v["tiles"]) for v in graph.vertices.values())
    print(f"suma de casillas-por-vertice: {total_vertex_touches} (esperado 114 = 19*6)")
    assert total_vertex_touches == 114

    total_edge_touches = sum(len(e["tiles"]) for e in graph.edges.values())
    print(f"suma de casillas-por-arista: {total_edge_touches} (esperado 114 = 19*6)")
    assert total_edge_touches == 114

    from collections import Counter
    vc = Counter(len(v["tiles"]) for v in graph.vertices.values())
    ec = Counter(len(e["tiles"]) for e in graph.edges.values())
    print(f"vertices por num. de casillas que tocan: {dict(vc)}")
    print(f"aristas por num. de casillas que tocan:  {dict(ec)}")

    print("\nOK: geometria del tablero verificada.")
