# -*- coding: utf-8 -*-
"""Lanza consultas SQL contra catan_stats.db y enseña el resultado en tabla.

    py sql.py "SELECT name, final_points FROM players WHERE game_id=1"
    py sql.py -f consulta.sql          la consulta está en un fichero
    py sql.py --tablas                 qué tablas y columnas hay
    py sql.py --tablas players         las columnas de una tabla

La base es SQLite y el fichero es `catan_stats.db`; lo único que faltaba era
con qué escribirle. Esto no hace nada que no haga el `sqlite3` de toda la
vida, pero no hay que instalarlo: Python ya trae SQLite dentro.

ABRE EN SOLO LECTURA salvo que se le pase --escribir. Esto es para consultar,
y una consulta mal escrita no debería poder borrar seis días de partidas. Con
--escribir se abre normal, por si algún día hace falta un UPDATE a mano.
"""
import argparse
import os
import sqlite3
import sys

RAIZ = os.path.dirname(os.path.abspath(__file__))
BASE = os.path.join(RAIZ, "catan_stats.db")
_ANCHO_MAXIMO = 60      # una columna más ancha que esto se recorta al enseñarla


def _texto(v):
    if v is None:
        return "NULL"          # se distingue de la cadena vacía a propósito
    s = str(v)
    return s if len(s) <= _ANCHO_MAXIMO else s[:_ANCHO_MAXIMO - 1] + "…"


def tabla(cabeceras, filas):
    """Las filas alineadas en columnas, como las enseñaría sqlite3."""
    if not cabeceras:
        return
    anchos = [len(c) for c in cabeceras]
    pintadas = []
    for fila in filas:
        celdas = [_texto(v) for v in fila]
        pintadas.append(celdas)
        for i, c in enumerate(celdas):
            if len(c) > anchos[i]:
                anchos[i] = len(c)

    def linea(celdas):
        return "  ".join(c.ljust(anchos[i]) for i, c in enumerate(celdas)).rstrip()

    print(linea(cabeceras))
    print("  ".join("-" * a for a in anchos))
    for celdas in pintadas:
        print(linea(celdas))
    print()
    print("%d fila%s" % (len(pintadas), "" if len(pintadas) == 1 else "s"))


def mandar_tablas(conn, cual=None):
    nombres = [r[0] for r in conn.execute(
        "SELECT name FROM sqlite_master WHERE type IN ('table','view') "
        "AND name NOT LIKE 'sqlite_%' ORDER BY type DESC, name")]
    if cual:
        if cual not in nombres:
            print("No hay ninguna tabla '%s'. Las que hay: %s"
                  % (cual, ", ".join(nombres)))
            return 1
        nombres = [cual]
    for n in nombres:
        cols = [(r[1], r[2]) for r in conn.execute("PRAGMA table_info(%s)" % n)]
        filas = conn.execute("SELECT COUNT(*) FROM %s" % n).fetchone()[0]
        print("%s  (%d filas)" % (n, filas))
        for nombre, tipo in cols:
            print("    %-22s %s" % (nombre, tipo or ""))
        print()
    return 0


def main():
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("consulta", nargs="?", help="el SQL, entre comillas")
    p.add_argument("-f", "--fichero", help="leer la consulta de un fichero")
    p.add_argument("--tablas", nargs="?", const=True,
                   help="listar las tablas (o las columnas de una)")
    p.add_argument("--escribir", action="store_true",
                   help="permitir escribir (por defecto es solo lectura)")
    args = p.parse_args()

    if not os.path.isfile(BASE):
        print("No hay base de datos en %s" % BASE)
        return 1

    if args.escribir:
        conn = sqlite3.connect(BASE)
    else:
        conn = sqlite3.connect("file:%s?mode=ro" % BASE.replace("\\", "/"),
                               uri=True)
    try:
        if args.tablas:
            return mandar_tablas(conn, None if args.tablas is True else args.tablas)

        sql = args.consulta
        if args.fichero:
            with open(args.fichero, encoding="utf-8") as f:
                sql = f.read()
        if not sql or not sql.strip():
            p.print_help()
            return 1

        try:
            cur = conn.execute(sql)
        except sqlite3.OperationalError as e:
            print("La consulta no vale: %s" % e)
            if "readonly" in str(e):
                print("(la base se abre en solo lectura; usa --escribir si de "
                      "verdad quieres modificarla)")
            return 1
        if cur.description is None:
            conn.commit()
            print("hecho, %d fila(s) afectadas" % cur.rowcount)
            return 0
        tabla([d[0] for d in cur.description], cur.fetchall())
        return 0
    finally:
        conn.close()


if __name__ == "__main__":
    sys.exit(main())
