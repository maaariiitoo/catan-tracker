# -*- coding: utf-8 -*-
"""Las preguntas de siempre, contestadas con lo que apuntó el mod.

    py analizar.py                  todas las partidas del mod, junto
    py analizar.py --partida 74     una sola
    py analizar.py --vision         usa las de la visión en vez de las del mod

Por qué separadas: si se juega con el mod y con el tracker a la vez, la
MISMA partida está dos veces en la base de datos -- una leída por dentro y
otra leída de la pantalla. Sumarlas contaría todo por duplicado, así que
aquí se mira una fuente o la otra, nunca las dos.

Esto no pretende ser el análisis, es el andamio: enseña que los datos están
y con qué consultas se sacan. Las conclusiones son cosa tuya.
"""
import argparse
import collections
import json
import os
import sqlite3
import sys

RAIZ = os.path.dirname(os.path.abspath(__file__))
BASE = os.path.join(RAIZ, "catan_stats.db")

# Cuántas de las 36 combinaciones de dos dados dan cada número. Es la medida
# honesta de "cómo de bueno es un número": un 6 vale cinco veces lo que un 2.
PIPS = {2: 1, 3: 2, 4: 3, 5: 4, 6: 5, 7: 6, 8: 5, 9: 4, 10: 3, 11: 2, 12: 1}


def _titulo(t):
    print()
    print(t)
    print("-" * len(t))


def partidas(conn, vision, una=None):
    if una:
        return [una]
    if vision:
        cond = "(source IS NULL OR source<>'mod')"
    else:
        cond = "source='mod'"
    return [r[0] for r in conn.execute(
        "SELECT game_id FROM games WHERE %s ORDER BY game_id" % cond)]


def quienes(conn, gs):
    """Las personas que salen en esas partidas, por nombre estable."""
    marcas = ",".join("?" * len(gs))
    return [r[0] for r in conn.execute(
        "SELECT DISTINCT COALESCE(person_name, name) FROM players "
        "WHERE game_id IN (%s) ORDER BY 1" % marcas, gs)]


def _uno(conn, sql, args, por_defecto=0):
    r = conn.execute(sql, args).fetchone()
    return (r[0] if r and r[0] is not None else por_defecto)


def informe(conn, gs):
    marcas = ",".join("?" * len(gs))
    gente = quienes(conn, gs)
    print("%d partida(s): %s" % (len(gs), ", ".join(str(g) for g in gs)))
    print("%d jugador(es): %s" % (len(gente), ", ".join(gente)))

    def por_persona(sql, extra=()):
        """Ejecuta una consulta que agrupa por persona y devuelve un dict."""
        return dict(conn.execute(sql % marcas, tuple(gs) + tuple(extra)).fetchall())

    jugadas = por_persona(
        "SELECT COALESCE(person_name,name), COUNT(*) FROM players "
        "WHERE game_id IN (%s) GROUP BY 1")
    ganadas = por_persona(
        "SELECT COALESCE(person_name,name), COUNT(*) FROM players "
        "WHERE game_id IN (%s) AND final_rank=1 GROUP BY 1")

    _titulo("Lo que ha construido cada uno")
    print("%-14s %7s %7s %8s %8s %9s" % ("", "partidas", "ganadas",
                                         "poblados", "ciudades", "carreteras"))
    for n in gente:
        pob = _uno(conn, "SELECT COUNT(*) FROM buildings b JOIN players p ON "
                   "p.player_id=b.player_id WHERE b.game_id IN (%s) AND "
                   "COALESCE(p.person_name,p.name)=? AND b.type='poblado'" % marcas,
                   tuple(gs) + (n,))
        ciu = _uno(conn, "SELECT COUNT(*) FROM buildings b JOIN players p ON "
                   "p.player_id=b.player_id WHERE b.game_id IN (%s) AND "
                   "COALESCE(p.person_name,p.name)=? AND b.type='ciudad'" % marcas,
                   tuple(gs) + (n,))
        car = _uno(conn, "SELECT COUNT(*) FROM roads r JOIN players p ON "
                   "p.player_id=r.player_id WHERE r.game_id IN (%s) AND "
                   "COALESCE(p.person_name,p.name)=?" % marcas, tuple(gs) + (n,))
        print("%-14s %7d %7d %8d %8d %9d"
              % (n, jugadas.get(n, 0), ganadas.get(n, 0), pob, ciu, car))

    _orden_de_turno(conn, gs, marcas, gente)
    _puntos_por_persona(conn, gs, marcas, gente, jugadas, ganadas)

    _titulo("Los recursos que ha producido cada uno")
    recursos = ["Madera", "Arcilla", "Lana", "Cereales", "Mineral"]
    print("%-14s %s %8s" % ("", "".join("%9s" % r for r in recursos), "total"))
    for n in gente:
        fila, total = [], 0
        for r in recursos:
            v = _uno(conn, "SELECT COALESCE(SUM(g.amount),0) FROM resource_gains g "
                     "JOIN players p ON p.player_id=g.player_id WHERE "
                     "g.game_id IN (%s) AND COALESCE(p.person_name,p.name)=? AND "
                     "g.resource=?" % marcas, tuple(gs) + (n, r))
            fila.append(v)
            total += v
        print("%-14s %s %8d" % (n, "".join("%9d" % v for v in fila), total))
    print()
    print("(producción del tablero: tiradas + colocación inicial. Los comercios")
    print(" y los robos no están, el mod no lee las manos de nadie.)")

    _titulo("En qué números se ha puesto cada uno")
    print("Los 'pips' son las combinaciones de 36 que dan ese número: un 6 vale")
    print("5 y un 2 vale 1. Es lo que mide si un sitio es bueno, no el número.")
    print()
    print("%-14s %6s %7s %9s %11s" % ("", "pips", "por ed.", "producido",
                                      "por pip"))
    for n in gente:
        pips = 0
        eds = _uno(conn, "SELECT COUNT(DISTINCT b.building_id) FROM buildings b "
                   "JOIN players p ON p.player_id=b.player_id WHERE "
                   "b.game_id IN (%s) AND COALESCE(p.person_name,p.name)=?" % marcas,
                   tuple(gs) + (n,))
        for num, veces, tipo in conn.execute(
                "SELECT t.number, COUNT(*), b.type FROM buildings b "
                "JOIN players p ON p.player_id=b.player_id "
                "JOIN building_tiles bt ON bt.building_id=b.building_id "
                "JOIN tiles t ON t.tile_id=bt.tile_id "
                "WHERE b.game_id IN (%s) AND COALESCE(p.person_name,p.name)=? "
                "AND t.number IS NOT NULL GROUP BY t.number, b.type" % marcas,
                tuple(gs) + (n,)):
            pips += PIPS.get(num, 0) * veces * (2 if tipo == "ciudad" else 1)
        prod = _uno(conn, "SELECT COALESCE(SUM(g.amount),0) FROM resource_gains g "
                    "JOIN players p ON p.player_id=g.player_id WHERE "
                    "g.game_id IN (%s) AND COALESCE(p.person_name,p.name)=? AND "
                    "g.source='produccion'" % marcas, tuple(gs) + (n,))
        print("%-14s %6d %7.1f %9d %11.2f"
              % (n, pips, (pips / eds) if eds else 0, prod,
                 (prod / pips) if pips else 0))
    print()
    print("'por pip' dice si le salieron los números: con muchas tiradas todos")
    print("deberían acercarse al mismo valor. El que se aleje, tuvo suerte o no.")

    _titulo("El ladrón")
    print("%-14s %8s %9s %10s %9s %9s" % ("", "lo movio", "robo a", "le robaron",
                                          "bloqueo", "bloqueado"))
    for n in gente:
        movio = _uno(conn, "SELECT COUNT(*) FROM robber_moves m JOIN players p ON "
                     "p.player_id=m.player_id WHERE m.game_id IN (%s) AND "
                     "COALESCE(p.person_name,p.name)=?" % marcas, tuple(gs) + (n,))
        robo = _uno(conn, "SELECT COUNT(*) FROM steals s JOIN players p ON "
                    "p.player_id=s.thief_id WHERE s.game_id IN (%s) AND "
                    "COALESCE(p.person_name,p.name)=?" % marcas, tuple(gs) + (n,))
        robado = _uno(conn, "SELECT COUNT(*) FROM steals s JOIN players p ON "
                      "p.player_id=s.victim_id WHERE s.game_id IN (%s) AND "
                      "COALESCE(p.person_name,p.name)=?" % marcas, tuple(gs) + (n,))
        bloqueo = _uno(conn, "SELECT COALESCE(SUM(b.amount),0) FROM robber_blocks b "
                       "JOIN players p ON p.player_id=b.blocker_id WHERE "
                       "b.game_id IN (%s) AND COALESCE(p.person_name,p.name)=?" % marcas,
                       tuple(gs) + (n,))
        sufrido = _uno(conn, "SELECT COALESCE(SUM(b.amount),0) FROM robber_blocks b "
                       "JOIN players p ON p.player_id=b.victim_id WHERE "
                       "b.game_id IN (%s) AND COALESCE(p.person_name,p.name)=?" % marcas,
                       tuple(gs) + (n,))
        print("%-14s %8d %9d %10d %9d %9d"
              % (n, movio, robo, robado, bloqueo, sufrido))
    print()
    print("'bloqueo' y 'bloqueado' son RECURSOS, no veces: lo que dejó de")
    print("producirse porque el ladrón estaba encima cuando salió ese número.")

    _titulo("Las tiradas")
    total = _uno(conn, "SELECT COUNT(*) FROM rolls WHERE game_id IN (%s)" % marcas,
                 tuple(gs))
    if total:
        print("%d tiradas en total" % total)
        print()
        for v in range(2, 13):
            n = _uno(conn, "SELECT COUNT(*) FROM rolls WHERE game_id IN (%s) "
                     "AND value=?" % marcas, tuple(gs) + (v,))
            real = 100.0 * n / total
            teor = 100.0 * PIPS[v] / 36
            barra = "#" * int(round(real * 2))
            print("  %2d  %4d  %5.1f%%  (teorico %4.1f%%)  %s" % (v, n, real, teor, barra))
        sietes = _uno(conn, "SELECT COUNT(*) FROM rolls WHERE game_id IN (%s) "
                      "AND value=7" % marcas, tuple(gs))
        print()
        print("el 7 salió %d veces (%.1f%%, teórico 16.7%%)"
              % (sietes, 100.0 * sietes / total))

    _titulo("Los comercios y las cartas de desarrollo")
    print("%-14s %10s %9s %9s" % ("", "comercios", "compradas", "jugadas"))
    for n in gente:
        com = _uno(conn, "SELECT COUNT(*) FROM trades t JOIN players p ON "
                   "p.player_id IN (t.player_a_id, t.player_b_id) WHERE "
                   "t.game_id IN (%s) AND COALESCE(p.person_name,p.name)=?" % marcas,
                   tuple(gs) + (n,))
        compra = _uno(conn, "SELECT COUNT(*) FROM dev_card_purchases d JOIN players p "
                      "ON p.player_id=d.player_id WHERE d.game_id IN (%s) AND "
                      "COALESCE(p.person_name,p.name)=?" % marcas, tuple(gs) + (n,))
        juega = _uno(conn, "SELECT COUNT(*) FROM dev_card_plays d JOIN players p "
                     "ON p.player_id=d.player_id WHERE d.game_id IN (%s) AND "
                     "COALESCE(p.person_name,p.name)=?" % marcas, tuple(gs) + (n,))
        print("%-14s %10d %9d %9d" % (n, com, compra, juega))
    cartas = conn.execute(
        "SELECT COALESCE(card_type,'(no se sabe)'), COUNT(*) FROM dev_card_plays "
        "WHERE game_id IN (%s) GROUP BY 1 ORDER BY 2 DESC" % marcas, gs).fetchall()
    if cartas:
        print()
        print("cartas jugadas: " + ", ".join("%s x%d" % (c, n) for c, n in cartas))

    _que_se_comercio(conn, gs, marcas, gente)


def _orden_de_turno(conn, gs, marcas, gente):
    """Quién empezó. Sale del orden real de colocación, no del asiento.

    Con una sola partida se enseña la secuencia; con varias, en qué puesto
    le suele tocar a cada uno y cuántas ganó desde ahí -- que es la pregunta
    de fondo: ¿influye empezar el primero?"""
    if len(gs) == 1:
        filas = conn.execute(
            "SELECT name, turn_order FROM players WHERE game_id=? AND "
            "turn_order IS NOT NULL ORDER BY turn_order", gs).fetchall()
        if not filas:
            return
        _titulo("El orden de turno")
        print("   " + "  ->  ".join("%d. %s" % (o, n) for n, o in filas))
        return

    filas = conn.execute(
        "SELECT COALESCE(person_name,name), turn_order, COUNT(*), "
        "       SUM(final_rank=1) "
        "FROM players WHERE game_id IN (%s) AND turn_order IS NOT NULL "
        "GROUP BY 1, 2" % marcas, gs).fetchall()
    if not filas:
        return
    puestos = sorted(set(f[1] for f in filas))
    veces = {}
    for nombre, puesto, n, gano in filas:
        veces[(nombre, puesto)] = (n, gano or 0)

    _titulo("Desde qué puesto ha empezado cada uno")
    print("%-14s %s %8s" % ("", "".join("%12s" % ("%do" % p) for p in puestos),
                            "media"))
    for n in gente:
        celdas, suma, total = [], 0, 0
        for p in puestos:
            d = veces.get((n, p))
            if not d:
                celdas.append(".")
                continue
            celdas.append("%d (gano %d)" % d if d[1] else "%d" % d[0])
            suma += p * d[0]
            total += d[0]
        print("%-14s %s %8s" % (n, "".join("%12s" % c for c in celdas),
                                "%.1f" % (suma / total) if total else "-"))
    print()
    print("Si con muchas partidas alguien gana bastante más desde el primer")
    print("puesto que desde el último, ahí hay algo. Con pocas, es ruido.")


def _puntos_por_persona(conn, gs, marcas, gente, jugadas, ganadas):
    """Puntos sumando todas las partidas, con la media.

    La columna «con puntos» no es de adorno: es el denominador de la media, y
    no siempre coincide con las partidas jugadas. Las grabaciones del 18 de
    agosto son de antes de que el mod leyera los puntos y llegan a NULL, así
    que una media de 6 partidas de las que 2 no tienen dato es una media de
    4. Enseñar «6.2» a secas sin decir sobre cuántas es exactamente la clase
    de número que parece más sólido de lo que es."""
    filas = conn.execute(
        "SELECT COALESCE(person_name,name), COUNT(final_points), "
        "       SUM(final_points), AVG(final_points), "
        "       MAX(final_points), MIN(final_points) "
        "FROM players WHERE game_id IN (%s) AND final_points IS NOT NULL "
        "GROUP BY 1" % marcas, gs).fetchall()
    por_nombre = dict((f[0], f[1:]) for f in filas)
    if not por_nombre:
        print()
        print("(sin puntos finales en estas partidas: el mod de entonces todavía")
        print(" no los leía. Las nuevas sí los traen.)")
        return

    _titulo("Puntos por persona, sumando todas las partidas")
    print("%-14s %8s %11s %7s %7s %6s %6s %8s"
          % ("", "partidas", "con puntos", "total", "media", "mejor", "peor",
             "ganadas"))
    orden = sorted(gente, key=lambda n: -(por_nombre.get(n, (0, 0, 0))[2] or 0))
    for n in orden:
        d = por_nombre.get(n)
        if not d:
            print("%-14s %8d %11s %7s %7s %6s %6s %8d"
                  % (n, jugadas.get(n, 0), 0, "-", "-", "-", "-",
                     ganadas.get(n, 0)))
            continue
        cuantas, total, media, mejor, peor = d
        print("%-14s %8d %11d %7d %7.2f %6d %6d %8d"
              % (n, jugadas.get(n, 0), cuantas, total, media, mejor, peor,
                 ganadas.get(n, 0)))
    print()
    print("En las partidas grabadas hasta el 19/8/2026 estos son los puntos")
    print("VISIBLES al ganar: al ganador se le ven todos, pero a los demás no se")
    print("les cuentan las cartas de punto de victoria que llevaran tapadas, así")
    print("que sus medias van cortas. Desde entonces el mod lee los totales en")
    print("la acción de ganar -- cuando la pantalla de resultados ya los enseña")
    print("y no son secreto de nadie -- y la media sale de verdad.")


def _que_se_comercio(conn, gs, marcas, gente):
    """Qué recursos entraron y salieron por comercio, por persona.

    Solo sale con las grabaciones que traen el detalle de la acción (desde el
    19 de agosto de 2026 por la noche). Antes el mod no lo capturaba, y en
    esas partidas la tabla tiene los comercios pero sin contenido."""
    filas = conn.execute(
        "SELECT pa.name, pb.name, t.gave_json, t.received_json FROM trades t "
        "JOIN players pa ON pa.player_id=t.player_a_id "
        "LEFT JOIN players pb ON pb.player_id=t.player_b_id "
        "WHERE t.game_id IN (%s) AND t.gave_json IS NOT NULL" % marcas, gs).fetchall()
    total = conn.execute("SELECT COUNT(*) FROM trades WHERE game_id IN (%s)"
                         % marcas, gs).fetchone()[0]
    if not filas:
        print()
        print("(qué se dio y qué se recibió en cada comercio no está en estas")
        print(" partidas: se grabaron con el mod anterior, que no leía el estado")
        print(" de la acción. Las nuevas sí lo traen.)")
        return

    dio = collections.Counter()
    recibio = collections.Counter()
    for a, b, gave, recv in filas:
        for c in json.loads(gave or "[]"):
            dio[(a, c["resource"])] += c["amount"] or 0
            if b:
                recibio[(b, c["resource"])] += c["amount"] or 0
        for c in json.loads(recv or "[]"):
            recibio[(a, c["resource"])] += c["amount"] or 0
            if b:
                dio[(b, c["resource"])] += c["amount"] or 0

    _titulo("Qué se ha comerciado (%d de %d comercios con detalle)"
            % (len(filas), total))
    recursos = ["Madera", "Arcilla", "Lana", "Cereales", "Mineral"]
    print("%-14s %s" % ("", "".join("%11s" % r for r in recursos)))
    for n in gente:
        celdas = []
        for r in recursos:
            d, e = dio[(n, r)], recibio[(n, r)]
            celdas.append("%+d" % (e - d) if (d or e) else ".")
        print("%-14s %s" % (n, "".join("%11s" % c for c in celdas)))
    print()
    print("El saldo neto por recurso: positivo = se lo llevó comerciando,")
    print("negativo = lo soltó, «+0» = comerció con él y quedó en tablas, y un")
    print("punto = no lo tocó. Dice de qué anda sobrado cada uno y qué busca.")
    print()
    print("Que la suma dé negativa es normal: los cambios con el banco son 4x1")
    print("o 3x1, así que el banco se queda la diferencia.")


def main():
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--partida", type=int, help="una sola partida")
    p.add_argument("--vision", action="store_true",
                   help="las partidas leídas por la visión, no las del mod")
    args = p.parse_args()

    if not os.path.isfile(BASE):
        print("No hay base de datos en %s" % BASE)
        return 1
    conn = sqlite3.connect(BASE)
    try:
        gs = partidas(conn, args.vision, args.partida)
        if not gs:
            print("No hay partidas %s en la base de datos."
                  % ("de la visión" if args.vision else "del mod"))
            if not args.vision:
                print("Guárdalas primero:  py mod_verdad/importar.py")
            return 1
        informe(conn, gs)
        return 0
    finally:
        conn.close()


if __name__ == "__main__":
    sys.exit(main())
