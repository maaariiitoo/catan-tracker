# -*- coding: utf-8 -*-
"""Mete en tu base las partidas de otra que aquí no están.

    py db/fundir.py la_base_de_un_amigo.db          dice qué traería
    py db/fundir.py la_base_de_un_amigo.db --de-verdad

PARA QUÉ. Cada uno juega en su ordenador y cada uno tiene su base. Sin esto,
juntar el histórico del grupo era sustituir una por otra, y sustituir pierde:
cargas la de uno y desaparecen las del otro, porque en su base nunca
estuvieron. Esto SUMA. Se pueden juntar cuatro bases, hoy y el mes que viene,
y lo único que pasa es que hay más partidas.

CÓMO SE SABE CUÁLES FALTAN. Por la huella de la mesa: quiénes jugaron y qué
tablero les tocó (`mod_verdad/importar.py`). Una partida que jugasteis los
dos tiene la misma huella en las dos bases aunque tenga otro número, otro
color y otros nombres, así que entra una vez. Y una partida en la que tú no
estabas no se parece a ninguna tuya, así que entra entera.

LOS NÚMEROS DE PARTIDA NO SE RESPETAN, y no se puede. Su partida 7 y tu
partida 7 son dos partidas distintas: la suya entra con el siguiente número
libre de tu base y todo lo que colgaba de ella -- jugadores, casillas,
tiradas, robos -- se vuelve a atar al número nuevo. Eso es lo delicado de
esto y es donde se rompería en silencio: una tirada que se quede apuntando al
jugador de otra partida no da error, da una estadística falsa.

Por eso el recorrido NO es una lista de tablas escrita a mano, que es lo que
ya se quedó corto una vez en `db/quitar_partidas.py`: se le pregunta al
esquema quién depende de quién y se copia de padres a hijos, remapeando cada
clave por el camino.

LOS NOMBRES SON LOS TUYOS. Las vistas agrupan por nombre, así que si en tu
base alguien es «Pedro» y en la suya `jugador_e6397905`, sin más serían dos
personas y sus partidas quedarían repartidas entre las dos sin que nada lo
dijera. Al copiar, cada jugador se renombra con el nombre que esa cuenta
tiene AQUÍ.
"""
import argparse
import datetime
import os
import shutil
import sqlite3
import sys

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RAIZ)
sys.path.insert(0, os.path.join(RAIZ, "mod_verdad"))

import mod_verdad.importar as imp      # noqa: E402

BASE = os.path.join(RAIZ, "catan_stats.db")
COPIAS = os.path.join(RAIZ, "copias")


def _columnas(conn, tabla, esquema="main"):
    return [r[1] for r in conn.execute("PRAGMA %s.table_info(%s)"
                                       % (esquema, tabla))]


def _clave(conn, tabla):
    """La columna que es `INTEGER PRIMARY KEY`, o None si no la hay.

    Es la que NO se copia: se deja que SQLite dé una nueva y se apunta la
    equivalencia. Las tablas de clave compuesta (`building_tiles`) no tienen
    ninguna y se copian enteras, que para eso sus dos columnas ya son claves
    remapeadas."""
    filas = [r for r in conn.execute("PRAGMA table_info(%s)" % tabla)]
    # `r[5]` no es un si/no: es el puesto de la columna DENTRO de la clave.
    # O sea que valdria 1 tanto para `buildings.building_id`, que va sola,
    # como para la primera mitad de `building_tiles (building_id, tile_id)`,
    # que no. Confundirlas dejaba a `building_tiles` sin su edificio: la
    # columna se saltaba al copiar por creerla autonumerica.
    claves = [r for r in filas if r[5]]
    if len(claves) == 1 and "INT" in (claves[0][2] or "").upper():
        return claves[0][1]
    return None


def _padres(conn, tabla):
    """{columna: tabla a la que apunta} de las claves ajenas de esa tabla."""
    return {r[3]: r[2]
            for r in conn.execute("PRAGMA foreign_key_list(%s)" % tabla)}


def tablas_de_una_partida(conn):
    """Las tablas que hay que copiar, padres antes que hijos.

    Se sacan del esquema y no de una lista: entran las que llevan `game_id` y
    las que cuelgan de ellas aunque no lo lleven (`building_tiles` va por su
    edificio). Una tabla nueva entra sola el día que se añada, que es lo que
    no pasa con una lista escrita a mano.
    """
    todas = [t for (t,) in conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' "
        "AND name NOT LIKE 'sqlite_%' ORDER BY name")]
    padres = {t: set(_padres(conn, t).values()) for t in todas}
    dentro = {t for t in todas if "game_id" in _columnas(conn, t)}
    dentro.add("games")
    creciendo = True
    while creciendo:
        creciendo = False
        for t in todas:
            if t not in dentro and (padres[t] & dentro):
                dentro.add(t)
                creciendo = True

    # Y ahora en orden: una tabla va después de todas las suyas. Con un tope
    # de vueltas, que un esquema con un ciclo colgaría esto para siempre.
    orden, quedan = [], sorted(dentro)
    for _vuelta in range(len(quedan) + 2):
        if not quedan:
            break
        listas = [t for t in quedan
                  if not ((padres[t] & dentro) - set(orden) - {t})]
        if not listas:
            raise ValueError("el esquema tiene un ciclo: %s" % quedan)
        orden.extend(listas)
        quedan = [t for t in quedan if t not in listas]
    if quedan:
        raise ValueError("no he sabido ordenar %s" % quedan)
    return orden


def _preparar(ruta):
    """Deja una base con `network_id` y `huella` puestos.

    Se hace también con la que llega, y hace falta: puede venir de una
    versión anterior, sin las columnas o sin rellenar, y entonces no habría
    con qué cruzarla y entraría repetida entera."""
    otra = sqlite3.connect(ruta)
    try:
        imp.crear_tablas(otra)
        imp.ponerle_huella_a_las_de_antes(otra)
        otra.commit()
    finally:
        otra.close()


def _que_falta(conn):
    """(las que faltan, las que ya están, las que no se pueden cruzar)."""
    mias = {h for (h,) in conn.execute(
        "SELECT huella FROM games WHERE huella IS NOT NULL")}
    faltan, estaban, ciegas = [], [], []
    for gid, huella in conn.execute(
            "SELECT game_id, huella FROM otra.games ORDER BY game_id"):
        if not huella:
            # Sin huella no se puede saber si ya la tienes. Se queda fuera y
            # se dice: meterla a ciegas es arriesgarse a duplicar una partida
            # tuya, y eso no se ve luego en ningún sitio.
            ciegas.append(gid)
        elif huella in mias:
            estaban.append(gid)
        else:
            faltan.append(gid)
    return faltan, estaban, ciegas


def _traer_identidades(conn):
    """Las cuentas que no conocías. Los nombres de aquí no se tocan.

    Si la misma cuenta tiene nombre en las dos bases, manda el tuyo: es el
    que sale en tus 32 tablas y el que tú pusiste a mano."""
    nuevas = 0
    for red, nombre, bot, visto in conn.execute(
            "SELECT network_id, display_name, is_bot, first_seen "
            "FROM otra.mod_identities"):
        cur = conn.execute(
            "INSERT OR IGNORE INTO mod_identities (network_id, display_name,"
            " is_bot, first_seen, last_seen) VALUES (?,?,?,?,?)",
            (red, nombre, bot, visto, visto))
        nuevas += cur.rowcount
    conn.execute("INSERT OR IGNORE INTO people (display_name) "
                 "SELECT display_name FROM mod_identities")
    # Y los nombres sueltos de sus jugadores que no salen de ninguna cuenta,
    # que si no la clave ajena de `players.person_name` no deja copiarlos.
    conn.execute("INSERT OR IGNORE INTO people (display_name) "
                 "SELECT DISTINCT person_name FROM otra.players "
                 "WHERE person_name IS NOT NULL")
    conn.execute("INSERT OR IGNORE INTO people (display_name) "
                 "SELECT DISTINCT name FROM otra.players "
                 "WHERE name IS NOT NULL")
    return nuevas


def _copiar(conn, tabla, gids, mapa):
    """Las filas de esa tabla que son de esas partidas, con las claves
    cambiadas por las de aquí. Devuelve cuántas."""
    cols_aqui = _columnas(conn, tabla)
    cols_alli = _columnas(conn, tabla, "otra")
    # Sólo las columnas que están en las dos. La base que llega puede ser de
    # una versión anterior, y entonces le faltan columnas o le sobran: las
    # que falten se quedan a NULL y las que sobren se ignoran, en vez de
    # reventar la fusión entera por una columna.
    cols = [c for c in cols_aqui if c in cols_alli]
    pk = _clave(conn, tabla)
    if pk in cols:
        cols.remove(pk)
    padres = {c: p for c, p in _padres(conn, tabla).items()
              if p in mapa and c in cols}

    if pk == "game_id":
        # `games` es su propia tabla de partidas: se filtra por su clave, que
        # es la que se acaba de sacar de `cols` para que la asigne SQLite.
        donde = "game_id IN (%s)" % ",".join("?" * len(gids))
        args = list(gids)
    elif "game_id" in cols:
        donde = "game_id IN (%s)" % ",".join("?" * len(gids))
        args = list(gids)
    else:
        # Sin `game_id`: se va por el padre que sí se ha copiado, que es como
        # cuelga `building_tiles` de sus edificios.
        col = next((c for c in padres), None)
        if col is None:
            return 0
        hijos = list(mapa[padres[col]])
        if not hijos:
            return 0
        donde = "%s IN (%s)" % (col, ",".join("?" * len(hijos)))
        args = hijos

    lectura = ([pk] if pk else []) + cols
    filas = conn.execute("SELECT %s FROM otra.%s WHERE %s"
                         % (", ".join(lectura), tabla, donde), args).fetchall()
    # `mod_imports` se apunta con el nombre de la grabación, que es su clave y
    # puede coincidir con una tuya. Si coincide, la tuya manda: es la que
    # sabe qué fichero de TU carpeta produjo qué partida.
    verbo = "INSERT OR IGNORE INTO" if tabla == "mod_imports" else "INSERT INTO"
    hueco = ",".join("?" * len(cols))
    cuantas = 0
    for fila in filas:
        viejo = fila[0] if pk else None
        valores = list(fila[1:] if pk else fila)
        for i, c in enumerate(cols):
            if c in padres and valores[i] is not None:
                valores[i] = mapa[padres[c]].get(valores[i])
        cur = conn.execute("%s %s (%s) VALUES (%s)"
                           % (verbo, tabla, ", ".join(cols), hueco), valores)
        if pk:
            mapa.setdefault(tabla, {})[viejo] = cur.lastrowid
        cuantas += 1
    return cuantas


def _ponerles_tus_nombres(conn, nuevos):
    """Los jugadores que acaban de entrar, con el nombre que usas tú.

    Se va por la cuenta, que es lo único que significa lo mismo en las dos
    bases. Al que no traiga cuenta se le deja el suyo: inventarle uno sería
    peor."""
    for gid in nuevos:
        conn.execute("""
            UPDATE players SET
                name = COALESCE((SELECT i.display_name FROM mod_identities i
                                  WHERE i.network_id = players.network_id),
                                name),
                person_name = COALESCE(
                    (SELECT i.display_name FROM mod_identities i
                      WHERE i.network_id = players.network_id),
                    person_name)
             WHERE game_id = ?""", (gid,))
        # Y el ganador de la partida, que se guarda por su nombre y no por su
        # fila: sin esto una partida traída diría que ganó «jugador_e639...»
        # mientras sus jugadores ya se llaman como tú los llamas.
        conn.execute("""
            UPDATE games SET winner = (
                SELECT p.name FROM players p
                 WHERE p.game_id = games.game_id
                   AND p.final_rank = 1)
             WHERE game_id = ? AND winner IS NOT NULL
               AND EXISTS (SELECT 1 FROM players p WHERE p.game_id = games.game_id
                            AND p.final_rank = 1)""", (gid,))


def fundir(conn, ruta_otra, di=None):
    """Trae a `conn` las partidas de `ruta_otra` que aquí no están.

    `ruta_otra` tiene que ser un fichero del que se pueda escribir: se le
    ponen las huellas antes de cruzar nada. Se le pasa una COPIA, no la base
    de nadie.
    """
    di = di or (lambda *a: None)
    _preparar(ruta_otra)
    imp.crear_tablas(conn)
    imp.ponerle_huella_a_las_de_antes(conn)

    conn.execute("ATTACH DATABASE ? AS otra", (ruta_otra,))
    try:
        faltan, estaban, ciegas = _que_falta(conn)
        di("  ya estaban: %d" % len(estaban))
        di("  traer:      %d" % len(faltan))
        if ciegas:
            di("  sin huella, se quedan fuera: %s"
               % ", ".join(str(g) for g in ciegas))
        if not faltan:
            return {"traidas": [], "ya_estaban": len(estaban),
                    "sin_huella": ciegas, "filas": 0}

        nuevas_cuentas = _traer_identidades(conn)
        mapa, filas = {}, 0
        for tabla in tablas_de_una_partida(conn):
            filas += _copiar(conn, tabla, faltan, mapa)
        nuevos = sorted(mapa.get("games", {}).values())
        _ponerles_tus_nombres(conn, nuevos)
        conn.commit()
        di("  %d filas en %d partidas, que aquí son la %s"
           % (filas, len(nuevos),
              ", ".join(str(n) for n in nuevos)))
        return {"traidas": nuevos, "ya_estaban": len(estaban),
                "sin_huella": ciegas, "filas": filas,
                "cuentas_nuevas": nuevas_cuentas}
    finally:
        conn.commit()
        conn.execute("DETACH DATABASE otra")


def copia_de_seguridad():
    if not os.path.isdir(COPIAS):
        os.makedirs(COPIAS)
    marca = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    destino = os.path.join(COPIAS, "catan_stats_antes_de_fundir_%s.db" % marca)
    shutil.copyfile(BASE, destino)
    return destino


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("otra", help="la base que llega")
    ap.add_argument("--de-verdad", action="store_true",
                    help="sin esto solo dice que traeria")
    args = ap.parse_args()

    if not os.path.isfile(args.otra):
        print("No encuentro %s" % args.otra)
        return 1
    if not os.path.isfile(BASE):
        print("No hay base en %s" % BASE)
        return 1

    # Siempre sobre una copia de la que llega: se le escriben las huellas, y
    # la base de un amigo no se toca.
    import tempfile
    tmp = tempfile.mkdtemp(prefix="catan_fundir_")
    copia = os.path.join(tmp, "la_que_llega.db")
    shutil.copyfile(args.otra, copia)
    try:
        if not args.de_verdad:
            conn = sqlite3.connect(BASE)
            try:
                _preparar(copia)
                imp.crear_tablas(conn)
                imp.ponerle_huella_a_las_de_antes(conn)
                conn.execute("ATTACH DATABASE ? AS otra", (copia,))
                faltan, estaban, ciegas = _que_falta(conn)
                conn.execute("DETACH DATABASE otra")
            finally:
                conn.close()
            print("Traeria %d partidas. Ya tenias %d de las suyas."
                  % (len(faltan), len(estaban)))
            if ciegas:
                print("Y %d se quedan fuera por no poder cruzarlas: %s"
                      % (len(ciegas), ciegas))
            print()
            print("Con --de-verdad se hace, y antes se copia tu base a copias/.")
            return 0

        print("copia de tu base en %s" % copia_de_seguridad())
        conn = sqlite3.connect(BASE)
        try:
            fundir(conn, copia, di=print)
        finally:
            conn.close()
        print("Hecho.")
        return 0
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(main())
