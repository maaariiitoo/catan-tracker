# -*- coding: utf-8 -*-
"""Una partida inventada, para los ejemplos de `VISTAS.md`.

Cuatro jugadores que no existen -- Ana, Bruno, Carla y Dani -- en un tablero
normal de 19 casillas. Se monta en una base en memoria y las vistas de
verdad se ejecutan encima, así que los números de los ejemplos **salen del
mismo SQL que usa el programa**. Si mañana cambia una vista, el ejemplo
cambia solo y sigue estando bien.

POR QUÉ INVENTADA Y NO UNA DE VERDAD. `VISTAS.md` se publica. Una partida
real llevaría dentro los nombres de con quién juego y lo que hizo cada uno,
y este repositorio no trae datos de nadie. Y además saldría distinta en cada
ordenador, con lo que la prueba de que el fichero está al día fallaría sin
que nadie hubiera tocado nada.

NO ES UNA PARTIDA JUGABLE, y no pretende serlo: no hay que gastar recursos
para construir ni cuadra el mazo. Es lo justo para que las 28 vistas
devuelvan filas que se entiendan. Hay una prueba que comprueba que ninguna
sale vacía -- una tabla de ejemplo sin filas explica menos que nada.

    py db/muestra.py        cuántas filas da cada vista con esta partida
"""
import json
import os
import sqlite3
import sys

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RAIZ)

from mod_verdad.importar import crear_tablas   # noqa: E402

# nombre, color, salida, puesto, puntos, carretera_larga, mayor_ejercito
JUGADORES = [
    ("Ana",   "Red",    1, 1, 10, 0, 1),
    ("Bruno", "Blue",   2, 2,  8, 1, 0),
    ("Carla", "Orange", 3, 3,  6, 0, 0),
    ("Dani",  "White",  4, 4,  5, 0, 0),
]

# El tablero de siempre: 19 casillas, un desierto y los 18 números.
TABLERO = [
    (0, -2, "Mineral", 10), (1, -2, "Lana", 2), (2, -2, "Lana", 9),
    (-1, -1, "Cereales", 12), (0, -1, "Arcilla", 6), (1, -1, "Lana", 4),
    (2, -1, "Arcilla", 10),
    (-2, 0, "Cereales", 9), (-1, 0, "Madera", 11), (0, 0, "Desierto", None),
    (1, 0, "Madera", 3), (2, 0, "Mineral", 8),
    (-2, 1, "Madera", 8), (-1, 1, "Mineral", 3), (0, 1, "Cereales", 4),
    (1, 1, "Lana", 5),
    (-2, 2, "Arcilla", 5), (-1, 2, "Cereales", 6), (0, 2, "Madera", 11),
]

PUERTOS = [("generico", 3), ("Mineral", 2), ("Lana", 2), ("generico", 3)]

# Quién tiene qué. Cada poblado se apunta con las casillas que toca, por su
# sitio en `TABLERO`. Los dos primeros de cada uno son la colocación inicial.
# jugador, turno, casillas que toca, turno en que subió a ciudad
CONSTRUIDO = [
    ("Ana",   0, (0, 1, 3), 18),
    ("Ana",   0, (11, 15), None),
    ("Ana",  22, (14, 16), None),
    ("Bruno", 0, (4, 5, 8), 25),
    ("Bruno", 0, (12, 16), None),
    ("Carla", 0, (2, 6), None),
    ("Carla", 0, (7, 8, 12), None),
    ("Carla", 30, (17, 18), None),
    ("Dani",  0, (13, 14), None),
    ("Dani",  0, (10, 11, 15), None),
]

CARRETERAS = [("Ana", 4), ("Bruno", 6), ("Carla", 3), ("Dani", 4)]

# Las tiradas, turno a turno. Hay números que salen de más y de menos a
# propósito: una tabla donde todo cuadra no enseña a leerla.
TIRADAS = [
    (1, "Ana", 8), (2, "Bruno", 6), (3, "Carla", 11), (4, "Dani", 4),
    (5, "Ana", 8), (6, "Bruno", 7), (7, "Carla", 5), (8, "Dani", 9),
    (9, "Ana", 6), (10, "Bruno", 8), (11, "Carla", 3), (12, "Dani", 10),
    (13, "Ana", 7), (14, "Bruno", 6), (15, "Carla", 8), (16, "Dani", 12),
    (17, "Ana", 5), (18, "Bruno", 9), (19, "Carla", 6), (20, "Dani", 8),
    (21, "Ana", 4), (22, "Bruno", 10), (23, "Carla", 7), (24, "Dani", 6),
    (25, "Ana", 11), (26, "Bruno", 8), (27, "Carla", 2), (28, "Dani", 5),
    (29, "Ana", 9), (30, "Bruno", 6), (31, "Carla", 8), (32, "Dani", 3),
]

# El ladrón: turno, quién lo mueve, a qué casilla, y por qué.
#
# Ninguno se lo pone en una casilla suya. Ponérselo a uno mismo es legal y
# pasa -- cuando no queda otra o para tapar un número que te da igual -- pero
# de ejemplo despista: sale una fila «Bruno / Bruno» que hace dudar de si la
# tabla está bien. Para eso está la partida de verdad.
LADRON = [
    (6, "Bruno", 0, "siete"),
    (10, "Ana", 12, "caballero"),
    (13, "Ana", 4, "siete"),
    (20, "Dani", 7, "caballero"),
    (23, "Carla", 0, "siete"),
    (26, "Ana", 12, "caballero"),
]

# Robos de la mano, pegados al movimiento del ladrón de ese turno. La víctima
# tiene algo en la casilla donde acaba de caer el ladrón, que es la única
# forma de que se pueda robar.
ROBOS = [(6, "Bruno", "Ana"), (10, "Ana", "Bruno"), (13, "Ana", "Bruno"),
         (20, "Dani", "Carla"), (23, "Carla", "Ana"), (26, "Ana", "Carla")]

# jugador, turno de compra, turno en que la juega (None: no la jugó), qué era
CARTAS = [
    ("Ana", 7, 10, "Caballero"),
    ("Ana", 9, 26, "Caballero"),
    ("Ana", 14, 21, "Monopolio"),
    ("Ana", 19, None, None),
    ("Bruno", 8, 16, "Invencion"),
    ("Bruno", 12, 24, "Construccion de carreteras"),
    ("Bruno", 21, None, None),
    ("Carla", 11, 17, "Caballero"),
    ("Carla", 18, 28, "Monopolio"),
    ("Dani", 15, 20, "Caballero"),
    ("Dani", 27, None, None),
]

# Qué se llevó cada monopolio, y de quién.
MONOPOLIOS = [
    (21, "Ana", "Lana", [("Bruno", 3), ("Carla", 1), ("Dani", 0)]),
    (28, "Carla", "Cereales", [("Ana", 2), ("Bruno", 0), ("Dani", 2)]),
]

# Tratos. Con `None` en el otro lado es la banca o un puerto.
TRATOS = [
    (5, "Ana", "Bruno", {"Madera": 2}, {"Mineral": 1}),
    (9, "Bruno", "Carla", {"Lana": 1}, {"Arcilla": 1}),
    (12, "Ana", "Carla", {"Cereales": 1}, {"Madera": 2}),
    (16, "Dani", "Ana", {"Mineral": 1}, {"Cereales": 1}),
    (18, "Bruno", "Ana", {"Arcilla": 2}, {"Lana": 1}),
    (22, "Carla", "Dani", {"Madera": 1}, {"Lana": 1}),
    (24, "Ana", None, {"Mineral": 3}, {"Cereales": 1}),
    (29, "Bruno", None, {"Lana": 2}, {"Madera": 1}),
]


def _cartas(dado):
    """El formato en que el mod apunta lo que cambia de manos: una lista de
    `{"resource": ..., "amount": ...}`. Aquí se escribe igual que allí, que
    si no las vistas de comercio no encuentran nada y salen vacías."""
    return json.dumps([{"resource": r, "amount": n}
                       for r, n in sorted(dado.items())])


def _iso(turno):
    """Una hora cualquiera pero creciente: las vistas ordenan por ella."""
    return "2026-01-15T20:%02d:%02d" % (10 + turno // 2, (turno * 7) % 60)


def construir(conn=None):
    """Monta la partida y devuelve la conexión, con las vistas ya creadas."""
    from db import vistas as V

    if conn is None:
        conn = sqlite3.connect(":memory:")
    crear_tablas(conn)
    c = conn.cursor()

    c.execute("INSERT INTO games (game_id, started_at, ended_at, winner, "
              "source) VALUES (1,?,?,'Ana','muestra')",
              ("2026-01-15T20:00:00", "2026-01-15T20:58:00"))

    pid = {}
    for nombre, color, salida, puesto, puntos, carretera, ejercito in JUGADORES:
        c.execute("INSERT INTO people (display_name) VALUES (?)", (nombre,))
        # `final_points_visible` es un punto menos en Ana: el que llevaba
        # escondido en una carta. Es lo que hace que «De dónde salió cada
        # punto» tenga algo que enseñar en la columna de las cartas.
        c.execute(
            "INSERT INTO players (game_id, person_name, name, color, is_bot, "
            "turn_order, final_rank, final_points, final_points_visible, "
            "longest_road, largest_army) VALUES (1,?,?,?,0,?,?,?,?,?,?)",
            (nombre, nombre, color, salida, puesto, puntos,
             puntos - (1 if nombre == "Ana" else 0), carretera, ejercito))
        pid[nombre] = c.lastrowid

    tid = []
    for q, r, recurso, numero in TABLERO:
        c.execute("INSERT INTO tiles (game_id, axial_q, axial_r, resource, "
                  "number) VALUES (1,?,?,?,?)", (q, r, recurso, numero))
        tid.append(c.lastrowid)

    hid = []
    for n, (kind, ratio) in enumerate(PUERTOS):
        # `edge_json` no es decorado: «Quién pilló cada puerto» exige que
        # esté, porque sin saber dónde cae el puerto en el tablero esa
        # pregunta no se puede contestar y la vista prefiere no salir a
        # salir vacía.
        c.execute("INSERT INTO harbors (game_id, kind, ratio, edge_json, "
                  "tiles_json) VALUES (1,?,?,?,?)",
                  (kind, ratio, json.dumps({"a": n, "b": n + 1}),
                   json.dumps([n])))
        hid.append(c.lastrowid)

    edificios = {}
    for i, (quien, turno, casillas, sube) in enumerate(CONSTRUIDO):
        tipo = "ciudad" if sube else "poblado"
        c.execute(
            "INSERT INTO buildings (game_id, player_id, type, turn_number, "
            "timestamp, vertex_key, upgraded_turn, upgraded_at) "
            "VALUES (1,?,?,?,?,?,?,?)",
            (pid[quien], tipo, turno, _iso(turno), "v%d" % i, sube,
             _iso(sube) if sube else None))
        bid = c.lastrowid
        edificios.setdefault(quien, []).append((bid, tipo, casillas))
        for k in casillas:
            c.execute("INSERT INTO building_tiles (building_id, tile_id) "
                      "VALUES (?,?)", (bid, tid[k]))

    # Un puerto para cada uno, en su primer poblado.
    for n, (quien, _color, _s, _p, _pt, _cl, _me) in enumerate(JUGADORES):
        c.execute("INSERT INTO harbor_owners (game_id, harbor_id, "
                  "building_id, player_id, turn_number, timestamp) "
                  "VALUES (1,?,?,?,0,?)",
                  (hid[n], edificios[quien][0][0], pid[quien], _iso(0)))

    for quien, cuantas in CARRETERAS:
        for n in range(cuantas):
            c.execute("INSERT INTO roads (game_id, player_id, edge_key, "
                      "turn_number, timestamp) VALUES (1,?,?,?,?)",
                      (pid[quien], "%s-%d" % (quien, n), n + 1, _iso(n + 1)))

    for turno, quien, _valor in TIRADAS:
        c.execute("INSERT INTO turns (game_id, player_id, turn_number, phase, "
                  "start_ts) VALUES (1,?,?,'normal',?)",
                  (pid[quien], turno, _iso(turno)))

    # El reparto inicial: lo da el SEGUNDO poblado de cada uno.
    for quien in pid:
        for k in edificios[quien][1][2]:
            if TABLERO[k][3] is None:
                continue
            c.execute("INSERT INTO resource_gains (game_id, player_id, "
                      "resource, amount, source, timestamp) "
                      "VALUES (1,?,?,1,'inicial',?)",
                      (pid[quien], TABLERO[k][2], _iso(0)))

    # Las tiradas y lo que produjeron, con el ladrón donde estuviera.
    movimientos = {t: (q, k, p) for t, q, k, p in LADRON}
    ladron_en, ladron_de = None, None
    for turno, quien, valor in TIRADAS:
        if turno in movimientos:
            q, k, porque = movimientos[turno]
            c.execute("INSERT INTO robber_moves (game_id, player_id, tile_id, "
                      "turn_number, timestamp, cause) VALUES (1,?,?,?,?,?)",
                      (pid[q], tid[k], turno, _iso(turno), porque))
            ladron_en, ladron_de = k, pid[q]
        c.execute("INSERT INTO rolls (game_id, player_id, turn_number, value, "
                  "die1, die2, timestamp) VALUES (1,?,?,?,?,?,?)",
                  (pid[quien], turno, valor, valor // 2, valor - valor // 2,
                   _iso(turno)))
        rid = c.lastrowid
        if valor == 7:
            continue
        for otro in sorted(pid):
            for _bid, tipo, casillas in edificios[otro]:
                cuanto = 2 if tipo == "ciudad" else 1
                for k in casillas:
                    if TABLERO[k][3] != valor:
                        continue
                    if k == ladron_en:
                        c.execute(
                            "INSERT INTO robber_blocks (game_id, roll_id, "
                            "tile_id, blocker_id, victim_id, building_type, "
                            "amount, timestamp) VALUES (1,?,?,?,?,?,?,?)",
                            (rid, tid[k], ladron_de, pid[otro], tipo, cuanto,
                             _iso(turno)))
                        continue
                    c.execute(
                        "INSERT INTO resource_gains (game_id, player_id, "
                        "roll_id, resource, amount, source, timestamp) "
                        "VALUES (1,?,?,?,?,'produccion',?)",
                        (pid[otro], rid, TABLERO[k][2], cuanto, _iso(turno)))

    for turno, ladron, victima in ROBOS:
        fila = c.execute("SELECT move_id FROM robber_moves WHERE "
                         "turn_number=?", (turno,)).fetchone()
        c.execute("INSERT INTO steals (game_id, move_id, thief_id, victim_id, "
                  "timestamp) VALUES (1,?,?,?,?)",
                  (fila[0] if fila else None, pid[ladron], pid[victima],
                   _iso(turno)))

    jugadas = {}
    for quien, compra, juega, que in CARTAS:
        c.execute("INSERT INTO dev_card_purchases (game_id, player_id, "
                  "turn_number, timestamp) VALUES (1,?,?,?)",
                  (pid[quien], compra, _iso(compra)))
        if juega is None or que is None:
            continue
        c.execute("INSERT INTO dev_card_plays (game_id, player_id, card_type, "
                  "turn_number, timestamp) VALUES (1,?,?,?,?)",
                  (pid[quien], que, juega, _iso(juega)))
        jugadas[(quien, juega)] = c.lastrowid

    for turno, quien, recurso, reparto in MONOPOLIOS:
        play = jugadas[(quien, turno)]
        c.execute("UPDATE dev_card_plays SET resource=? WHERE play_id=?",
                  (recurso, play))
        for victima, cuanto in reparto:
            c.execute("INSERT INTO monopoly_takes (game_id, play_id, "
                      "turn_number, taker_id, victim_id, resource, amount, "
                      "timestamp) VALUES (1,?,?,?,?,?,?,?)",
                      (play, turno, pid[quien], pid[victima], recurso, cuanto,
                       _iso(turno)))

    for turno, a, b, dio, recibio in TRATOS:
        c.execute("INSERT INTO trades (game_id, player_a_id, player_b_id, "
                  "gave_json, received_json, timestamp) VALUES (1,?,?,?,?,?)",
                  (pid[a], pid[b] if b else None,
                   _cartas(dio), _cartas(recibio), _iso(turno)))

    conn.commit()
    V.crear(conn)
    return conn


def main():
    conn = construir()
    from db import vistas as V
    vacias = []
    for v in V.VISTAS:
        _cols, filas = V.consultar(conn, v["nombre"])
        print("%-30s %3d filas" % (v["nombre"], len(filas)))
        if not filas:
            vacias.append(v["nombre"])
    if vacias:
        print("\nVACIAS: %s" % ", ".join(vacias))
        return 1
    print("\nLas %d dan filas." % len(V.VISTAS))
    return 0


if __name__ == "__main__":
    sys.exit(main())
