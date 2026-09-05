# -*- coding: utf-8 -*-
"""Mete en la base de datos lo que apuntó el mod.

El mod lee el estado del juego por dentro, así que lo que escribe no tiene
error: no hay que estimar nada ni fiarse de ningún píxel. Esto lo convierte
en las tablas de siempre (`games`, `players`, `buildings`, `roads`, `rolls`,
`resource_gains`...) para poder consultarlo con las mismas vistas y las
mismas consultas que las partidas leídas por visión.

    py mod_verdad/importar.py               importa lo que falte
    py mod_verdad/importar.py --quien       quién es quién
    py mod_verdad/importar.py --llamar <id> Pedro
    py mod_verdad/importar.py --carpeta partida_20260819_192154
    py mod_verdad/importar.py --rehacer     reimporta aunque ya esté

Tres cosas que conviene entender antes de tocar esto:

1. QUIÉN ES QUIÉN. El mod no guarda nombres: la lógica del juego no los
   tiene. Lo que sí guarda es el `CommunicationId`, que para una IA es
   "Jean_hard" y para una persona es el identificador de su cuenta. Ese
   identificador es ESTABLE -- comprobado, el mismo aparece en las 8
   grabaciones que había al escribir esto -- así que sirve para reconocer a
   la misma persona partida tras partida. Es mejor identidad que el nombre
   leído por OCR, que cambia según lo bien que se lea la bandera.

   Por eso hay una tabla `mod_identities`: identificador -> nombre. Se
   rellena una vez con --llamar y ya vale para siempre.

2. DE DÓNDE SALEN LOS RECURSOS. El mod no apunta las manos de nadie (a
   propósito: son información oculta, ver el comentario de
   BuscarReglaDePuntos en CatanVerdad.cs). Pero la PRODUCCIÓN no hace falta
   apuntarla, se DEDUCE: con la tirada, el tablero y los edificios, las
   reglas de Catan dicen exactamente quién recibe qué. Eso es lo que se
   guarda en `resource_gains`, y es exacto, no una estimación.

   Lo que no se puede deducir es qué se intercambió en un comercio ni qué
   carta se llevó un robo. Eso queda registrado como que pasó, con el
   contenido a NULL. Mejor un hueco honesto que un número inventado.

3. QUIÉN HIZO QUÉ, sin leer el estado de la acción. El mod solo captura el
   primer parámetro de Apply (el estado del juego), no el segundo (el de la
   acción), así que "a quién robó" no viene escrito. Pero sí vienen las
   `cuentas` de cada jugador, y esas se pueden RESTAR entre un evento y el
   siguiente: al que le sube `RobbedCount` es el robado, a los que les sube
   `SuccessfullTrades` son los dos que comerciaron. Es exacto y no hace
   falta tocar nada oculto.
"""
import argparse
import collections
import datetime
import glob
import gzip
import json
import os
import shutil
import sqlite3
import sys

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, RAIZ)
sys.path.insert(0, AQUI)

from red.sitios import Alineador, TERRENO_DEL_JUEGO  # noqa: E402
from vision.board_graph import TILE_AXIAL, axial_to_pixel  # noqa: E402
from donde_esta_el_juego import carpeta_de_verdad  # noqa: E402

BASE = os.path.join(RAIZ, "catan_stats.db")
DATOS = os.path.join(RAIZ, "mod_verdad", "datos")
CRUDO = os.path.join(RAIZ, "mod_verdad", "crudo")

PIEZA = {"Settlement": "poblado", "City": "ciudad", "Road": "carretera"}

# El juego ejecuta CADA acción CINCO veces seguidas, dentro de unos pocos
# milisegundos. Medido sobre la partida del 19/8 a las 19:21: 2220 eventos
# en el fichero, 444 acciones de verdad, 400 grupos de exactamente 5.
#
# Las cinco copias son idénticas en todo -- tablero, piezas, dados,
# jugadores, cuentas -- MENOS en dos campos: el reloj y `jugador_activo`.
# Y ahí está la trampa: las tres últimas traen jugador_activo = -1. O sea
# que quedarse con una copia cualquiera es quedarse, tres de cada cinco
# veces, con un estado que no dice de quién es el turno.
#
# Por eso se agrupan las repeticiones seguidas y se toma LA PRIMERA, que es
# la única que trae el jugador del turno de verdad.
_MISMO_MS = 200


# --------------------------------------------------------------------------
# leer el fichero del mod
# --------------------------------------------------------------------------

def _abrir(ruta):
    """Vale igual el fichero del juego que la copia comprimida del repo."""
    if ruta.endswith(".gz"):
        return gzip.open(ruta, "rt", encoding="utf-8")
    return open(ruta, encoding="utf-8")


def eventos(ruta):
    """Los eventos de un fichero del mod, en orden y sin las repeticiones.

    De cada grupo de repeticiones se devuelve la PRIMERA: es la que trae
    `jugador_activo` de verdad (ver el comentario de _MISMO_MS)."""
    if not os.path.isfile(ruta):
        return []
    salida = []
    ultima_accion, ultimo_ms = None, None
    with _abrir(ruta) as f:
        for linea in f:
            try:
                d = json.loads(linea)
            except ValueError:
                continue  # última línea a medias si el juego se cerró de golpe
            if d.get("esquema") or not d.get("accion"):
                continue
            accion, ms = d["accion"], d.get("reloj_ms") or 0
            if (accion == ultima_accion and ultimo_ms is not None
                    and ms - ultimo_ms <= _MISMO_MS):
                ultimo_ms = ms      # sigue el mismo grupo: esta copia se tira
                continue
            ultima_accion, ultimo_ms = accion, ms
            salida.append(d)
    return salida


def ficheros():
    """Los ficheros del mod, del más viejo al más nuevo.

    El bueno es el que escribe el mod en la carpeta del juego. El grabador
    (recopilar.py) deja también un `indice.jsonl` en mod_verdad/datos, pero
    ESE NO VALE para esto: solo apunta los estados que llegó a fotografiar,
    o sea uno de cada cinco, y encima elegido sin mirar cuál. Importando de
    ahí salían partidas sin una sola tirada ni turno.

    Si el de la carpeta del juego ya no está -- Steam verifica los ficheros
    y se los lleva por delante -- se usa la copia comprimida del repo."""
    vistos, salida = set(), []
    carpeta = carpeta_de_verdad()
    if carpeta and os.path.isdir(carpeta):
        for f in sorted(glob.glob(os.path.join(carpeta, "partida_*.jsonl"))):
            if os.path.getsize(f) > 0:
                vistos.add(nombre_de(f))
                salida.append(f)
    for f in sorted(glob.glob(os.path.join(CRUDO, "partida_*.jsonl.gz"))):
        if nombre_de(f) not in vistos:
            salida.append(f)
    return sorted(salida, key=nombre_de)


def nombre_de(ruta):
    """La clave con la que se recuerda una partida ya importada. Es el mismo
    nombre que lleva la carpeta del grabador, para poder cruzar las dos
    cosas: 'partida_20260819_192154'."""
    n = os.path.basename(ruta)
    if n.endswith(".gz"):
        n = n[:-3]
    return os.path.splitext(n)[0]


def _tamano_descomprimido(ruta_gz):
    """Cuántos bytes tenía el fichero original. Se lee entero porque el gzip
    no lo dice de fiar (el campo ISIZE de la cola solo guarda el tamaño
    módulo 4 GB), pero son décimas de segundo: estos ficheros comprimen a
    menos de una centésima de su tamaño."""
    total = 0
    try:
        with gzip.open(ruta_gz, "rb") as f:
            for trozo in iter(lambda: f.read(1 << 20), b""):
                total += len(trozo)
    except (OSError, EOFError):
        return -1        # copia corrupta o a medias: se vuelve a escribir
    return total


def guardar_copia(ruta):
    """Una copia comprimida en el repo del fichero crudo del mod.

    Los originales viven en la carpeta del juego, y ahí no están a salvo: si
    Steam verifica o reinstala Catan, desaparecen. Y hacen falta -- el
    importador se ha reescrito tres veces el día que se estrenó, y cada vez
    hubo que volver al fichero original.

    Comprimen muchísimo (105 MB -> 0,8 MB) porque el juego escribe cinco
    copias casi idénticas de cada acción, así que guardarlas no cuesta nada.
    Solo se copia lo que ha salido del mod. Suena a perogrullada y no lo es:
    importando un fichero de prueba desde otra carpeta, la copia lo metía en
    `crudo/` y a partir de ahí `ficheros()` lo veía como una partida más --
    una partida inventada, con sus tiradas y sus jugadores, indistinguible de
    las de verdad. Pasó de verdad probando esto.

    Devuelve el mensaje que hay que enseñar, o None si no había nada que
    hacer."""
    if ruta.endswith(".gz"):
        return None                      # ya es la copia
    suya = carpeta_de_verdad()
    if not suya or os.path.dirname(os.path.abspath(ruta)) != os.path.abspath(suya):
        return None                      # no lo ha escrito el mod: no se guarda
    try:
        if not os.path.isdir(CRUDO):
            os.makedirs(CRUDO)
        destino = os.path.join(CRUDO, nombre_de(ruta) + ".jsonl.gz")
        origen_bytes = os.path.getsize(ruta)
        if os.path.isfile(destino):
            # No basta con «ya está copiada»: importando a media partida se
            # guardaba media grabación, y como el fichero ya existía no se
            # refrescaba NUNCA. El día que desapareciera el original, la
            # copia -- la red de seguridad -- sería media partida, y encima
            # sin avisar de que le faltaba el resto.
            if _tamano_descomprimido(destino) == origen_bytes:
                return None
            nota = "copia actualizada"
        else:
            nota = "copia guardada"
        with open(ruta, "rb") as origen:
            with gzip.open(destino, "wb") as salida:
                shutil.copyfileobj(origen, salida)
        return "%s (%.1f MB -> %.2f MB)" % (
            nota, origen_bytes / 1e6, os.path.getsize(destino) / 1e6)
    except OSError as e:
        # No es motivo para no importar: los datos ya están en la base.
        return "AVISO: no se ha podido guardar la copia: %s" % e


def _iso(ms):
    if not ms:
        return None
    return datetime.datetime.fromtimestamp(ms / 1000.0).isoformat(timespec="seconds")


# --------------------------------------------------------------------------
# quién es quién
# --------------------------------------------------------------------------

def crear_tablas(conn):
    # El esquema base -- `games`, `players`, `rolls`, `buildings`... -- vive en
    # `db/schema.sql`, y hasta ahora nadie lo aplicaba: se daba por hecho que
    # el .db ya existia. En esta maquina existe, asi que no se notaba; en una
    # recien clonada NO, y el `py mod_verdad/importar.py` del README moria
    # en el primer `ALTER TABLE robber_moves`, porque `PRAGMA table_info` de
    # una tabla que no esta no da error: da cero columnas, y el ALTER se lanza
    # igual. O sea que las instrucciones de «en otra maquina» no funcionaban.
    #
    # Aplicarlo siempre es seguro: los 17 `CREATE TABLE` son `IF NOT EXISTS` y
    # no hay ningun `DROP`, asi que sobre una base ya hecha no toca nada.
    esquema = os.path.join(RAIZ, "db", "schema.sql")
    if os.path.exists(esquema):
        with open(esquema, encoding="utf-8") as f:
            conn.executescript(f.read())
        # `executescript` hace COMMIT antes de empezar, y el script lleva un
        # `PRAGMA foreign_keys = ON` que dentro de una transaccion no haria
        # nada. Se vuelve a poner aqui para que valga de verdad.
        conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("""
        CREATE TABLE IF NOT EXISTS mod_identities (
            network_id   TEXT PRIMARY KEY,
            display_name TEXT NOT NULL,
            is_bot       INTEGER NOT NULL DEFAULT 0,
            first_seen   TEXT,
            last_seen    TEXT
        )
    """)
    # De qué grabación salió cada partida. Sin esto no se puede saber si una
    # carpeta ya está importada, y reimportar duplicaría la partida entera
    # en silencio.
    conn.execute("""
        CREATE TABLE IF NOT EXISTS mod_imports (
            carpeta   TEXT PRIMARY KEY,
            game_id   INTEGER NOT NULL REFERENCES games(game_id),
            eventos   INTEGER,
            imported_at TEXT
        )
    """)
    # Lo que salio mal al importar ESTA grabacion, en una linea. No es un log:
    # es un dato de la partida, porque cambia lo que las tablas quieren decir.
    # El caso que lo estreno: en el tablero de 5-6 jugadores el mod no supo
    # leer donde estaba el ladron, asi que la partida 11 tiene 15 robos y CERO
    # movimientos de ladron, cero bloqueos, y la produccion contada como si no
    # hubiera ladron en el tablero. Mirando solo las tablas eso no se ve --
    # sale una partida creible-- y por eso la pega tiene que viajar con ella.
    cols = {r[1] for r in conn.execute("PRAGMA table_info(mod_imports)")}
    if "pegas" not in cols:
        conn.execute("ALTER TABLE mod_imports ADD COLUMN pegas TEXT")
    # Grabaciones que se han decidido dejar fuera del histórico. Hace falta
    # una tabla aparte y no un campo en `mod_imports`: al borrar una partida
    # se borra su fila de ahí, y sin esta marca la siguiente pasada del
    # importador la volvería a meter, deshaciendo el borrado en silencio.
    # Los puertos del tablero. `tiles_json` son los índices 0-18 de las
    # casillas del tablero a las que toca, que es lo que dice a qué poblados
    # les sirve. `ratio` puede venir a NULL si el juego no lo da como número.
    #
    # `where_json` es la posición TAL CUAL la da el mod, sin interpretar. Se
    # guarda porque todavía no se sabe si el juego pone el puerto en un
    # vértice o en una arista, y de eso depende cómo se saca de ahí el sitio
    # exacto. Interpretarla ahora sería adivinar; guardarla cruda cuesta nada
    # y evita tener que volver a jugar una partida para averiguarlo.
    conn.execute("""
        CREATE TABLE IF NOT EXISTS harbors (
            harbor_id   INTEGER PRIMARY KEY AUTOINCREMENT,
            game_id     INTEGER NOT NULL REFERENCES games(game_id),
            kind        TEXT,
            ratio       INTEGER,
            tiles_json  TEXT,
            where_json  TEXT
        )
    """)
    cols = {r[1] for r in conn.execute("PRAGMA table_info(harbors)")}
    if "where_json" not in cols:
        conn.execute("ALTER TABLE harbors ADD COLUMN where_json TEXT")
    # La arista del puerto: las dos casillas [x,y] entre las que está. Es lo
    # que hacía falta para saber de quién es cada puerto, y no estaba porque
    # se leía la clave del diccionario como si fuera una `HexGridPosition`
    # cuando es una `EdgePosition` -- ver el comentario de `Puertos()` en
    # CatanVerdad.cs. Sólo la traen las grabaciones del 22/8 en adelante.
    if "edge_json" not in cols:
        conn.execute("ALTER TABLE harbors ADD COLUMN edge_json TEXT")
    # Las tres casillas del vértice donde está el poblado, tal cual. `vertex_key`
    # no vale para esto: mezcla los tile_id con un centro en píxeles, y para
    # cruzarlo con la arista de un puerto hacen falta las caras en crudo.
    # Por qué se movió el ladrón: 'siete' o 'caballero'. En el Catan básico no
    # hay una tercera causa, así que con saber cuál de las dos es basta.
    #
    # No se deduce mirando la hora contra la tabla de tiradas: se sabe SIN
    # ambigüedad por el orden de los eventos, porque el juego manda la carta
    # antes del movimiento. Deducirlo después por cercanía fallaría justo en
    # el caso interesante -- jugar un caballero y luego sacar un 7 en el mismo
    # turno son DOS movimientos, y por tiempo se confunden.
    cols = {r[1] for r in conn.execute("PRAGMA table_info(robber_moves)")}
    if "cause" not in cols:
        conn.execute("ALTER TABLE robber_moves ADD COLUMN cause TEXT")
    cols = {r[1] for r in conn.execute("PRAGMA table_info(buildings)")}
    if "faces_json" not in cols:
        conn.execute("ALTER TABLE buildings ADD COLUMN faces_json TEXT")
    # Quién tiene cada puerto y desde cuándo. Se calcula al importar y no en
    # una vista porque es geometría, no una cuenta: un poblado tiene el puerto
    # si entre sus tres casillas están las dos de la arista.
    conn.execute("""
        CREATE TABLE IF NOT EXISTS harbor_owners (
            game_id     INTEGER NOT NULL REFERENCES games(game_id),
            harbor_id   INTEGER NOT NULL REFERENCES harbors(harbor_id),
            building_id INTEGER NOT NULL REFERENCES buildings(building_id),
            player_id   INTEGER NOT NULL REFERENCES players(player_id),
            turn_number INTEGER,
            timestamp   TEXT,
            PRIMARY KEY (harbor_id, building_id)
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS mod_ignoradas (
            carpeta   TEXT PRIMARY KEY,
            motivo    TEXT,
            cuando    TEXT
        )
    """)
    # Los dos premios de 2 puntos. Sin ellos no se puede saber qué parte de
    # los puntos totales venía de cartas de punto de victoria tapadas, que es
    # lo único que el mod no puede leer. 1 el que lo tiene, 0 el resto, NULL
    # si esa grabación es de antes de que el mod lo apuntara.
    cols = {r[1] for r in conn.execute("PRAGMA table_info(players)")}
    for columna in ("longest_road", "largest_army", "final_points_visible"):
        if columna not in cols:
            conn.execute("ALTER TABLE players ADD COLUMN %s INTEGER" % columna)
    # Cuándo un poblado se hizo ciudad. En `turn_number` se queda cuándo se
    # puso el poblado, que es otra pregunta y también hace falta.
    cols = {r[1] for r in conn.execute("PRAGMA table_info(buildings)")}
    if "upgraded_turn" not in cols:
        conn.execute("ALTER TABLE buildings ADD COLUMN upgraded_turn INTEGER")
    if "upgraded_at" not in cols:
        conn.execute("ALTER TABLE buildings ADD COLUMN upgraded_at TEXT")
    # Qué recurso pidió un monopolio. Va en la propia jugada, no en una tabla
    # aparte, porque es uno por carta. Se rellena desde la acción SIGUIENTE a
    # jugar la carta: el juego apunta primero «juega una carta de desarrollo»
    # sin decir cuál, y después manda `Monopoly_SelectResourceType` con el
    # recurso. Está en las grabaciones desde el principio -- el importador lo
    # tiraba, no el mod.
    cols = {r[1] for r in conn.execute("PRAGMA table_info(dev_card_plays)")}
    if "resource" not in cols:
        conn.execute("ALTER TABLE dev_card_plays ADD COLUMN resource TEXT")
    # Cuánto le sacó un monopolio a cada jugador.
    #
    # Es información pública: cuando alguien juega un monopolio la mesa entera
    # ve lo que entrega cada uno. No se parece al robo del ladrón, que es la
    # carta de UNO y a escondidas, y que por eso no se lee.
    #
    # `raw_json` es el reparto TAL CUAL lo vuelca el mod, sin interpretar. Va
    # aquí por lo mismo que `harbors.where_json`: `AsResourcesFromPlayers` es
    # un modelo generado, no se sabe qué forma tienen sus campos hasta verlo
    # jugando, y adivinarla ahora sería inventar. Guardarla cruda cuesta nada
    # y evita perder la primera partida que sí lo traiga. Las columnas de al
    # lado se rellenan cuando se sepa leerla.
    conn.execute("""
        CREATE TABLE IF NOT EXISTS monopoly_takes (
            take_id     INTEGER PRIMARY KEY AUTOINCREMENT,
            game_id     INTEGER NOT NULL REFERENCES games(game_id),
            play_id     INTEGER REFERENCES dev_card_plays(play_id),
            turn_number INTEGER,
            taker_id    INTEGER REFERENCES players(player_id),
            victim_id   INTEGER REFERENCES players(player_id),
            resource    TEXT,
            amount      INTEGER,
            raw_json    TEXT,
            timestamp   TEXT
        )
    """)
    # Un índice por cada columna que apunta a otra tabla, y se sacan de la
    # propia base en vez de escribirlos a mano. Escritos a mano, la lista se
    # queda corta el día que alguien añade una tabla -- y nadie lo nota,
    # porque de menos no falla nada, sólo va peor.
    #
    # No es por velocidad de hoy: la base pesa medio mega y la vista más lenta
    # tarda 45 ms. Es porque con las claves ajenas ENCENDIDAS, borrar una fila
    # padre obliga a SQLite a recorrer la tabla hija entera si la columna no
    # está indexada, y eso pasa de verdad cada vez que se rehace una partida.
    ya = set()
    tablas = [r[0] for r in conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' "
        "AND name NOT LIKE 'sqlite_%'")]
    for tabla in tablas:
        for idx in conn.execute("PRAGMA index_list(%s)" % tabla):
            primera = [c[2] for c in conn.execute("PRAGMA index_info(%s)" % idx[1])]
            if primera:
                ya.add((tabla, primera[0]))
    for tabla in tablas:
        for fk in conn.execute("PRAGMA foreign_key_list(%s)" % tabla):
            columna = fk[3]
            if columna is None or (tabla, columna) in ya:
                continue
            conn.execute("CREATE INDEX IF NOT EXISTS idx_fk_%s_%s ON %s(%s)"
                         % (tabla, columna, tabla, columna))
            ya.add((tabla, columna))

    cols = {r[1] for r in conn.execute("PRAGMA table_info(games)")}
    if "source" not in cols:
        # 'vision' para las de siempre, 'mod' para estas. Las que ya había
        # se quedan a NULL y eso es correcto: se leyeron por visión, pero
        # decirlo ahora sería inventarse un dato que nadie comprobó.
        conn.execute("ALTER TABLE games ADD COLUMN source TEXT")
    conn.commit()


def nombre_automatico(red, tipo):
    """El nombre que se le pone solo a un identificador nuevo.

    Las IA lo traen puesto ("Jean_hard" -> "Jean") y no hay nada que
    preguntar. Las personas no: su identificador es el de su cuenta y no se
    parece a nada, así que se les pone uno provisional y el importador avisa
    para que se les ponga el de verdad con --llamar."""
    if tipo and tipo != "Human":
        return red.replace("_hard", "").replace("_easy", "").replace("_medium", ""), 1
    return "jugador_" + (red or "?")[:8], 0


def identidades(conn, jugadores, cuando):
    """Identificador -> nombre, creando los que falten."""
    salida, nuevos = {}, []
    for j in jugadores:
        red = j.get("red") or ""
        fila = conn.execute(
            "SELECT display_name, is_bot FROM mod_identities WHERE network_id=?",
            (red,)).fetchone()
        if fila is None:
            nombre, es_bot = nombre_automatico(red, j.get("tipo"))
            conn.execute(
                "INSERT INTO mod_identities (network_id, display_name, is_bot, "
                "first_seen, last_seen) VALUES (?,?,?,?,?)",
                (red, nombre, es_bot, cuando, cuando))
            if not es_bot:
                nuevos.append((red, nombre))
        else:
            nombre, es_bot = fila
            conn.execute("UPDATE mod_identities SET last_seen=? WHERE network_id=?",
                         (cuando, red))
        conn.execute("INSERT OR IGNORE INTO people (display_name) VALUES (?)",
                     (nombre,))
        salida[j["id"]] = (nombre, es_bot)
    conn.commit()
    return salida, nuevos


# --------------------------------------------------------------------------
# la producción, que se deduce de las reglas
# --------------------------------------------------------------------------

def _hexes_de(pieza, alin):
    """Los índices 0-18 de las casillas que toca una pieza. Las que caen en
    el mar dan None y se descartan: un vértice del borde toca 3 hexágonos
    pero puede que solo 1 esté en el tablero."""
    caras = (pieza.get("donde") or {}).get("casillas") or []
    salida = []
    for c in caras:
        if c is None:
            continue
        i = alin.casilla(c)
        if i is not None:
            salida.append(i)
    return salida


def produccion(edificios, tablero, alin, valor, hex_ladron):
    """Quién recibe qué con esta tirada. Reglas de Catan, sin estimar nada:
    cada casilla con ese número que no tenga el ladrón encima produce su
    recurso, 1 por poblado y 2 por ciudad.

    Devuelve [(jugador_mod, recurso, cantidad), ...] y aparte la lista de
    bloqueos del ladrón, que es la misma cuenta al revés: lo que se habría
    llevado cada uno si el ladrón no estuviera ahí."""
    gana = collections.Counter()
    bloqueado = []
    for pieza in edificios:
        tipo = PIEZA.get(pieza.get("tipo"))
        if tipo not in ("poblado", "ciudad"):
            continue
        cantidad = 2 if tipo == "ciudad" else 1
        for i in _hexes_de(pieza, alin):
            recurso, numero = tablero[i]
            if numero != valor or recurso == "Desierto":
                continue
            if i == hex_ladron:
                bloqueado.append((pieza["de_jugador"], i, tipo, cantidad))
            else:
                gana[(pieza["de_jugador"], recurso)] += cantidad
    return ([(j, r, n) for (j, r), n in sorted(gana.items())], bloqueado)


# Los puertos, tal y como los nombra el juego. Leído del enum `HarborType` en
# Assembly-CSharp.dll, que NO lleva el mismo orden que `BaseResourceType`
# (ahí Wool=2 y Grain=3, aquí al revés). Copiarlo del otro habría cambiado los
# puertos de trigo por los de lana sin que se notara.
PUERTO_DEL_JUEGO = {
    "Lumber": "Madera", "Brick": "Arcilla", "Grain": "Cereales",
    "Wool": "Lana", "Ore": "Mineral", "Generic": "generico",
}
PUERTO_POR_NUMERO = {0: "Lumber", 1: "Brick", 2: "Grain", 3: "Wool",
                     4: "Ore", 5: "Generic"}


def _puerto_de(p):
    """De qué es el puerto y a cuánto cambia.

    Las grabaciones viejas guardaban el número del enum en un campo llamado
    `cambio`, creyendo que era el 2 del 2:1. No lo era: era el TIPO. Por eso
    se acepta el nombre si viene y se traduce el número si no -- y así los
    puertos de las partidas 5 y 6 salen bien sin volver a jugarlas.

    El cambio no se lee de ningún sitio porque no hace falta: en el Catan
    básico los de recurso son 2:1 y los genéricos 3:1, siempre."""
    nombre = p.get("tipo") or ""
    if nombre not in PUERTO_DEL_JUEGO:
        numero = p.get("tipo_num")
        if numero is None:
            numero = p.get("cambio")     # como se llamaba antes
        nombre = PUERTO_POR_NUMERO.get(numero, "")
    if nombre not in PUERTO_DEL_JUEGO:
        return None, None
    return PUERTO_DEL_JUEGO[nombre], 3 if nombre == "Generic" else 2


def _dueños_de_puertos(conn, game_id, contador):
    """Quién tiene cada puerto, cruzando la arista con los vértices.

    Un puerto está en la arista entre dos casillas. Los dos sitios desde los
    que se usa son los dos extremos de esa arista, y un vértice es un sitio
    donde se tocan tres casillas -- así que el poblado tiene el puerto si
    entre sus tres casillas están las dos de la arista. No hace falta calcular
    los vértices: basta con mirar si los contiene.

    Se hace aquí y no en una vista porque es geometría, no una cuenta, y
    porque en SQL comparar conjuntos guardados como JSON sale ilegible.

    Las ciudades cuentan igual que los poblados: una ciudad es un poblado
    mejorado y no se mueve del sitio. Por eso se mira `buildings` entero y el
    turno que se apunta es `turn_number`, el de ponerlo, no el de mejorarlo."""
    puertos = conn.execute(
        "SELECT harbor_id, edge_json FROM harbors "
        "WHERE game_id=? AND edge_json IS NOT NULL", (game_id,)).fetchall()
    if not puertos:
        return
    piezas = conn.execute(
        "SELECT building_id, player_id, turn_number, timestamp, faces_json "
        "FROM buildings WHERE game_id=? AND faces_json IS NOT NULL",
        (game_id,)).fetchall()
    caras_de = {}
    for bid, pid, turno, cuando, caras in piezas:
        caras_de[bid] = (pid, turno, cuando,
                         set(tuple(c) for c in json.loads(caras)))
    for harbor_id, arista in puertos:
        borde = set(tuple(c) for c in json.loads(arista))
        for bid, (pid, turno, cuando, caras) in caras_de.items():
            if borde <= caras:
                conn.execute(
                    "INSERT OR REPLACE INTO harbor_owners (game_id, harbor_id, "
                    "building_id, player_id, turn_number, timestamp) "
                    "VALUES (?,?,?,?,?,?)",
                    (game_id, harbor_id, bid, pid, turno, cuando))
                contador["puertos con dueño"] += 1


def _cartas_json(lista):
    """Las cartas de un lado de un comercio, en el formato que ya usa la
    tabla `trades`: [{"resource":"Cereales","amount":1}].

    El juego las nombra en inglés ("Lumber"), igual que los terrenos, así que
    se traducen con el mismo vocabulario. Devuelve None si no hay nada, para
    distinguir «no se sabe» (las grabaciones de antes del detalle) de «no dio
    nada», que son cosas distintas."""
    if not lista:
        return None
    salida = []
    for c in lista:
        recurso = c.get("recurso")
        if not recurso:
            continue
        salida.append({"resource": TERRENO_DEL_JUEGO.get(recurso, recurso),
                       "amount": c.get("cantidad")})
    return json.dumps(salida, ensure_ascii=False) if salida else None


def produccion_inicial(edificio, tablero, alin):
    """Lo que da el segundo poblado al colocarlo. Un recurso por cada
    casilla que toca, y el desierto no da nada."""
    salida = []
    for i in _hexes_de(edificio, alin):
        recurso, _numero = tablero[i]
        if recurso != "Desierto":
            salida.append((edificio["de_jugador"], recurso, 1))
    return salida


# --------------------------------------------------------------------------
# importar una grabación
# --------------------------------------------------------------------------

def importar(conn, ruta, rehacer=False, callado=False):
    def di(*a):
        if not callado:
            print(*a)

    nombre_carpeta = nombre_de(ruta)
    ya = conn.execute("SELECT game_id FROM mod_imports WHERE carpeta=?",
                      (nombre_carpeta,)).fetchone()
    if ya and not rehacer:
        return None, "ya estaba (partida %d)" % ya[0]
    # Se salta con --rehacer a propósito: pedir una carpeta por su nombre es
    # bastante explícito como para no discutirlo.
    fuera = conn.execute("SELECT motivo FROM mod_ignoradas WHERE carpeta=?",
                         (nombre_carpeta,)).fetchone()
    if fuera and not rehacer:
        return None, "dejada fuera a mano (%s)" % (fuera[0] or "sin motivo")

    evs = eventos(ruta)
    if not evs:
        return None, "sin eventos"
    con_tablero = [e for e in evs if e.get("casillas")]
    if not con_tablero:
        return None, "ninguna anotación trae el tablero"
    # Una partida de verdad deja cientos de eventos. Trece son los de
    # arrancar el juego y salirse antes de jugar nada -- pasa cada vez que se
    # abre Catan y se cambia de idea, y hay dos así entre las grabaciones.
    if len(evs) < 40:
        return None, "solo %d eventos: no llegó a ser una partida" % len(evs)

    ultimo = con_tablero[-1]

    try:
        alin = Alineador.encajar_solo(ultimo["casillas"])
    except ValueError as e:
        return None, "no se pueden nombrar los sitios: %s" % e

    # el tablero: índice 0-18 -> (recurso, número)
    tablero, sin_traducir = {}, set()
    for c in ultimo["casillas"]:
        if c.get("terreno") == "Water":
            continue
        i = alin.casilla(c["pos"])
        if i is None:
            continue
        terreno = c.get("terreno")
        if terreno not in TERRENO_DEL_JUEGO:
            sin_traducir.add(terreno)
        tablero[i] = (TERRENO_DEL_JUEGO.get(terreno, terreno), c.get("numero"))
    # Cuantas tiene que haber lo dice el tablero que el alineador ha
    # reconocido, no un 19 escrito aqui: el base son 19 y el de 5-6
    # jugadores 30 (filas 3-4-5-6-5-4-3). Lo que se comprueba es lo mismo de
    # siempre -- que TODAS las casillas del mod hayan caido en un sitio del
    # tablero, sin perder ninguna por el camino.
    if len(tablero) != len(alin.reticula):
        return None, ("salen %d casillas de las %d del tablero"
                      % (len(tablero), len(alin.reticula)))
    if sin_traducir:
        return None, ("el juego usa terrenos que no conozco: %s. Añádelos a "
                      "TERRENO_DEL_JUEGO en red/sitios.py"
                      % ", ".join(sorted(sin_traducir)))

    empezo = _iso(evs[0].get("reloj_ms"))
    acabo = _iso(evs[-1].get("reloj_ms"))

    # Rehaciendo se conserva el MISMO game_id. Antes se borraba y se volvía
    # a insertar, y el autoincremento daba uno nuevo: la partida 1 pasaba a
    # ser la 2 por reimportarla, y cualquier consulta escrita a mano dejaba
    # de encontrarla sin decir por qué.
    mismo_id = ya[0] if (ya and rehacer) else None
    if mismo_id is not None:
        borrar_partida(conn, mismo_id)

    # --- la partida y los jugadores ---------------------------------------
    if mismo_id is not None:
        conn.execute(
            "INSERT INTO games (game_id, started_at, ended_at, notes, source) "
            "VALUES (?,?,?,?,?)",
            (mismo_id, empezo, acabo, "mod: " + nombre_carpeta, "mod"))
        game_id = mismo_id
    else:
        cur = conn.execute(
            "INSERT INTO games (started_at, ended_at, notes, source) "
            "VALUES (?,?,?,?)",
            (empezo, acabo, "mod: " + nombre_carpeta, "mod"))
        game_id = cur.lastrowid

    quien, nuevos = identidades(conn, ultimo.get("jugadores") or [], empezo)
    pid_de = {}
    for j in ultimo.get("jugadores") or []:
        nombre, es_bot = quien[j["id"]]
        # turn_order se deja a NULL aquí: lo rellena _orden_de_turno al
        # acabar, mirando quién colocó antes. `hueco` NO vale para esto (ver
        # allí). Si la partida se importa antes de la colocación inicial, se
        # queda en NULL, que es la respuesta correcta: todavía no se sabe.
        cur = conn.execute(
            "INSERT INTO players (game_id, person_name, name, color, is_bot) "
            "VALUES (?,?,?,?,?)",
            (game_id, nombre, nombre, j.get("color"), es_bot))
        pid_de[j["id"]] = cur.lastrowid

    # --- las casillas del tablero (19 en el base, 30 en el de 5-6) ---------
    tile_id = {}
    for i in range(len(alin.reticula)):
        recurso, numero = tablero[i]
        # Las axiales salen de la reticula que ha encajado, no de la lista
        # fija del tablero base: con 30 casillas TILE_AXIAL solo tiene 19 y
        # esto reventaria con un IndexError -- o peor, guardaria las 19
        # primeras con coordenadas que no son las suyas.
        q, r = alin.reticula.casillas[i]
        cur = conn.execute(
            "INSERT INTO tiles (game_id, axial_q, axial_r, resource, number) "
            "VALUES (?,?,?,?,?)", (game_id, q, r, recurso, numero))
        tile_id[i] = cur.lastrowid

    # --- los puertos -------------------------------------------------------
    # Sólo en las grabaciones del 21/8 en adelante. Antes el mod no los
    # apuntaba, y no hay forma de sacarlos de lo grabado: no se guarda una
    # captura del tablero entero en la que se pudieran leer.
    contador = collections.Counter()
    for p in (ultimo.get("puertos") or []):
        # La arista es lo nuevo (22/8). Las grabaciones de antes traen
        # `donde.casillas`, que venía vacío, así que se aceptan las dos y una
        # de las dos estará.
        arista = [c for c in (p.get("arista") or []) if c]
        caras = arista or [c for c in
                           ((p.get("donde") or {}).get("casillas") or []) if c]
        # Un puerto está en el borde: de las casillas que toca, unas son mar
        # y otras tablero. Se guardan las del tablero, que son a las que se
        # puede llegar con un poblado.
        tocadas = sorted(set(i for i in (alin.casilla(c) for c in caras)
                             if i is not None))
        kind, ratio = _puerto_de(p)
        conn.execute(
            "INSERT INTO harbors (game_id, kind, ratio, tiles_json, where_json, "
            "edge_json) VALUES (?,?,?,?,?,?)",
            (game_id, kind, ratio, json.dumps(tocadas),
             json.dumps(p.get("donde"), ensure_ascii=False),
             json.dumps(arista) if len(arista) == 2 else None))
        contador["puertos"] += 1

    estado = _Recorrido(conn, game_id, alin, tablero, tile_id, pid_de, contador)
    for i, ev in enumerate(evs):
        estado.paso(ev, evs[i + 1:i + 6])
    estado.cerrar()
    _dueños_de_puertos(conn, game_id, contador)

    # Las pegas, si las hay. Van a la base con la partida y no solo a la
    # pantalla: quien mire estas tablas dentro de un mes no va a tener delante
    # lo que se imprimio el dia que se importaron.
    pegas = []
    if estado.desconocidas:
        # Las tres mas repetidas y cuantas hay en total: con eso ya se sabe a
        # que se ha jugado y cuanto falta por escribir, sin abrir el .jsonl.
        try:
            from mod_verdad import catalogar
            familias = sorted(set(
                f for f in (catalogar.familia_de(a) for a in estado.desconocidas)
                if f))
        except Exception:
            familias = []
        top = ", ".join("%s x%d" % (a, n)
                        for a, n in estado.desconocidas.most_common(3))
        pegas.append("%d acciones sin entender (%d tipos%s): %s"
                     % (sum(estado.desconocidas.values()),
                        len(estado.desconocidas),
                        (", " + "/".join(familias)) if familias else "", top))
    if contador.get("ladron sin sitio"):
        pegas.append(
            "el ladron no se pudo leer en %d movimientos: sin bloqueos y con "
            "la produccion contada como si no estuviera en el tablero"
            % contador["ladron sin sitio"])

    conn.execute("DELETE FROM mod_imports WHERE carpeta=?", (nombre_carpeta,))
    conn.execute(
        "INSERT INTO mod_imports (carpeta, game_id, eventos, imported_at, pegas) "
        "VALUES (?,?,?,?,?)",
        (nombre_carpeta, game_id, len(evs), datetime.datetime.now().isoformat(
            timespec="seconds"), "; ".join(pegas) or None))
    conn.commit()

    aviso = guardar_copia(ruta)
    if aviso:
        di("     %s" % aviso)
    for red, nombre in nuevos:
        di("    [!] identificador nuevo sin nombre: %s -> se ha llamado '%s'"
           % (red, nombre))
        di("        ponle el suyo con el boton «Ponerle nombre a alguien» del")
        di("        panel, o aqui:  py mod_verdad/importar.py --llamar %s Pedro"
           % red)
    detalle = "%d eventos -> %s" % (
        len(evs), ", ".join("%s %d" % (k, v) for k, v in sorted(contador.items())))
    # Sin la acción de ganar, o la partida se abandonó o TODAVÍA SE ESTÁ
    # JUGANDO. Importa decirlo: la grabación se lee entera aunque el juego
    # siga escribiéndola, así que importar a media partida guarda media
    # partida -- y encima queda apuntada como hecha, así que el siguiente
    # intento la salta y hay que acordarse de --rehacer.
    if estado.desconocidas:
        # De qué expansión son. El catálogo lo saca del ensamblado del juego y
        # va en el repo, así que esto funciona sin tener Catan instalado; si
        # falta, se dicen los nombres a secas, que ya sirven.
        try:
            from mod_verdad import catalogar
            de_quien = catalogar.familia_de
        except Exception:
            de_quien = lambda _a: None
        familias = sorted(set(
            f for f in (de_quien(a) for a in estado.desconocidas) if f))
        di("     [!] %d acciones que no entiendo, de %d tipos distintos%s."
           % (sum(estado.desconocidas.values()), len(estado.desconocidas),
              (" -- " + ", ".join(familias)) if familias else ""))
        for a, n in estado.desconocidas.most_common(8):
            di("         %-58s x%d" % (a, n))
        di("         La grabación está entera y guardada: cuando el importador")
        di("         aprenda estas acciones, `--rehacer` mete la partida sin")
        di("         perder nada.")
    if contador.get("ladron sin sitio"):
        di("     [!] EL LADRON NO SE HA PODIDO LEER en %d movimientos."
           % contador["ladron sin sitio"])
        di("         Sin su posición no hay bloqueos Y LA PRODUCCIÓN SALE DE MÁS:")
        di("         se cuenta como si el ladrón no estuviera en el tablero.")
        di("         Le pasaba al tablero de 5-6 jugadores: ahí el juego deja")
        di("         `GamePiecesRobber` vacío y guarda al ladrón en")
        di("         `GamePiecesRobbers[0]`. Ya arreglado -- el mod")
        di("         usa ya `BoardQuery.GetRobberTile`, que es el accesor del")
        di("         propio juego. Si esto sale en una grabación NUEVA, el")
        di("         juego ha vuelto a moverlo de sitio: mira `ladron_donde_buscar`")
        di("         en el .jsonl, que trae los nombres candidatos.")
    if not contador.get("final"):
        di("     [!] esta partida no tiene final: o se abandonó o se está")
        di("         jugando ahora mismo. Si era lo segundo, cuando acabe:")
        di("         py mod_verdad/importar.py --rehacer")
    return game_id, detalle


def borrar_partida(conn, game_id):
    """Todo lo de una partida, en el orden que no rompe las claves ajenas."""
    for tabla in ("robber_blocks", "steals", "robber_moves", "resource_gains",
                  "monopoly_takes", "dev_card_plays", "dev_card_purchases",
                  "trades", "turns", "rolls", "roads", "harbor_owners",
                  "harbors"):
        conn.execute("DELETE FROM %s WHERE game_id=?" % tabla, (game_id,))
    conn.execute("DELETE FROM building_tiles WHERE building_id IN "
                 "(SELECT building_id FROM buildings WHERE game_id=?)", (game_id,))
    conn.execute("DELETE FROM buildings WHERE game_id=?", (game_id,))
    conn.execute("DELETE FROM tiles WHERE game_id=?", (game_id,))
    conn.execute("DELETE FROM players WHERE game_id=?", (game_id,))
    conn.execute("DELETE FROM mod_imports WHERE game_id=?", (game_id,))
    conn.execute("DELETE FROM games WHERE game_id=?", (game_id,))
    conn.commit()


# Las acciones de reparto que son PRODUCCION de verdad. Tienen que ir por su
# nombre entero y no por `endswith("DistributeResources_GameAction")`, que era
# lo que habia: con esa terminacion cuadran tres acciones distintas y una de
# ellas es «Ano Productivo»:
#
#     CatanBase_DistributeResources_GameAction                  2345   produccion
#     CatanBase_StartPhase_DistributeResources_GameAction        180   colocacion
#     CatanBase_DevCard_Inventor_DistributeResources_GameAction   30   Ano Productivo
#
# La tercera no reparte por tirada: le da dos cartas a eleccion a UN jugador.
# Pero `_reparto` no lo sabia y volvia a calcular la produccion de la ULTIMA
# tirada, con lo que la apuntaba dos veces -- y los bloqueos del ladron
# tambien. Medido el 26 de agosto: 17 repartos duplicados y 34 cartas
# fantasma en las partidas 3, 4, 6 y 8.
#
# Lo encontro la deduccion de la produccion desde el tablero (db/deducir.py):
# cuadraba con el mod en 5 partidas de 9, y las 4 que fallaban fallaban por
# esto exactamente, carta por carta.
#
# Las dos cartas del Ano Productivo NO se apuntan: el mod manda la accion con
# el detalle vacio, asi que no hay forma de saber que recursos eligio. Se
# quedan sin registrar, que es mejor que registrarlas mal.
_REPARTOS_DE_VERDAD = frozenset((
    "CatanBase_DistributeResources_GameAction",
    "CatanBase_StartPhase_DistributeResources_GameAction",
))


# Las acciones que el importador ya sabe que existen y NO le hacen falta.
#
# Sin esta lista no se puede avisar de nada: el `if/elif` de `paso` entiende
# diez terminaciones y el juego manda treinta y cinco, asi que «lo que no
# entiendo» sin filtrar seria una partida normal entera y el aviso no diria
# nada. Con la lista, lo que queda fuera es lo que de verdad no se ha visto
# nunca -- que es justo lo que va a pasar el dia que se juegue a una
# expansion.
#
# NO esta escrita a mano: son las 35 acciones que aparecen en las doce
# grabaciones del Catan basico, menos las diez que `paso` atiende. Si manana
# sale una nueva del basico tambien saltara el aviso, y eso es lo que se
# quiere: preferimos enterarnos.
#
# Que una accion este aqui no quiere decir que sobre. Quiere decir que hoy no
# deja una fila: el turno y el reparto inicial se siguen por otro camino, y
# barajar el mazo o repartir el inventario no dejan nada que contar.
# De que familias sabe algo el importador. NADA MAS que estas dos.
#
# Hace falta porque el reparto de `paso` va por TERMINACION -- `endswith` --
# y las expansiones repiten los mismos finales. Sin esta puerta, ocho
# acciones de otros juegos entraban por la puerta de atras:
#
#   CatanCak_RollDice_GameAction        Ciudades y Caballeros
#   CatanInka_Robber_Move_GameAction    El ascenso de los incas
#   CatanBigGame_RollDice_GameAction    el modo multitudinario
#   RivalsBase_RollDice_GameAction      Rivals for Catan, que ni es este juego
#   ... y cuatro mas
#
# Y no es inofensivo: en Ciudades y Caballeros se tiran TRES dados -- los dos
# de siempre y el de sucesos -- asi que `dados[0] + dados[1]` daria un numero
# que parece una tirada normal y no lo es. En Rivals los dados son otra cosa
# entera. La partida entraria a medias, con tiradas creibles y sin nada de la
# expansion: el mismo fallo callado que el ladron de la partida 11.
#
# Asi que si no es del basico, no se procesa: se cuenta como desconocida y se
# dice. Las dos familias salen de las doce grabaciones, donde no hay una sola
# accion que no empiece por una de ellas (27.075 y 3.197).
_FAMILIAS_QUE_ENTIENDO = ("CatanBase_", "CatanTrade_")

_YA_SE_QUE_ESTAN = frozenset((
    "CatanBase_BuildCity_GameAction",
    "CatanBase_BuildFreeRoad_GameAction",
    "CatanBase_BuildRoad_GameAction",
    "CatanBase_BuildSettlement_GameAction",
    "CatanBase_CheckLargestArmy_GameAction",
    "CatanBase_CheckLongestRoad_GameAction",
    "CatanBase_DevCard_Inventor_DistributeResources_GameAction",
    "CatanBase_DevCard_Inventor_SelectResources_GameAction",
    "CatanBase_EndTurn_GameAction",
    "CatanBase_NextPlayer_GameAction",
    "CatanBase_NextPlayer_SixPlayer_GameAction",
    "CatanBase_Robber_HandOverResourcesToRobber_GameAction",
    "CatanBase_SelectPlayerToRob_GameAction",
    "CatanBase_SetupPlayerInventory_GameAction",
    "CatanBase_ShuffleDevCardStack_GameAction",
    "CatanBase_ShuffleDiceStack_GameAction",
    "CatanBase_StartGame_GameAction",
    "CatanBase_StartPhase_BuildRoad_GameAction",
    "CatanBase_StartPhase_BuildSettlement_GameAction",
    "CatanBase_StartPhase_NextPlayer_GameAction",
    "CatanTrade_CancelTrade_GameAction",
))


class _Recorrido:
    """Va evento a evento y escribe lo que ha cambiado.

    Los edificios y las carreteras NO se sacan del nombre de la acción sino
    de comparar el tablero con el del evento anterior. Es más fiable: el
    dueño viene dentro de la pieza (`de_jugador`), así que no hay que
    suponer que la construyó quien tenía el turno -- que con las carreteras
    gratis de la carta de desarrollo no siempre es verdad."""

    def __init__(self, conn, game_id, alin, tablero, tile_id, pid_de, contador):
        self.conn = conn
        self.game_id = game_id
        self.alin = alin
        self.tablero = tablero
        self.tile_id = tile_id
        self.pid = pid_de
        self.n = contador

        self.vertices = {}       # vid -> (tipo, building_id)
        self.aristas = {}        # eid -> road_id
        self.orden_poblados = collections.defaultdict(list)  # jugador -> [vid]
        self.orden_de_salida = []    # jugadores por orden de colocar el 1er poblado
        self.cuentas = {}        # jugador -> dict de estadísticas
        self.ultima_tirada = None
        self.valor_tirada = None
        self.ladron = None
        # Acciones que no entiendo y que ademas no habia visto nunca. La
        # cuenta viaja hasta `pegas`, con la partida.
        self.desconocidas = collections.Counter()
        self.quien_movio_ladron = None
        self.ultimo_movimiento = None   # para enlazar el robo con su jugada
        self.turno_abierto = None   # (turn_id, turno, jugador)
        self.ultimo_ms = None
        self.caballero_pendiente = None  # un caballero jugado y aún sin mover
                                         # el ladrón: el siguiente movimiento
                                         # es suyo
        self.ultima_carta = None    # (play_id, jugador_mod, turno) de la última
                                    # carta de desarrollo jugada, para poder
                                    # engancharle lo que diga la acción que
                                    # viene detrás

    # -- utilidades -----------------------------------------------------
    def _p(self, jugador_mod):
        return self.pid.get(jugador_mod)

    def _hex_del_ladron(self, ev):
        lad = ev.get("ladron")
        if not lad:
            return None
        hexes = _hexes_de(lad, self.alin)
        return hexes[0] if hexes else None

    def _diff(self, ev, campo):
        """Quién ha subido esa estadística desde el evento anterior."""
        salida = []
        for j in ev.get("jugadores") or []:
            ahora = (j.get("cuentas") or {}).get(campo)
            antes = (self.cuentas.get(j["id"]) or {}).get(campo)
            if ahora is None:
                continue
            if antes is not None and ahora > antes:
                salida.append((j["id"], ahora - antes))
        return salida

    # -- el paso --------------------------------------------------------
    def paso(self, ev, siguientes):
        accion = ev.get("accion") or ""
        cuando = _iso(ev.get("reloj_ms"))
        turno = ev.get("turno")
        # `jugador_activo` es el del turno; `accion_de` es quien hizo ESTA
        # acción, y lo trae el estado de la acción. Se prefiere el segundo
        # cuando está: el primero sale -1 en tres de las cinco copias que el
        # juego escribe de cada acción, y aunque aquí siempre llega la
        # primera, un dato que no depende de haber acertado con la copia es
        # mejor dato.
        activo = ev.get("jugador_activo")
        de_la_accion = ev.get("accion_de")
        if de_la_accion is not None and de_la_accion >= 0:
            activo = de_la_accion
        self.ultimo_ms = ev.get("reloj_ms")

        self._turno(ev, turno, activo, cuando)
        self._piezas(ev, turno, cuando)

        if not accion.startswith(_FAMILIAS_QUE_ENTIENDO):
            # De otro juego o de una expansion. Ni se intenta: ver arriba.
            self.desconocidas[accion] += 1
        elif accion.endswith("RollDice_GameAction"):
            self._tirada(ev, turno, activo, cuando)
        elif accion in _REPARTOS_DE_VERDAD:
            self._reparto(ev, accion, activo, cuando)
        elif accion.endswith("Robber_Move_GameAction"):
            self._ladron(ev, turno, activo, cuando)
        elif accion.endswith("RobPlayer_GameAction"):
            self._robo(ev, activo, cuando)
        elif accion.endswith("BuyDevelopmentCard_GameAction"):
            self._apunta("dev_card_purchases", activo, turno, cuando)
        elif accion.endswith("PlayDevelopmentCard_GameAction"):
            self._carta(ev, activo, turno, cuando, siguientes)
        elif accion.endswith("Monopoly_SelectResourceType_GameAction"):
            self._monopolio_elige(ev, activo, turno)
        elif accion.endswith("Monopoly_HandOverResourcesToPlayer_GameAction"):
            self._monopolio_reparte(ev, activo, turno, cuando)
        # El mismo trato con dos nombres. En mesa de 5-6 el juego usa
        # acciones aparte -- `...SixPlayer` y la de la ronda compartida de la
        # ampliacion, `...SixPlayerExtraordinaryRound` -- con exactamente el
        # mismo contenido dentro.
        #
        # Estaban en `_YA_SE_QUE_ESTAN`, asi que ni se importaban ni saltaba
        # el aviso de accion desconocida. Las dos partidas de mesa grande
        # entraron con CERO tratos entre personas, con sus tiradas y sus
        # edificios en su sitio y con toda la pinta de estar completas.
        elif accion.endswith(("CatanTrade_Bank_GameAction",
                              "CatanTrade_BankSixPlayerExtraordinaryRound"
                              "_GameAction")):
            self._comercio_con_banco(ev, activo, cuando)
        elif accion.endswith(("CatanTrade_FinishTrade_GameAction",
                              "CatanTrade_FinishTradeSixPlayer_GameAction")):
            self._comercio_entre(ev, activo, cuando)
        elif accion.endswith("WinGame_GameAction"):
            self._final(ev, activo, cuando)
        elif accion not in _YA_SE_QUE_ESTAN:
            # Ni la entiendo ni la conozco. Antes esto era el final de un
            # `if/elif` SIN `else` y la accion desaparecia sin dejar rastro:
            # una partida de Navegantes entraria con sus tiradas y sus
            # edificios, sin un solo barco, y con toda la pinta de estar
            # completa. Contarlas es lo unico que separa «no lo soporta» de
            # «lo soporta mal».
            self.desconocidas[accion] += 1

        self.cuentas = {j["id"]: dict(j.get("cuentas") or {})
                        for j in (ev.get("jugadores") or [])}

    # -- cada cosa ------------------------------------------------------
    def _turno(self, ev, turno, activo, cuando):
        """Un turno empieza cuando el juego dice que empieza.

        Antes se abría uno cada vez que cambiaba la pareja (turno, jugador)
        y salían 126 turnos para 60 tiradas. El motivo: `turno` y
        `jugador_activo` NO cambian a la vez, se alternan -- la secuencia
        real es (1,3), (1,0), (2,0), (2,1), (3,1)... -- así que cada turno
        de verdad cambiaba la pareja dos veces y se contaba dos veces.

        No hay que deducirlo: el juego lanza NextPlayer al pasar el turno.
        En esa misma partida hay 67 (59 normales y 8 de la colocación
        inicial), que es exactamente lo que hubo con sus 60 tiradas."""
        accion = ev.get("accion") or ""
        primero = self.turno_abierto is None and self._p(activo) is not None
        if not primero and "NextPlayer" not in accion:
            return
        pid = self._p(activo)
        if pid is None:
            return
        if self.turno_abierto:
            self.conn.execute("UPDATE turns SET end_ts=? WHERE turn_id=?",
                              (cuando, self.turno_abierto[0]))
        fase = "setup" if "StartPhase" in accion else "normal"
        cur = self.conn.execute(
            "INSERT INTO turns (game_id, player_id, turn_number, phase, start_ts) "
            "VALUES (?,?,?,?,?)", (self.game_id, pid, turno, fase, cuando))
        self.turno_abierto = (cur.lastrowid, turno, activo)
        self.n["turnos"] += 1

    def _piezas(self, ev, turno, cuando):
        for pieza in ev.get("edificios") or []:
            tipo = PIEZA.get(pieza.get("tipo"))
            if tipo not in ("poblado", "ciudad"):
                continue
            sitio = self.alin.sitio(pieza.get("donde"))
            if not sitio or sitio[0] != "vertice":
                continue
            vid = sitio[1]
            antes = self.vertices.get(vid)
            if antes is None:
                bid = self._nuevo_edificio(pieza, tipo, vid, turno, cuando)
                self.vertices[vid] = (tipo, bid)
                if tipo == "poblado":
                    self.orden_poblados[pieza["de_jugador"]].append(vid)
                    if pieza["de_jugador"] not in self.orden_de_salida:
                        self.orden_de_salida.append(pieza["de_jugador"])
            elif antes[0] != tipo and tipo == "ciudad":
                # Una ciudad nunca se construye de cero: es la mejora de un
                # poblado en ese mismo vértice. Se cambia la fila en vez de
                # añadir otra, si no el jugador tendría los dos a la vez.
                #
                # Pero `turn_number` y `timestamp` NO se tocan: son cuándo se
                # puso el poblado, y eso no ha dejado de ser verdad porque
                # luego creciera. Antes se sobrescribían, y con ellos se iba
                # el único rastro de cuándo se ocupó ese vértice: elGato salía
                # sin tercer poblado en una partida en la que construyó tres,
                # porque los había mejorado todos.
                self.conn.execute(
                    "UPDATE buildings SET type='ciudad', upgraded_turn=?, "
                    "upgraded_at=? WHERE building_id=?",
                    (turno, cuando, antes[1]))
                self.vertices[vid] = (tipo, antes[1])
                self.n["ciudades"] += 1

        for pieza in ev.get("carreteras") or []:
            sitio = self.alin.sitio(pieza.get("donde"))
            if not sitio or sitio[0] != "arista":
                continue
            eid = sitio[1]
            if eid in self.aristas:
                continue
            pid = self._p(pieza["de_jugador"])
            if pid is None:
                continue
            clave = self._clave(pieza, eid, "a")
            cur = self.conn.execute(
                "INSERT INTO roads (game_id, player_id, edge_key, turn_number, "
                "timestamp) VALUES (?,?,?,?,?)",
                (self.game_id, pid, clave, turno, cuando))
            self.aristas[eid] = cur.lastrowid
            self.n["carreteras"] += 1

    def _clave(self, pieza, sid, prefijo):
        """El mismo formato que usa el tracker (main._clave_de_sitio): los
        tile_id que toca y la posición exacta en el tablero ideal.

        La posición hace falta igual que allí: los vértices y aristas de
        fuera de las puntas del tablero no tocan ninguna otra casilla, así
        que la lista de tile_id sola los confunde entre sí."""
        hexes = _hexes_de(pieza, self.alin)
        ids = sorted(self.tile_id[i] for i in hexes)
        xs = ys = 0.0
        caras = [c for c in (pieza.get("donde") or {}).get("casillas") or []
                 if c is not None]
        for c in caras:
            q, r = self.alin.cara(c)
            x, y = axial_to_pixel(q, r, 1.0)
            xs += x
            ys += y
        n = max(1, len(caras))
        return ",".join(str(t) for t in ids) + "|%.3f,%.3f" % (xs / n, ys / n)

    def _nuevo_edificio(self, pieza, tipo, vid, turno, cuando):
        pid = self._p(pieza["de_jugador"])
        # Las tres casillas del vértice, tal cual vienen. Es lo que se cruza
        # con la arista de los puertos; `vertex_key` no sirve porque mezcla
        # tile_id con un centro en píxeles.
        caras = [c for c in ((pieza.get("donde") or {}).get("casillas") or [])
                 if c is not None]
        cur = self.conn.execute(
            "INSERT INTO buildings (game_id, player_id, type, turn_number, "
            "timestamp, vertex_key, faces_json) VALUES (?,?,?,?,?,?,?)",
            (self.game_id, pid, tipo, turno, cuando,
             self._clave(pieza, vid, "v"), json.dumps(caras)))
        bid = cur.lastrowid
        for i in _hexes_de(pieza, self.alin):
            self.conn.execute(
                "INSERT OR IGNORE INTO building_tiles (building_id, tile_id) "
                "VALUES (?,?)", (bid, self.tile_id[i]))
        self.n["poblados" if tipo == "poblado" else "ciudades"] += 1
        return bid

    def _tirada(self, ev, turno, activo, cuando):
        dados = ev.get("dados") or []
        if len(dados) < 2:
            return
        pid = self._p(activo)
        if pid is None:
            return
        d1, d2 = int(dados[0]), int(dados[1])
        # Se acabó la ventana del caballero. Si se jugó uno y NO movió el
        # ladrón -- pasa: si lo dejas donde estaba, el juego no manda ningún
        # movimiento -- la bandera se quedaba puesta y el siguiente
        # movimiento, que ya sería del 7, salía como del caballero. Un caso
        # raro que se apunta mal y no se nota: los totales siguen cuadrando.
        self.caballero_pendiente = None
        cur = self.conn.execute(
            "INSERT INTO rolls (game_id, player_id, turn_number, value, die1, "
            "die2, timestamp) VALUES (?,?,?,?,?,?,?)",
            (self.game_id, pid, turno, d1 + d2, d1, d2, cuando))
        self.ultima_tirada = cur.lastrowid
        self.valor_tirada = d1 + d2
        self.n["tiradas"] += 1

    def _reparto(self, ev, accion, activo, cuando):
        hex_ladron = self._hex_del_ladron(ev)
        if "StartPhase" in accion:
            # Reparto de la colocación inicial: lo da el SEGUNDO poblado del
            # jugador que está colocando, no la tirada.
            vids = self.orden_poblados.get(activo) or []
            if not vids:
                return
            ultimo_vid = vids[-1]
            for pieza in ev.get("edificios") or []:
                sitio = self.alin.sitio(pieza.get("donde"))
                if sitio and sitio[1] == ultimo_vid and sitio[0] == "vertice":
                    self._guardar_ganancias(
                        produccion_inicial(pieza, self.tablero, self.alin),
                        "inicial", None, cuando)
                    break
            return

        if self.valor_tirada is None:
            return
        gana, bloqueado = produccion(
            ev.get("edificios") or [], self.tablero, self.alin,
            self.valor_tirada, hex_ladron)
        self._guardar_ganancias(gana, "produccion", self.ultima_tirada, cuando)
        for jugador, i, tipo, cantidad in bloqueado:
            pid = self._p(jugador)
            if pid is None or self.ultima_tirada is None:
                continue
            self.conn.execute(
                "INSERT INTO robber_blocks (game_id, roll_id, tile_id, blocker_id, "
                "victim_id, building_type, amount, timestamp) VALUES (?,?,?,?,?,?,?,?)",
                (self.game_id, self.ultima_tirada, self.tile_id[i],
                 self._p(self.quien_movio_ladron), pid, tipo, cantidad, cuando))
            self.n["bloqueos"] += 1

    def _guardar_ganancias(self, ganancias, fuente, roll_id, cuando):
        for jugador, recurso, cantidad in ganancias:
            pid = self._p(jugador)
            if pid is None:
                continue
            self.conn.execute(
                "INSERT INTO resource_gains (game_id, player_id, roll_id, "
                "resource, amount, source, timestamp) VALUES (?,?,?,?,?,?,?)",
                (self.game_id, pid, roll_id, recurso, cantidad, fuente, cuando))
            self.n["recursos"] += cantidad

    def _ladron(self, ev, turno, activo, cuando):
        i = self._hex_del_ladron(ev)
        if i is None:
            # El juego ha movido el ladron y no sabemos adonde. Se cuenta, que
            # es lo que faltaba: antes se volvia en silencio y la partida
            # entraba entera y creible, con la produccion calculada como si el
            # ladron no existiera.
            self.n["ladron sin sitio"] += 1
            return
        if i == self.ladron:
            return
        self.ladron = i
        self.quien_movio_ladron = activo
        pid = self._p(activo)
        if pid is None:
            return
        # El primer movimiento después de un caballero es el del caballero, y
        # lo consume. Así, jugar un caballero y luego sacar un 7 en el mismo
        # turno sale como lo que es: uno de cada.
        if self.caballero_pendiente == activo:
            porque = "caballero"
            self.caballero_pendiente = None
        else:
            porque = "siete"
        cur = self.conn.execute(
            "INSERT INTO robber_moves (game_id, player_id, tile_id, turn_number, "
            "timestamp, cause) VALUES (?,?,?,?,?,?)",
            (self.game_id, pid, self.tile_id[i], turno, cuando, porque))
        self.ultimo_movimiento = cur.lastrowid
        self.n["ladron"] += 1

    def _robo(self, ev, activo, cuando):
        # A quién. Desde que el mod lee el estado de la acción viene escrito
        # en `detalle.robado_a`; antes había que deducirlo restando
        # `RobbedCount`, que también funciona pero se calla si suben dos a la
        # vez. Se mantienen los dos por las grabaciones viejas.
        ladron_pid = self._p(activo)
        if ladron_pid is None:
            return
        dicho = (ev.get("detalle") or {}).get("robado_a")
        if dicho is not None and dicho >= 0:
            victima_pid = self._p(dicho)
        else:
            victimas = self._diff(ev, "RobbedCount")
            if len(victimas) != 1:
                return
            victima_pid = self._p(victimas[0][0])
        if victima_pid is None or victima_pid == ladron_pid:
            return
        # resource a NULL a propósito: qué carta se llevó es información
        # oculta y el mod no la lee. Vale más el hueco que una estimación.
        #
        # `move_id` enlaza el robo con el movimiento del ladrón que lo
        # provocó. Sin él no se puede preguntar "cuando puso el ladrón AQUÍ,
        # ¿a quién robó?", que es media tabla `robber_moves` sin poder cruzar.
        self.conn.execute(
            "INSERT INTO steals (game_id, move_id, thief_id, victim_id, resource, "
            "timestamp) VALUES (?,?,?,?,?,?)",
            (self.game_id, self.ultimo_movimiento, ladron_pid, victima_pid,
             None, cuando))
        self.n["robos"] += 1

    def _apunta(self, tabla, activo, turno, cuando):
        pid = self._p(activo)
        if pid is None:
            return
        self.conn.execute(
            "INSERT INTO %s (game_id, player_id, turn_number, timestamp) "
            "VALUES (?,?,?,?)" % tabla, (self.game_id, pid, turno, cuando))
        self.n["cartas" if "purchases" in tabla else tabla] += 1

    # Qué carta era, según lo que el juego hace justo después de jugarla.
    # Cada una arrastra su propia secuencia y no se parecen entre sí:
    #
    #   Caballero     -> CheckLargestArmy, Robber_Move, SelectPlayerToRob...
    #   Monopolio     -> DevCard_Monopoly_SelectResourceType...
    #   Invención     -> DevCard_Inventor_SelectResources...
    #   Carreteras    -> BuildFreeRoad, CheckLongestRoad, BuildFreeRoad...
    #
    # El primer intento fue mirar si subía `KnightsBuild`, que para eso está
    # la estadística. No sube NUNCA: medido sobre la partida de las 16:27,
    # ese contador se queda a cero toda la partida aunque se jueguen siete
    # caballeros. El juego no lo usa en el Catan básico. Por eso 22 de las
    # 32 cartas se quedaban en "no se sabe".
    _POR_LO_QUE_VIENE_DESPUES = (
        ("CheckLargestArmy", "Caballero"),
        ("Monopoly", "Monopolio"),
        ("Inventor", "Invencion"),
        ("BuildFreeRoad", "Construccion de carreteras"),
    )

    # Como llama el juego a cada carta de desarrollo.
    _CARTAS_DEL_JUEGO = {
        "Knight": "Caballero",
        "Monopoly": "Monopolio",
        "YearOfPlenty": "Invencion",
        "Invention": "Invencion",
        "RoadBuilding": "Construccion de carreteras",
        "VictoryPoint": "Punto de victoria",
    }

    def _carta(self, ev, activo, turno, cuando, siguientes):
        # Si el mod capturó el estado de la acción, la carta viene con su
        # nombre y no hay nada que deducir. Si no, se mira lo que el juego
        # hace después, que es lo de siempre.
        tipo = None
        dicho = ((ev.get("detalle") or {}).get("carta") or {}).get("desarrollo")
        if dicho:
            tipo = self._CARTAS_DEL_JUEGO.get(dicho, dicho)
        if not tipo:
            for s in siguientes:
                a = s.get("accion") or ""
                for marca, nombre in self._POR_LO_QUE_VIENE_DESPUES:
                    if marca in a:
                        tipo = nombre
                        break
                if tipo:
                    break
        pid = self._p(activo)
        if pid is None:
            return
        cur = self.conn.execute(
            "INSERT INTO dev_card_plays (game_id, player_id, card_type, "
            "turn_number, timestamp) VALUES (?,?,?,?,?)",
            (self.game_id, pid, tipo, turno, cuando))
        self.ultima_carta = (cur.lastrowid, activo, turno)
        if tipo == "Caballero":
            self.caballero_pendiente = activo
        self.n["cartas jugadas"] += 1

    def _monopolio_elige(self, ev, activo, turno):
        """Qué recurso pidió el monopolio.

        No viene con la carta: el juego apunta «juega una carta de desarrollo»
        sin decir cuál y manda el recurso en la acción de después. Por eso hay
        que engancharlo a la jugada anterior.

        Se exige que esa jugada sea del MISMO jugador y del MISMO turno. Sin
        esa condición, un monopolio cuya carta no se llegó a apuntar -- pasa
        si la grabación empieza a media partida -- le pegaría su recurso a la
        carta de otro, y quedaría un dato falso con toda la pinta de ser
        bueno."""
        recurso = (ev.get("detalle") or {}).get("recurso_elegido")
        if not recurso or self.ultima_carta is None:
            return
        play_id, quien, turno_carta = self.ultima_carta
        if quien != activo or turno_carta != turno:
            return
        self.conn.execute(
            "UPDATE dev_card_plays SET resource=?, card_type='Monopolio' "
            "WHERE play_id=?",
            (TERRENO_DEL_JUEGO.get(recurso, recurso), play_id))
        self.n["monopolios"] += 1

    def _monopolio_reparte(self, ev, activo, turno, cuando):
        """Lo que soltó cada jugador. Una fila por víctima.

        El mod lo manda ya masticado, porque su forma está leída del
        Assembly-CSharp.dll y no adivinada:

            {"recurso": "Ore",
             "de": [{"jugador": 0, "cartas": [{"recurso":"Ore","cantidad":3}]},
                    ...],
             "crudo": {...}}

        Al que lo tira no se le apunta fila: un monopolio no te quita cartas a
        ti mismo, y si el diccionario trae su entrada será el total que recibe,
        que es otra cosa y sumaría dos veces.

        `raw_json` se guarda igualmente mientras el mod siga mandando `crudo`.
        Es la red por si algún campo viene relleno de otra manera de lo que
        dice el .dll -- pasó con los puertos, donde `HarborType` existía y
        llegaba vacío."""
        det = (ev.get("detalle") or {}).get("monopolio")
        pid = self._p(activo)
        if not det or pid is None:
            return
        play_id = None
        if self.ultima_carta and self.ultima_carta[1] == activo:
            play_id = self.ultima_carta[0]
        crudo = json.dumps(det.get("crudo"), ensure_ascii=False) \
            if det.get("crudo") is not None else None
        recurso_juego = det.get("recurso") or ""
        recurso = TERRENO_DEL_JUEGO.get(recurso_juego, recurso_juego) or None

        filas = 0
        for trozo in det.get("de") or []:
            victima = self._p(trozo.get("jugador"))
            if victima is None or victima == pid:
                continue
            # Un monopolio mueve un solo recurso, pero se suma la lista entera
            # en vez de coger la primera carta: si algún día trae más de una
            # entrada, quedarse con una daría un número menor y creíble.
            cuantas = sum(c.get("cantidad") or 0
                          for c in (trozo.get("cartas") or []))
            self.conn.execute(
                "INSERT INTO monopoly_takes (game_id, play_id, turn_number, "
                "taker_id, victim_id, resource, amount, raw_json, timestamp) "
                "VALUES (?,?,?,?,?,?,?,?,?)",
                (self.game_id, play_id, turno, pid, victima, recurso,
                 cuantas, crudo, cuando))
            filas += 1

        if filas:
            # LOS QUE NO SUELTAN NADA TAMBIEN SON UN DATO, y valen 0, no NULL.
            # El juego sólo mete en el diccionario a quien entrega algo, así
            # que el que falta es el que no tenía ese recurso -- y eso se sabe,
            # no se ignora. Sin esta parte, la partida 7 enseñaba «no se sabe»
            # para TheClonne en el monopolio del turno 15 teniendo el reparto
            # entero delante, igual que las partidas viejas que no lo traen.
            # Dos cosas distintas con la misma cara.
            for victima in set(self.pid.values()):
                if victima == pid:
                    continue
                self.conn.execute(
                    "INSERT INTO monopoly_takes (game_id, play_id, "
                    "turn_number, taker_id, victim_id, resource, amount, "
                    "timestamp) SELECT ?,?,?,?,?,?,0,? WHERE NOT EXISTS "
                    "(SELECT 1 FROM monopoly_takes t WHERE t.play_id IS ? "
                    " AND t.victim_id = ? AND t.turn_number = ?)",
                    (self.game_id, play_id, turno, pid, victima, recurso,
                     cuando, play_id, victima, turno))
        else:
            # Llegó el reparto pero sin nadie dentro. Se deja constancia con
            # el crudo al lado: sin esta fila, una lectura que falle es
            # indistinguible de un monopolio que no se jugó.
            self.conn.execute(
                "INSERT INTO monopoly_takes (game_id, play_id, turn_number, "
                "taker_id, resource, raw_json, timestamp) VALUES (?,?,?,?,?,?,?)",
                (self.game_id, play_id, turno, pid, recurso, crudo, cuando))
        self.n["repartos de monopolio"] += 1

    def _comercio(self, a, b, cuando, da=None, pide=None):
        pid_a = self._p(a)
        if pid_a is None:
            return
        self.conn.execute(
            "INSERT INTO trades (game_id, player_a_id, player_b_id, gave_json, "
            "received_json, timestamp) VALUES (?,?,?,?,?,?)",
            (self.game_id, pid_a, self._p(b) if b is not None else None,
             _cartas_json(da), _cartas_json(pide), cuando))
        self.n["comercios"] += 1
        if da is not None or pide is not None:
            self.n["comercios con detalle"] += 1

    @staticmethod
    def _cartas_del_comercio(ev):
        """El bloque de detalle que de verdad trae las cartas.

        El juego rellena DOS sitios y no siempre los dos: un cambio con el
        banco llega con `comercio` (AsTradeFinish) *y* `comercio_banco`
        (AsTradeInit), y en 4 de los 15 de una partida real el segundo venía
        con las listas vacías. Leyendo solo ese, esos 4 se guardaban sin
        cartas -- y el informe decía «25 de 29 comercios con detalle» cuando
        la grabación tenía los 29.

        Así que no se elige por el nombre del campo sino por cuál tiene algo
        dentro, que es lo que se quería en realidad."""
        d = ev.get("detalle") or {}
        for clave in ("comercio", "comercio_banco"):
            c = d.get(clave)
            if c and (c.get("da") or c.get("pide")):
                return c
        return d.get("comercio") or d.get("comercio_banco")

    def _comercio_entre(self, ev, activo, cuando):
        """Un comercio entre dos jugadores.

        Con `detalle` (grabaciones desde el 19/8 por la noche) viene todo
        escrito: quién ofreció, quién aceptó y qué cartas fueron en cada
        dirección. Sin él solo se puede saber QUE hubo comercio y entre
        quiénes, restando `SuccessfullTrades`. Se mantienen los dos caminos
        porque las grabaciones viejas no se pueden repetir."""
        c = self._cartas_del_comercio(ev)
        if c:
            otro = c.get("acepta")
            if c.get("banco_3a2") or c.get("banco_2a1") or otro is None or otro < 0:
                otro = None
            quien = c.get("ofrece")
            self._comercio(quien if quien is not None and quien >= 0 else activo,
                           otro, cuando, c.get("da"), c.get("pide"))
            return
        subieron = [j for j, _ in self._diff(ev, "SuccessfullTrades")]
        otro = None
        for j in subieron:
            if j != activo:
                otro = j
                break
        self._comercio(activo, otro, cuando)

    def _comercio_con_banco(self, ev, activo, cuando):
        # Aquí el otro lado es el banco siempre, así que solo hacen falta
        # las cartas -- pero da igual en cuál de los dos bloques vengan.
        c = self._cartas_del_comercio(ev)
        quien = (c or {}).get("ofrece")
        self._comercio(quien if quien is not None and quien >= 0 else activo,
                       None, cuando,
                       (c or {}).get("da"), (c or {}).get("pide"))

    def _final(self, ev, activo, cuando):
        jugadores = ev.get("jugadores") or []
        # `puntos_finales` son los TOTALES, y el mod solo los escribe en esta
        # acción -- cuando la partida ya ha acabado y la pantalla de
        # resultados los enseña, o sea cuando ya no son secreto de nadie.
        # Son los buenos: los visibles dejan fuera las cartas de punto de
        # victoria que los perdedores llevaran tapadas, así que con ellos
        # cualquier media de puntos sale corta para todos menos el ganador.
        # Y los VISIBLES del mismo instante, que no son un duplicado: son los
        # que la partida enseniaba en el panel de cada jugador. La diferencia
        # entre los dos es, exactamente, las cartas de punto de victoria que
        # llevaba tapadas -- sin mirar ni una carta, porque los dos numeros
        # los da el juego en la pantalla de resultados.
        #
        # Es el mismo dato al que se llega restando edificios y premios de los
        # totales, pero por un camino que no pasa por ahi. Tener los dos
        # permite que se comprueben entre ellos (ver db/pruebas.py).
        puntos, visibles = {}, {}
        for j in jugadores:
            v = j.get("puntos_finales")
            puntos[j["id"]] = v if v is not None else j.get("puntos_visibles")
            visibles[j["id"]] = j.get("puntos_visibles")
        # Las grabaciones del 18/8 son de antes de que el mod leyera los
        # puntos, y traen null. Entonces NO hay clasificación: se sabe quién
        # ganó y nada más. Poner ceros y ordenar por ellos daba un segundo,
        # un tercero y un cuarto inventados, que es peor que no tenerlos.
        hay_puntos = any(v is not None for v in puntos.values())
        # El que gana lo hace en su turno, así que el activo es el ganador.
        if hay_puntos:
            orden = sorted(puntos, key=lambda j: (j != activo, -(puntos[j] or 0)))
        else:
            orden = [activo] if activo in puntos else []
        for puesto, j in enumerate(orden, 1):
            pid = self._p(j)
            if pid is None:
                continue
            self.conn.execute(
                "UPDATE players SET final_rank=?, final_points=?, "
                "final_points_visible=? WHERE player_id=?",
                (puesto, puntos[j], visibles.get(j), pid))
        # Quién se quedó la carretera más larga y el mayor ejército. El mod
        # los da como índice de jugador, o -1 si no los tiene nadie. Se
        # apuntan aquí y no antes porque lo que interesa es cómo acabaron:
        # durante la partida cambian de mano y eso ya está en el histórico.
        for campo, columna in (("camino_mas_largo", "longest_road"),
                               ("mayor_ejercito", "largest_army")):
            quien = ev.get(campo)
            if quien is None:
                continue          # grabación vieja: mejor NULL que un 0 falso
            for j in puntos:
                pid = self._p(j)
                if pid is not None:
                    self.conn.execute(
                        "UPDATE players SET %s=? WHERE player_id=?" % columna,
                        (1 if j == quien else 0, pid))
        ganador = self._p(activo)
        if ganador is not None:
            nombre = self.conn.execute(
                "SELECT name FROM players WHERE player_id=?", (ganador,)).fetchone()
            self.conn.execute("UPDATE games SET winner=? WHERE game_id=?",
                              (nombre[0] if nombre else None, self.game_id))
        self.n["final"] += 1

    def cerrar(self):
        if self.turno_abierto:
            self.conn.execute("UPDATE turns SET end_ts=? WHERE turn_id=?",
                              (_iso(self.ultimo_ms), self.turno_abierto[0]))
        self._orden_de_turno()
        self.conn.commit()

    def _orden_de_turno(self):
        """Quién empezó, quién fue segundo, etc.

        Sale del orden en que cada uno coloca su PRIMER poblado, que es la
        verdad observada y no hay que fiarse de nada.

        Antes esto se sacaba de `hueco` (SlotIdx), que suena a lo mismo y no
        lo es: `hueco` es el asiento en la sala y sale siempre 0,1,2,3 --
        redundante con el id del jugador, cero información. El orden de turno
        ROTA cada partida. Comprobado sobre las 7 grabaciones que había: el
        orden real fue [3,0,1,2], [3,0,1,2], [3,0,1,2], [0,1,2,3], [1,2,3,0],
        [1,2,3,0] y [1,2,3,0]. O sea que `hueco` acertaba en UNA de siete, y
        por pura casualidad.

        No es un detalle cosmético: en Catan empezar el primero o el último
        cambia bastante, y con `turn_order` mal cualquier cuenta de «¿influye
        el orden?» habría salido mezclando a los cuatro."""
        for puesto, jugador in enumerate(self.orden_de_salida, 1):
            pid = self._p(jugador)
            if pid is None:
                continue
            self.conn.execute("UPDATE players SET turn_order=? WHERE player_id=?",
                              (puesto, pid))
        if self.orden_de_salida:
            self.n["orden de turno"] = len(self.orden_de_salida)


# --------------------------------------------------------------------------
# la línea de órdenes
# --------------------------------------------------------------------------

def mandar_quien(conn):
    filas = conn.execute(
        "SELECT network_id, display_name, is_bot, first_seen, last_seen "
        "FROM mod_identities ORDER BY is_bot, display_name").fetchall()
    if not filas:
        print("Todavía no hay ningún identificador. Importa una partida primero.")
        return
    print("%-40s %-16s %s" % ("identificador de la cuenta", "nombre", "partidas"))
    for red, nombre, es_bot, _pri, _ult in filas:
        n = conn.execute(
            "SELECT COUNT(*) FROM players p JOIN games g ON g.game_id=p.game_id "
            "WHERE g.source='mod' AND p.name=?", (nombre,)).fetchone()[0]
        marca = " (IA)" if es_bot else ""
        print("%-40s %-16s %d%s" % (red, nombre, n, marca))
    print()
    print("Para ponerle nombre a alguien:")
    print("  py mod_verdad/importar.py --llamar <identificador> Pedro")


def mandar_llamar(conn, red, nombre):
    fila = conn.execute(
        "SELECT display_name FROM mod_identities WHERE network_id=?", (red,)).fetchone()
    if fila is None:
        print("No conozco el identificador %s. Míralos con --quien." % red)
        return
    viejo = fila[0]
    if viejo == nombre:
        print("Ya se llamaba así.")
        return
    conn.execute("INSERT OR IGNORE INTO people (display_name) VALUES (?)", (nombre,))
    conn.execute("UPDATE mod_identities SET display_name=? WHERE network_id=?",
                 (nombre, red))
    # Y en las partidas ya importadas, que si no el cambio solo valdría para
    # las siguientes y el histórico quedaría partido en dos personas.
    n = conn.execute(
        "UPDATE players SET name=?, person_name=? WHERE person_name=? AND game_id IN "
        "(SELECT game_id FROM games WHERE source='mod')",
        (nombre, nombre, viejo)).rowcount
    conn.execute("UPDATE games SET winner=? WHERE winner=? AND source='mod'",
                 (nombre, viejo))
    # Y el nombre viejo se va, si no lo usa nadie. Era el provisional
    # (`jugador_4645eb8a`) y ya no significa nada; dejarlo ahí iba llenando
    # `people` de gente que no existe, uno por cada persona a la que se le
    # puso nombre. Las dos condiciones importan: `people` es destino de una
    # clave ajena desde `players.person_name`, así que borrar uno que todavía
    # se use rompería el histórico.
    conn.execute(
        "DELETE FROM people WHERE display_name=? "
        "AND display_name NOT IN (SELECT display_name FROM mod_identities) "
        "AND NOT EXISTS (SELECT 1 FROM players WHERE person_name=?)",
        (viejo, viejo))
    conn.commit()
    print("%s ahora se llama '%s' (antes '%s'); %d partidas actualizadas."
          % (red, nombre, viejo, n))


def main():
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--carpeta", help="una partida concreta (nombre o ruta)")
    p.add_argument("--rehacer", action="store_true",
                   help="reimporta aunque ya estuviera")
    p.add_argument("--quien", action="store_true", help="quién es quién")
    p.add_argument("--llamar", nargs=2, metavar=("ID", "NOMBRE"),
                   help="ponle nombre a un identificador")
    args = p.parse_args()

    conn = sqlite3.connect(BASE)
    # Las claves ajenas están declaradas en el esquema desde el principio,
    # pero SQLite las trae APAGADAS y es una opción POR CONEXIÓN: el
    # `PRAGMA foreign_keys = ON` de `db/schema.sql` sólo valió para la
    # conexión que creó las tablas, hace meses. O sea que las cuarenta y pico
    # referencias eran documentación, no una comprobación -- y el día que un
    # `player_id` no cuadrase, la fila entraría igual y la partida saldría
    # rara sin decir por qué.
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        crear_tablas(conn)
        if args.quien:
            mandar_quien(conn)
            return 0
        if args.llamar:
            mandar_llamar(conn, args.llamar[0], args.llamar[1])
            return 0

        todos = ficheros()
        if args.carpeta:
            pedido = nombre_de(args.carpeta)
            elegidas = [f for f in todos if nombre_de(f) == pedido]
            if not elegidas and os.path.isfile(args.carpeta):
                elegidas = [args.carpeta]
            if not elegidas:
                print("No encuentro '%s'. Las que hay:" % args.carpeta)
                for f in todos:
                    print("   %s" % nombre_de(f))
                return 1
        else:
            elegidas = todos
        if not elegidas:
            print("No hay ficheros del mod en %s" % (carpeta_de_verdad() or "?"))
            print("¿Has jugado alguna partida con el mod encendido?")
            return 1

        hechas = 0
        for ruta in elegidas:
            nombre = nombre_de(ruta)
            gid, detalle = importar(conn, ruta, rehacer=args.rehacer)
            if gid is None:
                print("  -  %-28s %s" % (nombre, detalle))
            else:
                hechas += 1
                print("  OK %-28s partida %d: %s" % (nombre, gid, detalle))
        print()
        print("%d partidas importadas." % hechas)

        # LAS VISTAS SE REHACEN AQUI, SIEMPRE. No es un capricho de limpieza:
        # las 28 vistas viven DENTRO del fichero .db, no en el codigo.
        # `db/vistas.py` es lo que genera los CREATE VIEW, y el resultado se
        # queda guardado en la base de quien lo use.
        #
        # Sin esto, quien se baje una version nueva del proyecto sigue
        # consultando las vistas VIEJAS que tiene guardadas, y no falla: si la
        # columna ya existia antes, ve numeros de la version anterior con el
        # codigo nuevo delante y nada se lo dice. Solo daba error cuando la
        # columna era nueva del todo.
        #
        # Es gratis y es seguro: una vista no guarda ni una fila -- es una
        # consulta con nombre -- asi que borrarlas y volver a crearlas no
        # toca un solo dato. Y este es el momento natural, porque es cuando
        # ya se esta escribiendo en la base.
        try:
            import db.vistas as _vistas
            _vistas.crear(conn)
        except Exception as e:
            # Que fallen las vistas no puede tirar una importacion que ya
            # esta guardada. Se dice y se sigue.
            print("Aviso: no se han podido rehacer las vistas (%s)." % e)
            print("       Hazlo a mano: py db/vistas.py --crear")
        sin_nombre = conn.execute(
            "SELECT network_id, display_name FROM mod_identities "
            "WHERE is_bot=0 AND display_name LIKE 'jugador\\_%' ESCAPE '\\'"
        ).fetchall()
        if sin_nombre:
            print()
            print("Hay %d persona(s) sin nombre de verdad:" % len(sin_nombre))
            for red, nombre in sin_nombre:
                print("  %s  (ahora '%s')" % (red, nombre))
            print("  py mod_verdad/importar.py --llamar <identificador> <nombre>")
        return 0
    finally:
        conn.close()


if __name__ == "__main__":
    sys.exit(main())
