# -*- coding: utf-8 -*-
"""Los titulares: las conclusiones que se escriben solas, con el número que las
sostiene y la tabla de donde sale.

    py db/titulares.py          los saca por consola

POR QUÉ EXISTE. Hay treinta y una tablas. Quien abre esto por primera vez no
sabe cuál mirar, y treinta y una tablas sin una entrada son treinta y una
tablas que nadie lee. Esto es la entrada: unas frases que ya son una
conclusión, cada una con su número y un enlace a la tabla que lo contiene.

CÓMO SE CALCULA, Y POR QUÉ ASÍ. Un titular NO trae SQL propio. Trae el nombre
de una vista y el de una columna, lee la vista con `vistas.consultar` --la
misma llamada que usa el panel para pintar la tabla-- y se queda con la fila
que más tiene de esa columna. El número del titular ES el número de la tabla,
byte a byte, porque es el mismo `SELECT`.

Escribir aquí una consulta a medida habría sido más corto y es justo lo que
no puede pasar: el titular diría 20,5 y la tabla de al lado 19,8, y el que
las viera juntas sacaría que la base se contradice. El panel lleva escrito
«no hay dos consultas que puedan decir cosas distintas» desde el primer día;
esto tampoco es una segunda consulta.

CAMBIAN SOLOS. No hay ni un nombre ni un número escritos aquí. Se recalculan
en cada visita, así que el día que alguien adelante a otro en sietes, el
titular cambia de nombre sin tocar una línea.

EL MÍNIMO DE PARTIDAS. Sólo entra quien lleve `MINIMO` partidas o más. Sin
eso el primer titular se lo lleva siempre el que jugó una vez y tuvo un buen
día: elGato saca un 7 el 23,9% de las veces, que es el número más alto de la
tabla, y son 7 partidas. Con 10 el titular es de LoboEstepario con un 20,5%
en 11. El corte se enseña en la página: un número escondido que decide quién
sale y quién no es peor que no tenerlo.
"""

import os
import sqlite3
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from db import vistas as V           # noqa: E402
import idiomas                       # noqa: E402


# Partidas que hay que llevar para poder salir en un titular.
MINIMO = 10


# Cada titular:
#
#   titulo   la pregunta que contesta, tal cual se lee en la página
#   vista    de qué tabla sale -- y a la que lleva el enlace
#   ordenar  la columna por la que gana: se queda el más alto
#   quien    quién es el titular. Casi siempre la persona; en las vistas de
#            pareja, las dos
#   cifra    el número grande
#   detalle  la frase de debajo, con lo que hace falta para creérselo
#
# Los `{ }` son nombres de columna de esa misma vista y se rellenan con la
# fila que gana. Si una vista deja de tener una columna, la prueba lo canta
# antes de que la página enseñe un `{porcentaje}` en crudo.
TITULARES = (
    {"id": "gana",
     "titulo": "Quién gana más",
     "vista": "amigos_marcador",
     "ordenar": "victorias",
     # LAS DOS MESAS EN LA MISMA FICHA. «Marcador» tiene una fila por
     # persona Y por tamaño de mesa, y sin acotar el titular se llevaba la
     # fila mas alta de las dos mesas mezcladas -- que hoy es una de cuatro,
     # pero eso es una casualidad de los datos, no una decision. Ahora la
     # linea de arriba es SIEMPRE la mesa de 4 y la de abajo la de 5 y 6, que
     # es como se lee un marcador partido: cada bloque contra el suyo.
     "donde": ("eran", "==", 4),
     "tambien": {
         "donde": ("eran", ">=", 5),
         "texto": "En mesa de 5 y 6 manda {quien}, con {victorias} "
                  "de {partidas}.",
         # Cuando el que mas gana gana CERO, la plantilla de arriba dice
         # «manda fulano con 0 de 2», que es verdad y no significa nada.
         # Ahora mismo es el caso: de los tres que llegan al minimo, los tres
         # han jugado dos partidas de 5-6 y las han perdido todas.
         "si_cero": "En mesa de 5 y 6 no ha ganado todavía ninguno de los "
                    "que llegan al mínimo.",
     },
     # Y QUIEN GANA MAS A MENUDO, que no es el mismo y no se ve solo.
     #
     # Ordenar por victorias a secas premia al que mas juega: 7 de 16 manda
     # sobre 6 de 12, o sea 43,8% por delante de un 50%. Ordenar por el
     # porcentaje seria peor: con diez partidas de minimo, UNA victoria da la
     # vuelta al titular --el de 6 de 12 pierde la siguiente, se queda en 46%
     # y deja de mandar-- y eso es ruido con nombre y apellidos.
     #
     # Asi que van las dos, y esta linea solo sale cuando son personas
     # distintas: cuando el que mas gana es ademas el que mas gana por
     # partida, decirlo dos veces no aniade nada.
     #
     # El numero de esta linea SIGUE SIENDO DE LA TABLA --«6 de 12» son dos
     # columnas de la misma fila-- y por eso se ordena aqui en vez de pedirle
     # a la vista un porcentaje que no tiene. No es una segunda consulta.
     "mejor_por": {
         "clave": ("victorias", "partidas"),
         "texto": "El que más gana por partida es {quien}, "
                  "{victorias} de {partidas}.",
     },
     "cifra": "{victorias} de {partidas}",
     # `eran` va en el detalle a propósito: «Marcador» tiene una fila por
     # persona Y por tamaño de mesa, porque a 5 se juega a 12 puntos y no es
     # la misma partida. Sin decirlo, el titular parecería el total de sus
     # partidas y no lo es.
     "detalle": "en mesa de {eran}. Acaba de media en el puesto "
                "{puesto_medio}, con {puntos_medios} puntos."},

    {"id": "sietes",
     "titulo": "Quién saca más sietes",
     "vista": "amigos_sietes",
     "ordenar": "porcentaje",
     "cifra": "{porcentaje}%",
     "detalle": "de sus tiradas: {sietes} sietes en {tiros} tiros. "
                "Lo normal es {porcentaje_normal}%."},

    {"id": "desarrollo",
     "titulo": "Quién compra más cartas de desarrollo",
     "vista": "amigos_desarrollo",
     "ordenar": "por_partida",
     "cifra": "{por_partida} por partida",
     "detalle": "{compradas} cartas en {partidas} partidas, "
                "{caballero} de ellas caballeros."},

    {"id": "casillas",
     "titulo": "Quién elige mejor las casillas",
     "vista": "amigos_suerte",
     "ordenar": "por_casilla",
     "cifra": "{por_casilla} puntitos",
     # Ojo con la frase: gana el más alto de los que entran, y eso no quiere
     # decir que esté por encima de la media. Por eso «el que mejor elige» y
     # no «elige bien»: lo primero es cierto siempre, lo segundo depende de
     # si `por_casilla` supera a `lo_normal`, y el que lee lo ve al lado.
     "detalle": "de media por casilla suya, cuando un sitio cualquiera de "
                "sus tableros vale {lo_normal}. Con eso le tocaron "
                "{le_toco} cobros de los {le_tocaba} que le tocaban."},

    {"id": "ladron",
     "titulo": "Con quién se ceba el ladrón",
     "vista": "amigos_ladron_a_quien",
     "ordenar": "se_lo_puso",
     "quien": "{quien} a {a_quien}",
     "cifra": "{se_lo_puso} veces",
     # `le_costo` y `le_robo` son dos danios distintos y en la primera
     # version se leian como uno repetido: «le costo 24 cartas de produccion
     # y 24 de la mano» con dos 24 que coinciden por casualidad (pasa en 4 de
     # las 34 parejas). Ahora va `le_bloqueo` en medio, que es el eslabon que
     # faltaba: de las veces que se lo puso, en cuantas salio el numero.
     "detalle": "{con_7} veces obligado por un 7 y {con_caballero} "
                "eligiéndolo con un caballero. En {le_bloqueo} de esas veces "
                "salió el número y {a_quien} no cobró: son {le_costo} cartas "
                "que se quedó sin producir. Y aparte le quitó {le_robo} "
                "cartas de la mano."},

    {"id": "intercambios",
     "titulo": "Quién va más en positivo, y con quién",
     # De «El saldo con cada uno» y NO de «Quién propone tratos a
     # quién», que es la de al lado y contesta otra cosa: aquella solo
     # mete los tratos que esa persona PROPUSO. Periplo con carla sale a -1
     # alli y a +4 aqui, y las dos son verdad -- la primera dice como le va
     # cuando pide el, la segunda como le va. Un titular tiene que ser la
     # segunda.
     "vista": "amigos_saldo",
     "ordenar": "neto",
     # La fila es una PAREJA, asi que el titular son dos nombres. Con uno
     # solo, el numero no se puede volver a encontrar en la tabla.
     "quien": "{quien} con {con_quien}",
     "cifra": "{neto} cartas",
     # Y la advertencia de siempre con el comercio, que aqui hace mas falta
     # que en ningun sitio porque el titular se lee como un ranking: llevarse
     # mas cartas NO es comerciar mejor. Dar tres por una puede ser el mejor
     # trato de la partida si esa una es la que te faltaba para la ciudad.
     "detalle": "de más en los {tratos} tratos entre los dos: se llevó "
                "{recibio} y soltó {dio}. Son cartas, no acierto: dar tres "
                "por una puede ser el mejor trato de la partida."},

    {"id": "suerte",
     "titulo": "Quién tiene más suerte",
     "vista": "amigos_suerte",
     # Ordena por `se_sale` y NO por `suerte`, aunque el titular ensenie el
     # porcentaje. Lo dice la propia columna en `columnas.py`: «es el numero
     # que de verdad ordena; por debajo de 2 no hay nada que contar». Un 108%
     # con nueve casillas esta dentro de lo normal y un 103% con cien no, y
     # ordenar por el porcentaje coronaria al primero.
     #
     # El minimo de partidas no sustituye a esto: quita al que jugo una vez,
     # pero entre dos que llevan doce sigue habiendo uno con ruido y otro sin
     # el, y el porcentaje solo no los distingue.
     "ordenar": "se_sale",
     # Y EL OTRO EXTREMO DE LA MISMA LISTA. Un titular aparte para la mala
     # suerte seria otra ficha diciendo lo mismo del reves, y la pregunta es
     # una sola: como se ha repartido el tablero. Arriba el que mas cobro de
     # lo suyo, aqui el que menos, y se ve el recorrido entero sin abrir la
     # tabla.
     #
     # Sale de la misma fila de la misma consulta, asi que el numero se
     # vuelve a encontrar abajo. Y no juzga: da el porcentaje y los margenes,
     # y la regla de los 2 esta dicha una linea antes, que vale para los dos
     # lados. Ahora mismo el de abajo la pasa y el de arriba no.
     "al_reves": {
         "texto": "El que menos suerte tiene es {quien}, "
                  "con {suerte}% y {se_sale} márgenes.",
     },
     "cifra": "{suerte}%",
     # La frase no dice si es suerte o no: dice el numero y la regla, y que
     # la lea quien mira. Una plantilla no puede ramificar, y escribir «y eso
     # es ruido» seria mentira el dia que alguien pase de 2.
     "detalle": "de lo que le tocaba: cobró {le_toco} veces contra las "
                "{le_tocaba} que le debía el tablero, y 100% es lo normal. "
                "Se sale {se_sale} márgenes: hace falta pasar de 2 para "
                "que sea suerte y no ruido."},
)


# Y los RECORDS, que son otra cosa: la mejor marca de UNA partida.
#
# Un titular es una costumbre -- lo que hace alguien partida tras partida --
# y por eso pide diez partidas. Un record es de un dia. Preguntar «cuantas
# partidas llevas» para dejarte tener un record no tiene sentido: si en tu
# primera te pusieron el ladron once veces, te lo pusieron once veces.
# AQUI NO HAY MINIMO A PROPOSITO, y lo dice la pagina.
#
# Se calcula distinto: en vez de leer la vista entera, la lee UNA VEZ POR
# PARTIDA -- el mismo `{donde}` que usa el desplegable -- y se queda con la
# mejor fila de todas. Por eso sabe de que partida es, que es medio record:
# «107% de suerte» sin decir cuando no se puede ir a comprobar.
RECORDS = (
    {"id": "suerte_de_un_dia",
     "titulo": "La mejor suerte en una partida",
     "vista": "amigos_suerte",
     # Por `se_sale` igual que el titular, y no por el porcentaje. La primera
     # version ordenaba por el porcentaje con la excusa de que \u00abun record es
     # la marca mas alta\u00bb; es la misma trampa que el minimo de partidas evita
     # arriba, y aqui no hay minimo. Un 137% con nueve casillas y un 125% con
     # dieciocho: el segundo es mas raro, y el porcentaje pelado corona al
     # primero.
     #
     # Da igual que en esta base el ganador sea el mismo por los dos caminos
     # (carla, partida 4). Lo era por suerte y lo es por `se_sale`; el
     # segundo y el tercero SI se cambian el sitio, asi que la regla importa.
     "ordenar": "se_sale",
     "cifra": "{suerte}%",
     # La frase da el numero y la regla, y no juzga. La version anterior
     # decia \u00abes una marca, no un merito\u00bb dando por hecho que en una sola
     # partida todo es ruido, y era falso justo en la fila que ensenia: 164%
     # con 9 casillas se sale 3,18 margenes, que no es ruido ni de lejos.
     "detalle": "cobró {le_toco} veces contra las {le_tocaba} que le "
                "tocaban, "
                "y con s\u00f3lo {casillas} casillas. Se sale {se_sale} m\u00e1rgenes "
                "de lo normal: el azar por s\u00ed solo ya mueve un {margen}%."},

    {"id": "ladron_de_un_dia",
     "titulo": "M\u00e1s ladrones en una partida",
     "vista": "amigos_ladron",
     "ordenar": "se_lo_pusieron",
     "cifra": "{se_lo_pusieron} ladrones",
     # Cada numero con su unidad, y la suma a la vista. La primera version
     # ponia \u00able costo 24 cartas y 24 de la mano\u00bb y se leia como un 24
     # repetido; peor todavia, \u00ab24 de la mano\u00bb sin unidad se lee como 24
     # VECES cuando son 24 cartas.
     "detalle": "se lo pusieron encima. En {le_bloquearon} de esas veces "
                "sali\u00f3 el n\u00famero y no cobr\u00f3: {perdido} cartas que se qued\u00f3 "
                "sin producir. M\u00e1s {le_robaron} que le robaron de la mano, "
                "{en_total} cartas en total."},

    # EL MISMO LADRON QUE EL DE ARRIBA, PERO EN CARTAS QUE NO SE COBRARON.
    # Aquel ordena por `se_lo_pusieron` --las veces que te lo plantaron
    # encima, que es lo que uno recuerda-- y este por `perdido`, que es lo
    # unico que te quita de verdad: el ladron en tu casilla, sale el numero,
    # y esa produccion no llega.
    #
    # Y son dos partidas distintas, que es justo lo que las separa: la 17 es
    # la de mas ladrones (21) y la 5 la de mas cartas bloqueadas (20, con
    # ocho ladrones menos). Ponerselo a alguien veinte veces sin que le salga
    # el numero no le cuesta una sola carta.
    #
    # `perdido` Y NO `en_total`, que es esto MAS las cartas que le sacaron
    # de la mano. Son dos cosas distintas --una te la quita el
    # ladron de la mano, la otra no te deja ni producirla-- y la pregunta
    # aqui es la segunda. El robo de la mano ya sale en el record de arriba.
    {"id": "bloqueado_de_un_dia",
     "titulo": "Lo que más bloqueó el ladrón en una partida",
     "vista": "amigos_ladron",
     "ordenar": "perdido",
     "cifra": "{perdido} cartas",
     "detalle": "que no llegó a cobrar: tenía el ladrón encima y el número "
                "le salió {le_bloquearon} veces. Ese día produjo "
                "{producido} cartas en total."},

    # EL MONOPOLIO MAS GORDO, de una sola carta.
    #
    # UNA FILA ES UN MONOPOLIO, no un jugador ni una partida, y esa es la
    # gracia: la pregunta es cuanto se llevo alguien con UNA carta, no cuanto
    # sumo tirando tres en la misma partida. Por eso va sobre esta vista y no
    # sobre una suma por jugador -- serian dos records distintos y este es el
    # que se nota en la mesa.
    #
    # `les_saco` es NULL en las grabaciones que no traian el reparto, y
    # `_un_record` se salta los None: esas no compiten, en vez de entrar como
    # un cero y colarse por debajo. Un cero SI compite, que es otra cosa:
    # pedir un material que no tiene nadie ha pasado.
    #
    # Se ensena de quien salio cada carta porque es la mitad de la historia.
    # «12 cartas» es una cifra; «9 se las quito a uno solo» es lo que se
    # cuenta despues.
    {"id": "monopolio_de_un_dia",
     "titulo": "El monopolio más grande",
     "vista": "amigos_monopolios",
     "ordenar": "les_saco",
     "cifra": "{les_saco} cartas",
     "detalle": "con un solo monopolio, pidiendo {pidio} en el turno "
                "{turno}. Se las soltaron: {de_quien}."},
)


def _num(valor, idioma=None):
    """Un número como se escribe en ese idioma, o el texto tal cual.

    La coma decimal no es cosmética: un inglés lee «3,18» como tres mil
    ciento dieciocho, o sea mil veces el número que es. Cada idioma dice cuál
    es la suya en `idiomas.py`."""
    if isinstance(valor, float):
        # Los enteros que vienen como float (7.0) se escriben sin coma: en un
        # titular, «7,0 de 12» se lee peor que «7 de 12».
        if valor == int(valor):
            return str(int(valor))
        return ("%g" % valor).replace(".", idiomas.decimal(idioma))
    return str(valor)


def _rellenar(plantilla, cols, fila, idioma=None):
    """La plantilla con los numeros de la fila puestos, en el idioma que sea.

    Traducir AQUI y no en el panel es lo que hace que funcione: para cuando
    el panel ve el titular, «{victorias} de {partidas}» ya es «7 de 10» y no
    hay nada que buscar en un diccionario. Y como todas las plantillas pasan
    por este embudo, no hay forma de que una se quede sin traducir."""
    texto = idiomas.frase(plantilla, idioma)
    for i, col in enumerate(cols):
        marca = "{%s}" % col
        if marca in texto:
            texto = texto.replace(marca, _num(fila[i], idioma))
    return texto


def elegibles(conn, minimo=MINIMO):
    """{persona: partidas} de los que llegan al mínimo."""
    return dict(conn.execute(
        "SELECT quien, COUNT(DISTINCT game_id) AS n FROM jugadores "
        " WHERE con_amigos = 1 GROUP BY quien HAVING n >= ?", (minimo,)))


def _cuantas_lleva(conn):
    """{persona: partidas}, todos. Para decir a quién le falta poco."""
    return dict(conn.execute(
        "SELECT quien, COUNT(DISTINCT game_id) FROM jugadores "
        " WHERE con_amigos = 1 GROUP BY quien"))


_COMO = {
    "==": lambda a, b: a == b,
    ">=": lambda a, b: a is not None and a >= b,
    "<=": lambda a, b: a is not None and a <= b,
}


def _filtrar(filas, cols, donde):
    """Las filas que cumplen `(columna, operador, valor)`. Sin `donde`, todas.

    Va aqui y no en el SQL de la vista a proposito: el titular tiene que leer
    LA MISMA consulta que pinta la tabla. Filtrando en SQL serian dos
    consultas distintas y volveria a poder pasar que la portada diga una cosa
    y la tabla de debajo otra."""
    if not donde:
        return list(filas)
    col, op, valor = donde
    if col not in cols:
        return []
    k = cols.index(col)
    return [f for f in filas if _COMO[op](f[k], valor)]


# Lo unico que se pega a mano: el «y» de «Fulano y Mengano». Va aqui y no
# escrito dentro de la funcion porque tiene que traducirse como cualquier
# otra frase del servidor, y `db/pruebas.py` no deja que se quede sin.
CONECTOR = " y "
# Y los dos puntos de «Fulano: lo suyo». Parece puntuacion y no idioma, pero
# el frances pide un espacio DELANTE (« Fulano : lo suyo ») y el ingles no.
# Por eso se traduce como cualquier otra frase en vez de ir pegado a mano.
SEPARADOR = ": "


def _juntar(nombres, idioma=None):
    """«A», «A y B», «A, B y C»."""
    if len(nombres) < 2:
        return nombres[0]
    return (", ".join(nombres[:-1]) + idiomas.frase(CONECTOR, idioma)
            + nombres[-1])


def _escribir(salida, plantillas, cols, iguales, idioma=None):
    """Quien, cifra y detalle. Y SI HAY EMPATE, salen todos.

    POR QUE NO VALE `max`. Dos personas con 3,45 puntitos por casilla son dos
    personas con 3,45 puntitos por casilla: `max` se queda con la primera que
    le llega --que es el orden en que salio la consulta, o sea ninguno-- y
    la otra desaparece de la portada teniendo el mismo numero que se ensena.
    Quien mire la tabla de debajo ve los dos 3,45 y la portada nombrando a
    uno, y eso parece un fallo de la cuenta aunque no lo sea.

    Con empate, el detalle se parte en una linea por persona y cada una lleva
    su nombre delante, porque los numeros que lo sostienen NO son los mismos:
    los dos eligen igual de bien las casillas, pero uno cobro 534 veces y el
    otro 635. Una sola frase con los numeros de uno y los dos nombres arriba
    seria mentira sobre el otro.

    La cifra grande solo se queda arriba si es la misma para todos. Se empata
    por la columna que ordena, que no siempre es la que se ensena: «Quien
    tiene mas suerte» ordena por `se_sale` y ensena `suerte`, asi que dos
    empatados pueden traer dos porcentajes distintos. En ese caso cada uno
    lleva el suyo en su linea y arriba no va ninguno, que es lo unico que no
    se puede leer mal."""
    nombres = [_rellenar(plantillas.get("quien", "{quien}"), cols, f, idioma)
               for f in iguales]
    cifras = [_rellenar(plantillas["cifra"], cols, f, idioma)
              for f in iguales]
    detalles = [_rellenar(plantillas["detalle"], cols, f, idioma)
                for f in iguales]
    salida["quien"] = _juntar(nombres, idioma)
    if len(iguales) == 1:
        salida["cifra"] = cifras[0]
        salida["detalle"] = detalles[0]
        return salida
    misma = len(set(cifras)) == 1
    salida["cifra"] = cifras[0] if misma else ""
    dos_puntos = idiomas.frase(SEPARADOR, idioma)
    lineas = [n + (dos_puntos if misma else ", %s%s" % (c, dos_puntos)) + d
              for n, c, d in zip(nombres, cifras, detalles)]
    salida["detalle"] = lineas[0]
    salida["empate"] = lineas[1:]
    return salida


def _uno(conn, titular, gente, idioma=None):
    """Un titular resuelto, o con `falta` puesto si todavía no se puede."""
    salida = {"id": titular["id"],
              "titulo": idiomas.frase(titular["titulo"], idioma),
              "vista": titular["vista"],
              "vista_titulo": idiomas.frase(
                  V.POR_NOMBRE[titular["vista"]]["titulo"], idioma)}
    try:
        cols, filas = V.consultar(conn, titular["vista"])
    except sqlite3.Error as e:
        salida["falta"] = "%s -- prueba con: py db/vistas.py --crear" % e
        return salida

    # Entra quien llegue al mínimo. En las vistas de pareja tienen que
    # llegar los dos: «X se lo puso a Y quince veces» con una Y de dos
    # partidas es un titular sobre Y, y de Y no se sabe nada todavía.
    #
    # `con_quien` estaba fuera de esta lista y era un agujero: ninguna vista
    # de `con_quien` daba titulares todavía, así que no se notaba. En cuanto
    # «El saldo con cada uno» dio uno, el mínimo se le habría aplicado sólo a
    # la mitad izquierda de la pareja.
    quienes = [c for c in ("quien", "a_quien", "con_quien") if c in cols]
    orden = cols.index(titular["ordenar"])
    # `pueden` son las que entran por el minimo, SIN acotar todavia por
    # bloque: de aqui salen tanto la linea principal como la de `tambien`, y
    # cada una se lleva su trozo. Acotando antes, el segundo filtro caeria
    # sobre el resultado del primero y no quedaria ni una fila -- que es
    # justo lo que pasaba: «mesa de 4» y luego «mesa de 5 o mas» sobre eso.
    pueden = [f for f in filas
              if f[orden] is not None
              and all(f[cols.index(c)] in gente for c in quienes)]
    dentro = _filtrar(pueden, cols, titular.get("donde"))
    if not dentro:
        salida["falta"] = "todavía nadie"
        return salida

    tope = max(f[orden] for f in dentro)
    _escribir(salida, titular, cols, [f for f in dentro if f[orden] == tope],
              idioma)

    # La otra forma de mirar la misma lista: el mejor por partida jugada.
    # Sale solo si no es quien ya manda, y el empate aqui se queda en uno por
    # lo mismo que la segunda mesa: es una frase hecha, no una ficha.
    ritmo = titular.get("mejor_por")
    if ritmo:
        arriba, abajo = ritmo["clave"]
        if arriba in cols and abajo in cols:
            ia, ib = cols.index(arriba), cols.index(abajo)
            conta = [f for f in dentro if f[ia] is not None and f[ib]]
            if conta:
                suyo = max(conta, key=lambda f: f[ia] / float(f[ib]))
                if suyo[orden] != tope:
                    salida["ritmo"] = _rellenar(ritmo["texto"], cols, suyo,
                                                idioma)

    # El extremo de abajo de la misma lista. No sale si hay una sola fila
    # --entonces el mismo seria el primero y el ultimo-- y el empate abajo se
    # queda en uno, por lo mismo que las otras frases hechas.
    reves = titular.get("al_reves")
    if reves:
        fondo = min(f[orden] for f in dentro)
        if fondo != tope:
            peor = [f for f in dentro if f[orden] == fondo][0]
            salida["reves"] = _rellenar(reves["texto"], cols, peor, idioma)

    # La segunda linea, cuando la vista se parte en bloques que no se pueden
    # mezclar. Es OTRA fila de LA MISMA consulta -- no una consulta nueva --
    # asi que sigue valiendo lo de siempre: el numero que se lee aqui es el
    # que esta en la tabla.
    extra = titular.get("tambien")
    if extra:
        otras = _filtrar(pueden, cols, extra.get("donde"))
        if not otras:
            salida["tambien"] = idiomas.frase(extra.get("si_nadie"),
                                              idioma)
        else:
            # Aqui el empate SI se queda en uno, al reves que arriba: esto es
            # una frase hecha --«En mesa de 5 y 6 manda {quien}, con
            # {victorias} de {partidas}»-- y con dos empatados serian dos
            # frases iguales seguidas. El dia que haga falta, lo que hay que
            # partir es la plantilla, no esta linea.
            otra = max(otras, key=lambda f: f[orden])
            salida["tambien"] = (
                idiomas.frase(extra["si_cero"], idioma)
                if not otra[orden] and extra.get("si_cero")
                else _rellenar(extra["texto"], cols, otra, idioma))
    return salida


def _las_partidas(conn):
    """[(numero, dia)] de las partidas de amigos, de la mas nueva a la mas
    vieja. El orden decide los empates: entre dos marcas iguales se queda la
    primera que se mira, y que sea la reciente es lo que hace que un record
    igualado cambie de nombre en vez de quedarse anclado al de 2026."""
    return [(r[0], r[1]) for r in conn.execute(
        "SELECT game_id, dia FROM partidas WHERE con_amigos = 1 "
        " ORDER BY game_id DESC")]


def _un_record(conn, record, partidas, idioma=None):
    """La mejor marca de una sola partida, mirandolas todas una a una."""
    salida = {"id": record["id"],
              "titulo": idiomas.frase(record["titulo"], idioma),
              "vista": record["vista"],
              "vista_titulo": idiomas.frase(
                  V.POR_NOMBRE[record["vista"]]["titulo"], idioma)}
    mejor = None
    for numero, dia in partidas:
        try:
            cols, filas = V.consultar(conn, record["vista"], numero)
        except sqlite3.Error as e:
            salida["falta"] = "%s -- prueba con: py db/vistas.py --crear" % e
            return salida
        if record["ordenar"] not in cols:
            salida["falta"] = ("la columna %s ya no esta en %s"
                               % (record["ordenar"], record["vista"]))
            return salida
        i = cols.index(record["ordenar"])
        for f in filas:
            if f[i] is None:
                continue
            if mejor is None or f[i] > mejor[0]:
                mejor = [f[i], numero, dia, cols, [f]]
            elif f[i] == mejor[0] and numero == mejor[1]:
                # Empate en LA MISMA partida: los dos hicieron la marca ese
                # dia, asi que los dos son el record. Entre partidas
                # distintas no se juntan --la ficha dice de que partida es y
                # el enlace filtra por ella-- y ahi sigue mandando el orden
                # de `_las_partidas`: gana la mas reciente.
                mejor[4].append(f)
    if mejor is None:
        salida["falta"] = "todavia no hay partidas"
        return salida

    _valor, numero, dia, cols, iguales = mejor
    _escribir(salida, record, cols, iguales, idioma)
    salida["partida"] = numero
    salida["dia"] = dia
    return salida


def calcular(conn, minimo=MINIMO, idioma=None):
    """Los titulares de ahora mismo, en orden.

    Devuelve `{minimo, cuantos_llegan, el_que_mas, titulares}`. Lo de fuera
    de la lista es para que la página pueda explicar un titular vacío en vez
    de dejar un hueco: en una base recién estrenada no llega nadie, y eso hay
    que decirlo con el número que falta."""
    gente = elegibles(conn, minimo)
    todos = _cuantas_lleva(conn)
    el_que_mas = max(todos.items(), key=lambda x: x[1]) if todos else None
    partidas = _las_partidas(conn)
    return {"minimo": minimo,
            "cuantos_llegan": len(gente),
            "el_que_mas": ({"quien": el_que_mas[0], "partidas": el_que_mas[1]}
                           if el_que_mas else None),
            "titulares": [_uno(conn, t, gente, idioma) for t in TITULARES],
            "records": [_un_record(conn, r, partidas, idioma)
                        for r in RECORDS]}


def main():
    raiz = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    base = os.path.join(raiz, "catan_stats.db")
    if not os.path.isfile(base):
        print("No hay base de datos en %s" % base)
        return 1
    conn = sqlite3.connect("file:%s?mode=ro" % base.replace("\\", "/"),
                           uri=True)
    try:
        todo = calcular(conn)
    finally:
        conn.close()
    print("Desde %d partidas. Llegan %d."
          % (todo["minimo"], todo["cuantos_llegan"]))
    for t in todo["titulares"]:
        _pintar(t)
    print()
    print("Records de una sola partida. Sin minimo.")
    for r in todo["records"]:
        _pintar(r)
    return 0


def _pintar(t):
    print()
    print("  %s" % t["titulo"].upper())
    if "falta" in t:
        print("    (%s)" % t["falta"])
        return
    print("    %s  --  %s" % (t["quien"], t["cifra"]))
    print("    %s" % t["detalle"])
    for linea in t.get("empate", []):
        print("    %s" % linea)
    if "ritmo" in t:
        print("    %s" % t["ritmo"])
    if "reves" in t:
        print("    %s" % t["reves"])
    if "partida" in t:
        print("    partida %s, %s" % (t["partida"], t["dia"]))
    print("    de: %s" % t["vista_titulo"])


if __name__ == "__main__":
    sys.exit(main())
