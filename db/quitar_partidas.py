# -*- coding: utf-8 -*-
"""Saca partidas sueltas del histórico, sin vaciar la base entera.

    py db/quitar_partidas.py --con-ia            dice qué quitaría
    py db/quitar_partidas.py --con-ia --de-verdad
    py db/quitar_partidas.py 1 3                 por número de partida

Sin --de-verdad no toca nada. Con --de-verdad copia la base a `copias/`
antes, igual que `db/vaciar.py`, porque tampoco hay deshacer.

DEJA LA GRABACIÓN MARCADA. Borrar las filas no basta: la carpeta de
`mod_verdad/datos/` sigue ahí, y la marca de "ya importada" se va con la
partida, así que la siguiente pasada del importador la metería otra vez. Por
eso la carpeta se apunta en `mod_ignoradas` y el importador la salta. Para
volver a meterla:

    py mod_verdad/importar.py --carpeta partida_20260819_213741 --rehacer

NO BORRA LAS CAPTURAS. Los PNG y el `indice.jsonl` se quedan enteros, y eso
es lo que entrena y mide la red. Quitar una partida del histórico no le hace
perder ni un recorte a la visión.

ANTES DE QUITAR LAS DE LA IA, dos cosas que conviene saber:

  - Para no verlas en las estadísticas no hace falta borrarlas. Están las
    vistas `amigos_*` de `db/vistas.py`, que ya filtran las partidas en las
    que los cuatro son personas.
  - Son la mayor parte de las etiquetas del histórico. Los caballeros que se
    ven en el panel, los recursos, las tiradas: eso sale de aquí, y es con
    lo que se comprueba que la lectura de la pantalla acierta.
"""
import argparse
import datetime
import os
import shutil
import sqlite3
import sys

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BASE = os.path.join(RAIZ, "catan_stats.db")
COPIAS = os.path.join(RAIZ, "copias")

# Las que cuelgan de una partida, en el orden que no rompe las claves ajenas.
# `building_tiles` no tiene game_id y va por su edificio, así que aparte.
# De qué tablas hay que borrar. NO es una lista escrita a mano, y por algo:
# la que había se quedó corta. Le faltaban `harbor_owners` y
# `monopoly_takes`, así que quitar una partida dejaba filas apuntando a una
# partida que ya no existe. Eso no da error -- no salta nada, no se ve en el
# panel -- hasta el día que una vista pasa por ahí y saca datos de una
# partida borrada.
#
# Se le pregunta al esquema, que es lo único que no se puede olvidar de una
# tabla nueva.
def tablas_con_partida(conn):
    """Las tablas que llevan `game_id`, `games` aparte porque va la última."""
    tablas = []
    for (t,) in conn.execute("SELECT name FROM sqlite_master "
                             "WHERE type='table' ORDER BY name"):
        if t == "games":
            continue
        if "game_id" in [c[1] for c in conn.execute("PRAGMA table_info(%s)" % t)]:
            tablas.append(t)
    return tablas


def copia_de_seguridad():
    if not os.path.isdir(COPIAS):
        os.makedirs(COPIAS)
    marca = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    destino = os.path.join(COPIAS, "catan_stats_antes_de_quitar_%s.db" % marca)
    shutil.copyfile(BASE, destino)
    return destino


def con_ia(conn):
    return [r[0] for r in conn.execute(
        "SELECT g.game_id FROM games g WHERE EXISTS "
        "(SELECT 1 FROM players p WHERE p.game_id=g.game_id AND p.is_bot=1) "
        "ORDER BY g.game_id")]


def ficha(conn, gid):
    fila = conn.execute(
        "SELECT substr(started_at,1,16), winner FROM games WHERE game_id=?",
        (gid,)).fetchone()
    if fila is None:
        return None
    quienes = [r[0] for r in conn.execute(
        "SELECT COALESCE(person_name, name) FROM players WHERE game_id=? "
        "ORDER BY is_bot, turn_order", (gid,))]
    ias = conn.execute("SELECT COUNT(*) FROM players WHERE game_id=? AND is_bot=1",
                       (gid,)).fetchone()[0]
    carpeta = conn.execute("SELECT carpeta FROM mod_imports WHERE game_id=?",
                           (gid,)).fetchone()
    # Las mismas tablas de las que se va a borrar, para que el «se pierden N
    # filas» no diga menos de lo que de verdad se lleva por delante.
    filas = 0
    for t in tablas_con_partida(conn) + ["games"]:
        filas += conn.execute(
            "SELECT COUNT(*) FROM %s WHERE game_id=?" % t, (gid,)).fetchone()[0]
    filas += conn.execute(
        "SELECT COUNT(*) FROM building_tiles bt JOIN buildings b "
        " ON b.building_id = bt.building_id WHERE b.game_id=?",
        (gid,)).fetchone()[0]
    return {"cuando": fila[0], "gano": fila[1], "quienes": quienes, "ias": ias,
            "carpeta": carpeta[0] if carpeta else None, "filas": filas}


def que_se_pierde(conn, gids):
    """Lo que dejaría de haber con qué medir, que es lo que de verdad duele."""
    marca = ",".join(str(g) for g in gids)
    def cuenta(sql):
        return conn.execute(sql).fetchone()[0]
    return [
        ("caballeros jugados", cuenta(
            "SELECT COUNT(*) FROM dev_card_plays WHERE card_type='Caballero' "
            "AND game_id IN (%s)" % marca),
         cuenta("SELECT COUNT(*) FROM dev_card_plays WHERE card_type='Caballero'")),
        ("tiradas", cuenta("SELECT COUNT(*) FROM rolls WHERE game_id IN (%s)" % marca),
         cuenta("SELECT COUNT(*) FROM rolls")),
        ("recursos cobrados", cuenta(
            "SELECT COUNT(*) FROM resource_gains WHERE game_id IN (%s)" % marca),
         cuenta("SELECT COUNT(*) FROM resource_gains")),
        ("comercios", cuenta(
            "SELECT COUNT(*) FROM trades WHERE game_id IN (%s)" % marca),
         cuenta("SELECT COUNT(*) FROM trades")),
        ("robos", cuenta("SELECT COUNT(*) FROM steals WHERE game_id IN (%s)" % marca),
         cuenta("SELECT COUNT(*) FROM steals")),
    ]


def quitar(conn, gid, motivo):
    carpeta = conn.execute("SELECT carpeta FROM mod_imports WHERE game_id=?",
                           (gid,)).fetchone()
    # `building_tiles` no tiene `game_id`: se llega por su edificio, y hay
    # que hacerlo ANTES de borrar los edificios o ya no hay por dónde.
    conn.execute("DELETE FROM building_tiles WHERE building_id IN "
                 "(SELECT building_id FROM buildings WHERE game_id=?)", (gid,))
    for t in tablas_con_partida(conn):
        conn.execute("DELETE FROM %s WHERE game_id=?" % t, (gid,))
    conn.execute("DELETE FROM games WHERE game_id=?", (gid,))
    if carpeta:
        conn.execute(
            "INSERT OR REPLACE INTO mod_ignoradas (carpeta, motivo, cuando) "
            "VALUES (?,?,?)",
            (carpeta[0], motivo,
             datetime.datetime.now().isoformat(timespec="seconds")))
    return carpeta[0] if carpeta else None


def main():
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("partidas", nargs="*", type=int, help="números de partida")
    p.add_argument("--con-ia", action="store_true",
                   help="todas las que tengan algún jugador de la IA")
    p.add_argument("--de-verdad", action="store_true",
                   help="quitarlas (sin esto solo dice qué quitaría)")
    p.add_argument("--motivo", default="partida contra la IA",
                   help="por qué se deja fuera, para acordarse luego")
    args = p.parse_args()

    if not os.path.isfile(BASE):
        print("No hay base de datos en %s" % BASE)
        return 1

    conn = sqlite3.connect(BASE)
    try:
        gids = sorted(set(args.partidas) | (set(con_ia(conn)) if args.con_ia else set()))
        if not gids:
            print("No has dicho qué quitar. Con --con-ia van las de la IA,")
            print("o pásale números: py db/quitar_partidas.py 1 3")
            return 1

        fichas = [(g, ficha(conn, g)) for g in gids]
        faltan = [g for g, f in fichas if f is None]
        if faltan:
            print("No existe(n) la(s) partida(s) %s." %
                  ", ".join(str(g) for g in faltan))
            return 1

        print("%s del histórico:" %
              ("QUITANDO" if args.de_verdad else "Se quitarían"))
        print()
        total = 0
        for g, f in fichas:
            total += f["filas"]
            print("   partida %d   %s   ganó %s" % (g, f["cuando"], f["gano"]))
            print("      %s%s" % (", ".join(f["quienes"]),
                                  "   (%d de la IA)" % f["ias"] if f["ias"] else ""))
            print("      %d filas   grabación: %s"
                  % (f["filas"], f["carpeta"] or "ninguna"))
        print()
        print("   %d filas en total" % total)

        print()
        print("   y con ellas se va esto, que es con lo que se mide:")
        for que, va, hay in que_se_pierde(conn, gids):
            print("      %-20s %3d de %3d  (%d%%)"
                  % (que, va, hay, round(100.0 * va / hay) if hay else 0))

        if not args.de_verdad:
            print()
            print("   para verlas sin borrarlas: las vistas amigos_* ya las filtran")
            print('      py sql.py "SELECT * FROM amigos_marcador"')
            print()
            print("No se ha tocado nada. Para hacerlo de verdad:")
            print("   py db/quitar_partidas.py %s --de-verdad"
                  % ("--con-ia" if args.con_ia else
                     " ".join(str(g) for g in gids)))
            return 0

        destino = copia_de_seguridad()
        print()
        print("   copia de seguridad: %s" % destino)
        marcadas = []
        for g, _f in fichas:
            carpeta = quitar(conn, g, args.motivo)
            if carpeta:
                marcadas.append(carpeta)
        conn.commit()
        conn.execute("VACUUM")
        conn.commit()

        quedan = conn.execute("SELECT COUNT(*) FROM games").fetchone()[0]
        print("   quitadas %d. Quedan %d partidas." % (len(fichas), quedan))
        if marcadas:
            print()
            print("   grabaciones marcadas para que el importador no las repita:")
            for c in marcadas:
                print("      %s" % c)
            print("   (las capturas siguen en disco; no se ha borrado ninguna)")
        return 0
    finally:
        conn.close()


if __name__ == "__main__":
    sys.exit(main())
