# -*- coding: utf-8 -*-
"""Vacía el histórico de partidas de la base de datos, para empezar de cero.

    py db/vaciar.py                 dice qué borraría, sin tocar nada
    py db/vaciar.py --de-verdad     lo borra

Siempre hace una copia antes, en `copias/`, aunque se le pase --de-verdad.
No es paranoia: esto borra el trabajo de varios días y no hay deshacer.

QUÉ BORRA: las partidas y todo lo que cuelga de ellas -- jugadores, tablero,
edificios, carreteras, tiradas, turnos, recursos, ladrón, robos, comercios y
cartas. Y `mod_imports`, para que el importador vuelva a considerar nuevas
las grabaciones que ya había metido.

QUÉ NO BORRA, y conviene saberlo:

  - `mod_identities`: qué identificador de cuenta es qué persona. Eso no es
    el histórico de una partida, es conocimiento que costó ponerlo y que vale
    para las que vengan. Con --tambien-los-nombres se borra también.
  - `name_aliases`: cómo lee mal el OCR cada nombre. Igual de reutilizable.
  - `mod_ignoradas`: qué grabaciones se decidieron dejar fuera. Es una
    decisión tomada, no histórico; si se borrara, la siguiente pasada del
    importador las volvería a meter todas.
  - Las capturas de `mod_verdad/datos/` ni los ficheros crudos de
    `mod_verdad/crudo/`. Eso son los datos para entrenar la red y no tienen
    nada que ver con el histórico. Si quieres tirarlos, bórralos a mano
    sabiendo lo que haces: son 16 GB que no se pueden volver a generar.
  - `red/tableros_de_prueba.json`, que es de donde salen los tableros de
    red/pruebas.py desde que la base puede estar vacía.
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

# En este orden: primero lo que apunta a otras cosas, luego lo apuntado. Con
# PRAGMA foreign_keys activado, al revés no se puede.
TABLAS = [
    "robber_blocks", "steals", "robber_moves", "resource_gains",
    "dev_card_plays", "dev_card_purchases", "trades", "turns", "rolls",
    "roads", "building_tiles", "buildings", "tiles", "harbors", "players",
    "games", "mod_imports",
]
CONOCIMIENTO = ["mod_identities", "name_aliases", "people", "mod_ignoradas"]


def cuenta(conn, tabla):
    try:
        return conn.execute("SELECT COUNT(*) FROM %s" % tabla).fetchone()[0]
    except sqlite3.OperationalError:
        return None      # la tabla no existe en esta base


def copia_de_seguridad():
    if not os.path.isdir(COPIAS):
        os.makedirs(COPIAS)
    marca = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    destino = os.path.join(COPIAS, "catan_stats_antes_de_vaciar_%s.db" % marca)
    shutil.copyfile(BASE, destino)
    return destino


def main():
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--de-verdad", action="store_true",
                   help="borra (sin esto solo dice qué borraría)")
    p.add_argument("--tambien-los-nombres", action="store_true",
                   help="borra también quién es quién y los alias del OCR")
    args = p.parse_args()

    if not os.path.isfile(BASE):
        print("No hay base de datos en %s" % BASE)
        return 1

    conn = sqlite3.connect(BASE)
    try:
        objetivo = list(TABLAS)
        if args.tambien_los_nombres:
            objetivo += CONOCIMIENTO

        antes = [(t, cuenta(conn, t)) for t in objetivo]
        total = sum(n for _t, n in antes if n)
        print("%s la base de datos %s" %
              ("VACIANDO" if args.de_verdad else "Se vaciaría", BASE))
        print()
        for t, n in antes:
            if n:
                print("   %-22s %6d filas" % (t, n))
        print("   %-22s %6d filas en total" % ("", total))

        if not args.tambien_los_nombres:
            print()
            print("   se conservan:")
            for t in CONOCIMIENTO:
                n = cuenta(conn, t)
                if n:
                    print("      %-19s %6d filas" % (t, n))
            print("      (con --tambien-los-nombres se borran)")

        if not args.de_verdad:
            print()
            print("No se ha tocado nada. Para hacerlo de verdad:")
            print("   py db/vaciar.py --de-verdad")
            return 0

        destino = copia_de_seguridad()
        print()
        print("   copia de seguridad: %s" % destino)

        conn.execute("PRAGMA foreign_keys = OFF")
        for t in objetivo:
            if cuenta(conn, t) is None:
                continue
            conn.execute("DELETE FROM %s" % t)
        # que los identificadores vuelvan a empezar en 1
        try:
            conn.execute("DELETE FROM sqlite_sequence")
        except sqlite3.OperationalError:
            pass
        conn.commit()

        # Si se han quitado los nombres, hay que dejar `people` coherente:
        # se queda con los que siga conociendo mod_identities y nada más.
        if not args.tambien_los_nombres:
            conn.execute(
                "DELETE FROM people WHERE display_name NOT IN "
                "(SELECT display_name FROM mod_identities)")
            conn.commit()

        conn.execute("VACUUM")
        conn.close()
        conn = sqlite3.connect(BASE)

        print()
        quedan = [(t, cuenta(conn, t)) for t in TABLAS + CONOCIMIENTO]
        malas = [(t, n) for t, n in quedan if n and t in objetivo]
        if malas:
            print("   ALGO HA QUEDADO: %s" % malas)
            return 1
        print("   vaciada. Quedan: %s" % (", ".join(
            "%s %d" % (t, n) for t, n in quedan if n) or "nada"))
        print("   tamaño del fichero: %.1f MB" % (os.path.getsize(BASE) / 1e6))
        print()
        print("Para volver a meter las partidas del mod:")
        print("   py mod_verdad/importar.py")
        return 0
    finally:
        conn.close()


if __name__ == "__main__":
    sys.exit(main())
