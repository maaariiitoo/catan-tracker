# -*- coding: utf-8 -*-
"""Dice si el mod ha funcionado de verdad, y que ha apuntado.

Hace falta porque "el plugin compila" y "el plugin funciona" son dos cosas
distintas y hasta hoy solo estaba comprobada la primera: el .dll nunca se
habia llegado a ejecutar dentro del juego. Entre las dos hay bastantes
formas de fallar en silencio -- que el interruptor este apagado, que
BepInEx no llegue a cargar, que Harmony no enganche ninguna accion, o que
enganche y luego cada anotacion falle por un nombre de campo equivocado.
Ninguna de esas grita: simplemente no aparece el fichero, o aparece vacio.

Uso:
    py mod_verdad/comprobar.py

No toca nada; solo mira y cuenta lo que ve.
"""
import collections
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from mod_verdad.donde_esta_el_juego import carpeta_del_juego, carpeta_de_verdad

AQUI = os.path.dirname(os.path.abspath(__file__))
DATOS = os.path.join(AQUI, "datos")


def _lee(ruta):
    try:
        with open(ruta, "r", encoding="utf-8", errors="replace") as f:
            return f.read()
    except OSError:
        return ""


def _mas_nuevo(carpeta, extension):
    if not carpeta or not os.path.isdir(carpeta):
        return None
    ficheros = [os.path.join(carpeta, f) for f in os.listdir(carpeta)
                if f.endswith(extension)]
    return max(ficheros, key=os.path.getmtime) if ficheros else None


def _titulo(texto):
    print()
    print(texto)
    print("-" * len(texto))


def revisar_interruptor(juego):
    _titulo("1. el interruptor")
    cfg = os.path.join(juego, "doorstop_config.ini")
    if not os.path.isfile(cfg):
        print("   NO hay doorstop_config.ini: el mod no esta instalado.")
        return False
    encendido = re.search(r"(?m)^enabled\s*=\s*true", _lee(cfg)) is not None
    print("   %s" % ("ENCENDIDO" if encendido else "apagado"))
    plugin = os.path.join(juego, "BepInEx", "plugins", "CatanVerdad.dll")
    if os.path.isfile(plugin):
        mio = os.path.join(AQUI, "CatanVerdad.dll")
        aviso = ""
        if os.path.isfile(mio) and os.path.getmtime(mio) > os.path.getmtime(plugin) + 1:
            aviso = "   <- el de aqui es MAS NUEVO: falta compilar.ps1"
        print("   plugin puesto: si%s" % aviso)
    else:
        print("   plugin puesto: NO (falta BepInEx/plugins/CatanVerdad.dll)")
        encendido = False
    if not encendido:
        print()
        print("   -> .\\mod_verdad\\interruptor.ps1 on")
    return encendido


def revisar_bepinex(juego):
    """Lo que dice el registro de BepInEx. Es el unico sitio donde se ve si
    Harmony llego a enganchar las acciones: si engancha 0, el fichero de
    verdad sale vacio y no hay nada que diga por que."""
    _titulo("2. BepInEx arranco?")
    registro = os.path.join(juego, "BepInEx", "LogOutput.log")
    if not os.path.isfile(registro):
        print("   NO existe BepInEx/LogOutput.log.")
        print("   El juego no ha llegado a arrancar nunca con el mod puesto.")
        print()
        print("   -> abre Catan Universe una vez y vuelve a lanzar esto")
        return False

    texto = _lee(registro)
    # La fecha importa: BepInEx reescribe el log en cada arranque, asi que un
    # log viejo se lee igual de bien que uno nuevo y dice lo que pasaba ANTES
    # del ultimo cambio del plugin. Sin la fecha delante es facil dar por
    # roto algo que ya esta arreglado, o al reves.
    import datetime
    cuando = datetime.datetime.fromtimestamp(os.path.getmtime(registro))
    edad = (datetime.datetime.now() - cuando).total_seconds()
    aviso = ""
    if edad > 3600:
        aviso = "   <- de hace %.1f h: NO es del ultimo arranque" % (edad / 3600.0)
    print("   si, del %s%s" % (cuando.strftime("%d/%m %H:%M:%S"), aviso))

    plugin = os.path.join(juego, "BepInEx", "plugins", "CatanVerdad.dll")
    if os.path.isfile(plugin) and os.path.getmtime(plugin) > os.path.getmtime(registro):
        print("   OJO: el plugin es MAS NUEVO que este log. Lo que dice abajo es")
        print("        de la version anterior. Abre el juego otra vez y repite.")

    if "Catan Verdad" not in texto and "mario.catan.verdad" not in texto:
        print("   pero BepInEx NO cargo el plugin: no aparece en el registro.")
        print("   Mira si hay algun error de carga arriba del todo del fichero.")
        return False
    print("   el plugin cargo.")

    enganchadas = None
    m = re.search(r"acciones enganchadas:\s*(\d+)", texto)
    if m:
        enganchadas = int(m.group(1))
        n = enganchadas
        print("   acciones enganchadas: %d" % n)
        if n == 0:
            print("   <- CERO. Sin enganches no se apunta nada. Puede que el")
            print("      juego haya cambiado el espacio de nombres")
            print("      Catan.GameLogic.Actions o la firma de Apply.")
    else:
        print("   no encuentro la linea 'acciones enganchadas'.")

    fallos = re.findall(r"fallo apuntando:\s*(.+)", texto)
    if fallos:
        vistos = {}
        for f in fallos:
            vistos[f.strip()] = vistos.get(f.strip(), 0) + 1
        print("   fallos apuntando: %d (%d distintos)" % (len(fallos), len(vistos)))
        for mensaje, veces in sorted(vistos.items(), key=lambda kv: -kv[1])[:5]:
            print("      x%-5d %s" % (veces, mensaje))

    sin_enganchar = re.findall(r"no se pudo enganchar\s+(\S+)", texto)
    if sin_enganchar:
        print("   acciones que no se pudieron enganchar: %d" % len(sin_enganchar))
        for nombre in sin_enganchar[:5]:
            print("      %s" % nombre)
    return enganchadas


def _resumen_esquema(esquema):
    """La primera linea del fichero trae los miembros reales de las clases
    del juego, para poder comprobar que lo que se lee es lo que se cree."""
    print("   jugadores en la partida: %s" % esquema.get("num_jugadores"))
    for clave in ("catan", "tablero", "partida", "jugador_comun", "jugador_catan"):
        bloque = esquema.get(clave)
        if not bloque:
            print("   %-14s -> NO se pudo leer" % clave)
            continue
        campos = bloque.get("campos") or {}
        print("   %-14s %s  (%d miembros)" % (clave, bloque.get("tipo"), len(campos)))
    colores = esquema.get("colores")
    if colores:
        print("   colores por jugador: %s" % colores)
    else:
        print("   AVISO: ColorIdByPlayerId ha salido vacio. Sin el color no se")
        print("          puede saber de quien es una pieza entre partidas.")

    jugador = esquema.get("jugador_comun")
    if jugador:
        campos = (jugador.get("campos") or {})
        print()
        print("   miembros del jugador comun (aqui estan el id y el hueco):")
        for k, v in sorted(campos.items()):
            print("      %-28s %s" % (k, v))


def revisar_verdad(verdad, enganchadas=None):
    _titulo("3. que se ha apuntado")
    jsonl = _mas_nuevo(verdad, ".jsonl")
    if not jsonl:
        print("   ninguna partida apuntada todavia.")
        print("   (la carpeta la crea el mod al arrancar el juego: %s)" % verdad)
        return None
    print("   %s" % jsonl)

    esquema, registros, malas = None, [], 0
    with open(jsonl, "r", encoding="utf-8", errors="replace") as f:
        for linea in f:
            linea = linea.strip()
            if not linea:
                continue
            try:
                d = json.loads(linea)
            except ValueError:
                malas += 1
                continue
            if "esquema" in d:
                esquema = d["esquema"]
            else:
                registros.append(d)
    print("   acciones apuntadas: %d%s" %
          (len(registros), "   (%d lineas ilegibles)" % malas if malas else ""))
    if not registros:
        # Cero acciones con los enganches puestos no es un fallo: en el menu
        # principal no se ejecuta ninguna accion de partida. Decirlo importa,
        # porque el mensaje de antes sonaba a alarma justo en el momento en
        # que todo estaba bien -- que es la peor forma de avisar de nada.
        if enganchadas:
            print("   normal si todavia no has empezado ninguna partida: en el menu")
            print("   no se ejecuta ninguna accion. Con %d enganches puestos, en" % enganchadas)
            print("   cuanto entres en una partida esto empezara a subir.")
        else:
            print("   <- el fichero esta vacio y no hay enganches. No se va a")
            print("      apuntar nada; mira el punto 2.")
        return None

    if esquema:
        print()
        _resumen_esquema(esquema)
    else:
        print("   sin linea de esquema (plugin anterior a este cambio).")

    ultimo = registros[-1]
    print()
    print("   ultimo estado apuntado:")
    print("      accion        %s" % ultimo.get("accion"))
    print("      turno         %s" % ultimo.get("turno"))
    print("      casillas      %d de tierra (%d con el mar)"
          % (len([c for c in (ultimo.get("casillas") or [])
                  if c.get("terreno") != "Water"]),
             len(ultimo.get("casillas") or [])))
    print("      edificios     %d" % len(ultimo.get("edificios") or []))
    print("      carreteras    %d" % len(ultimo.get("carreteras") or []))

    print("      jugador activo %s" % ultimo.get("jugador_activo"))
    jugadores = ultimo.get("jugadores") or []
    print("      jugadores     %d" % len(jugadores))
    for p in jugadores:
        print("         id=%-4s hueco=%-4s color=%-6s tipo=%s" %
              (p.get("id"), p.get("hueco"), p.get("color"), p.get("tipo")))
    # El id y el color son los dos unicos datos del jugador que el tracker
    # necesita de verdad: con ellos se sabe de quien es cada pieza. Si
    # faltan, lo demas da igual.
    vacios = [c for c in ("id", "color")
              if jugadores and all(p.get(c) is None for p in jugadores)]
    if vacios:
        print()
        print("   AVISO: estos campos salen vacios en TODOS los jugadores: %s"
              % ", ".join(vacios))
        print("   Sin ellos no se puede saber de quien es una pieza. Mira el")
        print("   volcado entero: py mod_verdad/comprobar.py --esquema")

    # Las de TIERRA son 19; el mod apunta ademas el anillo de mar que las
    # rodea, asi que en total salen 37. Contarlas todas hacia saltar el aviso
    # en todas las partidas, incluidas las que estaban perfectas -- y un
    # aviso que salta siempre es un aviso que se deja de leer, justo cuando
    # esto existe para avisar de lo que falla.
    casillas = ultimo.get("casillas") or []
    tierra = [c for c in casillas if c.get("terreno") != "Water"]
    if len(tierra) != 19:
        print()
        print("   AVISO: %d casillas de tierra, se esperaban 19 (%d con el mar)."
              % (len(tierra), len(casillas)))

    _revisar_ladron(registros, ultimo)
    _revisar_extras(registros, ultimo)
    _revisar_revelado(registros)
    _revisar_puertos(ultimo)
    _revisar_monopolios(registros)
    _revisar_detalle(registros)
    return jsonl


def _revisar_ladron(registros, ultimo):
    """El ladron: SI se esta leyendo, y de donde sale.

    Esta comprobacion existe por una averia concreta. En el tablero de 5-6
    jugadores el juego deja `BoardState.GamePiecesRobber` a NULL y guarda al
    ladron en `GamePiecesRobbers[0]` -- lo hace su propio `BoardQuery`, que
    prueba el primero y si no tira del segundo. El mod solo miraba el primero,
    asi que `partida_20260827_173755` entro con 15 robos, CERO movimientos de
    ladron y CERO bloqueos, y la produccion contada como si el ladron no
    estuviera en el tablero. Y entro callada: una partida entera y creible.

    Arreglado usando `BoardQuery.GetRobberTile`, que es el accesor del propio
    juego. Pero «compila» y «funciona» siguen siendo dos cosas distintas, y
    esto es lo que separa la una de la otra: con arrancar una partida y correr
    esto ya se sabe, sin tener que jugarla entera."""
    print()
    print("   el ladron:")
    con = sum(1 for r in registros if r.get("ladron"))
    sin = sum(1 for r in registros if "ladron" in r and not r.get("ladron"))
    print("      leido en %d de %d anotaciones" % (con, con + sin))
    if not con:
        print()
        print("      AVISO: NO SE ESTA LEYENDO. Sin el, no hay movimientos de")
        print("      ladron, no hay bloqueos, y la produccion sale DE MAS.")
        candidatos = None
        for r in registros:
            if r.get("ladron_donde_buscar"):
                candidatos = r["ladron_donde_buscar"]
                break
        if candidatos:
            print("      el juego lo guarda en alguno de estos campos: %s"
                  % ", ".join(candidatos))
            print("      (ponlo en `Ladron()`, en mod_verdad/CatanVerdad.cs)")
        else:
            # Sin la lista de candidatos hay dos motivos posibles, y no dan la
            # misma respuesta: o la grabacion es vieja -- el mod de entonces
            # ni buscaba -- o es nueva y no encontro NADA que sonara a ladron,
            # que ya seria que `Board` no es lo que se cree.
            print("      y no hay lista de campos candidatos. O esta grabacion")
            print("      es de antes del arreglo -- el mod de entonces ni")
            print("      buscaba, y basta con volver a jugar -- o `Board` no")
            print("      es lo que se cree en mod_verdad/CatanVerdad.cs")
        return

    # De donde sale. `BoardQuery.GetRobberTile` es el camino bueno; los demas
    # son los respaldos, y verlos aqui quiere decir que al metodo del juego le
    # han cambiado el nombre.
    de = collections.Counter(r["ladron"].get("de") or "sin decir"
                             for r in registros if r.get("ladron"))
    for fuente, veces in de.most_common():
        print("      de %-32s %d veces" % (fuente, veces))
    if "sin decir" in de:
        print("      («sin decir» es una grabacion de antes del 27/8/2026)")

    # Y que se MUEVA. Leerlo siempre en el mismo sitio seria el otro fallo
    # posible: haber cogido la posicion inicial congelada en vez de la de
    # ahora, que da una partida sin un solo bloqueo y con pinta de buena.
    sitios = set()
    for r in registros:
        lad = r.get("ladron")
        if not lad:
            continue
        casillas = ((lad.get("donde") or {}).get("casillas") or [])
        if casillas:
            sitios.add(tuple(casillas[0]))
    print("      ha estado en %d casillas distintas" % len(sitios))
    movs = sum(1 for r in registros
               if (r.get("accion") or "").endswith("Robber_Move_GameAction"))
    if movs and len(sitios) <= 1:
        print()
        print("      AVISO: %d acciones de mover el ladron y siempre sale en" % movs)
        print("      el mismo sitio. Lo que se esta leyendo no es donde esta")
        print("      ahora, sino donde empezo.")


def _revisar_extras(registros, ultimo):
    """`extras`: lo que hay en el tablero y el basico no usa.

    Catan Universe trae Ciudades y Caballeros, Navegantes, los Incas y varios
    escenarios, y `BoardState` guarda DIECINUEVE colecciones de piezas. El mod
    leia seis. Las otras trece -- caballeros, murallas, el pirata, la niebla,
    el mercader, los barbaros, los canales -- se tiraban.

    Ahora se apuntan todas, y no para entenderlas: el importador no sabe nada
    de ellas todavia. Se apuntan para no PERDERLAS. Las grabaciones se guardan
    comprimidas y la base se rehace entera desde ellas, asi que el dia que se
    compre una expansion, la primera partida ya estara bien grabada aunque
    tarde meses en entenderse.

    Jugando al basico esto tiene que salir vacio. Que salga vacio ES el
    resultado bueno; lo que no puede es faltar, porque entonces no se sabe si
    la partida no tenia nada o si lo grabo un mod viejo."""
    print()
    print("   extras (piezas de las expansiones):")
    con_campo = sum(1 for r in registros if "extras" in r)
    if not con_campo:
        print("      no lo trae: grabacion hecha con el mod anterior.")
        return
    print("      lo traen %d de %d anotaciones" % (con_campo, len(registros)))
    hay = collections.Counter()
    for r in registros:
        for k, v in (r.get("extras") or {}).items():
            if v:
                hay[k] += 1
    if not hay:
        print("      vacio en todas -- es lo normal en el Catan basico.")
        return
    for k, n in hay.most_common():
        print("      %-22s en %d anotaciones" % (k, n))
    print()
    print("      Hay piezas de expansion. El importador NO las entiende")
    print("      todavia, pero estan guardadas: cuando aprenda, `--rehacer`")
    print("      mete la partida entera sin perder nada.")


def _revisar_revelado(registros):
    """Qué ha enseñado esta partida que el proyecto todavía no sabe leer.

    Es el informe de después de jugar, y existe para que ampliar el soporte de
    una expansión no sea adivinar. Tres cosas:

      - las acciones que no son del Catan básico, contadas y con nombre
      - los payloads que han disparado (`presentes`), que es lo que dice DÓNDE
        vive el dato de cada una
      - cuánto queda, contra el catálogo entero

    Por qué hace falta lo segundo. El mod lee seis de los 63 accesores de
    `CatanGameActionState` y de los demás sólo apunta cuál ha disparado, nunca
    lo que traen -- entre ellos hay información tapada (`AsSpy` mira la mano
    de otro, `AsShuffleDevelopmentCards` es el orden del mazo). Así que la
    lista de los que dispararon es exactamente el trabajo pendiente: se abren
    uno a uno, mirando qué llevan, con la grabación delante."""
    print()
    print("   lo que esta partida enseña de nuevo:")
    try:
        from mod_verdad import catalogar, importar
        cat = catalogar.cargar()
    except Exception:
        cat, catalogar, importar = None, None, None
    if importar is None:
        print("      no puedo mirarlo (falta importar.py)")
        return

    fuera = collections.Counter()
    for r in registros:
        a = r.get("accion") or ""
        if a and not a.startswith(importar._FAMILIAS_QUE_ENTIENDO):
            fuera[a] += 1
    if not fuera:
        print("      nada: todo es del Catan básico, que ya se entiende.")
    else:
        familias = collections.Counter()
        for a, n in fuera.items():
            familias[catalogar.familia_de(a) if catalogar else "?"] += n
        print("      %d acciones de fuera del básico, de %d tipos:"
              % (sum(fuera.values()), len(fuera)))
        for f, n in familias.most_common():
            print("         %-42s %d" % (f, n))
        for a, n in fuera.most_common(12):
            print("         %-58s x%d" % (a, n))
        if cat:
            # Cuánto de esa expansión queda por ver. Es el numero que dice si
            # con esta partida ya hay bastante para escribir el soporte o si
            # conviene jugar otra.
            for f in familias:
                dela = [x for x in cat["acciones"]
                        if catalogar.familia_de(x) == f]
                vistas = [x for x in dela if x in fuera]
                print("         %s: vistas %d de sus %d acciones"
                      % (f, len(vistas), len(dela)))

    # Los payloads. Salen en `detalle.presentes`, y son los que dicen dónde
    # vive el dato de cada acción.
    pres = collections.Counter()
    for r in registros:
        for p in ((r.get("detalle") or {}).get("presentes") or []):
            pres[p] += 1
    if pres:
        print()
        print("      payloads que han disparado (%d distintos):" % len(pres))
        for p, n in pres.most_common(20):
            print("         %-42s x%d" % (p, n))
        print()
        print("      De estos, el mod NO apunta lo que traen dentro -- sólo que")
        print("      dispararon. Abrirlos uno a uno, mirando qué llevan, es")
        print("      exactamente el trabajo de dar soporte a la expansión.")
    elif fuera:
        print()
        print("      ningún payload ha disparado, que es raro con acciones de")
        print("      fuera del básico: mira si el mod es el nuevo.")


def _revisar_puertos(ultimo):
    """Los puertos: cuantos, de que tipo y -- lo que hace falta saber -- SI
    van en un vertice o en una arista.

    El mod los apunta desde el 21 de agosto de 2026. De eso no se pudo
    comprobar nada al escribirlo: los nombres (`GamePiecesHarbors`,
    `AsHarbor`, `HarborType`) estan verificados en el .dll, pero que un nombre
    exista no dice de que TIPO es el campo, y el juego solo se puede mirar
    jugando.

    Lo que decide todo lo que viene despues es `que`: si el puerto esta en un
    vertice toca TRES casillas y es un sitio concreto; si esta en una arista
    toca dos y son los dos vertices de esa arista los que valen. De ahi sale
    quien tiene el puerto, que es lo unico que no se puede deducir de los
    comercios.

    Un tablero normal tiene NUEVE puertos: cuatro genericos y cinco de un
    recurso cada uno."""
    print()
    print("   puertos:")
    puertos = ultimo.get("puertos")
    if puertos is None:
        print("      no los trae: grabacion hecha con el mod anterior.")
        return
    print("      cuantos:  %d  (en un tablero normal son 9)" % len(puertos))
    if not puertos:
        print()
        print("      AVISO: el mod es el nuevo y no ha leido ni un puerto.")
        print("      O `GamePiecesHarbors` no es el diccionario que se creia,")
        print("      o esta vacio en este momento de la partida.")
        return

    tipos = collections.Counter(p.get("tipo") or "?" for p in puertos)
    print("      tipos:    %s" % dict(tipos))
    print("      uno tal cual: %s" % json.dumps(puertos[0], ensure_ascii=False)[:300])

    # Lo que decide si se puede saber de quien es cada puerto. Desde el 22/8
    # el mod manda `arista`: las DOS casillas entre las que esta. Antes se
    # mandaba `donde`, que salia vacio porque la clave del diccionario se
    # leia como una clase que no era.
    con_arista = sum(1 for p in puertos
                     if len([c for c in (p.get("arista") or []) if c]) == 2)
    print("      con su arista (las dos casillas): %d de %d"
          % (con_arista, len(puertos)))
    if not con_arista:
        print()
        print("      AVISO: se leen los puertos pero no DONDE estan. Sin eso")
        print("      no se puede saber quien tiene cada uno.")
        if puertos[0].get("arista_cruda") is not None:
            print("      la clave, volcada entera:")
            print("         %s" % json.dumps(puertos[0]["arista_cruda"],
                                             ensure_ascii=False)[:400])
    if len(set(tipos)) <= 1:
        print()
        print("      AVISO: todos los puertos salen del mismo tipo (%s)."
              % list(tipos)[0])
        print("      `HarborTypeValue` no esta trayendo el enum.")
    else:
        # En un tablero normal hay cinco de recurso, uno de cada, y cuatro
        # genericos. Si no cuadra no es necesariamente un fallo (podria ser
        # otro mapa), pero es lo primero que hay que mirar.
        genericos = tipos.get("Generic", 0)
        print("      reparto: %d de recurso y %d genericos%s"
              % (len(puertos) - genericos, genericos,
                 "   (un tablero normal: 5 y 4)"
                 if (len(puertos) - genericos, genericos) != (5, 4) else "   OK"))


def _revisar_monopolios(registros):
    """El monopolio: quien lo tira, que pide y cuanto suelta cada uno.

    Lo primero y lo segundo ya se apuntaban (`accion_de` y
    `recurso_elegido`). Lo tercero empezo el 22 de agosto de 2026 y no se ha
    podido comprobar sin jugar: sale de `AsResourcesFromPlayers`, que es un
    modelo generado por thrift cuyos campos no se ven desde fuera del juego.
    Por eso se vuelca entero y por eso hay que mirar aqui QUE forma tiene,
    antes de escribir nada que lo lea.

    Es informacion publica: cuando alguien juega un monopolio, la mesa entera
    ve lo que entrega cada uno."""
    print()
    print("   monopolios:")
    elige = [d for d in registros
             if "Monopoly_SelectResourceType" in str(d.get("accion") or "")]
    reparte = [d for d in registros
               if "Monopoly_HandOverResources" in str(d.get("accion") or "")]
    print("      jugados:  %d  (y %d repartos)" % (len(elige), len(reparte)))
    if not elige and not reparte:
        print("      ninguno en esta partida. No es un fallo.")
        return

    for d in elige:
        det = d.get("detalle") or {}
        print("      turno %-4s lo tira el jugador %-3s y pide %s"
              % (d.get("turno"), d.get("accion_de"),
                 det.get("recurso_elegido") or "?"))

    con_reparto = [d for d in reparte if (d.get("detalle") or {}).get("monopolio")]
    print("      repartos con el detalle de cuanto suelta cada uno: %d de %d"
          % (len(con_reparto), len(reparte)))
    if con_reparto:
        # Que el campo llegue no basta: `HarborType` tambien llegaba, vacio.
        # Lo que hay que ver aqui es si trae jugadores dentro y con cuanto.
        con_gente = [d for d in con_reparto
                     if (d["detalle"]["monopolio"].get("de") or [])]
        print("      y con quien solto que: %d de %d"
              % (len(con_gente), len(con_reparto)))
        muestra = (con_gente or con_reparto)[0]["detalle"]["monopolio"]
        for trozo in (muestra.get("de") or []):
            cartas = trozo.get("cartas") or []
            print("         el jugador %-3s solto %s"
                  % (trozo.get("jugador"),
                     ", ".join("%s x%s" % (c.get("recurso"), c.get("cantidad"))
                               for c in cartas) or "nada"))
        if not con_gente:
            print()
            print("      AVISO: llega el reparto pero sin jugadores dentro.")
            print("      `Resources` esta vacio en el momento en que se mira.")
            print("      El volcado crudo esta al lado, en `crudo`:")
            print("         %s" % json.dumps(muestra.get("crudo"),
                                             ensure_ascii=False)[:500])
    elif reparte:
        print()
        print("      AVISO: se ve el reparto pero no lo que suelta cada uno.")
        print("      `AsResourcesFromPlayers` no es el campo que lo lleva, o")
        print("      el .dll instalado es anterior al 22/8. Si acabas de")
        print("      recompilar, cierra Catan antes: con el juego abierto el")
        print("      .dll no se puede sustituir y sigue cargando el viejo.")


def _revisar_detalle(registros):
    """El detalle de la accion: que se comercio, a quien se robo, que carta.

    Sale del SEGUNDO parametro de Apply, que el mod no capturaba hasta el 19
    de agosto por la noche. Que se lea o no depende de que Harmony inyecte
    bien ese parametro, y eso no se puede comprobar sin jugar una partida --
    por eso se comprueba aqui, que es lo primero que se mira despues de
    jugar. Si el mod es el nuevo y aqui salen ceros, es que la inyeccion no
    esta funcionando y hay que mirarlo, no seguir jugando partidas.

    En las grabaciones anteriores no hay nada de esto y no es un fallo: es
    que se grabaron con el mod de antes."""
    print()
    print("   detalle de las acciones (comercios, robos, cartas):")

    tiene_campo = sum(1 for d in registros if "accion_de" in d)
    if not tiene_campo:
        print("      no lo trae: grabacion hecha con el mod anterior.")
        return

    comercios = [d for d in registros if (d.get("detalle") or {}).get("comercio")]
    banco = [d for d in registros if (d.get("detalle") or {}).get("comercio_banco")]
    robos = [d for d in registros
             if (d.get("detalle") or {}).get("robado_a") is not None]
    cartas = [d for d in registros if (d.get("detalle") or {}).get("carta")]
    con_autor = sum(1 for d in registros
                    if d.get("accion_de") is not None and d["accion_de"] >= 0)

    print("      quien hizo la accion:  %d de %d acciones" % (con_autor, len(registros)))
    print("      comercios con cartas:  %d entre jugadores, %d con el banco"
          % (len(comercios), len(banco)))
    print("      robos con victima:     %d" % len(robos))
    print("      cartas con su nombre:  %d" % len(cartas))

    ejemplo = comercios[0] if comercios else (banco[0] if banco else None)
    if ejemplo:
        c = (ejemplo["detalle"].get("comercio")
             or ejemplo["detalle"].get("comercio_banco"))
        print("      un comercio de ejemplo: da %s  pide %s"
              % (_cartas_cortas(c.get("da")), _cartas_cortas(c.get("pide"))))

    if not con_autor:
        print()
        print("      AVISO: el mod es el nuevo pero no ha leido ni una accion.")
        print("      Harmony no esta inyectando el segundo parametro de Apply.")
        print("      Mira el log de BepInEx: si dice 'acciones enganchadas: 0',")
        print("      es eso.")


def _cartas_cortas(lista):
    if not lista:
        return "(nada)"
    return " + ".join("%s x%s" % (c.get("recurso"), c.get("cantidad"))
                      for c in lista)


def revisar_fotos(jsonl):
    _titulo("4. fotos emparejadas")
    if not os.path.isdir(DATOS):
        print("   no hay ninguna todavia (mod_verdad/datos no existe).")
        print("   -> py mod_verdad/recopilar.py   mientras juegas")
        return
    total_fotos, total_lineas = 0, 0
    for nombre in sorted(os.listdir(DATOS)):
        carpeta = os.path.join(DATOS, nombre)
        if not os.path.isdir(carpeta):
            continue
        fotos = [f for f in os.listdir(carpeta) if f.endswith(".png")]
        indice = os.path.join(carpeta, "indice.jsonl")
        lineas = sum(1 for _ in open(indice, encoding="utf-8", errors="replace")) \
            if os.path.isfile(indice) else 0
        total_fotos += len(fotos)
        total_lineas += lineas
        marca = "" if len(fotos) == lineas else "   <- descuadrado"
        print("   %-30s %4d fotos  %4d estados%s" % (nombre, len(fotos), lineas, marca))
    if total_fotos == 0:
        print("   ninguna. Sin fotos emparejadas no se puede entrenar nada:")
        print("   -> py mod_verdad/recopilar.py   mientras juegas")
    else:
        print("   total: %d fotos con su verdad al lado" % total_fotos)


def volcar_esquema(verdad):
    """El esquema entero, para cuando hay que buscar un nombre de campo."""
    jsonl = _mas_nuevo(verdad, ".jsonl")
    if not jsonl:
        print("no hay ninguna partida apuntada.")
        return
    with open(jsonl, "r", encoding="utf-8", errors="replace") as f:
        for linea in f:
            try:
                d = json.loads(linea)
            except ValueError:
                continue
            if "esquema" in d:
                print(json.dumps(d["esquema"], indent=2, ensure_ascii=False))
                return
    print("ese fichero no tiene linea de esquema.")


def main():
    juego = carpeta_del_juego()
    if not juego:
        print("No encuentro Catan Universe. Abre Steam una vez si lo has movido.")
        return 1
    verdad = carpeta_de_verdad()
    if "--esquema" in sys.argv:
        volcar_esquema(verdad)
        return 0

    print("juego: %s" % juego)
    revisar_interruptor(juego)
    enganchadas = revisar_bepinex(juego)
    jsonl = revisar_verdad(verdad, enganchadas)
    revisar_fotos(jsonl)
    print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
