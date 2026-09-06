# -*- coding: utf-8 -*-
"""Qué quiere decir cada columna de cada vista. El único sitio donde se dice.

    py db/catalogo.py            escribe VISTAS.md con todo esto dentro
    py db/catalogo.py --faltan   qué columnas no están explicadas

POR QUÉ ESTÁ EN UN .py Y NO EN EL MARKDOWN. Esto estuvo dentro de
PROYECTO.md, que es donde se escribió. Se sacó aquí el 2 de septiembre de
2026 al crear `VISTAS.md`: en cuanto hay dos ficheros que explican las mismas
columnas, tarde o temprano dicen cosas distintas -- que es exactamente el
fallo que se arregló ese mismo día con `le_costo`, que quería decir dos cosas
en dos vistas. Aquí el texto está una vez, `VISTAS.md` se genera de aquí, y
una prueba comprueba que el fichero generado está al día.

Y así lo puede comprobar la máquina: `db/pruebas.py` exige que cada columna
que la base devuelve esté explicada aquí, y que aquí no sobre ninguna que ya
no exista. Un `.md` no da para eso.
"""

# Las que salen en varias vistas y quieren decir lo mismo en todas. La lista
# de las que se repiten -- y el motivo -- está en `vistas.COMPARTIDAS`.
COMUNES = {
    "quien"     : "la persona, con el nombre ya puesto. Es la misma entre partidas aunque cambie de color o de asiento",
    "a_quien"   : "la otra persona de la pareja: a quien le pasó lo que cuenta la fila",
    "con_quien" : "la otra persona de la pareja. `la banca` no es nadie: es cambiar cartas en el banco o por un puerto",
    "partida"   : "el número de la partida",
    "game_id"   : "el número de la partida",
    "player_id" : "número interno de esa persona **en esa partida**. No es la persona: la misma tiene uno distinto en cada partida",
    "dia"       : "el día que se jugó",
    "hora"      : "a qué hora empezó",
    "turno"     : "en qué turno pasó. El **0** es la colocación inicial",
    "puesto"    : "en qué puesto acabó. 1 es ganar",
    "puntos"    : "con cuántos puntos acabó",
    "color"     : "de qué color jugaba esa partida",
    "salida"    : "el orden de turno: 1 el que empieza",
    "numero"    : "el número de la ficha, de 2 a 12",
    "recurso"   : "madera, arcilla, lana, cereales o mineral",
    "producido" : "cartas que le entraron PRODUCIENDO: las que pagó el tablero al salir su número. Sin tratos, sin monopolios y sin el reparto inicial: para eso está `del_reparto`. Comprobado que las tres vistas que la traen dan el mismo número",
    "se_lo_pusieron": "veces que **otro** movió el ladrón a una casilla suya. Es lo que uno recuerda, y es más del doble que la siguiente. Ponérselo uno mismo no cuenta aquí (no te lo pusieron, lo pusiste) y sale en «El ladrón, uno a uno», en la fila que lleva a la misma persona en las dos columnas",
    "con_amigos": "1 si los cuatro eran personas; 0 si había máquinas",
}


# Y las propias de cada vista, en el orden en que salen.
POR_VISTA = {
    "partidas": {
        "gano"            : "quién ganó",
        "jugadores"       : "cuántos jugaban",
        "a_puntos"        : "a cuántos puntos se jugaba: **10 el Catan básico, 12 el de 5-6 jugadores**. No está apuntado en ningún sitio porque no hace falta: se sabe por cuántos eran",
        "casillas_tablero": "cuántas tenía el tablero: **19 el básico, 30 el de 5-6**. Es la forma más rápida de ver qué partidas son del tablero grande",
        "ias"             : "cuántos de los jugadores eran la máquina",
        "tiradas"         : "cuántas veces se tiraron los dados en esa partida",
        "minutos"         : "minutos entre el principio y el final de la partida. **Vacío** si no tiene final apuntado: o se abandonó, o se está jugando ahora mismo",
        "pegas"           : "lo que salió mal al importarla, si salió algo, o acciones que no entiende, si has jugado a una expansión. Vacío es lo normal. Va en la tabla y no en un log porque **cambia lo que dicen las demás filas**: la partida 11 tiene la producción contada como si no hubiera ladrón, y sin esta columna no se ve por ningún lado: sale una partida perfectamente creíble",
    },
    "jugadores": {
        "es_ia"    : "1 si es la máquina",
        "jugadores": "cuántos jugaban esa partida",
        "a_puntos" : "a cuántos puntos se jugaba (10 o 12)",
    },
    "amigos_marcador": {
        "partidas"     : "cuántas ha jugado **en mesas de ese tamaño**",
        "eran"         : "cuántos jugaban. Es lo que parte la tabla en bloques",
        "victorias"    : "cuántas de ésas ha ganado",
        "puntos_medios": "media de los puntos con los que acaba",
        "se_jugaba_a"  : "a cuántos puntos: 10 hasta cuatro, 12 con cinco o seis. Va al lado de `puntos_medios` porque sin esto no se puede leer: 9 puntos en una mesa de seis está más lejos de ganar que 9 en una de cuatro",
        "puesto_medio" : "media del puesto. Más bajo es mejor",
        "su_mejor"     : "los puntos de su mejor partida de ese tamaño",
    },
    "amigos_puntos": {
        "poblados"       : "poblados que tenía al acabar. Cada uno **1 punto**",
        "ciudades"       : "ciudades al acabar. Cada una **2 puntos**",
        "carretera_larga": "1 si tenía la carretera más larga. Son **2 puntos**",
        "mayor_ejercito" : "1 si tenía el mayor ejército. Son **2 puntos**",
        "cartas_de_punto": "puntos que llevaba escondidos en cartas. **Sale por resta**, no leyéndolas: los puntos finales menos poblados, ciudades y los dos premios. Lo que sobra tenían que ser cartas. Vacío cuando falta alguno de esos sumandos y la resta no se puede hacer",
    },
    "amigos_ritmo": {
        "tercer_poblado"  : "turno del **tercer** poblado, que es el primero que construyó jugando: los dos primeros los coloca todo el mundo antes de empezar y salen en el turno 0, así que no dicen nada de nadie. Se llama por el número que hace y no «primero» para que no se confunda con ésos",
        "primera_ciudad"  : "turno en que mejoró su primer poblado a ciudad",
        "primera_carta"   : "turno en que compró su primera carta de desarrollo",
        "primer_caballero": "turno en que jugó su primer caballero",
        "duro_hasta"      : "el último turno de la partida, para tener contra qué comparar los demás",
    },
    "amigos_salida": {
        "puestos_ganados": "`salida` menos `puesto`. Positivo: acabó mejor de lo que empezó",
    },
    "amigos_por_salida": {
        "veces"          : "cuántas veces alguien ha salido en ese puesto",
        "victorias"      : "cuántas de esas veces ganó",
        "puesto_medio"   : "media del puesto en que acaba quien sale ahí",
        "puntos_medios"  : "media de puntos de quien sale ahí",
        "puestos_ganados": "media de puestos ganados o perdidos saliendo ahí",
    },
    "amigos_salida_de_cada_uno": {
        "partidas"    : "en cuántas partidas ha jugado",
        "salio_1"     : "cuántas veces le tocó **salir** el primero. Ojo, que es lo que más se confunde de toda la tabla: dice dónde EMPEZÓ, no dónde acabó. Se llamaba `primero` y se leía al revés: para dónde acabó están `victorias` en «El marcador» y la tabla «De cada salida, cómo acabó»",
        "salio_2"     : "cuántas veces salió el segundo",
        "salio_3"     : "cuántas veces salió el tercero",
        "salio_4"     : "cuántas veces salió el cuarto",
        "salio_5"     : "cuántas veces salió el quinto. Sólo en mesas de 5 o 6",
        "salio_6"     : "cuántas veces salió el sexto. Sólo en mesas de 6",
        "salio_ultimo": "cuántas veces salió el último, sea la mesa de la que sea. No es lo mismo el 4 entre cuatro que el 4 entre seis, y en Catan salir el último tiene premio: coloca dos poblados seguidos y elige el último",
        "salida_media": "la media de su orden de salida. **No se suma**",
        "esperado"    : "cuántas primeras salidas le habrían tocado por azar. Se suma 1/jugadores partida a partida, así que una mesa de seis no ensucia la cuenta de las de cuatro. Contra `salio_1` dice si el sorteo le ha tratado bien",
    },
    "amigos_salida_como_acabo": {
        "veces"  : "en cuántas partidas salió en ese puesto. Es la suma de las seis columnas de al lado",
        "quedo_1": "de esas veces, en cuántas **acabó** el primero. O sea: ganó saliendo desde ese puesto",
        "quedo_2": "en cuántas acabó segundo",
        "quedo_3": "en cuántas acabó tercero",
        "quedo_4": "en cuántas acabó cuarto",
        "quedo_5": "en cuántas acabó quinto. Sólo en mesas de 5 o 6",
        "quedo_6": "en cuántas acabó sexto. Sólo en mesas de 6",
    },
    "amigos_desarrollo": {
        "partidas"      : "partidas suyas que hay apuntadas. Está aquí porque sin ella la columna de al lado no se puede comparar: 61 cartas en 12 partidas y 37 en 11 no son lo que parecen puestas una debajo de otra",
        "compradas"     : "cartas de desarrollo que compró, sumando todas sus partidas",
        "por_partida"   : "cartas de desarrollo **por partida**: `compradas` entre `partidas`. Ésta es la que se puede comparar entre personas, porque no premia al que más ha jugado",
        "caballero"     : "de ésas, cuántas eran caballeros. Una carta de desarrollo está tapada hasta que se juega, así que esto sólo cuenta las que llegó a jugar: las que se quedó en la mano están en `sin_saber`",
        "invencion"     : "cuántas eran de invención (año de la abundancia)",
        "monopolio"     : "cuántas eran de monopolio",
        "carreteras"    : "cuántas eran de construcción de carreteras",
        "punto_victoria": "cuántas eran de punto de victoria. Éstas nunca se juegan, así que no se ven en la mesa: salen de restar a sus puntos finales todo lo que sí se ve (poblados, ciudades y los dos premios)",
        "sin_saber"     : "compradas que ni jugó ni eran de punto. Se quedaron en la mano y no hay forma de saber cuáles eran",
    },
    "amigos_mazo": {
        "carta"            : "el tipo de carta de desarrollo: caballero, punto de victoria, monopolio, invención o carreteras",
        "salieron"         : "cuántas de ésas se han visto. Las últimas filas **no son tipos de carta**: son las que se compraron y nunca se jugaron (siguen en la mano de alguien), las que nadie llegó a comprar y se quedaron en el mazo, y (sólo si llega a pasar) las que compró alguien de fuera del grupo. Todo junto suma el mazo entero: en una partida de cuatro salieron 10, quedaron 4 en la mano y 11 sin comprar, y el mazo eran 25",
        "deberian_salir"   : "cuántas de ésas **deberían** haber salido. Sale de dos cosas: cuántas cartas se compraron en total y qué parte del mazo es este tipo. Si salieron 10 cartas y el 56% del mazo son caballeros, lo normal habría sido 5,6 caballeros. Se lee contra `salieron`, que está justo al lado",
        "porcentaje_normal": "qué parte del mazo es esta carta, que es la parte que le tocaría. 14 caballeros de 25 son el 56%; con 5 o 6 jugadores son 20 de 35, el 57,1%. Se llama igual que en «Las tiradas» porque es lo mismo con cartas en vez de dados: 70 contra 56 quiere decir que salieron más caballeros de los que el mazo lleva dentro",
        "porcentaje"       : "qué parte de todas las cartas vistas fue ésta. **No es la probabilidad de que salga**: es lo que pasó de verdad. De las 10 que salieron, 7 fueron caballeros, o sea el 70%. Se lee contra `porcentaje_normal`",
    },
    "amigos_monopolios": {
        "pidio"   : "el recurso que declaró. `sin saber` si esa grabación no lo trae",
        "les_saco": "cartas que se llevó en total. **NULL** quiere decir que esa grabación no lo apuntó, no que no se llevara nada",
        "de_quien": "a quién le sacó cuánto, en una línea: `Bruno 2, Carla 0`. El 0 también sale, porque «no tenía ninguna» es información. **Vacío** en las partidas de antes del 22/8/2026, cuando el mod todavía no apuntaba el reparto",
    },
    "amigos_monopolios_a_quien": {
        "monopolios": "cuántos monopolios le tiró a esa persona",
        "turnos"    : "en qué turnos fue. Una pareja puede tener varios, así que salen todos en orden: se ve si fue una racha o si le tiene tomada la matrícula desde el principio",
        "madera"    : "cartas de madera que le sacó con ellos",
        "arcilla"   : "cartas de arcilla que le sacó",
        "lana"      : "cartas de lana que le sacó",
        "cereales"  : "cartas de cereales que le sacó",
        "mineral"   : "cartas de mineral que le sacó",
        "cartas"    : "el total de las cinco de al lado",
    },
    "amigos_ladron": {
        "le_robaron"    : "cartas que le robaron al caer el ladrón a su lado. Una por robo: qué carta fue no se apunta, es información tapada",
        "le_bloquearon" : "**veces**, no cartas: las que además salió el número y se quedó sin cobrar. Casi la mitad de las veces el ladrón se sienta encima y el número no vuelve a salir, así que no cuesta nada. Puede salir mayor que la anterior: si se queda ahí y el número sale tres veces, son tres bloqueos de una sola puesta",
        "perdido"       : "**cartas**, no veces: las que le costaron esos bloqueos. Es el mismo número que `le_quito_el_ladron` de «Producción». No coincide con `le_bloquearon` porque una ciudad paga doble: un bloqueo en un poblado son 1 carta y en una ciudad, 2.",
        "madera"        : "de `perdido`, cuántos eran madera",
        "arcilla"       : "de `perdido`, cuántos eran arcilla",
        "lana"          : "de `perdido`, cuántos eran lana",
        "cereales"      : "de `perdido`, cuántos eran cereales",
        "mineral"       : "de `perdido`, cuántos eran mineral",
        "en_total"      : "**lo que le costó el ladrón entero**: `perdido` + `le_robaron`. Es la cuenta que uno lleva en la cabeza, y la que faltaba: «he perdido 4» eran 4 de producción y 6 robadas. Se llama así y no `le_costo` porque ese nombre ya está cogido en «El ladrón, uno a uno», donde son **sólo** los recursos bloqueados",
    },
    "amigos_ladron_proporcion": {
        "movimientos"   : "cuántas veces movieron el ladrón **los demás** en sus partidas. Es sobre cuántas está medido todo lo de al lado, y va delante por lo mismo que `tiradas_contadas` en la suerte: un 116 y un 63 parecen comparables y uno sale de 197 movimientos y el otro de 7",
        "se_lo_pusieron": "de esos movimientos, cuántos le cayeron encima. Es el mismo número que en «El ladrón», y una prueba lo exige",
        "porcentaje"    : "`se_lo_pusieron` entre `movimientos`. **Aquí no se descuenta nada**: tener muchas casillas también es parte del juego, y si lo que quieres saber es a quién le cae más el ladrón (y punto), ésta es tu columna. Lo único que quita es lo que no dice nada de nadie: cuántas partidas ha jugado y cuánto duraron",
        "le_tocaban"    : "cuántos le **tocaban**, y es un número y no un porcentaje para que se compare de un vistazo con `se_lo_pusieron`, que está al lado: 109 contra 94,3 se lee solo. Sale de repartir cada movimiento entre los jugadores según las casillas que tenía cada uno **en ese momento**, dando por bueno a cuánta gente pilló de verdad. Sumando la columna entera sale exactamente el total de ladrones que se pusieron (352,9 contra 353), y eso es lo que hace que el 100 de al lado sea el 100",
        "se_ceban"      : "`se_lo_pusieron` entre `le_tocaban`, en porcentaje. **Ésta es la columna que dice si se ceban contigo**: 100 es lo que toca, por encima te lo ponen más de la cuenta y por debajo te dejan en paz. Se lee igual que `suerte` en «La suerte de cada uno» a propósito, que es la misma forma (lo que pasó contra lo que tocaba). **La primera versión de esta tabla comparaba contra un ladrón ciego y estaba mal**: con esa referencia todo el mundo salía por encima de lo normal, lo cual es imposible como grupo. Medido: un ladrón puesto a mano pilla 1,49 personas por movimiento y uno tirado al azar 1,14, un 31% más. Claro que todos salían altos (el ladrón se pone *a alguien* a propósito). Con la referencia de ahora hay gente arriba y gente abajo, que es lo que tiene que pasar",
    },
    "amigos_ladron_a_quien": {
        "se_lo_puso"   : "veces que le movió el ladrón a una casilla donde el otro ya tenía algo. Es la intención. **Si las dos personas de la fila son la misma, se lo puso a sí mismo**: es legal y pasa: con un 7 a veces no queda mejor sitio, y a veces se hace a posta para robarle a alguien que toca esa casilla sin regalarle el bloqueo a un rival",
        "con_7"        : "de ésas, cuántas fueron **obligadas** por sacar un 7",
        "con_caballero": "de ésas, cuántas fueron **elegidas**, jugando un caballero",
        "le_bloqueo"   : "**veces**, no cartas: de esas puestas, en cuántas salió además el número y el otro se quedó sin cobrar. Es el daño que llegó a pasar, frente a `se_lo_puso`, que es sólo la intención",
        "le_costo"     : "**cartas**, no veces: las que el otro no llegó a cobrar por esos bloqueos. No coincide con `le_bloqueo` porque una ciudad paga doble. Ojo: aquí son **sólo** las bloqueadas, lo que le robó de la mano va aparte, en `le_robo`",
        "madera"       : "de `le_costo`, cuántos eran madera",
        "arcilla"      : "de `le_costo`, cuántos eran arcilla",
        "lana"         : "de `le_costo`, cuántos eran lana",
        "cereales"     : "de `le_costo`, cuántos eran cereales",
        "mineral"      : "de `le_costo`, cuántos eran mineral",
        "le_robo"      : "cartas que le quitó de la mano. **Cuántas, no cuáles**: la carta robada no la lee nadie",
    },
    "amigos_ladron_a_quien_numero": {
        "numero"       : "el número de la casilla donde le puso el ladrón",
        "se_lo_puso"   : "veces que le movió el ladrón a esa casilla concreta teniendo el otro algo ahí. Aquí es sólo la intención: lo que llegó a costar está en «El ladrón, uno a uno»",
        "con_7"        : "de ésas, cuántas fueron **obligadas** por sacar un 7",
        "con_caballero": "de ésas, cuántas fueron **elegidas**, jugando un caballero. Con un número gordo, ésta es la columna que separa la mala suerte de la mala idea",
    },
    "amigos_ladron_numeros": {
        "veces"        : "cuántas veces ha ido el ladrón a ese número, sumando a todo el mundo",
        "con_7"        : "de ésas, cuántas fueron obligadas por un 7",
        "con_caballero": "de ésas, cuántas fueron eligiendo, con un caballero",
        "personas"     : "cuántas personas distintas lo han tapado",
    },
    "amigos_ladron_donde": {
        "veces"        : "cuántas veces mandó el ladrón a ese número",
        "con_7"        : "de ésas, cuántas fueron obligadas por un 7",
        "con_caballero": "de ésas, cuántas fueron eligiendo, con un caballero",
        "a_si_mismo": "de esas veces, cuántas lo puso en una casilla **suya**. Es legal y se hace: unas veces porque con un 7 no queda mejor sitio, y otras a posta, para robarle a alguien que también toca esa casilla sin regalarle el bloqueo a un rival. No sale en «El ladrón, uno a uno» porque aquélla va por parejas y una fila consigo mismo confunde; sale aquí",
    },
    "amigos_robos": {
        "robo_el"   : "cartas que robó de la mano de otros",
        "le_robaron": "cartas que le robaron a él",
    },
    "amigos_comercio": {
        "tratos"              : "tratos que **él propuso** a esa persona. Los que propuso el otro están en la fila de vuelta",
        "dio"                 : "cartas que soltó en esos tratos",
        "recibio"             : "cartas que le llegaron en esos tratos",
        "neto_proponiendo"    : "`recibio` menos `dio` **sólo en los tratos que propuso él**. **No es su saldo con esa persona**: para eso está `neto` en «El saldo con cada uno», que sale distinto en 16 de las 26 parejas y en varias con el signo cambiado. El aviso está en la propia tabla: las dos filas de un par pueden ser **las dos negativas**, y en un saldo de verdad eso es imposible (las cartas no se evaporan al cambiarlas de mano). Pueden serlo porque son tratos distintos. Y hay un motivo para que casi todas lo sean: de los 141 tratos propuestos, el que propone acaba con **30 cartas de menos**",
        "tratos_entre_los_dos": "los tratos que han hecho entre los dos, propusiera quien propusiera. **La misma cifra en las dos filas del par**",
        "partidas_juntos"     : "en cuántas partidas han coincidido los dos. Es lo que le da sentido a la columna de al lado: dos tratos entre dos que sólo han jugado dos partidas juntos y dos entre dos que han jugado trece se leen igual en la tabla y no son lo mismo",
    },
    "amigos_saldo": {
        "tratos" : "tratos entre los dos, los propusiera quien los propusiera",
        "dio"    : "cartas que le dio en total",
        "recibio": "cartas que le llegaron de él",
        "neto"   : "`recibio` menos `dio`. La fila de vuelta lleva el mismo número cambiado de signo",
    },
    "amigos_tratos": {
        "dio"      : "lo que soltó, escrito tal cual: `1 Madera + 1 Lana`",
        "a"        : "a quién se lo dio",
        "y_recibio": "lo que le dieron a cambio",
    },
    "amigos_comercio_material": {
        "dio"    : "cuántas cartas de ese recurso le dio",
        "recibio": "cuántas de ese recurso le llegaron de él",
        "neto"   : "`recibio` menos `dio` de ese recurso. De qué anda corto con quién",
    },
    "amigos_puertos": {
        "puerto"    : "cuál usó: `Madera 2:1` o `generico 3:1`. Los cambios a 4:1 (los de quien no tiene puerto) no salen: esta tabla es la de los puertos, y están todos en «Trato a trato»",
        "veces"     : "cuántos cambios con la banca hizo por ahí, **sumando todas sus partidas**. Para saber en cuántas partidas distintas se le pudo contar ese puerto, «Cuántos, por jugador»",
        "primer_uso": "**lo más pronto** que lo ha estrenado: el turno más bajo de todas sus partidas. Es un techo de cuándo lo pilló, no cuándo lo pilló (tenerlo lo tenía como muy tarde entonces)",
        "ultimo_uso": "**lo más tarde** que lo ha usado, de todas sus partidas. No es el otro extremo de la misma partida que `primer_uso`",
    },
    "amigos_cuantos_puertos": {
        "partidas"       : "partidas suyas que hay apuntadas. Va delante porque sin ella lo demás no se puede comparar: cuatro veces el puerto de madera en veinte partidas no es lo mismo que cuatro en seis",
        "puerto_madera"  : "en cuántas partidas se le pudo contar el 2:1 de madera. **En cuántas partidas, no cuántas veces lo usó**: usarlo quince veces en una partida cuenta una, porque lo que se mide es tenerlo. Y «se le pudo contar» y no «lo tuvo»: esto **se deduce de los cambios que hizo**, no de mirar el tablero, así que un puerto suyo que no llegó a usar no aparece",
        "puerto_arcilla" : "lo mismo con el 2:1 de arcilla",
        "puerto_lana"    : "lo mismo con el 2:1 de lana",
        "puerto_cereales": "lo mismo con el 2:1 de cereales",
        "puerto_mineral" : "lo mismo con el 2:1 de mineral",
        "genericos"      : "en cuántas partidas se le pudo contar un puerto genérico (3:1). Los genéricos no se pueden separar entre ellos: uno ya sirve para los cinco recursos, así que tener dos no deja ninguna huella distinta de tener uno",
    },
    "amigos_puertos_pillados": {
        "puerto": "cuál es, con su cambio",
        "quien" : "quién se puso encima. **`nadie`** es un puerto que no pilló ninguno, y es media razón de que esta tabla exista",
        "turno" : "turno en que puso la pieza. Mejorar a ciudad no cuenta: el puerto se pilla al colocarse",
        "pieza" : "en qué acabó ese sitio, poblado o ciudad",
    },
    "amigos_produccion": {
        "madera"            : "madera que le dio el tablero",
        "arcilla"           : "arcilla que le dio el tablero",
        "lana"              : "lana que le dio el tablero",
        "cereales"          : "cereales que le dio el tablero",
        "mineral"           : "mineral que le dio el tablero",
        "total"             : "la suma de los cinco. **Incluye el reparto inicial**, que también lo da el tablero; si quieres sólo lo que salió tirando, réstale `del_reparto`",
        "del_reparto": "las cartas que cobró **al colocar su segundo poblado**: una por cada casilla que toca. Es lo único de `total` que no salió de una tirada, y son unas 3 por partida. Va aparte porque es la diferencia con `producido`, que sólo cuenta lo que pagó el tablero al salir el número",
        "le_quito_el_ladron": "**cartas** que no llegó a cobrar porque el ladrón tapaba la casilla. Es el mismo número que `perdido` de «El ladrón», con otro nombre: allí la fila va del ladrón y aquí de lo que produce, y en cada sitio se lee mejor así",
    },
    "amigos_numeros": {
        "edificios"    : "cuántas piezas suyas tocan ese número, sumando todas sus partidas. Trece poblados en el 6 pueden ser trece partidas con uno o dos con seis",
        "primer_poblado": "en qué turno puso ahí la primera pieza. **`0` es el reparto inicial** y una raya (—) es que nunca puso nada en ese número (son lo contrario, ojo). Dentro de una partida es el **primero**: dos poblados en el mismo número, turnos 0 y 41, dan 0 y no 20, porque desde el 0 ya cobrabas ahí. Juntando partidas es la **media** de esos primeros, y por eso lleva decimal: un 13,8 avisa de que es una media y no el turno 13. Se lee pegada a `veces_salio`, porque esa columna cuenta las tiradas de toda la partida: tener el 6 desde el turno 0 y tenerlo desde el 30 salen iguales ahí y no valen lo mismo. Mejorar a ciudad no lo mueve (cuenta cuándo se puso el poblado)",
        "puntitos"     : "los puntitos de debajo del número en la ficha: de cuántas de las 36 combinaciones de dos dados sale. El 6 lleva cinco, el 2 lleva uno. **No se suma**: es una propiedad del número, no una cuenta, así que aquí sale igual mires una partida o todas",
        "veces_salio"  : "cuántas veces salió ese número, contando sólo las partidas en las que tenía algo puesto ahí. En una partida donde no tocaba ese número no cuenta ninguna tirada",
        "deberia_salir": "cuántas veces debería haber salido, por sus puntitos: los puntitos entre 36, multiplicado por las tiradas que hubo. Se cuenta partida a partida y se suma, igual que `veces_salio`, así que las dos se pueden comparar directamente",
    },
    "amigos_sietes": {
        "partidas"         : "partidas suyas que hay apuntadas",
        "tiros"            : "cuántas veces ha tirado él los dados. Es lo que hace comparable la columna de al lado: las partidas no duran lo mismo. Se llama `tiros` y no `tiradas` a propósito (la caja de preguntas de arriba traduce «sale» y «dado» a «tirada», y con ese nombre esta tabla se llevaba preguntas de comercio)",
        "sietes"           : "cuántos de esos tiros salieron 7",
        "porcentaje"       : "qué parte de **sus** tiradas fue un 7",
        "porcentaje_normal": "el 16,7 que le toca a cualquiera: 6 de las 36 combinaciones. Por encima es que le sale el 7 más de la cuenta (y el 7 es el único número que va del que tira: mueve el ladrón y hace descartar)",
    },
    "amigos_tiradas": {
        "veces"            : "cuántas veces salió ese número",
        "veces_normales"   : "cuántas debería haber salido, por sus puntitos entre 36. El 7 son 6 de cada 36 tiradas; el 2, una",
        "porcentaje"       : "qué parte de las tiradas fue ese número",
        "porcentaje_normal": "qué parte debería haber sido: los puntitos de ese número entre 36. Se lee al lado de `porcentaje`, que es lo que pasó",
    },
    "amigos_suerte": {
        "casillas" : "**sitios suyos que cobran**, no casillas distintas del tablero. Si tiene dos piezas tocando la misma casilla, esa casilla cuenta dos veces, porque cuando sale el número le pagan dos veces. Pasa mucho: 159 casos en las partidas de ahora. Lo que **no** cuenta doble es mejorar a ciudad: los dados no saben qué hay encima, y esta columna mide cuántas veces te va a salir el número, no cuántas cartas te dan",
        "puntitos" : "los puntitos de esos sitios, sumados. **Aquí es donde un 6 pesa cinco veces lo que un 2.** Ojo con la cuenta: un 6 son **5** puntitos, no 6, así que dos sitios en un 6 son 10. Y da igual que sean dos casillas distintas del 6 o dos piezas tuyas en la misma: cobras dos veces en los dos casos",
        "por_casilla": "`puntitos` entre `casillas`: **lo que vale de media una casilla suya**. Es lo que deja comparar a dos personas, porque los puntitos a secas premian al que ha jugado más partidas",
        "lo_normal": "lo que valdría una casilla cualquiera de los tableros en los que jugó, el 3,22 del tablero de siempre. Por encima es que elige buenos sitios; por debajo, que se conforma. **Esto no es suerte, es criterio**: la suerte es que esos números salgan, y eso está en `suerte`",
        "cada_casilla": "cartas que le ha pagado de media cada casilla suya. **No se compara con `por_casilla`**: aquélla son puntitos y ésta son cartas. Aquí entran las ciudades, que pagan doble, y el ladrón, que no paga",
        "tiros": "**cuántas veces tiró el dado él.** No confundir con la de al lado: `tiradas_contadas` son todas las tiradas de la mesa que le podían pagar (las tire quien las tire) y ésta sólo las suyas, así que en una mesa de cuatro sale más o menos la cuarta parte. **No entra en la cuenta de la suerte**, porque al dado le da igual de qué mano salga: si sale un 6 cobra quien tenga algo en el 6, no quien lo tiró. El único número que sí depende del que tira es el 7, y eso está en «Los sietes de cada uno» (donde esta misma columna es el denominador)",
        "tiradas_contadas": "**sobre cuántas tiradas está medido todo lo demás.** Sin ella un 108% y un 99% parecen dos resultados comparables, y uno puede salir de 53 tiradas y el otro de 837. Son las tiradas en las que tenía algo puesto (que hoy son todas las de sus partidas, porque los dos poblados iniciales se colocan antes de que ruede el primer dado). **No es el multiplicador de `le_tocaba`**: aquélla usa la ventana de cada casilla por separado, así que ésta por los puntitos no da aquello ni tiene por qué. Es el tamaño de la muestra, no un factor",
        "le_toco"  : "**cobros, no tiradas**. Cada vez que salió un número suyo cuenta una vez **por cada casilla que tiene en él**: tres sitios en el 4 y sale un 4 son *una tirada y tres cobros*. En una partida de la base: 46 tiradas, 28 cayeron en un número suyo y cobró 41 veces. Es lo que el tablero le pagó",
        "le_tocaba": "los cobros que debería haber tenido: por cada casilla suya, sus puntitos entre 36, por cada tirada. Se cuenta igual que `le_toco` (con el mismo *por cada casilla*) y por eso las dos se comparan. Es lo que el tablero le debía",
        "de_mas"   : "`le_toco` menos `le_tocaba`, en cobros",
        "suerte"   : "`le_toco` entre `le_tocaba`, en porcentaje. **100 es la suerte normal**",
        "margen"   : "cuánto mueve el azar normalmente, en porcentaje. Con nueve casillas el azar solo ya te mueve un ±17%; con cincuenta, un ±6%",
        "se_sale"  : "cuántos márgenes se sale, con signo. **Es el número que de verdad ordena**: por debajo de 2 no hay nada que contar, pase lo que pase con el porcentaje",
    },
}


# Qué es UNA FILA en cada vista, y para qué sirve mirarla.
#
# Es lo primero que hay que saber para leer una tabla y lo único que no se
# puede deducir de los nombres de las columnas. En «El ladrón» una fila es
# una persona; en «El ladrón, uno a uno» es una PAREJA; en «Los números» es
# un número del 2 al 12. Con las mismas columnas delante, las tres se leen
# distinto.
#
# El texto va en dos partes:
#   fila  -- «una fila por cada...», para saber qué estás mirando
#   para  -- qué pregunta contesta, en la lengua en que se hace la pregunta
FILA_ES = {
    "partidas": {
        "fila": "cada partida jugada",
        "para": "ver de un vistazo cuántas llevas, cuánto duran y cuáles fueron contra la máquina",
    },
    "jugadores": {
        "fila": "cada jugador en cada partida",
        "para": "es la tabla de la que salen casi todas las demás: nombre, color, en qué puesto salió y en cuál acabó",
    },
    "amigos_marcador": {
        "fila": "cada persona",
        "para": "el marcador de siempre: quién gana más y quién acaba mejor colocado",
    },
    "amigos_salida": {
        "fila": "cada jugador en cada partida",
        "para": "ver partida a partida quién salió el primero y si le sirvió de algo",
    },
    "amigos_por_salida": {
        "fila": "cada puesto de salida (1º, 2º, 3º...)",
        "para": "la pregunta de siempre: ¿compensa salir el primero, o es mejor el último porque coloca dos poblados seguidos?",
    },
    "amigos_salida_de_cada_uno": {
        "fila": "cada persona",
        "para": "si el sorteo te trata bien: cuántas veces te ha tocado salir primero, contra las que te tocaban. **Todas sus columnas hablan de dónde empezaste, no de dónde acabaste**",
    },
    "amigos_salida_como_acabo": {
        "fila": "cada persona **y puesto de salida**",
        "para": "si a ti salir el primero te sirve. Que alguien salga mucho primero y gane mucho no dice que gane CUANDO sale primero, y ninguna otra tabla cruza las dos cosas persona a persona. Con pocas partidas sale muy repartida: es lo que hay, se lee bien cuando hay muchas",
    },
    "amigos_puntos": {
        "fila": "cada jugador en cada partida",
        "para": "de dónde salieron sus puntos: poblados, ciudades, los dos premios y, por resta, las cartas escondidas",
    },
    "amigos_desarrollo": {
        "fila": "cada persona",
        "para": "qué le sale del mazo a cada uno: si le tocan muchos caballeros o muchos puntos de victoria",
    },
    "amigos_mazo": {
        "fila": "cada tipo de carta de desarrollo",
        "para": "si el mazo se porta: lo que ha salido contra lo que el mazo lleva dentro",
    },
    "amigos_monopolios": {
        "fila": "cada monopolio jugado",
        "para": "verlos uno a uno: quién lo tiró, qué pidió y cuánto se llevó",
    },
    "amigos_monopolios_a_quien": {
        "fila": "cada pareja de jugadores",
        "para": "a quién le duelen los monopolios de quién, y en qué material",
    },
    "amigos_ladron": {
        "fila": "cada persona",
        "para": "cuánto te cuesta el ladrón en toda la partida: lo que no cobraste y lo que te robaron",
    },
    "amigos_ladron_proporcion": {
        "fila": "cada persona",
        "para": "saber a quién se lo ponen más **de verdad**, no quién ha jugado más partidas. Es «El ladrón» en proporción, y cambia el orden",
    },
    "amigos_ladron_a_quien": {
        "fila": "cada pareja de jugadores",
        "para": "las manías: si alguien te lo pone a ti mucho más que a los demás, aquí se ve",
    },
    "amigos_ladron_a_quien_numero": {
        "fila": "cada pareja de jugadores **y número**",
        "para": "si te lo ponen donde duele. No es lo mismo que te lo pongan en un 11 (con un 7 hay que moverlo a algún sitio, y a veces se busca robarte la carta sin más) que en un 6, que sale dos veces y media más. Es la más fina de las cuatro del ladrón: con pocas partidas saldrán muchas filas de 1, y eso no es un fallo",
    },
    "amigos_ladron_donde": {
        "fila": "cada persona y número",
        "para": "a qué números manda cada uno el ladrón. Casi todo el mundo tiene su número favorito",
    },
    "amigos_ladron_numeros": {
        "fila": "cada número del tablero",
        "para": "qué números acaban tapados, sumando lo que hace todo el mundo",
    },
    "amigos_produccion": {
        "fila": "cada persona",
        "para": "qué material le da el tablero a cada uno, y cuánto se quedó por el camino",
    },
    "amigos_numeros": {
        "fila": "cada persona y **cada uno de los diez números**, juntando todas sus partidas. Los diez salen siempre, aunque nunca haya puesto nada ahí: un 6 vacío dice más que media tabla. El 7 no está porque no hay fichas con un 7",
        "para": "de qué números se hace cada uno, cuánto le tocaba por ellos y cuánto le llegó. Para un tablero concreto, el desplegable filtra esta misma tabla",
    },
    "amigos_suerte": {
        "fila": "cada persona",
        "para": "quién tiene suerte de verdad. Compara lo que le tocó con lo que le tocaba, y dice si la diferencia se sale de lo normal o es ruido",
    },
    "amigos_comercio": {
        "fila": "cada pareja **y quién propuso**. La fila de vuelta son OTROS tratos: 3 y 1 quiere decir que uno pidió tres veces y el otro una, cuatro en total",
        "para": "quién le propone tratos a quién, y si sale ganando o perdiendo cartas",
    },
    "amigos_saldo": {
        "fila": "cada pareja **vista desde cada uno**. Ojo, que es lo que más se confunde: `quien` NO es el que propuso el trato (eso está en «Quién propone tratos a quién»), es desde quién se mira la fila. Las dos filas de un par son **los mismos tratos** y por eso llevan el mismo `tratos` y el `neto` con el signo cambiado",
        "para": "el saldo pelado con cada uno: cuántas cartas le has dado y cuántas te ha dado",
    },
    "amigos_tratos": {
        "fila": "cada trato cerrado",
        "para": "verlos uno a uno, con lo que se dio por lo que se recibió",
    },
    "amigos_comercio_material": {
        "fila": "cada pareja y material",
        "para": "en qué material sale ganando cada uno: «a éste siempre le acabo dando madera»",
    },
    "amigos_puertos": {
        "fila": "cada persona y puerto, juntando todas sus partidas",
        "para": "quién usa los puertos y a partir de qué turno. Se deduce de los cambios con la banca. Para un tablero concreto, el desplegable filtra esta misma tabla",
    },
    "amigos_puertos_pillados": {
        "fila": "cada puerto del mapa",
        "para": "quién se quedó cada puerto, incluidos los que no pilló nadie",
    },
    "amigos_cuantos_puertos": {
        "fila": "cada persona, juntando todas sus partidas",
        "para": "de qué puerto se hace cada uno. Tablero a tablero esto son cuatro filas casi vacías; juntando todas se ve la costumbre. Para verlo partida a partida, el desplegable filtra esta misma tabla, y «Quién pilló cada puerto» lo enseña por tablero",
    },
    "amigos_ritmo": {
        "fila": "cada jugador en cada partida",
        "para": "quién arranca antes: en qué turno llegó a su primera ciudad, a su primera carta, a su primer caballero",
    },
    "amigos_robos": {
        "fila": "cada persona",
        "para": "cuántas cartas de la mano ha robado y cuántas le han robado",
    },
    "amigos_tiradas": {
        "fila": "cada número, del 2 al 12",
        "para": "si los dados están limpios: lo que salió contra lo que debería salir",
    },
    "amigos_sietes": {
        "fila": "cada persona, juntando todas sus partidas",
        "para": "a quién le sale el 7 más de la cuenta cuando tira. «Las tiradas» mira si el dado es justo con la mesa; ésta, si lo es con cada uno",
    },
}
