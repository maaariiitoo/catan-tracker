# -*- coding: utf-8 -*-
"""El examen de la caja de preguntas: cuánto acierta, medido.

    py db/examen.py              la nota y las que falla
    py db/examen.py --todas      todas, acierte o no
    py db/examen.py --nueva "..."  probar una suelta sin tocar nada

POR QUÉ EXISTE. Hasta el 2 de septiembre de 2026 la caja se arreglaba a
golpe de anécdota: alguien enseñaba una pregunta mal contestada, se añadía
una regla, y a otra cosa. Eso mejora esa pregunta y no dice nada del resto —
ni siquiera si la regla nueva ha roto tres que iban bien. Sin un número, la
única respuesta honesta a «¿cuánto acierta esto?» era «no lo sé».

Es el mismo trato que se le da a la visión: un examen que se pasa entero
cada vez, con su nota apuntada, y las mejoras se miden contra él.

CÓMO ESTÁN ESCRITAS LAS PREGUNTAS, que es lo que decide si el examen vale:

  - Salen de lo que hace cada vista (`columnas.FILA_ES`), NO de leer el
    código que las empareja. Escribirlas mirando el emparejador es hacerse
    trampas al solitario: saldrían las que ya funcionan.
  - Cada vista tiene al menos dos, dichas de formas distintas.
  - Se usan las palabras que usa la gente y no las de las columnas: oveja,
    barro, trigo, piedra, leña; «cuánto», «cuál», «a quién».
  - Se dejan dentro las que FALLAN. Quitar una porque no pasa convierte el
    examen en un adorno. La nota es la nota.

LO QUE MIDE Y LO QUE NO. Son dos notas, y la segunda existe porque la
primera tenía un punto ciego.

  1. LA VISTA: si te lleva al sitio donde está la respuesta.
  2. EL LADO: si contesta con el que MÁS cuando le pides el que más.

La segunda se añadió el 2 de septiembre de 2026 después de un fallo que la
primera no vio. A «quien ha salido más veces primero» contestaba «el que
MENOS primero: ANAKIN, con 0» -- con la vista y la columna correctas. La
palabra «primero» estaba en la lista de pistas de «menos» (por «quien llega
primero a su primera ciudad», donde antes es turno más bajo) y tapaba al
«más» de al lado. Se arregló, y la nota de la vista no se movió ni un punto:
36 de 60 antes y después. Una prueba que no puede bajar cuando algo se rompe
no está midiendo eso.

Lo que sigue sin medirse es si la frase está bien redactada. Eso es más
difícil de comprobar y menos importante: con la vista buena, la tabla está
debajo.
"""
import argparse
import os
import sqlite3
import sys

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RAIZ)

BASE = os.path.join(RAIZ, "catan_stats.db")

# Cada una: la pregunta y la vista donde está la respuesta. `ALGUIEN` se
# cambia por un nombre de la base -- escrito aquí no valdría en otro
# ordenador, donde la gente se llama de otra forma.
PREGUNTAS = [
    # -- las partidas --
    ("cuantas partidas hemos jugado", "partidas"),
    ("cuanto duran las partidas", "partidas"),
    ("cuantas partidas fueron contra la maquina", "partidas"),
    ("de que color jugo ALGUIEN", "jugadores"),

    # -- puntos y ritmo --
    ("quien gana mas", "amigos_marcador"),
    ("quien acaba mejor colocado", "amigos_marcador"),
    ("cuantas partidas ha ganado ALGUIEN", "amigos_marcador"),
    ("de donde saco los puntos ALGUIEN", "amigos_puntos"),
    ("quien tiene mas ciudades", "amigos_puntos"),
    ("quien llega antes a su primera ciudad", "amigos_ritmo"),
    ("en que turno compro su primera carta ALGUIEN", "amigos_ritmo"),
    ("compensa salir el primero", "amigos_por_salida"),
    ("que tal le va al que sale el cuarto", "amigos_por_salida"),
    ("cuantas veces ha salido primero ALGUIEN", "amigos_salida_de_cada_uno"),
    ("a quien le toca salir primero mas veces", "amigos_salida_de_cada_uno"),
    ("en que puesto salio cada uno", "amigos_salida"),

    # -- cartas de desarrollo --
    ("cuantos caballeros ha jugado ALGUIEN", "amigos_desarrollo"),
    ("quien compra mas cartas de desarrollo", "amigos_desarrollo"),
    ("cuantos puntos de victoria le han salido a ALGUIEN", "amigos_desarrollo"),
    ("salen los caballeros que deberian salir", "amigos_mazo"),
    ("que sale mas del mazo", "amigos_mazo"),
    ("quien ha tirado monopolios", "amigos_monopolios"),
    ("que recurso piden en los monopolios", "amigos_monopolios"),
    ("a quien le saca mas con el monopolio ALGUIEN", "amigos_monopolios_a_quien"),
    ("quien me quita mas ovejas con el monopolio", "amigos_monopolios_a_quien"),

    # -- el ladron --
    ("quien recibe mas ladrones de lo que toca", "amigos_ladron_proporcion"),
    ("quien recibe mas ladrones en proporcion", "amigos_ladron_proporcion"),
    # Esta FALLA y se queda. Contesta «El ladron, uno a uno», y no es un
    # disparate: «a quien» pide una pareja y la caja premia a las vistas que
    # la tienen -- con razon, porque la respuesta a un «a quien» es un
    # nombre. La pregunta es de las que se hacen de verdad, asi que se deja
    # dentro con la vista buena escrita al lado, que es para lo que sirve el
    # examen.
    ("a quien le ponen mas el ladron en proporcion",
     "amigos_ladron_proporcion"),
    ("cuanto me cuesta el ladron", "amigos_ladron"),
    ("cuantos materiales ha perdido ALGUIEN por el ladron", "amigos_ladron"),
    ("a quien le pone mas el ladron ALGUIEN", "amigos_ladron_a_quien"),
    ("quien le tiene mania a quien con el ladron", "amigos_ladron_a_quien"),
    ("a que numeros manda el ladron ALGUIEN", "amigos_ladron_donde"),
    ("donde pone el ladron ALGUIEN", "amigos_ladron_donde"),
    ("que numero se come mas ladron", "amigos_ladron_numeros"),
    ("cuantas cartas ha robado ALGUIEN de la mano", "amigos_robos"),
    ("quien roba mas", "amigos_robos"),
    ("a quien le roba mas ALGUIEN", "amigos_ladron_a_quien"),

    # -- comercio --
    ("quien propone mas tratos", "amigos_comercio"),
    ("con quien ha hecho mas tratos ALGUIEN", "amigos_comercio"),
    ("sale ganando cartas ALGUIEN en los tratos", "amigos_comercio"),
    # Las dos de abajo se quedan aunque la vista por persona ya no exista. La
    # respuesta esta en «El saldo con cada uno», que es la unica que suma los
    # tratos de los dos sentidos: no da un total por persona -- eso es lo que
    # se quito -- pero es donde hay que mirar. Se dejan porque son preguntas
    # que se hacen, y una pregunta no se borra del examen por ser dificil.
    ("quien gana mas en los intercambios", "amigos_saldo"),
    ("quien sale ganando cartas de todos los tratos", "amigos_saldo"),
    ("cuantas cartas le ha dado ALGUIEN a los demas", "amigos_saldo"),
    ("cual es mi saldo con cada uno", "amigos_saldo"),
    ("que trato se hizo en el turno 20", "amigos_tratos"),
    ("que material da mas ALGUIEN en los tratos", "amigos_comercio_material"),
    ("a quien le acabo dando siempre madera", "amigos_comercio_material"),

    # -- puertos --
    ("quien usa mas los puertos", "amigos_puertos"),
    ("desde que turno usa el puerto ALGUIEN", "amigos_puertos"),
    ("cuantos puertos ha pillado ALGUIEN", "amigos_cuantos_puertos"),
    ("quien se quedo cada puerto", "amigos_puertos_pillados"),
    ("que puertos no pillo nadie", "amigos_puertos_pillados"),

    # -- el tablero y los dados --
    ("cuanto mineral ha producido ALGUIEN", "amigos_produccion"),
    ("de que material anda corto ALGUIEN", "amigos_produccion"),
    ("cuanta oveja ha sacado ALGUIEN", "amigos_produccion"),
    ("cuanto barro le ha dado el tablero a ALGUIEN", "amigos_produccion"),
    ("en que numeros se puso ALGUIEN", "amigos_numeros"),
    ("cuantas veces le salio el 8 a ALGUIEN", "amigos_numeros"),
    ("estan trucados los dados", "amigos_tiradas"),
    # Los sietes van a su tabla y no a «Las tiradas»: aquella dice si el dado
    # es justo con la MESA y esta si lo es con cada uno. Las dos formas de
    # preguntarlo estan aqui porque no se emparejan igual -- «sietes» da con
    # la columna y «7» no -- y esa diferencia es justo lo que hay que medir.
    ("quien saca mas sietes", "amigos_sietes"),
    ("a quien le tocan mas 7", "amigos_sietes"),
    ("en que turno puso el poblado ALGUIEN", "amigos_numeros"),
    ("que numero sale mas", "amigos_tiradas"),
    ("cuantas veces ha salido el siete", "amigos_tiradas"),
    ("quien ha tenido mas suerte", "amigos_suerte"),
    ("quien elige mejor las casillas", "amigos_suerte"),
    ("se sale alguien del margen de suerte", "amigos_suerte"),
]


# La misma pregunta dicha hacia los dos lados. No hace falta saber quién
# gana -- eso depende de las partidas de cada uno y aquí no se puede saber --
# sino que las dos respuestas NO sean la misma y que cada una diga su lado.
# Se eligen preguntas donde los dos extremos existen de verdad.
PAREJAS = [
    ("quien ha salido mas veces primero", "quien ha salido menos veces primero"),
    ("quien gana mas partidas", "quien gana menos partidas"),
    ("quien tiene mas ciudades", "quien tiene menos ciudades"),
    ("quien ha jugado mas caballeros", "quien ha jugado menos caballeros"),
    ("quien propone mas tratos", "quien propone menos tratos"),
    ("quien ha tenido mas suerte", "quien ha tenido menos suerte"),
    ("quien roba mas cartas", "quien roba menos cartas"),
    ("quien usa mas los puertos", "quien usa menos los puertos"),
]


# Y el mismo examen en los otros idiomas. NO es una traduccion palabra a
# palabra del castellano: son las preguntas como las escribiria alguien en su
# idioma, que es lo unico que sirve para medir. Traduciendo literalmente se
# mediria si el diccionario deshace mi propia traduccion, que es una prueba
# que se aprueba sola.
#
# La nota que importa no es la absoluta sino la comparada: la caja falla lo
# que falla tambien en castellano, y lo que no puede pasar es que falle MAS
# por el idioma.
# --- ingles ---
EXAMEN_EN = [
    ("how many games have we played", "partidas"),
    ("how long do the games last", "partidas"),
    ("how many games were against the computer", "partidas"),
    ("what color did ALGUIEN play", "jugadores"),
    ("who wins most", "amigos_marcador"),
    ("who finishes best ranked", "amigos_marcador"),
    ("how many games has ALGUIEN won", "amigos_marcador"),
    ("where did ALGUIEN get their points from", "amigos_puntos"),
    ("who has the most cities", "amigos_puntos"),
    ("who reaches their first city earliest", "amigos_ritmo"),
    ("on what turn did ALGUIEN buy their first card", "amigos_ritmo"),
    ("does it pay to start first", "amigos_por_salida"),
    ("how does the one who starts fourth do", "amigos_por_salida"),
    ("how many times has ALGUIEN started first", "amigos_salida_de_cada_uno"),
    ("who gets to start first most often", "amigos_salida_de_cada_uno"),
    ("what position did each one start in", "amigos_salida"),
    ("how many knights has ALGUIEN played", "amigos_desarrollo"),
    ("who buys the most development cards", "amigos_desarrollo"),
    ("how many victory points has ALGUIEN drawn", "amigos_desarrollo"),
    ("do the knights come out as they should", "amigos_mazo"),
    ("what comes out of the deck most", "amigos_mazo"),
    ("who has played monopolies", "amigos_monopolios"),
    ("what resource do they ask for in the monopolies", "amigos_monopolios"),
    ("who does ALGUIEN take most from with the monopoly",
     "amigos_monopolios_a_quien"),
    ("who takes most sheep from me with the monopoly",
     "amigos_monopolios_a_quien"),
    ("who gets more robbers than they should", "amigos_ladron_proporcion"),
    ("who gets the most robbers in proportion", "amigos_ladron_proporcion"),
    ("on whom is the robber put most in proportion",
     "amigos_ladron_proporcion"),
    ("how much does the robber cost me", "amigos_ladron"),
    ("how many resources has ALGUIEN lost to the robber", "amigos_ladron"),
    ("on whom does ALGUIEN put the robber most", "amigos_ladron_a_quien"),
    ("who has it in for whom with the robber", "amigos_ladron_a_quien"),
    ("what numbers does ALGUIEN send the robber to", "amigos_ladron_donde"),
    ("where does ALGUIEN put the robber", "amigos_ladron_donde"),
    ("which number gets the robber most", "amigos_ladron_numeros"),
    ("how many cards has ALGUIEN stolen from the hand", "amigos_robos"),
    ("who steals most", "amigos_robos"),
    ("from whom does ALGUIEN steal most", "amigos_ladron_a_quien"),
    ("who proposes the most deals", "amigos_comercio"),
    ("with whom has ALGUIEN made the most deals", "amigos_comercio"),
    ("does ALGUIEN come out ahead on cards in the deals", "amigos_comercio"),
    ("who gains most in the exchanges", "amigos_saldo"),
    ("who comes out ahead on cards across all the deals", "amigos_saldo"),
    ("how many cards has ALGUIEN given the others", "amigos_saldo"),
    ("what is my balance with each one", "amigos_saldo"),
    ("what deal was made on turn 20", "amigos_tratos"),
    ("what resource does ALGUIEN give most in the deals",
     "amigos_comercio_material"),
    ("to whom do I always end up giving wood", "amigos_comercio_material"),
    ("who uses the ports most", "amigos_puertos"),
    ("from what turn does ALGUIEN use the port", "amigos_puertos"),
    ("how many ports has ALGUIEN claimed", "amigos_cuantos_puertos"),
    ("who ended up with each port", "amigos_puertos_pillados"),
    ("what ports did nobody claim", "amigos_puertos_pillados"),
    ("how much ore has ALGUIEN produced", "amigos_produccion"),
    ("what resource is ALGUIEN short of", "amigos_produccion"),
    ("how much wool has ALGUIEN got", "amigos_produccion"),
    ("how much brick has the board given ALGUIEN", "amigos_produccion"),
    ("what numbers did ALGUIEN settle on", "amigos_numeros"),
    ("how many times did the 8 come up for ALGUIEN", "amigos_numeros"),
    ("are the dice rigged", "amigos_tiradas"),
    ("who rolls the most sevens", "amigos_sietes"),
    ("who gets more 7s", "amigos_sietes"),
    ("on what turn did ALGUIEN place the settlement", "amigos_numeros"),
    ("what number comes up most", "amigos_tiradas"),
    ("how many times has the seven come up", "amigos_tiradas"),
    ("who has had the most luck", "amigos_suerte"),
    ("who picks the best tiles", "amigos_suerte"),
    ("is anyone outside the luck margin", "amigos_suerte"),
]


# --- frances ---
EXAMEN_FR = [
    ("combien de parties avons-nous jouees", "partidas"),
    ("combien de temps durent les parties", "partidas"),
    ("combien de parties etaient contre la machine", "partidas"),
    ("de quelle couleur a joue ALGUIEN", "jugadores"),
    ("qui gagne le plus", "amigos_marcador"),
    ("qui finit le mieux classe", "amigos_marcador"),
    ("combien de parties a gagne ALGUIEN", "amigos_marcador"),
    ("d'ou viennent les points de ALGUIEN", "amigos_puntos"),
    ("qui a le plus de villes", "amigos_puntos"),
    ("qui arrive le plus tot a sa premiere ville", "amigos_ritmo"),
    ("a quel tour a achete sa premiere carte ALGUIEN", "amigos_ritmo"),
    ("est-ce que ca vaut le coup de partir premier", "amigos_por_salida"),
    ("comment s'en sort celui qui part quatrieme", "amigos_por_salida"),
    ("combien de fois est parti premier ALGUIEN", "amigos_salida_de_cada_uno"),
    ("qui part premier le plus souvent", "amigos_salida_de_cada_uno"),
    ("de quelle place est parti chacun", "amigos_salida"),
    ("combien de chevaliers a joue ALGUIEN", "amigos_desarrollo"),
    ("qui achete le plus de cartes developpement", "amigos_desarrollo"),
    ("combien de points de victoire a tires ALGUIEN", "amigos_desarrollo"),
    ("est-ce que les chevaliers sortent comme ils devraient", "amigos_mazo"),
    ("qu'est-ce qui sort le plus du paquet", "amigos_mazo"),
    ("qui a joue des monopoles", "amigos_monopolios"),
    ("quelle ressource demandent-ils dans les monopoles", "amigos_monopolios"),
    ("a qui ALGUIEN prend le plus avec le monopole",
     "amigos_monopolios_a_quien"),
    ("qui me prend le plus de laine avec le monopole",
     "amigos_monopolios_a_quien"),
    ("qui recoit plus de voleurs que ce qui lui revient",
     "amigos_ladron_proporcion"),
    ("qui recoit le plus de voleurs en proportion",
     "amigos_ladron_proporcion"),
    ("a qui pose-t-on le plus le voleur en proportion",
     "amigos_ladron_proporcion"),
    ("combien me coute le voleur", "amigos_ladron"),
    ("combien de ressources a perdu ALGUIEN a cause du voleur",
     "amigos_ladron"),
    ("a qui ALGUIEN pose le plus le voleur", "amigos_ladron_a_quien"),
    ("qui en veut a qui avec le voleur", "amigos_ladron_a_quien"),
    ("vers quels numeros envoie le voleur ALGUIEN", "amigos_ladron_donde"),
    ("ou pose le voleur ALGUIEN", "amigos_ladron_donde"),
    ("quel numero recoit le plus le voleur", "amigos_ladron_numeros"),
    ("combien de cartes a volees ALGUIEN dans la main", "amigos_robos"),
    ("qui vole le plus", "amigos_robos"),
    ("a qui vole le plus ALGUIEN", "amigos_ladron_a_quien"),
    ("qui propose le plus d'echanges", "amigos_comercio"),
    ("avec qui a fait le plus d'echanges ALGUIEN", "amigos_comercio"),
    ("est-ce que ALGUIEN sort gagnant en cartes dans les echanges",
     "amigos_comercio"),
    ("qui gagne le plus dans les echanges", "amigos_saldo"),
    ("qui sort gagnant en cartes sur tous les echanges", "amigos_saldo"),
    ("combien de cartes a donnees ALGUIEN aux autres", "amigos_saldo"),
    ("quel est mon solde avec chacun", "amigos_saldo"),
    ("quel echange a ete fait au tour 20", "amigos_tratos"),
    ("quelle ressource donne le plus ALGUIEN dans les echanges",
     "amigos_comercio_material"),
    ("a qui je finis toujours par donner du bois", "amigos_comercio_material"),
    ("qui utilise le plus les ports", "amigos_puertos"),
    ("a partir de quel tour utilise le port ALGUIEN", "amigos_puertos"),
    ("combien de ports a pris ALGUIEN", "amigos_cuantos_puertos"),
    ("qui s'est adjuge chaque port", "amigos_puertos_pillados"),
    ("quels ports personne n'a pris", "amigos_puertos_pillados"),
    ("combien de minerai a produit ALGUIEN", "amigos_produccion"),
    ("de quelle ressource manque ALGUIEN", "amigos_produccion"),
    ("combien de laine a eu ALGUIEN", "amigos_produccion"),
    ("combien d'argile le plateau a donne a ALGUIEN", "amigos_produccion"),
    ("sur quels numeros s'est installe ALGUIEN", "amigos_numeros"),
    ("combien de fois est sorti le 8 pour ALGUIEN", "amigos_numeros"),
    ("est-ce que les des sont truques", "amigos_tiradas"),
    ("qui sort le plus de sept", "amigos_sietes"),
    ("a qui tombent le plus de 7", "amigos_sietes"),
    ("a quel tour a pose la colonie ALGUIEN", "amigos_numeros"),
    ("quel numero sort le plus", "amigos_tiradas"),
    ("combien de fois est sorti le sept", "amigos_tiradas"),
    ("qui a eu le plus de chance", "amigos_suerte"),
    ("qui choisit le mieux ses tuiles", "amigos_suerte"),
    ("est-ce que quelqu'un sort de la marge de chance", "amigos_suerte"),
]


def examinar_idioma(idioma, corpus):
    """La nota de la caja en un idioma. Mismo formato que `examinar`."""
    import panel
    conn = sqlite3.connect("file:%s?mode=ro" % BASE.replace("\\", "/"),
                           uri=True)
    try:
        quien = _alguien(conn)
    finally:
        conn.close()

    aciertos, fallos, saltadas = 0, [], 0
    for texto, esperada in corpus:
        if "ALGUIEN" in texto:
            if quien is None:
                saltadas += 1
                continue
            texto = texto.replace("ALGUIEN", quien)
        r = panel.preguntar(texto, "amigos", idioma)
        salio = r.get("vista")
        if salio == esperada:
            aciertos += 1
        else:
            fallos.append((texto, esperada, salio, r.get("respuesta")))
    return aciertos, len(corpus) - saltadas, fallos, saltadas


LOS_IDIOMAS = (("en", EXAMEN_EN), ("fr", EXAMEN_FR))


def examinar_el_lado():
    """Devuelve (aciertos, total, fallos).

    Un acierto es que la respuesta al «mas» diga «mas» y la del «menos» diga
    «menos». Si las dos frases salen iguales, es que la pregunta no se ha
    entendido hacia ningun lado, y eso cuenta como fallo aunque la vista sea
    la correcta."""
    import panel
    aciertos, fallos = 0, []
    for de_mas, de_menos in PAREJAS:
        r_mas = panel.preguntar(de_mas).get("respuesta") or ""
        r_menos = panel.preguntar(de_menos).get("respuesta") or ""
        bien = ("menos" not in r_mas.lower()
                and "menos" in r_menos.lower()
                and r_mas != r_menos)
        if bien:
            aciertos += 1
        else:
            fallos.append((de_mas, r_mas, r_menos))
    return aciertos, len(PAREJAS), fallos


def _alguien(conn):
    """Alguien con apodo de verdad, o None en un clon recién bajado.

    Sin apodos la caja se NIEGA a adivinar entre `jugador_4645eb8a` y
    `jugador_21edc045`, que es lo correcto, así que las preguntas con nombre
    no se pueden examinar y se saltan."""
    fila = conn.execute("SELECT quien FROM jugadores WHERE es_ia = 0 "
                        "GROUP BY quien ORDER BY COUNT(*) DESC "
                        "LIMIT 1").fetchone()
    if not fila or fila[0].startswith("jugador_"):
        return None
    return fila[0]


# El examen son 68 preguntas contra la base, y lo piden dos pruebas
# distintas. Sin esto la bateria lo corria dos veces enteras para dar el mismo
# numero.
_YA_EXAMINADO = {}


def examinar():
    """Devuelve (aciertos, total, fallos, saltadas)."""
    if "es" in _YA_EXAMINADO:
        return _YA_EXAMINADO["es"]
    import panel
    conn = sqlite3.connect("file:%s?mode=ro" % BASE.replace("\\", "/"),
                           uri=True)
    try:
        quien = _alguien(conn)
    finally:
        conn.close()

    aciertos, fallos, saltadas = 0, [], 0
    for texto, esperada in PREGUNTAS:
        if "ALGUIEN" in texto:
            if quien is None:
                saltadas += 1
                continue
            texto = texto.replace("ALGUIEN", quien)
        r = panel.preguntar(texto)
        salio = r.get("vista")
        if salio == esperada:
            aciertos += 1
        else:
            fallos.append((texto, esperada, salio, r.get("respuesta")))
    _YA_EXAMINADO["es"] = (aciertos, len(PREGUNTAS) - saltadas, fallos,
                           saltadas)
    return _YA_EXAMINADO["es"]


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--todas", action="store_true",
                    help="enseñar también las que acierta")
    ap.add_argument("--nueva", help="probar una pregunta suelta")
    args = ap.parse_args()

    if args.nueva:
        import panel
        r = panel.preguntar(args.nueva)
        print("vista:    %s" % r.get("vista"))
        print("columna:  %s" % r.get("columna"))
        print("respuesta: %s" % r.get("respuesta"))
        return 0

    if not os.path.isfile(BASE):
        print("No hay base de datos: el examen necesita partidas de verdad.")
        return 0

    aciertos, total, fallos, saltadas = examinar()
    if not total:
        print("Nadie tiene apodo todavia: no hay nada que examinar.")
        return 0
    lado_bien, lado_total, lado_fallos = examinar_el_lado()

    if args.todas:
        import panel
        conn = sqlite3.connect("file:%s?mode=ro" % BASE.replace("\\", "/"),
                               uri=True)
        quien = _alguien(conn)
        conn.close()
        for texto, esperada in PREGUNTAS:
            if "ALGUIEN" in texto:
                if quien is None:
                    continue
                texto = texto.replace("ALGUIEN", quien)
            salio = panel.preguntar(texto).get("vista")
            print("%s %-52s %s" % ("ok  " if salio == esperada else "MAL ",
                                   texto, salio))
        print()

    if fallos:
        print("Falla %d de %d:" % (len(fallos), total))
        print()
        for texto, esperada, salio, frase in fallos:
            print("  %s" % texto)
            print("     esperaba %s, contesto %s" % (esperada, salio))
            print("     %s" % (frase or "")[:100])
            print()

    if lado_fallos:
        print("No distingue el mas del menos en %d de %d:"
              % (len(lado_fallos), lado_total))
        print()
        for pregunta, r_mas, r_menos in lado_fallos:
            print("  %s" % pregunta)
            print("     al mas:   %s" % (r_mas or "")[:90])
            print("     al menos: %s" % (r_menos or "")[:90])
            print()

    print("la vista: %d de %d  (%.0f%%)"
          % (aciertos, total, 100.0 * aciertos / total))
    print("el lado:  %d de %d  (%.0f%%)"
          % (lado_bien, lado_total, 100.0 * lado_bien / lado_total))
    # Y la misma nota en los otros idiomas, que es la unica forma de saber si
    # el diccionario de cada uno vale o solo lo parece.
    for idioma, corpus in LOS_IDIOMAS:
        a, n, _f, _s = examinar_idioma(idioma, corpus)
        if n:
            print("  en %s:   %d de %d  (%.0f%%)"
                  % (idioma, a, n, 100.0 * a / n))
    if saltadas:
        print("(%d saltadas: hablan de una persona y nadie tiene apodo)"
              % saltadas)
    return 0


if __name__ == "__main__":
    sys.exit(main())
