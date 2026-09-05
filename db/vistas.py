# -*- coding: utf-8 -*-
"""Las vistas de la base, y la misma consulta filtrada por una partida.

    py db/vistas.py                 qué vistas hay y cuáles faltan
    py db/vistas.py --crear         las crea (o las rehace si cambiaron)
    py db/vistas.py --quitar        las borra
    py db/vistas.py --ver amigos_marcador          la enseña
    py db/vistas.py --ver amigos_marcador --partida 4

Una vista es una consulta con nombre. No copia datos: cada vez que la miras
vuelve a mirar las tablas, así que no se queda vieja y no ocupa nada. Y como
no guarda nada, crearlas y borrarlas es gratis y no hay nada que romper.

POR QUÉ ESTÁN: casi todo lo que se quiere preguntar empieza igual -- unir
`players` con `games`, resolver el nombre de la persona, y dejar fuera las
partidas contra la IA. Escribir eso a mano cada vez es de donde salen los
errores callados (una partida contra la IA colada en la media, un JOIN que
duplica filas). Aquí está escrito una vez.

UN SQL, DOS USOS. Cada consulta lleva un hueco `{donde}`. Al crear la vista
se rellena con el filtro de siempre -- las de `amigos_` con «los cuatro son
personas» -- y al pedir una partida suelta, con esa partida. Es el mismo
texto en los dos casos, que es lo que evita que el global y el detalle se
contesten con cuentas distintas.

Por eso las de `amigos_` filtradas por partida **no** exigen que sea de
amigos: si pides la partida 3, quieres la 3. El filtro de amigos es lo que
significa «todas».

QUÉ NO SON: no borran nada ni esconden nada. Las tablas siguen enteras
debajo, y las partidas contra la IA se siguen pudiendo consultar. Esto es a
propósito -- son más de la mitad del histórico y son las etiquetas con las
que se mide la lectura de los paneles.
"""
import argparse
import os
import sqlite3
import sys

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BASE = os.path.join(RAIZ, "catan_stats.db")


# --------------------------------------------------------------------------
# Trozos que se repiten. Se montan aquí y no copiados en cada consulta: la
# resta de los puntos tapados aparece en tres vistas y tenerla tres veces es
# pedir que un día digan cosas distintas.
# --------------------------------------------------------------------------

# Los jugadores que entran. `{donde}` es lo único que cambia entre el global
# y una partida suelta.
_J = """j AS (
        SELECT * FROM jugadores WHERE {donde}
    )"""

# De dónde salió cada punto, y cuántos no salen de nada que se vea.
#
# El mod lee los puntos TOTALES sólo al acabar, cuando la pantalla de
# resultados los enseña y ya no son secreto. Todo lo demás -- edificios,
# carretera más larga, mayor ejército -- está a la vista durante la partida.
# Lo que sobra al restar son cartas de punto de victoria, que es justo lo que
# el mod se niega a mirar mientras se juega.
#
# `tapados` sale NULL y no un número cuando falta algún sumando: poner 0 por
# «no lo tenía» cuando en realidad es «no se apuntó» sumaría 2 puntos e
# inventaría una carta que nadie tuvo. Las grabaciones anteriores al 21/8 no
# traen los dos premios.
_PTS = """pts AS (
        SELECT j.game_id, j.dia, j.quien, j.color, j.puesto, j.puntos,
               (SELECT COUNT(*) FROM buildings b
                 WHERE b.player_id = j.player_id
                   AND b.type = 'poblado')              AS poblados,
               (SELECT COUNT(*) FROM buildings b
                 WHERE b.player_id = j.player_id
                   AND b.type = 'ciudad')               AS ciudades,
               p.longest_road                           AS carretera_larga,
               p.largest_army                           AS mayor_ejercito,
               -- La otra via al mismo numero, y por un camino que no pasa
               -- por los edificios ni por los premios: el juego enseña en la
               -- pantalla de resultados los puntos totales Y los que la
               -- partida iba enseñando en el panel. Lo que hay entre los dos
               -- son las cartas de punto tapadas, sin mirar ninguna carta.
               CASE WHEN p.final_points IS NULL
                      OR p.final_points_visible IS NULL THEN NULL
                    ELSE p.final_points - p.final_points_visible
               END                                      AS cartas_de_punto_del_mod,
               CASE WHEN j.puntos IS NULL
                      OR p.longest_road IS NULL
                      OR p.largest_army IS NULL THEN NULL
                    ELSE j.puntos
                      - (SELECT COUNT(*) FROM buildings b
                          WHERE b.player_id = j.player_id AND b.type = 'poblado')
                      - 2 * (SELECT COUNT(*) FROM buildings b
                              WHERE b.player_id = j.player_id AND b.type = 'ciudad')
                      - 2 * p.longest_road
                      - 2 * p.largest_army
               END                                      AS cartas_de_punto
          FROM j JOIN players p ON p.player_id = j.player_id
    )"""

# Qué le tocó a cada uno de las cartas que compró.
#
# El mod NO apunta qué carta sale al comprarla, y hace bien: hasta que se
# juega es información tapada. El tipo sólo se sabe por dos caminos -- porque
# la jugó, o porque era de punto y la delata la resta de `pts`.
#
# `punto_victoria` sale NULL si alguna de sus partidas no se puede cuadrar:
# SUM se saltaría los NULL y daría una cuenta corta que parece buena.
_CARTAS = """cartas AS (
        SELECT quien, partidas, compradas,
               -- Sin `partidas` al lado, `compradas` no se puede comparar
               -- entre personas: 61 cartas en 12 partidas y 37 en 11 se
               -- parecen mucho m�s de lo que parec�a.
               ROUND(compradas * 1.0 / NULLIF(partidas, 0), 2) AS por_partida,
               caballero, invencion, monopolio, carreteras, punto_victoria,
               -- El COALESCE no es descuido. `punto_victoria` sale NULL
               -- cuando la partida no se puede cuadrar, y restar NULL dejaba
               -- `sin_saber` en NULL: las cartas de esa partida no aparecían
               -- en ninguna fila, ni siquiera en la de «sin saber». Se
               -- perdían. Contarlas como lo que son -- compradas y sin
               -- identificar -- es lo honesto, y además es lo que mantiene
               -- en pie la cuenta de que todo lo comprado sale por algún
               -- lado.
               compradas - caballero - invencion - monopolio - carreteras
                         - COALESCE(punto_victoria, 0)  AS sin_saber
          FROM (
            SELECT j.quien,
                   COUNT(*)                                              AS partidas,
                   (SELECT COUNT(*) FROM dev_card_purchases c
                     WHERE c.player_id IN (SELECT player_id FROM j aj
                                            WHERE aj.quien = j.quien))  AS compradas,
                   (SELECT COUNT(*) FROM dev_card_plays d
                     WHERE d.card_type = 'Caballero'
                       AND d.player_id IN (SELECT player_id FROM j aj
                                            WHERE aj.quien = j.quien))  AS caballero,
                   (SELECT COUNT(*) FROM dev_card_plays d
                     WHERE d.card_type = 'Invencion'
                       AND d.player_id IN (SELECT player_id FROM j aj
                                            WHERE aj.quien = j.quien))  AS invencion,
                   (SELECT COUNT(*) FROM dev_card_plays d
                     WHERE d.card_type = 'Monopolio'
                       AND d.player_id IN (SELECT player_id FROM j aj
                                            WHERE aj.quien = j.quien))  AS monopolio,
                   (SELECT COUNT(*) FROM dev_card_plays d
                     WHERE d.card_type = 'Construccion de carreteras'
                       AND d.player_id IN (SELECT player_id FROM j aj
                                            WHERE aj.quien = j.quien))  AS carreteras,
                   (SELECT CASE WHEN SUM(pt.cartas_de_punto IS NULL) > 0 THEN NULL
                                ELSE SUM(pt.cartas_de_punto) END
                      FROM pts pt WHERE pt.quien = j.quien)             AS punto_victoria
              FROM j
             GROUP BY j.quien)
    )"""


# --------------------------------------------------------------------------
# El mazo de desarrollo, por tamaño de mesa.
#
# Con 5 o con 6 no se juega con el mazo de siempre: la ampliación mete diez
# cartas más -- seis caballeros y una de cada uno de los otros cuatro tipos,
# la de punto de victoria incluida -- y se pasa de 25 a 35. Es justo el dato
# que no da error: `amigos_mazo` comparaba lo que salió contra un mazo de 25
# aunque la partida fuera de seis, y el «esperado» salía mal sin que nada
# chirriara.
#
# Esto NO está medido, está leído del reglamento, y la diferencia importa. El
# juego no enseña el mazo, y mirárselo por dentro sería hacer trampas: la
# acción que lo baraja es de las que el mod tiene PROHIBIDAS, porque da el
# orden de las cartas, o sea el futuro. Así que aquí hay una suposición.
#
# Una suposición escrita se puede vigilar, y la vigila una prueba desde los
# datos: si de una partida sale más veces una carta de las que su mazo dice
# que lleva, los números de aquí están mal y salta.
_BASICO = {"caballero": 14, "punto_victoria": 5, "carreteras": 2,
           "invencion": 2, "monopolio": 2}
_AMPLIADO = {"caballero": 20, "punto_victoria": 6, "carreteras": 3,
             "invencion": 3, "monopolio": 3}

# El de 5 y el de 6 son el mismo objeto a propósito: es la misma caja.
MAZO = {2: _BASICO, 3: _BASICO, 4: _BASICO, 5: _AMPLIADO, 6: _AMPLIADO}


def _mazos_sql():
    """`MAZO` como una tabla de SQL, para poder cruzarla por tamaño de mesa.

    Generado y no escrito a mano: son cinco números por mesa y copiarlos en
    el SQL es garantizar que un día el diccionario y la consulta digan cosas
    distintas.
    """
    filas = []
    for eran in sorted(MAZO):
        m = MAZO[eran]
        n = (m["caballero"], m["punto_victoria"], m["carreteras"],
             m["invencion"], m["monopolio"], sum(m.values()))
        if not filas:
            filas.append("SELECT %d AS eran, %d AS caballero, "
                         "%d AS punto_victoria, %d AS carreteras, "
                         "%d AS invencion, %d AS monopolio, %d AS total"
                         % ((eran,) + n))
        else:
            filas.append("UNION ALL SELECT %d, %d, %d, %d, %d, %d, %d"
                         % ((eran,) + n))
    salto = "\n            "
    return "mazos AS (" + salto + salto.join(filas) + "\n    )"


_MAZOS = _mazos_sql()


def _con(*trozos):
    """Une los CTE en un WITH, en orden de dependencia."""
    return "WITH " + ",\n     ".join(trozos) + "\n"


# --------------------------------------------------------------------------
# Las vistas
#
#   global  -- el filtro al crear la vista y al pedir «todas»
#   partida -- el filtro al pedir una partida suelta, con un ? por el número
# --------------------------------------------------------------------------

VISTAS = [

    # `partidas` y `jugadores` se guardan SIN filtrar, y tiene que seguir
    # siendo así: casi todas las demás se apoyan en ellas. Si la vista guardada
    # se quedara sólo con las de amigos, pedir «todas, la IA incluida» daría
    # las de amigos igual y no habría forma de verlo -- el filtro estaría
    # puesto dos capas más abajo. El ámbito se aplica al consultar, encima.
    {"nombre": "partidas", "titulo": "Partidas",
     # «casillas del tablero» va en el resumen a proposito: es lo que
     # distingue esta vista de las del ladron cuando alguien pregunta por
     # casillas. Una casilla se nombra por su numero, asi que sin la palabra
     # «tablero» aqui, «cuantas casillas tiene el tablero» se iba a «los
     # numeros que mas tapa el ladron» y contestaba con seguridad otra cosa.
     "que": "una por partida, con quién ganó, cuántas casillas tenía el "
            "tablero y si eran todos personas",
     "global": "1=1", "partida": "g.game_id = ?",
     # `jugadores` aquí es un alias de un subselect de este mismo SELECT, no
     # una columna, así que el filtro por tamaño de mesa tiene que repetir la
     # cuenta. Lo mismo que hace `columna_amigos` en «Jugadores».
     "columna_jugadores": "(SELECT COUNT(*) FROM players p2"
                          "  WHERE p2.game_id = g.game_id)",
     "sql": """
        SELECT g.game_id,
               substr(g.started_at, 1, 10)                    AS dia,
               substr(g.started_at, 12, 5)                    AS hora,
               g.winner                                       AS gano,
               (SELECT COUNT(*) FROM players p
                 WHERE p.game_id = g.game_id)                  AS jugadores,
               -- A cuantos puntos se jugaba: el basico es a 10 y el de 5-6
               -- jugadores a 12. No se apunta en ningun sitio porque no hace
               -- falta -- se sabe por cuantos eran.
               CASE WHEN (SELECT COUNT(*) FROM players p
                           WHERE p.game_id = g.game_id) >= 5
                    THEN 12 ELSE 10 END                        AS a_puntos,
               -- `casillas_tablero` y no `casillas` a secas: en
               -- `amigos_suerte` hay otra columna `casillas` que son las de
               -- cada JUGADOR, y esas si se suman. Con el mismo nombre, lo
               -- que vale para una valia para la otra -- y sumar tamanos de
               -- tablero da 182, que no es un numero que exista.
               -- Cuantas casillas tenia el tablero: 19 el basico, 30 el de
               -- 5-6. Va aqui porque es la forma mas directa de ver de un
               -- vistazo que partidas son del tablero grande.
               (SELECT COUNT(*) FROM tiles t
                 WHERE t.game_id = g.game_id)                  AS casillas_tablero,
               (SELECT COUNT(*) FROM players p
                 WHERE p.game_id = g.game_id AND p.is_bot = 1) AS ias,
               CASE WHEN (SELECT COUNT(*) FROM players p
                           WHERE p.game_id = g.game_id AND p.is_bot = 1) = 0
                    THEN 1 ELSE 0 END                         AS con_amigos,
               (SELECT COUNT(*) FROM rolls r
                 WHERE r.game_id = g.game_id)                 AS tiradas,
               CASE WHEN g.ended_at IS NULL THEN NULL
                    ELSE CAST((julianday(g.ended_at)
                             - julianday(g.started_at)) * 1440 AS INTEGER)
               END                                            AS minutos,
               -- Lo que salio mal al importarla, si salio algo. Va en la
               -- tabla y no en un log porque cambia lo que las demas filas
               -- quieren decir: la partida 11 tiene la produccion contada
               -- como si no hubiera ladron, y sin esta columna eso no se ve
               -- por ningun lado -- sale una partida perfectamente creible.
               (SELECT mi.pegas FROM mod_imports mi
                 WHERE mi.game_id = g.game_id)                 AS pegas
          FROM games g
         WHERE {donde}
         -- LA MÁS RECIENTE ARRIBA. La tabla se pagina de 11 en 11, así que
         -- en orden cronológico la primera pantalla es la de agosto y la
         -- partida que acabas de jugar está en la última página. Y esa es
         -- justo la que se abre a mirar: se graba una, se importa y se viene
         -- aquí a ver si entró bien.
         --
         -- El desplegable de «Qué partidas» ya iba así (`ORDER BY game_id
         -- DESC` en el catálogo del panel), o sea que esto además los deja
         -- de acuerdo: la de arriba del todo es la misma en los dos sitios.
         ORDER BY g.game_id DESC
    """},

    {"nombre": "jugadores", "titulo": "Jugadores",
     "que": "una fila por jugador y partida, con el nombre ya resuelto",
     "global": "1=1", "partida": "p.game_id = ?",
     # El filtro tiene que ir contra `pa`, que es de donde sale la columna.
     "columna_amigos": "pa.con_amigos",
     "columna_jugadores": "(SELECT COUNT(*) FROM players x2"
                          "  WHERE x2.game_id = p.game_id)",
     "sql": """
        SELECT p.player_id,
               p.game_id,
               pa.dia,
               pa.con_amigos,
               COALESCE(p.person_name, p.name) AS quien,
               p.is_bot                        AS es_ia,
               p.color,
               p.turn_order                    AS salida,
               p.final_rank                    AS puesto,
               p.final_points                  AS puntos,
               -- Cuantos jugaban esa partida. Hace falta para casi todo lo
               -- que compara partidas entre si: ganar entre seis no es lo
               -- mismo que ganar entre cuatro.
               (SELECT COUNT(*) FROM players x
                 WHERE x.game_id = p.game_id)   AS jugadores,
               -- A cuantos puntos se jugaba. El Catan basico es a 10 y el de
               -- 5-6 jugadores a 12 -- confirmado en pantalla el 27 de
               -- agosto. No hace falta apuntarlo: se sabe por cuantos son.
               CASE WHEN (SELECT COUNT(*) FROM players x
                           WHERE x.game_id = p.game_id) >= 5
                    THEN 12 ELSE 10 END         AS a_puntos
          FROM players p
          JOIN partidas pa ON pa.game_id = p.game_id
         WHERE {donde}
         -- La más reciente arriba, como en «Las partidas»; el porqué
         -- está escrito allí. Lo de DENTRO de cada partida no se toca:
         -- una partida se lee hacia adelante.
         ORDER BY p.game_id DESC, p.final_rank
    """},

    {"nombre": "amigos_marcador", "titulo": "Marcador",
     "que": "partidas, victorias y puntos medios de cada uno, por tamaño de mesa",
     "global": "con_amigos = 1", "partida": "game_id = ?",
     "sql": _con(_J) + """
        -- UNA FILA POR PERSONA Y POR TAMAÑO DE MESA. No una por persona.
        --
        -- Estuvo un tiempo siendo una sola fila con `eran` de rango --«4-6»--
        -- y no valia: dice que ha mezclado, pero no deshace la mezcla, y
        -- debajo del rango las medias no significan nada. Entre cuatro se
        -- gana una de cada cuatro y entre seis una de cada seis; se juega a
        -- 10 y a 12 puntos. Sumadas, las dos mesas dan una media que no es de
        -- ninguna de las dos: TheClonne salia con 7,7 puntos de media sobre
        -- «10-12», que no es un dato de nada.
        --
        -- Partido, cada bloque se lee entero y por dentro es comparable, que
        -- es lo que se pedia: el marcador de cuando sois cuatro, el de cuando
        -- sois cinco y el de cuando sois seis.
        --
        -- Aqui NO va lo que «le tocaba» ganar (las partidas entre el numero de
        -- jugadores) ni la diferencia contra eso. Estuvieron puestas y
        -- sobraban: con bloques de una y de seis partidas, esa resta se
        -- dispara sola -- una victoria de una entre seis sale +0,8 y es UNA
        -- partida -- y ocupaba dos columnas en la unica tabla que se mira
        -- siempre. La comparacion entre mesas de distinto tamano sigue
        -- pendiente de decidir; cuando se decida, ira donde no estorbe.
        SELECT quien,
               COUNT(*)                                        AS partidas,
               -- Cuantos jugaban: es lo que parte la tabla en bloques.
               jugadores                                       AS eran,
               SUM(CASE WHEN puesto = 1 THEN 1 ELSE 0 END)     AS victorias,
               ROUND(AVG(puntos), 1)                           AS puntos_medios,
               -- Al lado de `puntos_medios` a proposito: sin esto no se puede
               -- leer. 9 puntos en una mesa de seis (a 12) esta MAS LEJOS de
               -- ganar que 9 en una de cuatro (a 10).
               a_puntos                                        AS se_jugaba_a,
               ROUND(AVG(puesto), 2)                           AS puesto_medio,
               MAX(puntos)                                     AS su_mejor
          FROM j
         GROUP BY quien, jugadores, a_puntos
         -- La mesa primero: cada bloque es un marcador completo, y con las
         -- mesas entremezcladas por victorias no habria bloques que leer.
         -- Dentro, el orden de siempre. Para ver juntas las filas de una
         -- persona se toca la cabecera `quien` en el panel.
         ORDER BY jugadores, victorias DESC, puntos_medios DESC
    """},

    {"nombre": "amigos_salida", "titulo": "El orden de salida",
     "que": "en qué puesto salió cada uno y en cuál acabó",
     "global": "con_amigos = 1", "partida": "game_id = ?",
     "sql": _con(_J) + """
        -- `salida` es el orden de turno: 1 el que empieza. Lo apunta el mod
        -- (`turn_order`), no se deduce de quién movió antes -- que sería lo
        -- mismo casi siempre y no siempre, porque la colocación inicial va en
        -- serpiente y el último en poner el primer poblado pone dos seguidos.
        --
        -- `puestos_ganados` es `salida - puesto`: positivo, acabó mejor de lo
        -- que empezó. Se escribe así y no al revés porque «ganar puestos» con
        -- un número negativo se lee mal.
        SELECT j.game_id                AS partida,
               j.dia,
               j.salida,
               j.quien,
               j.puesto,
               j.puntos,
               j.salida - j.puesto      AS puestos_ganados
          FROM j
         -- La más reciente arriba, como en «Las partidas»; el porqué
         -- está escrito allí. Lo de DENTRO de cada partida no se toca:
         -- una partida se lee hacia adelante.
         ORDER BY j.game_id DESC, j.salida
    """},

    {"nombre": "amigos_por_salida", "titulo": "¿Importa salir primero?",
     "que": "qué tal le va a cada puesto de salida, sumando todas las partidas",
     "global": "con_amigos = 1", "partida": "game_id = ?",
     "sql": _con(_J) + """
        -- La pregunta de siempre en Catan: ¿compensa salir el primero, o es
        -- mejor el cuarto porque coloca dos poblados seguidos y elige último?
        --
        -- Con cuatro partidas esto NO contesta nada y es importante decirlo:
        -- cada puesto de salida tiene cuatro datos. Está para que la respuesta
        -- se vaya construyendo sola según se juegue, no para mirarla hoy.
        SELECT j.salida,
               COUNT(*)                                  AS veces,
               SUM(CASE WHEN j.puesto = 1 THEN 1 ELSE 0 END) AS victorias,
               ROUND(AVG(j.puesto), 2)                   AS puesto_medio,
               ROUND(AVG(j.puntos), 1)                   AS puntos_medios,
               ROUND(AVG(j.salida - j.puesto), 2)        AS puestos_ganados
          FROM j
         WHERE j.salida IS NOT NULL
         GROUP BY j.salida
         ORDER BY j.salida
    """},

    {"nombre": "amigos_salida_de_cada_uno",
     "titulo": "Con qué salida le toca a cada uno",
     "que": "cuántas veces ha salido primero, segundo, tercero… cada persona",
     "global": "con_amigos = 1", "partida": "game_id = ?",
     "sql": _con(_J) + """
        -- Las otras dos de salida contestan otra cosa. `amigos_salida` es el
        -- detalle -- una fila por persona y partida -- y `amigos_por_salida`
        -- mira el PUESTO, no a la persona: qué tal le va al que sale tercero,
        -- sea quien sea. Aquí es al revés: cuántas veces le ha tocado a cada
        -- uno cada sitio.
        --
        -- El orden de salida lo sortea el juego, así que esto es una vista de
        -- suerte, como las de los dados. Por eso lleva `esperado`.
        --
        -- ESPERADO. Cuántas primeras salidas tocarían por azar. No es
        -- `partidas / 4`: entre seis, salir primero toca una de cada seis. Se
        -- suma 1/jugadores partida a partida y así una mesa de seis no
        -- ensucia la cuenta de las de cuatro. Es la misma cuenta que hace
        -- `amigos_mazo` con los mazos, y por el mismo motivo.
        --
        -- `salio_ultimo` aparte de las columnas por número porque salir el
        -- último NO es lo mismo en una mesa que en otra: es el 4 entre
        -- cuatro y el 6 entre seis. Y en Catan es un sitio que muchos
        -- prefieren -- coloca dos poblados seguidos y elige el último -- así
        -- que tenerlo contado suelto es lo que deja compararlo.
        --
        -- SE LLAMABAN `primero`, `segundo`, `tercero`... y se renombraron el
        -- 2 de septiembre de 2026 porque se leían al revés. Esta tabla cuenta
        -- dónde EMPEZÓ cada uno, y `primero` se entiende como «quedó
        -- primero»: TheClonne y carla salieron primeros cuatro veces cada
        -- uno, o sea el mismo 4 en la misma columna, pero carla ha ganado 7
        -- partidas y TheClonne 2. Leída al revés, la tabla decía que
        -- empatan. El SQL siempre estuvo bien; el nombre no.
        SELECT j.quien,
               COUNT(*)                                              AS partidas,
               SUM(CASE WHEN j.salida = 1 THEN 1 ELSE 0 END)         AS salio_1,
               SUM(CASE WHEN j.salida = 2 THEN 1 ELSE 0 END)         AS salio_2,
               SUM(CASE WHEN j.salida = 3 THEN 1 ELSE 0 END)         AS salio_3,
               SUM(CASE WHEN j.salida = 4 THEN 1 ELSE 0 END)         AS salio_4,
               SUM(CASE WHEN j.salida = 5 THEN 1 ELSE 0 END)         AS salio_5,
               SUM(CASE WHEN j.salida = 6 THEN 1 ELSE 0 END)         AS salio_6,
               SUM(CASE WHEN j.salida = j.jugadores THEN 1 ELSE 0 END)
                                                                     AS salio_ultimo,
               ROUND(AVG(j.salida), 2)                               AS salida_media,
               ROUND(SUM(1.0 / j.jugadores), 2)                      AS esperado
          FROM j
         WHERE j.salida IS NOT NULL
         GROUP BY j.quien
         ORDER BY salio_1 DESC, partidas DESC
    """},

    {"nombre": "amigos_salida_como_acabo",
     "titulo": "De cada salida, cómo acabó",
     "que": "de las veces que salió en cada puesto, en cuáles acabó",
     "global": "con_amigos = 1", "partida": "game_id = ?",
     "sql": _con(_J) + """
        -- LA PREGUNTA QUE CONTESTA, y que no contesta ninguna otra: «a MÍ
        -- salir el primero, ¿me sirve?».
        --
        -- «Con qué salida le toca a cada uno» dice cuántas veces salió en
        -- cada puesto, y el marcador dice cuántas ganó. Las dos por separado
        -- no cruzan: que alguien salga mucho primero y gane mucho no dice si
        -- gana CUANDO sale primero. Y «Compensa salir el primero» sí cruza,
        -- pero de toda la mesa junta, no persona a persona.
        --
        -- Una fila por (persona, puesto de salida). `veces` es en cuántas
        -- partidas salió ahí, y las columnas `quedo_N` reparten esas mismas
        -- veces por dónde acabó: `veces` tiene que ser la suma de las seis.
        --
        -- Con pocas partidas esto sale muy repartido -- trece partidas en
        -- doce casillas son casi todo unos -- y eso no es un fallo de la
        -- tabla, es lo que hay. Se hace legible con muchas partidas.
        --
        -- Mesas de tamaños distintos van juntas, igual que en la vista de
        -- salidas: salir cuarto entre cuatro y entre seis no es lo mismo, y
        -- para eso está `salio_ultimo` en la otra.
        SELECT j.quien,
               -- `salida` y no `salio`: es la misma columna que en «En que
               -- puesto salio cada uno», asi que se llama igual. Y ademas
               -- `salio` colisionaba -- la caja de preguntas lo traduce a
               -- «tirada», como «sale» o «tirado», y esta vista se llevaba
               -- «quien ha tirado monopolios».
               j.salida                                          AS salida,
               COUNT(*)                                          AS veces,
               SUM(CASE WHEN j.puesto = 1 THEN 1 ELSE 0 END)     AS quedo_1,
               SUM(CASE WHEN j.puesto = 2 THEN 1 ELSE 0 END)     AS quedo_2,
               SUM(CASE WHEN j.puesto = 3 THEN 1 ELSE 0 END)     AS quedo_3,
               SUM(CASE WHEN j.puesto = 4 THEN 1 ELSE 0 END)     AS quedo_4,
               SUM(CASE WHEN j.puesto = 5 THEN 1 ELSE 0 END)     AS quedo_5,
               SUM(CASE WHEN j.puesto = 6 THEN 1 ELSE 0 END)     AS quedo_6
          FROM j
         WHERE j.salida IS NOT NULL AND j.puesto IS NOT NULL
         GROUP BY j.quien, j.salida
         ORDER BY j.quien, j.salida
    """},

    {"nombre": "amigos_puntos", "titulo": "De dónde salió cada punto",
     "que": "edificios, premios y — por resta — las cartas de punto",
     "global": "con_amigos = 1", "partida": "game_id = ?",
     "sql": _con(_J, _PTS) + """
        -- La fila suma los puntos del final: poblados + 2 por ciudad + 2 por
        -- cada premio + las cartas de punto. Lo que no cuadra no existe.
        --
        -- `cartas_de_punto` se llamaba `tapados`, que era el nombre de cómo se
        -- calcula (lo que sobra al restar) y no el de lo que es. Se leía como
        -- «algo que no se puede ver» cuando es justo al revés: son los puntos
        -- que la carta te da y que aquí SÍ constan.
        --
        -- Hay una segunda cuenta del mismo número por otro camino
        -- (`cartas_de_punto_del_mod`, la resta de los dos totales que el juego
        -- enseña al acabar). No sale en la tabla: es el mismo número dicho dos
        -- veces, y una columna que siempre repite a la de al lado sólo hace
        -- ruido. Vive en `pts` y quien la vigila es la prueba, que es donde
        -- sirve de algo.
        SELECT game_id AS partida, dia, quien, color, puesto, puntos,
               poblados, ciudades, carretera_larga, mayor_ejercito,
               cartas_de_punto
          FROM pts
         -- La más reciente arriba, como en «Las partidas»; el porqué
         -- está escrito allí. Lo de DENTRO de cada partida no se toca:
         -- una partida se lee hacia adelante.
         ORDER BY game_id DESC, puesto
    """},

    {"nombre": "amigos_desarrollo", "titulo": "Cartas de desarrollo",
     "que": "qué le tocó a cada uno de las cartas que compró",
     "global": "con_amigos = 1", "partida": "game_id = ?",
     "sql": _con(_J, _PTS, _CARTAS) + """
        SELECT * FROM cartas ORDER BY compradas DESC
    """},

    {"nombre": "amigos_mazo", "titulo": "El mazo",
     "que": "qué salió contra lo que el mazo lleva dentro",
     "global": "con_amigos = 1", "partida": "game_id = ?",
     "sql": _con(_J, _PTS, _CARTAS, _MAZOS) + """
        -- Lo que salió, PARTIDA A PARTIDA, porque el mazo no es el mismo en
        -- todas: con 5 o con 6 se juega con la ampliación y son 34 cartas en
        -- vez de 25. Sumarlo todo y compararlo contra un mazo único es lo que
        -- hacía antes, y en cuanto se mezcla una mesa de seis con las de
        -- cuatro el «esperado» sale mal sin avisar.
        , porpartida AS (
            SELECT m.game_id, m.jugadores,
                   (SELECT COUNT(*) FROM dev_card_plays d
                     WHERE d.game_id = m.game_id
                       AND d.card_type = 'Caballero'
                       AND d.player_id IN (SELECT player_id FROM j))   AS caballero,
                   (SELECT COUNT(*) FROM dev_card_plays d
                     WHERE d.game_id = m.game_id
                       AND d.card_type = 'Invencion'
                       AND d.player_id IN (SELECT player_id FROM j))   AS invencion,
                   (SELECT COUNT(*) FROM dev_card_plays d
                     WHERE d.game_id = m.game_id
                       AND d.card_type = 'Monopolio'
                       AND d.player_id IN (SELECT player_id FROM j))   AS monopolio,
                   (SELECT COUNT(*) FROM dev_card_plays d
                     WHERE d.game_id = m.game_id
                       AND d.card_type = 'Construccion de carreteras'
                       AND d.player_id IN (SELECT player_id FROM j))   AS carreteras,
                   -- NULL si esta partida no se puede cuadrar. Se mira por
                   -- partida y no por persona: así una partida vieja sin los
                   -- premios se lleva por delante sólo sus cartas, no todas
                   -- las de quien jugó en ella.
                   (SELECT CASE WHEN SUM(pt.cartas_de_punto IS NULL) > 0 THEN NULL
                                ELSE SUM(pt.cartas_de_punto) END
                      FROM pts pt WHERE pt.game_id = m.game_id)        AS punto_victoria
              FROM (SELECT DISTINCT game_id, jugadores FROM j) m
        ),
        -- Cuántas tendrían que haber salido: lo de cada partida repartido
        -- según SU mazo, y luego sumado. Si todas las partidas son de cuatro
        -- da exactamente lo de siempre.
        esperado AS (
            SELECT SUM(p.n * z.caballero      / (z.total * 1.0)) AS caballero,
                   SUM(p.n * z.punto_victoria / (z.total * 1.0)) AS punto_victoria,
                   SUM(p.n * z.carreteras     / (z.total * 1.0)) AS carreteras,
                   SUM(p.n * z.invencion      / (z.total * 1.0)) AS invencion,
                   SUM(p.n * z.monopolio      / (z.total * 1.0)) AS monopolio,
                   SUM(p.n)                                      AS n
              FROM (SELECT jugadores,
                           caballero + invencion + monopolio + carreteras
                                     + COALESCE(punto_victoria, 0)     AS n
                      FROM porpartida) p
              JOIN mazos z ON z.eran = p.jugadores
        ),
        -- CUANTAS CARTAS HABIA Y CUANTAS SE TOCARON. Sin esto la tabla
        -- ensena lo que salio y no contra que: en la partida 13 salieron 10
        -- cartas y parece mucho o poco segun con que se compare. El mazo
        -- eran 25 y se compraron 14, o sea que once no las toco nadie.
        --
        -- `todas` cuenta las compras de TODOS los de la mesa y no solo las
        -- de los amigos, porque el mazo es uno para todos: una carta que
        -- compro un bot tampoco esta ya en el mazo. Hoy da igual (en las
        -- partidas con amigos no ha jugado ningun bot: 168 compras y las
        -- 168 son de amigos) pero el dia que juegue uno, esto seguira
        -- cuadrando y la ultima fila lo dira.
        sobras AS (
            SELECT SUM(z.total)                                  AS del_mazo,
                   SUM((SELECT COUNT(*) FROM dev_card_purchases c
                          JOIN players pl ON pl.player_id = c.player_id
                         WHERE pl.game_id = g.game_id))          AS todas,
                   (SELECT SUM(compradas) FROM cartas)           AS de_amigos
              FROM (SELECT DISTINCT game_id, jugadores FROM j) g
              JOIN mazos z ON z.eran = g.jugadores
        ),
        salidas AS (
            SELECT 1 AS orden, 'Caballero' AS carta,
                   (SELECT SUM(caballero) FROM porpartida)      AS salieron,
                   (SELECT caballero FROM esperado)             AS esperadas
            UNION ALL SELECT 2, 'Punto de victoria',
                   (SELECT SUM(punto_victoria) FROM porpartida),
                   (SELECT punto_victoria FROM esperado)
            UNION ALL SELECT 3, 'Construccion de carreteras',
                   (SELECT SUM(carreteras) FROM porpartida),
                   (SELECT carreteras FROM esperado)
            UNION ALL SELECT 4, 'Invencion',
                   (SELECT SUM(invencion) FROM porpartida),
                   (SELECT invencion FROM esperado)
            UNION ALL SELECT 5, 'Monopolio',
                   (SELECT SUM(monopolio) FROM porpartida),
                   (SELECT monopolio FROM esperado)
            -- Compradas y nunca jugadas: siguen en la mano al acabar. No
            -- se sabe QUE son, y por eso no llevan ni «deberian salir» ni
            -- porcentaje: meterlas en la comparacion seria repartirlas a
            -- ojo entre los cinco tipos.
            UNION ALL SELECT 6, 'compradas y sin jugar',
                   (SELECT SUM(sin_saber) FROM cartas), NULL
            -- Las que se quedaron en el mazo: nadie las compro y nadie las
            -- vio. Cierran la cuenta -- jugadas + en la mano + estas = el
            -- mazo entero -- y hay una prueba que lo comprueba.
            UNION ALL SELECT 7, 'nunca se compraron',
                   (SELECT del_mazo - todas FROM sobras), NULL
            -- Solo sale si alguien de fuera del grupo compro cartas (un bot,
            -- o alguien que no es de los amigos). Si no, no hay fila: una
            -- linea con un 0 clavado es ruido.
            UNION ALL SELECT 8, 'las compraron otros',
                   (SELECT todas - de_amigos FROM sobras), NULL
             WHERE (SELECT todas - de_amigos FROM sobras) > 0
        )
        -- Igual que en las tiradas: al lado de cada porcentaje, el mismo dato
        -- en cartas. «20,0 contra 20,0» y «5 de 25» dicen lo mismo, pero sólo
        -- el segundo se puede comparar con lo que uno se acuerda de la
        -- partida. La fila «sin saber» no tiene esperado porque no es una
        -- carta del mazo, es lo que quedó sin identificar.
        SELECT s.carta, s.salieron,
               ROUND(s.esperadas, 1)                            AS deberian_salir,
               -- La fila «sin saber» se queda sin porcentaje a propósito:
               -- no es una carta del mazo, es lo que no se pudo identificar,
               -- y darle un tanto por ciento la metería en la comparación.
               CASE WHEN s.esperadas IS NULL THEN NULL ELSE
                   ROUND(100.0 * s.salieron
                         / NULLIF((SELECT n FROM esperado), 0), 1)
               END                                              AS porcentaje,
               -- Que parte del mazo es esta carta. Se llama igual que
               -- en «Las tiradas» a proposito: alli `porcentaje` es la parte
               -- de las tiradas que se llevo ese numero y `porcentaje_normal`
               -- la que le tocaba por los dados. Aqui es lo mismo con cartas,
               -- y son las dos columnas que hay que mirar juntas: 70 contra
               -- 56 es que salieron mas caballeros de los que el mazo lleva.
               --
               -- Con mesas de tamanos distintos mezcladas no hay UN mazo,
               -- asi que es la media de los que se usaron, pesada por lo que
               -- salio en cada uno.
               ROUND(100.0 * s.esperadas
                     / NULLIF((SELECT n FROM esperado), 0), 1)  AS porcentaje_normal
          FROM salidas s
         ORDER BY s.orden
    """},

    {"nombre": "amigos_monopolios", "titulo": "Los monopolios",
     "que": "quién tiró cada monopolio y qué recurso pidió",
     "vacio": "Ninguno todavía. Si en la partida se jugó alguno y aquí no "
              "sale, es que la carta no llegó a apuntarse: el recurso sólo "
              "se engancha a una jugada del mismo jugador y el mismo turno.",
     "global": "con_amigos = 1", "partida": "game_id = ?",
     "sql": _con(_J) + """
        -- Una fila por monopolio jugado. El recurso NO viene con la carta:
        -- el juego apunta «juega una carta de desarrollo» sin decir cuál y
        -- manda el recurso en la acción de después. El importador los une.
        --
        -- `les_saco` es cuántas cartas se llevó en total, y sale NULL
        -- mientras no haya una grabación que lo traiga -- no 0, que querría
        -- decir que no se llevó nada. Lo de quién soltó qué está en
        -- `amigos_monopolios_a_quien`.
        SELECT j.game_id                        AS partida,
               j.dia,
               d.turn_number                    AS turno,
               j.quien,
               COALESCE(d.resource, 'sin saber') AS pidio,
               (SELECT SUM(t.amount) FROM monopoly_takes t
                 WHERE t.play_id = d.play_id)   AS les_saco,
               -- El desglose aquí mismo, para no tener que saltar a la otra
               -- vista sólo para ver a quién le dolió. `t.play_id = d.play_id`
               -- lo ata a ESTE monopolio y no a los del mismo jugador en otra
               -- partida, que es donde se cuela el doble conteo.
               --
               -- Un 0 se enseña igual que un 2: cuando el reparto está
               -- grabado, «no soltó nada» es un dato, no un hueco.
               (SELECT group_concat(x, ', ') FROM (
                   SELECT v.quien || ' ' || t.amount AS x
                     FROM monopoly_takes t
                     JOIN j v ON v.player_id = t.victim_id
                    WHERE t.play_id = d.play_id AND t.amount IS NOT NULL
                    ORDER BY t.amount DESC, v.quien))  AS de_quien
          FROM j
          JOIN dev_card_plays d ON d.player_id = j.player_id
         WHERE d.card_type = 'Monopolio'
         -- La más reciente arriba, como en «Las partidas»; el porqué
         -- está escrito allí. Lo de DENTRO de cada partida no se toca:
         -- una partida se lee hacia adelante.
         ORDER BY j.game_id DESC, d.turn_number
    """},

    {"nombre": "amigos_monopolios_a_quien", "titulo": "El monopolio, uno a uno",
     "que": "cuántas cartas de cada recurso le ha sacado cada uno a cada uno",
     "vacio": "Aquí sólo entran los monopolios de los que se sabe cuánto se "
              "llevaron. Si en esta partida se jugó alguno y no sale, es de "
              "antes del 22/8/2026: el mod no leía el reparto todavía. Están "
              "en «Los monopolios», con quién lo tiró y qué pidió.",
     "global": "con_amigos = 1", "partida": "game_id = ?",
     "sql": _con(_J) + """
        -- Una fila por PAREJA, igual que `amigos_ladron_a_quien`. Es lo que
        -- hace que el desplegable de partida baste: pidiendo todas sale el
        -- total de siempre, y pidiendo una, lo de esa. Antes esto listaba un
        -- evento por fila y hubo que añadir una tercera vista para tener los
        -- totales -- que es justo lo que el filtro ya hacía.
        --
        -- Monopolio a monopolio, con el desglose de quién soltó qué, está en
        -- «Los monopolios», que es la vista de eventos.
        --
        -- A QUIÉN afecta no hay que apuntarlo: un monopolio se lleva ese
        -- recurso de toda la mesa, así que los rivales salen de `j`. Por eso
        -- aparece hasta quien no soltó nada.
        --
        -- SÓLO LOS MONOPOLIOS CON REPARTO GRABADO. Un monopolio del que no
        -- se sabe cuánto se llevó no cuenta aquí: no aporta una cifra y sí
        -- ocupa una fila, y trece filas con un guion tapan las que sí dicen
        -- algo. Los de antes del 22/8/2026 siguen estando en «Los
        -- monopolios», uno por uno y con su `les_saco` vacío, que es donde
        -- toca verlos.
        --
        -- Por eso aquí no hay ni un NULL: todas las cifras son cifras.
        --
        -- Los rivales salen de la propia tabla del reparto y no cruzando `j`
        -- consigo misma. Se puede porque el importador apunta una fila por
        -- CADA rival cuando el reparto llega -- con un 0 si no soltó nada --
        -- así que la cobertura ya está completa. Y de paso se evita el cruce
        -- por `game_id`, que es donde `amigos_puertos` se equivocó.
        , uno AS (
            SELECT j.quien        AS quien,
                   v.quien        AS a_quien,
                   d.play_id,
                   d.turn_number  AS turno,
                   d.resource,
                   t.amount
              FROM j
              JOIN dev_card_plays d ON d.player_id = j.player_id
                                   AND d.card_type = 'Monopolio'
              JOIN monopoly_takes t ON t.play_id = d.play_id
                                   AND t.amount IS NOT NULL
              JOIN j v ON v.player_id = t.victim_id
        )
        -- Una columna por recurso, como en `amigos_produccion`, y no una
        -- lista de nombres: la lista dice CUÁLES y la pregunta es CUÁNTOS de
        -- cada uno. Con cincuenta partidas es lo que deja ver el patrón --
        -- «a éste siempre le quita el trigo» -- que en una sola columna de
        -- total no se ve.
        SELECT quien, a_quien,
               COUNT(DISTINCT play_id)                   AS monopolios,
               -- En que turnos fue. Una pareja puede tener varios, asi que
               -- no cabe UN turno: caben todos, en orden. Con la lista
               -- delante se ve si fue una racha o si le tiene tomada la
               -- matricula desde el principio.
               (SELECT group_concat(x, ', ') FROM
                  (SELECT DISTINCT u2.turno AS x FROM uno u2
                    WHERE u2.quien = uno.quien AND u2.a_quien = uno.a_quien
                      AND u2.turno IS NOT NULL
                    ORDER BY u2.turno))                  AS turnos,
               COALESCE(SUM(CASE WHEN resource='Madera'   THEN amount END), 0) AS madera,
               COALESCE(SUM(CASE WHEN resource='Arcilla'  THEN amount END), 0) AS arcilla,
               COALESCE(SUM(CASE WHEN resource='Lana'     THEN amount END), 0) AS lana,
               COALESCE(SUM(CASE WHEN resource='Cereales' THEN amount END), 0) AS cereales,
               COALESCE(SUM(CASE WHEN resource='Mineral'  THEN amount END), 0) AS mineral,
               SUM(amount)                               AS cartas
          FROM uno
         GROUP BY quien, a_quien
         ORDER BY cartas DESC, monopolios DESC, quien
    """},

    {"nombre": "amigos_ladron", "titulo": "El ladrón",
     "que": "recursos que no dejó producir, contra los que sí se cobraron",
     "global": "con_amigos = 1", "partida": "game_id = ?",
     "sql": _con(_J) + """
        -- Desglosado por recurso, que sale de la casilla que tapó el ladrón.
        -- «Quién ha perdido más» y «qué le quitaron» son la misma pregunta
        -- dicha entera, y tenerlas en dos vistas obligaba a mirar dos sitios
        -- para contestarla. El desglose por PAREJAS -- quién se lo hizo --
        -- sigue en «El ladrón, uno a uno», que es otra cosa.
        --
        -- TRES COSAS Y NO UNA, y hay que separarlas o la tabla engaña. Se
        -- llamaba `veces` a secas y se leia como «veces que me lo pusieron»,
        -- que es otra cosa y mas del doble: 21 contra 8 en la partida 16.
        --
        --   se_lo_pusieron -- veces que alguien movio el ladron a una casilla
        --                     suya. Es lo que uno recuerda.
        --   le_bloquearon  -- veces que ademas salio el numero y se quedo
        --                     sin cobrar. Es lo que paso de verdad, y OJO:
        --                     puede ser mayor que la anterior. Una puesta
        --                     que se queda tres tiradas son tres bloqueos.
        --                     Pasa en 3 de las 14 partidas, asi que no es
        --                     un caso raro que se pueda contar mal.
        --   perdido        -- cuantas cartas eran. Es el daño.
        --
        -- Poner el ladron encima de alguien y que no le salga el numero en
        -- diez turnos no le cuesta nada, y la mitad de las veces es lo que
        -- pasa. Sin la primera columna esa mitad no se ve y el ladron parece
        -- inofensivo; sin la segunda, parece devastador.
        --
        -- `se_lo_pusieron` y `se_lo_puso` de «El ladron, uno a uno» son la
        -- misma cuenta -- mismo `bu.timestamp <= m.timestamp` -- CON UNA
        -- DIFERENCIA que hay que decir, porque el comentario que habia aqui
        -- decia «para que las dos tablas cuadren al sumarlas» y era falso:
        --
        --   sumando la de parejas por `a_quien`  ->  69
        --   esta columna                         ->  68
        --
        -- El uno que sobra es PONERSELO A UNO MISMO. Alli sale, en una fila
        -- con la misma persona en las dos columnas, a proposito y explicado
        -- en esa vista; aqui no, porque la pregunta es «cuantas veces me lo
        -- pusieron» y ponertelo tu no cuenta. Pasa dos veces en 194
        -- movimientos, o sea poco y no cero -- que es justo el tipo de
        -- diferencia que nadie mira hasta que le cuadra mal una suma.
        --
        -- La relacion exacta la fija una prueba: esta columna es la suma de
        -- la otra por `a_quien` MENOS las filas de uno consigo mismo.
        SELECT j.quien,
               (SELECT COUNT(DISTINCT m.move_id)
                  FROM robber_moves m
                  JOIN building_tiles bt ON bt.tile_id = m.tile_id
                  JOIN buildings bu ON bu.building_id = bt.building_id
                  JOIN j jb ON jb.player_id = bu.player_id
                  JOIN j jm ON jm.player_id = m.player_id
                 WHERE jb.quien = j.quien
                   AND jm.quien <> j.quien
                   AND bu.timestamp <= m.timestamp)            AS se_lo_pusieron,
               -- PEGADA A LA DE ARRIBA, y no al final entre los cinco
               -- recursos. Son las dos cosas que te hace el ladron y se
               -- cuentan igual, en veces: te tapa una casilla y te roba de
               -- la mano. Enterrada detras del desglose por material se leia
               -- como una nota al pie, y es la mitad del daño -- 72 contra
               -- 70 en la fila mas alta.
               --
               -- `en_total` (produccion perdida + robadas) sigue al final,
               -- que es donde va una suma.
               (SELECT COUNT(*) FROM steals s
                 WHERE s.victim_id IN (SELECT player_id FROM j aj
                                        WHERE aj.quien = j.quien))  AS le_robaron,
               COUNT(b.block_id)                               AS le_bloquearon,
               COALESCE(SUM(b.amount), 0)                      AS perdido,
               COALESCE(SUM(CASE WHEN t.resource='Madera'   THEN b.amount END), 0) AS madera,
               COALESCE(SUM(CASE WHEN t.resource='Arcilla'  THEN b.amount END), 0) AS arcilla,
               COALESCE(SUM(CASE WHEN t.resource='Lana'     THEN b.amount END), 0) AS lana,
               COALESCE(SUM(CASE WHEN t.resource='Cereales' THEN b.amount END), 0) AS cereales,
               COALESCE(SUM(CASE WHEN t.resource='Mineral'  THEN b.amount END), 0) AS mineral,
               -- Sólo producción, y a propósito. El ladrón sólo puede
               -- taparte lo que produce el tablero: no te tapa un trato ni
               -- el reparto inicial. Si aquí entraran las cartas de los
               -- tratos, `perdido` se leería contra un total que incluye
               -- cosas que el ladrón nunca habría podido quitarte, y el
               -- porcentaje saldría más bajo sin querer decir nada.
               --
               -- Se llamaba `cobrado`, que sonaba a todo lo que le entró.
               COALESCE(SUM(b.amount), 0)
                 + (SELECT COUNT(*) FROM steals s
                     WHERE s.victim_id IN (SELECT player_id FROM j aj
                                            WHERE aj.quien = j.quien))
               -- `en_total` y NO `le_costo`, aunque «lo que le costo» sea
               -- justo lo que es. `le_costo` ya existe en «El ladron, uno a
               -- uno» y alli son SOLO los recursos bloqueados -- el robo va
               -- aparte, en `le_robo`. Dos vistas del mismo grupo con la
               -- misma columna queriendo decir dos cosas es el fallo que mas
               -- caro sale aqui: no rompe nada, no lo canta ninguna prueba, y
               -- quien compare las dos tablas saca que la base se contradice.
               -- Un nombre distinto para una cuenta distinta.
                                                               AS en_total,
               COALESCE((SELECT SUM(g.amount) FROM resource_gains g
                          WHERE g.player_id IN (SELECT player_id FROM j aj
                                                 WHERE aj.quien = j.quien)
                            AND g.source = 'produccion'), 0)   AS producido
          FROM j
          LEFT JOIN robber_blocks b ON b.victim_id = j.player_id
          LEFT JOIN tiles t ON t.tile_id = b.tile_id
         GROUP BY j.quien
         ORDER BY perdido DESC
    """},

    {"nombre": "amigos_ladron_proporcion",
     "titulo": "¿A quién se ceba el ladrón?",
     "que": "si a alguien le ponen el ladrón más de lo que le toca, "
            "descontando cuánto juega y cuántas casillas tiene",
     "global": "con_amigos = 1", "partida": "game_id = ?",
     "sql": _con(_J) + """
        -- «El ladron» cuenta VECES y esta dice si esas veces son muchas o
        -- las que tocan. Van en dos tablas y no en una: la primera se lee de
        -- un vistazo --«a este le han puesto 109 ladrones»-- y esta pide
        -- leerse las columnas en orden. Juntas eran dieciseis en una fila y
        -- no se entendia ninguna.
        --
        -- TRES SESGOS QUE HAY QUE QUITAR, y en este orden:
        --
        -- 1. CUANTO JUEGA. Con trece partidas te ponen el ladron mas veces
        --    que con siete aunque nadie te tenga mania.
        -- 2. CUANTO DURAN. «Por partida» no arregla lo anterior: una partida
        --    de sesenta turnos tiene el doble de sietes que una de treinta.
        --    Los dos se van con el mismo denominador: cuantas veces movieron
        --    el ladron LOS OTROS en sus partidas (`movimientos`).
        -- 3. CUANTAS CASILLAS TIENE. Quien mas construye se come mas
        --    ladrones sin que nadie le apunte. Este es el de `le_tocaban`.
        --
        -- Y AQUI EL ERROR QUE TUVO ESTA VISTA EL PRIMER DIA, que es el que
        -- hay que entender para leerla. La primera version comparaba con un
        -- ladron CIEGO -- tirado sobre una casilla ocupada cualquiera -- y
        -- con eso TODO EL MUNDO salia por encima de lo normal, lo cual es
        -- imposible como grupo. Medido: un ladron puesto a mano pilla 1,49
        -- personas por movimiento y uno tirado al azar 1,14, o sea un 31%
        -- mas. Claro que todos salian altos: el ladron se pone A ALGUIEN a
        -- proposito y encima se busca la casilla que pilla a varios.
        --
        -- Comparar contra el ciego mezcla dos cosas: lo agresivo que se pone
        -- el ladron en esta mesa (que es igual para todos) y a quien se lo
        -- ponen (que es la pregunta). La referencia buena da por bueno lo
        -- primero y solo pregunta lo segundo: DE CADA MOVIMIENTO SE TOMA A
        -- CUANTA GENTE PILLO, y se reparte entre los jugadores segun las
        -- casillas que tenia cada uno en ese momento.
        --
        -- Con eso el 1,00 -- aqui 100, que se lee como en «La suerte de cada
        -- uno» -- SI es el punto neutro, porque lo repartido suma exactamente
        -- lo que paso. Ahora hay gente por encima y gente por debajo, que es
        -- lo que tiene que pasar, y los numeros son mucho mas modestos: el
        -- mas perseguido pasa de un 1,58 inventado a un 116 de verdad.
        , movidas AS (
            SELECT m.move_id, m.game_id, m.timestamp, m.player_id AS movio,
                   m.tile_id
              FROM robber_moves m
             WHERE m.tile_id IS NOT NULL
               AND m.game_id IN (SELECT game_id FROM j)
        ),
        -- Una fila por movimiento y por cada persona que NO lo movio:
        -- cuantas casillas suyas habia puestas y si le cayo encima.
        --
        -- `bu.timestamp <= md.timestamp` en las dos: una casilla construida
        -- DESPUES ni podia recibir el ladron ni contaba para el reparto.
        cruce AS (
            SELECT md.move_id, j.quien,
                   (SELECT COUNT(DISTINCT bt.tile_id)
                      FROM buildings bu
                      JOIN building_tiles bt ON bt.building_id = bu.building_id
                      JOIN j jj ON jj.player_id = bu.player_id
                     WHERE jj.quien = j.quien AND jj.game_id = md.game_id
                       AND bu.timestamp <= md.timestamp)         AS suyas,
                   (SELECT COUNT(*) FROM building_tiles bt2
                      JOIN buildings b2
                        ON b2.building_id = bt2.building_id
                       AND b2.timestamp <= md.timestamp
                      JOIN j j2 ON j2.player_id = b2.player_id
                     WHERE bt2.tile_id = md.tile_id
                       AND j2.quien = j.quien)                   AS le_cayo
              FROM movidas md
              JOIN j ON j.game_id = md.game_id
             WHERE md.movio <> j.player_id
             GROUP BY md.move_id, j.quien
        ),
        -- Lo que hace que el 100 sea el 100: por cada movimiento, A CUANTOS
        -- pillo de verdad y cuantas casillas habia entre todos. Eso es lo
        -- que se reparte.
        pormovimiento AS (
            SELECT move_id,
                   SUM(CASE WHEN le_cayo > 0 THEN 1 ELSE 0 END)  AS a_cuantos,
                   SUM(suyas)                                    AS entre_todos
              FROM cruce
             GROUP BY move_id
        )
        SELECT c.quien,
               -- Sobre cuantos movimientos esta medido todo lo demas. Va
               -- delante por lo mismo que `tiradas_contadas` en la suerte:
               -- un 116 y un 63 parecen comparables y uno sale de 197
               -- movimientos y el otro de 7.
               COUNT(*)                                          AS movimientos,
               SUM(CASE WHEN c.le_cayo > 0 THEN 1 ELSE 0 END)    AS se_lo_pusieron,
               -- Sin descontar NADA: de los movimientos de sus partidas,
               -- cuantos le cayeron. Quien quiera saber a quien le cae mas
               -- el ladron -- casillas incluidas, que tener muchas tambien
               -- es parte del juego -- mira esta y no las de al lado.
               ROUND(100.0 * SUM(CASE WHEN c.le_cayo > 0 THEN 1 ELSE 0 END)
                     / COUNT(*), 1)                              AS porcentaje,
               -- Y cuantos le TOCABAN. Un numero, no un porcentaje, para que
               -- se lea contra `se_lo_pusieron` que esta al lado: 109 contra
               -- 94,3 se compara solo.
               ROUND(SUM(1.0 * pm.a_cuantos * c.suyas
                         / NULLIF(pm.entre_todos, 0)), 1)        AS le_tocaban,
               -- EL NUMERO QUE CONTESTA LA PREGUNTA. 100 es lo que toca;
               -- por encima se ceban con el y por debajo le dejan en paz.
               -- Se lee igual que `suerte` en «La suerte de cada uno», y a
               -- proposito: es la misma forma -- lo que paso contra lo que
               -- tocaba -- y no hacia falta un segundo idioma.
               ROUND(100.0 * SUM(CASE WHEN c.le_cayo > 0 THEN 1 ELSE 0 END)
                     / NULLIF(SUM(1.0 * pm.a_cuantos * c.suyas
                                  / NULLIF(pm.entre_todos, 0)), 0), 1)
                                                                 AS se_ceban
          FROM cruce c
          JOIN pormovimiento pm ON pm.move_id = c.move_id
         GROUP BY c.quien
         ORDER BY se_ceban DESC
    """},

    {"nombre": "amigos_ladron_a_quien", "titulo": "El ladrón, uno a uno",
     "que": "quién se lo puso a quién, cuántas veces le tocó y qué le costó",
     "global": "con_amigos = 1", "partida": "game_id = ?",
     "sql": _con(_J) + """
        -- Tres cosas distintas que se suelen confundir en una sola:
        --
        --   se_lo_puso  -- veces que movió el ladrón a una casilla donde el
        --                  otro YA tenía algo. Es la intención.
        --   le_bloqueo  -- veces que ademas salió ese número y el otro se
        --                  quedó sin cobrar. Es lo que pasó de verdad.
        --   le_costo    -- recursos que dejó de recibir por eso. Es el daño.
        --   le_robo     -- cartas que le quitó de la mano. Cuántas, no cuáles.
        --
        -- Poner el ladrón encima de alguien y que no le salga el número en
        -- diez turnos no le cuesta nada, y sale igual de agresivo en la
        -- primera columna que en la tercera. Por eso van las tres.
        --
        -- `bu.timestamp <= m.timestamp` no es un detalle: sin eso, un poblado
        -- construido DESPUÉS contaría como si le hubieran puesto el ladrón
        -- encima antes de existir.
        --
        -- PONERSELO A UNO MISMO SALE, en una fila con la misma persona en
        -- las dos columnas. Estuvo excluido de `se_lo_puso` hasta el 2 de
        -- septiembre de 2026, con el argumento de que una fila «Periplo /
        -- Periplo» confunde. El argumento era malo por dos motivos: pasa de
        -- verdad -- dos veces en 194 movimientos -- y sobre todo la vista ya
        -- lo contaba en `le_bloqueo`, que sale de `robber_blocks` y nunca
        -- excluyo nada. O sea que la fila aparecia igual, con un 0 en la
        -- primera columna y un numero en la cuarta: la unica lectura posible
        -- era que la tabla estaba mal.
        --
        -- Que sea legal no lo hace irrelevante: con un 7 a veces no queda
        -- mejor sitio, y a veces se hace a posta para robarle a alguien que
        -- toca esa casilla sin regalarle el bloqueo a un rival.
        , puestas AS (
            SELECT jm.quien AS quien, jb.quien AS a_quien,
                   COUNT(DISTINCT m.move_id) AS se_lo_puso,
                   COUNT(DISTINCT CASE WHEN m.cause='siete'
                                       THEN m.move_id END) AS con_7,
                   COUNT(DISTINCT CASE WHEN m.cause='caballero'
                                       THEN m.move_id END) AS con_caballero
              FROM robber_moves m
              JOIN j jm ON jm.player_id = m.player_id
              JOIN building_tiles bt ON bt.tile_id = m.tile_id
              JOIN buildings bu ON bu.building_id = bt.building_id
              JOIN j jb ON jb.player_id = bu.player_id
             WHERE bu.timestamp <= m.timestamp
             GROUP BY jm.quien, jb.quien
        ),
        golpes AS (
            -- Desglosado por recurso, que sale de la casilla que tapó el
            -- ladrón. Es lo que deja ver el patrón con muchas partidas: «a
            -- éste siempre le corta el trigo» no se ve en una columna de
            -- total.
            --
            -- Ojo: esto desglosa `le_costo`, lo que NO le dejó producir.
            -- `le_robo` no se puede desglosar y no se podrá nunca -- la carta
            -- que te llevas del ladrón no la ve nadie y el mod no la lee.
            SELECT ja.quien AS quien, jv.quien AS a_quien,
                   COUNT(*) AS le_bloqueo, SUM(b.amount) AS le_costo,
                   COALESCE(SUM(CASE WHEN t.resource='Madera'   THEN b.amount END), 0) AS madera,
                   COALESCE(SUM(CASE WHEN t.resource='Arcilla'  THEN b.amount END), 0) AS arcilla,
                   COALESCE(SUM(CASE WHEN t.resource='Lana'     THEN b.amount END), 0) AS lana,
                   COALESCE(SUM(CASE WHEN t.resource='Cereales' THEN b.amount END), 0) AS cereales,
                   COALESCE(SUM(CASE WHEN t.resource='Mineral'  THEN b.amount END), 0) AS mineral
              FROM robber_blocks b
              JOIN j ja ON ja.player_id = b.blocker_id
              JOIN j jv ON jv.player_id = b.victim_id
              JOIN tiles t ON t.tile_id = b.tile_id
             GROUP BY ja.quien, jv.quien
        ),
        manos AS (
            SELECT jt.quien AS quien, jv.quien AS a_quien, COUNT(*) AS le_robo
              FROM steals s
              JOIN j jt ON jt.player_id = s.thief_id
              JOIN j jv ON jv.player_id = s.victim_id
             GROUP BY jt.quien, jv.quien
        ),
        pares AS (
            SELECT quien, a_quien FROM puestas
            UNION SELECT quien, a_quien FROM golpes
            UNION SELECT quien, a_quien FROM manos
        )
        SELECT p.quien, p.a_quien,
               COALESCE(pu.se_lo_puso, 0)  AS se_lo_puso,
               -- Obligado y elegido no es lo mismo: el 7 te obliga a mover el
               -- ladrón a algún sitio, y el caballero lo mueves porque
               -- quieres. Ponerle el ladrón a alguien nueve veces con el 7 es
               -- que te tocó; hacerlo con caballeros es una campaña.
               COALESCE(pu.con_7, 0)         AS con_7,
               COALESCE(pu.con_caballero, 0) AS con_caballero,
               COALESCE(g.le_bloqueo, 0)   AS le_bloqueo,
               COALESCE(g.le_costo, 0)     AS le_costo,
               COALESCE(g.madera, 0)       AS madera,
               COALESCE(g.arcilla, 0)      AS arcilla,
               COALESCE(g.lana, 0)         AS lana,
               COALESCE(g.cereales, 0)     AS cereales,
               COALESCE(g.mineral, 0)      AS mineral,
               COALESCE(m.le_robo, 0)      AS le_robo
          FROM pares p
          LEFT JOIN puestas pu ON pu.quien = p.quien AND pu.a_quien = p.a_quien
          LEFT JOIN golpes  g  ON g.quien  = p.quien AND g.a_quien  = p.a_quien
          LEFT JOIN manos   m  ON m.quien  = p.quien AND m.a_quien  = p.a_quien
         ORDER BY le_costo DESC, se_lo_puso DESC
    """},

    {"nombre": "amigos_ladron_a_quien_numero",
     "titulo": "El ladron: a quien y en que numero",
     "que": "a quien se lo puso cada uno y sobre que numero",
     "global": "con_amigos = 1", "partida": "game_id = ?",
     "sql": _con(_J) + """
        -- POR QUE ESTA SEPARADA DE «El ladron, uno a uno».
        --
        -- Alli se sabe quien se lo puso a quien, y aqui ADEMAS sobre que
        -- numero. Y no duele lo mismo. Ponerselo a alguien en un 11 se
        -- entiende: con un 7 hay que moverlo a algun sitio y a veces no
        -- queda nada mejor, o se busca robarle la carta sin hacer mucho
        -- dano. Ponerselo en un 6 es otra cosa: el 6 sale cinco veces de
        -- cada 36 y el 11 dos, o sea que el mismo movimiento cuesta dos
        -- veces y media mas.
        --
        -- Una fila por (quien, a quien, numero). Es la mas fina de las
        -- cuatro del ladron, asi que con pocas partidas saldran muchas filas
        -- de 1: eso no es un fallo, es lo que hay. Para el total, «El
        -- ladron, uno a uno»; para lo que costo de verdad, tambien, que
        -- aqui solo esta la intencion.
        --
        -- `bu.timestamp <= m.timestamp` por lo mismo que en la otra: sin
        -- eso, un poblado construido DESPUES contaria como si le hubieran
        -- puesto el ladron encima antes de existir.
        --
        -- Ponerselo a uno mismo sale, con la misma persona en las dos
        -- columnas, igual que en la otra vista.
        SELECT jm.quien                     AS quien,
               jb.quien                     AS a_quien,
               t.number                     AS numero,
               COUNT(DISTINCT m.move_id)    AS se_lo_puso,
               COUNT(DISTINCT CASE WHEN m.cause='siete'
                                   THEN m.move_id END)      AS con_7,
               COUNT(DISTINCT CASE WHEN m.cause='caballero'
                                   THEN m.move_id END)      AS con_caballero
          FROM robber_moves m
          JOIN j jm ON jm.player_id = m.player_id
          JOIN tiles t ON t.tile_id = m.tile_id
          JOIN building_tiles bt ON bt.tile_id = m.tile_id
          JOIN buildings bu ON bu.building_id = bt.building_id
          JOIN j jb ON jb.player_id = bu.player_id
         WHERE bu.timestamp <= m.timestamp
           AND t.number IS NOT NULL
         GROUP BY jm.quien, jb.quien, t.number
         ORDER BY se_lo_puso DESC, numero
    """},

    {"nombre": "amigos_ladron_donde", "titulo": "Dónde pone el ladrón cada uno",
     "que": "a qué número lo manda cada uno, cuántas veces, y si por el 7 o con un caballero",
     "global": "con_amigos = 1", "partida": "game_id = ?",
     "sql": _con(_J) + """
        -- Una fila por persona y NÚMERO. Los números se repiten
        -- entre partidas -- cada tablero es distinto -- y juntarlos es lo que
        -- se quiere: la pregunta es «¿a este siempre le tapa el 6?», no qué
        -- hexágono concreto de qué partida.
        --
        -- `con_7` y `con_caballero` no son lo mismo aunque sumen: el 7 te
        -- OBLIGA a mover el ladrón a alguna parte, el caballero lo mueves
        -- porque quieres. Los dos van al lado porque la mezcla es la que
        -- engaña: veinte movimientos al 6 son otra cosa si diecinueve fueron
        -- sietes.
        -- Sin el terreno. Un 6 de arcilla y un 6 de piedra son EL MISMO 6:
        -- el terreno lo pone el tablero de esa partida, no la persona, y
        -- separarlos partía en tres filas de dos lo que son seis veces al 6.
        -- La pregunta que se lee aquí es «¿a este siempre le tapan el 6?», y
        -- con las filas partidas no se puede contestar de un vistazo.
        --
        -- Lo que el ladrón le CUESTA por recurso -- que es otra cosa y más
        -- útil, porque un ladrón en una casilla que no es tuya no cuesta
        -- nada -- está desglosado en «El ladrón» y en «El ladrón, uno a uno».
        SELECT j.quien,
               t.number                                       AS numero,
               COUNT(*)                                       AS veces,
               SUM(CASE WHEN m.cause='siete' THEN 1 ELSE 0 END)     AS con_7,
               SUM(CASE WHEN m.cause='caballero' THEN 1 ELSE 0 END) AS con_caballero,
               -- ENCIMA DE LO SUYO. Pasa, y hasta hoy no salia en ningun
               -- sitio: «El ladron, uno a uno» va por parejas y deja fuera
               -- ponerselo a uno mismo -- una fila «Periplo / Periplo»
               -- confunde mas de lo que aclara -- y aqui se contaba el
               -- movimiento sin decir sobre quien caia. El movimiento
               -- constaba; el detalle no. Ahora si.
               --
               -- Se hace con las mismas dos condiciones que `se_lo_puso`:
               -- que la casilla toque una pieza suya y que la pieza
               -- estuviera puesta ANTES del movimiento. Sin lo segundo, un
               -- poblado construido despues contaria como si se hubiera
               -- tapado a si mismo antes de existir.
               SUM(CASE WHEN EXISTS (
                     SELECT 1 FROM building_tiles bt
                       JOIN buildings bu ON bu.building_id = bt.building_id
                      WHERE bt.tile_id = m.tile_id
                        AND bu.player_id = m.player_id
                        AND bu.timestamp <= m.timestamp)
                    THEN 1 ELSE 0 END)                        AS a_si_mismo
          FROM j
          JOIN robber_moves m ON m.player_id = j.player_id
          JOIN tiles t ON t.tile_id = m.tile_id
         GROUP BY j.quien, t.number
         -- Por persona primero: lo que se lee aqui es «que hace ESTE», y con
         -- las filas de cada uno separadas por medio tablero no se lee. El
         -- «cual es el numero mas tapado de todos» se saca ahora tocando la
         -- cabecera de `veces` en el panel.
         ORDER BY j.quien, veces DESC, numero
    """},

    {"nombre": "amigos_ladron_numeros",
     "titulo": "Los números que más tapa el ladrón",
     "que": "a qué números va el ladrón, sumando a todo el mundo",
     "global": "con_amigos = 1", "partida": "game_id = ?",
     "sql": _con(_J) + """
        -- La misma tabla que «Dónde pone el ladrón cada uno» pero SIN la
        -- persona. No es la misma pregunta con otro orden: ahí se lee «¿qué
        -- hace éste?» y aquí «¿qué número se come más ladrón en esta mesa?»,
        -- y esa segunda no se puede contestar mirando la otra -- habría que
        -- sumar a mano las filas de cuatro personas.
        --
        -- Los números se juntan entre partidas a propósito: cada tablero es
        -- distinto, así que el 6 puede ser madera en una y mineral en otra, y
        -- la pregunta es «¿qué número se come el ladrón?», no cuál de los
        -- hexágonos de una partida concreta. El terreno de cada uno está en
        -- «Dónde pone el ladrón cada uno», que es donde se puede cruzar con
        -- la persona.
        SELECT t.number                                        AS numero,
               COUNT(*)                                        AS veces,
               SUM(CASE WHEN m.cause='siete' THEN 1 ELSE 0 END)     AS con_7,
               SUM(CASE WHEN m.cause='caballero' THEN 1 ELSE 0 END) AS con_caballero,
               COUNT(DISTINCT j.quien)                         AS personas
          FROM j
          JOIN robber_moves m ON m.player_id = j.player_id
          JOIN tiles t ON t.tile_id = m.tile_id
         GROUP BY t.number
         ORDER BY veces DESC, numero
    """},

    {"nombre": "amigos_produccion", "titulo": "Producción",
     "que": "qué recursos le dio el tablero a cada uno, y de qué anda corto",
     "global": "con_amigos = 1", "partida": "game_id = ?",
     "sql": _con(_J) + """
        -- Sólo lo que produjo el tablero: tiradas y colocación inicial. Sin
        -- comercios ni robos, porque el mod no lee las manos de nadie.
        SELECT j.quien,
               COALESCE(SUM(CASE WHEN g.resource='Madera'   THEN g.amount END), 0) AS madera,
               COALESCE(SUM(CASE WHEN g.resource='Arcilla'  THEN g.amount END), 0) AS arcilla,
               COALESCE(SUM(CASE WHEN g.resource='Lana'     THEN g.amount END), 0) AS lana,
               COALESCE(SUM(CASE WHEN g.resource='Cereales' THEN g.amount END), 0) AS cereales,
               COALESCE(SUM(CASE WHEN g.resource='Mineral'  THEN g.amount END), 0) AS mineral,
               COALESCE(SUM(g.amount), 0)                                          AS total,
               -- De ese total, cuánto fue el REPARTO INICIAL. Está
               -- porque sin ella dos vistas se contradicen a la vista: aquí
               -- `total` es todo lo que dio el tablero -- el reparto del
               -- segundo poblado incluido, que también lo da el tablero -- y
               -- `producido` de «El ladrón» es sólo lo que salió al tirar.
               -- 573 contra 544, y la diferencia son exactamente estas
               -- cartas. Cada número es el bueno para su pregunta; lo que
               -- faltaba era poder ver de dónde sale la resta.
               COALESCE(SUM(CASE WHEN g.source = 'inicial'
                                 THEN g.amount END), 0)                            AS del_reparto,
               (SELECT COALESCE(SUM(b.amount), 0) FROM robber_blocks b
                 WHERE b.victim_id IN (SELECT player_id FROM j aj
                                        WHERE aj.quien = j.quien))                 AS le_quito_el_ladron
          FROM j
          LEFT JOIN resource_gains g ON g.player_id = j.player_id
         GROUP BY j.quien
         ORDER BY total DESC
    """},

    {"nombre": "amigos_numeros", "titulo": "Los números de cada uno",
     "que": "en qué números se puso, cuántas veces salieron y qué sacó",
     "global": "con_amigos = 1", "partida": "game_id = ?",
     "sql": _con(_J) + """
        -- Separa «elegiste mal» de «tuviste mala suerte». `edificios` son las
        -- piezas que tenía en ese número al acabar; `veces_salio` es cuántas
        -- veces lo sacaron los dados en sus partidas; `producido` lo que
        -- le llegó de verdad -- que es menos si el ladrón estaba encima.
        --
        -- UNA FILA POR PERSONA Y NÚMERO, juntando todas las partidas. Iba por
        -- partida, con este argumento escrito aquí: «el 6 de una partida y el
        -- 6 de otra están en casillas distintas y sumarlos no querría decir
        -- nada». El argumento vale para el TABLERO y no para lo que mide esta
        -- tabla: cuántas veces te ha salido el 6 teniendo algo puesto en un 6,
        -- y cuánto te ha pagado, se suman perfectamente entre partidas -- son
        -- tiradas y son cartas. Y sumado es cuando dice algo: 331 filas de
        -- una o dos partidas no enseñan la costumbre de nadie.
        --
        -- Lo que NO se puede leer aquí es un tablero concreto. Para eso está
        -- el desplegable de partida, que filtra esta misma tabla.
        --
        -- Se calcula por partida y se suma después, no de golpe: `veces_salio`
        -- son las tiradas DE LAS PARTIDAS EN QUE tenía algo en ese número, y
        -- eso no se puede sacar sin pasar por la partida. Contando de golpe
        -- saldrían las tiradas de todas, también las de partidas en las que no
        -- tenía nada ahí.
        , porpartida AS (
        SELECT j.game_id                                   AS partida,
               j.quien,
               t.number                                    AS numero,
               COUNT(DISTINCT bt.building_id)              AS edificios,
               -- Turno en que puso su PRIMERA pieza en ese número; 0 es el
               -- reparto inicial. Está aquí porque `veces_salio` cuenta las
               -- tiradas de TODA la partida, también las de antes de que
               -- pusiera nada: tener el 6 desde el turno 0 y tenerlo desde el
               -- 30 sale igual en esa columna y no es lo mismo.
               --
               -- `buildings.turn_number` es cuándo apareció el poblado y no
               -- se toca al mejorar a ciudad (eso va en `upgraded_at`), que
               -- es justo lo que hace falta: desde cuándo cobra ahí.
               MIN(bu.turn_number)                         AS primer_poblado,
               -- Los puntitos que la ficha lleva debajo del número, que no
               -- son adorno: son de cuántas de las 36 combinaciones de dos
               -- dados sale ese número. El 6 lleva cinco, el 2 lleva uno. Es
               -- lo que vale un sitio antes de tirar, y no depende de la
               -- partida.
               --
               -- Se llamaban `combinaciones` aquí y `pips` en la de la
               -- suerte, que es la misma cosa con dos nombres y ninguno de
               -- los dos se entiende sin explicarlo. `puntitos` se entiende
               -- mirando la ficha.
               6 - ABS(7 - t.number)                       AS puntitos,
               (SELECT COUNT(*) FROM rolls r
                 WHERE r.game_id = j.game_id
                   AND r.value = t.number)                 AS veces_salio,
               -- Cuántas veces DEBERÍA haber salido en esta partida. Con
               -- `veces_salio` al lado, ahí se separa «elegí mal» de «tuve
               -- mala suerte» sin tener que echar cuentas.
               ROUND((SELECT COUNT(*) FROM rolls r WHERE r.game_id = j.game_id)
                     * (6 - ABS(7 - t.number)) / 36.0, 1)  AS deberia_salir,
               (SELECT COALESCE(SUM(g.amount), 0)
                  FROM resource_gains g JOIN rolls r ON r.roll_id = g.roll_id
                 WHERE g.player_id = j.player_id
                   AND r.value = t.number)                 AS producido
          FROM j
          JOIN buildings bu ON bu.player_id = j.player_id
          JOIN building_tiles bt ON bt.building_id = bu.building_id
          JOIN tiles t ON t.tile_id = bt.tile_id
         WHERE t.number IS NOT NULL
         GROUP BY j.game_id, j.quien, j.player_id, t.number
        )
        -- LOS DIEZ NUMEROS SALEN SIEMPRE, tenga o no tenga algo puesto.
        -- Antes la tabla se hacía sobre los edificios, así que un número en
        -- el que nunca puso nada no tenía fila -- y ese es de los más
        -- interesantes que hay: «no tenías NADA en el 6» dice más que la
        -- mitad de las filas que sí salían. Es lo mismo que hace «Las
        -- tiradas» con los once números del dado, y por el mismo motivo.
        --
        -- Son DIEZ y no once: el 7 no está, porque no hay ninguna ficha con
        -- un 7. Ahí va el desierto. En «Las tiradas» sí sale, que allí se
        -- cuenta lo que sacan los dados y un 7 se saca.
        --
        -- Comprobado que los dos tableros llevan los mismos diez: el de 19
        -- casillas y el de 30 reparten distinto, pero ninguno estrena un
        -- número que el otro no tenga.
        , numeros(numero) AS (
            VALUES (2),(3),(4),(5),(6),(8),(9),(10),(11),(12)
        ),
        gente AS (SELECT DISTINCT quien FROM j)
        SELECT g.quien,
               n.numero,
               COALESCE(SUM(p.edificios), 0)               AS edificios,
               -- La MEDIA de los turnos en que lo estrenó, no el más pronto.
               -- `veces_salio` es una suma de partidas, así que lo que se lee
               -- al lado tiene que valer para todas: quien lo puso en el
               -- turno 0 en cuatro partidas y en el 30 en una tiene una
               -- media de 6 y el 6 es la verdad. Con MIN saldría 0 y diría
               -- que siempre lo tuvo desde el principio.
               --
               -- DENTRO de una partida NO es la media: es el primero. Dos
               -- poblados en el mismo número, turnos 0 y 41, dan 0 y no 20 --
               -- desde el 0 ya cobrabas ahí. El MIN está en `porpartida` y
               -- la media sólo junta partidas distintas.
               --
               -- Con UN decimal a propósito. Redondeado a entero, un 14 se
               -- lee como «el turno 14» y no hay ninguna partida en la que lo
               -- pusiera en el 14: es la media de 0, 0, 0, 40 y 29. El «,8»
               -- de 13,8 avisa solo de que eso es una media. Y cuando la
               -- media es redonda -- que es el caso de los números que
               -- siempre pilla en el reparto -- sale `0` limpio, porque la
               -- página no pinta el decimal de un entero.
               --
               -- NULL, que la página pinta como una raya, cuando nunca puso
               -- nada ahí. Eso no es el turno 0: el 0 es «lo tenía desde el
               -- reparto» y la raya es «no lo tuve nunca», y son lo contrario
               -- la una de la otra.
               ROUND(AVG(p.primer_poblado), 1)             AS primer_poblado,
               -- `puntitos` NO se suma: es cuántas de las 36 combinaciones
               -- dan ese número, o sea una propiedad de la ficha. Sumándolo
               -- entre partidas, el 6 de alguien que ha jugado trece saldría
               -- con 65 puntitos y no querría decir nada. Sale del número de
               -- la fila y no de `porpartida` para que las filas vacías lo
               -- traigan igual: el 6 vale cinco puntitos aunque no lo tengas.
               6 - ABS(7 - n.numero)                       AS puntitos,
               COALESCE(SUM(p.veces_salio), 0)             AS veces_salio,
               ROUND(COALESCE(SUM(p.deberia_salir), 0), 1) AS deberia_salir,
               COALESCE(SUM(p.producido), 0)               AS producido
          FROM gente g
          CROSS JOIN numeros n
          LEFT JOIN porpartida p ON p.quien = g.quien AND p.numero = n.numero
         GROUP BY g.quien, n.numero
         ORDER BY g.quien, n.numero
    """},

    {"nombre": "amigos_suerte", "titulo": "La suerte de cada uno",
     "que": "de las casillas donde está puesto, cuántas veces le pagó el tablero "
            "contra las que le debía. 100 es la suerte normal",
     "global": "con_amigos = 1", "partida": "game_id = ?",
     "sql": _con(_J) + """
        -- La pregunta: de los números en los que cada uno está puesto,
        -- ¿cuántas veces le pagó el tablero contra las que le debía? 100 es
        -- tener la suerte que toca; 110 es cobrar un 10% más de lo debido.
        --
        -- SON COBROS Y NO TIRADAS, y da igual cómo suene: si tiene TRES
        -- sitios en el 4, un 4 es UNA tirada y TRES cobros, y `le_toco`
        -- suma tres. Medido en una partida de la base: 46 tiradas, 28
        -- cayeron en un número suyo, `le_toco` da 41. Tener dos seises no
        -- hace más probable el 6 -- eso es 5 de 36 se tenga lo que se tenga
        -- -- lo que dobla es lo que cobras cuando sale. Y no infla la
        -- `suerte`, porque el mismo *por cada casilla* está en las dos
        -- partes de la división.
        --
        -- Esto estuvo escrito como «tiradas que salieron en sus números»
        -- hasta el 3 de septiembre de 2026, en la vista, en las columnas y
        -- en la portada. La cuenta siempre estuvo bien; el nombre no, y un
        -- nombre equivocado en una columna bien calculada no lo caza
        -- ninguna prueba de las que miran números.
        --
        -- Esto NO mide si eligió bien. Un 8 y un 3 valen distinto, y eso ya
        -- lo dice `puntitos` en «Los números de cada uno». Aquí el sitio
        -- se da por bueno y sólo se mira si los dados lo acompañaron: cada
        -- casilla con número aporta lo que le toca (los pips entre 36) y se
        -- compara con lo que salió de verdad.
        --
        -- CADA CASILLA CUENTA UNA VEZ, no dos por ser ciudad. Los dados no
        -- saben si ahí hay poblado o ciudad, y esto va de dados. Un poblado
        -- que toca tres casillas sí cuenta tres veces, porque son tres
        -- oportunidades distintas.
        --
        -- LO QUE HACE QUE ESTO SIGNIFIQUE ALGO: sólo se cuentan las tiradas
        -- desde que la pieza existe. Sin eso, quien construye en el turno 50
        -- sale con mala suerte garantizada -- se le achacarían cincuenta
        -- tiradas en las que no tenía nada ahí -- y la tabla mediría a qué
        -- hora construye cada uno, no su suerte.
        --
        -- El `> desde` no es un detalle: en un turno se tira PRIMERO y se
        -- construye después, así que una pieza del turno 34 no cobra el 34.
        -- Las de la colocación inicial son turno 0 y sí cobran esa tirada
        -- (la mesa se coloca antes de que ruede el primer dado), y por eso
        -- se les pone `desde = -1` en vez de 0.
        , sitios AS (
            SELECT j.game_id, j.quien, t.number AS numero,
                   CASE WHEN bu.turn_number IS NULL OR bu.turn_number = 0
                        THEN -1 ELSE bu.turn_number END          AS desde
              FROM j
              JOIN buildings bu ON bu.player_id = j.player_id
                               AND bu.type IN ('poblado', 'ciudad')
              JOIN building_tiles bt ON bt.building_id = bu.building_id
              JOIN tiles t ON t.tile_id = bt.tile_id
             WHERE t.number IS NOT NULL
        ),
        -- Una fila por persona, tirada y número: cuántas casillas suyas
        -- tenían ese número cuando rodaron esos dados. Con esto salen las
        -- tres cuentas -- lo que le tocaba, lo que le tocó y cuánto mueve el
        -- azar -- sin que puedan discrepar entre ellas.
        vivas AS (
            SELECT s.quien, r.roll_id, r.value AS valor, s.numero,
                   COUNT(*) AS cuantas
              FROM sitios s
              JOIN rolls r ON r.game_id = s.game_id
                          AND r.turn_number > s.desde
             GROUP BY s.quien, r.roll_id, s.numero
        ),
        -- Por tirada: lo que esperaba cobrar (m1), el mismo cálculo con el
        -- cuadrado (m2) y lo que cobró. La varianza de una tirada es
        -- m2 - m1*m1, y se suman todas.
        --
        -- Se hace tirada a tirada y no casilla a casilla porque UNA tirada
        -- resuelve todas las casillas a la vez: dos casillas suyas en el 6
        -- aciertan o fallan juntas, nunca una sí y otra no. Tratarlas como
        -- independientes daría un margen más pequeño del que es, y el margen
        -- es justo lo que aquí se quiere medir bien.
        portirada AS (
            SELECT quien, roll_id,
                   SUM(1.0 * (6 - ABS(7 - numero)) * cuantas / 36.0)      AS m1,
                   SUM(1.0 * (6 - ABS(7 - numero)) * cuantas * cuantas
                       / 36.0)                                            AS m2,
                   SUM(CASE WHEN numero = valor THEN cuantas ELSE 0 END)  AS acerto
              FROM vivas
             GROUP BY quien, roll_id
        ),
        cuenta AS (
            SELECT quien,
                   -- `portirada` ya trae UNA FILA POR TIRADA, así que
                   -- contarlas es contar en cuántas tenía algo puesto. No
                   -- vale sumar el `tiradas` de `expuesto`, que va por
                   -- casilla: con nueve casillas contaría cada tirada nueve
                   -- veces.
                   COUNT(*)           AS cuantas_tiradas,
                   SUM(m1)            AS tocaba,
                   SUM(acerto)        AS toco,
                   SUM(m2 - m1 * m1)  AS varianza
              FROM portirada
             GROUP BY quien
        ),
        expuesto AS (
            SELECT s.quien, s.numero,
                   (SELECT COUNT(*) FROM rolls r
                     WHERE r.game_id = s.game_id
                       AND r.turn_number > s.desde)              AS tiradas,
                   (SELECT COUNT(*) FROM rolls r
                     WHERE r.game_id = s.game_id
                       AND r.turn_number > s.desde
                       AND r.value = s.numero)                   AS salio,
                   -- Lo que valdría una casilla cualquiera DE ESE TABLERO.
                   -- Sale del tablero de cada partida y no de un 3,22
                   -- escrito aquí: el de 5-6 jugadores tiene 30 casillas y
                   -- no reparte los números igual, así que la media no es la
                   -- misma. Al hacerse por partida, quien juegue en los dos
                   -- se compara contra el suyo en cada una.
                   (SELECT AVG(6 - ABS(7 - t2.number)) FROM tiles t2
                     WHERE t2.game_id = s.game_id
                       AND t2.number IS NOT NULL)                AS normal
              FROM sitios s
        )
        SELECT quien,
               COUNT(*)                                          AS casillas,
               -- Los puntitos de debajo del número, sumados: el 6 lleva
               -- cinco y el 2 lleva uno, porque de las 36 combinaciones de
               -- dos dados el 6 sale en cinco y el 2 en una.
               --
               -- Esta columna está para que se VEA que un 6 no es un 2. La
               -- cuenta ya lo tenía dentro -- `le_tocaba` son los puntitos
               -- entre 36, por tirada -- pero desde fuera parecía que se
               -- contaban casillas a secas, y una tabla que hay que creerse
               -- no vale. Con los puntitos al lado se lee solo: 17 casillas
               -- con 25 puntitos son peores que 15 con 30.
               SUM(6 - ABS(7 - numero))                          AS puntitos,
               -- LO QUE ELIGIÓ, separado de lo que le tocó. `puntitos` a
               -- secas premia al que jugó más partidas: el que lleva cien
               -- casillas suma más que el que lleva veinte aunque las tenga
               -- peores. Dividido por casillas ya se pueden comparar dos
               -- personas -- y contra `lo_normal`, saber si eso es elegir
               -- bien o es lo que había.
               --
               -- No es suerte y por eso va aparte: colocarse en los seises
               -- es criterio. Que salgan es lo que mide `suerte`.
               ROUND(SUM(6 - ABS(7 - numero)) * 1.0 / COUNT(*), 2)
                                                                 AS por_casilla,
               ROUND(AVG(normal), 2)                             AS lo_normal,
               -- Y lo que esas casillas le pagaron DE VERDAD, por casilla.
               -- `por_casilla` son puntitos y esto son cartas: no se
               -- comparan entre si, que son unidades distintas. Lo que dice
               -- esta es otra cosa y no la decia ninguna -- cuanto rinde una
               -- casilla suya -- y ahi entran las ciudades, que pagan doble,
               -- y el ladron, que no paga.
               --
               -- Solo producción de tirada, como en «El ladrón»: el reparto
               -- inicial no lo paga la casilla por estar donde está, lo paga
               -- por colocarla, y contarlo subiría a todo el mundo lo mismo.
               COALESCE((SELECT SUM(g.amount) FROM resource_gains g
                          WHERE g.player_id IN (SELECT player_id FROM j aj
                                                 WHERE aj.quien = expuesto.quien)
                            AND g.source = 'produccion'), 0)     AS producido,
               ROUND(COALESCE((SELECT SUM(g.amount) FROM resource_gains g
                                WHERE g.player_id IN (
                                          SELECT player_id FROM j aj
                                           WHERE aj.quien = expuesto.quien)
                                  AND g.source = 'produccion'), 0)
                     * 1.0 / COUNT(*), 2)                        AS cada_casilla,
               -- Sobre cuántas tiradas está medido todo lo que viene
               -- detrás. Sin esto, un 108% y un 99% parecen dos resultados
               -- comparables, y uno puede salir de 53 tiradas y el otro de
               -- 837. `margen` ya lo dice en forma de porcentaje, pero el
               -- tamaño de la muestra en crudo se entiende sin explicación y
               -- el margen no.
               --
               -- Son las tiradas EN LAS QUE TENÍA ALGO PUESTO. Hoy eso
               -- coincide con todas las de sus partidas -- comprobado, las
               -- siete personas dan el mismo número por los dos caminos --
               -- porque los dos poblados iniciales se colocan antes de que
               -- ruede el primer dado. La definición es la de la ventana
               -- igualmente: es la que valdría si alguien jugara una partida
               -- sin poner nada en una casilla con número.
               --
               -- Y NO es el multiplicador de `le_tocaba`. Aquélla usa la
               -- ventana DE CADA CASILLA -- una pieza del turno 30 sólo
               -- cuenta desde el 30 -- así que `tiradas_contadas` por los
               -- puntitos no da `le_tocaba`, ni tiene por qué. Esta columna
               -- es el tamaño de la muestra, no un factor.
               --
               -- Se llama `tiradas_contadas` y no `tiradas` por dos razones,
               -- y la segunda está medida. La primera: dice CUÁLES, que es
               -- justo lo que había que explicar. La segunda: una columna
               -- llamada `tiradas` en una vista que además tiene `quien` le
               -- roba preguntas a la caja -- traduce «sale» y «dado» a
               -- «tirada» -- y el examen bajó de 37 a 36 al ponerla así.
               -- Con el nombre largo vuelve a 37. Y por eso la de al lado
               -- se llama `tiros` y no `tiradas` tampoco: son dos cosas
               -- distintas y ninguna de las dos puede quedarse la palabra.
               --
               -- CUÁNTAS VECES TIRÓ EL DADO ÉL. La otra mitad de la
               -- pregunta, y no se parecen: `tiradas_contadas` son todas
               -- las de la mesa que le podían pagar --las tire quien las
               -- tire-- y `tiros` sólo las suyas, o sea del orden de una de
               -- cada cuatro en una mesa de cuatro.
               --
               -- NO ENTRA EN LA CUENTA DE LA SUERTE ni tiene por qué: el
               -- dado no sabe quién lo tira, así que cobrar o no cobrar da
               -- lo mismo de qué mano salga. Está aquí porque es el número
               -- que faltaba para leer la fila entera -- de las tiradas de
               -- sus partidas, cuáles hizo él -- y porque el único número
               -- del que sí depende quién tira es el 7, que mueve el
               -- ladrón, y ése tiene su propia tabla.
               --
               -- Misma cuenta y mismo nombre que `tiros` en «Los sietes de
               -- cada uno»: `rolls` contadas por `player_id`, que es quién
               -- tiró. Comprobado que las dos dan lo mismo persona a
               -- persona; si algún día dejaran de cuadrar es que una está
               -- mal.
               (SELECT COUNT(*) FROM rolls r
                 WHERE r.player_id IN (SELECT player_id FROM j aj
                                        WHERE aj.quien = expuesto.quien))
                                                                 AS tiros,
               (SELECT c.cuantas_tiradas FROM cuenta c
                 WHERE c.quien = expuesto.quien)        AS tiradas_contadas,
               SUM(salio)                                        AS le_toco,
               ROUND(SUM(tiradas * (6 - ABS(7 - numero)) / 36.0), 1)
                                                                 AS le_tocaba,
               -- El número al lado del porcentaje, como en las tiradas: «un
               -- 8% de suerte» no dice si son tres tiradas o treinta.
               ROUND(SUM(salio)
                     - SUM(tiradas * (6 - ABS(7 - numero)) / 36.0), 1)
                                                                 AS de_mas,
               ROUND(100.0 * SUM(salio)
                     / NULLIF(SUM(tiradas * (6 - ABS(7 - numero)) / 36.0), 0), 1)
                                                                 AS suerte,
               -- Cuánto mueve el azar normalmente, en porcentaje de lo que le
               -- tocaba. Es lo que contesta la pregunta «¿y el que tiene más
               -- casillas?»: el porcentaje de suerte ya está normalizado --
               -- más casillas suben `le_toco` y `le_tocaba` a la vez -- pero
               -- con pocas casillas se dispara solo. Nueve casillas y un 109%
               -- no es lo mismo que cincuenta y seis y un 93%.
               ROUND(100.0 * (SELECT SQRT(c.varianza) FROM cuenta c
                               WHERE c.quien = expuesto.quien)
                     / NULLIF(SUM(tiradas * (6 - ABS(7 - numero)) / 36.0), 0), 1)
                                                                 AS margen,
               -- Cuántos márgenes se sale, con signo. Es el número que de
               -- verdad ordena: por debajo de 2 no hay nada que contar, pase
               -- lo que pase con el porcentaje.
               ROUND((SUM(salio)
                      - SUM(tiradas * (6 - ABS(7 - numero)) / 36.0))
                     / NULLIF((SELECT SQRT(c.varianza) FROM cuenta c
                                WHERE c.quien = expuesto.quien), 0), 2)
                                                                 AS se_sale
          FROM expuesto
         GROUP BY quien
         ORDER BY se_sale DESC
    """},

    {"nombre": "amigos_comercio", "titulo": "Quién propone tratos a quién",
     "que": "quién mueve ficha: sólo los tratos que propuso cada uno, y cómo "
            "le salieron ESOS",
     "global": "con_amigos = 1", "partida": "game_id = ?",
     "sql": _con(_J) + """
        -- Direccional a propósito: `quien` es el que PROPUSO el trato y
        -- `con_quien` el que lo aceptó. Contar cada trato una sola vez
        -- perdería quién movió ficha, que es la mitad de lo que se ve aquí.
        --
        -- Y por eso el título dice «propone» y no «comercia», que es lo que
        -- decía antes: quien lea «quién comercia con quién» va a sumar mal.
        -- Los tratos entre dos personas están repartidos en DOS filas -- una
        -- por cada uno que propuso -- así que `tratos` no es cuántos hicieron
        -- entre ellos. Para eso está `tratos_entre_los_dos`, que es la misma
        -- cifra en las dos filas del par.
        --
        -- Sólo tratos entre personas. Los de la banca están en
        -- `amigos_puertos`, que es donde dicen algo.
        --
        -- TUVO `que_dio` Y `que_recibio` -- la lista de recursos -- y se
        -- quitaron el 2 de septiembre de 2026. Se pusieron para no tener que
        -- cambiar de vista y saber de qué iba el trato, y era mala idea: una
        -- lista de nombres sin cantidades («Arcilla, Madera») no dice si dio
        -- una arcilla o siete, así que no contesta nada y ocupa las dos
        -- columnas más anchas de la tabla. Eso desglosado y con cifras está
        -- en «Qué se comercia», por pareja y por material, que es donde
        -- vale. Esta vista es la global: quién propone y con qué saldo.
        SELECT ja.quien                                     AS quien,
               jb.quien                                     AS con_quien,
               COUNT(*)                                     AS tratos,
               SUM((SELECT SUM(json_extract(value, '$.amount'))
                      FROM json_each(t.gave_json)))         AS dio,
               SUM((SELECT SUM(json_extract(value, '$.amount'))
                      FROM json_each(t.received_json)))     AS recibio,
               -- SE LLAMABA `neto` Y ERA UNA TRAMPA. Es «lo que ganó o
               -- perdió EN LOS TRATOS QUE PROPUSO ÉL», y al lado hay otra
               -- vista, del mismo grupo, con una columna `neto` que es «lo
               -- que ganó o perdió con esa persona, en total». No es que se
               -- parezcan: en 16 de las 26 parejas dan números distintos, y
               -- en varias CAMBIAN DE SIGNO -- Periplo con carla sale a -1
               -- aquí y a +4 allí.
               --
               -- El tell de que no es un saldo está en la propia tabla: las
               -- dos filas de un par pueden ser LAS DOS NEGATIVAS (carla con
               -- TheClonne -3 y TheClonne con carla -2), que en un saldo de
               -- verdad es imposible -- las cartas no se evaporan al
               -- cambiarlas de mano. Pueden serlo porque son tratos
               -- distintos. En «El saldo con cada uno» son -1 y +1 y siempre
               -- suman cero, que es lo que define un saldo.
               --
               -- Ese es exactamente el caso de `le_costo` del 1 de
               -- septiembre: dos vistas del mismo grupo, la misma columna,
               -- dos cuentas distintas. La lista de `COMPARTIDAS` existe
               -- para eso y ésta se coló dentro el 4 de septiembre de 2026
               -- con la excusa de que las dos son «recibio menos dio» -- que
               -- es verdad y no basta, porque lo que cambia es qué tratos
               -- entran en la fila.
               --
               -- Con el nombre largo se lee sola y ya no compite: quien
               -- busque el saldo con alguien no lo va a encontrar aquí.
               SUM((SELECT SUM(json_extract(value, '$.amount'))
                      FROM json_each(t.received_json)))
             - SUM((SELECT SUM(json_extract(value, '$.amount'))
                      FROM json_each(t.gave_json)))         AS neto_proponiendo,
               -- LA ULTIMA A PROPOSITO. Todas las de antes hablan de los
               -- tratos que propuso `quien`; esta habla del par entero, en
               -- los dos sentidos. Estuvo puesta entre `tratos` y `dio` y era
               -- una trampa: leyendo la fila de izquierda a derecha, `dio`
               -- parecia referirse a estos tratos y no a los de la columna
               -- anterior. Al final estorba menos y se lee como lo que es.
               (SELECT COUNT(*) FROM trades t3
                 WHERE (t3.player_a_id IN (SELECT player_id FROM j
                                            WHERE quien = ja.quien)
                        AND t3.player_b_id IN (SELECT player_id FROM j
                                                WHERE quien = jb.quien))
                    OR (t3.player_a_id IN (SELECT player_id FROM j
                                            WHERE quien = jb.quien)
                        AND t3.player_b_id IN (SELECT player_id FROM j
                                                WHERE quien = ja.quien)))
                                                            AS tratos_entre_los_dos,
               -- Y en cuántas partidas coincidieron. Es la perspectiva que le
               -- faltaba a la columna de al lado: dos tratos entre dos que
               -- han jugado dos partidas juntos y dos entre dos que han
               -- jugado trece no son lo mismo, y puestos en la misma tabla se
               -- leen igual. Cuenta partidas COMPARTIDAS, no las de cada uno.
               (SELECT COUNT(*) FROM (
                    SELECT game_id FROM j WHERE quien = ja.quien
                    INTERSECT
                    SELECT game_id FROM j WHERE quien = jb.quien))
                                                            AS partidas_juntos
          FROM trades t
          JOIN j ja ON ja.player_id = t.player_a_id
          JOIN j jb ON jb.player_id = t.player_b_id
         GROUP BY ja.quien, jb.quien
         -- Primero las parejas que más se mueven entre ellas, no las que más
         -- proponen: quien propone mucho pero le aceptan poco no es con quien
         -- más se comercia. Dentro del par, primero el que propuso más.
         ORDER BY tratos_entre_los_dos DESC, tratos DESC
    """},

    {"nombre": "amigos_saldo", "titulo": "El saldo con cada uno",
     "que": "quién gana cartas con quién y quién las pierde: el saldo de "
            "verdad, con TODOS sus tratos dentro, los propusiera quien los "
            "propusiera (sin la banca)",
     "global": "con_amigos = 1", "partida": "game_id = ?",
     "sql": _con(_J) + """
        -- La pregunta es «con quién he movido más cartas, y salgo ganando o
        -- perdiendo». Una fila por pareja, con TODOS sus tratos dentro, los
        -- propusiera quien los propusiera.
        --
        -- Por qué no vale ninguna de las otras tres:
        --   amigos_comercio           sólo los que propuso `quien`
        --   amigos_comercio_material  una fila por recurso, no un saldo
        --   amigos_tratos             uno a uno, sin sumar
        --
        -- `neto` negativo es haber entregado más cartas de las que se llevó.
        -- Ojo con leerlo como «me han timado»: dar tres por una puede ser el
        -- mejor trato de la partida si esa una es la que te faltaba. Dice
        -- cuántas cartas se movieron y hacia dónde, no si valió la pena.
        --
        -- SÓLO PERSONAS: la banca no entra. Con ella el neto es negativo por
        -- definición -- cambiar 4 por 1 son 3 cartas perdidas siempre -- así
        -- que no dice nada de nadie y encima se lleva los primeros puestos de
        -- la tabla, que es justo donde estorba. Lo que se cambió con el banco
        -- está en `amigos_puertos` y en `amigos_comercio_material`, donde sí
        -- significa algo.
        --
        -- Al ser sólo personas, todo trato tiene dos lados y el JOIN es el
        -- mismo en las dos ramas.
        , lados AS (
            SELECT ja.quien     AS quien,
                   jb.quien     AS con_quien,
                   t.gave_json  AS dio_json,
                   t.received_json AS recibio_json
              FROM trades t
              JOIN j ja ON ja.player_id = t.player_a_id
              JOIN j jb ON jb.player_id = t.player_b_id
            UNION ALL
            SELECT jb.quien, ja.quien, t.received_json, t.gave_json
              FROM trades t
              JOIN j ja ON ja.player_id = t.player_a_id
              JOIN j jb ON jb.player_id = t.player_b_id
        )
        SELECT quien, con_quien,
               COUNT(*)                                     AS tratos,
               SUM((SELECT SUM(json_extract(value, '$.amount'))
                      FROM json_each(dio_json)))            AS dio,
               SUM((SELECT SUM(json_extract(value, '$.amount'))
                      FROM json_each(recibio_json)))        AS recibio,
               SUM((SELECT SUM(json_extract(value, '$.amount'))
                      FROM json_each(recibio_json)))
             - SUM((SELECT SUM(json_extract(value, '$.amount'))
                      FROM json_each(dio_json)))            AS neto
          FROM lados
         GROUP BY quien, con_quien
         ORDER BY tratos DESC, neto
    """},

    {"nombre": "amigos_tratos", "titulo": "Trato a trato",
     "que": "cada intercambio con los dos lados: quién dio qué y a cambio de qué",
     "global": "con_amigos = 1", "partida": "game_id = ?",
     "sql": _con(_J) + """
        -- Las otras dos vistas de comercio agregan, y agregando se pierde el
        -- trato: en `amigos_comercio_material` ves que carla recibió 2 lanas
        -- de Pshyfer, pero no a cambio de qué, porque eso está en otras filas.
        -- Aquí cada fila es un intercambio entero.
        --
        -- El turno no está en `trades`, así que sale del último turno que ya
        -- había empezado cuando se hizo el trato.
        SELECT j.game_id                                    AS partida,
               (SELECT MAX(tu.turn_number) FROM turns tu
                 WHERE tu.game_id = t.game_id
                   AND tu.start_ts <= t.timestamp)          AS turno,
               j.quien                                      AS quien,
               (SELECT group_concat(json_extract(value, '$.amount')
                                    || ' ' || json_extract(value, '$.resource'),
                                    ' + ')
                  FROM json_each(t.gave_json))              AS dio,
               CASE WHEN t.player_b_id IS NULL THEN 'la banca'
                    ELSE (SELECT quien FROM j jb
                           WHERE jb.player_id = t.player_b_id) END AS a,
               (SELECT group_concat(json_extract(value, '$.amount')
                                    || ' ' || json_extract(value, '$.resource'),
                                    ' + ')
                  FROM json_each(t.received_json))          AS y_recibio
          FROM trades t
          JOIN j ON j.player_id = t.player_a_id
         -- La más reciente arriba, como en «Las partidas»; el porqué
         -- está escrito allí. Lo de DENTRO de cada partida no se toca:
         -- una partida se lee hacia adelante.
         ORDER BY j.game_id DESC, t.timestamp
    """},

    {"nombre": "amigos_comercio_material", "titulo": "Qué se comercia",
     "que": "qué recurso da y cuál recibe cada uno, y con quién",
     "global": "con_amigos = 1", "partida": "game_id = ?",
     "sql": _con(_J) + """
        -- `con_quien` es la persona, o 'la banca' cuando el otro lado es el
        -- banco o un puerto. Se decide por `player_b_id IS NULL` y no por que
        -- el JOIN falle: si un día fallara por otro motivo, un trato entre
        -- personas se contaría como de banca y nadie lo notaría.
        --
        -- `neto` positivo es lo que acaba entrando. Ahí se ve de qué anda
        -- corto cada uno mejor que en la producción: la producción dice lo
        -- que le tocó, esto dice lo que le faltaba.
        --
        -- LOS DOS LADOS DE CADA TRATO, y esto estuvo mal hasta el 22/8/2026.
        -- `trades` guarda quién PROPUSO (player_a) y quién aceptó (player_b),
        -- y aquí se leía sólo la fila de player_a. O sea que a cada uno le
        -- salían únicamente los tratos que había iniciado él, y los que le
        -- aceptaron a otro no aparecían por ningún lado en su cuenta.
        --
        -- No se notaba porque no faltaban filas ni cuadraban mal los totales:
        -- cada trato estaba, entero, pero apuntado a nombre de uno solo. Con
        -- eso, `neto` -- que es para lo que existe esta vista -- decía media
        -- verdad. Salió mirando dos tratos de la partida 5 en los que
        -- LoboEstepario le dio madera a elGato por cereales las dos veces, y
        -- sólo salía uno porque el otro lo había propuesto elGato.
        --
        -- La banca no tiene otro lado, así que sólo entra por la primera
        -- rama; el JOIN de la segunda la deja fuera él solo.
        , lados AS (
            SELECT ja.quien                            AS quien,
                   CASE WHEN t.player_b_id IS NULL THEN 'la banca'
                        ELSE jb.quien END              AS con_quien,
                   t.gave_json                         AS dio_json,
                   t.received_json                     AS recibio_json
              FROM trades t
              JOIN j ja ON ja.player_id = t.player_a_id
              LEFT JOIN j jb ON jb.player_id = t.player_b_id
            UNION ALL
            SELECT jb.quien, ja.quien, t.received_json, t.gave_json
              FROM trades t
              JOIN j ja ON ja.player_id = t.player_a_id
              JOIN j jb ON jb.player_id = t.player_b_id
        ),
        juntos AS (
            SELECT quien, con_quien,
                   json_extract(e.value, '$.resource') AS recurso,
                   json_extract(e.value, '$.amount')   AS dio,
                   0                                   AS recibio
              FROM lados JOIN json_each(dio_json) e
            UNION ALL
            SELECT quien, con_quien,
                   json_extract(e.value, '$.resource'), 0,
                   json_extract(e.value, '$.amount')
              FROM lados JOIN json_each(recibio_json) e
        )
        SELECT quien, con_quien, recurso,
               SUM(dio)                AS dio,
               SUM(recibio)            AS recibio,
               SUM(recibio) - SUM(dio) AS neto
          FROM juntos
         GROUP BY quien, con_quien, recurso
         ORDER BY quien, con_quien, dio + recibio DESC
    """},

    {"nombre": "amigos_puertos", "titulo": "Puerto a puerto",
     "que": "una fila por puerto usado: cuál, cuántas veces y entre qué turnos",
     "global": "con_amigos = 1", "partida": "game_id = ?",
     "sql": _con(_J) + """
        -- Un cambio con la banca delata el puerto: 2 por 1 sólo se puede
        -- hacer con el puerto DE ESE RECURSO, y 3 por 1 con uno genérico. El
        -- 4:1 es el cambio de quien no tiene ninguno.
        --
        -- Los 2:1 se pueden contar: cada recurso distinto es un puerto
        -- distinto. Los 3:1 NO. Un puerto genérico ya sirve para los cinco
        -- recursos, así que el segundo no cambia nada de lo que puedes hacer
        -- y no deja ninguna huella. Aquí saldrá 'generico 3:1' tanto si tiene
        -- uno como si tiene tres.
        --
        -- Y un puerto que se coge y no se usa no aparece: no hay trato que lo
        -- delate. Para esas dos cosas hace falta el tablero, que es lo que el
        -- mod empezó a apuntar el 21/8 en la tabla `harbors`.
        --
        -- UNA FILA POR PERSONA Y PUERTO, juntando todas las partidas. Iba por
        -- partida, con este argumento escrito aquí: «un puerto es de un
        -- tablero, y el 2:1 de mineral de la partida 2 y el de la 4 no son el
        -- mismo puerto». Es verdad y no manda sobre lo que mide esta tabla,
        -- que no son puertos sino USOS: cuántos cambios con la banca ha hecho
        -- a ese cambio y desde qué turno. Los cambios se suman entre partidas
        -- -- son tratos -- y sumados es cuando dicen algo: quién se hace del
        -- puerto de mineral no se ve en cuatro filas de una partida suelta.
        --
        -- Lo que NO se puede leer aquí es un puerto concreto de un tablero
        -- concreto. Para eso está el desplegable de partida, que filtra esta
        -- misma tabla, y «Quién pilló cada puerto», que va por tablero.
        , cambios AS (
            SELECT ja.game_id AS partida, ja.quien AS quien,
                   (SELECT SUM(json_extract(value, '$.amount'))
                      FROM json_each(t.gave_json))     AS dio,
                   (SELECT SUM(json_extract(value, '$.amount'))
                      FROM json_each(t.received_json)) AS recibio,
                   (SELECT json_extract(value, '$.resource')
                      FROM json_each(t.gave_json) LIMIT 1) AS recurso,
                   (SELECT MAX(tu.turn_number) FROM turns tu
                     WHERE tu.game_id = t.game_id
                       AND tu.start_ts <= t.timestamp)  AS turno
              FROM trades t
              JOIN j ja ON ja.player_id = t.player_a_id
             WHERE t.player_b_id IS NULL
        )
        -- `primer_uso` es cuándo lo USÓ por primera vez, no cuándo lo pilló:
        -- es un techo, tenerlo lo tenía como muy tarde entonces. La
        -- diferencia puede ser grande. LoboEstepario, partida 2: puso poblado
        -- en el turno 27 y no cambió a 2:1 de mineral hasta el 40. En cambio
        -- su puerto de madera lo estrenó el mismo turno 51 en que lo pilló.
        -- Saber cuál de los dos casos es requiere el tablero (`harbors`).
        --
        -- Juntando partidas, `primer_uso` es lo más pronto que lo ha
        -- estrenado en ninguna, y `ultimo_uso` lo más tarde que lo ha usado.
        -- No son los dos extremos de una misma partida: son el mejor y el
        -- peor caso de todas las suyas.
        --
        -- Los 4:1 NO salen. Un 4:1 es el cambio de quien no tiene puerto, y
        -- esta vista va de puertos: una fila que dice «sin puerto» en la
        -- tabla de los puertos ocupa sitio y no cuenta nada que no se
        -- entienda solo. Se ven igual en «Trato a trato», que es donde estan
        -- todos los cambios.
        SELECT quien,
               CASE WHEN dio / recibio = 2 THEN recurso || ' 2:1'
                    ELSE 'generico 3:1' END            AS puerto,
               COUNT(*)                                AS veces,
               MIN(turno)                              AS primer_uso,
               MAX(turno)                              AS ultimo_uso
          FROM cambios
         WHERE recibio > 0
           AND dio / recibio IN (2, 3)
         GROUP BY quien, puerto
         ORDER BY quien, veces DESC
    """},

    {"nombre": "amigos_puertos_pillados", "titulo": "Quién pilló cada puerto",
     "que": "los nueve puertos del mapa y quién se quedó cada uno, incluidos "
            "los que no pilló nadie",
     "vacio": "De esta partida no se puede saber. Que alguien USE un puerto "
              "se deduce de los comercios y eso está en «Puerto a puerto»; "
              "PILLARLO es otra cosa y necesita saber dónde está cada puerto "
              "en el tablero. El mod no lo leía bien hasta el 22/8/2026 -- la "
              "posición viene en una `EdgePosition` y se estaba leyendo como "
              "si fuera otra clase, así que llegaba vacía -- y eso no se "
              "puede recuperar sin volver a jugar la partida.",
     "global": "con_amigos = 1", "partida": "game_id = ?",
     "sql": _con(_J) + """
        -- Esto es lo que NO se puede deducir de los comercios, y por eso hace
        -- falta el mod. Un puerto que nadie usa no deja rastro en los tratos,
        -- y un 3:1 usado prueba que tienes uno pero nunca cuántos. Aquí está
        -- el hecho: quién puso una pieza encima, y cuándo.
        --
        -- Van LOS NUEVE, también los que no pilló nadie, y eso es la mitad de
        -- lo que contesta la tabla: «¿los 3:1 se los queda alguien o se
        -- ignoran?» sólo se puede responder si los vacíos también salen.
        -- Antes eran dos vistas -- ésta con los pillados y otra con la tabla
        -- del mod en crudo, coordenadas incluidas -- y la segunda no contaba
        -- nada que se pudiera leer: eran los mismos puertos con los sitios
        -- escritos en JSON.
        --
        -- Sólo salen las partidas cuyo tablero se pudo leer (`edge_json`).
        -- En las anteriores al 22/8 el mod no traía dónde está cada puerto,
        -- así que de esas no se sabe quién pilló qué -- y una fila con el
        -- nombre del puerto y todo lo demás vacío no dice nada, mientras que
        -- poner 'nadie' diría que se jugaron sin pillar un solo puerto, que
        -- es mentira. Se van enteras y el mensaje de vacío lo explica.
        -- `quien` es entonces un nombre, o `nadie` si el puerto se quedó sin
        -- pillar, que es media razón de que esta tabla exista.
        --
        -- El turno es el de PONER el poblado, no el de mejorarlo a ciudad: el
        -- puerto se pilla al colocarse y mejorar no da nada nuevo. `pieza`
        -- dice en qué acabó, que es otra pregunta.
        SELECT h.game_id                          AS partida,
               pa.dia,
               h.kind || ' ' || h.ratio || ':1'   AS puerto,
               COALESCE(j.quien, 'nadie')         AS quien,
               o.turn_number                      AS turno,
               b.type                             AS pieza
          FROM harbors h
          JOIN partidas pa ON pa.game_id = h.game_id
          LEFT JOIN harbor_owners o ON o.harbor_id = h.harbor_id
          LEFT JOIN j ON j.player_id = o.player_id
          LEFT JOIN buildings b ON b.building_id = o.building_id
        -- El filtro entra por `j` y no aquí: `{donde}` sólo puede aparecer
        -- una vez en toda la consulta -- se sustituye con un solo `?` -- y ya
        -- lo gasta el CTE. Pedirlo así además hace lo correcto en los dos
        -- usos: global son las partidas con amigos, y con número es ésa.
         WHERE h.game_id IN (SELECT game_id FROM j)
           AND h.edge_json IS NOT NULL
         -- La más reciente arriba, como en «Las partidas»; el porqué
         -- está escrito allí. Lo de DENTRO de cada partida no se toca:
         -- una partida se lee hacia adelante.
         ORDER BY h.game_id DESC,
                  o.turn_number IS NULL, o.turn_number,
                  h.harbor_id
    """},

    {"nombre": "amigos_cuantos_puertos", "titulo": "Cuántos, por jugador",
     "que": "una fila por jugador: cuántos puertos se le pueden contar y cuáles",
     "global": "con_amigos = 1", "partida": "game_id = ?",
     "sql": _con(_J) + """
        -- `al_menos` es un suelo, no un total, y por eso se llama así: cada
        -- 2:1 de un recurso distinto es un puerto seguro, y todos los 3:1
        -- juntos cuentan como uno porque no hay forma de distinguir uno de
        -- dos. Si alguien pilló dos genéricos, aquí sale como uno.
        , cambios AS (
            SELECT ja.game_id AS partida, ja.quien AS quien,
                   (SELECT SUM(json_extract(value, '$.amount'))
                      FROM json_each(t.gave_json))     AS dio,
                   (SELECT SUM(json_extract(value, '$.amount'))
                      FROM json_each(t.received_json)) AS recibio,
                   (SELECT json_extract(value, '$.resource')
                      FROM json_each(t.gave_json) LIMIT 1) AS recurso
              FROM trades t
              JOIN j ja ON ja.player_id = t.player_a_id
             WHERE t.player_b_id IS NULL
        )
        --
        -- VA POR PERSONA Y NO POR PARTIDA. Tablero a tablero esto son cuatro
        -- filas casi vacías; juntando todas se ve de qué puerto se hace cada
        -- uno. `partidas` va delante porque sin ella los números no se pueden
        -- comparar: cuatro veces el de madera en veinte partidas no es lo
        -- mismo que cuatro en seis.
        --
        -- Partida a partida no se pierde: el desplegable del panel filtra
        -- esta misma vista, y para verlo tablero a tablero está «Quién pilló
        -- cada puerto», que además enseña los que no cogió nadie.
        , tiene AS (
            SELECT DISTINCT c.partida, c.quien, c.recurso
              FROM cambios c
             WHERE c.recibio > 0 AND c.dio / c.recibio = 2
        ),
        genericos AS (
            SELECT DISTINCT c.partida, c.quien
              FROM cambios c
             WHERE c.recibio > 0 AND c.dio / c.recibio = 3
        )
        -- En cuántas PARTIDAS se le pudo contar cada puerto. No es cuántas
        -- veces lo usó: uno usado quince veces en una partida cuenta una,
        -- porque lo que se mide es tenerlo.
        SELECT j.quien,
               COUNT(DISTINCT j.game_id)                        AS partidas,
               COUNT(DISTINCT CASE WHEN t.recurso = 'Madera'
                                   THEN t.partida END)          AS puerto_madera,
               COUNT(DISTINCT CASE WHEN t.recurso = 'Arcilla'
                                   THEN t.partida END)          AS puerto_arcilla,
               COUNT(DISTINCT CASE WHEN t.recurso = 'Lana'
                                   THEN t.partida END)          AS puerto_lana,
               COUNT(DISTINCT CASE WHEN t.recurso = 'Cereales'
                                   THEN t.partida END)          AS puerto_cereales,
               COUNT(DISTINCT CASE WHEN t.recurso = 'Mineral'
                                   THEN t.partida END)          AS puerto_mineral,
               (SELECT COUNT(*) FROM genericos g
                 WHERE g.quien = j.quien
                   AND g.partida IN (SELECT aj.game_id FROM j aj
                                      WHERE aj.quien = j.quien)) AS genericos
          FROM j
          LEFT JOIN tiene t ON t.quien = j.quien AND t.partida = j.game_id
         GROUP BY j.quien
         ORDER BY partidas DESC, j.quien
    """},

    {"nombre": "amigos_ritmo", "titulo": "El ritmo de cada uno",
     "que": "en qué turno llegó a su primera ciudad, su primera carta...",
     "global": "con_amigos = 1", "partida": "game_id = ?",
     "sql": _con(_J) + """
        -- El turno 0 es la colocación inicial: todo el mundo pone DOS
        -- poblados ahí y eso no dice nada de nadie. El primero que se
        -- construye jugando es por tanto el TERCERO, y ese sí.
        --
        -- Se mira `turn_number` sin filtrar por tipo a propósito: un vértice
        -- que hoy es ciudad empezó siendo poblado, y `turn_number` es cuándo
        -- se puso el poblado. Filtrando por `type='poblado'` se perdían los
        -- de quien mejoró todos -- elGato construyó tres en la partida 4 y
        -- salía sin ninguno.
        --
        -- Un NULL aquí no es un cero: quiere decir que no llegó a hacerlo en
        -- toda la partida, que es un dato en sí mismo.
        SELECT j.game_id                                    AS partida,
               j.quien,
               j.puesto,
               j.puntos,
               (SELECT MIN(b.turn_number) FROM buildings b
                 WHERE b.player_id = j.player_id
                   AND b.turn_number > 0)                   AS tercer_poblado,
               (SELECT MIN(b.upgraded_turn) FROM buildings b
                 WHERE b.player_id = j.player_id
                   AND b.type = 'ciudad')                   AS primera_ciudad,
               (SELECT MIN(c.turn_number) FROM dev_card_purchases c
                 WHERE c.player_id = j.player_id)           AS primera_carta,
               (SELECT MIN(d.turn_number) FROM dev_card_plays d
                 WHERE d.player_id = j.player_id
                   AND d.card_type = 'Caballero')           AS primer_caballero,
               (SELECT MAX(r.turn_number) FROM rolls r
                 WHERE r.game_id = j.game_id)               AS duro_hasta
          FROM j
         -- La más reciente arriba, como en «Las partidas»; el porqué
         -- está escrito allí. Lo de DENTRO de cada partida no se toca:
         -- una partida se lee hacia adelante.
         ORDER BY j.game_id DESC, j.puesto
    """},

    {"nombre": "amigos_robos", "titulo": "Robos de la mano",
     "que": "cuántos hizo y cuántos sufrió cada uno (cuántos, no cuáles)",
     "global": "con_amigos = 1", "partida": "game_id = ?",
     "sql": _con(_J) + """
        SELECT j.quien,
               (SELECT COUNT(*) FROM steals s
                 WHERE s.thief_id IN (SELECT player_id FROM j aj
                                       WHERE aj.quien = j.quien))  AS robo_el,
               (SELECT COUNT(*) FROM steals s
                 WHERE s.victim_id IN (SELECT player_id FROM j aj
                                        WHERE aj.quien = j.quien)) AS le_robaron
          FROM j
         GROUP BY j.quien
         ORDER BY le_robaron DESC
    """},

    {"nombre": "amigos_tiradas", "titulo": "Las tiradas",
     "que": "qué salió contra lo que debería haber salido",
     "global": "con_amigos = 1", "partida": "game_id = ?",
     "sql": """
        -- Los once números salen SIEMPRE, aunque no se haya sacado ninguno.
        -- Antes se agrupaba sobre las tiradas que hubo, así que un número que
        -- no salió nunca no tenía fila -- y ese es justo el más interesante
        -- de esta tabla: en la partida 4 el 12 no salió ni una vez y no se
        -- veía por ningún lado.
        --
        -- Y las columnas se llaman en cristiano y no `pct`: la tabla la lee
        -- alguien que no ha escrito esta consulta, y una cabecera que hay que
        -- preguntar qué significa es una cabecera mal puesta.
        WITH p AS (SELECT * FROM partidas WHERE {donde}),
             numeros(numero) AS (VALUES (2),(3),(4),(5),(6),(7),(8),(9),(10),
                                        (11),(12)),
             cuantas AS (SELECT COUNT(*) AS n FROM rolls r2
                          JOIN p p2 ON p2.game_id = r2.game_id)
        -- Dos parejas y en este orden: las veces al lado de las veces, y el
        -- porcentaje al lado del porcentaje. El porcentaje solo no dice si la
        -- diferencia es mucha o poca -- «13,9 contra 11,1» son dos números
        -- que hay que traducir a tiradas en la cabeza, y «31 contra 25» ya
        -- viene traducido. Con pocas partidas eso importa: seis tiradas de
        -- más parecen una barbaridad en porcentaje y son seis tiradas.
        SELECT n.numero,
               COUNT(r.roll_id)                                 AS veces,
               ROUND((SELECT n FROM cuantas)
                     * (6 - ABS(7 - n.numero)) / 36.0, 1)       AS veces_normales,
               ROUND(100.0 * COUNT(r.roll_id)
                     / NULLIF((SELECT n FROM cuantas), 0), 1)   AS porcentaje,
               ROUND(100.0 * (6 - ABS(7 - n.numero)) / 36.0, 1) AS porcentaje_normal
          FROM numeros n
          LEFT JOIN rolls r ON r.value = n.numero
                           AND r.game_id IN (SELECT game_id FROM p)
         GROUP BY n.numero
         ORDER BY n.numero
    """},

    {"nombre": "amigos_sietes", "titulo": "Los sietes de cada uno",
     "que": "quién saca más sietes al tirar, contra el 16,7% que toca",
     "global": "con_amigos = 1", "partida": "game_id = ?",
     "sql": _con(_J) + """
        -- `rolls.player_id` es QUIÉN TIRÓ, se lleva grabando desde el
        -- principio y hasta hoy no lo usaba ninguna vista. Esta lo usa.
        --
        -- Y sólo para el 7, no para los once números. El 7 es el único que
        -- va del que tira: mueve el ladrón, elige a quién y hace descartar a
        -- media mesa. Los otros diez pagan a quien tenga algo puesto ahí, y
        -- eso ya está en «Los números de cada uno» -- da igual quién los
        -- sacara. Abrir esta tabla por número serían setenta y siete filas
        -- para repetir lo que ya se lee mejor en otro sitio.
        --
        -- La columna del total se llama `tiros` y no `tiradas`, que es como
        -- se diria. `tiradas` costo un punto del examen y esta medido: la
        -- caja de preguntas traduce «sale», «dado» y «tirado» a «tirada»
        -- antes de emparejar, asi que «sale ganando cartas en los tratos» y
        -- «cuantas cartas le ha DADO» se venian aqui -- una columna con esa
        -- palabra en una vista que ademas tiene `quien` se lleva media caja.
        -- Con `tiros` el examen vuelve a 36 y la columna se sigue
        -- entendiendo. `partidas.tiradas` ya tiraba de esas preguntas y se
        -- queda como esta: ahi la palabra es la que es.
        --
        -- `porcentaje` y no sietes por partida: las partidas no duran lo
        -- mismo. Quien juega partidas largas tira más veces y saca más
        -- sietes sin que eso diga nada de nadie. Sobre sus tiradas sí se
        -- comparan, y al lado va el 16,7 que es lo que toca -- seis de las
        -- treinta y seis combinaciones, el número más probable del juego.
        SELECT j.quien,
               COUNT(DISTINCT j.game_id)                        AS partidas,
               COUNT(r.roll_id)                                 AS tiros,
               SUM(r.value = 7)                                 AS sietes,
               ROUND(100.0 * SUM(r.value = 7)
                     / NULLIF(COUNT(r.roll_id), 0), 1)          AS porcentaje,
               ROUND(100.0 * 6 / 36.0, 1)                       AS porcentaje_normal
          FROM j
          JOIN rolls r ON r.player_id = j.player_id
         GROUP BY j.quien
         ORDER BY porcentaje DESC
    """},
]

POR_NOMBRE = dict((v["nombre"], v) for v in VISTAS)


# --------------------------------------------------------------------------
# Cómo se agrupan en el panel.
#
# Con 25 vistas puestas en rejilla, el orden en que están escritas aquí arriba
# no basta: la pantalla las coloca de tres en tres o de dos en dos según lo
# ancha que sea, así que una pareja que aquí va seguida acaba partida entre
# dos filas y parece que no tienen nada que ver. Y había cosas de verdad
# descolocadas -- `amigos_robos` es del ladrón y estaba la 24, entre el ritmo
# y las tiradas.
#
# Va en un sitio y no como un campo `grupo` en cada vista por lo mismo que el
# `{donde}`: el orden se lee de un vistazo, y una vista que se olvide de un
# grupo se ve enseguida. La prueba exige que cada vista esté en uno y sólo
# uno, así que añadir una y no ponerla aquí no cuela.
# --------------------------------------------------------------------------

GRUPOS = (
    # DENTRO DE CADA GRUPO: PRIMERO EL GENERAL, DESPUES EL DESGLOSE. Es la
    # regla y no hay excepciones; si se anade una vista, va donde le toque
    # por esto y no al final.
    #
    # «General» es la que junta mas: una fila por persona manda sobre una
    # fila por pareja, y esa sobre una fila por cada cosa que paso. Cuando
    # hay dos dimensiones -- personas y numeros, personas y puertos -- van
    # primero las dos por separado y el CRUCE al final, que es el que solo
    # se entiende habiendo visto las otras dos.
    #
    # POR QUE. El grupo de comercio estuvo al reves y costo tres o cuatro
    # vueltas explicarlo: la primera ficha era «Quien propone tratos a
    # quien», que es el total de una pareja PARTIDO por quien pidio el
    # trato, y el total sin partir estaba en la ficha de al lado. Es el
    # desglose de algo que todavia no habias visto, y asi no hay forma de
    # saber de que es desglose. Con el total delante, la segunda ficha se
    # lee sola.
    ("Las partidas", (
        # una partida por fila; luego cada jugador de cada partida
        "partidas", "jugadores")),
    ("Puntos y ritmo", (
        # el marcador (persona), su desglose partida a partida, y despues
        # el bloque de la salida: el resumen por puesto, por persona, el
        # cruce de los dos, y al final partida a partida
        "amigos_marcador", "amigos_puntos", "amigos_ritmo",
        "amigos_por_salida", "amigos_salida_de_cada_uno",
        "amigos_salida_como_acabo", "amigos_salida")),
    ("Cartas de desarrollo", (
        # persona, tipo de carta, pareja, y cada monopolio suelto
        "amigos_desarrollo", "amigos_mazo",
        "amigos_monopolios_a_quien", "amigos_monopolios")),
    ("El ladrón", (
        # las dos de persona primero -- son las dos mitades del dano, el
        # bloqueo y el robo de la mano -- y luego los dos desgloses: por a
        # quien (y su cruce con el numero) y por numero (y su cruce con la
        # persona)
        "amigos_ladron", "amigos_ladron_proporcion", "amigos_robos",
        "amigos_ladron_a_quien", "amigos_ladron_a_quien_numero",
        "amigos_ladron_numeros", "amigos_ladron_donde")),
    ("Comercio", (
        # el total de la pareja, ese total partido por quien propuso, el
        # mismo partido por material, y los tratos uno a uno
        "amigos_saldo", "amigos_comercio",
        "amigos_comercio_material", "amigos_tratos")),
    ("Puertos", (
        # cuantos tiene cada uno, quien se quedo cada puerto del mapa, y el
        # cruce de los dos
        "amigos_cuantos_puertos", "amigos_puertos_pillados",
        "amigos_puertos")),
    ("El tablero y los dados", (
        # las tres de persona, luego los dados por numero, y el cruce
        # persona-numero al final
        "amigos_produccion", "amigos_suerte", "amigos_sietes",
        "amigos_tiradas", "amigos_numeros")),
)

# --------------------------------------------------------------------------
# Columnas que salen en MAS DE UNA vista. Cada una con el motivo por el que
# esta bien que se repita.
#
# POR QUE ESTA ESTA LISTA. El 1 de septiembre `amigos_ladron` estreno una
# columna `le_costo` que era «produccion bloqueada + cartas robadas». Ya
# habia una `le_costo` en «El ladron, uno a uno» que era «produccion
# bloqueada» a secas. Dos vistas del mismo grupo, el mismo nombre, dos
# cuentas distintas: 14 en una y 33 en la otra para la misma partida. No
# rompio nada, no lo canto ninguna prueba, y quien puso las dos tablas una
# encima de otra saco que la base se contradecia. Que es lo peor que puede
# pasarle a esto.
#
# Se deniega por defecto: una columna nueva que coincida con otra existente
# falla la prueba hasta que alguien la mire y la apunte aqui. Apuntarla es
# barato; el error que evita, no.
#
# Las que salen en el apartado de columnas COMUNES de PROYECTO.md (`quien`,
# `turno`, `partida`...) no hacen falta aqui: ya estan declaradas alli.
COMPARTIDAS = {
    "madera":    "los cinco recursos: siempre cartas de ese material",
    "arcilla":   "idem",
    "lana":      "idem",
    "cereales":  "idem",
    "mineral":   "idem",
    "dio":       "cartas que solto, en las tres vistas de comercio",
    "recibio":   "cartas que se llevo, en las tres de comercio",
    # «Quien propone tratos a quien» NO esta en esta lista y por eso su
    # columna se llama `neto_proponiendo`: alli solo entran los tratos que
    # propuso esa persona, asi que es otro numero -- distinto en 16 de las 26
    # parejas y con el signo cambiado en varias. Estuvo aqui dentro unas
    # horas el 4 de septiembre de 2026 con la excusa de que las dos son
    # «recibio menos dio». Lo son, y da igual: lo que cambia no es la resta,
    # son las filas que se restan.
    "neto":      "recibio menos dio",
    "tratos":    "cuantos tratos, cerrados",
    "con_7":     "veces que el ladron se movio por un 7 y no por un caballero",
    "con_caballero": "lo mismo al reves",
    "puerto":    "que puerto es, con el mismo nombre en las dos",
    # Comprobado fila a fila en las 16 partidas y en el global: la
    # misma cuenta y el mismo numero en las dos. Salta la prueba
    # cuando se anadio a «El ladron», y eso es lo que hay que hacer:
    # mirar si dicen lo mismo antes de dejarlas convivir.
    "le_robaron": "cartas que le quitaron de la mano; identica en las dos",
    # Las dos salen de contar `rolls` por `player_id`, que es quien tiro, y
    # dan el mismo numero persona a persona -- lo comprueba una prueba. En
    # «Los sietes» es el denominador del porcentaje de sietes; en «La suerte»
    # es el contrapunto de `tiradas_contadas`, que son las de toda la mesa.
    "tiros":         "cuantas veces tiro el dado esa persona",
    "puntitos":      "las probabilidades de sus casillas, en decimas de 36",
    # Dos formas y las dos son «la parte observada»: en «Las tiradas» y «El
    # mazo» es esa fila sobre el total de la tabla; en «Los sietes» y «El
    # ladron» es una tasa DENTRO de la fila -- que porcentaje de sus tiradas
    # fueron sietes, que porcentaje de los ladrones de sus partidas le
    # cayeron. La descripcion las cubre a las dos a proposito: si algun dia
    # una vista la usa para otra cosa, hay que cambiarle el nombre y no
    # ensanchar esta frase otra vez.
    "porcentaje":    "el tanto por ciento observado de esa fila",
    # `porcentaje` y `porcentaje_normal` van en pareja y significan lo mismo
    # en las dos vistas donde salen: lo que paso contra lo que tocaba. En
    # «Las tiradas» son numeros de dado; en «El mazo», cartas. Comprobado:
    # las dos se calculan igual, la parte observada sobre el total y la parte
    # teorica sobre el mismo total.
    "porcentaje_normal": "el tanto por ciento que le tocaria a esa fila si "
                         "no pasara nada raro",
    # Misma cuenta exacta en las dos vistas del ladron -- la de abajo es la
    # de arriba abierta por numero -- y por eso el total de una tiene que
    # salir de sumar la otra. Si algun dia dejaran de cuadrar, es que una de
    # las dos esta mal.
    "se_lo_puso":    "veces que le movio el ladron a una casilla donde el "
                     "otro ya tenia algo",
    "partidas":      "en cuantas partidas jugo",
    "victorias":     "cuantas gano",
    "puesto_medio":  "media del puesto en que acaba",
    "puntos_medios": "media de puntos",
    "jugadores":     "cuantos jugaban esa partida",
    "a_puntos":      "a cuantos puntos se jugaba: 10 o 12",
    # Las dos que NO quieren decir exactamente lo mismo, y por que pasan:
    #
    # `veces` es un contador de filas y su unidad la pone la vista: veces que
    # alguien salio en ese puesto, veces que le bloquearon, veces que se uso
    # ese puerto. Nadie compara dos `veces` de vistas distintas porque no
    # cuentan lo mismo NI LO PARECEN -- al reves que `le_costo`, que en las
    # dos era «cartas que le costo el ladron» y por eso enganaba.
    "veces": "contador de filas; la unidad la pone cada vista",
    # `puestos_ganados` si es el mismo numero: `salida` menos `puesto`. En
    # «El orden de salida» es el de esa partida y en «Importa salir primero»
    # es la MEDIA de esos mismos. Se deja porque la segunda esta marcada como
    # no sumable y su vista se llama «medios» por todas partes, pero es el
    # caso mas parecido al de `le_costo` que queda en pie.
    "puestos_ganados": "el mismo numero; en `amigos_por_salida` promediado",
}

# Una vista sin grupo no se esconde: sale al final y con un nombre que canta.
SIN_GRUPO = "Sin colocar"


def grupo_de(nombre):
    for titulo, nombres in GRUPOS:
        if nombre in nombres:
            return titulo
    return SIN_GRUPO


def por_grupos():
    """Las vistas en el orden en que se enseñan, agrupadas.

    Devuelve [(titulo, [vista, ...]), ...]. Dentro de cada grupo mandan los
    nombres de `GRUPOS`, no el orden en que están escritas las vistas: si no,
    cambiar una de sitio en el fichero movería la pantalla sin querer."""
    salida, colocadas = [], set()
    for titulo, nombres in GRUPOS:
        vistas = [POR_NOMBRE[n] for n in nombres if n in POR_NOMBRE]
        colocadas.update(v["nombre"] for v in vistas)
        if vistas:
            salida.append((titulo, vistas))
    sueltas = [v for v in VISTAS if v["nombre"] not in colocadas]
    if sueltas:
        salida.append((SIN_GRUPO, sueltas))
    return salida


# Los tres ámbitos. Es el mismo hueco `{donde}` de siempre, así que una vista
# no se entera de que existen: no hay que escribir nada en las 25 para que los
# tengan, ni acordarse en la 26.
#
# Por qué tres y no un «ver también la IA»: las partidas contra la máquina no
# son las mismas partidas peor jugadas, son otro juego -- la IA no propone
# tratos, no bloquea igual y no aguanta una partida larga. Mezclarlas con las
# de la mesa no ensucia un poco la media, la deja sin significado. Y a la vez
# tirarlas del todo tampoco vale, que son las que sirven para probar el mod.
# Separadas, cada una contesta lo suyo.
AMBITOS = ("amigos", "todo", "ia")
NOMBRE_DEL_AMBITO = {
    "amigos": "solo con amigos (sin la IA)",
    "todo": "todas, la IA incluida",
    "ia": "solo las partidas contra la IA",
}

# Y el OTRO eje: de cuanta gente era la mesa.
#
# Va aparte del ambito y no como tres valores mas de la misma lista porque
# son preguntas independientes -- «con amigos y en mesa de 4» es una
# combinacion legitima -- y meterlas en una sola lista obliga a escribir
# todas las parejas.
#
# POR QUE HACE FALTA. Una partida de 5 o 6 no es la misma partida con dos
# sillas mas: el tablero tiene 30 casillas en vez de 19 y no reparte los
# numeros igual, y se juega a 12 puntos y no a 10. Mezclarlas es el mismo
# error que mezclar las de la IA -- que ya tiene su filtro -- y por eso este
# se parece a aquel. Se ve en `amigos_marcador`, que lleva partiendose por
# `eran` desde el principio justo por esto: 9 puntos en una mesa de seis
# estan mas lejos de ganar que 9 en una de cuatro.
#
# El corte es 4 contra 5-y-6 y no uno por tamanio porque el corte del JUEGO
# esta ahi: 5 y 6 comparten tablero, mazo y puntos.
#
# «todas» es lo de siempre y sigue siendo el de serie. Poner «4» por defecto
# habria cambiado en silencio todos los numeros que ya se han leido, y eso
# lo decide quien mira, no la tabla.
MESAS = ("todas", "4", "5y6")
NOMBRE_DE_LA_MESA = {
    "todas": "mesas de cualquier tamaño",
    "4": "solo mesas de 4",
    "5y6": "solo mesas de 5 y 6",
}


def donde_del_ambito(vista, ambito):
    """El filtro de una vista para un ámbito. `None` = el de siempre.

    La columna es `con_amigos` en casi todas; una vista que la tenga con otro
    nombre o detrás de un alias lo dice en `columna_amigos`."""
    if ambito is None:
        return vista["global"]
    if ambito not in AMBITOS:
        raise ValueError(ambito)
    if ambito == "todo":
        return "1=1"
    col = vista.get("columna_amigos", "con_amigos")
    return "%s = %d" % (col, 1 if ambito == "amigos" else 0)


def donde_de_la_mesa(vista, mesa):
    """El filtro por tamaño de mesa, o `None` si no hay que filtrar.

    La columna es `jugadores` en casi todas, porque casi todas filtran sobre
    las vistas `jugadores` o `partidas` y las dos la traen. Las dos vistas
    base son la excepción: ahí `jugadores` es un alias de un subselect de su
    propio SQL, así que lo dicen con `columna_jugadores` -- igual que ya
    hacían con `columna_amigos`."""
    if mesa is None or mesa == "todas":
        return None
    if mesa not in MESAS:
        raise ValueError(mesa)
    col = vista.get("columna_jugadores", "jugadores")
    return "%s = 4" % col if mesa == "4" else "%s >= 5" % col


def sql_de(vista, partida=None, ambito=None, mesa=None):
    """El SQL de una vista, y los parámetros que le hacen falta.

    Sin `partida` sale el de siempre -- el que se guarda como vista -- o el
    del ámbito y el tamaño de mesa que se pidan. Con `partida`, el mismo
    texto filtrado por ese número: una partida es una partida, y ni el
    ámbito ni el tamaño de mesa pintan ya nada."""
    if partida is None:
        donde = donde_del_ambito(vista, ambito)
        mas = donde_de_la_mesa(vista, mesa)
        if mas:
            # Con paréntesis: el del ámbito puede ser `1=1` hoy y un `OR`
            # mañana, y un AND pegado detrás de un OR filtra otra cosa.
            donde = "(%s) AND %s" % (donde, mas)
        return vista["sql"].replace("{donde}", donde), ()
    return vista["sql"].replace("{donde}", vista["partida"]), (int(partida),)


def consultar(conn, nombre, partida=None, ambito=None, mesa=None):
    """(columnas, filas) de una vista, de una partida, o de un ámbito y un
    tamaño de mesa."""
    vista = POR_NOMBRE.get(nombre)
    if vista is None:
        raise KeyError(nombre)
    sql, args = sql_de(vista, partida, ambito, mesa)
    cur = conn.execute(sql, args)
    return [d[0] for d in cur.description], cur.fetchall()


def las_que_hay(conn):
    return set(r[0] for r in conn.execute(
        "SELECT name FROM sqlite_master WHERE type='view'"))


def crear(conn):
    # DROP y CREATE de todas, siempre. Una vista no guarda datos, así que
    # rehacerlas es gratis y evita que quede una versión vieja si se cambia
    # el SQL de aquí arriba.
    for v in reversed(VISTAS):
        conn.execute("DROP VIEW IF EXISTS %s" % v["nombre"])
    for v in VISTAS:
        sql, _args = sql_de(v)
        conn.execute("CREATE VIEW %s AS %s" % (v["nombre"], sql.strip()))
    conn.commit()


def quitar(conn):
    for v in reversed(VISTAS):
        conn.execute("DROP VIEW IF EXISTS %s" % v["nombre"])
    conn.commit()


def _pintar(columnas, filas):
    anchos = [len(c) for c in columnas]
    texto = [["" if v is None else str(v) for v in f] for f in filas]
    for f in texto:
        for i, c in enumerate(f):
            anchos[i] = max(anchos[i], len(c))
    print("  ".join(c.ljust(anchos[i]) for i, c in enumerate(columnas)).rstrip())
    print("  ".join("-" * a for a in anchos))
    for f in texto:
        print("  ".join(c.ljust(anchos[i]) for i, c in enumerate(f)).rstrip())
    print()
    print("%d fila%s" % (len(filas), "" if len(filas) == 1 else "s"))


def main():
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--crear", action="store_true", help="crear o rehacer")
    p.add_argument("--quitar", action="store_true", help="borrarlas")
    p.add_argument("--ver", metavar="VISTA", help="enseñar una")
    p.add_argument("--partida", type=int, help="con --ver, sólo esa partida")
    p.add_argument("--ambito", choices=AMBITOS,
                   help="con --ver y sin --partida: %s"
                        % ", ".join("%s = %s" % (a, NOMBRE_DEL_AMBITO[a])
                                    for a in AMBITOS))
    # Tiene que estar aquí y no sólo en el panel: la pantalla enseña debajo
    # de cada tabla el comando que la saca por consola, y si el filtro no se
    # pudiera pedir por consola ese comando daría una tabla distinta de la
    # que se está mirando.
    p.add_argument("--mesa", choices=MESAS,
                   help="con --ver y sin --partida: %s"
                        % ", ".join("%s = %s" % (m, NOMBRE_DE_LA_MESA[m])
                                    for m in MESAS))
    args = p.parse_args()

    if not os.path.isfile(BASE):
        print("No hay base de datos en %s" % BASE)
        return 1
    if args.crear and args.quitar:
        print("O --crear o --quitar, no las dos.")
        return 1

    conn = sqlite3.connect(BASE)
    try:
        if args.quitar:
            quitar(conn)
            print("quitadas las %d vistas. Las tablas no se han tocado."
                  % len(VISTAS))
            return 0

        if args.ver:
            if args.ver not in POR_NOMBRE:
                print("No hay ninguna vista '%s'. Las que hay: %s"
                      % (args.ver, ", ".join(POR_NOMBRE)))
                return 1
            columnas, filas = consultar(conn, args.ver, args.partida,
                                        args.ambito, args.mesa)
            _pintar(columnas, filas)
            return 0

        if args.crear:
            crear(conn)
            print("%d vistas creadas en %s" % (len(VISTAS), BASE))
            print()
            for v in VISTAS:
                n = conn.execute("SELECT COUNT(*) FROM %s"
                                 % v["nombre"]).fetchone()[0]
                print("   %-20s %4d filas" % (v["nombre"], n))
            print()
            print("Se consultan como una tabla más:")
            print('   py sql.py "SELECT * FROM amigos_marcador"')
            return 0

        hay = las_que_hay(conn)
        faltan = [v["nombre"] for v in VISTAS if v["nombre"] not in hay]
        print("Vistas de este fichero: %d" % len(VISTAS))
        for v in VISTAS:
            print("   %-20s %s" % (v["nombre"],
                                   "está" if v["nombre"] in hay else "FALTA"))
        sobran = sorted(hay - set(POR_NOMBRE))
        if sobran:
            print()
            print("   en la base hay además: %s" % ", ".join(sobran))
        print()
        if faltan:
            print("Faltan %d. Para crearlas:" % len(faltan))
            print("   py db/vistas.py --crear")
            return 1
        print("Están todas. Se consultan como una tabla más:")
        print('   py sql.py "SELECT * FROM amigos_marcador"')
        print("Si se cambia el SQL de este fichero, --crear las rehace.")
        return 0
    finally:
        conn.close()


if __name__ == "__main__":
    sys.exit(main())
