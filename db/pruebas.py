# -*- coding: utf-8 -*-
"""Pruebas de las vistas y de lo que el panel enseña de ellas.

    py -m db.pruebas

Lo que vigilan, sobre todo: que **el global y el detalle por partida digan lo
mismo**. Las dos cosas salen del mismo SQL con un hueco distinto relleno, y
justo por eso un fallo ahí sería invisible -- las dos tablas se pintarían
igual de bien y una de las dos estaría mal.

No comprueban que los números sean los correctos: eso no lo puede saber una
prueba, lo sabe el mod. Comprueban que sean *coherentes entre sí*, que es lo
que se rompe al tocar una consulta.

Necesitan la base con partidas dentro. Si está vacía se saltan solas, porque
una prueba que pasa por no tener datos es peor que no tenerla.
"""
import collections
import io
import json
import os
import re
import sqlite3
import sys
import threading
import urllib.request
from http.server import ThreadingHTTPServer

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RAIZ)

from db import columnas as C
from db import vistas as V
from db import titulares as T

BASE = os.path.join(RAIZ, "catan_stats.db")
PUERTO = 8797          # otro, para no chocar con el panel de verdad

_hechas, _malas, _saltadas = 0, 0, 0


def comprobar(que, bien, detalle=""):
    global _hechas, _malas
    _hechas += 1
    if bien:
        print("OK   %s" % que)
    else:
        _malas += 1
        print("MAL  %s%s" % (que, "   " + detalle if detalle else ""))


def saltar(por_que):
    global _saltadas
    _saltadas += 1
    print("--   %s" % por_que)


def _columna(columnas, filas, nombre):
    i = columnas.index(nombre)
    return [f[i] for f in filas]


# --------------------------------------------------------------------------

def prueba_las_vistas_se_crean(conn):
    """Crearlas es lo primero: si el SQL no compila, todo lo demás sobra."""
    V.crear(conn)
    hay = V.las_que_hay(conn)
    faltan = [v["nombre"] for v in V.VISTAS if v["nombre"] not in hay]
    comprobar("las %d vistas se crean" % len(V.VISTAS), not faltan, str(faltan))


def prueba_cada_vista_tiene_su_grupo():
    """Cada vista en uno y sólo un grupo, y ningún nombre inventado.

    El panel las pinta agrupadas, así que una vista que no esté en `GRUPOS`
    no desaparece -- sale al final bajo «Sin colocar» -- pero eso es un aviso,
    no un sitio. Y un nombre en `GRUPOS` que no exista sería una entrada que
    no pinta nada y que nadie echa de menos."""
    en_grupos = [n for _t, ns in V.GRUPOS for n in ns]
    repes = [n for n in set(en_grupos) if en_grupos.count(n) > 1]
    comprobar("ninguna vista está en dos grupos", not repes, str(repes))

    inventados = [n for n in en_grupos if n not in V.POR_NOMBRE]
    comprobar("los grupos no nombran vistas que no existen", not inventados,
              str(inventados))

    sueltas = [v["nombre"] for v in V.VISTAS if v["nombre"] not in en_grupos]
    comprobar("todas las vistas tienen grupo", not sueltas, str(sueltas))

    # Y que `por_grupos()` las devuelva todas: es lo que el panel enseña, y
    # perder una ahí es perderla de la pantalla sin que falte de la base.
    salen = [v["nombre"] for _t, vs in V.por_grupos() for v in vs]
    comprobar("el panel recibe las %d, agrupadas" % len(V.VISTAS),
              sorted(salen) == sorted(v["nombre"] for v in V.VISTAS),
              "%d de %d" % (len(salen), len(V.VISTAS)))


def prueba_todas_contestan(conn, partidas):
    """Cada vista, entera y filtrada, sin reventar y con las mismas columnas."""
    mal = []
    for v in V.VISTAS:
        try:
            cg, _fg = V.consultar(conn, v["nombre"])
            cp, _fp = V.consultar(conn, v["nombre"], partidas[0])
        except sqlite3.Error as e:
            mal.append("%s: %s" % (v["nombre"], e))
            continue
        if cg != cp:
            mal.append("%s cambia de columnas al filtrar" % v["nombre"])
    comprobar("las %d contestan, en global y por partida" % len(V.VISTAS),
              not mal, "; ".join(mal))


def prueba_el_filtro_de_partida_filtra_de_verdad(conn, partidas):
    """Que elegir una partida en el panel filtre TODAS las vistas.

    `prueba_todas_contestan` sólo mira que no revienten y que las columnas
    sean las mismas. Una vista puede contestar perfectamente y estar
    enseñando las cuatro partidas: sale una tabla creíble y no hay forma de
    notarlo mirándola.

    Aquí se comprueba con dos invariantes que valen para casi todas sin saber
    qué hace cada una:

      - si trae una columna de partida, todas sus filas tienen que ser de esa
      - si trae nombres, tienen que ser de gente que jugó esa partida

    Las dos que no tienen ni una cosa ni otra -- `amigos_tiradas` y
    `amigos_mazo` -- se comprueban por su total más abajo."""
    columnas_partida = ("partida", "game_id")
    columnas_gente = ("quien", "con_quien", "a_quien", "a")
    fallos, revisadas, sin_forma = [], 0, []
    for p in partidas:
        gente = set(r[0] for r in conn.execute(
            "SELECT quien FROM jugadores WHERE game_id=?", (p,)))
        # Dos nombres que no son personas y tienen que estar permitidos:
        # 'la banca' es con quien se cambia en los puertos, y 'nadie' es el
        # puerto que no pilló ninguno -- que es media razón de que la vista de
        # puertos exista. Se listan aquí y no se dejan pasar por parecerse a
        # algo: cualquier otro nombre que no juegue esa partida sigue siendo
        # el fallo que esta prueba busca.
        gente |= {"la banca", "nadie"}
        for v in V.VISTAS:
            nombre = v["nombre"]
            c, f = V.consultar(conn, nombre, p)
            mira_partida = [x for x in columnas_partida if x in c]
            mira_gente = [x for x in columnas_gente if x in c]
            if not mira_partida and not mira_gente:
                if nombre not in sin_forma:
                    sin_forma.append(nombre)
                continue
            revisadas += 1
            for col in mira_partida:
                otras = set(_columna(c, f, col)) - {p}
                if otras:
                    fallos.append("%s(p%d): %s trae %s" % (nombre, p, col, otras))
            for col in mira_gente:
                fuera = set(x for x in _columna(c, f, col)
                            if x is not None) - gente
                if fuera:
                    fallos.append("%s(p%d): %s trae a %s, que no jugó"
                                  % (nombre, p, col, fuera))
    comprobar("al pedir una partida, ninguna vista cuela otra (%d revisiones)"
              % revisadas, not fallos, "; ".join(fallos[:4]))

    # Y las dos que no llevan ni partida ni nombres, por su total.
    for p in partidas:
        c, f = V.consultar(conn, "amigos_tiradas", p)
        suyas = conn.execute("SELECT COUNT(*) FROM rolls WHERE game_id=?",
                             (p,)).fetchone()[0]
        if sum(_columna(c, f, "veces")) != suyas:
            return comprobar("y las tiradas filtradas son las de esa partida",
                             False, "p%d: %d vs %d"
                             % (p, sum(_columna(c, f, "veces")), suyas))
    comprobar("y las tiradas filtradas son las de esa partida", True)

    # `amigos_mazo` tampoco lleva partida ni nombres. Su total son las cartas
    # de desarrollo compradas: todas tienen que estar, con tipo conocido o
    # como «sin saber».
    # La tabla tiene que CUADRAR, y son dos cuentas encadenadas:
    #
    #   jugadas + en la mano            = las que se compraron
    #   eso     + las que nadie compro  = el mazo entero
    #
    # La segunda es la que se anadio el 2 de septiembre de 2026, cuando la
    # tabla ensenaba lo que salio sin decir contra que. Y cuadra sola: si un
    # dia el mazo de una mesa de seis se apunta mal, o una compra no se
    # importa, la resta deja de dar y salta aqui.
    for p in partidas:
        c, f = V.consultar(conn, "amigos_mazo", p)
        por_carta = dict(zip(_columna(c, f, "carta"),
                             _columna(c, f, "salieron")))
        sin_jugar = por_carta.pop("compradas y sin jugar", 0) or 0
        en_el_mazo = por_carta.pop("nunca se compraron", 0) or 0
        de_otros = por_carta.pop("las compraron otros", 0) or 0
        jugadas = sum(x for x in por_carta.values() if x is not None)

        compradas = conn.execute(
            "SELECT COUNT(*) FROM dev_card_purchases WHERE game_id=?",
            (p,)).fetchone()[0]
        if jugadas + sin_jugar + de_otros != compradas:
            return comprobar(
                "y el mazo filtrado son las cartas de esa partida", False,
                "p%d: %d jugadas + %d en la mano + %d de otros != %d compradas"
                % (p, jugadas, sin_jugar, de_otros, compradas))

        eran = conn.execute("SELECT COUNT(*) FROM players WHERE game_id=?",
                            (p,)).fetchone()[0]
        mazo = sum(V.MAZO[eran].values())
        if compradas + en_el_mazo != mazo:
            return comprobar(
                "y el mazo filtrado son las cartas de esa partida", False,
                "p%d: %d compradas + %d sin comprar != %d del mazo de %d"
                % (p, compradas, en_el_mazo, mazo, eran))
    comprobar("y el mazo filtrado son las cartas de esa partida", True)
    if sin_forma:
        print("     (sin columna de partida ni de nombre: %s)"
              % ", ".join(sin_forma))


def prueba_el_global_es_la_suma(conn, amigas):
    """Lo comprado en cada partida tiene que sumar lo comprado en total.

    Esta es la prueba que de verdad importa. Si el hueco `{donde}` se colara
    en un sitio y no en otro -- por ejemplo en la consulta de fuera pero no en
    una subconsulta -- las dos tablas seguirían saliendo, y una mentiría."""
    if len(amigas) < 2:
        return saltar("el global contra la suma (hacen falta 2 partidas)")
    cg, fg = V.consultar(conn, "amigos_desarrollo")
    total = dict(zip(_columna(cg, fg, "quien"), _columna(cg, fg, "compradas")))
    suma = {}
    for p in amigas:
        c, f = V.consultar(conn, "amigos_desarrollo", p)
        for quien, n in zip(_columna(c, f, "quien"), _columna(c, f, "compradas")):
            suma[quien] = suma.get(quien, 0) + n
    comprobar("las cartas de cada partida suman las del global",
              suma == total, "%s vs %s" % (suma, total))


def prueba_las_tiradas_cuadran(conn, amigas):
    cg, fg = V.consultar(conn, "amigos_tiradas")
    total = sum(_columna(cg, fg, "veces"))
    suma = 0
    for p in amigas:
        c, f = V.consultar(conn, "amigos_tiradas", p)
        suma += sum(_columna(c, f, "veces"))
    comprobar("las tiradas de cada partida suman las del global",
              suma == total, "%d vs %d" % (suma, total))

    # `veces_normales` es el mismo reparto que `porcentaje_normal` pero en
    # tiradas, así que tiene que sumar EXACTAMENTE las tiradas que hubo. Si
    # se escribe con el divisor equivocado (36 fijo, o las tiradas de una sola
    # partida) la columna sigue saliendo y sigue pareciendo razonable: 8,2
    # frente a 8 no chirría. Sólo el total lo delata.
    esperadas = sum(_columna(cg, fg, "veces_normales"))
    comprobar("las tiradas esperadas suman las que hubo",
              abs(esperadas - total) < 0.6, "%.1f vs %d" % (esperadas, total))
    # Y lo mismo en el mazo, con las cartas que se han podido identificar.
    cm, fm = V.consultar(conn, "amigos_mazo")
    sal = [x for x in _columna(cm, fm, "deberian_salir") if x is not None]
    con = [s for s, e in zip(_columna(cm, fm, "salieron"),
                             _columna(cm, fm, "deberian_salir"))
           if e is not None]
    if sal:
        comprobar("las cartas esperadas suman las que se saben",
                  abs(sum(sal) - sum(con)) < 0.6,
                  "%.1f vs %d" % (sum(sal), sum(con)))


def prueba_la_suerte_cuadra(conn, amigas):
    """La suerte: que la cuenta sea la que dice, y que la ventana sea la buena.

    Lo que puede salir mal aquí no es el porcentaje, es **desde cuándo** se le
    cuentan las tiradas a una pieza. Si se le contaran todas las de la
    partida, quien construye en el turno 50 tendría mala suerte garantizada y
    la tabla mediría a qué hora construye cada uno. Y el error sería invisible:
    los números seguirían saliendo, y hasta ordenarían parecido.

    Por eso la comprobación de verdad no mira la vista, mira los datos: cada
    producción que HUBO tiene que caer dentro de la ventana de alguna de sus
    piezas. Si la ventana empieza un turno tarde, aparecen producciones que
    según la vista no podían pasar -- y esas dos cosas salen de sitios
    distintos: una la dedujo el importador del estado del tablero, la otra es
    aritmética de turnos."""
    if not amigas:
        return saltar("la suerte (no hay partidas de amigos)")
    c, f = V.consultar(conn, "amigos_suerte")
    if not f:
        return saltar("la suerte (no hay edificios con número)")
    i = {n: c.index(n) for n in ("quien", "casillas", "puntitos", "le_tocaba",
                                 "le_toco", "de_mas", "suerte", "margen",
                                 "se_sale")}
    mal = []
    for fila in f:
        toco, tocaba = fila[i["le_toco"]], fila[i["le_tocaba"]]
        if abs((toco - tocaba) - fila[i["de_mas"]]) > 0.11:
            mal.append((fila[i["quien"]], "de_mas"))
        if tocaba and abs(100.0 * toco / tocaba - fila[i["suerte"]]) > 0.11:
            mal.append((fila[i["quien"]], "suerte"))
    comprobar("la suerte es lo que salió entre lo que tocaba", not mal, str(mal))

    # `le_toco` son COBROS, no tiradas. Si tiene tres sitios en el 4, un 4 es
    # UNA tirada y TRES cobros, y la columna suma tres.
    #
    # Esto no lo comprobaba nada, y estuvo escrito al revés -- «tiradas que
    # salieron en sus números» -- en la vista, en las columnas, en PROYECTO.md
    # y en la portada, hasta el 3 de septiembre de 2026. La cuenta siempre
    # estuvo bien; el nombre no. Y un nombre equivocado sobre una columna bien
    # calculada no lo caza ninguna prueba de las que comparan números: todas
    # cuadraban, porque el número era correcto.
    #
    # Así que aquí se fija CUÁL DE LAS DOS COSAS es, y con eso la palabra que
    # está escrita fuera deja de poder cambiar sola: los cobros nunca pueden
    # ser menos que las tiradas que le salieron, y en alguien tienen que ser
    # MÁS -- si fueran iguales para todos, la columna sí serían tiradas.
    salieron = dict(conn.execute("""
        WITH sitios AS (
            SELECT p.game_id, COALESCE(p.person_name, p.name) AS quien,
                   t.number AS numero,
                   CASE WHEN bu.turn_number IS NULL OR bu.turn_number = 0
                        THEN -1 ELSE bu.turn_number END AS desde
              FROM players p
              JOIN buildings bu ON bu.player_id = p.player_id
                               AND bu.type IN ('poblado','ciudad')
              JOIN building_tiles bt ON bt.building_id = bu.building_id
              JOIN tiles t ON t.tile_id = bt.tile_id
             WHERE t.number IS NOT NULL
               AND p.game_id IN (SELECT game_id FROM partidas
                                  WHERE con_amigos = 1)
        )
        SELECT s.quien, COUNT(DISTINCT r.roll_id)
          FROM sitios s
          JOIN rolls r ON r.game_id = s.game_id
                      AND r.turn_number > s.desde
                      AND r.value = s.numero
         GROUP BY s.quien"""))
    menos = [(fila[i["quien"]], fila[i["le_toco"]],
              salieron.get(fila[i["quien"]], 0))
             for fila in f
             if fila[i["le_toco"]] < salieron.get(fila[i["quien"]], 0)]
    comprobar("`le_toco` nunca es menos que las tiradas que le salieron",
              not menos, str(menos))
    dobles = [fila[i["quien"]] for fila in f
              if fila[i["le_toco"]] > salieron.get(fila[i["quien"]], 0)]
    comprobar("y en alguien es MÁS, o sea que son cobros y no tiradas",
              dobles, "en nadie: la columna estaría contando tiradas")

    # `tiros` -- cuántas veces tiró él el dado -- contra las dos cosas con las
    # que se puede confundir.
    #
    # Primero: es la MISMA columna que `tiros` en «Los sietes de cada uno»,
    # que es de donde sale el porcentaje de sietes de cada uno. Con el mismo
    # nombre en dos vistas del mismo grupo, que dijeran números distintos
    # sería el caso de `le_costo` otra vez, y ese no lo cazó nada.
    #
    # Y segundo: NO es `tiradas_contadas`. Esa cuenta todas las tiradas de la
    # mesa que le podían pagar, las tire quien las tire, así que la suya tiene
    # que ser menor para todo el mundo -- se juega a cuatro o más. Si algún
    # día salieran iguales, es que una de las dos se ha copiado de la otra.
    c2, f2 = V.consultar(conn, "amigos_sietes")
    j2 = {n: c2.index(n) for n in ("quien", "tiros")}
    alli = dict((fila[j2["quien"]], fila[j2["tiros"]]) for fila in f2)
    i["tiros"] = c.index("tiros")
    i["tiradas_contadas"] = c.index("tiradas_contadas")
    distintos = [(fila[i["quien"]], fila[i["tiros"]], alli.get(fila[i["quien"]]))
                 for fila in f if fila[i["tiros"]] != alli.get(fila[i["quien"]])]
    comprobar("`tiros` es el mismo número que en «Los sietes de cada uno»",
              not distintos, str(distintos))
    suyas = [(fila[i["quien"]], fila[i["tiros"]], fila[i["tiradas_contadas"]])
             for fila in f if fila[i["tiros"]] >= fila[i["tiradas_contadas"]]]
    comprobar("y son las SUYAS, no las de la mesa (`tiradas_contadas`)",
              not suyas, str(suyas))

    # Y `sitios` son las casillas con número que toca, contando una vez cada
    # pareja pieza-casilla. Una ciudad no cuenta doble: los dados no saben si
    # ahí hay poblado o ciudad.
    esperados = dict(conn.execute("""
        SELECT COALESCE(p.person_name, p.name), COUNT(*)
          FROM players p
          JOIN buildings bu ON bu.player_id = p.player_id
                           AND bu.type IN ('poblado','ciudad')
          JOIN building_tiles bt ON bt.building_id = bu.building_id
          JOIN tiles t ON t.tile_id = bt.tile_id
         WHERE t.number IS NOT NULL
           AND p.game_id IN (SELECT game_id FROM partidas WHERE con_amigos = 1)
         GROUP BY 1"""))
    difieren = [(fila[i["quien"]], fila[i["casillas"]],
                 esperados.get(fila[i["quien"]]))
                for fila in f if fila[i["casillas"]] != esperados.get(fila[i["quien"]])]
    comprobar("y `casillas` son sus casillas con número", not difieren,
              str(difieren))

    # La ventana. Cada producción tiene que caber en la de alguna pieza suya
    # sobre una casilla de ese número.
    fuera = conn.execute("""
        SELECT COUNT(*) FROM resource_gains g
          JOIN rolls r ON r.roll_id = g.roll_id
         WHERE g.source = 'produccion'
           AND NOT EXISTS (
               SELECT 1 FROM buildings bu
                 JOIN building_tiles bt ON bt.building_id = bu.building_id
                 JOIN tiles t ON t.tile_id = bt.tile_id
                WHERE bu.player_id = g.player_id
                  AND bu.type IN ('poblado','ciudad')
                  AND t.number = r.value
                  AND r.turn_number > CASE WHEN bu.turn_number IS NULL
                                             OR bu.turn_number = 0
                                           THEN -1 ELSE bu.turn_number END)
    """).fetchone()[0]
    comprobar("ninguna producción cae fuera de la ventana de sus piezas",
              fuera == 0, "%d producciones" % fuera)

    # Y la cuenta entera, rehecha aquí a mano. Es reimplementarla, sí, y a
    # propósito: lo que se vigila es que un 6 NO pese lo mismo que un 2. Sin
    # esto, cambiar `6 - ABS(7 - numero)` por un 1 dejaría la tabla igual de
    # creíble -- todas las columnas seguirían saliendo, ordenarían parecido y
    # sólo estarían mal. Aquí el factor está escrito aparte y en otro idioma.
    pips_de = {}
    tocaba_de = {}
    toco_de = {}
    piezas = conn.execute("""
        SELECT COALESCE(p.person_name, p.name), p.game_id, t.number,
               CASE WHEN bu.turn_number IS NULL OR bu.turn_number = 0
                    THEN -1 ELSE bu.turn_number END
          FROM players p
          JOIN buildings bu ON bu.player_id = p.player_id
                           AND bu.type IN ('poblado','ciudad')
          JOIN building_tiles bt ON bt.building_id = bu.building_id
          JOIN tiles t ON t.tile_id = bt.tile_id
         WHERE t.number IS NOT NULL
           AND p.game_id IN (SELECT game_id FROM partidas WHERE con_amigos = 1)
    """).fetchall()
    tiradas = {}
    for gid in set(p[1] for p in piezas):
        tiradas[gid] = conn.execute(
            "SELECT turn_number, value FROM rolls WHERE game_id = ?",
            (gid,)).fetchall()
    for quien, gid, numero, desde in piezas:
        pips = 6 - abs(7 - numero)
        cuantas = [v for (tn, v) in tiradas[gid] if tn is not None and tn > desde]
        pips_de[quien] = pips_de.get(quien, 0) + pips
        tocaba_de[quien] = tocaba_de.get(quien, 0.0) + len(cuantas) * pips / 36.0
        toco_de[quien] = toco_de.get(quien, 0) + sum(1 for v in cuantas
                                                     if v == numero)
    difieren = []
    for fila in f:
        q = fila[i["quien"]]
        if fila[i["puntitos"]] != pips_de.get(q):
            difieren.append((q, "puntitos", fila[i["puntitos"]], pips_de.get(q)))
        if fila[i["le_toco"]] != toco_de.get(q):
            difieren.append((q, "le_toco", fila[i["le_toco"]], toco_de.get(q)))
        if abs(fila[i["le_tocaba"]] - tocaba_de.get(q, 0)) > 0.06:
            difieren.append((q, "le_tocaba", fila[i["le_tocaba"]],
                             round(tocaba_de.get(q, 0), 2)))
    comprobar("y un 6 pesa cinco veces lo que un 2, no lo mismo",
              not difieren, str(difieren[:3]))

    # El margen: cuánto mueve el azar. Se rehace aquí igual que lo anterior, y
    # por el mismo motivo -- pero con una trampa propia que sí hay que vigilar.
    #
    # UNA TIRADA RESUELVE TODAS LAS CASILLAS A LA VEZ. Dos casillas suyas en
    # el 6 aciertan o fallan juntas, nunca una sí y otra no. Si se calculara
    # casilla por casilla como si fueran independientes, el margen saldría más
    # pequeño del que es y la tabla diría que alguien «se sale» cuando no.
    # Por eso la varianza se suma TIRADA a tirada, y por eso esta prueba
    # también se escribe así.
    import math
    from collections import defaultdict
    porjuego = defaultdict(list)
    for quien, gid, numero, desde in piezas:
        porjuego[(quien, gid)].append((numero, desde))
    var_de, esp_de, real_de = {}, {}, {}
    for (quien, gid), lista in porjuego.items():
        for tn, valor in tiradas[gid]:
            if tn is None:
                continue
            cuantas = defaultdict(int)
            for numero, desde in lista:
                if tn > desde:
                    cuantas[numero] += 1
            if not cuantas:
                continue
            m1 = sum((6 - abs(7 - n)) / 36.0 * k for n, k in cuantas.items())
            m2 = sum((6 - abs(7 - n)) / 36.0 * k * k for n, k in cuantas.items())
            esp_de[quien] = esp_de.get(quien, 0.0) + m1
            var_de[quien] = var_de.get(quien, 0.0) + m2 - m1 * m1
            real_de[quien] = real_de.get(quien, 0) + cuantas.get(valor, 0)
    fallan = []
    for fila in f:
        q = fila[i["quien"]]
        sd = math.sqrt(var_de[q])
        margen = 100.0 * sd / esp_de[q]
        sale = (real_de[q] - esp_de[q]) / sd
        if abs(fila[i["margen"]] - margen) > 0.06:
            fallan.append((q, "margen", fila[i["margen"]], round(margen, 2)))
        if abs(fila[i["se_sale"]] - sale) > 0.006:
            fallan.append((q, "se_sale", fila[i["se_sale"]], round(sale, 3)))
    comprobar("el margen cuenta la tirada entera, no casilla por casilla",
              not fallan, str(fallan[:3]))

    # AQUÍ HABÍA UNA COMPROBACIÓN QUE ERA FALSA y la midió esta suite: «a más
    # tiradas en juego, menos margen». Suena a ley y no lo es. elGato tiene
    # 216,9 tiradas esperadas con un margen del 5,9% y TheClonne 247,2 con un
    # 6,2%: más en juego y MÁS margen.
    #
    # El motivo es el mismo que hace que la varianza se sume por tirada:
    # varias casillas en el mismo número se mueven juntas. Quien las tiene
    # repartidas cobra más regular que quien las amontona, aunque los dos
    # esperen lo mismo. Así que el margen no sale del total, sale de CÓMO
    # están repartidas -- y por eso no se puede comprobar con una regla de
    # «más es menos». Queda escrito para que no vuelva a parecer obvio.
    comprobar("el margen nunca es negativo ni cero",
              all(fila[i["margen"]] > 0 for fila in f),
              str([fila[i["margen"]] for fila in f]))


# La version de Python que el README promete. Si algun dia hace falta una
# mas nueva, se cambia AQUI y la prueba obliga a cambiar tambien el README.
PYTHON_MINIMO = (3, 7)


def io_leer(ruta):
    with open(ruta, encoding="utf-8") as fh:
        return fh.read()


def prueba_una_maquina_recien_clonada_arranca():
    """Que el `git clone` + `importar.py` del README funcione de verdad.

    Es la promesa del proyecto entera: «descárgatelo y úsalo». Y estaba rota
    sin que se notase, porque aquí el `.db` ya existe desde hace semanas.

    El esquema base vive en `db/schema.sql` y nadie lo aplicaba. En una base
    recién hecha `crear_tablas` moría en el primer `ALTER TABLE robber_moves
    ADD COLUMN cause`, porque `PRAGMA table_info` de una tabla que no existe
    no da error -- da cero columnas -- y el ALTER se lanzaba igual.

    Se comprueba sobre una base de datos de mentira en un directorio temporal,
    sin tocar la de verdad."""
    import sqlite3, tempfile, shutil
    try:
        from mod_verdad import importar as _imp
    except Exception as e:
        return saltar("clon recién hecho (%s)" % e)

    carpeta = tempfile.mkdtemp(prefix="catan_clon_")
    try:
        conn = sqlite3.connect(os.path.join(carpeta, "recien.db"))
        try:
            _imp.crear_tablas(conn)          # <- esto es lo que petaba
            hay = {r[0] for r in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'")}
            # Las del esquema base, que son las que no crea `crear_tablas`.
            faltan = {"games", "players", "rolls", "buildings",
                      "robber_moves", "steals", "harbors"} - hay
            comprobar("una base recién creada sale con el esquema entero",
                      not faltan, "faltan: %s" % sorted(faltan))
            # Y las migraciones han corrido de verdad, no se han saltado.
            cols = {r[1] for r in conn.execute(
                "PRAGMA table_info(robber_moves)")}
            comprobar("y con las columnas añadidas después",
                      "cause" in cols, sorted(cols))
        finally:
            conn.close()
    finally:
        shutil.rmtree(carpeta, ignore_errors=True)

    # Y lo primero que dice el README que hagas tiene que existir.
    # Hubo un `panel.bat` para abrirlo con doble clic. Se quito: no aportaba
    # nada y era una segunda puerta de entrada que mantener. Lo que sigue
    # importando es que el README no mande a un fichero que no existe, y de
    # eso se encarga la prueba de los ficheros nombrados.
    comprobar("el panel se arranca con py panel.py",
              os.path.exists(os.path.join(RAIZ, "panel.py")))

    # Y NINGUN fichero que nombre el README puede faltar. Esto no es
    # cosmetica: media docena de ficheros no van al repositorio (la mitad de
    # la vision, el diario, la base), y una portada que mande a `mirar.py` o
    # a `DIARIO.md` deja al que se lo descarga buscando algo que no existe.
    # Aqui siempre pasa --los ficheros estan-- pero se cae sola el dia que se
    # nombre uno que no sube, porque no estaria en la carpeta tampoco.
    #
    # Solo el README. `PROYECTO.md` documenta a proposito la mitad que no
    # sube todavia, y ahi es correcto nombrarla.
    portada = io_leer(os.path.join(RAIZ, "README.md"))
    nombrados = set(re.findall(r"`([\w./-]+\.(?:py|md|txt|sql|ps1|json))`",
                               portada))
    nombrados |= set(re.findall(r"\]\(([\w./-]+)\)", portada))
    nombrados.discard("catan_stats.db")     # se crea al importar
    faltan = sorted(n for n in nombrados
                    if not os.path.exists(os.path.join(RAIZ, n)))
    comprobar("y el README no manda a ningun fichero que no exista",
              not faltan, str(faltan))

    # Y que el Python que promete el README sea verdad. `feature_version` le
    # dice al analizador «hazte el de la 3.7»: si alguien mete un `match`, un
    # walrus o una union `int | None`, esto revienta y avisa de que el
    # requisito ha subido. Es syntaxis, no APIs -- de eso no protege -- pero
    # es lo que se cuela sin querer.
    import ast
    duros = []
    for raiz, ds, fs in os.walk(RAIZ):
        ds[:] = [d for d in ds
                 if d not in ("__pycache__", ".git", ".vscode", "copias",
                              "datos", "crudo", "modelos", "fotos",
                              "debug_ocr", "registros", "referencias_tablero")]
        for f in sorted(fs):
            if not f.endswith(".py"):
                continue
            ruta_py = os.path.join(raiz, f)
            try:
                ast.parse(io_leer(ruta_py), filename=f,
                          feature_version=PYTHON_MINIMO)
            except SyntaxError as e:
                duros.append("%s: %s" % (os.path.relpath(ruta_py, RAIZ), e.msg))
            except Exception:
                pass
    comprobar("todo el codigo compila con Python %d.%d, que es lo que promete"
              % PYTHON_MINIMO, not duros, str(duros[:3]))
    comprobar("y el README dice esa misma version",
              "Python %d.%d" % PYTHON_MINIMO in io_leer(
                  os.path.join(RAIZ, "README.md")))

    # Sin licencia, «descárgatelo y úsalo» es mentira: por defecto no hay
    # permiso para nada. Y tiene que ser la MIT SIN retocar, que si no GitHub
    # no la reconoce y deja de poner «MIT» en la ficha del repositorio.
    ruta = os.path.join(RAIZ, "LICENSE")
    comprobar("hay licencia", os.path.exists(ruta))
    if os.path.exists(ruta):
        with open(ruta, encoding="utf-8") as f:
            texto = f.read()
        for trozo in ("MIT License",
                      "Permission is hereby granted, free of charge",
                      "THE SOFTWARE IS PROVIDED \"AS IS\""):
            comprobar("la licencia lleva %r" % trozo[:28], trozo in texto)
        comprobar("y con dueño y año",
                  "Copyright (c) 2026 Mario Razquin" in texto)


def prueba_la_base_esta_entera(conn):
    """Claves ajenas de verdad, no de adorno.

    SQLite trae las claves ajenas APAGADAS y es una opción **por conexión**:
    tener `PRAGMA foreign_keys = ON` en el `schema.sql` no vale para nada más
    que para la conexión que creó las tablas. Las cuarenta y pico referencias
    del esquema eran documentación, no una comprobación.

    Aquí se mira lo único que se puede mirar desde fuera: que no haya ni una
    fila huérfana. Y aparte, que el importador -- que es quien escribe -- las
    encienda, porque es lo que impide que la primera aparezca."""
    huerfanas = conn.execute("PRAGMA foreign_key_check").fetchall()
    comprobar("no hay ni una fila apuntando a algo que no existe",
              not huerfanas, str(huerfanas[:5]))

    import inspect
    try:
        from mod_verdad import importar as _imp
        fuente = inspect.getsource(_imp.main)
    except Exception as e:
        return saltar("que el importador encienda las claves ajenas (%s)" % e)
    comprobar("y el importador las enciende al escribir",
              'PRAGMA foreign_keys = ON' in fuente)

    # Toda columna que apunta a otra tabla, con índice. Sin él, SQLite recorre
    # la tabla hija ENTERA cada vez que se borra una fila padre -- y con las
    # claves ajenas encendidas eso pasa de verdad, al rehacer una partida.
    indexadas = set()
    for (tabla,) in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' "
            "AND name NOT LIKE 'sqlite_%'"):
        for idx in conn.execute("PRAGMA index_list(%s)" % tabla):
            cols = [c[2] for c in conn.execute("PRAGMA index_info(%s)" % idx[1])]
            if cols:
                indexadas.add((tabla, cols[0]))
    sin_indice = []
    for (tabla,) in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' "
            "AND name NOT LIKE 'sqlite_%'"):
        for fk in conn.execute("PRAGMA foreign_key_list(%s)" % tabla):
            if (tabla, fk[3]) not in indexadas:
                sin_indice.append("%s.%s" % (tabla, fk[3]))
    comprobar("y cada clave ajena tiene su índice (%d columnas)"
              % len(sin_indice or [1]) if sin_indice else
              "y cada clave ajena tiene su índice",
              not sin_indice, str(sorted(set(sin_indice))))


def _columnas_declaradas():
    """Lo que `db/columnas.py` declara: las comunes y las de cada vista.

    Un solo lector para los dos que lo necesitan -- la prueba de que todas
    las columnas estan explicadas y la de que ninguna dice dos cosas. Con dos
    lectores acabarian discrepando, que es el error del que va la segunda.

    Estuvo leyendo las tablas de PROYECTO.md a golpe de regex. Ahora el texto
    vive en un `.py` y se lee importandolo: menos codigo, y una columna sin
    explicar la canta el propio diccionario en vez de una expresion regular
    que un dia deja de casar y se calla."""
    comunes = set(C.COMUNES)
    por_vista = {n: set(d) for n, d in C.POR_VISTA.items()}
    return comunes, por_vista


def prueba_todas_las_columnas_estan_explicadas(conn):
    """Cada columna de cada vista, explicada en `db/columnas.py`.

    Un diccionario de columnas escrito a mano se queda viejo el primer día que
    alguien añade una columna, y no se nota: el README sigue ahí, sigue
    pareciendo completo, y la que falta es justo la que no se entiende. Esto
    lo convierte en una promesa que se rompe sola cuando deja de ser verdad.

    Se acepta que la explicación esté en la tabla de las comunes (`quien`,
    `partida`, `turno`...) o en la sección de su propia vista, que es la que
    empieza por `##### \\`nombre\\``."""
    comunes, por_vista = _columnas_declaradas()

    faltan, sin_seccion = [], []
    for v in V.VISTAS:
        cols, _f = V.consultar(conn, v["nombre"])
        if v["nombre"] not in por_vista:
            sin_seccion.append(v["nombre"])
            continue
        for c in cols:
            if c not in comunes and c not in por_vista[v["nombre"]]:
                faltan.append("%s.%s" % (v["nombre"], c))
    comprobar("cada vista tiene su apartado de columnas",
              not sin_seccion, str(sin_seccion))
    comprobar("y ninguna columna se queda sin explicar (%d vistas)"
              % len(V.VISTAS), not faltan, str(faltan[:5]))

    # Y al revés: nada explicado que ya no exista. Es lo que deja el catálogo
    # lleno de columnas fantasma después de un par de cambios de nombre.
    hay = set()
    for v in V.VISTAS:
        cols, _f = V.consultar(conn, v["nombre"])
        hay.update(cols)
    sobran = sorted((comunes | set().union(*por_vista.values())) - hay)
    comprobar("y no se explica ninguna columna que ya no exista", not sobran,
              str(sobran))


def prueba_los_puntos_cuadran(conn):
    """`cartas_de_punto` no puede ser negativo ni salirse del mazo.

    El tope sale de `V.MAZO`, y de la mesa de CADA partida, no de un 5
    escrito aquí. La diferencia importa: con 5 o 6 el mazo trae 6 cartas de
    punto en vez de 5, y coger el mayor de los dos como tope único aflojaría
    la comprobación también en las mesas de cuatro, donde 6 es imposible. Un
    negativo querría decir que la resta está mal, y saldría callado."""
    c, f = V.consultar(conn, "amigos_puntos")
    tap = [t for t in _columna(c, f, "cartas_de_punto") if t is not None]
    if not tap:
        return saltar("las cartas de punto (ninguna partida las puede cuadrar)")
    mesa = dict(conn.execute("SELECT DISTINCT game_id, jugadores FROM jugadores"))
    i_p, i_t = c.index("partida"), c.index("cartas_de_punto")
    imposibles = []
    for fila in f:
        t = fila[i_t]
        if t is None:
            continue
        tope = V.MAZO.get(mesa.get(fila[i_p]), {}).get("punto_victoria", 5)
        if not 0 <= t <= tope:
            imposibles.append("partida %s: %s con un mazo de %d"
                              % (fila[i_p], t, tope))
    comprobar("ningún jugador tiene cartas de punto imposibles",
              not imposibles, str(imposibles[:3]))

    # Y la fila entera tiene que sumar los puntos con los que se acabó. Es la
    # comprobación que convierte la tabla en una cuenta y no en una lista de
    # números que se parecen: poblados + 2 por ciudad + 2 por premio + cartas.
    i = {n: c.index(n) for n in ("quien", "puntos", "poblados", "ciudades",
                                 "carretera_larga", "mayor_ejercito",
                                 "cartas_de_punto")}
    mal = []
    for fila in f:
        if any(fila[i[n]] is None for n in i if n != "quien"):
            continue
        suma = (fila[i["poblados"]] + 2 * fila[i["ciudades"]]
                + 2 * fila[i["carretera_larga"]] + 2 * fila[i["mayor_ejercito"]]
                + fila[i["cartas_de_punto"]])
        if suma != fila[i["puntos"]]:
            mal.append((fila[i["quien"]], suma, fila[i["puntos"]]))
    comprobar("cada fila suma los puntos con los que acabó", not mal, str(mal[:3]))


def prueba_las_dos_cuentas_de_lo_tapado_coinciden(conn):
    """Las cartas de punto se saben por dos caminos. Tienen que dar lo mismo.

    Uno resta del total los edificios y los dos premios. El otro es la
    diferencia entre los puntos totales y los que la partida enseñaba en el
    panel, los dos leídos del juego. No comparten ni un dato intermedio, así
    que si coinciden es que las dos están bien -- y si dejan de coincidir, hay
    algo roto y esto es lo único que lo diría.

    La segunda cuenta ya no sale en la tabla -- repetía a la de al lado y sólo
    hacía ruido -- así que aquí se pide el CTE a pelo. Que no se enseñe no
    quiere decir que se deje de mirar: es al revés, se quita de la vista
    PORQUE esto la vigila."""
    sql = (V._con(V._J, V._PTS)
           + " SELECT quien, cartas_de_punto, cartas_de_punto_del_mod FROM pts"
           ).replace("{donde}", "con_amigos = 1")
    cur = conn.execute(sql)
    c = [d[0] for d in cur.description]
    f = cur.fetchall()
    a = _columna(c, f, "cartas_de_punto")
    b = _columna(c, f, "cartas_de_punto_del_mod")
    quien = _columna(c, f, "quien")
    juntos = [(q, x, y) for q, x, y in zip(quien, a, b)
              if x is not None and y is not None]
    if not juntos:
        return saltar("las dos cuentas de lo tapado (no hay con qué)")
    mal = [t for t in juntos if t[1] != t[2]]
    comprobar("la resta y lo que dice el mod dan las mismas cartas tapadas "
              "(%d jugadores)" % len(juntos), not mal, str(mal))


def prueba_las_cartas_cuadran(conn):
    """Ninguna cuenta puede pasarse de lo que se compró."""
    c, f = V.consultar(conn, "amigos_desarrollo")
    sin = [s for s in _columna(c, f, "sin_saber") if s is not None]
    comprobar("nadie juega más cartas de las que compró",
              all(s >= 0 for s in sin), str(sin))


def prueba_los_robos_cuadran(conn):
    """Cada robo tiene un ladrón y una víctima: los dos totales son el mismo."""
    c, f = V.consultar(conn, "amigos_robos")
    hechos = sum(_columna(c, f, "robo_el"))
    sufridos = sum(_columna(c, f, "le_robaron"))
    comprobar("los robos hechos son los mismos que los sufridos",
              hechos == sufridos, "%d vs %d" % (hechos, sufridos))


def prueba_el_ladron_uno_a_uno_suma_el_total(conn):
    """El desglose por parejas y el total del ladrón son la misma cuenta.

    Se calculan por caminos distintos -- uno agrupa por víctima, el otro por
    (quien, a quien) -- así que si uno se deja filas fuera, esto lo ve."""
    c1, f1 = V.consultar(conn, "amigos_ladron")
    c2, f2 = V.consultar(conn, "amigos_ladron_a_quien")
    comprobar("lo que el ladrón costó, por parejas, suma el total",
              sum(_columna(c2, f2, "le_costo")) == sum(_columna(c1, f1, "perdido")),
              "%d vs %d" % (sum(_columna(c2, f2, "le_costo")),
                            sum(_columna(c1, f1, "perdido"))))
    c3, f3 = V.consultar(conn, "amigos_robos")
    comprobar("y los robos por parejas suman los del total",
              sum(_columna(c2, f2, "le_robo")) == sum(_columna(c3, f3, "robo_el")),
              "%d vs %d" % (sum(_columna(c2, f2, "le_robo")),
                            sum(_columna(c3, f3, "robo_el"))))


def prueba_una_partida_de_seis_cabe(conn):
    """El tablero de 5-6 jugadores: 30 casillas en vez de 19.

    Todo lo que nombra un sitio estaba escrito para las 19 del base. Ahora la
    reticula se construye con las casillas que haya, y la FORMA no esta
    escrita en ningun sitio: sale de lo que apunto el mod.

    Lo que se sujeta aqui es el filtro que decide si una conversion de
    coordenadas ha producido un tablero de verdad, porque es lo unico que
    separa nombrar los sitios bien de nombrarlos mal sin enterarse. Dos
    intentos se quedaron cortos antes de este:

      1. «sin repetir y de una pieza» -> lo cumple un paralelogramo sesgado
      2. «el perfil de filas sube y baja» -> lo cumple un zigzag, y nombraba
         92 vertices donde hay 86

    Lo que sirve son las dos juntas: convexo en los tres ejes del hexagono, Y
    con el perfil de un tablero. El perfil de 5-6 esta confirmado sobre una
    captura del juego: 3-4-5-6-5-4-3."""
    from red import sitios
    from vision import board_graph as bg

    comprobar("el tablero base pasa el filtro",
              sitios._es_un_tablero(list(bg.TILE_AXIAL)))
    hex3 = [(q, r) for q in range(-3, 4) for r in range(-3, 4)
            if abs(q + r) <= 3]
    comprobar("y un hexagono mayor tambien", sitios._es_un_tablero(hex3))

    zigzag = []
    for k, largo in enumerate([3, 4, 5, 6, 5, 4, 3]):
        r = k - 3
        q0 = -((largo - 1) // 2) - ((r + 1) // 2)
        zigzag += [(q0 + n, r) for n in range(largo)]
    comprobar("un zigzag con el perfil bueno NO pasa",
              not sitios._es_un_tablero(zigzag))
    comprobar("y un paralelogramo tampoco",
              not sitios._es_un_tablero([(q, r) for r in range(6)
                                         for q in range(5)]))

    comprobar("la reticula del base sigue en 54 y 72",
              len(sitios.VERTICE_POR_CARAS) == 54
              and len(sitios.ARISTA_POR_CARAS) == 72)
    r3 = sitios.reticula_de(hex3)
    euler = (len(r3.vertice_por_caras) - len(r3.arista_por_caras)
             + len(r3) + 1)
    comprobar("y la de un tablero mayor cuadra con Euler", euler == 2,
              "da %d" % euler)

    import inspect
    from mod_verdad import importar as _imp
    fuente = inspect.getsource(_imp)
    comprobar("el importador no exige 19 casillas",
              "len(alin.reticula)" in fuente)

    # Y ahora, contra una de verdad. Todo lo de arriba se escribio antes de
    # que existiera ninguna: eran hexagonos inventados y el perfil sacado de
    # una captura. El 27/8/2026 se jugo una de seis y entro entera, asi que
    # esto ya no comprueba una idea del tablero grande sino el tablero grande.
    seis = [g for (g,) in conn.execute(
        "SELECT game_id FROM games g WHERE (SELECT COUNT(*) FROM players p "
        "WHERE p.game_id = g.game_id) >= 5")]
    if not seis:
        return saltar("una partida de 5-6 de verdad (todavia no hay ninguna)")
    g = seis[0]
    cas = [(q, r) for q, r in conn.execute(
        "SELECT axial_q, axial_r FROM tiles WHERE game_id=?", (g,))]
    comprobar("la partida de seis trae 30 casillas", len(cas) == 30,
              "trae %d" % len(cas))
    ret = sitios.reticula_de(frozenset(cas))
    # 80 vertices y 109 aristas es la geometria del tablero de 5-6, igual que
    # 54 y 72 lo son del base. Y Euler dice que es una superficie de una
    # pieza y sin agujeros, que es lo que de verdad se quiere saber.
    comprobar("y su reticula es la de 5-6: 80 sitios y 109 caminos",
              len(ret.vertice_por_caras) == 80
              and len(ret.arista_por_caras) == 109,
              "%d y %d" % (len(ret.vertice_por_caras),
                           len(ret.arista_por_caras)))
    e = len(ret.vertice_por_caras) - len(ret.arista_por_caras) + len(cas) + 1
    comprobar("y cuadra con Euler", e == 2, "da %d" % e)

    # El reparto de terrenos de la ampliacion: 6 madera, 6 lana, 6 cereales,
    # 5 mineral, 5 arcilla y DOS desiertos. Que haya dos importa mas de lo que
    # parece: «la casilla sin numero» deja de identificar al desierto, que es
    # como `db/deducir.py` sabe donde empieza el ladron.
    reparto = dict(conn.execute(
        "SELECT resource, COUNT(*) FROM tiles WHERE game_id=? "
        "GROUP BY resource", (g,)))
    comprobar("y el reparto de terrenos es el de la ampliacion",
              reparto == {"Madera": 6, "Lana": 6, "Cereales": 6,
                          "Mineral": 5, "Arcilla": 5, "Desierto": 2},
              str(reparto))
    # A 12 puntos, y el que gano llego a 12. Es lo unico que comprueba que la
    # regla «de 5 en adelante se juega a 12» no es una suposicion escrita en
    # una vista, sino lo que paso en la mesa.
    fila = conn.execute(
        "SELECT MAX(final_points) FROM players WHERE game_id=?", (g,)).fetchone()
    comprobar("y se jugaba a 12, porque el que gano llego a 12",
              fila and fila[0] is not None and fila[0] >= 12,
              "el mejor hizo %s" % (fila[0] if fila else None))


def prueba_un_ladron_ilegible_no_pasa_callado(conn):
    """Una partida con robos TIENE que tener movimientos del ladron.

    No se puede robar sin mover el ladron: los robos salen de un 7 o de un
    caballero, y los dos lo mueven. Asi que `robos > 0` y `ladron = 0` es una
    contradiccion, y es exactamente la forma que tuvo el fallo del tablero de
    seis -- 15 robos, cero movimientos, cero bloqueos.

    Lo malo no fue el fallo, fue que entrara callado. El importador se saltaba
    la posicion que no sabia leer y seguia; la partida quedaba entera y
    creible, y la produccion contada como si el ladron no estuviera en el
    tablero. Ni siquiera `db/deducir.py` lo veia, porque deduce con la misma
    ceguera.

    Por eso lo que se exige aqui no es que no vuelva a pasar -- la grabacion
    de la 11 no trae la posicion y no la va a traer nunca -- sino que cuando
    pase QUEDE ESCRITO en la partida, en `pegas`, viajando con los datos."""
    malas = []
    for g, robos, movs, pegas in conn.execute(
            "SELECT g.game_id,"
            " (SELECT COUNT(*) FROM steals s WHERE s.game_id = g.game_id),"
            " (SELECT COUNT(*) FROM robber_moves m WHERE m.game_id = g.game_id),"
            " (SELECT mi.pegas FROM mod_imports mi WHERE mi.game_id = g.game_id)"
            " FROM games g"):
        if robos and not movs and not pegas:
            malas.append(g)
    comprobar("ninguna partida tiene robos sin ladron y sin decirlo",
              not malas, str(malas))

    # Y al reves: una pega apuntada tiene que corresponder a algo real. Una
    # marca que se queda pegada despues de reimportar bien seria peor que no
    # tenerla, porque desconfiar de datos buenos no se arregla nunca.
    sobran = [g for g, in conn.execute(
        "SELECT mi.game_id FROM mod_imports mi"
        " WHERE mi.pegas LIKE '%ladron%'"
        "   AND (SELECT COUNT(*) FROM robber_moves m"
        "         WHERE m.game_id = mi.game_id) > 0")]
    comprobar("y ninguna arrastra una pega del ladron ya resuelta",
              not sobran, str(sobran))


def _sufijos_que_atiende():
    """Las terminaciones que el repartidor de `importar.py` atiende.

    Sacadas del propio código con `ast`, y en UN solo sitio porque hay dos
    pruebas que las necesitan. Antes se sacaban con una expresión regular
    que sólo veía la forma `accion.endswith("...")`, y era frágil de la peor manera:
    el día que una de esas llamadas pasó a recibir una TUPLA -- dos nombres
    para el mismo trato, el de mesa de cuatro y el de mesa grande -- la
    expresión dejó de verlas, la prueba se quedó con menos terminaciones de
    las que hay, y lo que anunció fue que el importador se había roto.

    `ast` lee lo que el intérprete lee, y le da igual la forma.
    """
    import ast
    import inspect
    from mod_verdad import importar as _imp
    mejor = set()
    for nodo in ast.walk(ast.parse(inspect.getsource(_imp))):
        if not isinstance(nodo, ast.FunctionDef):
            continue
        aqui = set()
        for n in ast.walk(nodo):
            if (isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
                    and n.func.attr == "endswith" and n.args):
                a = n.args[0]
                trozos = a.elts if isinstance(a, (ast.Tuple, ast.List)) else [a]
                for x in trozos:
                    if isinstance(x, ast.Constant) and isinstance(x.value, str):
                        aqui.add(x.value)
        if len(aqui) > len(mejor):
            mejor = aqui
    return mejor


def prueba_lo_que_no_entiende_no_se_pierde(conn):
    """El dia que se juegue a una expansion, que se note.

    Catan Universe trae mucho mas que el basico: Ciudades y Caballeros (65
    acciones), Navegantes (31), el Ascenso de los Incas (19), Tierra
    Encantada, el Gran Canal... 433 acciones distintas en el ensamblado. El
    importador entiende diez terminaciones, todas del basico.

    Eso no es el problema -- escribir el soporte a ciegas, sin una grabacion
    que mirar, es como se colaron todos los fallos de este proyecto. El
    problema era COMO fallaba: el `if/elif` de `paso` no tenia `else`, asi que
    una accion desconocida desaparecia sin dejar rastro. Una partida de
    Navegantes habria entrado con sus tiradas y sus edificios, sin un solo
    barco, y con toda la pinta de estar completa. Igual que la partida 11 con
    el ladron.

    Ahora se cuentan y van a `pegas`, con la partida. Lo que se comprueba
    aqui son las dos mitades de que eso sirva de algo:

      - que NO salte con lo que ya se juega (si saltara siempre, no se
        volveria a mirar)
      - que SI salte con algo que no se ha visto nunca
    """
    from mod_verdad import importar as _imp

    finales = _sufijos_que_atiende()
    comprobar("el importador atiende las doce acciones de siempre",
              len(finales) >= 12, str(sorted(finales)))

    def se_entiende(a):
        # La puerta va PRIMERO, igual que en `paso`. Si no es del basico, da
        # igual como termine.
        if not a.startswith(_imp._FAMILIAS_QUE_ENTIENDO):
            return False
        if a in _imp._REPARTOS_DE_VERDAD or a in _imp._YA_SE_QUE_ESTAN:
            return True
        return any(a.endswith(f) for f in finales)

    # 1. Nada de lo que ya se juega puede saltar. Se mira contra las acciones
    #    de TODAS las grabaciones guardadas, que es la unica lista honesta de
    #    "lo que ya se juega".
    import gzip
    import json
    import os
    crudo = os.path.join(_imp.RAIZ if hasattr(_imp, "RAIZ") else ".",
                         "mod_verdad", "crudo")
    if not os.path.isdir(crudo):
        crudo = os.path.join("mod_verdad", "crudo")
    vistas = set()
    if os.path.isdir(crudo):
        for f in sorted(os.listdir(crudo)):
            if not f.endswith(".jsonl.gz"):
                continue
            with gzip.open(os.path.join(crudo, f), "rt", encoding="utf-8") as fh:
                for linea in fh:
                    try:
                        ev = json.loads(linea)
                    except Exception:
                        continue
                    if isinstance(ev, dict) and ev.get("accion"):
                        vistas.add(ev["accion"])
    if not vistas:
        saltar("las acciones desconocidas (no hay grabaciones guardadas)")
    else:
        nuevas = sorted(a for a in vistas if not se_entiende(a))
        comprobar("ninguna accion de las %d ya jugadas salta como desconocida"
                  % len(vistas), not nuevas, str(nuevas))

    # 2. Y en la base tampoco: ninguna partida importada arrastra esa pega.
    con_pega = [g for g, in conn.execute(
        "SELECT game_id FROM mod_imports WHERE pegas LIKE '%sin entender%'")]
    comprobar("y ninguna partida importada la arrastra", not con_pega,
              str(con_pega))

    # 3. Lo que de verdad importa: que con una expansion SI salte.
    #
    # Y en concreto la trampa que tenia esto: el reparto de `paso` va por
    # TERMINACION, y las expansiones repiten los mismos finales. Ocho acciones
    # de otros juegos entraban por la puerta de atras --
    # `CatanCak_RollDice_GameAction` se apuntaba como una tirada normal, y en
    # Ciudades y Caballeros se tiran TRES dados. `RivalsBase_RollDice` ni
    # siquiera es este juego. Habrian dado partidas a medias con tiradas
    # creibles: el mismo fallo callado que el ladron de la partida 11.
    #
    # Las ocho salen del catalogo, no de una lista escrita a mano, asi que si
    # el juego anade una novena tambien se comprueba.
    from mod_verdad import catalogar as _cat
    cat = _cat.cargar()
    if cat is None:
        return saltar("las acciones de expansion (falta el catalogo)")
    deberian_saltar = [a for a in cat["acciones"]
                       if not a.startswith(_imp._FAMILIAS_QUE_ENTIENDO)]
    comprobar("el catalogo trae acciones de expansion con las que probar",
              len(deberian_saltar) > 200, "%d" % len(deberian_saltar))
    cuelan = [a for a in deberian_saltar if se_entiende(a)]
    comprobar("ni una sola de las %d acciones de otros juegos se cuela"
              % len(deberian_saltar), not cuelan, str(cuelan[:5]))

    # Y que la puerta no se haya pasado de cerrada: las del basico entran.
    delbasico = [a for a in cat["acciones"]
                 if a.startswith(_imp._FAMILIAS_QUE_ENTIENDO)]
    entran = [a for a in delbasico if se_entiende(a)]
    comprobar("y las del basico siguen entrando (%d de %d)"
              % (len(entran), len(delbasico)),
              len(entran) >= len(delbasico) - 3,
              "solo %d de %d" % (len(entran), len(delbasico)))


def prueba_las_variantes_de_mesa_grande_no_se_pierden(conn):
    """Con 5 o 6 el juego usa acciones APARTE para lo mismo.

    `CatanTrade_FinishTradeSixPlayer_GameAction` es un trato entre dos
    personas, exactamente igual que `CatanTrade_FinishTrade_GameAction` y con
    el mismo contenido dentro. Lo mismo con la banca durante la ronda
    compartida de la ampliación. Las dos estaban en la lista de «ya sé que
    están», así que ni se importaban ni saltaba el aviso de acción
    desconocida: las partidas de mesa grande entraron con CERO tratos entre
    personas, con sus tiradas y sus edificios en su sitio, y con toda la
    pinta de estar completas.

    De dónde salió el fallo importa, porque es reproducible: la lista de «ya
    sé que están» se generó restando las acciones entendidas a las vistas en
    las grabaciones. Una lista hecha así **absorbe justo lo que se te ha
    olvidado** -- si no lo entiendes, aparece como «visto y no usado», que es
    la única categoría que no da la cara.

    Se comprueba en los dos sitios:

      1. que ninguna acción IGNORADA sea una variante de nombre de otra que
         sí se atiende.
      2. que ninguna del CATÁLOGO lo sea tampoco, aunque no se haya jugado
         nunca. Ésta es la que avisa antes y no después.
    """
    sys.path.insert(0, RAIZ)
    from mod_verdad import importar as imp

    atiende = _sufijos_que_atiende()
    comprobar("se ven los sufijos que el importador atiende",
              len(atiende) >= 12, "%d" % len(atiende))

    S = "_GameAction"
    raices = sorted(h[:-len(S)] for h in atiende if h.endswith(S) and h != S)

    def variante_de(nombre):
        """La misma acción con algo metido en el nombre, no otra distinta."""
        if not nombre.endswith(S):
            return None
        r = nombre[:-len(S)]
        for rh in raices:
            if r != rh and (r.startswith(rh) or r.endswith(rh)
                            or ("_" + rh) in r):
                return rh + S
        return None

    malas = [(i, variante_de(i)) for i in sorted(imp._YA_SE_QUE_ESTAN)
             if variante_de(i)]
    comprobar("ninguna acción ignorada es una variante de otra que sí se usa",
              not malas, str(malas[:3]))

    # Y lo mismo contra el catálogo entero, que trae las 422 acciones del
    # juego aunque no se hayan jugado nunca. Aquí se ve la de mesa grande el
    # día que se escribe el código, no el día que alguien juega con seis.
    ruta = os.path.join(RAIZ, "mod_verdad", "catalogo.json")
    if not os.path.isfile(ruta):
        return saltar("las variantes del catálogo (no está catalogo.json)")
    with open(ruta, encoding="utf-8") as fh:
        catalogo = json.load(fh)
    todas = [a["nombre"] if isinstance(a, dict) else a
             for a in catalogo["acciones"]]
    sueltas = []
    for a in sorted(todas):
        if not a.startswith(imp._FAMILIAS_QUE_ENTIENDO):
            continue
        if any(a.endswith(h) for h in atiende):
            continue                      # ya la atiende
        de_quien = variante_de(a)
        if de_quien:
            sueltas.append("%s es un %s con otro nombre" % (a, de_quien))
    comprobar("y ninguna del juego se queda fuera por llamarse distinto",
              not sueltas, str(sueltas[:3]))


def prueba_el_mazo_es_el_de_la_mesa(conn):
    """Con 5 o con 6 el mazo no es el de 25 cartas, y la vista tiene que saberlo.

    Aquí hay una suposición, y conviene decirlo: el reparto del mazo está
    LEÍDO DEL REGLAMENTO, no medido. El juego no lo enseña, y la acción que
    lo baraja es de las que el mod tiene prohibidas porque daría el orden de
    las cartas. Así que `V.MAZO` es lo único del proyecto que se cree algo
    sin haberlo visto.

    Esta prueba es lo que impide que esa suposición pase de largo:

      1. que todas las mesas que hay en la base tengan mazo. Una mesa sin
         mazo no da error: el JOIN se la come y el esperado sale corto.
      2. que ninguna partida haya sacado más cartas de un tipo de las que su
         mazo dice que lleva. Si los números están mal, esto es lo que lo
         canta -- y lo canta con datos, no con opiniones.
      3. que la vista use de verdad el mazo de cada mesa. Es la parte que se
         rompería sin ruido: seguiría dando porcentajes creíbles, sólo que
         los de otra caja.
    """
    mesas = [r[0] for r in conn.execute(
        "SELECT DISTINCT jugadores FROM jugadores WHERE jugadores IS NOT NULL")]
    faltan = sorted(m for m in mesas if m not in V.MAZO)
    comprobar("todas las mesas jugadas tienen su mazo", not faltan,
              "sin mazo: %s" % faltan)

    # 2. Lo que salió contra lo que la caja lleva. Los cuatro tipos que se
    # juegan se cuentan de `dev_card_plays`; las de punto salen de la resta.
    tipos = {"Caballero": "caballero", "Invencion": "invencion",
             "Monopolio": "monopolio",
             "Construccion de carreteras": "carreteras"}
    pasados = []
    for gid, eran in conn.execute(
            "SELECT DISTINCT game_id, jugadores FROM jugadores"):
        mazo = V.MAZO.get(eran)
        if not mazo:
            continue
        for tipo, clave in tipos.items():
            n = conn.execute("SELECT COUNT(*) FROM dev_card_plays "
                             "WHERE game_id=? AND card_type=?",
                             (gid, tipo)).fetchone()[0]
            if n > mazo[clave]:
                pasados.append("partida %s: %d de %s con un mazo de %d"
                               % (gid, n, tipo, mazo[clave]))
    comprobar("ninguna partida saca más cartas de las que su mazo lleva",
              not pasados, str(pasados[:3]))

    # 3. Que la vista mire el mazo que toca. Se comprueba contra el número
    # exacto, no contra «es distinto»: 14/25 y 20/35 son 56,0 y 57,1, y sólo
    # el segundo puede salir en una partida de seis.
    for eran in sorted(set(mesas) & set(V.MAZO)):
        # Una partida de ese tamaño en la que se jugara alguna carta. En una
        # donde no salió ninguna la columna sale vacía, y hace bien: sin
        # cartas no hay nada contra lo que comparar. Pero no sirve de prueba.
        fila = conn.execute(
            "SELECT j.game_id FROM (SELECT DISTINCT game_id, jugadores "
            "                         FROM jugadores) j "
            " WHERE j.jugadores = ? "
            "   AND EXISTS (SELECT 1 FROM dev_card_plays d "
            "                WHERE d.game_id = j.game_id) LIMIT 1",
            (eran,)).fetchone()
        if not fila:
            saltar("el mazo de una mesa de %d (nadie jugó una carta)" % eran)
            continue
        c, f = V.consultar(conn, "amigos_mazo", partida=fila[0])
        i_carta, i_mazo = c.index("carta"), c.index("porcentaje_normal")
        mazo = V.MAZO[eran]
        total = sum(mazo.values())
        esperado = round(100.0 * mazo["caballero"] / total, 1)
        dice = [r[i_mazo] for r in f if r[i_carta] == "Caballero"]
        otro = 35 if total == 25 else 25
        comprobar("en una mesa de %d el mazo son %d cartas, no %d"
                  % (eran, total, otro),
                  dice and abs(dice[0] - esperado) < 0.05,
                  "dice %s y son %s" % (dice, esperado))


def prueba_el_catalogo_contempla_el_juego_entero(conn):
    """Lo que PUEDE pasar se sabe hoy; lo que trae dentro, no.

    Durante un rato el razonamiento fue «una partida sólo enseña el 82% de
    las acciones, así que no se puede prever el 100%», y mezclaba dos cosas:

      qué EXISTE        se sabe entero, leyendo el ensamblado del juego
      qué TRAE DENTRO   no se sabe hasta jugar

    Lo segundo es donde han estado todos los fallos -- `HarborType` existía y
    venía vacío, `GamePiecesRobber` existía y venía `null` -- y por eso no se
    escribe soporte a ciegas. Pero lo primero no había por qué adivinarlo, y
    adivinarlo era el error.

    `mod_verdad/catalogar.py` lo saca del ensamblado y lo deja en
    `catalogo.json`, que va al repo para que esto funcione en una máquina sin
    Catan instalado. Aquí se comprueba que ese catálogo sirva."""
    import json
    import os
    from mod_verdad import catalogar

    cat = catalogar.cargar()
    if cat is None:
        return comprobar("el catálogo del juego está en el repo", False,
                         "falta mod_verdad/catalogo.json")
    comprobar("el catálogo del juego está en el repo y se lee",
              len(cat.get("acciones") or []) > 300,
              "%d acciones" % len(cat.get("acciones") or []))

    # 1. Que no se haya inventado familias. `Trade_Finish_GameActionState` es
    #    la clase del PAYLOAD y colaba como una acción «Trade_Finish» que no
    #    existe; salían cinco expansiones fantasma.
    inventadas = sorted(set(
        catalogar.familia_de(a) for a in cat["acciones"]
        if catalogar.familia_de(a) not in catalogar.FAMILIAS.values()
        and not catalogar.familia_de(a).startswith("Rivals")))
    comprobar("y no nombra expansiones que no existen", not inventadas,
              str(inventadas))

    # 2. LA QUE IMPORTA: todo lo que se ha jugado de verdad tiene que estar en
    #    el catálogo. Si algo jugado no está, la extracción se deja cosas y el
    #    «100%» no lo es.
    import gzip
    crudo = os.path.join("mod_verdad", "crudo")
    vistas = set()
    if os.path.isdir(crudo):
        for f in sorted(os.listdir(crudo)):
            if not f.endswith(".jsonl.gz"):
                continue
            with gzip.open(os.path.join(crudo, f), "rt", encoding="utf-8") as fh:
                for linea in fh:
                    try:
                        ev = json.loads(linea)
                    except Exception:
                        continue
                    if isinstance(ev, dict) and ev.get("accion"):
                        vistas.add(ev["accion"])
    if not vistas:
        saltar("el catálogo contra lo jugado (no hay grabaciones)")
    else:
        faltan = sorted(vistas - set(cat["acciones"]))
        comprobar("y contiene las %d acciones que se han jugado de verdad"
                  % len(vistas), not faltan, str(faltan))

    # 3. Los accesores del payload. Son 63 y el mod lee seis; de los otros
    #    sólo se apunta CUÁL ha disparado, nunca lo que trae. Lo que se sujeta
    #    aquí es que los tapados sigan estando prohibidos por su nombre: es la
    #    única lista que impide que un día se vuelquen «por si acaso».
    import codecs
    from mod_verdad import importar as _imp
    cs = os.path.join(os.path.dirname(os.path.dirname(
        os.path.abspath(_imp.__file__))), "mod_verdad", "CatanVerdad.cs")
    fuente = ""
    if os.path.isfile(cs):
        with codecs.open(cs, encoding="utf-8") as fh:
            fuente = fh.read()
    tapados = ["AsRobbedResources", "AsSpy", "AsMasterMerchant",
               "AsShuffleDevelopmentCards", "AsShuffleProgressCards",
               "AsProgressCardDistribution"]
    sin_prohibir = [a for a in tapados
                    if ('"%s"' % a) not in fuente.split("NoMirarNunca", 1)[-1]
                    .split("};", 1)[0]]
    comprobar("los accesores con información tapada siguen prohibidos",
              fuente and not sin_prohibir, str(sin_prohibir))

    # Y que ninguno de ellos se lea en ningún otro sitio del mod.
    leidos = [a for a in ("AsRobbedResources", "AsSpy", "AsMasterMerchant")
              if ('Campo(c, "%s")' % a) in fuente]
    comprobar("y no se leen en ninguna parte", not leidos, str(leidos))


def prueba_quitar_una_partida_no_deja_restos(conn):
    """Quitar una partida tiene que llevarse TODO lo suyo.

    Es lo único del panel que borra, y el borrado va por diecisiete tablas.
    La que se escapa siempre es `building_tiles`: no tiene `game_id`, hay que
    ir por los edificios. Una tabla que se olvide no da error --deja filas
    huérfanas apuntando a una partida que ya no existe-- y eso no se ve
    mirando el panel: se ve el día que una vista cruza por ahí y salen datos
    de una partida borrada.

    Se prueba sobre una COPIA. Una prueba que borre de verdad en la base de
    quien la corre no es una prueba, es un accidente esperando.
    """
    import os
    import shutil
    import sqlite3 as _sq
    import tempfile
    from db import quitar_partidas as qp

    # La partida que MÁS tablas toca, no la primera. Elegir la primera es lo
    # que dejó pasar el fallo: la 1 es la más vieja y no tiene puertos, así
    # que `harbor_owners` -- que no se estaba borrando -- se comprobaba
    # siempre con cero filas y siempre daba bien. Una prueba que pasa porque
    # no hay nada que mirar no está probando nada.
    tablas_gid = [t for (t,) in conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
        if "game_id" in [c[1] for c in conn.execute("PRAGMA table_info(%s)" % t)]]
    mejor, gid = -1, None
    for (g,) in conn.execute("SELECT game_id FROM games ORDER BY game_id"):
        toca = sum(1 for t in tablas_gid if conn.execute(
            "SELECT 1 FROM %s WHERE game_id=? LIMIT 1" % t, (g,)).fetchone())
        if toca > mejor:
            mejor, gid = toca, g
    if gid is None:
        return saltar("quitar una partida (no hay ninguna)")

    tmp = tempfile.mkdtemp(prefix="catan_quitar_")
    copia = os.path.join(tmp, "catan_stats.db")
    try:
        shutil.copy2(BASE, copia)
        c2 = _sq.connect(copia)
        antes = c2.execute("SELECT COUNT(*) FROM games").fetchone()[0]
        qp.quitar(c2, gid, "prueba")
        c2.commit()
        despues = c2.execute("SELECT COUNT(*) FROM games").fetchone()[0]
        comprobar("quitar una partida la quita", despues == antes - 1,
                  "%d -> %d" % (antes, despues))

        # Ninguna tabla con `game_id` puede seguir teniendo filas suyas. Se
        # recorren TODAS las que existan, no una lista escrita a mano: si
        # manana se anade una tabla y nadie la mete en el borrado, esto salta.
        tablas = [r[0] for r in c2.execute(
            "SELECT name FROM sqlite_master WHERE type='table'")]
        restos = []
        for tabla in tablas:
            cols = [r[1] for r in c2.execute("PRAGMA table_info(%s)" % tabla)]
            if "game_id" not in cols:
                continue
            n = c2.execute("SELECT COUNT(*) FROM %s WHERE game_id=?" % tabla,
                           (gid,)).fetchone()[0]
            if n:
                restos.append("%s(%d)" % (tabla, n))
        comprobar("y no deja ni una fila suya en las %d tablas con game_id"
                  % sum(1 for x in tablas
                        if "game_id" in [r[1] for r in
                                         c2.execute("PRAGMA table_info(%s)" % x)]),
                  not restos, str(restos))

        # Y la que no lleva `game_id`, por su padre.
        sueltas = c2.execute(
            "SELECT COUNT(*) FROM building_tiles bt "
            "LEFT JOIN buildings b ON b.building_id = bt.building_id "
            "WHERE b.building_id IS NULL").fetchone()[0]
        comprobar("ni casillas de edificios que ya no existen", sueltas == 0,
                  "%d" % sueltas)

        # La marca. Sin ella el importador la volveria a meter en la siguiente
        # pasada, y el borrado se desharia solo.
        marcada = c2.execute("SELECT COUNT(*) FROM mod_ignoradas").fetchone()[0]
        comprobar("y deja la grabación marcada para no reimportarla",
                  marcada > 0)
        c2.close()
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    # El panel lo ofrece por POST, no por GET: un GET se dispara desde un
    # enlace o desde el precargado del navegador, y esto no tiene deshacer.
    import inspect
    import panel as _pan
    fuente = inspect.getsource(_pan.Servidor) if hasattr(_pan, "Servidor") else \
        inspect.getsource(_pan)
    get = fuente.split("def do_GET", 1)[-1].split("def do_POST", 1)[0]
    comprobar("y el panel no lo ofrece por GET", '"/quitar"' not in get)


def prueba_la_produccion_se_deduce_del_tablero(conn):
    """Que la producción salga del tablero, sin leerla en ningún sitio.

    Es la pregunta de «¿puede la visión hacer lo que hace el mod?» contestada
    con números. El tablero -- edificios, casillas, tiradas, ladrón -- es lo
    único que la visión sabe leer, y son 77 filas de las 405 que apunta el mod
    en una partida. Pero **la producción es una regla, no un dato**: con esas
    cuatro cosas, quién cobra qué está determinado.

    Aquí se comprueba contra la verdad del mod, carta por carta. Y las dos
    trampas que costó encontrar, porque son la diferencia entre 97,7% y
    exacto: dentro de un turno primero se tira y luego se construye, y un
    caballero mueve el ladrón DESPUÉS de la tirada de su turno. Las dos se
    resuelven mirando la marca de tiempo y no el número de turno.

    Esta comprobación es la que encontró el «Año Productivo» duplicado -- ver
    `_REPARTOS_DE_VERDAD` en importar.py."""
    from db import deducir
    total_c = total_n = total_m = total_d = 0
    for (g,) in conn.execute("SELECT game_id FROM games ORDER BY game_id"):
        cuadran, cuantas, mod, ded = deducir.comparar(conn, g)
        total_c += cuadran
        total_n += cuantas
        total_m += mod
        total_d += ded
        comprobar("partida %d: la producción deducida cuadra" % g,
                  cuadran == cuantas and mod == ded,
                  "%d de %d casillas, %d cartas contra %d"
                  % (cuadran, cuantas, ded, mod))
    comprobar("y en total, carta por carta",
              total_m == total_d and total_c == total_n,
              "%d de %d cartas, %d de %d casillas"
              % (total_d, total_m, total_c, total_n))

    # Los bloqueos del ladrón son la otra mitad de la misma cuenta: lo que
    # HABRIA producido y no produjo. Si esos no cuadran, la produccion cuadra
    # por casualidad.
    import collections
    mios = suyos = 0
    for (g,) in conn.execute("SELECT game_id FROM games ORDER BY game_id"):
        _gana, bloq = deducir.produccion(conn, g)
        mios += len(bloq)
        suyos += conn.execute(
            "SELECT COUNT(*) FROM robber_blocks WHERE game_id = ?",
            (g,)).fetchone()[0]
    comprobar("y los bloqueos del ladrón también",
              mios == suyos, "deducidos %d, el mod dice %d" % (mios, suyos))


def prueba_el_ano_productivo_no_se_cuenta_como_produccion(conn):
    """«Año Productivo» no reparte por tirada, y se colaba como si lo hiciera.

    `importar.py` cazaba el reparto por la terminación de la acción, y con
    `endswith("DistributeResources_GameAction")` cuadran TRES acciones
    distintas: la producción de verdad, la de la colocación inicial y la del
    Año Productivo. La tercera le da dos cartas a elección a un jugador, pero
    `_reparto` no lo sabía: volvía a calcular la producción de la última
    tirada y la apuntaba otra vez. 17 repartos duplicados y 34 cartas
    fantasma en las partidas 3, 4, 6 y 8.

    No lo encontró nadie leyendo: lo encontró tener una segunda fuente."""
    repetidos = conn.execute(
        "SELECT COUNT(*) FROM (SELECT 1 FROM resource_gains "
        "WHERE source = 'produccion' "
        "GROUP BY game_id, roll_id, player_id, resource, amount "
        "HAVING COUNT(*) > 1)").fetchone()[0]
    comprobar("ningún reparto está apuntado dos veces", repetidos == 0,
              "%d grupos repetidos" % repetidos)

    import inspect
    from mod_verdad import importar as _imp
    comprobar("y el importador filtra por el nombre entero, no por el final",
              "_REPARTOS_DE_VERDAD" in inspect.getsource(_imp))
    comprobar("y el Año Productivo se queda fuera",
              all("Inventor" not in a for a in _imp._REPARTOS_DE_VERDAD),
              str(sorted(_imp._REPARTOS_DE_VERDAD)))


def prueba_la_produccion_cuadra(conn):
    """Lo que suman los cinco recursos tiene que ser el total de cada uno."""
    c, f = V.consultar(conn, "amigos_produccion")
    i = dict((n, c.index(n)) for n in
             ("madera", "arcilla", "lana", "cereales", "mineral", "total"))
    mal = [fila for fila in f
           if sum(fila[i[r]] for r in ("madera", "arcilla", "lana",
                                       "cereales", "mineral")) != fila[i["total"]]]
    comprobar("los cinco recursos suman el total de cada uno", not mal, str(mal))


def prueba_por_que_se_movio_el_ladron(conn, amigas):
    """Cada movimiento del ladrón tiene una causa, y sólo puede ser una de dos.

    El cruce que lo valida no está en la tabla del ladrón: los movimientos por
    el 7 no pueden pasar de los sietes que se tiraron, y los de caballero no
    pueden pasar de los caballeros que se jugaron. Son dos tablas que no se
    hablan, y por eso vale.

    No tienen por qué salir IGUALES: un caballero que deja el ladrón donde ya
    estaba no genera movimiento, y lo mismo un 7."""
    if not amigas:
        return saltar("la causa del ladrón (no hay partidas de amigos)")
    sin_causa = conn.execute(
        "SELECT COUNT(*) FROM robber_moves WHERE cause IS NULL AND game_id IN "
        "(SELECT game_id FROM partidas WHERE con_amigos = 1)").fetchone()[0]
    comprobar("todo movimiento del ladrón dice por qué fue", sin_causa == 0,
              "%d sin causa" % sin_causa)

    raras = [r[0] for r in conn.execute(
        "SELECT DISTINCT cause FROM robber_moves WHERE cause NOT IN "
        "('siete', 'caballero')")]
    comprobar("y la causa es el 7 o un caballero, no otra cosa", not raras,
              str(raras))

    for causa, tabla, cuenta in (
            ("siete", "rolls", "SELECT COUNT(*) FROM rolls WHERE value=7"),
            ("caballero", "dev_card_plays",
             "SELECT COUNT(*) FROM dev_card_plays WHERE card_type='Caballero'")):
        movs = conn.execute(
            "SELECT COUNT(*) FROM robber_moves WHERE cause=?", (causa,)).fetchone()[0]
        pudo = conn.execute(cuenta).fetchone()[0]
        comprobar("los movimientos por %s no pasan de los que hubo (%d de %d)"
                  % (causa, movs, pudo), movs <= pudo)

    # Y el desglose de `amigos_ladron_a_quien` suma lo que dice la columna.
    c, f = V.consultar(conn, "amigos_ladron_a_quien")
    i = {n: c.index(n) for n in ("quien", "a_quien", "se_lo_puso", "con_7",
                                 "con_caballero")}
    mal = [(fila[i["quien"]], fila[i["a_quien"]]) for fila in f
           if fila[i["con_7"]] + fila[i["con_caballero"]] != fila[i["se_lo_puso"]]]
    comprobar("el 7 y el caballero suman las veces que se lo puso",
              not mal, str(mal[:3]))

    # Lo mismo en la vista de dónde lo pone.
    c2, f2 = V.consultar(conn, "amigos_ladron_donde")
    j = {n: c2.index(n) for n in ("quien", "numero", "veces", "con_7",
                                  "con_caballero")}
    mal2 = [(fila[j["quien"]], fila[j["numero"]]) for fila in f2
            if fila[j["con_7"]] + fila[j["con_caballero"]] != fila[j["veces"]]]
    comprobar("y también en «dónde pone el ladrón»", not mal2, str(mal2[:3]))

    # La vista viene agrupada por persona. Lo que se lee ahí es «qué hace
    # ÉSTE», y con las filas de cada uno repartidas por toda la tabla no se
    # lee. Que un nombre aparezca, desaparezca y vuelva es el fallo.
    nombres = [fila[j["quien"]] for fila in f2]
    vistos, roto = set(), []
    for k, n in enumerate(nombres):
        if k and n == nombres[k - 1]:
            continue
        if n in vistos:
            roto.append(n)
        vistos.add(n)
    comprobar("y las filas de cada uno van juntas", not roto, str(roto[:3]))

    # Y el total de esa vista son los movimientos que hay en la tabla.
    en_la_vista = sum(fila[j["veces"]] for fila in f2)
    en_la_tabla = conn.execute(
        "SELECT COUNT(*) FROM robber_moves WHERE tile_id IS NOT NULL "
        "AND game_id IN (SELECT game_id FROM partidas WHERE con_amigos = 1)").fetchone()[0]
    comprobar("los movimientos de la vista son los de la tabla",
              en_la_vista == en_la_tabla,
              "%d vs %d" % (en_la_vista, en_la_tabla))


def prueba_el_dano_del_ladron_se_desglosa(conn, amigas):
    """Las cinco columnas de recurso suman lo que costó el ladrón.

    Es la cuenta que se rompe al añadir un recurso y olvidarse de la columna:
    la tabla se seguiría pintando bien y el total saldría corto.

    Y desglosa `le_costo`, no `le_robo`. Lo que el ladrón NO te dejó producir
    sale de la casilla que tapó y se sabe exacto; la carta que te quita de la
    mano no la ve nadie y el mod no la lee -- los %d robos guardados tienen el
    recurso a NULL, y eso es a propósito."""
    if not amigas:
        return saltar("el daño del ladrón (no hay partidas de amigos)")
    c, f = V.consultar(conn, "amigos_ladron_a_quien")
    recursos = ("madera", "arcilla", "lana", "cereales", "mineral")
    i = {n: c.index(n) for n in recursos + ("quien", "a_quien", "le_costo")}
    mal = [(fila[i["quien"]], fila[i["a_quien"]]) for fila in f
           if sum(fila[i[n]] for n in recursos) != fila[i["le_costo"]]]
    comprobar("los recursos que bloqueó el ladrón suman lo que costó",
              not mal, str(mal[:3]))

    # Y el desglose tiene que cuadrar con la tabla, no sólo consigo mismo.
    a_mano = conn.execute(
        "SELECT COALESCE(SUM(b.amount), 0) FROM robber_blocks b "
        "WHERE b.blocker_id IS NOT NULL AND b.game_id IN "
        "(SELECT game_id FROM partidas WHERE con_amigos = 1)").fetchone()[0]
    en_la_vista = sum(fila[i["le_costo"]] for fila in f)
    comprobar("y son los bloqueos que hay en la tabla",
              en_la_vista == a_mano, "%d vs %d" % (en_la_vista, a_mano))

    # La carta robada NO se lee. Si algún día apareciera un recurso aquí sería
    # que el mod ha empezado a mirar manos ajenas.
    con_recurso = conn.execute(
        "SELECT COUNT(*) FROM steals WHERE resource IS NOT NULL").fetchone()[0]
    comprobar("la carta que roba el ladrón sigue sin leerse",
              con_recurso == 0, "%d robos con recurso" % con_recurso)


def prueba_la_produccion_es_la_de_la_tabla(conn, amigas):
    """Contra la tabla en crudo, no contra sí misma.

    La prueba de arriba pasaría igual si un JOIN duplicara filas: los cinco
    recursos y el total se doblarían a la vez. Esta compara con lo que hay
    escrito, que es lo único que no se dobla."""
    if not amigas:
        return saltar("la producción contra la tabla (no hay partidas)")
    c, f = V.consultar(conn, "amigos_produccion")
    en_la_vista = sum(_columna(c, f, "total"))
    en_la_tabla = conn.execute(
        "SELECT COALESCE(SUM(amount), 0) FROM resource_gains WHERE game_id IN (%s)"
        % ",".join(str(g) for g in amigas)).fetchone()[0]
    comprobar("la producción de la vista es la de la tabla",
              en_la_vista == en_la_tabla,
              "%d vs %d" % (en_la_vista, en_la_tabla))


def prueba_los_comercios_estan_todos(conn, amigas):
    """Ni un trato de más ni de menos: los de la tabla son los de la vista."""
    if not amigas:
        return saltar("los comercios (no hay partidas de amigos)")
    marca = ",".join(str(g) for g in amigas)
    c, f = V.consultar(conn, "amigos_comercio")
    en_la_vista = sum(_columna(c, f, "tratos"))
    en_la_tabla = conn.execute(
        "SELECT COUNT(*) FROM trades WHERE player_b_id IS NOT NULL "
        "AND game_id IN (%s)" % marca).fetchone()[0]
    comprobar("los tratos entre jugadores son los que hay en la tabla",
              en_la_vista == en_la_tabla,
              "%d vs %d" % (en_la_vista, en_la_tabla))

    # `tratos` va por quien PROPUSO, así que un par sale en dos filas y
    # sumarlas es lo que contesta «quién trata más con quién».
    # `tratos_entre_los_dos` es esa suma, y tiene que salir igual en las dos
    # filas del par -- si no, es que el par se está mirando desde un lado.
    por_par = {}
    for q, o, n, dos in zip(_columna(c, f, "quien"), _columna(c, f, "con_quien"),
                            _columna(c, f, "tratos"),
                            _columna(c, f, "tratos_entre_los_dos")):
        par = tuple(sorted((q, o)))
        por_par.setdefault(par, {"suma": 0, "dice": set()})
        por_par[par]["suma"] += n
        por_par[par]["dice"].add(dos)
    mal = [(par, d) for par, d in por_par.items()
           if len(d["dice"]) != 1 or d["suma"] not in d["dice"]]
    comprobar("los tratos de un par son los mismos mirados desde los dos lados",
              not mal, str(mal[:3]))

    # `amigos_puertos` clasifica los cambios con la banca por el puerto que
    # delatan. Si apareciera uno con otra forma -- un 5:1, o uno con dos
    # recursos por lado -- se caería de la tabla sin avisar, así que se cuentan
    # y tienen que estar todos.
    #
    # La cuenta es a tres bandas desde el 2 de septiembre de 2026, cuando los
    # 4:1 dejaron de salir en la tabla: un 4:1 es el cambio de quien NO tiene
    # puerto y en la tabla de los puertos no dice nada. Lo que se sigue
    # exigiendo es que no se pierda ninguno: 2:1 y 3:1 son los de la vista,
    # los 4:1 se cuentan aparte, y los tres juntos tienen que ser todos. Si un
    # día aparece un 5:1 la suma deja de dar y salta aquí, que es de lo que iba
    # esta prueba.
    c2, f2 = V.consultar(conn, "amigos_puertos")
    con_puerto = sum(_columna(c2, f2, "veces"))
    reparto = dict(conn.execute(
        "SELECT (SELECT SUM(json_extract(value,'$.amount')) "
        "          FROM json_each(gave_json)) "
        "      / (SELECT SUM(json_extract(value,'$.amount')) "
        "          FROM json_each(received_json)) AS ratio, COUNT(*) "
        "  FROM trades WHERE player_b_id IS NULL AND game_id IN (%s) "
        " GROUP BY ratio" % marca).fetchall())
    sin_puerto = reparto.get(4, 0)
    todos = sum(reparto.values())
    comprobar("y ningún cambio con la banca se queda sin clasificar",
              con_puerto + sin_puerto == todos,
              "%d con puerto + %d a 4:1 != %d cambios (reparto: %s)"
              % (con_puerto, sin_puerto, todos, sorted(reparto.items())))


def prueba_los_materiales_son_los_comerciados(conn, amigas):
    """Cada carta que cambió de mano sale una vez, y sólo una.

    Se abre cada trato en sus recursos con json_each, que es justo donde una
    fila se puede duplicar sin que se note. El total tiene que ser el mismo
    que sumando el JSON por fuera."""
    if not amigas:
        return saltar("los materiales (no hay partidas de amigos)")
    c, f = V.consultar(conn, "amigos_comercio_material")
    en_la_vista = sum(_columna(c, f, "dio"))
    # Cada trato se cuenta por los DOS lados, así que lo que la vista llama
    # «dio» es: lo que dio quien lo propuso, más lo que dio quien lo aceptó
    # -- que es lo que el otro recibió. Los de la banca sólo tienen un lado.
    a_mano = 0
    for gj, rj, otro in conn.execute(
            "SELECT gave_json, received_json, player_b_id FROM trades "
            "WHERE game_id IN (%s)" % ",".join(str(g) for g in amigas)):
        a_mano += sum(x["amount"] for x in json.loads(gj or "[]"))
        if otro is not None:
            a_mano += sum(x["amount"] for x in json.loads(rj or "[]"))
    comprobar("los recursos dados en la vista son los de los tratos",
              en_la_vista == a_mano, "%d vs %d" % (en_la_vista, a_mano))
    # Si el CASE de `con_quien` se equivocara, un trato entre personas se
    # etiquetaría con el nombre del que lo hizo.
    consigo = [(q, o) for q, o in zip(_columna(c, f, "quien"),
                                      _columna(c, f, "con_quien")) if q == o]
    comprobar("nadie comercia consigo mismo", not consigo, str(consigo))

    # LA QUE HABRÍA CAZADO EL FALLO. Un trato tiene dos lados y son el mismo
    # trato: lo que A dice que le dio a B tiene que ser exactamente lo que B
    # dice que recibió de A, recurso a recurso.
    #
    # Hasta el 22/8/2026 la vista leía sólo la fila del que PROPUSO el trato,
    # así que a cada uno le salían nada más los tratos que había iniciado él.
    # No faltaba ni una carta del total y por eso la prueba de arriba pasaba:
    # cada trato estaba entero, pero apuntado a nombre de uno solo.
    torcidos = [r for r in conn.execute("""
        SELECT a.quien, a.con_quien, a.recurso, a.dio, b.recibio
          FROM amigos_comercio_material a
          LEFT JOIN amigos_comercio_material b
                 ON b.quien = a.con_quien AND b.con_quien = a.quien
                AND b.recurso = a.recurso
         WHERE a.con_quien <> 'la banca'
           AND a.dio <> COALESCE(b.recibio, -1)""")]
    comprobar("lo que uno da es lo que el otro recibe", not torcidos,
              str(torcidos[:3]))


def prueba_el_saldo_cuadra_por_los_dos_lados(conn, amigas):
    """El saldo de un par tiene que ser el mismo con el signo cambiado.

    Es la propiedad que define un intercambio: las cartas no se crean ni se
    destruyen al cambiarlas de mano, así que lo que A gana con B es
    exactamente lo que B pierde con A. Si esto no cuadra, o falta un trato en
    un sentido o alguno se está contando dos veces -- y las dos cosas darían
    una tabla con la pinta de siempre.

    Y la propiedad sólo se cumple entre personas, que es la otra mitad de lo
    que se comprueba aquí: la banca no tiene fila, y si la tuviera no habría
    vuelta con la que cuadrarla."""
    if not amigas:
        return saltar("el saldo (no hay partidas de amigos)")
    c, f = V.consultar(conn, "amigos_saldo")
    i = {n: c.index(n) for n in ("quien", "con_quien", "tratos", "dio",
                                 "recibio", "neto")}
    con_banca = [r for r in f if "banca" in (r[i["quien"]], r[i["con_quien"]])]
    comprobar("la banca no sale en el saldo", not con_banca, str(con_banca[:2]))

    por_par = {(r[i["quien"]], r[i["con_quien"]]): r for r in f}
    mal = []
    for (a, b), fila in por_par.items():
        vuelta = por_par.get((b, a))
        if vuelta is None:
            mal.append("%s->%s no tiene vuelta" % (a, b))
            continue
        if fila[i["neto"]] != -vuelta[i["neto"]]:
            mal.append("%s/%s neto %s vs %s" % (a, b, fila[i["neto"]],
                                                vuelta[i["neto"]]))
        if fila[i["dio"]] != vuelta[i["recibio"]]:
            mal.append("%s dio %s y %s recibio %s" % (a, fila[i["dio"]], b,
                                                      vuelta[i["recibio"]]))
        if fila[i["tratos"]] != vuelta[i["tratos"]]:
            mal.append("%s/%s tratos %s vs %s" % (a, b, fila[i["tratos"]],
                                                  vuelta[i["tratos"]]))
    comprobar("el saldo de un par es el mismo con el signo cambiado",
              not mal, "; ".join(mal[:3]))

    # Y el saldo de un par tiene que ser lo mismo que sumar `amigos_comercio`
    # por los dos sentidos. Son dos consultas distintas sobre los mismos
    # tratos: si dijeran cosas distintas, no habria forma de saber cual creer.
    c2, f2 = V.consultar(conn, "amigos_comercio")
    j = {n: c2.index(n) for n in ("quien", "con_quien", "dio", "recibio")}
    suma = {}
    for r in f2:
        a, b = r[j["quien"]], r[j["con_quien"]]
        suma.setdefault((a, b), [0, 0])
        suma[(a, b)][0] += r[j["dio"]]
        suma[(a, b)][1] += r[j["recibio"]]
        # lo que A dio proponiendo, B lo recibio; y al reves
        suma.setdefault((b, a), [0, 0])
        suma[(b, a)][0] += r[j["recibio"]]
        suma[(b, a)][1] += r[j["dio"]]
    discrepan = []
    for par, (dio, recibio) in suma.items():
        fila = por_par.get(par)
        if fila is None:
            discrepan.append("%s/%s no esta en el saldo" % par)
        elif (fila[i["dio"]], fila[i["recibio"]]) != (dio, recibio):
            discrepan.append("%s/%s saldo %s/%s vs comercio %s/%s"
                             % (par[0], par[1], fila[i["dio"]],
                                fila[i["recibio"]], dio, recibio))
    comprobar("el saldo dice lo mismo que sumar los dos sentidos del comercio",
              not discrepan, "; ".join(discrepan[:3]))


def prueba_los_tratos_estan_uno_a_uno(conn, amigas):
    """Una fila por trato: ni se pierde ninguno ni se repite."""
    if not amigas:
        return saltar("los tratos uno a uno (no hay partidas de amigos)")
    c, f = V.consultar(conn, "amigos_tratos")
    en_la_tabla = conn.execute(
        "SELECT COUNT(*) FROM trades WHERE game_id IN (%s)"
        % ",".join(str(g) for g in amigas)).fetchone()[0]
    comprobar("hay una fila por trato, ni una más ni una menos",
              len(f) == en_la_tabla, "%d vs %d" % (len(f), en_la_tabla))
    # Los dos lados llenos: si un group_concat volviera NULL, la fila saldría
    # a medias y parecería un trato de una sola direccion.
    vacios = [fila for fila in f
              if not fila[c.index("dio")] or not fila[c.index("y_recibio")]
              or not fila[c.index("a")]]
    comprobar("ningún trato sale con un lado en blanco", not vacios,
              str(vacios[:3]))


def prueba_estan_los_once_numeros(conn, amigas):
    """Del 2 al 12 siempre, aunque alguno no haya salido nunca.

    Un número que no salió es el dato más interesante de esa tabla -- en la
    partida 4 el 12 no salió ni una vez -- y agrupando sobre las tiradas que
    hubo, simplemente no tenía fila y no se veía."""
    c, f = V.consultar(conn, "amigos_tiradas")
    comprobar("las tiradas traen los once números",
              _columna(c, f, "numero") == list(range(2, 13)),
              str(_columna(c, f, "numero")))
    for p in amigas:
        c2, f2 = V.consultar(conn, "amigos_tiradas", p)
        if _columna(c2, f2, "numero") != list(range(2, 13)):
            return comprobar("y también al filtrar por una partida", False,
                             "partida %d: %s" % (p, _columna(c2, f2, "numero")))
    comprobar("y también al filtrar por una partida", True)


def prueba_los_puertos_se_deducen_bien(conn, amigas):
    """Un puerto deducido tiene que poder existir, y contarse una sola vez."""
    c, f = V.consultar(conn, "amigos_puertos")
    nombres = set(_columna(c, f, "puerto"))
    validos = {"generico 3:1"} | set(
        "%s 2:1" % r for (r,) in conn.execute(
            "SELECT DISTINCT resource FROM resource_gains"))
    raros = nombres - validos
    comprobar("los puertos deducidos son puertos que existen", not raros,
              str(raros))

    # `amigos_cuantos_puertos` pasó a ser global el 2 de septiembre de 2026:
    # una fila por persona, y cada columna es EN CUANTAS PARTIDAS se le pudo
    # contar ese puerto. De ahí el techo: nadie puede tener el puerto de
    # madera en más partidas de las que ha jugado. Suena obvio y es justo lo
    # que se rompería contando usos en vez de partidas -- un puerto usado
    # quince veces daría 15 en una columna que dice «partidas».
    puertos = ("puerto_madera", "puerto_arcilla", "puerto_lana",
               "puerto_cereales", "puerto_mineral", "genericos")
    c2, f2 = V.consultar(conn, "amigos_cuantos_puertos")
    mal = [(fila[c2.index("quien")], col, fila[c2.index(col)],
            fila[c2.index("partidas")])
           for fila in f2 for col in puertos
           if not 0 <= fila[c2.index(col)] <= fila[c2.index("partidas")]]
    comprobar("nadie tiene un puerto en mas partidas de las que jugo",
              not mal, str(mal[:3]))

    # Y en UNA partida no puede haber más puertos repartidos que los 9 del
    # tablero. Esto es lo que comprobaba el `al_menos <= 9` de antes, y sigue
    # comprobándose: la vista global filtrada por partida da lo mismo que
    # daba la vista por partida.
    for p in amigas:
        c3, f3 = V.consultar(conn, "amigos_cuantos_puertos", p)
        total = sum(fila[c3.index(col)] for fila in f3 for col in puertos)
        if total > 9:
            return comprobar("y en una partida no se reparten mas de 9",
                             False, "partida %d: %d puertos" % (p, total))
    comprobar("y en una partida no se reparten mas de 9", True)

    # Quien tiene un puerto contado tiene que haberlo usado: sale de los
    # tratos, así que sin tratos no puede salir ninguno.
    sin_banca = conn.execute(
        "SELECT COUNT(*) FROM amigos_cuantos_puertos cp "
        " WHERE cp.puerto_madera + cp.puerto_arcilla + cp.puerto_lana "
        "     + cp.puerto_cereales + cp.puerto_mineral + cp.genericos > 0 "
        "   AND NOT EXISTS (SELECT 1 FROM amigos_puertos p "
        "                    WHERE p.quien = cp.quien)").fetchone()[0]
    comprobar("nadie tiene un puerto contado sin haberlo usado",
              sin_banca == 0, "%d" % sin_banca)


def prueba_los_puertos_deducidos_estan_en_el_tablero(conn):
    """Los puertos que salen de los comercios, contra los que leyó el mod.

    Este cruce no se podía hacer hasta hoy y es el bueno: son dos fuentes que
    no se hablan. Uno sale de mirar a qué cambio comerció cada uno con la
    banca; el otro, de leer el tablero. Si el tablero dice que no hay puerto
    de mineral y los tratos dicen que alguien cambió 2 minerales por 1 carta,
    una de las dos lecturas está mal.

    Sólo se miran las partidas que tienen tablero leído: las anteriores al
    21/8 no lo traen y ahí no hay nada contra lo que cruzar."""
    con_tablero = [r[0] for r in conn.execute(
        "SELECT DISTINCT game_id FROM harbors WHERE kind IS NOT NULL")]
    if not con_tablero:
        return saltar("los puertos deducidos contra el tablero (no hay tablero)")

    mal = []
    for partida in con_tablero:
        en_el_mapa = set(r[0] for r in conn.execute(
            "SELECT kind || ' ' || ratio || ':1' FROM harbors WHERE game_id=?",
            (partida,)))
        c, f = V.consultar(conn, "amigos_puertos", partida)
        for puerto in _columna(c, f, "puerto"):
            if puerto == "sin puerto (4:1)":
                continue
            if puerto not in en_el_mapa:
                mal.append("partida %s: se dedujo %s y en el tablero no está"
                           % (partida, puerto))
    comprobar("los puertos deducidos están en el tablero de esa partida",
              not mal, "; ".join(mal))

    # Un tablero no puede tener dos puertos del mismo recurso, y el cambio va
    # con el tipo: los de recurso son 2:1 y los genéricos 3:1, siempre.
    repes = [r for r in conn.execute(
        "SELECT game_id, kind, COUNT(*) FROM harbors WHERE kind <> 'generico' "
        "GROUP BY game_id, kind HAVING COUNT(*) > 1")]
    comprobar("ningún tablero tiene dos puertos del mismo recurso",
              not repes, str(repes))
    torcidos = [r for r in conn.execute(
        "SELECT game_id, kind, ratio FROM harbors WHERE kind IS NOT NULL AND "
        "((kind = 'generico' AND ratio <> 3) OR (kind <> 'generico' AND ratio <> 2))")]
    comprobar("el cambio de cada puerto va con su tipo", not torcidos,
              str(torcidos))


def prueba_un_puerto_lo_pillan_dos_como_mucho(conn):
    """Una arista tiene dos extremos, así que un puerto lo tienen dos sitios.

    Si esta cuenta se pasa de dos, la geometría está mal: querría decir que
    hay vértices que contienen las dos casillas de la arista y no son sus
    extremos, o sea que el cruce está cogiendo cosas que no toca. Hoy la
    tabla está vacía y la prueba no dice nada; el día que se llene, dirá."""
    pasados = [r for r in conn.execute(
        "SELECT harbor_id, COUNT(*) FROM harbor_owners "
        "GROUP BY harbor_id HAVING COUNT(*) > 2")]
    comprobar("ningún puerto lo pillan más de dos sitios", not pasados,
              str(pasados))

    # Y el que lo pilló tiene que ser el dueño de esa pieza, no otro.
    cruzados = conn.execute(
        "SELECT COUNT(*) FROM harbor_owners o JOIN buildings b "
        "ON b.building_id = o.building_id "
        "WHERE b.player_id <> o.player_id OR b.game_id <> o.game_id"
    ).fetchone()[0]
    comprobar("el puerto es de quien puso la pieza", cruzados == 0,
              "%d" % cruzados)

    # La vista tiene que traer LOS NUEVE puertos de cada tablero leído, no
    # sólo los pillados. Media razón de que exista es contestar «¿los 3:1 se
    # los queda alguien o se ignoran?», y eso se responde con las filas que
    # NO tienen dueño. Antes eran dos vistas y la de los nueve enseñaba
    # coordenadas en JSON, así que la pregunta no se podía contestar en
    # ninguna de las dos. Si un día alguien vuelve a filtrar por dueño, la
    # tabla seguirá saliendo bien y habrá perdido justo esa mitad.
    c, f = V.consultar(conn, "amigos_puertos_pillados")
    if not f:
        return saltar("los puertos sin pillar (ningún tablero leído todavía)")
    i = {n: c.index(n) for n in ("partida", "puerto", "quien")}
    porpartida = {}
    for fila in f:
        porpartida.setdefault(fila[i["partida"]], []).append(fila)
    mal = [(p, len(fs)) for p, fs in porpartida.items() if len(fs) != 9]
    comprobar("cada tablero leído trae sus nueve puertos", not mal, str(mal))
    for p, fs in sorted(porpartida.items()):
        conduenyo = sum(1 for x in fs if x[i["quien"]] != "nadie")
        enlatabla = conn.execute(
            "SELECT COUNT(*) FROM harbor_owners WHERE game_id = ?",
            (p,)).fetchone()[0]
        comprobar("los puertos con dueño de la partida %d son los de la tabla"
                  % p, conduenyo == enlatabla,
                  "%d vs %d" % (conduenyo, enlatabla))


def prueba_los_monopolios_son_los_de_la_grabacion(conn):
    """Los monopolios de la vista, contra los del fichero del mod.

    Va al fichero crudo y no a `dev_card_plays` a propósito. La lección es de
    `amigos_puertos`: aquella vista se comparaba con la tabla de la que salía
    y por eso no descubrió nada -- el fallo estaba en el JOIN que las unía, y
    las dos cuentas salían igual de mal. El fichero del mod es el único sitio
    donde el dato no ha pasado por el importador.

    Lo que se compara es la pareja (turno, recurso). El recurso solo prueba la
    traducción; el turno prueba lo que de verdad puede fallar, que es el
    enganche: el juego manda el recurso en la acción SIGUIENTE a jugar la
    carta, así que si el enlace se equivoca de jugada el recurso aparece en
    otro turno -- y con toda la pinta de ser bueno."""
    try:
        from mod_verdad.importar import eventos, ficheros, nombre_de
        from mod_verdad.importar import TERRENO_DEL_JUEGO
    except Exception as e:                       # sin el mod no hay nada que ver
        return saltar("los monopolios contra la grabación (%s)" % e)

    donde = {nombre_de(f): f for f in ficheros()}
    juegos = conn.execute("SELECT carpeta, game_id FROM mod_imports").fetchall()
    if not juegos:
        return saltar("los monopolios contra la grabación (no hay grabaciones)")

    mal, mirados = [], 0
    for carpeta, game_id in juegos:
        ruta = donde.get(carpeta)
        if ruta is None:
            continue                              # la grabación ya no está
        crudos = []
        for ev in eventos(ruta):
            if not str(ev.get("accion") or "").endswith(
                    "Monopoly_SelectResourceType_GameAction"):
                continue
            pedido = (ev.get("detalle") or {}).get("recurso_elegido")
            if not pedido:
                continue                          # grabación anterior al detalle
            crudos.append((ev.get("turno"),
                           TERRENO_DEL_JUEGO.get(pedido, pedido)))
        c, f = V.consultar(conn, "amigos_monopolios", game_id)
        vista = list(zip(_columna(c, f, "turno"), _columna(c, f, "pidio")))
        mirados += 1
        if sorted(crudos) != sorted(vista):
            mal.append("partida %s: grabación %s, vista %s"
                       % (game_id, sorted(crudos), sorted(vista)))
    if not mirados:
        return saltar("los monopolios contra la grabación (no hay ficheros)")
    comprobar("los monopolios son los que hay en la grabación", not mal,
              "; ".join(mal))

    # El recurso, o es uno de los cinco o no se sabe. Un "Wool" aquí sería la
    # traducción sin hacer, y pasaría desapercibido: la vista se pintaría
    # igual de bien y no cuadraría con `amigos_produccion`.
    validos = {"Madera", "Arcilla", "Lana", "Cereales", "Mineral", "sin saber"}
    c, f = V.consultar(conn, "amigos_monopolios")
    raros = set(_columna(c, f, "pidio")) - validos
    comprobar("el recurso del monopolio está en castellano", not raros,
              str(raros))


def prueba_el_reparto_del_monopolio_no_se_inventa(conn):
    """Las dos vistas del monopolio, contra la tabla y entre ellas.

    Son dos formas del mismo dato -- una por monopolio y otra por pareja -- y
    esas son las que un día dicen cosas distintas."""
    huerfanas = conn.execute(
        "SELECT COUNT(*) FROM monopoly_takes t "
        "WHERE t.play_id IS NOT NULL AND NOT EXISTS ("
        "  SELECT 1 FROM dev_card_plays d WHERE d.play_id = t.play_id "
        "   AND d.game_id = t.game_id AND d.card_type = 'Monopolio')"
    ).fetchone()[0]
    comprobar("ningún reparto cuelga de una jugada que no es suya",
              huerfanas == 0, "%d" % huerfanas)

    c, f = V.consultar(conn, "amigos_monopolios_a_quien")
    i = {n: c.index(n) for n in ("quien", "a_quien", "monopolios", "cartas")}
    # Aquí no puede haber ni un NULL: los monopolios sin reparto grabado no
    # entran. Si aparece uno, es que el filtro se ha caído.
    malas = [fila for fila in f
             if fila[i["cartas"]] is None or fila[i["cartas"]] < 0
             or fila[i["monopolios"]] < 1]
    comprobar("todas las cifras del reparto son cifras", not malas,
              str(malas[:3]))

    # Las cinco columnas de recurso tienen que sumar el total. Es la cuenta
    # que se rompe al añadir un recurso nuevo y olvidarse de la columna: la
    # tabla seguiría pintándose bien y el total saldría corto.
    recursos = ("madera", "arcilla", "lana", "cereales", "mineral")
    ir = {n: c.index(n) for n in recursos}
    descuadre = [(fila[i["quien"]], fila[i["a_quien"]])
                 for fila in f
                 if sum(fila[ir[n]] for n in recursos) != fila[i["cartas"]]]
    comprobar("los recursos del monopolio suman el total", not descuadre,
              str(descuadre[:3]))

    # Un monopolio GRABADO afecta a toda la mesa menos al que lo tira, y el
    # importador apunta una fila por rival aunque suelte 0. Sumando la columna
    # `monopolios` tienen que salir esos rivales. Si no, el JOIN duplica o se
    # deja gente -- el fallo que tuvo `amigos_puertos`.
    esperadas = conn.execute(
        "SELECT COALESCE(SUM(cuantos - 1), 0) FROM ("
        "  SELECT d.play_id, (SELECT COUNT(*) FROM players p2 "
        "                      WHERE p2.game_id = d.game_id) AS cuantos "
        "    FROM dev_card_plays d "
        "   WHERE d.card_type = 'Monopolio' "
        "     AND EXISTS (SELECT 1 FROM monopoly_takes t "
        "                  WHERE t.play_id = d.play_id AND t.amount IS NOT NULL) "
        "     AND NOT EXISTS (SELECT 1 FROM players p3 "
        "                      WHERE p3.game_id = d.game_id AND p3.is_bot = 1))"
    ).fetchone()[0]
    suma = sum(fila[i["monopolios"]] for fila in f)
    comprobar("cada monopolio cuenta una vez por cada rival",
              suma == esperadas, "%d filas-monopolio, tocaban %d"
              % (suma, esperadas))

    # Y las cartas contadas aquí son las que hay en la tabla, ni una más.
    en_la_tabla = conn.execute(
        "SELECT COALESCE(SUM(amount), 0) FROM monopoly_takes t "
        "WHERE t.game_id IN (SELECT game_id FROM partidas WHERE con_amigos = 1)").fetchone()[0]
    en_la_vista = sum(fila[i["cartas"]] for fila in f)
    comprobar("las cartas del monopolio son las de la tabla",
              en_la_vista == en_la_tabla,
              "%d vs %d" % (en_la_vista, en_la_tabla))

    # El total de «Los monopolios» tiene que ser el mismo, y su desglose
    # tener una entrada por rival cuando está medido.
    c2, f2 = V.consultar(conn, "amigos_monopolios")
    j = {n: c2.index(n) for n in ("les_saco", "de_quien")}
    total = sum(fila[j["les_saco"]] or 0 for fila in f2)
    comprobar("y las mismas que cuenta «Los monopolios»", total == en_la_tabla,
              "%d vs %d" % (total, en_la_tabla))

    mal_desglose = []
    for fila in f2:
        texto, cifra = fila[j["de_quien"]], fila[j["les_saco"]]
        if cifra is None:
            if texto:
                mal_desglose.append("sin total pero con desglose: %s" % texto)
            continue
        trozos = texto.split(", ") if texto else []
        if sum(int(t.rsplit(" ", 1)[1]) for t in trozos) != cifra:
            mal_desglose.append("%s no suma %s" % (texto, cifra))
    comprobar("el desglose de cada monopolio suma su total",
              not mal_desglose, "; ".join(mal_desglose[:3]))


def prueba_el_importador_sabe_leer_un_reparto():
    """El reparto del monopolio, con un evento inventado y una base de mentira.

    Esta prueba existe porque la alternativa es jugar una partida para saber
    si el código funciona, y eso ya salió mal una vez: los puertos se
    escribieron, se jugó, y lo que llegó estaba vacío. Una partida por intento
    es un ciclo carísimo.

    Aquí se le da al importador exactamente la forma que manda el mod -- la
    que está leída de `Assembly-CSharp.dll`, no adivinada -- y se mira qué
    filas escribe."""
    try:
        from mod_verdad.importar import _Recorrido, crear_tablas
    except Exception as e:
        return saltar("el importador y un reparto de mentira (%s)" % e)

    # Las tablas base son las de `db/schema.sql`; `crear_tablas` sólo añade
    # encima lo que el mod fue necesitando. Se montan las dos, en ese orden,
    # que es como está la base de verdad.
    base = sqlite3.connect(":memory:")
    with open(os.path.join(RAIZ, "db", "schema.sql"), encoding="utf-8") as f:
        base.executescript(f.read())
    crear_tablas(base)
    base.execute("INSERT INTO games (game_id, started_at) VALUES (7, ?)",
                 ("2026-08-22T12:00:00",))
    for pid, nombre in ((70, "yo"), (71, "otro"), (72, "tercero")):
        base.execute("INSERT INTO people (display_name) VALUES (?)", (nombre,))
        base.execute("INSERT INTO players (player_id, game_id, person_name, name) "
                     "VALUES (?,?,?,?)", (pid, 7, nombre, nombre))
    cur = base.execute(
        "INSERT INTO dev_card_plays (game_id, player_id, card_type, turn_number) "
        "VALUES (7, 70, 'Monopolio', 12)")
    play_id = cur.lastrowid

    r = object.__new__(_Recorrido)
    r.conn, r.game_id = base, 7
    r.pid = {0: 70, 1: 71, 2: 72}
    r.ultima_carta = (play_id, 0, 12)
    r.n = collections.Counter()

    ev = {"detalle": {"monopolio": {
        "recurso": "Ore",
        "de": [
            {"jugador": 0, "cartas": [{"recurso": "Ore", "cantidad": 9}]},
            {"jugador": 1, "cartas": [{"recurso": "Ore", "cantidad": 3}]},
            {"jugador": 2, "cartas": []},
        ],
        "crudo": {"lo": "que sea"}}}}
    r._monopolio_reparte(ev, 0, 12, "2026-08-22T12:00:00")

    filas = base.execute(
        "SELECT victim_id, resource, amount FROM monopoly_takes "
        "WHERE game_id=7 ORDER BY victim_id").fetchall()
    comprobar("el reparto se guarda una fila por víctima, sin el que lo tira",
              filas == [(71, "Mineral", 3), (72, "Mineral", 0)], str(filas))

    engancha = base.execute(
        "SELECT COUNT(*) FROM monopoly_takes WHERE play_id=?", (play_id,)).fetchone()[0]
    comprobar("y colgando de la carta que se jugó", engancha == 2, "%d" % engancha)

    # Un reparto que llega vacío tiene que dejar rastro, no desaparecer: si no,
    # una lectura rota se lee igual que «no hubo monopolio».
    r.ultima_carta = None
    r._monopolio_reparte({"detalle": {"monopolio": {"recurso": "Wool", "de": []}}},
                         0, 20, "2026-08-22T12:05:00")
    vacio = base.execute(
        "SELECT victim_id, amount FROM monopoly_takes WHERE turn_number=20").fetchall()
    comprobar("un reparto vacío deja constancia en vez de perderse",
              vacio == [(None, None)], str(vacio))
    base.close()


def prueba_ponerle_nombre_a_alguien_arregla_lo_ya_guardado():
    """El botón «Ponerle nombre a alguien», con una base de mentira.

    Lo que de verdad hay que comprobar no es que cambie el nombre, es que
    arregle **las partidas que ya estaban**. Si sólo valiera para las
    siguientes, el histórico quedaría partido en dos personas -- `jugador_ab`
    hasta hoy y `Pedro` desde mañana -- y ninguna tabla lo diría: las dos
    saldrían bien, cada una con la mitad de las partidas.

    Sobre una base en memoria, que renombrar de verdad y volver a renombrar
    para dejarlo como estaba es la clase de prueba que un día se queda a
    medias y deja la base de Mario con otro nombre."""
    try:
        from mod_verdad.importar import crear_tablas, mandar_llamar
    except Exception as e:
        return saltar("ponerle nombre a alguien (%s)" % e)

    base = sqlite3.connect(":memory:")
    with open(os.path.join(RAIZ, "db", "schema.sql"), encoding="utf-8") as f:
        base.executescript(f.read())
    crear_tablas(base)
    viejo = "jugador_4645eb8a"
    base.execute("INSERT INTO mod_identities (network_id, display_name, is_bot) "
                 "VALUES ('4645eb8a-xx', ?, 0)", (viejo,))
    base.execute("INSERT INTO people (display_name) VALUES (?)", (viejo,))
    for gid in (1, 2):
        base.execute("INSERT INTO games (game_id, started_at, source, winner) "
                     "VALUES (?, ?, 'mod', ?)",
                     (gid, "2026-08-2%dT12:00:00" % gid, viejo))
        base.execute("INSERT INTO players (game_id, person_name, name) "
                     "VALUES (?,?,?)", (gid, viejo, viejo))

    import io as _io
    import contextlib
    with contextlib.redirect_stdout(_io.StringIO()):
        mandar_llamar(base, "4645eb8a-xx", "Pedro")

    quedan = [r[0] for r in base.execute(
        "SELECT DISTINCT person_name FROM players")]
    comprobar("ponerle nombre arregla las partidas ya guardadas",
              quedan == ["Pedro"], str(quedan))
    ganadores = [r[0] for r in base.execute("SELECT winner FROM games")]
    comprobar("y también quién ganó cada una",
              ganadores == ["Pedro", "Pedro"], str(ganadores))
    comprobar("y el nombre provisional no se queda en `people`",
              [r[0] for r in base.execute("SELECT display_name FROM people")]
              == ["Pedro"])
    # Y el identificador sigue siendo el mismo: es la cuenta, no el nombre.
    # Si cambiara, la siguiente partida crearía una persona nueva otra vez.
    comprobar("y el identificador de la cuenta no cambia",
              base.execute("SELECT network_id, display_name FROM mod_identities"
                           ).fetchone() == ("4645eb8a-xx", "Pedro"))
    base.close()

    # Y los avisos del panel, que son los que evitan llamadas que no hacen
    # nada o que hacen algo raro.
    import panel as _panel
    for red, nombre, cacho in (
            ("no-existe", "Pedro", "no conozco"),
            ("4645eb8a-17fd-4a21-bf4d-01ebdd96e0c5", "  ", "hace falta"),
            ("4645eb8a-17fd-4a21-bf4d-01ebdd96e0c5", "jugador_x", "provisional"),
            ("4645eb8a-17fd-4a21-bf4d-01ebdd96e0c5", "x" * 41, "no vale")):
        ok, error = _panel.poner_nombre(red, nombre)
        comprobar("el panel avisa: %s" % cacho,
                  not ok and cacho in (error or ""), str(error))


def prueba_no_hay_gente_de_mentira(conn):
    """`people` sin nombres que no sean de nadie.

    Cada vez que se le pone nombre a alguien con `--llamar`, su nombre
    provisional (`jugador_4645eb8a`) dejaba de usarse pero se quedaba en la
    tabla. No rompía nada -- `people` sólo se escribe -- pero iba creciendo
    con una persona inventada por cada persona de verdad."""
    sobran = [r[0] for r in conn.execute(
        "SELECT display_name FROM people "
        "WHERE display_name NOT IN (SELECT display_name FROM mod_identities) "
        "AND NOT EXISTS (SELECT 1 FROM players p "
        "                 WHERE p.person_name = people.display_name)")]
    comprobar("en `people` no hay nadie que no exista", not sobran, str(sobran))
    # Y al revés: nadie jugando con un nombre que no está en `people`, que es
    # a lo que apunta la clave ajena.
    huerfanos = conn.execute(
        "SELECT COUNT(*) FROM players p WHERE p.person_name IS NOT NULL "
        "AND p.person_name NOT IN (SELECT display_name FROM people)"
    ).fetchone()[0]
    comprobar("y nadie juega con un nombre que no está en `people`",
              huerfanos == 0, "%d jugadores" % huerfanos)


def prueba_las_vistas_viejas_siguen_de_acuerdo(conn):
    """Las dos vistas de `db/schema.sql` contra las que las han sustituido.

    `v_player_number_exposure` y `amigos_numeros` cuentan los mismos edificios
    por número, y `v_player_turn_order` y `jugadores.salida` el mismo orden de
    salida. Se quedan las cuatro porque las viejas funcionan y están
    documentadas, pero dos consultas que contestan lo mismo son dos que un día
    pueden decir cosas distintas -- y nadie sabría cuál mirar."""
    viejas = set(r[0] for r in conn.execute(
        "SELECT name FROM sqlite_master WHERE type='view' AND name LIKE 'v\\_%' "
        "ESCAPE '\\'"))
    if "v_player_number_exposure" not in viejas:
        return saltar("las vistas viejas (ya no están en la base)")

    # `amigos_numeros` pasó a ser global el 2 de septiembre de 2026 -- una
    # fila por persona y número, sin la partida -- así que la vieja se suma
    # por (persona, número) antes de comparar. La comprobación es la misma y
    # de hecho es más dura: si la agregación nueva perdiera o duplicara una
    # partida, la suma dejaría de cuadrar y la de antes ni se enteraba.
    viejas_sumadas = (
        "SELECT v.player_name AS quien, v.number AS numero, "
        "       SUM(v.buildings_on_number) AS edificios "
        "  FROM v_player_number_exposure v "
        "  JOIN partidas p ON p.game_id = v.game_id AND p.con_amigos = 1 "
        " GROUP BY v.player_name, v.number")
    distintas = conn.execute(
        "SELECT COUNT(*) FROM amigos_numeros a "
        "JOIN (%s) v ON v.quien = a.quien AND v.numero = a.numero "
        "WHERE v.edificios <> a.edificios" % viejas_sumadas).fetchone()[0]
    faltan = conn.execute(
        "SELECT COUNT(*) FROM (%s) v "
        "WHERE NOT EXISTS (SELECT 1 FROM amigos_numeros a "
        " WHERE a.quien = v.quien AND a.numero = v.numero)"
        % viejas_sumadas).fetchone()[0]
    comprobar("la vista vieja de números dice lo mismo que amigos_numeros",
              distintas == 0 and faltan == 0,
              "%d distintas, %d filas suyas que no están" % (distintas, faltan))

    # Y los puntitos: la vieja los tenía escritos a mano en un CASE de once
    # ramas, la nueva los calcula. Tienen que dar lo mismo.
    # Aquí no se suma nada: los puntitos son una propiedad del número, así que
    # la vieja tiene el mismo valor en todas las filas de ese número y la nueva
    # uno solo. Comparar contra CUALQUIERA de las viejas vale, y de paso esto
    # comprueba que la nueva no los sumó al agregar -- que era el error fácil.
    pips = conn.execute(
        "SELECT COUNT(*) FROM amigos_numeros a "
        "JOIN v_player_number_exposure v ON v.player_name = a.quien "
        " AND v.number = a.numero "
        "WHERE v.theoretical_pips <> a.puntitos").fetchone()[0]
    comprobar("y los puntitos calculados son los de la tabla escrita",
              pips == 0, "%d distintas" % pips)


def prueba_las_mejoras_no_borran_el_poblado(conn):
    """Una ciudad se mejora DESPUÉS de poner el poblado, nunca antes.

    Al mejorar, la fila del poblado se convierte en ciudad -- si no, el
    jugador tendría los dos a la vez en el mismo vértice. Lo que no puede
    pasar es que se lleve por delante cuándo se puso el poblado, que es lo que
    hacía antes: `turn_number` se sobrescribía con el turno de la mejora y no
    quedaba rastro. Quien mejoraba todos sus poblados salía sin haber
    construido ninguno."""
    mal = conn.execute(
        "SELECT COUNT(*) FROM buildings "
        "WHERE upgraded_turn IS NOT NULL AND upgraded_turn < turn_number"
    ).fetchone()[0]
    comprobar("ninguna ciudad se mejoró antes de existir el poblado",
              mal == 0, "%d filas" % mal)
    # Y quien tiene ciudades tiene que tener cuándo las mejoró.
    sin_marca = conn.execute(
        "SELECT COUNT(*) FROM buildings b JOIN games g USING(game_id) "
        "WHERE b.type='ciudad' AND b.upgraded_turn IS NULL AND g.source='mod'"
    ).fetchone()[0]
    comprobar("y todas las ciudades del mod saben cuándo lo fueron",
              sin_marca == 0, "%d sin marcar" % sin_marca)


def prueba_el_ritmo_va_en_orden(conn):
    """Nadie hace su primera ciudad antes de que empiece la partida."""
    c, f = V.consultar(conn, "amigos_ritmo")
    mal = [fila for fila in f
           if any(fila[c.index(k)] is not None and fila[c.index(k)] < 0
                  for k in ("tercer_poblado", "primera_ciudad",
                            "primera_carta", "primer_caballero"))]
    comprobar("los turnos del ritmo son turnos de verdad", not mal, str(mal))
    # Y nadie llega más lejos de donde acabó la partida.
    fuera = [fila for fila in f
             if fila[c.index("primera_ciudad")] is not None
             and fila[c.index("duro_hasta")] is not None
             and fila[c.index("primera_ciudad")] > fila[c.index("duro_hasta")]]
    comprobar("nadie construye después de acabar la partida", not fuera,
              str(fuera))


def prueba_una_partida_de_ia_no_sale_en_el_global(conn, con_ia):
    """De serie no sale la IA. En NINGUNA vista, no en las que se recuerden.

    Una partida contra la máquina no es una partida peor jugada, es otro
    juego: la IA no propone tratos, no bloquea igual y no aguanta una partida
    larga. Colada en la media no la ensucia un poco, la deja sin significado.

    Se barren todas y no dos: la que se olvide del filtro será la que se
    escriba mañana, y el fallo no se ve mirando -- son cuatro nombres más en
    una tabla que ya tiene cuatro.

    `partidas` y `jugadores` se GUARDAN sin filtrar y tiene que seguir siendo
    así -- casi todas las demás se apoyan en ellas, y si la vista guardada ya
    viniera recortada no habría forma de pedir «todas». Lo que se comprueba
    entonces no es la vista guardada sino lo que se sirve, que es lo que llega
    a la pantalla: el panel pone `amigos` cuando no le dicen otra cosa, y esa
    es la garantía. La segunda mitad de la prueba es justamente ésa."""
    if not con_ia:
        return saltar("las de la IA fuera del global (no hay ninguna)")
    malas = []
    for v in V.VISTAS:
        c, f = V.consultar(conn, v["nombre"], ambito="amigos")
        for col in ("partida", "game_id"):
            if col not in c:
                continue
            i = c.index(col)
            if any(fila[i] in con_ia for fila in f):
                malas.append("%s.%s" % (v["nombre"], col))
    comprobar("ninguna partida contra la IA entra en el global (%d vistas)"
              % len(V.VISTAS), not malas, str(malas))

    # Y que pedir una vista a secas -- sin ámbito y sin partida -- no la sirva
    # sin filtrar. Es el único camino por el que la IA podría llegar sola a la
    # pantalla, y el que se cierra en `panel.ver_vista`.
    import panel as _panel
    ida = _panel.ver_vista("partidas")
    i = ida["columnas"].index("game_id")
    comprobar("pedir una vista sin decir nada la sirve sin la IA",
              not any(fila[i] in con_ia for fila in ida["filas"]),
              str([f[i] for f in ida["filas"]]))


def prueba_el_filtro_de_mesa(conn):
    """El tamaño de mesa: que filtre de verdad, y en todas.

    Es el mismo hueco `{donde}` que el ámbito, así que sale gratis en las 31
    -- y eso es justo lo peligroso: si la condición fuera contra una columna
    equivocada, las 31 tablas seguirían saliendo, con filas, y ninguna
    cantaría. Aquí se comprueba contra lo que las filas DICEN de sí mismas.

    Las dos vistas base son la excepción interesante: en ellas `jugadores` es
    un alias de un subselect y no una columna, así que llevan
    `columna_jugadores` con la cuenta repetida. Si esa repetición se refiriera
    a la tabla equivocada, el filtro daría cero filas o todas, y las dos cosas
    se ven aquí."""
    # 1. Ninguna se rompe con ninguno de los tres valores.
    rotas = []
    for v in V.VISTAS:
        for m in V.MESAS:
            try:
                V.consultar(conn, v["nombre"], None, None, m)
            except Exception as e:
                rotas.append((v["nombre"], m, str(e)[:60]))
    comprobar("las %d vistas contestan con los %d tamaños de mesa"
              % (len(V.VISTAS), len(V.MESAS)), not rotas, str(rotas[:3]))

    # 2. `partidas` lleva su propio tamaño en una columna, así que dice si el
    #    filtro hizo lo que promete sin fiarse de nada de fuera.
    mal = []
    for m, cuadra in (("4", lambda n: n == 4), ("5y6", lambda n: n >= 5)):
        c, f = V.consultar(conn, "partidas", None, "todo", m)
        i = c.index("jugadores")
        coladas = sorted(set(fila[i] for fila in f if not cuadra(fila[i])))
        if coladas:
            mal.append("mesa=%s deja entrar %s" % (m, coladas))
    comprobar("y «Partidas» sólo trae las del tamaño que se pide", not mal,
              "; ".join(mal))

    # 3. Y no se pierde ninguna por el camino: las dos mitades son el total.
    todas = len(V.consultar(conn, "partidas", None, "todo", "todas")[1])
    cuatro = len(V.consultar(conn, "partidas", None, "todo", "4")[1])
    grandes = len(V.consultar(conn, "partidas", None, "todo", "5y6")[1])
    comprobar("las de 4 más las de 5-6 son todas",
              cuatro + grandes == todas,
              "%d + %d != %d" % (cuatro, grandes, todas))

    # 4. La misma comprobación en una vista de las de `_J`, que son 29 de 31
    #    y filtran por otro camino. `amigos_marcador` lleva `eran`, que es
    #    otra vez el tamaño dicho por la propia fila.
    mal = []
    for m, cuadra in (("4", lambda n: n == 4), ("5y6", lambda n: n >= 5)):
        c, f = V.consultar(conn, "amigos_marcador", None, None, m)
        i = c.index("eran")
        coladas = sorted(set(fila[i] for fila in f if not cuadra(fila[i])))
        if coladas:
            mal.append("mesa=%s deja entrar %s" % (m, coladas))
    comprobar("y las vistas de amigos también", not mal, "; ".join(mal))

    # 5. Pedir una partida suelta manda sobre el tamaño de mesa: esa partida
    #    era de los que era. Si el filtro se aplicara igual, pedir una de 4
    #    con «solo mesas de 5 y 6» devolvería una tabla vacía -- que se lee
    #    como «no hay datos» y no como «esa combinación no tiene sentido».
    de4 = [r[0] for r in conn.execute(
        "SELECT game_id FROM partidas WHERE jugadores = 4 LIMIT 1")]
    if de4:
        a = V.consultar(conn, "amigos_marcador", de4[0])[1]
        b = V.consultar(conn, "amigos_marcador", de4[0], None, "5y6")[1]
        comprobar("pedir una partida manda sobre el tamaño de mesa",
                  a == b and len(a) > 0, "%d filas contra %d" % (len(a), len(b)))
    else:
        saltar("una partida manda sobre la mesa (no hay ninguna de 4)")


def prueba_los_tres_ambitos(conn, con_ia, amigas):
    """Los tres ámbitos son el mismo hueco `{donde}`, así que salen gratis en
    todas las vistas. Lo que hay que comprobar es que digan lo que prometen.

    Y que `todo` sea la suma de los otros dos: es la cuenta que se rompe si
    algún día un ámbito filtra por una columna que no es, porque entonces las
    tres tablas siguen saliendo y ninguna canta."""
    if not con_ia or not amigas:
        return saltar("los tres ámbitos (hacen falta partidas de los dos tipos)")
    fallos = []
    for v in V.VISTAS:
        cuenta = {}
        for a in V.AMBITOS:
            c, f = V.consultar(conn, v["nombre"], ambito=a)
            cuenta[a] = (c, f)
            col = next((x for x in ("partida", "game_id") if x in c), None)
            if col is None:
                continue
            i = c.index(col)
            juegos = set(fila[i] for fila in f)
            if a == "amigos" and juegos & set(con_ia):
                fallos.append("%s: amigos trae IA" % v["nombre"])
            if a == "ia" and juegos - set(con_ia):
                fallos.append("%s: ia trae partidas de amigos" % v["nombre"])
            if a == "todo" and not (juegos <= set(con_ia) | set(amigas)):
                fallos.append("%s: todo trae partidas que no existen" % v["nombre"])
        # Las tres tienen que traer las mismas columnas: el ámbito filtra
        # filas, no cambia la forma de la tabla.
        formas = set(tuple(c) for c, _f in cuenta.values())
        if len(formas) > 1:
            fallos.append("%s: cambia de columnas segun el ambito" % v["nombre"])
    comprobar("los tres ámbitos filtran lo que dicen (%d vistas)"
              % len(V.VISTAS), not fallos, str(fallos[:3]))

    # `todo` = `amigos` + `ia`, contado en partidas distintas.
    def juegos(nombre, a):
        c, f = V.consultar(conn, nombre, ambito=a)
        col = next((x for x in ("partida", "game_id") if x in c), None)
        return set(fila[c.index(col)] for fila in f) if col else set()

    mal = [v["nombre"] for v in V.VISTAS
           if juegos(v["nombre"], "todo")
           != juegos(v["nombre"], "amigos") | juegos(v["nombre"], "ia")]
    comprobar("«todas» es exactamente amigos más la IA", not mal, str(mal[:3]))

    # Y el ámbito que no existe da error, no una tabla que parece buena.
    try:
        V.consultar(conn, "partidas", ambito="inventado")
        comprobar("un ámbito que no existe da error", False, "no dio error")
    except ValueError:
        comprobar("un ámbito que no existe da error", True)


def prueba_pedir_una_de_ia_la_da(conn, con_ia):
    """Pero si la pides por su número, la quieres: ahí no se filtra."""
    if not con_ia:
        return saltar("pedir una de la IA por su número (no hay ninguna)")
    c, f = V.consultar(conn, "amigos_marcador", con_ia[0])
    comprobar("pedir una partida de la IA por su número sí la da", len(f) > 0)


def prueba_el_numero_de_partida_no_es_texto(conn):
    """`{donde}` se rellena con un `?`, no pegando el número en el SQL."""
    sql, args = V.sql_de(V.POR_NOMBRE["amigos_marcador"], 4)
    comprobar("la partida viaja como parámetro y no dentro del SQL",
              args == (4,) and "?" in sql and " 4" not in sql.split("WHERE")[1][:40])


def prueba_el_panel_las_sirve(partidas):
    """Las mismas vistas, pero por HTTP, que es como las va a ver el panel."""
    import panel
    srv = ThreadingHTTPServer(("127.0.0.1", PUERTO), panel.Manejador)
    threading.Thread(target=srv.serve_forever, daemon=True).start()

    def pedir(ruta):
        with urllib.request.urlopen(
                "http://127.0.0.1:%d%s" % (PUERTO, ruta), timeout=10) as r:
            return json.loads(r.read().decode("utf-8"))

    def mandar(ruta, dato):
        pet = urllib.request.Request(
            "http://127.0.0.1:%d%s" % (PUERTO, ruta),
            data=json.dumps(dato).encode("utf-8"),
            headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(pet, timeout=10) as r:
            return json.loads(r.read().decode("utf-8"))
    try:
        cat = pedir("/vistas")
        comprobar("el panel lista las %d vistas" % len(V.VISTAS),
                  len(cat["vistas"]) == len(V.VISTAS))
        comprobar("y las partidas, la más nueva primero",
                  [p["id"] for p in cat["partidas"]] == sorted(partidas,
                                                               reverse=True))
        comprobar("una vista que no existe da un error, no una excepción",
                  "error" in pedir("/vista?nombre=loquesea"))

        # Lo que sirve el panel tiene que ser lo mismo que sale por consola.
        # No basta con que conteste: `ver_vista` se olvidaba de releer
        # `db/vistas.py` -- lo hacía sólo `catalogo()` -- así que la lista de
        # vistas salía nueva y la consulta era la vieja. Una vista recién
        # cambiada devolvía 0 filas, que se lee como «no hay nada» y no como
        # un fallo.
        conn2 = sqlite3.connect("file:%s?mode=ro" % BASE.replace("\\", "/"),
                                uri=True)
        una = max(partidas)
        distintos = []
        try:
            # Los tres ámbitos y una partida suelta. Y el caso «a secas»,
            # que en el panel quiere decir amigos: `partidas` y `jugadores`
            # se guardan sin filtrar, así que ahí es donde se notaría que el
            # panel sirve la forma cruda sin que nadie se la haya pedido.
            casos = [(None, None), (None, "amigos"), (None, "todo"),
                     (None, "ia"), (una, None)]
            for v in V.VISTAS:
                for p, a in casos:
                    c, f = V.consultar(conn2, v["nombre"], p,
                                       a or (None if p else "amigos"))
                    r = pedir("/vista?nombre=%s%s%s" % (
                        v["nombre"],
                        "" if p is None else "&partida=%d" % p,
                        "" if a is None else "&ambito=%s" % a))
                    if r.get("columnas") != c or len(r.get("filas", [])) != len(f):
                        distintos.append("%s%s%s" % (
                            v["nombre"], "" if p is None else "/%d" % p,
                            "" if a is None else "/%s" % a))
        finally:
            conn2.close()
        comprobar("el panel sirve exactamente lo que sale por consola",
                  not distintos, str(distintos))

        # Y que las dos puertas de entrada relean, no sólo una. Es la que se
        # olvidó, y por HTTP no se ve mientras el módulo esté recién cargado.
        import inspect
        comprobar("las dos puertas del panel releen las vistas",
                  all("_vistas_al_dia()" in inspect.getsource(f)
                      for f in (panel.catalogo, panel.ver_vista)))
        # Que no llegue SQL por la barra de direcciones. La partida se pasa
        # por int() antes de tocar la base, y esto lo deja escrito.
        comprobar("un número de partida que no es un número da error",
                  "error" in pedir("/vista?nombre=amigos_mazo&partida=1;DROP"))
        with urllib.request.urlopen("http://127.0.0.1:%d/" % PUERTO,
                                    timeout=10) as r:
            html = r.read().decode("utf-8")
        # El desplegable lleva los tres ámbitos, y los manda el servidor:
        # escritos también en el HTML habría dos sitios que actualizar el día
        # que se añada uno, y el que se olvidaría es el de la página.
        cat = pedir("/vistas")
        comprobar("el catálogo manda los tres ámbitos",
                  [a["id"] for a in cat.get("ambitos", [])] == list(V.AMBITOS),
                  str(cat.get("ambitos")))
        comprobar("y un ámbito inventado da error, no una tabla",
                  "error" in pedir("/vista?nombre=partidas&ambito=loquesea"))
        comprobar("la página trae el selector, los botones y el escapador",
                  'id="selPartida"' in html and 'id="botonesVista"' in html
                  and "function escapar(" in html)
        # El paginado vive entero en el navegador, así que lo único que se
        # puede comprobar desde aquí es que las piezas estén y que el número
        # sea el que se dice en la documentación. Lo que de verdad se vigila:
        # que la página se reinicie al filtrar y al cambiar de vista. Sin eso,
        # saltar de una tabla de 100 filas a una de 5 la deja en blanco --
        # sigues en la página 7 y allí no hay nada. Parece «no hay datos».
        # 11 y no 10: los dados son once numeros, y «Las tiradas» tiene once
        # filas SIEMPRE -- las saca de un VALUES fijo para que un numero que
        # no salio nunca tenga su fila igual. Con 10 esa tabla se partia en
        # dos paginas y la segunda traia una sola fila.
        comprobar("la tabla se pagina, y de 11 en 11",
                  "const POR_PAGINA = 11;" in html and 'id="pSig"' in html
                  and 'id="pTodas"' in html)
        comprobar("y la página vuelve a la 1 al filtrar y al cambiar de vista",
                  html.count("pagina = 0;") >= 3)
        comprobar("y el filtro, con su normalizador de acentos",
                  'id="filtro"' in html and "function normaliza(" in html
                  and "\\u0300-\\u036f" in html)
        comprobar("y la regla de números enteros contra texto por dentro",
                  "function coincide(" in html)
        # El orden por cabecera es de la tabla, no de cada vista: se escribe
        # una vez y lo tienen las 27 y las que vengan. Por eso se comprueba
        # aquí y no vista por vista.
        comprobar("se puede ordenar tocando la cabecera",
                  "function engancharCabeceras(" in html
                  and 'class="orden' in html and "data-col=" in html)
        comprobar("y los nombres se ordenan como nombres, no como bytes",
                  "localeCompare(" in html and 'sensitivity: "base"' in html)
        # Dos cosas que se rompen solas y no se ven mirando la pantalla:
        # ordenar después de partir en páginas (ordenas diez filas de cien) y
        # subir los NULL al ordenar de mayor a menor, como si «no se sabe»
        # fuera el número más alto.
        comprobar("y ordena la tabla entera, no la página que se ve",
                  html.index("filas.slice().sort(")
                  < html.index("filas.slice(pagina * POR_PAGINA"))
        comprobar("y los «no se sabe» se quedan abajo",
                  "if (x === null) return 1;" in html)
        # El orden se suelta al cambiar de vista: la columna 3 de una no es la
        # 3 de la otra, y arrastrarlo deja tablas ordenadas por una columna
        # que no has tocado nunca.
        comprobar("y el orden no se arrastra de una vista a otra",
                  "orden = null;" in html)
        # El botón de los nombres: que la lista se sirva y que la página
        # tenga con qué pintarla. Lo de dentro (que renombrar arregle el
        # histórico) va aparte, contra una base de mentira.
        g = pedir("/gente")
        comprobar("el panel sirve quién es quién",
                  isinstance(g.get("gente"), list)
                  and all("red" in x and "provisional" in x
                          for x in g["gente"]), str(g)[:120])
        # Cada botón que lanza una tarea tiene que existir en las dos puntas:
        # el par `["bX","tarea"]` en la página y la orden en `TAREAS`. Quitar
        # uno son tres sitios -- el botón, el par y la orden -- y olvidarse de
        # cualquiera deja o un botón que no hace nada o una orden muerta.
        # Ninguna de las dos se ve mirando la pantalla.
        # Se cuentan las dos formas de engancharlos: los del bucle, en pares,
        # y los tres que van sueltos porque hacen algo más antes de pedir.
        import re
        pares = set(re.findall(r'\["(b\w+)","(\w+)"\]', html))
        pares |= set(re.findall(r'boton\("(b\w+)",.*?que:"(\w+)"', html))
        # Contra la pagina COMPLETA, no contra la que se acaba de servir: hay
        # trozos que el servidor quita segun lo que haya en esta copia, y en
        # un clon sin la mitad de entrenar la mitad de estos botones no
        # existe. Eso no es un fallo -- `boton()` lo tolera a proposito --
        # pero un nombre mal escrito sigue siendo un fallo, y contra la
        # pagina entera se sigue viendo.
        botones = set(re.findall(r'id="(b\w+)"', panel.PAGINA))
        comprobar("cada botón de tarea tiene su orden y al revés",
                  set(t for _b, t in pares) == set(panel.TAREAS),
                  str(set(t for _b, t in pares) ^ set(panel.TAREAS)))
        sueltos = [b for b, _t in pares if b not in botones]
        comprobar("y no hay ninguno que apunte a un botón que no existe",
                  not sueltos, str(sueltos))
        # Y que tolerarlo no sea casualidad: sin esta linea, el primer botón
        # que falte revienta y deja sin cablear TODOS los de después -- el
        # panel entero muerto, y sin un error a la vista.
        comprobar("y cablear uno que no está no rompe el resto",
                  "if (!document.getElementById(id)) return;" in panel.PAGINA)
        comprobar("y la página trae el botón de ponerle nombre",
                  'id="bNombres"' in html and 'id="gente"' in html
                  and "function pintarGente(" in html)
        comprobar("y avisa por HTTP si el identificador no existe",
                  mandar("/llamar", {"red": "no-existe", "nombre": "Pedro"})
                  .get("ok") is False)
        # La caja de preguntas. Lo que se comprueba no es que acierte -- eso
        # depende de cómo escriba cada uno -- sino las tres cosas que la hacen
        # fiable: que conteste con un número que sale de una vista de verdad,
        # que diga de dónde, y que cuando no sepa lo diga en vez de apañar
        # algo. Lo último es lo importante: un buscador que siempre contesta
        # es un buscador en el que no se puede confiar.
        import panel as _p
        #
        # Cada una de estas se escribio porque la caja fallaba en ella, y las
        # cuatro ultimas son la misma leccion: una respuesta EQUIVOCADA con
        # cara de buena es mucho peor que un «no lo se».
        pruebas_pregunta = [
            ("cuantos caballeros le han caido a alguien",
             "amigos_desarrollo", "caballero"),
            ("quien ha tenido mas suerte", "amigos_suerte", "suerte"),
            ("cuanto mineral ha producido alguien", "amigos_produccion",
             "mineral"),
            ("cuantas tiradas ha habido en total", "partidas", "tiradas"),
            # Un eje no es una cantidad. Antes contestaba «el que mas numero:
            # LoboEstepario, con 11», que era el numero de casilla mas alto.
            ("numeros que mas bloquea el ladron",
             "amigos_ladron_numeros", "numero"),
            # Y la vista tiene que ser la del TABLERO, no la de por persona:
            # sumando a los cuatro son 23 veces, y en la de cada uno son 4.
            ("que numeros tapa mas el ladron",
             "amigos_ladron_numeros", "numero"),
            # Sin nadie nombrado y sin «quien», la pregunta es de la mesa.
            ("que numero sale mas", "amigos_tiradas", "numero"),
            ("quien ha perdido mas recursos por el ladron y que recursos",
             "amigos_ladron", "perdido"),
            # Y con «quien», la vista tiene que saber de gente: la de numeros
            # sabe cuantas veces y no de quien, y contestaba «1 veces».
            ("quien tapo el 11", "amigos_ladron_donde", None),
            # «A QUIEN» y «CON QUIEN» piden un NOMBRE, y solo lo tienen las
            # vistas de parejas. Sin esto se iban a la vista que se llamara
            # igual que la pregunta: «a quien le roba mas X» acababa en
            # «Robos de la mano» -- que se llama robos y gana por nombre --
            # contestando todo lo que ha robado en su vida, a nadie en
            # concreto. El numero estaba bien y no era la pregunta.
            ("a quien le pone mas el ladron alguien",
             "amigos_ladron_a_quien", "se_lo_puso"),
            ("a quien le roba mas alguien",
             "amigos_ladron_a_quien", "le_robo"),
            ("con quien ha hecho mas tratos alguien",
             "amigos_comercio", "tratos"),
            # Y sin «a quien», la misma palabra tiene que seguir yendo a la
            # vista de siempre: la penalizacion no puede llevarse por delante
            # las preguntas normales.
            ("cuantos robos ha hecho alguien", "amigos_robos", "robo_el"),
            ("quien roba mas", "amigos_robos", "robo_el"),
        ]
        _quien = sqlite3.connect("file:%s?mode=ro" % BASE.replace("\\", "/"),
                                 uri=True).execute(
            "SELECT quien FROM jugadores WHERE es_ia = 0 "
            "GROUP BY quien ORDER BY COUNT(*) DESC LIMIT 1").fetchone()
        fallos = []
        for texto, vista, columna in pruebas_pregunta:
            if "alguien" in texto:
                # Sin nadie con apodo -- un clon recien bajado -- estas no se
                # pueden hacer: la caja se niega a adivinar entre nombres
                # provisionales, y eso es lo correcto.
                if not _quien or _quien[0].startswith("jugador_"):
                    continue
                texto = texto.replace("alguien", _quien[0])
            r = _p.preguntar(texto)
            if r.get("vista") != vista or r.get("columna") != columna:
                fallos.append((texto, r.get("vista"), r.get("columna")))
        comprobar("la caja de preguntas encuentra la columna buena",
                  not fallos, str(fallos))
        # El número que dice tiene que estar en la tabla que enseña debajo.
        #
        # El nombre sale de la base y no escrito aquí: en esta máquina la
        # gente se llama `elGato`, y en un clon recién bajado `jugador_...`,
        # porque el apodo lo pone quien importa y vive en la base, que no va
        # al repositorio.
        conn2b = sqlite3.connect("file:%s?mode=ro" % BASE.replace("\\", "/"),
                                 uri=True)
        alguien = conn2b.execute(
            "SELECT quien FROM jugadores WHERE es_ia = 0 "
            "GROUP BY quien ORDER BY COUNT(*) DESC LIMIT 1").fetchone()[0]
        # En un clon recien bajado nadie tiene apodo todavia: todos se llaman
        # `jugador_<8 letras>` y la caja se NIEGA a adivinar cual es cual, que
        # es lo correcto. Estas tres preguntas hablan de personas concretas,
        # asi que ahi no hay nada que comprobar hasta que alguien ponga los
        # nombres -- el paso 2 del panel.
        provisionales = all(
            q.startswith("jugador_") for (q,) in conn2b.execute(
                "SELECT DISTINCT quien FROM jugadores WHERE es_ia = 0"))
        if provisionales:
            saltar("las preguntas por persona (nadie tiene nombre todavia: "
                   "ponselos con «Ponerle nombre a alguien»)")
            conn2b.close()
            return
        r = _p.preguntar("cuantos caballeros le han caido a %s" % alguien)
        i = r["columnas"].index("caballero")
        j = r["columnas"].index("quien")
        real = sum(f[i] for f in r["filas"] if f[j] == alguien)
        comprobar("y el número que dice está en la tabla que enseña",
                  str(real) in r["respuesta"],
                  "%s / %s" % (real, r["respuesta"]))
        comprobar("y dice de dónde lo ha sacado",
                  "db/vistas.py --ver" in r.get("de_donde", ""))
        # «...y que recursos» es media pregunta, y antes se quedaba sin
        # contestar teniendo el desglose en la fila de al lado.
        r3 = _p.preguntar("quien ha perdido mas recursos por el ladron "
                          "y que recursos")
        comprobar("y contesta la segunda mitad de la pregunta",
                  "arcilla" in r3.get("respuesta", "").lower(),
                  r3.get("respuesta"))
        # Pero no la pega cuando lo preguntado ES un recurso: «cuanto mineral»
        # no se contesta con «sobre todo cereales».
        r4 = _p.preguntar("cuanto mineral ha producido %s" % alguien)
        comprobar("y no la pega cuando ya preguntas por un recurso",
                  "sobre todo" not in r4.get("respuesta", "").lower(),
                  r4.get("respuesta"))
        # Agrupar: contestar cosas que NO estan en ninguna vista, juntando
        # filas de una que si existe. Sin esto habria que crear una vista por
        # cada pregunta, y ya pasó una vez.
        r5 = _p.preguntar("que recurso se comercia mas")
        comprobar("junta las filas de una vista para contestar lo que no hay",
                  r5.get("vista") == "amigos_comercio_material"
                  and "juntando" in r5.get("respuesta", ""),
                  r5.get("respuesta"))
        # Y solo suma lo que se puede sumar. Un porcentaje o una media no.
        c5, f5 = V.consultar(conn2b, "amigos_suerte")
        cg, fg = _p._agrupar(c5, f5, "quien")
        comprobar("y no suma porcentajes ni medias al juntar",
                  cg is not None and "suerte" not in cg and "margen" not in cg
                  and "casillas" in cg, str(cg))
        # «Que carta sale mas del mazo» leia `en_el_mazo`, que es el
        # porcentaje que el mazo LLEVA DENTRO -- ni siquiera es lo que salio.
        r6 = _p.preguntar("que carta sale mas del mazo")
        comprobar("y elige una medida que se pueda contar, no un porcentaje",
                  "salieron" in r6.get("respuesta", ""), r6.get("respuesta"))
        # Filtrar por un valor de la pregunta. El «11» es un valor, no una
        # cantidad, y contarlo como cantidad daba «el que mas caballero:
        # carlarr, con 11» -- una respuesta con toda la pinta de buena.
        # Cuantos sietes hay AHORA. Estuvo escrito a mano -- un «61» -- y se
        # cayo el dia que entro la partida 12: la prueba fallaba sin que
        # hubiera nada roto, que es la peor clase de prueba, porque la
        # siguiente vez ya no se la cree nadie. Lo que se comprueba es que el
        # «7» se tome como VALOR a filtrar y no como una cantidad; el numero
        # con el que se compara tiene que salir de la base, igual que sale la
        # respuesta.
        c7, f7 = V.consultar(conn2b, "amigos_tiradas")
        sietes = str(dict(zip(_columna(c7, f7, "numero"),
                              _columna(c7, f7, "veces")))[7])
        # Los nombres NO se escriben a mano. En esta maquina la gente se llama
        # `carlarr` y `LoboEstepario`; en un clon recien bajado se llaman
        # `jugador_4645eb8a`, porque el apodo lo pone quien importa y vive en
        # la base, que no va al repositorio. Con los nombres escritos, estas
        # cinco pruebas fallaban en cuanto alguien se descargara esto -- y lo
        # primero que veria es un 194 de 199 sin nada roto.
        def el_que_mas(vista, columna, **filtro):
            c, f = V.consultar(conn2b, vista)
            filas = [dict(zip(c, x)) for x in f]
            for k, v in filtro.items():
                filas = [x for x in filas if x.get(k) == v]
            if not filas:
                return None
            return max(filas, key=lambda x: x[columna] or 0)["quien"]

        tapa_el_11 = el_que_mas("amigos_ladron_donde", "veces", numero=11)
        caballero_3 = el_que_mas("amigos_ladron_donde", "con_caballero", numero=3)
        gano_la_7 = conn2b.execute(
            "SELECT gano FROM partidas WHERE game_id = 7").fetchone()
        casos_filtro = [
            ("quien ha puesto el ladron en el 11", [tapa_el_11 or "", "11"]),
            ("quien puso el caballero en el 11", ["11", "0"]),
            ("quien ha puesto un caballero en el 3", [caballero_3 or ""]),
            ("cuantos 7 han salido", [sietes]),
            ("en la partida 7 quien gano", [gano_la_7[0] if gano_la_7 else ""]),
        ]
        malos = []
        for texto, trozos in casos_filtro:
            resp = (_p.preguntar(texto).get("respuesta") or "").lower()
            faltan = [t for t in trozos if t.lower() not in resp]
            if faltan:
                malos.append((texto, faltan, resp[:60]))
        comprobar("filtra por el valor que dice la pregunta", not malos,
                  str(malos[:2]))
        # Y un numero suelto NO es una partida: «cuantos 7 han salido»
        # acababa filtrando la partida 7 y contestando 64, sus tiradas.
        comprobar("y un numero suelto no se toma por una partida",
                  sietes in (_p.preguntar("cuantos 7 han salido")
                             .get("respuesta") or ""))
        # Turnos y medias NO se suman. «En que turno hizo su primera ciudad»
        # contestaba 131, que es la suma de cinco turnos.
        r7 = _p.preguntar("en que turno hizo su primera ciudad %s" % alguien)
        comprobar("y no suma turnos, que no se suman",
                  "131" not in (r7.get("respuesta") or ""), r7.get("respuesta"))
        # «Menos» es el otro extremo, no «mas» dicho al reves. Y las
        # columnas de turno no compiten por nombre -- `primera_ciudad` no se
        # llama «turno» -- asi que «quien tardo menos en poner una ciudad»
        # acababa contando ciudades y contestando con el que mas tiene.
        # Igual que arriba: el nombre sale de la tabla, no de esta maquina.
        cr, fr = V.consultar(conn2b, "amigos_ritmo")
        conr = [dict(zip(cr, x)) for x in fr
                if dict(zip(cr, x)).get("primera_ciudad") is not None]
        pronto = min(conr, key=lambda x: x["primera_ciudad"]) if conr else None
        casos_menos = [
            ("quien ha tardado menos en poner una ciudad",
             ["menos"] + ([pronto["quien"], str(pronto["primera_ciudad"])]
                          if pronto else [])),
            ("quien roba menos", ["menos"]),
        ]
        peor = []
        for texto, trozos in casos_menos:
            resp = (_p.preguntar(texto).get("respuesta") or "").lower()
            faltan = [t for t in trozos if t.lower() not in resp]
            if faltan:
                peor.append((texto, faltan, resp[:60]))
        comprobar("«menos» contesta con el otro extremo", not peor,
                  str(peor[:2]))

        # DOS personas: las vistas de parejas tienen `quien` y `a_quien`, y
        # con una sola no se puede contestar. Lo importante es lo de abajo:
        # cuando la pareja no tiene filas, la respuesta es CERO, y antes se
        # devolvian las filas de uno de los dos -- «lobo le ha puesto el
        # ladron a bruno» contestaba 19, que son las de lobo con todos.
        # La pareja que más veces aparece, y una que no aparece nunca: las dos
        # salen de la tabla, por lo mismo que arriba.
        cp, fp = V.consultar(conn2b, "amigos_ladron_a_quien")
        pares = [dict(zip(cp, x)) for x in fp]
        con_filas = [p for p in pares if (p.get("se_lo_puso") or 0) > 0]
        if not con_filas:
            saltar("las preguntas de dos personas (nadie ha puesto el ladrón)")
        else:
            mejor = max(con_filas, key=lambda p: p["se_lo_puso"])
            r8 = _p.preguntar("cuantas veces le ha puesto %s el ladron a %s"
                              % (mejor["quien"], mejor["a_quien"]))
            comprobar("entiende una pregunta de dos personas",
                      mejor["quien"] in (r8.get("respuesta") or "")
                      and mejor["a_quien"] in (r8.get("respuesta") or "")
                      and str(mejor["se_lo_puso"]) in (r8.get("respuesta") or ""),
                      r8.get("respuesta"))

            # Y una pareja SIN filas: la respuesta es cero, no el total de uno
            # de los dos. Antes «lobo le ha puesto el ladrón a bruno»
            # contestaba 19, que son las de lobo con todo el mundo.
            gente = sorted(set(p["quien"] for p in pares)
                           | set(p["a_quien"] for p in pares))
            hay = set((p["quien"], p["a_quien"]) for p in con_filas)
            vacia = next(((a, b) for a in gente for b in gente
                          if a != b and (a, b) not in hay), None)
            if vacia is None:
                saltar("la pareja sin filas (todas las parejas tienen alguna)")
            else:
                total_de_uno = sum(p["se_lo_puso"] or 0
                                   for p in pares if p["quien"] == vacia[0])
                r9 = _p.preguntar("veces que %s ha puesto el ladron a %s"
                                  % vacia)
                resp = r9.get("respuesta") or ""
                comprobar("y una pareja sin filas es cero, no el total de uno",
                          str(total_de_uno) not in resp and "ninguna" in resp,
                          resp)
        conn2b.close()
        # Lo que no sabe, no se lo inventa.
        r2 = _p.preguntar("que tiempo hace manana en bilbao")
        comprobar("y lo que no sabe lo dice, no se lo inventa",
                  r2.get("sin_respuesta") is True and not r2.get("vista"),
                  str(r2)[:120])
        comprobar("la página trae la caja de preguntas",
                  'id="pregunta"' in html and 'id="respuesta"' in html
                  and "function preguntar(" in html)
        comprobar("y se puede preguntar por HTTP",
                  "respuesta" in pedir("/preguntar?q=" + urllib.parse.quote(
                      "quien ha tenido mas suerte")))
        comprobar("el desplegable arranca en «solo con amigos»",
                  '<option value="amigos">' in html
                  and 'sel.value = "amigos"' in html)
        comprobar("y separa el grupo de partidas de la partida suelta",
                  "Todas las partidas" in html and "Una sola partida" in html)
        # La página vive dentro de panel.py, y panel.py no se recarga solo.
        # Media reencarnación es peor que ninguna: `db/vistas.py` sí se relee,
        # así que el panel se quedaba con SQL nuevo y pantalla vieja -- tocas
        # la cabecera, no pasa nada, y nada dice por qué.
        comprobar("la página se relee del fichero, no de la memoria",
                  "_pagina_al_dia()" in inspect.getsource(panel.Manejador.do_GET))
        comprobar("y lo que saca del fichero es la página entera",
                  panel._pagina_al_dia() == panel.PAGINA)

        # LA OTRA MITAD, que es la que engaña de verdad: la página se relee,
        # el código no. Un panel abierto de antes sirve botones nuevos contra
        # un servidor viejo, la ruta nueva da 404 y el botón no hace nada.
        #
        # Pasó con «Quitar una partida»: estaba todo bien escrito, y en el
        # panel de Mario el botón no quitaba nada.
        #
        # Se comprueban las dos piezas del aviso: que el servidor sepa
        # decirlo y que la página lo enseñe.
        # La fecha se enseña como se lee -- día, mes, año -- y se GUARDA en
        # ISO. Las dos mitades importan: si se guardara dada la vuelta, el
        # `ORDER BY dia` de media docena de vistas pondría el 31 de agosto
        # antes que el 1 de septiembre, y el resultado parecería correcto.
        comprobar("la fecha se enseña en día/mes/año",
                  panel._dia_es("2026-08-31") == "31/08/2026")
        comprobar("y lo que no es una fecha se queda como está",
                  panel._dia_es("no soy una fecha") == "no soy una fecha"
                  and panel._dia_es(None) is None)
        cat = panel.catalogo()
        comprobar("y las partidas del panel salen así",
                  all(re.match(r"^\d{2}/\d{2}/\d{4}", p["texto"])
                      for p in cat["partidas"]),
                  str([p["texto"][:12] for p in cat["partidas"][:3]]))
        _cx = sqlite3.connect(BASE)
        _c, _f = V.consultar(_cx, "partidas")
        _cx.close()
        comprobar("pero por debajo sigue en ISO, que es lo que se ordena",
                  all(re.match(r"^\d{4}-\d{2}-\d{2}$", str(x))
                      for x in _columna(_c, _f, "dia")))
        comprobar("y la tabla del panel la da la vuelta al pintarla",
                  "function fecha(" in html and "resaltar(fecha(v), aguja)" in html)

        # Un solo panel, no dos. Montar dos APIs habría sido más fácil de
        # escribir y más fácil de que se separaran: el 90% de las rutas son
        # las mismas. En vez de eso, los trozos de la página que no son para
        # todo el mundo van marcados y el servidor los QUITA.
        fuera = [k for k, (_n, o) in panel.TAREAS.items()
                 if panel._es_de_desarrollo(o)]
        comprobar("el panel sabe qué se enseña y qué no",
                  len(panel.A_LA_VISTA) >= 3 and len(fuera) >= 8,
                  "%d a la vista, %d fuera" % (len(panel.A_LA_VISTA), len(fuera)))
        # Una errata en `A_LA_VISTA` dejaría ese botón escondido sin decir
        # nada, y sería justo el botón que se quería enseñar.
        inventadas = sorted(set(panel.A_LA_VISTA) - set(panel.TAREAS))
        comprobar("y todo lo que dice enseñar existe", not inventadas,
                  str(inventadas))
        # Cada tarea tiene que apuntar a un fichero, y el que se OFRECE
        # tiene que existir. Los de la mitad de entrenar pueden faltar --en
        # un clon faltan, que es justo el caso-- y por eso no se exigen
        # siempre: se exigen cuando el panel dice tenerlos.
        sin_ruta = [k for k, (_n, o) in panel.TAREAS.items()
                    if not panel._script_de(o)]
        comprobar("cada tarea del panel apunta a un fichero", not sin_ruta,
                  str(sin_ruta))
        hay_que_estar = set(panel.A_LA_VISTA)
        if panel.hay_desarrollo():
            hay_que_estar |= set(panel.TAREAS)
        if not panel.hay_vision():
            hay_que_estar.discard("mirar")
        perdidas = sorted(k for k in hay_que_estar
                          if not os.path.isfile(
                              panel._script_de(panel.TAREAS[k][1])))
        comprobar("y el fichero de lo que ofrece está", not perdidas,
                  str(perdidas))

        # Las marcas tienen que estar emparejadas. Una <!--dev--> sin cerrar
        # se comería el resto de la página de una sentada, y en la versión de
        # siempre no se notaría: sólo la vería quien se descargue esto.
        abre = panel.PAGINA.count("<!--dev-->")
        cierra = panel.PAGINA.count("<!--/dev-->")
        comprobar("las marcas de lo que no se enseña están emparejadas",
                  abre == cierra and abre >= 4, "%d abren, %d cierran"
                  % (abre, cierra))

        antes = panel.MODO_USUARIO
        try:
            panel.MODO_USUARIO = True
            comprobar("y se puede ver el panel de usar esto",
                      panel.hay_desarrollo() is False)
            simple = panel._pagina_para(panel.PAGINA, False)
            comprobar("no queda ni una marca sin resolver",
                      "<!--dev-->" not in simple
                      and "<!--/dev-->" not in simple)
            # Lo que tiene que salir, y lo que no.
            hay = set(re.findall(r'id="(b[A-Z]\w*)"', simple))
            faltan = {"bInstalar", "bSoloMod", "bParar", "bImportar",
                      "bAnalizar", "bMirar", "bQuitar", "bMatar"} - hay
            comprobar("sale lo de tener tus datos y leer la pantalla",
                      not faltan, str(sorted(faltan)))
            cuelan = hay & {"bEmpezar", "bDataset", "bRutina", "bEntrenar",
                            "bEntrenarTodo", "bHistorial", "bMedir",
                            "bTablero", "bEnsayo", "bMesa", "bPruebas"}
            comprobar("y no sale nada de grabar capturas ni de entrenar",
                      not cuelan, str(sorted(cuelan)))
            comprobar("ni la lista de partidas grabadas ni el modelo",
                      'id="partidas"' not in simple
                      and 'id="modelo"' not in simple)
            # Lo que queda tiene que seguir siendo HTML entero: el recorte
            # tiene que llevarse tantas aperturas como cierres. Se compara
            # con la página completa y NO se exige que cuadre en absoluto:
            # dentro del <script> hay `<div>` en cadenas de texto, así que el
            # total nunca cuadra y pedirlo sería una prueba que falla siempre
            # por un motivo que no es. Lo que no puede cambiar es el saldo.
            def saldo(h):
                return h.count("<div") - h.count("</div>")
            comprobar("y lo que queda sigue siendo una página entera",
                      saldo(simple) == saldo(panel.PAGINA),
                      "saldo %d, y la entera %d"
                      % (saldo(simple), saldo(panel.PAGINA)))
            # Esconder no basta: la ruta contesta a quien la llame.
            r = mandar("/tarea", {"que": fuera[0]})
            comprobar("y la ruta se niega, no solo desaparece el botón",
                      r.get("ok") is False and "disponible" in (r.get("error") or ""),
                      str(r))
        finally:
            panel.MODO_USUARIO = antes

        comprobar("el panel sabe si su propio código se ha quedado atrás",
                  "codigo_viejo" in panel.estado())

        # Y no salta por cualquier cosa. El aviso rojo se comparaba con la
        # FECHA del fichero, asi que tocar la pantalla -- que se relee sola y
        # con F5 basta -- mandaba a cerrar la ventana negra sin motivo. Un
        # aviso que salta cuando no hace falta ensenia a no leer los avisos.
        fuente = io.open(panel.__file__, encoding="utf-8").read()
        huella = panel._huella_del_codigo(fuente)
        comprobar("el panel sabe sacar la huella de su propio código",
                  huella is not None)
        # Que la PAGINA se le quita de verdad: si un dia dejara de encontrarla
        # -- porque se parta en dos, o se saque a un fichero -- todo contaria
        # como codigo y volveriamos al aviso de antes sin que se note.
        pelado = panel._sin_la_pagina(fuente)
        comprobar("y la página no está en esa huella",
                  "<!doctype html>" not in pelado)
        comprobar("pero el código sí", "def _codigo_viejo" in pelado)

        # Y en pequeño, con un módulo de mentira: la página cambia y la
        # huella no; una función cambia y la huella sí.
        ejemplo = "\n".join((
            "import os",
            "",
            "",
            'PAGINA = r"""<html>hola</html>"""',
            "",
            "",
            "def f():",
            "    return 1",
            ""))
        comprobar("tocar la página no cambia la huella",
                  panel._huella_del_codigo(ejemplo.replace("hola", "adios"))
                  == panel._huella_del_codigo(ejemplo))
        comprobar("y tocar el código sí",
                  panel._huella_del_codigo(ejemplo.replace("return 1", "return 2"))
                  != panel._huella_del_codigo(ejemplo))
        comprobar("un fichero a medio guardar no cuenta como cambio",
                  panel._huella_del_codigo("def x(:") is None)
        comprobar("y la página avisa cuando pasa",
                  'id="desfase"' in html and "e.codigo_viejo" in html)

        # Y de paso, lo que habría cazado el fallo mirando sólo el fichero:
        # ninguna ruta que la página llame puede faltar en el servidor.
        rutas = set(re.findall(r'pedir\("(/[a-z_]+)', html))
        atiende = (inspect.getsource(panel.Manejador.do_GET)
                   + inspect.getsource(panel.Manejador.do_POST))
        huerfanas = sorted(r for r in rutas if '"%s"' % r not in atiende)
        comprobar("y las %d rutas que la página llama existen en el servidor"
                  % len(rutas), not huerfanas, str(huerfanas))
    finally:
        srv.shutdown()


# --------------------------------------------------------------------------

def prueba_los_titulares_salen_de_las_tablas(conn):
    """Los cinco titulares de la portada, contra las tablas que enlazan.

    Es la unica prueba que importa de esa portada. Un titular es una FRASE
    con un numero dentro, y una frase se lee como verdad sin comprobar nada:
    quien la ve no va a abrir la tabla a ver si cuadra. Si el numero se
    desviara del de la tabla -- por una columna renombrada, por una plantilla
    apuntando a otra vista -- no lo cazaria nadie.

    Se comprueba en los dos sentidos: que cada `{hueco}` sea una columna de
    SU vista, y que cada numero que acaba en la pagina este de verdad en esa
    tabla. Lo segundo no repite el codigo del modulo: no mira si eligio bien
    la fila, mira que el numero exista, que es lo que promete la portada."""
    def cifras(t):
        return set(re.findall(r"\d+(?:,\d+)?", t))

    gente = T.elegibles(conn)
    todos = T._cuantas_lleva(conn)
    hecho = T.calcular(conn)

    comprobar("hay titulares que enseniar",
              len(hecho["titulares"]) == len(T.TITULARES),
              "%d de %d" % (len(hecho["titulares"]), len(T.TITULARES)))

    inventados, sin_columna, crudos, de_la_nada, no_ganan = [], [], [], [], []
    for t in T.TITULARES:
        if t["vista"] not in V.POR_NOMBRE:
            inventados.append(t["vista"])
            continue
        cols, filas = V.consultar(conn, t["vista"])
        plantillas = " ".join(t.get(k, "")
                              for k in ("quien", "cifra", "detalle"))
        for hueco in re.findall(r"\{([a-z0-9_]+)\}", plantillas):
            if hueco not in cols:
                sin_columna.append("%s: {%s} no esta en %s"
                                   % (t["id"], hueco, t["vista"]))
        if t["ordenar"] not in cols:
            sin_columna.append("%s: ordena por %s, que no esta en %s"
                               % (t["id"], t["ordenar"], t["vista"]))
            continue

        salido = [x for x in hecho["titulares"] if x["id"] == t["id"]][0]
        if "falta" in salido:
            continue
        escrito = (salido["quien"] + " " + salido["cifra"] + " "
                   + salido["detalle"])
        if "{" in escrito or "}" in escrito:
            crudos.append("%s: %s" % (t["id"], escrito))

        # Todo numero que la pagina ensenia tiene que estar en la tabla. Los
        # que ya venian escritos en la plantilla («por un 7») se descuentan
        # tapando los huecos y mirando que numeros quedan sueltos.
        literal = cifras(re.sub(r"\{[a-z0-9_]+\}", "@", plantillas))
        en_la_tabla = set()
        for f in filas:
            en_la_tabla.update(T._num(v) for v in f if v is not None)
        for c in cifras(escrito) - literal - en_la_tabla:
            de_la_nada.append("%s: el %s no esta en %s"
                              % (t["id"], c, t["vista"]))

        # Y el que sale es el que mas tiene, de los que llegan al minimo.
        quienes = [c for c in ("quien", "a_quien") if c in cols]
        i = cols.index(t["ordenar"])
        cabe = [f[i] for f in filas if f[i] is not None
                and all(f[cols.index(c)] in gente for c in quienes)]
        if cabe and T._num(max(cabe)) not in cifras(escrito):
            no_ganan.append("%s: el mas alto es %s y el titular dice %s"
                            % (t["id"], T._num(max(cabe)), salido["cifra"]))

    comprobar("los titulares enlazan a vistas que existen", not inventados,
              str(inventados))
    comprobar("y cada hueco de la frase es una columna de SU vista",
              not sin_columna, "; ".join(sin_columna))
    comprobar("no se escapa ningun hueco sin rellenar", not crudos,
              "; ".join(crudos))
    comprobar("todo numero del titular esta en la tabla que enlaza",
              not de_la_nada, "; ".join(de_la_nada))
    comprobar("y el titular se lo lleva el que mas tiene", not no_ganan,
              "; ".join(no_ganan))

    # El minimo de partidas no es decoracion: sin el, el titular se lo lleva
    # el que jugo una vez y tuvo un buen dia. Nadie por debajo sale nombrado.
    cortos = [q for q, n in todos.items() if n < T.MINIMO]
    colados = [(q, x["id"]) for x in hecho["titulares"] if "quien" in x
               for q in cortos if q in x["quien"]]
    comprobar("nadie por debajo de %d partidas sale en un titular" % T.MINIMO,
              not colados, str(colados))

    # Y los RECORDS, que van por otro camino: leen la vista UNA VEZ POR
    # PARTIDA y se quedan con la mejor de todas. Lo que hay que comprobar es
    # lo mismo -- que el numero este en la tabla -- pero en la tabla FILTRADA
    # POR ESA PARTIDA, que es adonde lleva el enlace. Un record que apunte a
    # la partida equivocada manda a mirar una tabla donde su numero no esta.
    sin_partida, de_otra, no_es_record = [], [], []
    todas = T._las_partidas(conn)
    for r in T.RECORDS:
        salido = [x for x in hecho["records"] if x["id"] == r["id"]][0]
        if "falta" in salido:
            continue
        if "partida" not in salido or not salido.get("dia"):
            sin_partida.append(r["id"])
            continue
        cols, filas = V.consultar(conn, r["vista"], salido["partida"])
        i = cols.index(r["ordenar"])
        plantillas = " ".join(r.get(k, "") for k in ("quien", "cifra", "detalle"))
        literal = cifras(re.sub(r"\{[a-z0-9_]+\}", "@", plantillas))
        escrito = (salido["quien"] + " " + salido["cifra"] + " "
                   + salido["detalle"])
        aqui = set()
        for f in filas:
            aqui.update(T._num(v) for v in f if v is not None)
        for c in cifras(escrito) - literal - aqui:
            de_otra.append("%s: el %s no esta en %s de la partida %s"
                           % (r["id"], c, r["vista"], salido["partida"]))
        # Y que sea de verdad la mejor de TODAS las partidas, no de la suya.
        techo = None
        for numero, _dia in todas:
            c2, f2 = V.consultar(conn, r["vista"], numero)
            j = c2.index(r["ordenar"])
            for f in f2:
                if f[j] is not None and (techo is None or f[j] > techo):
                    techo = f[j]
        if techo is not None and T._num(techo) not in cifras(escrito):
            no_es_record.append("%s: el techo es %s y el record dice %s"
                                % (r["id"], T._num(techo), salido["cifra"]))

    comprobar("cada record dice de que partida es", not sin_partida,
              str(sin_partida))
    comprobar("y sus numeros estan en esa partida, que es adonde enlaza",
              not de_otra, "; ".join(de_otra))
    comprobar("y no hay ninguna partida con una marca mejor",
              not no_es_record, "; ".join(no_es_record))


def prueba_ninguna_columna_dice_dos_cosas(conn):
    """Una columna que sale en dos vistas tiene que estar declarada.

    El fallo que esto pilla no rompe nada y no lo canta nadie: dos vistas
    del mismo grupo con la misma columna queriendo decir cuentas distintas.
    Paso de verdad con `le_costo` -- «produccion bloqueada» en una y
    «produccion bloqueada + cartas robadas» en la otra, 14 contra 33 para la
    misma partida -- y lo encontro una persona mirando las dos tablas, que
    es justo lo que estas pruebas estan para que no haga falta.

    Se deniega por defecto. Repetir un nombre esta permitido y es normal
    (`madera` es madera en todas), pero hay que apuntarlo en `COMPARTIDAS`
    con el motivo. Lo que no puede pasar es que se repita sin que nadie lo
    haya mirado.

    Las comunes de PROYECTO.md no cuentan: ya estan declaradas alli, y esa
    lista la comprueba `prueba_todas_las_columnas_estan_explicadas`."""
    comunes = _columnas_declaradas()[0]
    donde = {}
    for v in V.VISTAS:
        cols, _f = V.consultar(conn, v["nombre"])
        for c in cols:
            donde.setdefault(c, []).append(v["nombre"])

    repetidas = {c: vs for c, vs in donde.items()
                 if len(vs) > 1 and c not in comunes}
    sin_declarar = sorted(c for c in repetidas if c not in V.COMPARTIDAS)
    comprobar("ninguna columna sale en dos vistas sin estar declarada",
              not sin_declarar,
              ", ".join("%s (%s)" % (c, "/".join(repetidas[c]))
                        for c in sin_declarar))

    # Y al reves, que la lista no se quede con nombres de antes: una entrada
    # que ya no se repite es una que dejo de vigilar algo sin avisar.
    sobran = sorted(c for c in V.COMPARTIDAS if c not in repetidas)
    comprobar("y la lista no arrastra columnas que ya no se repiten",
              not sobran, ", ".join(sobran))

def prueba_el_catalogo_esta_al_dia():
    """`VISTAS.md` tiene que ser lo que `db/catalogo.py` genera hoy.

    Es el fichero que se lee para saber que hay en la base, asi que una
    columna renombrada y no regenerada convierte la documentacion en una
    mentira -- y de las malas: la que parece completa. Como se genera, la
    comprobacion es exacta y no una aproximacion: se vuelve a generar en
    memoria y se compara caracter a caracter.

    Y se genera contra una base VACIA, asi que esta prueba pasa igual en un
    ordenador recien clonado y no cambia al jugar una partida.

    Si falla: `py db/catalogo.py`."""
    from db import catalogo
    from db import vistas as V

    nuevo, faltan = catalogo.texto()
    comprobar("el catalogo explica todas las columnas", not faltan,
              ", ".join(faltan[:5]))
    # Que salgan TODAS en el fichero. Arriba ya hay una prueba de que ninguna
    # vista se queda sin grupo; esta mira el RESULTADO, que es lo que se
    # publica, y cubre el caso de que una vista con grupo no llegue a pintarse.
    #
    # No es teorico: `amigos_ladron_a_quien_numero` nacio sin grupo el 2 de
    # septiembre de 2026 y desaparecio entera del fichero. Sin error: la
    # documentacion sale completa a la vista y le falta una tabla. El motivo
    # es que `grupo_de` devuelve "Sin colocar" para las huerfanas, y eso es un
    # texto VERDADERO, asi que el filtro que debia recogerlas nunca las veia.
    fuera = [v["nombre"] for v in V.VISTAS if v["nombre"] not in nuevo]
    comprobar("y todas salen en VISTAS.md", not fuera,
              "no aparecen: %s" % ", ".join(fuera))
    if not os.path.isfile(catalogo.DESTINO):
        return comprobar("VISTAS.md existe", False, catalogo.DESTINO)
    with open(catalogo.DESTINO, encoding="utf-8") as f:
        viejo = f.read()
    comprobar("y VISTAS.md es lo que se genera hoy", viejo == nuevo,
              "vuelve a lanzar: py db/catalogo.py")

    # Los enlaces del indice. Un ancla mal calculada no rompe nada y no se ve
    # hasta que alguien pincha, que es cuando ya esta publicado.
    import re
    anclas = {catalogo._ancla(t)
              for t in re.findall(r"^#+ (.+)$", viejo, re.M)}
    rotos = [d for d in re.findall(r"\]\(#([^)]+)\)", viejo)
             if d not in anclas]
    comprobar("y ningun enlace del indice apunta a la nada", not rotos,
              str(rotos[:5]))


def prueba_lo_que_se_publica_no_lleva_el_nombre_de_nadie(conn):
    """NINGUN fichero del repositorio puede llevar el apodo de quien juega.

    La de abajo mira `VISTAS.md`; esta mira TODO lo que sube. Hace falta
    porque los apodos no se colaban en los datos -- ahi no hay forma -- sino
    en los COMENTARIOS: cada fallo que se arregla se documenta con el caso
    medido, y el caso medido tiene el nombre de quien lo sufrio. El 5 de
    septiembre de 2026 habia 48 repartidos por siete ficheros, y ninguno era
    un descuido: eran ejemplos de verdad, escritos a conciencia.

    Son sus apodos de Catan Universe, no sus nombres, pero son personas y no
    han pedido salir en el repositorio de nadie.

    Los ejemplos de los comentarios se quedan con nombres falsos, y estan
    elegidos para que las explicaciones sigan valiendo: varias hablan de COMO
    ESTA ESCRITO el apodo -- que en minusculas empiece por «el», que lleve un
    guion que lo parte en dos palabras, que un prefijo corto lo encuentre --
    asi que los falsos conservan esa forma.

    QUE MIRA Y QUE NO. Los ficheros que `git` dice que estan en el
    repositorio, sean del ultimo commit o todavia sin anadir. Sin git no se
    puede saber cual es cual, y entonces se salta y lo dice: callarse seria
    dar por buena una comprobacion que no se ha hecho."""
    import subprocess
    try:
        salida = subprocess.run(
            ["git", "ls-files", "-co", "--exclude-standard"],
            cwd=RAIZ, capture_output=True, text=True, timeout=30)
    except Exception as e:
        return saltar("los nombres en lo que se publica (sin git: %s)" % e)
    if salida.returncode != 0:
        return saltar("los nombres en lo que se publica (esto no es un "
                      "repositorio git todavia)")

    # Los de tres letras o menos no se buscan: darian falsos positivos en
    # cualquier palabra. Los provisionales tampoco -- `jugador_4645eb8a` no
    # es el nombre de nadie, y ademas sale en los comentarios a proposito.
    # `is_bot = 0`: las IA del juego -- Jean, Louis, Siegfried... -- no son
    # personas y sus nombres salen a proposito en el esquema, en el mod y en
    # el catalogo del juego. Sin esta condicion la prueba las cazaba a ellas.
    apodos = [r[0] for r in conn.execute(
        "SELECT DISTINCT COALESCE(person_name, name) FROM players "
        " WHERE is_bot = 0")
        if r[0] and len(r[0]) > 3 and not r[0].startswith("jugador_")]
    if not apodos:
        return saltar("los nombres en lo que se publica (nadie tiene apodo)")

    dentro = []
    for rel in salida.stdout.split("\n"):
        rel = rel.strip()
        if not rel:
            continue
        camino = os.path.join(RAIZ, rel)
        if not os.path.isfile(camino):
            continue
        try:
            texto = io.open(camino, encoding="utf-8", errors="ignore").read()
        except Exception:
            continue
        bajo = texto.lower()
        for a in apodos:
            if a.lower() in bajo:
                dentro.append("%s (%s)" % (rel, a))
    comprobar("lo que se publica no lleva el apodo de nadie", not dentro,
              ", ".join(sorted(set(dentro))[:5]))


def prueba_el_catalogo_no_lleva_datos_de_nadie(conn):
    """En `VISTAS.md` no puede salir el nombre de ningun jugador.

    Este fichero se publica. Se genera contra una base vacia justamente para
    que no pueda llevar partidas dentro, pero eso es una intencion y esto es
    la comprobacion: se cogen los nombres que hay en la base de verdad y se
    buscan en el texto.

    Vale la pena aunque hoy sea imposible por construccion. El dia que a
    alguien le parezca buena idea meter una fila de ejemplo -- y lo parece,
    porque se entiende mejor -- esto lo para."""
    from db import catalogo
    nuevo, _faltan = catalogo.texto()
    bajo = nuevo.lower()
    dentro = sorted({r[0] for r in conn.execute(
        "SELECT DISTINCT COALESCE(person_name, name) FROM players")
        if r[0] and len(r[0]) > 3 and r[0].lower() in bajo})
    comprobar("VISTAS.md no lleva el nombre de ningun jugador", not dentro,
              str(dentro))

def prueba_la_partida_de_muestra_llena_las_vistas():
    """Ninguna vista puede salir vacia en los ejemplos de `VISTAS.md`.

    Una tabla de ejemplo con la cabecera y ni una fila explica menos que no
    poner ejemplo: parece que la vista no devuelve nada nunca. Y es facil que
    pase sin querer -- basta anadir una vista y no tocar la partida
    inventada, o cambiarle a esta un detalle del que dependia una vista sola.

    Tambien comprueba que los nombres inventados no son los de nadie de
    verdad: si un dia alguien se llama Ana, la prueba de que `VISTAS.md` no
    lleva datos de nadie empezaria a fallar sin que nada estuviera mal."""
    from db import muestra
    conn = muestra.construir()
    try:
        vacias = []
        for v in V.VISTAS:
            _cols, filas = V.consultar(conn, v["nombre"])
            if not filas:
                vacias.append(v["nombre"])
        comprobar("la partida de muestra llena las %d vistas" % len(V.VISTAS),
                  not vacias, ", ".join(vacias))
    finally:
        conn.close()

    de_verdad = {r[0] for r in sqlite3.connect(
        "file:%s?mode=ro" % BASE, uri=True).execute(
        "SELECT DISTINCT COALESCE(person_name, name) FROM players") if r[0]}
    chocan = sorted({n for n, _c, _s, _p, _pt, _cl, _me in muestra.JUGADORES}
                    & de_verdad)
    comprobar("y los nombres inventados no son los de nadie", not chocan,
              str(chocan))

def prueba_los_dos_temas_definen_los_mismos_colores():
    """El claro y el oscuro tienen que declarar EXACTAMENTE las mismas
    variables, y el boton tiene que llegarle tambien al usuario.

    Si el oscuro se deja una fuera no falla nada y no se ve un error: esa
    variable se queda con el valor del claro, o sea un color pensado para
    fondo blanco puesto sobre fondo negro. Texto gris oscuro sobre casi
    negro, por ejemplo. Se lee mal y nadie sabe por que.

    Es el mismo tipo de fallo que persigue el resto de este fichero: dos
    sitios que tienen que decir lo mismo y nadie comprueba que lo digan."""
    import panel
    import re
    claro = re.search(r':root\{([^}]*)\}', panel.PAGINA)
    oscuro = re.search(r':root\[data-tema="oscuro"\]\{([^}]*)\}', panel.PAGINA)
    if not claro or not oscuro:
        return comprobar("estan las dos paletas", False,
                         "claro:%s oscuro:%s" % (bool(claro), bool(oscuro)))
    nombres = lambda s: set(re.findall(r'(--[a-z]+)\s*:', s))
    a, b = nombres(claro.group(1)), nombres(oscuro.group(1))
    comprobar("los dos temas declaran los mismos %d colores" % len(a),
              a == b, "solo en claro %s, solo en oscuro %s"
                      % (sorted(a - b), sorted(b - a)))

    # Y que las use alguien: una variable declarada dos veces y usada cero
    # es peso muerto que igualmente hay que mantener a juego.
    sin_usar = sorted(c for c in a if "var(%s)" % c not in panel.PAGINA)
    comprobar("y todas se usan en algun sitio", not sin_usar, str(sin_usar))

    # El interruptor no lleva marca de `<!--dev-->`, asi que tiene que
    # sobrevivir al recorte. Si algun dia se envuelve sin querer, el usuario
    # se queda sin poder cambiarlo y nadie se entera: el panel de trabajo lo
    # sigue teniendo.
    recortada = panel._pagina_para(panel.PAGINA, con_desarrollo=False,
                                   con_vision=False)
    comprobar("y el interruptor de tema le llega tambien al usuario",
              'id="bTema"' in recortada
              and 'localStorage.getItem("tema")' in recortada)

def prueba_ningun_idioma_se_queda_a_medias():
    """Cada idioma tiene que cubrirlo TODO. Media traduccion no vale.

    Una pagina medio en ingles y medio en castellano es peor que una entera
    en castellano: el que la lee no sabe si le falta algo o es que ahi pone
    eso. Y se cuela sola, porque se anade un parrafo en el idioma de casa y
    nadie se acuerda de los demas.

    Se miran los CUATRO sitios de donde sale texto, que son cuatro fallos
    distintos y ninguno avisa solo:

      texto     lo que hay entre etiquetas de la pagina -- la ENTERA, con los
                bloques <!--dev--> dentro. Se dejaron fuera una vez, con el
                argumento de que no se publican, y el resultado fue media
                pagina traducida para quien desarrolla esto.
      atributos el gris de una caja de busqueda y el globo del raton. No son
                texto de la pagina y por eso se colaron.
      guion     las cadenas que escribe el JavaScript.
      frases    lo que manda el servidor: titulos de tabla, titulares,
                filtros y nombres de tarea.
      columnas  las cabeceras de las tablas.

    Y en los dos sentidos: falta una entrada es traduccion incompleta; sobra
    una es traduccion CADUCA, que es peor, porque parece hecha.
    """
    import re
    import panel
    import idiomas
    import db.vistas as V
    import db.titulares as T

    # --- lo que se ve en la pagina, la entera -----------------------------
    cuerpo = panel.PAGINA.split("</head>", 1)[-1]
    sin_guion = re.sub(r"<script.*?</script>", "", cuerpo, flags=re.S)
    trozos = []
    for crudo in re.split(r"<[^>]+>", sin_guion):
        limpio = " ".join(crudo.split())
        if len(limpio) > 2 and re.search(r"[a-zA-Z]", limpio):
            trozos.append(limpio)
    for etiqueta in re.findall(r"<[^>]+>", panel.PAGINA):
        for atributo in panel._ATRIBUTOS_QUE_SE_LEEN:
            for valor in re.findall(r'\b%s="([^"]+)"' % atributo, etiqueta):
                valor = valor.strip()
                if len(valor) > 2 and re.search(r"[a-zA-Z]", valor):
                    trozos.append(valor)
    trozos = list(dict.fromkeys(trozos))
    guiones = "\n".join(re.findall(r"<script[^>]*>(.*?)</script>",
                                   panel.PAGINA, re.S))

    # --- lo que manda el servidor ------------------------------------------
    frases = [g for g, _ in V.GRUPOS]
    for v in V.VISTAS:
        frases += [v["titulo"], v.get("que"), v.get("vacio")]
    frases += list(V.NOMBRE_DEL_AMBITO.values())
    frases += list(V.NOMBRE_DE_LA_MESA.values())
    frases += [n[0] if isinstance(n, tuple) else n
               for n in panel.TAREAS.values()]

    def plantillas(d):
        fuera = []
        for clave in ("titulo", "cifra", "detalle", "quien", "texto",
                      "si_cero", "si_nadie"):
            if isinstance(d.get(clave), str):
                fuera.append(d[clave])
        if isinstance(d.get("tambien"), dict):
            fuera += plantillas(d["tambien"])
        return fuera

    for uno in list(T.TITULARES) + list(T.RECORDS):
        frases += plantillas(uno)
    frases = [f for f in dict.fromkeys(frases) if f]

    columnas = set(C.COMUNES)
    for v in V.VISTAS:
        columnas |= set(C.POR_VISTA.get(v["nombre"]) or {})
    columnas = sorted(columnas)

    # Y las fichas del catalogo: que quiere decir cada columna y que es una
    # fila. No salen en el panel --las escribe `py db/catalogo.py`-- pero un
    # catalogo medio traducido es exactamente el mismo problema.
    filas = [v["nombre"] for v in V.VISTAS if v["nombre"] in C.FILA_ES]

    comprobar("hay %d trozos de pagina, %d frases y %d columnas que traducir"
              % (len(trozos), len(frases), len(columnas)),
              len(trozos) > 150 and len(frases) > 100 and len(columnas) > 100)

    for clave in sorted(idiomas.IDIOMAS):
        lengua = idiomas.IDIOMAS[clave]
        for que, tiene, hay in (
                ("los %d trozos de la pagina" % len(trozos),
                 lengua["texto"], trozos),
                ("las %d frases del servidor" % len(frases),
                 lengua["frases"], frases),
                ("las %d cabeceras de columna" % len(columnas),
                 lengua["columnas"], columnas),
                ("las %d columnas comunes del catalogo" % len(C.COMUNES),
                 lengua["comunes"], list(C.COMUNES)),
                ("el «que es una fila» de las %d tablas" % len(filas),
                 lengua["fila_es"], filas)):
            faltan = [x for x in hay if x not in tiene]
            comprobar("«%s» traduce %s" % (clave, que), not faltan,
                      "sin traducir: %s" % [x[:45] for x in faltan[:3]])
            caducas = [k for k in tiene if k not in hay]
            comprobar("y no le sobra ninguna", not caducas,
                      "ya no existen: %s" % [k[:45] for k in caducas[:3]])

        # `fila_es` no es una frase, son dos: que es una fila y para que
        # sirve mirarla. Con una sola el catalogo sale cojo y no lo dice.
        cojas = [k for k, v in lengua["fila_es"].items()
                 if not (isinstance(v, dict) and v.get("fila") and v.get("para"))]
        comprobar("y cada «que es una fila» trae sus dos frases", not cojas,
                  str(cojas[:3]))

        # Y las propias de cada vista, tabla por tabla: es donde estan
        # las tres cuartas partes del texto del catalogo.
        sin_ficha, de_mas = [], []
        for v in V.VISTAS:
            suyas = C.POR_VISTA.get(v["nombre"]) or {}
            tiene = lengua["por_vista"].get(v["nombre"]) or {}
            sin_ficha += ["%s.%s" % (v["nombre"], c)
                          for c in suyas if c not in tiene]
            de_mas += ["%s.%s" % (v["nombre"], c)
                       for c in tiene if c not in suyas]
        comprobar("«%s» explica las columnas propias de las 32 tablas" % clave,
                  not sin_ficha, "sin ficha: %s" % sin_ficha[:3])
        comprobar("y no explica ninguna que ya no exista", not de_mas,
                  "sobran: %s" % de_mas[:3])
        sobran_tablas = [t for t in lengua["por_vista"]
                         if t not in V.POR_NOMBRE]
        comprobar("y ninguna tabla suya ha desaparecido", not sobran_tablas,
                  str(sobran_tablas[:3]))

        huerfanas = [k for k in lengua["guion"] if k not in guiones]
        comprobar("y sus %d cadenas de JavaScript siguen existiendo"
                  % len(lengua["guion"]), not huerfanas,
                  "no aparecen: %s" % [k[:45] for k in huerfanas[:3]])

        # LAS LLAVES. Un titular es una plantilla: «{victorias} de
        # {partidas}». Si la traduccion se come un hueco o se inventa otro, en
        # la pantalla sale un `{victorias}` en crudo o falta el numero.
        malas = []
        for es, otro in lengua["frases"].items():
            if set(re.findall(r"\{(\w+)\}", es)) != set(
                    re.findall(r"\{(\w+)\}", otro)):
                malas.append(es)
        comprobar("y los huecos {} de las plantillas son los mismos",
                  not malas, str([m[:45] for m in malas[:3]]))

        # Traducir cambia el texto, nunca la FORMA. Si una entrada se colara
        # dentro de una etiqueta o de un <script>, el numero de etiquetas
        # cambiaria y esto lo canta.
        otra = panel._traducir(panel.PAGINA, clave)
        comprobar("y traducir a «%s» no cambia la forma de la pagina" % clave,
                  otra.count("<") == panel.PAGINA.count("<")
                  and otra.count("<script") == panel.PAGINA.count("<script"),
                  "etiquetas %d -> %d" % (panel.PAGINA.count("<"),
                                          otra.count("<")))
        comprobar("y la pagina en «%s» no es la misma que en castellano"
                  % clave, otra != panel.PAGINA)

    comprobar("y el menu de idiomas le llega al usuario",
              'id="selIdioma"' in panel._pagina_para(panel.PAGINA,
                                                    False, False))


def prueba_el_javascript_tampoco_se_queda_en_castellano():
    """Las cadenas que escribe el JavaScript, todas traducidas. Todas.

    La prueba de al lado mira el texto de la pagina y las frases que manda el
    servidor. No ve una tercera cosa: lo que el guion PINTA. Un
    `"guardar"` dentro de un `<script>` no es texto de la pagina, es codigo,
    y para el que recorre etiquetas no existe. Asi se quedaron 21 cadenas en
    castellano en la version inglesa hasta que se vieron en una captura, ya a
    punto de publicarla.

    Como se separa el texto del codigo, que es lo dificil:

      1. Las cadenas se leen recorriendo el guion de izquierda a derecha, no
         con un regex. `'<div class="x">hola '` lleva comillas dobles DENTRO
         de unas simples: cualquier alternancia empieza a contar por la de
         dentro y se lleva media linea por delante. Ese fallo es el que
         escondio las 21.
      2. Lo que despues de quitarle las etiquetas no tiene ni dos letras
         seguidas no es texto para nadie.
      3. Lo que encaja en `CODIGO` --un identificador, un selector, una ruta,
         una opcion, una declaracion de CSS-- tampoco.
      4. Y lo que sobrevive a eso y aun asi es codigo esta escrito en
         `PERDONADAS`, una por una. Es a proposito que sea una lista y no una
         regla: cuando aparezca una cadena nueva, esta prueba falla y alguien
         tiene que mirarla y decidir. Traducirla o apuntarla aqui. Lo que no
         puede es colarse sola.
    """
    import re
    import panel
    import idiomas

    # Codigo que parece texto. No se traduce ninguna: son selectores,
    # rutas, nombres de clase y trozos de etiqueta a medio abrir.
    PERDONADAS = {
        '" &rarr;</button></div>"',
        '"#botonesVista button"',
        '"#tablaVista th.orden"',
        '"&ambito="',
        '"&desde="',
        '"&mesa="',
        '"&partida="',
        '"(prefers-color-scheme:dark)"',
        '"/preguntar?q="',
        '"/registro?fuente="',
        '"/vista?nombre="',
        '";path=/;max-age=31536000"',
        '"application/json"',
        '"banda off"',
        '"banda ojo"',
        '"banda on"',
        '"button[data-vista]"',
        '"Catan Tracker"',
        '"var(--alerta)"',
        '"var(--borde)"',
        '"var(--tinta)"',
        '\' data-partida="\'',
        '\'" data-col="\'',
        '\'" value="\'',
        '\'<button data-vista="\'',
        '\'<button id="pAnt"\'',
        '\'<button id="pSig"\'',
        '\'<option value="\'',
        '\'<td class="\'',
        '\'<td><button data-i="\'',
        '\'<td><button data-id="\'',
        '\'<td><input type="text" maxlength="40" data-red="\'',
        '\'<th class="orden\'',
        '\'<tr class="\'',
    }

    CODIGO = re.compile(r"""^(?:
          [A-Za-z_][A-Za-z0-9_\-]*
        | [#.][A-Za-z][\w\-]*
        | /[a-z]+
        | --?[a-z\-]+
        | [a-z\-]+:[^;]*;?
        | &[a-z]+;
        | [\W\d]+
        | [A-Za-z_][\w\-]*=
        | (?:py|SELECT)\s.*
    )$""", re.X)

    def literales(js):
        """Las cadenas del guion, leyendo de izquierda a derecha."""
        fuera, i, n, antes = [], 0, len(js), ""
        while i < n:
            c = js[i]
            if c == "/" and i + 1 < n and js[i + 1] == "/":
                i = js.find("\n", i)
                if i < 0:
                    break
            elif c == "/" and i + 1 < n and js[i + 1] == "*":
                i = js.find("*/", i) + 2
            elif c == "/" and antes in "(,=:[!&|?{};\n":
                j = i + 1                       # una expresion regular
                while j < n and js[j] not in "/\n":
                    j += 2 if js[j] == "\\" else 1
                i = j + 1
            elif c in "\"'`":
                j = i + 1
                while j < n and js[j] != c:
                    if js[j] == "\\":
                        j += 1
                    elif js[j] == "\n" and c != "`":
                        break
                    j += 1
                if j < n and js[j] == c:
                    fuera.append(js[i:j + 1])
                i = j + 1
            else:
                if not c.isspace():
                    antes = c
                i += 1
        return fuera

    js = "\n".join(re.findall(r"<script[^>]*>(.*?)</script>",
                              panel.PAGINA, re.S))
    LETRAS = re.compile(r"[A-Za-z\xc1\xc9\xcd\xd3\xda\xe1\xe9\xed"
                        r"\xf3\xfa\xd1\xf1]{2,}")

    de_texto, codigo = [], []
    for lit in dict.fromkeys(literales(js)):
        d = lit[1:-1]
        if not LETRAS.search(re.sub(r"<[^>]*>", " ", d)):
            continue
        if CODIGO.match(d.strip()) or lit in PERDONADAS:
            codigo.append(lit)
        else:
            de_texto.append(lit)

    comprobar("el guion de la pagina escribe %d cadenas de texto"
              % len(de_texto), len(de_texto) > 60)

    for clave in sorted(idiomas.IDIOMAS):
        guion = idiomas.IDIOMAS[clave]["guion"]
        faltan = [l for l in de_texto if l not in guion]
        comprobar("y «%s» las traduce todas" % clave, not faltan,
                  "en castellano: %s" % [l[:50] for l in faltan[:3]])
        # Y al reves: una cadena traducida que ya no existe en el guion es
        # una traduccion caduca, que es peor porque parece hecha.
        huerfanas = [k for k in guion if k not in js]
        comprobar("y no le sobra ninguna", not huerfanas,
                  "ya no aparecen: %s" % [k[:50] for k in huerfanas[:3]])

    # Perdonar es una decision, no un descuido: si una de la lista deja de
    # existir, se quita de la lista.
    fantasmas = [l for l in PERDONADAS if l not in js]
    comprobar("y las %d cadenas perdonadas por ser codigo siguen ahi"
              % len(PERDONADAS), not fantasmas,
              "ya no existen: %s" % [l[:50] for l in fantasmas[:3]])

def prueba_ponerselo_a_uno_mismo_cuadra(conn):
    """Las dos vistas del ladron tienen que cuadrar quitando lo de uno mismo.

    «El ladron, uno a uno» cuenta ponerselo a uno mismo -- una fila con la
    misma persona en las dos columnas -- y «El ladron» NO lo cuenta en
    `se_lo_pusieron`, porque ahi la pregunta es cuantas veces te lo pusieron
    y esa no te la pusieron. Las dos decisiones son buenas y juntas son una
    trampa: quien sume la columna de una y la compare con la otra ve una
    diferencia sin explicacion.

    Asi que la relacion se escribe aqui y se comprueba: sumando por victima y
    dejando fuera la fila de uno mismo, tienen que dar exactamente lo mismo.
    Si algun dia se cambia una de las dos, esto lo dice.

    Hasta el 2 de septiembre de 2026 `se_lo_puso` tambien excluia lo de uno
    mismo, y la vista se contradecia a si misma: `le_bloqueo` sale de
    `robber_blocks` y nunca excluyo nada, asi que la fila aparecia igual con
    un 0 en la primera columna."""
    cp, fp = V.consultar(conn, "amigos_ladron_a_quien")
    ip = {n: k for k, n in enumerate(cp)}
    cl, fl = V.consultar(conn, "amigos_ladron")
    il = {n: k for k, n in enumerate(cl)}

    de_otros = {}
    a_si_mismo = 0
    for f in fp:
        quien, victima = f[ip["quien"]], f[ip["a_quien"]]
        if quien == victima:
            a_si_mismo += f[ip["se_lo_puso"]]
            continue
        de_otros[victima] = de_otros.get(victima, 0) + f[ip["se_lo_puso"]]

    mal = []
    for f in fl:
        q = f[il["quien"]]
        if de_otros.get(q, 0) != f[il["se_lo_pusieron"]]:
            mal.append("%s: parejas %d vs ladron %d"
                       % (q, de_otros.get(q, 0), f[il["se_lo_pusieron"]]))
    comprobar("las puestas por parejas cuadran con las de cada uno",
              not mal, "; ".join(mal))

    # Y que lo de uno mismo siga saliendo por algun lado. Es raro -- dos de
    # casi doscientos movimientos -- y por eso es justo lo que se cae sin que
    # nadie lo note.
    cd, fd = V.consultar(conn, "amigos_ladron_donde")
    idd = {n: k for k, n in enumerate(cd)}
    en_donde = sum(f[idd["a_si_mismo"]] for f in fd)
    comprobar("y ponerselo a uno mismo sale igual en las dos vistas",
              en_donde == a_si_mismo,
              "«donde» %d vs «uno a uno» %d" % (en_donde, a_si_mismo))

    # Y la tercera vista con esa columna: «A quien se lo ponen mas», que es
    # «El ladron» en proporcion. Ahi `se_lo_pusieron` es el numerador de todo
    # lo demas, asi que tiene que ser el MISMO numero: si una tabla dijera 109
    # y la otra 110, el porcentaje de al lado no se podria comprobar contra
    # nada. Las dos consultas estan escritas por separado -- una correlada y
    # la otra en un CTE -- asi que esto no es una tautologia.
    cpr, fpr = V.consultar(conn, "amigos_ladron_proporcion")
    ipr = {n: k for k, n in enumerate(cpr)}
    suyo = {f[ipr["quien"]]: f[ipr["se_lo_pusieron"]] for f in fpr}
    distintos = [(f[il["quien"]], f[il["se_lo_pusieron"]],
                  suyo.get(f[il["quien"]]))
                 for f in fl
                 if f[il["se_lo_pusieron"]] != suyo.get(f[il["quien"]])]
    comprobar("`se_lo_pusieron` dice lo mismo en «El ladron» y en la de "
              "proporcion", not distintos, str(distintos[:3]))

    # LO QUE HACE QUE EL 100 SEA EL 100. `le_tocaban` reparte cada movimiento
    # entre los jugadores, asi que sumando la columna entera tiene que salir
    # el total de ladrones que se pusieron de verdad. Si no cuadra, el punto
    # neutro no esta en 100 y la columna `se_ceban` no significa lo que dice.
    #
    # Esto no es una comprobacion de adorno: la primera version de la vista
    # comparaba contra un ladron CIEGO y esta suma daba muy por debajo del
    # total -- por eso salia TODO EL MUNDO por encima de lo normal, que como
    # grupo es imposible. Con la referencia buena las dos sumas coinciden y
    # hay gente por encima y gente por debajo.
    puestos = sum(f[ipr["se_lo_pusieron"]] for f in fpr)
    tocaban = sum(f[ipr["le_tocaban"]] for f in fpr)
    comprobar("lo que «tocaba» suma lo mismo que lo que paso, o el 100 no "
              "es el 100", abs(puestos - tocaban) <= 1.0,
              "puestos %s, tocaban %s" % (puestos, tocaban))
    comprobar("y hay gente por encima y por debajo de 100",
              any((f[ipr["se_ceban"]] or 0) > 100 for f in fpr)
              and any((f[ipr["se_ceban"]] or 0) < 100 for f in fpr),
              "todos al mismo lado: la referencia esta mal puesta")

# La nota mas baja que se acepta en el examen de la caja de preguntas. Es un
# TRINQUETE, no un objetivo: sube cuando la caja mejora y no baja nunca.
#
# Por que un minimo y no «que pasen todas»: exigir el 100% obliga a escribir
# el examen a la medida de lo que ya funciona, que es exactamente el vicio
# que este examen viene a quitar. Las preguntas que falla se quedan dentro y
# a la vista.
# Bajado a mano de 40 a 38 el 4 de septiembre de 2026, y hay que decir por
# que: se quito la vista «Quien gana en los intercambios», que era la unica
# que sumaba los tratos de una persona contra todos. Con ella la caja
# acertaba «quien gana mas en los intercambios» y «quien sale ganando cartas
# de todos los tratos»; sin ella no hay ninguna vista que conteste eso -- la
# unica que suma los dos sentidos va por PAREJA, y una fila de pareja no
# contesta un «quien» a secas. Las dos preguntas se quedan en el examen
# fallando, que es lo que toca.
#
# Bajar este numero solo vale cuando se ha quitado algo a proposito. Si baja
# sin que nadie haya quitado nada, es una regresion.
NOTA_MINIMA = 40


def prueba_un_clon_recien_bajado_puede_importar():
    """Lo que se publica tiene que bastarse solo.

    El .gitignore no sube el proyecto entero: la mitad de la vision se queda
    fuera (pesa, arrastra OpenCV y todavia no esta fina) pero TRES ficheros
    de `red/` y `vision/` si suben, porque `mod_verdad/importar.py` los
    necesita para nombrar los sitios del tablero:

        vision/board_graph.py   la geometria del hexagono
        red/sitios.py           nombra los sitios
        red/reglas.py           las reglas que los validan

    El corte esta escrito en el .gitignore y NO SE VE al programar: aqui todo
    esta en disco, asi que un import de mas funciona igual y no se nota hasta
    que alguien clona. Paso el 2 de septiembre de 2026: `red/reglas.py`
    empezo a importar de `red/dataset.py` -- que no se publica y arrastra
    OpenCV -- y un clon recien bajado se habria quedado sin poder importar
    ni una partida, con un ImportError y ninguna pista de por que.

    Se comprueba de verdad y no leyendo el codigo: en un Python aparte, se
    hace desaparecer todo lo que no se publica y se importa el importador.
    Si tira de algo que no esta, revienta aqui."""
    import subprocess
    import sys

    # El guion que corre en el Python de al lado. `PERMITIDOS` son los de
    # `red/` y `vision/` que SI van al repositorio, tal como los deja el
    # .gitignore; todo lo demas de esas dos carpetas se hace desaparecer.
    GUION = r"""
import sys
PERMITIDOS = {'red', 'red.sitios', 'red.reglas',
              'vision', 'vision.board_graph'}

class SinPublicar:
    # hace como que no existe lo que no se sube. Es `find_spec` y no el
    # `find_module` de siempre: ese lo quitaron en Python 3.12, asi que un
    # bloqueador escrito con el no bloquea nada y la prueba pasa siempre.
    def find_spec(self, nombre, ruta=None, destino=None):
        raiz = nombre.split('.')[0]
        if raiz in ('red', 'vision') and nombre not in PERMITIDOS:
            raise ImportError(nombre + ' no se publica (ver .gitignore)')
        return None

sys.meta_path.insert(0, SinPublicar())
sys.path.insert(0, sys.argv[1])

import sqlite3

# TODO lo que se publica tiene que poder importarse, no solo lo que usa el
# importador. `red.reglas` sube y `mod_verdad/importar.py` no lo toca, asi
# que probando solo el importador un `red.reglas` roto pasaba de largo.
import red.sitios
import red.reglas
import vision.board_graph
import db.vistas as V
from mod_verdad.importar import crear_tablas

# y que ademas SIRVA: crear el esquema y las vistas de cero
conn = sqlite3.connect(':memory:')
crear_tablas(conn)
V.crear(conn)
cuantas = conn.execute(
    "SELECT COUNT(*) FROM sqlite_master WHERE type='view'").fetchone()[0]

# y las reglas del Catan, que son lo que mas facil se queda sin sus piezas
t = red.reglas.topo(19)
assert len(t['aristas_de_vertice']) == 54
print('vistas:%d' % cuantas)
"""

    r = subprocess.run([sys.executable, "-c", GUION, RAIZ],
                       capture_output=True, text=True, cwd=RAIZ)
    comprobar("lo que se publica se basta solo para importar una partida",
              r.returncode == 0 and "vistas:" in r.stdout,
              "un clon no puede importar: %s"
              % (r.stderr.strip().splitlines() or ["sin error"])[-1])


def prueba_la_caja_de_preguntas_no_empeora():
    """La caja tiene que acertar al menos `NOTA_MINIMA` de las del examen.

    Hasta el 2 de septiembre de 2026 esto se arreglaba a golpe de anecdota:
    alguien ensenaba una pregunta mal contestada, se anadia una regla, y a
    otra cosa. Eso mejora esa pregunta y no dice nada del resto -- ni
    siquiera si la regla nueva ha roto tres que iban bien.

    Con el examen, cualquier cambio en el emparejador se mide contra las 60 a
    la vez. Que suba una y bajen dos deja de pasar desapercibido.

    Si sube la nota, sube tambien `NOTA_MINIMA`: es lo que convierte una
    mejora en algo que no se puede deshacer sin querer."""
    from db import examen
    aciertos, total, fallos, saltadas = examen.examinar()
    if not total:
        return saltar("el examen de preguntas (nadie tiene apodo)")
    comprobar("la caja de preguntas acierta %d de %d (%.0f%%)"
              % (aciertos, total, 100.0 * aciertos / total),
              aciertos >= NOTA_MINIMA,
              "ha bajado de %d; fallan: %s"
              % (NOTA_MINIMA, ", ".join(f[0] for f in fallos[:3])))
    # Y que el trinquete no se quede atras: con la nota muy por encima del
    # minimo, el minimo ya no protege nada.
    comprobar("y el minimo del examen esta al dia",
              aciertos - NOTA_MINIMA <= 3,
              "acierta %d y el minimo sigue en %d: subelo en db/pruebas.py"
              % (aciertos, NOTA_MINIMA))



def prueba_la_caja_de_preguntas_entiende_los_otros_idiomas():
    """La caja tiene que acertar en cada idioma casi tanto como en castellano.

    El liston NO es acertarlo todo. La caja falla 28 de 68 en su propio
    idioma, y eso no lo arregla ningun diccionario: es lo que hay cuando se
    empareja por palabras y no se entiende la frase. Lo que si se puede
    exigir es que no falle MAS por estar en otro idioma, que es justo lo que
    mide esto.

    Por que existe. La caja empareja la pregunta contra los nombres, titulos
    y columnas de las vistas, que estan escritos en castellano. Traducir la
    pagina no la toca: un ingles leia «ask me something» y no le contestaba
    nada. Peor todavia, el panel le sugeria ejemplos concretos --«how many
    knights has X had»-- y ninguno funcionaba, que parece una caja rota.

    Y por que un diccionario y no una traduccion. No hace falta entender la
    pregunta: hace falta que las palabras lleguen en castellano. «who wins
    most» se reescribe como «quien victoria mas», que no se lee bien y
    empareja igual de bien.

    Las preguntas del examen de cada idioma NO son la traduccion literal de
    las castellanas: son como las escribiria alguien en su idioma. Con una
    traduccion literal se mediria si el diccionario deshace mi propia
    traduccion, que es una prueba que se aprueba sola.
    """
    from db import examen
    import idiomas

    en_castellano, total, _f, _s = examen.examinar()
    if not total:
        return saltar("el examen de preguntas en otros idiomas")

    # Cuanto se le deja bajar. Tres de 68 es margen para un giro que en un
    # idioma no existe, no para un diccionario a medias.
    MARGEN = 3

    for idioma, corpus in examen.LOS_IDIOMAS:
        aciertos, cuantas, fallos, _ = examen.examinar_idioma(idioma, corpus)
        comprobar("la caja en «%s» acierta %d de %d, y en castellano %d"
                  % (idioma, aciertos, cuantas, en_castellano),
                  aciertos >= en_castellano - MARGEN,
                  "se queda %d por debajo; fallan: %s"
                  % (en_castellano - aciertos,
                     ", ".join(f[0][:40] for f in fallos[:2])))

    # Y que el examen de cada idioma pregunte lo mismo que el castellano: si
    # alguien quita una pregunta dificil de un idioma, la nota sube sola y no
    # significa nada.
    esperadas = [v for _q, v in examen.PREGUNTAS]
    for idioma, corpus in examen.LOS_IDIOMAS:
        comprobar("y el examen de «%s» tiene las mismas %d preguntas"
                  % (idioma, len(esperadas)),
                  [v for _q, v in corpus] == esperadas,
                  "no coinciden las vistas esperadas")

    # Un diccionario vacio pasaria las dos de arriba si el examen estuviera
    # vacio. Que cada idioma traiga palabras de verdad.
    for clave in sorted(idiomas.IDIOMAS):
        lengua = idiomas.IDIOMAS[clave]
        # `giros` es (patron, diccionario): se aplican de una pasada, asi
        # que lo que se cuenta es el diccionario.
        _patron, giros = lengua["giros"]
        comprobar("y «%s» trae %d palabras y %d giros para la caja"
                  % (clave, len(lengua["preguntas"]), len(giros)),
                  len(lengua["preguntas"]) > 150 and len(giros) > 10)


def prueba_la_caja_contesta_en_el_idioma_del_panel():
    """Con lo que contesta la caja, traducido y con los huecos cuadrados.

    Entender la pregunta es media caja. La otra media es la frase con la que
    contesta, y esa se arma con plantillas: «El que %s %s: %s, con %s.» Si se
    traduce la pagina y no las plantillas, un ingles pregunta en ingles y le
    contesta en castellano, que es lo mismo que no haberla traducido.

    LOS HUECOS SON DE `%` Y VAN POR ORDEN, no por nombre como en `FRASES`.
    Eso los hace mas fragiles: una traduccion que se coma un `%s` no se ve
    rara, revienta al pintarla; y una que cambie dos de orden dice otra cosa
    con toda naturalidad -- «7 de 10» por «10 de 7». Asi que aqui se compara
    la secuencia entera, no cuantos hay.

    Las frases se sacan del ARBOL del codigo y no de una lista escrita a
    mano: se leen las llamadas a `_di(...)`, que es por donde pasan todas. Una
    lista seria un segundo sitio que actualizar, y el dia que alguien anadiera
    una frase nueva estaria sin traducir y la prueba diria que todo va bien.
    """
    import ast
    import io
    import re
    import idiomas

    fuente = io.open("panel.py", encoding="utf-8").read()
    piden = set()
    for n in ast.walk(ast.parse(fuente)):
        if (isinstance(n, ast.Call) and isinstance(n.func, ast.Name)
                and n.func.id == "_di" and n.args
                and isinstance(n.args[0], ast.Constant)
                and isinstance(n.args[0].value, str)):
            piden.add(n.args[0].value)
    piden = {p for p in piden if p.strip()}

    comprobar("la caja contesta con %d frases distintas" % len(piden),
              len(piden) > 30)

    for clave in sorted(idiomas.IDIOMAS):
        dice = idiomas.IDIOMAS[clave]["respuestas"]
        faltan = sorted(piden - set(dice))
        comprobar("y «%s» las traduce todas" % clave, not faltan,
                  "en castellano: %s" % [f[:45] for f in faltan[:3]])
        # Y al reves: una traducida que ya no se usa es una traduccion
        # caduca, que es peor porque parece hecha.
        sobran = sorted(set(dice) - piden)
        comprobar("y no le sobra ninguna", not sobran,
                  "ya no se usan: %s" % [f[:45] for f in sobran[:3]])

        # LOS HUECOS, en el mismo orden.
        malas = [k for k in dice
                 if re.findall(r"%[sdfr%]", k) != re.findall(r"%[sdfr%]",
                                                             dice[k])]
        comprobar("y los huecos %s van en el mismo orden", not malas,
                  "no cuadran: %s" % [m[:45] for m in malas[:3]])

    # Y que de verdad conteste en el idioma, no solo que el diccionario este
    # lleno: se le pregunta y se mira la frase.
    import panel
    for clave in sorted(idiomas.IDIOMAS):
        de_ejemplo = {"en": "who has had the most luck",
                      "fr": "qui a eu le plus de chance"}.get(clave)
        if not de_ejemplo:
            continue
        r = panel.preguntar(de_ejemplo, "amigos", clave)
        dicho = r.get("respuesta") or r.get("error") or ""
        castellano = idiomas.IDIOMAS[clave]["respuestas"]
        # Ninguna plantilla castellana puede asomar en la frase final.
        asoman = [k for k in castellano
                  if len(k) > 12 and "%" not in k and k in dicho]
        comprobar("y preguntando en «%s» contesta en «%s»" % (clave, clave),
                  dicho and not asoman,
                  "asoma el castellano: %s" % [a[:40] for a in asoman[:2]])


def prueba_el_instalador_y_el_importador_hablan_el_idioma_del_panel():
    """Lo que escriben los dos scripts que se ven desde el panel.

    No son la pagina ni el servidor: son procesos aparte que el panel lanza,
    y su salida se ve tal cual en el registro de abajo. Traducir la pagina no
    los toca, y por eso se quedaron fuera la primera vez.

    Los dos que importan son estos y no los demas. El INSTALADOR es el paso
    0, lo primero que hace alguien que acaba de clonar esto, y ahi es donde
    lee por que no encuentra Catan, por que no ha compilado el plugin y el
    aviso de que el mod va contra las condiciones de uso. El IMPORTADOR es el
    paso 2 y sale cada vez que se guardan partidas. El informe y la bateria
    de pruebas se quedan en castellano a proposito: uno es opcional y la otra
    son 15 KB de etiquetas de desarrollo.

    COMO LLEGA EL IDIOMA. No por un argumento: por la variable de entorno
    `CATAN_IDIOMA`, que pone el panel al lanzar la tarea. Estos scripts se
    llaman desde muchos sitios --el panel, la consola, otro script-- y un
    `--idioma` habria que anadirlo a cada llamada.

    Y como en las respuestas de la caja, se envuelve la PLANTILLA y no la
    frase montada: para cuando esta montada lleva dentro rutas, nombres y
    numeros, y no se encontraria en el diccionario.
    """
    import ast
    import io
    import re
    import idiomas

    FICHEROS = ("mod_verdad/instalar.py", "mod_verdad/importar.py")
    piden = set()
    for fichero in FICHEROS:
        fuente = io.open(fichero, encoding="utf-8").read()
        for n in ast.walk(ast.parse(fuente)):
            if (isinstance(n, ast.Call) and isinstance(n.func, ast.Name)
                    and n.func.id == "_t" and n.args
                    and isinstance(n.args[0], ast.Constant)
                    and isinstance(n.args[0].value, str)):
                piden.add(n.args[0].value)

    comprobar("el instalador y el importador escriben %d lineas distintas"
              % len(piden), len(piden) > 70)

    # Los huecos de `%`, con su ancho y su relleno: `%-28s` tiene que seguir
    # siendo `%-28s` o la tabla de `--quien` se desalinea.
    HUECO = re.compile(r"%[-#0 +]*\d*(?:\.\d+)?[sdifr%]")

    for clave in sorted(idiomas.IDIOMAS):
        dice = idiomas.IDIOMAS[clave]["consola"]
        faltan = sorted(piden - set(dice))
        comprobar("y «%s» las traduce todas" % clave, not faltan,
                  "en castellano: %s" % [f[:45] for f in faltan[:3]])
        sobran = sorted(set(dice) - piden)
        comprobar("y no le sobra ninguna", not sobran,
                  "ya no se escriben: %s" % [f[:45] for f in sobran[:3]])
        malas = [k for k in dice
                 if HUECO.findall(k) != HUECO.findall(dice[k])]
        comprobar("y los huecos %s van en el mismo orden y con el mismo ancho",
                  not malas, "no cuadran: %s" % [m[:45] for m in malas[:3]])

    # Y que el panel se lo diga de verdad. Sin esto, los diccionarios podrian
    # estar llenos y los scripts seguir escribiendo en castellano.
    import panel
    entorno = panel._entorno_hijo("fr")
    comprobar("y el panel les pasa el idioma en CATAN_IDIOMA",
              entorno.get("CATAN_IDIOMA") == "fr")
    comprobar("y en castellano no les pasa nada",
              "CATAN_IDIOMA" not in panel._entorno_hijo(None))

def prueba_la_caja_distingue_el_mas_del_menos():
    """Pedir «el que mas» y que conteste «el que menos» es un fallo entero,
    y la nota de arriba no lo ve.

    Paso de verdad: a «quien ha salido MAS veces primero» contestaba «el que
    menos primero: ANAKIN, con 0», con la vista y la columna CORRECTAS. La
    palabra «primero» estaba en la lista de pistas de «menos» -- puesta ahi
    por «quien llega primero a su primera ciudad», donde antes es turno mas
    bajo -- y tapaba al «mas» de al lado.

    Se arreglo, y el examen de vistas no se movio: 36 de 60 antes y despues.
    Por eso esto se mide aparte. Se exige el pleno y no un minimo: son ocho
    preguntas dichas hacia los dos lados, y fallar una es no haber entendido
    la pregunta."""
    from db import examen
    aciertos, total, fallos = examen.examinar_el_lado()
    comprobar("la caja distingue el mas del menos (%d de %d)"
              % (aciertos, total),
              aciertos == total,
              "no lo distingue en: %s"
              % ", ".join("«%s»" % f[0] for f in fallos[:3]))


def prueba_avisa_si_las_vistas_de_la_base_son_viejas():
    """El panel tiene que darse cuenta de que la base lleva vistas de antes.

    LAS VISTAS VIVEN DENTRO DEL .db. `db/vistas.py` genera los CREATE VIEW y
    el resultado se queda guardado en la base de quien lo use, asi que al
    bajarse una version nueva del proyecto las vistas siguen siendo las
    viejas. Y no falla: si la columna ya existia antes, se ven numeros de la
    version anterior con el codigo nuevo delante y nada lo dice.

    Es el fallo tipico de una actualizacion y no lo cubria nada. Desde el 2
    de septiembre de 2026 el importador las rehace al terminar, y el panel
    avisa mientras tanto.

    Se comprueba sobre una base de mentira, no sobre la de verdad."""
    import panel
    import sqlite3
    import tempfile
    import shutil
    from mod_verdad.importar import crear_tablas

    carpeta = tempfile.mkdtemp(prefix="catan_vistas_")
    try:
        falsa = os.path.join(carpeta, "prueba.db")
        conn = sqlite3.connect(falsa)
        crear_tablas(conn)
        V.crear(conn)
        conn.close()

        antes = panel.BASE_DATOS
        try:
            panel.BASE_DATOS = falsa
            comprobar("con las vistas al dia no avisa de nada",
                      panel.vistas_viejas() == [])

            # Se ensucia UNA vista, como haria una version nueva del codigo.
            conn = sqlite3.connect(falsa)
            conn.execute("DROP VIEW amigos_marcador")
            conn.execute("CREATE VIEW amigos_marcador AS SELECT 1 AS quien")
            conn.commit()
            conn.close()
            comprobar("y con una vieja la nombra",
                      panel.vistas_viejas() == ["amigos_marcador"],
                      str(panel.vistas_viejas()))

            # Y que el importador las deje bien: es lo que hace que el aviso
            # se apague solo en cuanto se juega una partida.
            conn = sqlite3.connect(falsa)
            V.crear(conn)
            conn.close()
            comprobar("y rehacerlas lo apaga", panel.vistas_viejas() == [])
        finally:
            panel.BASE_DATOS = antes

        # La otra mitad: que el importador REHAGA las vistas al acabar. Se
        # mira en el codigo y no ejecutandolo, que necesitaria grabaciones.
        import ast
        import inspect
        from mod_verdad import importar as _imp
        arbol = ast.parse(inspect.getsource(_imp.main))
        rehace = any(isinstance(n, ast.Attribute) and n.attr == "crear"
                     for n in ast.walk(arbol))
        comprobar("y el importador las rehace al terminar", rehace)
    finally:
        shutil.rmtree(carpeta, ignore_errors=True)

def main():
    if not os.path.isfile(BASE):
        print("No hay base de datos todavia, asi que no hay nada que probar.\n"
              "Enciende el mod, juega una partida y luego:\n"
              "    py mod_verdad/importar.py\n"
              "Las pruebas necesitan datos porque comprueban CUENTAS,\n"
              "no funciones sueltas.")
        return 0
    conn = sqlite3.connect(BASE)
    try:
        prueba_las_vistas_se_crean(conn)
        prueba_cada_vista_tiene_su_grupo()
        prueba_ninguna_columna_dice_dos_cosas(conn)
        prueba_los_titulares_salen_de_las_tablas(conn)
        prueba_la_partida_de_muestra_llena_las_vistas()
        prueba_el_catalogo_esta_al_dia()
        prueba_avisa_si_las_vistas_de_la_base_son_viejas()
        prueba_un_clon_recien_bajado_puede_importar()
        prueba_la_caja_de_preguntas_no_empeora()
        prueba_la_caja_de_preguntas_entiende_los_otros_idiomas()
        prueba_la_caja_contesta_en_el_idioma_del_panel()
        prueba_el_instalador_y_el_importador_hablan_el_idioma_del_panel()
        prueba_la_caja_distingue_el_mas_del_menos()
        prueba_ponerselo_a_uno_mismo_cuadra(conn)
        prueba_los_dos_temas_definen_los_mismos_colores()
        prueba_ningun_idioma_se_queda_a_medias()
        prueba_el_javascript_tampoco_se_queda_en_castellano()
        prueba_lo_que_se_publica_no_lleva_el_nombre_de_nadie(conn)
        prueba_el_catalogo_no_lleva_datos_de_nadie(conn)
        partidas = [r[0] for r in conn.execute(
            "SELECT game_id FROM games ORDER BY game_id")]
        if not partidas:
            print("La base está vacía. Nada más que probar.")
            return 0
        amigas = [r[0] for r in conn.execute(
            "SELECT game_id FROM partidas WHERE con_amigos=1 ORDER BY game_id")]
        con_ia = [g for g in partidas if g not in amigas]

        prueba_todas_contestan(conn, partidas)
        prueba_el_filtro_de_partida_filtra_de_verdad(conn, partidas)
        prueba_el_global_es_la_suma(conn, amigas)
        prueba_las_tiradas_cuadran(conn, amigas)
        prueba_una_maquina_recien_clonada_arranca()
        prueba_la_base_esta_entera(conn)
        prueba_todas_las_columnas_estan_explicadas(conn)
        prueba_la_suerte_cuadra(conn, amigas)
        prueba_los_puntos_cuadran(conn)
        prueba_las_dos_cuentas_de_lo_tapado_coinciden(conn)
        prueba_las_cartas_cuadran(conn)
        prueba_los_robos_cuadran(conn)
        prueba_el_ladron_uno_a_uno_suma_el_total(conn)
        prueba_una_partida_de_seis_cabe(conn)
        prueba_un_ladron_ilegible_no_pasa_callado(conn)
        prueba_lo_que_no_entiende_no_se_pierde(conn)
        prueba_las_variantes_de_mesa_grande_no_se_pierden(conn)
        prueba_el_mazo_es_el_de_la_mesa(conn)
        prueba_el_catalogo_contempla_el_juego_entero(conn)
        prueba_quitar_una_partida_no_deja_restos(conn)
        prueba_la_produccion_se_deduce_del_tablero(conn)
        prueba_el_ano_productivo_no_se_cuenta_como_produccion(conn)
        prueba_la_produccion_cuadra(conn)
        prueba_por_que_se_movio_el_ladron(conn, amigas)
        prueba_el_dano_del_ladron_se_desglosa(conn, amigas)
        prueba_la_produccion_es_la_de_la_tabla(conn, amigas)
        prueba_los_comercios_estan_todos(conn, amigas)
        prueba_los_materiales_son_los_comerciados(conn, amigas)
        prueba_el_saldo_cuadra_por_los_dos_lados(conn, amigas)
        prueba_los_tratos_estan_uno_a_uno(conn, amigas)
        prueba_estan_los_once_numeros(conn, amigas)
        prueba_los_puertos_se_deducen_bien(conn, amigas)
        prueba_los_puertos_deducidos_estan_en_el_tablero(conn)
        prueba_un_puerto_lo_pillan_dos_como_mucho(conn)
        prueba_los_monopolios_son_los_de_la_grabacion(conn)
        prueba_el_reparto_del_monopolio_no_se_inventa(conn)
        prueba_el_importador_sabe_leer_un_reparto()
        prueba_ponerle_nombre_a_alguien_arregla_lo_ya_guardado()
        prueba_no_hay_gente_de_mentira(conn)
        prueba_las_vistas_viejas_siguen_de_acuerdo(conn)
        prueba_las_mejoras_no_borran_el_poblado(conn)
        prueba_el_ritmo_va_en_orden(conn)
        prueba_una_partida_de_ia_no_sale_en_el_global(conn, con_ia)
        prueba_el_filtro_de_mesa(conn)
        prueba_los_tres_ambitos(conn, con_ia, amigas)
        prueba_pedir_una_de_ia_la_da(conn, con_ia)
        prueba_el_numero_de_partida_no_es_texto(conn)
    finally:
        conn.close()

    prueba_el_panel_las_sirve(partidas)

    print()
    print("%d de %d%s" % (_hechas - _malas, _hechas,
                          "   (%d saltadas)" % _saltadas if _saltadas else ""))
    return 1 if _malas else 0


if __name__ == "__main__":
    sys.exit(main())
