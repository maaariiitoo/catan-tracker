# -*- coding: utf-8 -*-
"""Las reglas del Catan como filtro de lo que la red cree ver.

De donde sale esto. Midiendo el tablero acumulado de una partida apartada
(red/acumular.py) se ve que 21 de las 25 piezas inventadas son CARRETERAS, y
que no son dudas: sacan 31 votos de mediana. Subir el liston no las quita
(a confianza 0.99 y 40 votos se van todas, pero se llevan por delante 17
piezas buenas). O sea que no es un problema de umbral.

Lo que la red no sabe es que el Catan tiene reglas. Un recorte de una arista
contiene tambien los dos vertices de sus extremos, asi que una carretera de
al lado se cuela dentro; para la red son pixeles de carretera en el sitio
que le han preguntado, y contesta que si. Nada en su entrada le dice que ahi
no PUEDE haber una carretera.

Las cuatro reglas que se usan aqui son invariantes del juego, no heuristicas:

1. Toda carretera toca, por uno de sus dos extremos, otra pieza propia
   (carretera o edificio). Al construirla es obligatorio, y las piezas no
   desaparecen nunca -- un poblado puede subir a ciudad, pero sigue siendo
   del mismo dueno. Asi que se cumple hasta el final de la partida.

2. Dos edificios no pueden estar en vertices contiguos, sean de quien sean
   (la regla de la distancia).

3. Cada jugador tiene 15 carreteras, 5 poblados y 4 ciudades. No hay
   dieciseis.

4. Todo edificio tiene al lado una carretera propia. Los dos poblados
   iniciales se colocan con su carretera, y los demas necesitan un camino.

La 1 y la 2 son las que hacen el trabajo; la 3 y la 4 recogen lo que quede.

Se aplican quitando, nunca poniendo. Inventar una pieza porque "deberia
haberla" seria cambiar un error por otro que ademas no se nota.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from red.sitios import PIEZAS, TOPE_VERTICES, es_arista   # noqa: F401
from vision.board_graph import axial_de, axial_to_pixel, build_board_graph

# Cuantas piezas de cada tipo tiene un jugador. Son las del juego de mesa y
# las que usa Catan Universe.
LIMITE = {"carretera": 15, "poblado": 5, "ciudad": 4}


def topologia(casillas=19):
    """Quien toca a quien, en las claves de sitio del proyecto
    (`dataset.clave_de_sitio`: vertices por debajo del 80, aristas por
    encima).

    Sale del tablero IDEAL, sin mirar ninguna foto: la topologia del Catan
    es la misma en todas las partidas y en todas las pantallas. Se construye
    con el mismo `build_board_graph` que usa el resto del proyecto para que
    los identificadores signifiquen lo mismo -- calcularla aparte seria
    pedir que dos numeraciones distintas coincidan por su cuenta."""
    centros = [axial_to_pixel(q, r, 1.0) for (q, r) in axial_de(casillas)]
    grafo = build_board_graph(centros, 1.0)

    vertices_de = {}     # arista -> (vertice, vertice)
    aristas_de = {}      # vertice -> [aristas]
    for eid, e in grafo.edges.items():
        va, vb = e["vertices"]
        clave = TOPE_VERTICES + eid
        vertices_de[clave] = (int(va), int(vb))
        aristas_de.setdefault(int(va), []).append(clave)
        aristas_de.setdefault(int(vb), []).append(clave)
    for vid in grafo.vertices:
        aristas_de.setdefault(int(vid), [])

    # vertices contiguos: los que comparten una arista
    vecinos_de = {vid: set() for vid in grafo.vertices}
    for (va, vb) in vertices_de.values():
        vecinos_de[va].add(vb)
        vecinos_de[vb].add(va)

    return {"vertices_de_arista": vertices_de,
            "aristas_de_vertice": aristas_de,
            "vertices_vecinos": {k: sorted(v) for k, v in vecinos_de.items()}}


_TOPO = {}


def topo(casillas=19):
    """La topologia de ese tablero, calculada una vez y guardada.

    `es_arista` NO esta aqui: se importa de `dataset`, porque el corte entre
    vertices y aristas tiene que ser el mismo que usa quien numera los
    sitios. Cuando estaban en dos sitios, aqui ponia 54 -- el corte del
    tablero de 19 -- y en un tablero de 5-6 las 29 primeras carreteras
    pasaban por edificios: el filtro de distancia las borraba por estar
    «pegadas» a un poblado que no existe."""
    if casillas not in _TOPO:
        _TOPO[casillas] = topologia(casillas)
    return _TOPO[casillas]


def tocan(sitio_a, sitio_b, casillas=19):
    """Si dos sitios comparten un vertice. Sirve para los cuatro casos
    (arista-arista, arista-vertice, vertice-vertice)."""
    t = topo(casillas)

    def puntos(s):
        return set(t["vertices_de_arista"][s]) if es_arista(s) else {s}

    return bool(puntos(sitio_a) & puntos(sitio_b))


def vecinas_de_arista(sitio, casillas=19):
    """Las aristas que comparten un extremo con esta."""
    t = topo(casillas)
    va, vb = t["vertices_de_arista"][sitio]
    salida = set(t["aristas_de_vertice"][va]) | set(t["aristas_de_vertice"][vb])
    salida.discard(sitio)
    return sorted(salida)


# --- el filtro ---------------------------------------------------------

def _grupos_de_carreteras(sitios, casillas=19):
    """Las carreteras de un jugador, agrupadas por las que se tocan."""
    t = topo(casillas)
    resto = set(sitios)
    grupos = []
    while resto:
        semilla = resto.pop()
        grupo, pendientes = {semilla}, [semilla]
        while pendientes:
            actual = pendientes.pop()
            for otra in vecinas_de_arista(actual, casillas):
                if otra in resto:
                    resto.discard(otra)
                    grupo.add(otra)
                    pendientes.append(otra)
        grupos.append(grupo)
    return grupos, t


def limpiar(tablero, reglas_activas=("distancia", "apoyo"), casillas=19):
    """Quita del tablero leido lo que el Catan no permite.

    `tablero` es {sitio: (pieza, color, votos)} tal como sale de acumular.
    Devuelve (tablero limpio, {regla: [sitios quitados]}).

    Cuando dos piezas se estorban se quita la que MENOS votos saco. No es un
    desempate cualquiera: los votos son las veces que la red la ha visto a lo
    largo de la partida, asi que una pieza de verdad, que esta ahi desde que
    la pusieron, casi siempre tiene mas que una que se cuela por el reflejo
    de la de al lado.

    Se repite hasta que no cambia nada. Hace falta: un grupo de carreteras
    inventadas se sostiene a si mismo mientras no se mire el grupo entero, y
    quitar una deja a la siguiente sin apoyo."""
    t = topo(casillas)
    tablero = dict(tablero)
    quitadas = {r: [] for r in reglas_activas}

    def es_edificio(s):
        return not es_arista(s)

    for _ in range(20):
        antes = len(tablero)

        # 1. dos edificios no pueden estar en vertices contiguos
        if "distancia" in reglas_activas:
            for v in sorted(x for x in tablero if es_edificio(x)):
                if v not in tablero:
                    continue
                for w in t["vertices_vecinos"][v]:
                    if w not in tablero or not es_edificio(w):
                        continue
                    perdedor = v if tablero[v][2] < tablero[w][2] else w
                    del tablero[perdedor]
                    quitadas["distancia"].append(perdedor)
                    if perdedor == v:
                        break

        # 2. todo grupo de carreteras de un jugador contiene un edificio
        #    suyo. Es cierto por como se construye: la primera carretera de
        #    un grupo se puso pegada a un edificio propio, y las piezas no
        #    desaparecen. Un poblado sube a ciudad pero sigue siendo del
        #    mismo. Esta es la regla que tumba los grupos enteros de
        #    carreteras inventadas: se sostienen entre ellas, pero no cuelgan
        #    de ningun edificio.
        if "apoyo" in reglas_activas:
            por_color = {}
            for s, (pieza, color, _v) in tablero.items():
                por_color.setdefault(color, {"aristas": [], "vertices": set()})
                if es_arista(s):
                    por_color[color]["aristas"].append(s)
                else:
                    por_color[color]["vertices"].add(s)
            for color, cosas in por_color.items():
                grupos, _ = _grupos_de_carreteras(cosas["aristas"], casillas)
                for grupo in grupos:
                    puntos = set()
                    for s in grupo:
                        puntos.update(t["vertices_de_arista"][s])
                    if puntos & cosas["vertices"]:
                        continue
                    for s in sorted(grupo):
                        del tablero[s]
                        quitadas["apoyo"].append(s)

        # 3. nadie tiene mas de 15 carreteras, 5 poblados ni 4 ciudades
        if "limite" in reglas_activas:
            cajas = {}
            for s, (pieza, color, votos) in tablero.items():
                cajas.setdefault((color, pieza), []).append((votos, s))
            for (color, pieza), lista in cajas.items():
                tope = LIMITE.get(PIEZAS[pieza])
                if tope is None or len(lista) <= tope:
                    continue
                for _votos, s in sorted(lista, reverse=True)[tope:]:
                    del tablero[s]
                    quitadas["limite"].append(s)

        # 4. todo edificio tiene una carretera propia al lado. Va la ultima
        #    porque es la mas delicada: si la red se ha dejado las carreteras
        #    de un poblado de verdad, esta regla se lleva el poblado.
        if "camino" in reglas_activas:
            for v in sorted(x for x in tablero if es_edificio(x)):
                color = tablero[v][1]
                suyas = [a for a in t["aristas_de_vertice"][v]
                         if a in tablero and tablero[a][1] == color]
                if not suyas:
                    del tablero[v]
                    quitadas["camino"].append(v)

        if len(tablero) == antes:
            break

    return tablero, {k: v for k, v in quitadas.items() if v}
