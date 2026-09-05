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


def examinar():
    """Devuelve (aciertos, total, fallos, saltadas)."""
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
    return aciertos, len(PREGUNTAS) - saltadas, fallos, saltadas


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
    if saltadas:
        print("(%d saltadas: hablan de una persona y nadie tiene apodo)"
              % saltadas)
    return 0


if __name__ == "__main__":
    sys.exit(main())
