# -*- coding: utf-8 -*-
"""La producción no hace falta leerla en ningún sitio: se deduce.

Esto nació de una pregunta de Mario -- «¿puede la visión hacer todo lo que
hace el mod?» -- y de mirar cuánto de la base de datos es tablero y cuánto son
sucesos. El tablero es el 16%: 77 filas de las 405 que apunta el mod en una
partida. Las otras 328 son sucesos, y la idea de partida era que hacía falta
leer el panel de «REGISTRO DE LA PARTIDA» con OCR para tenerlos.

Para una buena parte, no. **La producción es una regla, no un dato.** Si sabes
qué edificios hay, en qué casillas tocan, qué número salió y dónde está el
ladrón, quién cobra qué está determinado -- y esas cuatro cosas la visión ya
las lee. No hay nada que reconocer ni ninguna frase que entender.

    de 405 filas por partida
       77   tablero, la visión ya las lee
      197   producción y bloqueos: SE DEDUCEN de las anteriores  <- esto
      131   comercios, robos, cartas, turnos: siguen haciendo falta

MEDIDO contra lo que apuntó el mod, las nueve partidas: **1.886 cartas de
1.886, 180 casillas de 180**. Exacto, sin una sola diferencia.

QUÉ COMPRUEBA ESTO EXACTAMENTE, que estuvo un tiempo dicho de más. La
producción que hay en `resource_gains` **no la lee el mod del juego: la
calcula `importar.py`**, con esta misma regla, sobre el tablero que venía en
cada acción de reparto. Así que esto no son dos fuentes independientes de la
misma cifra, y decir que lo eran era vender más de lo que hay.

Lo que sí compara, que no es poco: `importar.py` calcula **en el momento**,
con la lista de edificios que trae ese evento; esto lo calcula **después**,
reconstruyendo qué había en cada instante a partir de las marcas de tiempo de
la base. Que las dos coincidan dice que el historial guardado reproduce los
tableros que el mod vio, uno a uno. Es lo que cazó lo del «Año Productivo».

Y hay un límite que conviene tener delante: **las dos cuentas comparten el
ladrón**. Si el mod no supo leer dónde estaba --pasa en el tablero de 5-6
jugadores, ver `pegas` en la vista de Partidas-- las dos reparten de más
exactamente igual y salen idénticas. Un 341 de 341 en una partida así no dice
que la producción esté bien; dice que las dos están mal igual.

Dos detalles que costaron descubrir y que son la diferencia entre 97,7% y
exacto:

1. **Por marca de tiempo, no por número de turno.** Dentro de un mismo turno
   primero se tira y luego se construye, así que un poblado puesto en el turno
   42 no cobra la tirada del turno 42. Los cuatro únicos fallos de la primera
   versión eran exactamente eso, de 2 a 22 segundos después de su tirada.

2. **Lo mismo con el ladrón**: un caballero jugado a media ronda lo mueve
   DESPUÉS de la tirada de ese turno, así que bloquearla sería adelantarse.

Y de paso encontró un fallo en el importador: cazaba las acciones de reparto
por su terminación, con lo que «Año Productivo» se colaba como producción y
volvía a apuntar la de la última tirada. 17 repartos duplicados y 34 cartas
fantasma en cuatro partidas. Arreglado en `_REPARTOS_DE_VERDAD`. Calcular lo
mismo por dos caminos distintos sirve justo para esto.

Uso:
    py -m db.deducir            # comprueba las nueve contra el mod
    py -m db.deducir --partida 9
"""

import argparse
import collections
import os
import sqlite3
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BASE = os.path.join(RAIZ, "catan_stats.db")


def _tablero(conn, game_id):
    """Lo que la visión ve: edificios con sus casillas, y las casillas."""
    edificios = {}
    for bid, pid, tipo, cuando, mejorado_en in conn.execute(
            "SELECT building_id, player_id, type, timestamp, upgraded_at "
            "FROM buildings WHERE game_id = ?", (game_id,)):
        edificios[bid] = {"pid": pid, "tipo": tipo, "cuando": cuando or "",
                          "mejorado_en": mejorado_en, "casillas": []}
    for bid, tid in conn.execute(
            "SELECT bt.building_id, bt.tile_id FROM building_tiles bt "
            "JOIN buildings b ON b.building_id = bt.building_id "
            "WHERE b.game_id = ?", (game_id,)):
        if bid in edificios:
            edificios[bid]["casillas"].append(tid)
    casillas = {tid: (num, rec) for tid, num, rec in conn.execute(
        "SELECT tile_id, number, resource FROM tiles WHERE game_id = ?",
        (game_id,))}
    return edificios, casillas


def _ladron_en(conn, game_id):
    """Una función que dice en qué casilla está el ladrón a una hora dada."""
    saltos = list(conn.execute(
        "SELECT timestamp, tile_id FROM robber_moves WHERE game_id = ? "
        "ORDER BY timestamp", (game_id,)))
    # Empieza en el desierto, que en el tablero básico es la única casilla sin
    # número. En el de 5-6 jugadores hay DOS, y entonces no se sabe en cuál
    # empieza: se deja en None, que quiere decir «no hay ninguna tapada».
    # Antes esto hacía `fetchone()` y se quedaba con uno de los dos, elegido
    # por el orden en que estuvieran guardados -- un ladrón inventado en una
    # casilla concreta, callado. En cuanto hay un movimiento apuntado da
    # igual, porque manda el movimiento; sin ninguno, mejor no tapar nada que
    # tapar la que no es.
    desiertos = [t for (t,) in conn.execute(
        "SELECT tile_id FROM tiles WHERE game_id = ? AND number IS NULL",
        (game_id,))]
    desierto = desiertos[0] if len(desiertos) == 1 else None

    def donde(cuando):
        sitio = desierto
        for t, tid in saltos:
            if t is not None and t <= cuando:
                sitio = tid
        return sitio
    return donde


def produccion(conn, game_id):
    """Lo que produce cada tirada, deducido del tablero.

    Devuelve (gana, bloqueado):
      gana      [(player_id, recurso, cantidad, roll_id)]
      bloqueado [(player_id, tile_id, tipo, cantidad, roll_id)]  lo que el
                ladrón impidió, que es la otra mitad de la misma cuenta.
    """
    edificios, casillas = _tablero(conn, game_id)
    donde_el_ladron = _ladron_en(conn, game_id)

    gana, bloqueado = [], []
    for roll_id, valor, cuando in conn.execute(
            "SELECT roll_id, value, timestamp FROM rolls WHERE game_id = ? "
            "ORDER BY turn_number", (game_id,)):
        if valor == 7:
            continue                       # el 7 no produce, roba
        tapada = donde_el_ladron(cuando)
        for e in edificios.values():
            if e["cuando"] > cuando:
                continue                   # todavía no estaba puesto
            # una ciudad da 2, pero sólo desde que se mejoró: antes de eso
            # ese mismo edificio era un poblado y daba 1
            if e["tipo"] == "ciudad" and e["mejorado_en"] is not None \
                    and e["mejorado_en"] <= cuando:
                cuantas, tipo = 2, "ciudad"
            else:
                cuantas, tipo = 1, "poblado"
            for tid in e["casillas"]:
                num, rec = casillas.get(tid, (None, None))
                if num != valor or rec in (None, "Desierto"):
                    continue
                if tid == tapada:
                    bloqueado.append((e["pid"], tid, tipo, cuantas, roll_id))
                else:
                    gana.append((e["pid"], rec, cuantas, roll_id))
    return gana, bloqueado


# --- comprobarlo contra el mod -------------------------------------------

def comparar(conn, game_id):
    """(cuadran, total, cartas_mod, cartas_deducidas) por jugador y recurso."""
    gana, _bloq = produccion(conn, game_id)
    mio = collections.Counter()
    for pid, rec, n, _r in gana:
        mio[(pid, rec)] += n
    suyo = collections.Counter()
    for pid, rec, n in conn.execute(
            "SELECT player_id, resource, SUM(amount) FROM resource_gains "
            "WHERE game_id = ? AND source = 'produccion' "
            "GROUP BY player_id, resource", (game_id,)):
        suyo[(pid, rec)] = n
    claves = set(mio) | set(suyo)
    cuadran = sum(1 for k in claves if mio.get(k, 0) == suyo.get(k, 0))
    return cuadran, len(claves), sum(suyo.values()), sum(mio.values())


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--partida", type=int, help="sólo esta")
    ap.add_argument("--base", default=BASE)
    args = ap.parse_args()

    conn = sqlite3.connect("file:%s?mode=ro" % args.base, uri=True)
    partidas = ([args.partida] if args.partida else
                [r[0] for r in conn.execute(
                    "SELECT game_id FROM games ORDER BY game_id")])
    print("La producción, deducida del tablero, contra lo que apuntó el mod")
    print()
    # Las partidas en las que el ladrón no se pudo leer. Cuadran igual, y por
    # eso hay que decirlo: las dos cuentas reparten de más exactamente igual,
    # así que el «bien» de esa fila no vale.
    ciegas = set(g for g, in conn.execute(
        "SELECT game_id FROM mod_imports WHERE pegas LIKE '%ladron%'"))         if conn.execute("SELECT COUNT(*) FROM sqlite_master WHERE type='table'"
                        " AND name='mod_imports'").fetchone()[0] else set()
    tot_c = tot_n = tot_m = tot_d = 0
    for g in partidas:
        cuadran, cuantas, mod, deducidas = comparar(conn, g)
        tot_c += cuadran
        tot_n += cuantas
        tot_m += mod
        tot_d += deducidas
        if cuadran != cuantas or mod != deducidas:
            nota = "  <- MAL"
        elif g in ciegas:
            nota = "  <- cuadra, pero SIN LADRÓN: las dos reparten de más"
        else:
            nota = ""
        print("   partida %-3d %4d cartas -> %-4d   %2d de %2d casillas   %s"
              % (g, mod, deducidas, cuadran, cuantas, nota))
    print()
    print("   TOTAL %d cartas de %d, %d casillas de %d"
          % (tot_d, tot_m, tot_c, tot_n))
    conn.close()
    return 0 if (tot_c == tot_n and tot_m == tot_d) else 1


if __name__ == "__main__":
    sys.exit(main())
