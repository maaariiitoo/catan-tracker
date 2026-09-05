# -*- coding: utf-8 -*-
"""Poner de acuerdo al mod y al tracker sobre QUE SITIO del tablero es cada
sitio. Es la pieza de la que depende todo lo demas: sin esto, la verdad que
apunta el juego y lo que ve la vision son dos listas que no se pueden
comparar, y sin poder compararlas no hay ni medicion ni etiquetas para
entrenar nada.

Hay dos problemas distintos, y conviene no mezclarlos:

1. NOMBRAR un sitio sin ambiguedad. El mod dice donde esta una pieza dando
   las casillas que la rodean: tres para un vertice (CornerPosition tiene
   FaceA, FaceB, FaceC) y dos para una arista. El tracker nombra los sitios
   por las casillas que tocan DENTRO del tablero -- y eso no basta, porque
   en las seis puntas del tablero hay vertices que solo tocan una o dos
   casillas y se confunden entre si (por eso _clave_de_sitio en main.py
   tuvo que anadir la posicion ideal para desempatar).

   Aqui se usa la identidad del mod, que si es unica: las TRES casillas que
   rodean al vertice, incluidas las que caen fuera del tablero. Un vertice
   de un hexagono siempre tiene 3 hexagonos alrededor y una arista siempre
   2, esten dentro del tablero o en el mar. Verificado abajo: las 54 ternas
   son distintas y las 72 parejas tambien.

2. TRADUCIR las coordenadas del juego a las nuestras. El mod da FacePosition
   (X, Y) y el tracker usa axiales (q, r), y NO se sabe si son el mismo
   sistema: puede haber un giro, un espejo, un desplazamiento, o ser
   coordenadas "offset" en vez de axiales. En vez de suponerlo, se prueban
   todas las convenciones habituales y se elige la que encaja.

   Y encajar la FORMA no sirve: el tablero de Catan es un hexagono, que es
   simetrico bajo los 12 giros y espejos, asi que los 12 candidatos encajan
   igual de bien y no hay forma de distinguirlos por el contorno. Lo que los
   distingue es el CONTENIDO: los 18 numeros del tablero. La probabilidad de
   que un tablero girado tenga los mismos numeros en los mismos sitios es
   despreciable, asi que los numeros deciden -- y una vez decidido, los
   nombres de terreno del juego ("Forest", "Hills"...) se aprenden solos
   emparejandolos con los recursos que ya leyo la calibracion.
"""

import collections
import math
from collections import defaultdict

# Lo que puede haber en un sitio, EN EL ORDEN EN QUE LO NUMERA LA RED: el
# indice de esta lista es la clase que sale del modelo. Vivia en
# `red/modelo.py`, que no se publica y arrastra torch, y `red/reglas.py` --
# que si se publica -- lo importaba de alli dentro de una funcion. En esta
# maquina no se nota; en un clon, esa rama revienta pidiendo torch.
#
# Aqui no arrastra nada y sigue habiendo UNA sola definicion: `red/modelo.py`
# la importa de este fichero.
PIEZAS = ["vacio", "poblado", "ciudad", "carretera"]

from vision.board_graph import (
    TILE_AXIAL,
    axial_de,
    axial_to_pixel,
    _VERTICES_IDEALES,
    _ARISTAS_IDEALES,
    _topologia_ideal,
)

# Radio del hexagono en el tablero ideal (board_graph trabaja en radios).
_RADIO = 1.0
# Distancia del centro de una casilla a uno de sus vertices: el radio.
_DIST_VERTICE = _RADIO
# Distancia del centro de una casilla al punto medio de uno de sus lados:
# la apotema.
_DIST_ARISTA = _RADIO * math.sqrt(3) / 2.0
_HOLGURA = 1e-6

# Como llama el juego a cada terreno, y como lo llamamos nosotros.
#
# Cuando hay tablero del tracker con el que comparar, esto NO se usa: se
# aprende solo (ver _aprender_terrenos), que es mas robusto porque no
# depende de que el juego no cambie los nombres. Pero importando una
# partida que solo grabo el mod no hay nada de donde aprenderlo, y estos
# seis son los que lleva usando Catan Universe en las 8 grabaciones que hay.
#
# Si un dia sale un terreno que no este aqui, el importador lo dice en vez
# de guardarlo con el nombre en ingles y dejar que aparezca meses despues
# como un recurso "Lumber" que ninguna consulta encuentra.
TERRENO_DEL_JUEGO = {
    "Grain": "Cereales",
    "Ore": "Mineral",
    "Brick": "Arcilla",
    "Lumber": "Madera",
    "Wool": "Lana",
    "Desert": "Desierto",
}


_VECINOS_AXIALES = ((1, 0), (-1, 0), (0, 1), (0, -1), (1, -1), (-1, 1))


def _casillas_hasta(radio):
    """Todas las casillas axiales hasta cierta distancia del centro. Hace
    falta llegar a radio 3 aunque el tablero solo tenga radio 2: los
    vertices del borde estan rodeados tambien por casillas de fuera (el
    mar), y son justamente esas las que hacen unica su identidad."""
    salida = []
    for q in range(-radio, radio + 1):
        for r in range(-radio, radio + 1):
            if abs(q) <= radio and abs(r) <= radio and abs(q + r) <= radio:
                salida.append((q, r))
    return salida


# El vecindario tiene que pasarse del tablero: los vertices del borde estan
# rodeados TAMBIEN por casillas de fuera (el mar), y son justamente esas las
# que hacen unica su identidad. Con el tablero base (radio 2) bastaba llegar a
# radio 3; el de 5-6 llega a radio 3, asi que hace falta 4. Se deja en 5, que
# cuesta nada -- son 91 centros mas -- y evita volver a tropezar el dia que
# aparezca un tablero mayor.
_VECINDARIO = _casillas_hasta(5)
_CENTROS = {qr: axial_to_pixel(qr[0], qr[1], _RADIO) for qr in _VECINDARIO}


def _centros_alrededor_de(casillas):
    """Los centros del tablero MAS su anillo de mar.

    Los vertices del borde estan rodeados tambien por casillas de fuera, y
    son justamente esas las que hacen unica su identidad. Antes esto era una
    lista fija a radio 3 del origen, y ataba dos cosas a la vez: el tamano
    del tablero y su POSICION. Con el de 5-6 anclado en la esquina, las
    casillas se salian de esa lista y la construccion reventaba.

    Calculandolo del tablero que hay, no hay ni tamano ni posicion que valga
    -- funciona para 19, para 30 y para donde este."""
    fuera = set(casillas)
    for q, r in list(fuera):
        for dq, dr in _VECINOS_AXIALES:
            fuera.add((q + dq, r + dr))
    # y un anillo mas, que los vertices de la esquina lo necesitan
    for q, r in list(fuera):
        for dq, dr in _VECINOS_AXIALES:
            fuera.add((q + dq, r + dr))
    return {qr: axial_to_pixel(qr[0], qr[1], _RADIO) for qr in fuera}


def _caras_alrededor(punto, distancia, cuantas, centros=None):
    """Las casillas cuyo centro esta a `distancia` de ese punto. Un vertice
    tiene 3 y una arista 2, siempre, sin excepciones ni casos de borde: es
    geometria del hexagono, no una deteccion."""
    cerca = []
    for qr, (cx, cy) in (centros or _CENTROS).items():
        d = math.hypot(cx - punto[0], cy - punto[1])
        if abs(d - distancia) < 1e-6:
            cerca.append(qr)
    if len(cerca) != cuantas:
        raise AssertionError(
            "se esperaban %d casillas alrededor de %r y salieron %d: %r"
            % (cuantas, punto, len(cerca), sorted(cerca)))
    return frozenset(cerca)


def _construir(casillas=None):
    """Las tres caras de cada vertice y las dos de cada arista. Los
    identificadores (vid, eid) son los MISMOS que reparte
    board_graph.build_board_graph, que enumera estos dos diccionarios en
    este orden: si eso cambiara, cambiarian a la vez y seguirian
    cuadrando."""
    if casillas is None:
        vertices, aristas = _VERTICES_IDEALES, _ARISTAS_IDEALES
        centros = _CENTROS
    else:
        vertices, aristas = _topologia_ideal(list(casillas))
        centros = _centros_alrededor_de(casillas)
    caras_vertice = {}
    for vid, v in vertices.items():
        caras_vertice[vid] = _caras_alrededor(v["xy"], _DIST_VERTICE, 3, centros)

    caras_arista = {}
    for eid, (par, _tiles) in enumerate(aristas.items()):
        va, vb = tuple(par)
        pa, pb = vertices[va]["xy"], vertices[vb]["xy"]
        medio = ((pa[0] + pb[0]) / 2.0, (pa[1] + pb[1]) / 2.0)
        caras_arista[eid] = _caras_alrededor(medio, _DIST_ARISTA, 2, centros)
    return caras_vertice, caras_arista


class Reticula:
    """Los nombres de los sitios de UN tablero concreto.

    Esto era un punado de globales calculadas una vez para las 19 casillas
    del tablero base. Se hizo clase para que quepa el tablero de 5-6
    jugadores: 30 casillas (filas 3-4-5-6-5-4-3), 86 vertices y 115 aristas
    -- comprobado con Euler, 86-115+31 = 2, o sea conexo y sin agujeros.

    Lo importante es que la FORMA no esta escrita en ningun sitio. Se
    construye con las casillas que se le den, y para el de 5-6 esas casillas
    salen de lo que apunto el mod. Cablear una forma de 30 adivinada seria
    justo el fallo silencioso que este proyecto lleva documentado tres veces:
    todo seguiria funcionando y estaria nombrando sitios que no son."""

    def __init__(self, casillas):
        self.casillas = tuple(casillas)
        vert, aris = _construir(self.casillas)
        self.caras_de_vertice = vert
        self.caras_de_arista = aris
        self.vertice_por_caras = {c: vid for vid, c in vert.items()}
        self.arista_por_caras = {c: eid for eid, c in aris.items()}
        # Si esto saltara, dos sitios distintos compartirian nombre y todo lo
        # que viene despues emparejaria cosas que no son la misma.
        if len(self.vertice_por_caras) != len(vert):
            raise ValueError("las ternas no identifican los %d vertices: %d"
                             % (len(vert), len(self.vertice_por_caras)))
        if len(self.arista_por_caras) != len(aris):
            raise ValueError("las parejas no identifican las %d aristas: %d"
                             % (len(aris), len(self.arista_por_caras)))
        self.conjunto = frozenset(self.casillas)
        self.indice = {qr: i for i, qr in enumerate(self.casillas)}

    def __len__(self):
        return len(self.casillas)


_reticulas = {}


def reticula_de(casillas):
    """La reticula de ese conjunto de casillas, calculada una sola vez."""
    clave = frozenset(casillas)
    if clave not in _reticulas:
        # Siempre en el mismo orden, para que los identificadores no bailen
        # de una ejecucion a otra.
        _reticulas[clave] = Reticula(sorted(clave, key=lambda qr: (qr[1], qr[0])))
    return _reticulas[clave]


RETICULA_BASE = Reticula(TILE_AXIAL)

# Las de siempre, que son las del tablero base. Se dejan porque medio
# proyecto las importa, y para 19 casillas valen exactamente lo que valian.
CARAS_DE_VERTICE = RETICULA_BASE.caras_de_vertice
CARAS_DE_ARISTA = RETICULA_BASE.caras_de_arista
VERTICE_POR_CARAS = RETICULA_BASE.vertice_por_caras
ARISTA_POR_CARAS = RETICULA_BASE.arista_por_caras
CASILLAS_DEL_TABLERO = RETICULA_BASE.conjunto
INDICE_DE_CASILLA = RETICULA_BASE.indice

# EL NOMBRE DE UN SITIO, y el corte entre vertices y aristas.
#
# Vive aqui, y no en `red/dataset.py`, por dos motivos que apuntan al mismo
# sitio. El de fondo: este fichero es el que nombra los sitios del tablero,
# asi que el numero con el que se les llama es suyo. Y el practico: al
# publicar, `red/reglas.py` SI va al repositorio (sin el, un clon no puede
# importar una partida) y `red/dataset.py` NO -- arrastra OpenCV y las
# grabaciones. Teniendo esto en dataset, reglas lo importaba y un clon
# recien bajado se quedaba sin poder importar nada. Hay una prueba que lo
# comprueba, porque leyendo el .gitignore no se ve.
#
# Se separa en el 80, el tope de vertices de cualquier tablero (54 el de 19,
# 80 el de 5-6): los vertices caen por debajo y las aristas por encima, valga
# el tablero que valga. Ver `dataset.clave_de_sitio`, que es quien lo aplica.
TOPE_VERTICES = 80


def es_arista(clave):
    """Si una clave de sitio es de arista. Vertices por debajo del tope."""
    return clave >= TOPE_VERTICES


assert len(VERTICE_POR_CARAS) == 54 and len(ARISTA_POR_CARAS) == 72,     "el tablero base tiene que dar 54 vertices y 72 aristas, y da %d y %d"     % (len(VERTICE_POR_CARAS), len(ARISTA_POR_CARAS))


# --- las 12 simetrias del hexagono -----------------------------------
# En coordenadas axiales el giro de 60 grados y el espejo son cuentas
# exactas con enteros (salen de las coordenadas cubicas), asi que no hay
# redondeos de por medio.

def _girar(qr):
    q, r = qr
    return (-r, q + r)


def _espejar(qr):
    q, r = qr
    return (q, -q - r)


def _simetrias():
    salida = []
    for espejo in (False, True):
        for giros in range(6):
            salida.append((espejo, giros))
    return salida


def _aplicar_simetria(qr, simetria):
    espejo, giros = simetria
    if espejo:
        qr = _espejar(qr)
    for _ in range(giros):
        qr = _girar(qr)
    return qr


# --- las convenciones de coordenadas que puede estar usando el juego ---
# El mod entrega FacePosition (X, Y) y no consta en ningun sitio que sean
# axiales. Estas son las formas habituales de numerar una rejilla
# hexagonal; se prueban todas y gana la que cuadre con los numeros del
# tablero, asi que no hay que acertar a la primera.

def _axial(x, y):
    return (x, y)


def _impar_r(x, y):
    return (x - (y - (y & 1)) // 2, y)


def _par_r(x, y):
    return (x - (y + (y & 1)) // 2, y)


def _impar_q(x, y):
    return (x, y - (x - (x & 1)) // 2)


def _par_q(x, y):
    return (x, y - (x + (x & 1)) // 2)


CONVENCIONES = [
    ("axial", _axial),
    ("offset impar-r", _impar_r),
    ("offset par-r", _par_r),
    ("offset impar-q", _impar_q),
    ("offset par-q", _par_q),
]


_VECINOS = ((1, 0), (-1, 0), (0, 1), (0, -1), (1, -1), (-1, 1))


def _es_un_tablero(colocadas):
    """Si esas axiales tienen la forma de un tablero de Catan.

    Sustituye a comparar con una forma conocida cuando no la hay, y hay que
    tener cuidado con lo que se pide. Dos intentos se quedaron cortos:

    1. «Sin repetir y de una pieza» -- lo cumple un paralelogramo sesgado, que
       es justo lo que produce una convencion de coordenadas equivocada.

    2. «Que el perfil de filas suba y baje de uno en uno y sea simetrico»
       (3-4-5-4-3, 3-4-5-6-5-4-3) -- lo cumple TAMBIEN un zigzag, filas del
       largo correcto pero desplazadas a un lado y a otro. Medido: nombraba
       92 vertices donde hay 86. Todo habria seguido funcionando, nombrando
       sitios que no son.

    Lo que de verdad define un tablero es que sea CONVEXO en los tres ejes
    del hexagono. En una rejilla hexagonal hay tres direcciones de fila --
    `r` constante, `q` constante y `q+r` constante -- y en un tablero, entre
    dos casillas de la misma linea estan todas las de en medio. En un zigzag
    o en un sesgo, no. Es una condicion geometrica, no un tamano: vale para
    las 19 del base, para las 30 del de 5-6 y para el que venga."""
    unicas = set(colocadas)
    if len(unicas) != len(colocadas) or len(unicas) < 7:
        return False
    for eje in (lambda qr: qr[1],            # filas: r constante
                lambda qr: qr[0],            # columnas: q constante
                lambda qr: qr[0] + qr[1]):   # diagonales: q+r constante
        lineas = {}
        for qr in unicas:
            lineas.setdefault(eje(qr), []).append(qr)
        for clave, puntos in lineas.items():
            # dentro de una linea basta ordenar por q (o por r si q es fijo)
            seguidas = sorted(q for q, _r in puntos)                 if len({q for q, _r in puntos}) == len(puntos)                 else sorted(r for _q, r in puntos)
            if seguidas != list(range(seguidas[0], seguidas[0] + len(seguidas))):
                return False

    # Convexo no basta: un paralelogramo tambien lo es, y tiene cuatro lados
    # donde un tablero tiene seis. Lo que lo distingue es el perfil de las
    # filas -- sube de una en una hasta el centro y baja igual, simetrico.
    # 3-4-5-4-3 en el base, 3-4-5-6-5-4-3 en el de 5-6; un paralelogramo da
    # 5-5-5-5-5-5 y se cae aqui. Las dos condiciones juntas dejan pasar los
    # tableros y solo los tableros, sin escribir ningun tamano.
    largos = collections.Counter(r for _q, r in unicas)
    perfil = [largos[r] for r in sorted(largos)]
    if len(perfil) < 3 or perfil != perfil[::-1]:
        return False
    for i in range(len(perfil) // 2):
        if perfil[i + 1] - perfil[i] != 1:
            return False
    return perfil[0] >= 3


class Alineador:
    """Traduce las posiciones del mod a las del tracker.

    Se construye con `encajar`, que lo deduce de una partida real; no se
    configura a mano. Una vez encajado, `vertice` y `arista` devuelven el
    mismo identificador que usa board_graph, y `casilla` el indice 0-18
    dentro de TILE_AXIAL."""

    def __init__(self, convencion, intercambio, simetria, desplazamiento,
                 aciertos=None, de_cuantas=None, segundo=None, reticula=None):
        self.convencion = convencion
        self.intercambio = intercambio
        self.simetria = simetria
        self.desplazamiento = desplazamiento
        self.aciertos = aciertos
        self.de_cuantas = de_cuantas
        self.segundo = segundo
        # La del tablero base si no se dice otra cosa, que es lo que usaban
        # todas las llamadas de antes.
        self.reticula = reticula or RETICULA_BASE
        self.vocabulario_terreno = {}
        self.terrenos_sin_traducir = []

    # --- traduccion ---------------------------------------------------
    def cara(self, xy):
        """Una FacePosition del mod -> axial del tracker. Vale tambien para
        las casillas de fuera del tablero, que es lo que hace unica la
        identidad de los vertices del borde."""
        x, y = int(xy[0]), int(xy[1])
        if self.intercambio:
            x, y = y, x
        qr = self.convencion[1](x, y)
        qr = _aplicar_simetria(qr, self.simetria)
        return (qr[0] + self.desplazamiento[0], qr[1] + self.desplazamiento[1])

    def casilla(self, xy):
        """Indice 0-18 dentro de TILE_AXIAL, o None si cae fuera."""
        return self.reticula.indice.get(self.cara(xy))

    def vertice(self, caras):
        """Las 3 caras que da el mod -> vid, o None si no cuadra."""
        return self.reticula.vertice_por_caras.get(
            frozenset(self.cara(c) for c in caras))

    def arista(self, caras):
        return self.reticula.arista_por_caras.get(
            frozenset(self.cara(c) for c in caras))

    def sitio(self, posicion):
        """Un bloque "donde" del fichero del mod -> ('vertice'|'arista', id).

        No se fia de la etiqueta "que" que trae el mod (corner/edge): se
        mira cuantas casillas vienen, que es lo que de verdad determina de
        que se trata."""
        if not posicion:
            return None
        caras = posicion.get("casillas") or []
        caras = [c for c in caras if c is not None]
        if len(caras) == 3:
            vid = self.vertice(caras)
            return ("vertice", vid) if vid is not None else None
        if len(caras) == 2:
            eid = self.arista(caras)
            return ("arista", eid) if eid is not None else None
        return None

    def __repr__(self):
        return ("<Alineador %s%s, giro %d%s, desplaza %r -- %s/%s numeros>"
                % (self.convencion[0],
                   " con X e Y intercambiadas" if self.intercambio else "",
                   self.simetria[1], " con espejo" if self.simetria[0] else "",
                   self.desplazamiento, self.aciertos, self.de_cuantas))

    def explicacion(self):
        lineas = ["coordenadas del juego: %s%s"
                  % (self.convencion[0],
                     " con X e Y intercambiadas" if self.intercambio else ""),
                  "giro de %d x 60 grados%s"
                  % (self.simetria[1], " y espejo" if self.simetria[0] else ""),
                  "desplazamiento %r" % (self.desplazamiento,)]
        if self.de_cuantas:
            lineas.append("cuadra en %d de %d numeros del tablero (el siguiente "
                          "candidato, %d)" % (self.aciertos, self.de_cuantas,
                                              self.segundo))
        if self.vocabulario_terreno:
            lineas.append("terrenos aprendidos: " + ", ".join(
                "%s=%s" % (k, v) for k, v in sorted(self.vocabulario_terreno.items())))
        lineas += self.problemas()
        return "\n".join(lineas)

    def problemas(self):
        """Lo que la alineacion deja ver de que la calibracion leyo mal el
        tablero. La alineacion puede ganar igualmente -- gana con los
        numeros, y le sobran unos cuantos -- pero eso no la convierte en una
        lectura buena, y hasta ahora "cuadra en 15 de 19" se leia como un
        exito cuando en realidad decia que 4 casillas estaban mal."""
        avisos = []
        if self.de_cuantas and self.aciertos is not None:
            fallan = self.de_cuantas - self.aciertos
            if fallan:
                avisos.append(
                    "AVISO: %d de las %d casillas NO cuadran en el numero. La "
                    "alineacion gana igual (%d contra %d), pero esas casillas "
                    "las leyo mal la calibracion." %
                    (fallan, self.de_cuantas, self.aciertos, self.segundo or 0))
        if self.terrenos_sin_traducir:
            avisos.append(
                "AVISO: no se ha podido traducir el terreno %s. Los seis "
                "terrenos de Catan son seis cosas distintas, asi que si uno se "
                "queda sin sitio es que la calibracion leyo mal su casilla."
                % ", ".join(self.terrenos_sin_traducir))
        return avisos

    # --- deduccion ----------------------------------------------------
    @staticmethod
    def encajar(casillas_mod, casillas_tracker, minimo=15, margen=5):
        """Deduce la traduccion comparando un tablero visto por los dos.

        casillas_mod:     lo que trae el fichero del mod, [{"pos":[x,y],
                          "terreno":str, "numero":int|None}, ...]
        casillas_tracker: las 19 casillas calibradas EN EL ORDEN DE
                          TILE_AXIAL, [{"resource":str, "number":int|None},...]

        Devuelve un Alineador, o lanza ValueError explicando por que no se
        ha podido -- que es mejor que devolver uno cualquiera de los 12 que
        encajan por forma y dejar que el error salga tres pasos mas
        adelante convertido en "la vision falla mucho"."""
        # EL TABLERO PUEDE SER DE 19 O DE 30. Los dos lados tienen que traer
        # el mismo, y tiene que ser uno que exista: el basico o el de 5-6.
        # Antes esto exigia 19 a secas, asi que una partida de seis moria
        # aqui con «el mod apunto 30 casillas, no 19» -- y el resto de la
        # funcion ya sabia trabajar con cualquier tamano.
        cuantas = len(casillas_mod)
        if len(casillas_tracker) != cuantas:
            raise ValueError(
                "el tracker trae %d casillas y el mod %d: no son el mismo "
                "tablero" % (len(casillas_tracker), cuantas))
        try:
            reticula = axial_de(cuantas)
        except ValueError as e:
            raise ValueError(str(e))
        # LOS DOS LADOS TIENEN QUE ANCLARSE IGUAL o no se tocan nunca. En el
        # tablero de 19 las coordenadas del mod se centran en el origen, y la
        # reticula de `board_graph` tambien, asi que coinciden solas. En el
        # de 5-6 el centro cae entre dos casillas y no se puede centrar: se
        # ancla en la esquina (minimo 0,0). Si la reticula del tracker se
        # deja centrada y la del mod anclada en la esquina, `numero_esperado`
        # se consulta con claves que no existen y cuadran 3 de 30 -- que es
        # exactamente lo que pasaba.
        if cuantas != 19:
            dq = -min(qr[0] for qr in reticula)
            dr = -min(qr[1] for qr in reticula)
            reticula = [(q + dq, r + dr) for q, r in reticula]

        numero_esperado = {}
        for i, casilla in enumerate(casillas_tracker):
            numero_esperado[reticula[i]] = casilla.get("number")

        candidatos = []
        for intercambio in (False, True):
            for convencion in CONVENCIONES:
                convertidas = []
                for casilla in casillas_mod:
                    x, y = casilla["pos"]
                    if intercambio:
                        x, y = y, x
                    convertidas.append(convencion[1](int(x), int(y)))
                for simetria in _simetrias():
                    giradas = [_aplicar_simetria(qr, simetria) for qr in convertidas]
                    # el desplazamiento no se busca: sale de exigir que los
                    # centros coincidan, y si no es entero ya no puede encajar
                    # El desplazamiento no se busca: sale de exigir que los
                    # centros coincidan. El tablero de 19 es simetrico
                    # respecto de una casilla y su centro es entero; el de
                    # 5-6 no lo es -- su centro cae entre dos casillas -- asi
                    # que ahi se ancla en la esquina, igual que en
                    # `encajar_solo`. Exigirle centro entero rechazaba las 12
                    # simetrias, o sea el tablero entero.
                    if cuantas == 19:
                        sq = sum(qr[0] for qr in giradas)
                        sr = sum(qr[1] for qr in giradas)
                        if sq % cuantas or sr % cuantas:
                            continue
                        desplazamiento = (-sq // cuantas, -sr // cuantas)
                    else:
                        desplazamiento = (-min(qr[0] for qr in giradas),
                                          -min(qr[1] for qr in giradas))
                    colocadas = [(qr[0] + desplazamiento[0], qr[1] + desplazamiento[1])
                                 for qr in giradas]
                    if cuantas == 19 and set(colocadas) != CASILLAS_DEL_TABLERO:
                        continue  # ni siquiera es el tablero: no hay nada que puntuar
                    if cuantas != 19 and len(set(colocadas)) != cuantas:
                        continue  # dos casillas en el mismo sitio: no es reticula
                    aciertos = sum(
                        1 for qr, casilla in zip(colocadas, casillas_mod)
                        if numero_esperado.get(qr) == casilla.get("numero"))
                    # La clave es la CORRESPONDENCIA, no los parametros: hay
                    # sistemas de coordenadas distintos que colocan el tablero
                    # exactamente igual (los offset y los axiales coinciden en
                    # muchos casos). Contarlos como candidatos distintos
                    # hacia que el ganador siempre empatara consigo mismo y no
                    # se aceptara nunca una alineacion, ni siquiera la correcta.
                    candidatos.append((aciertos, tuple(colocadas), convencion,
                                       intercambio, simetria, desplazamiento))

        if not candidatos:
            raise ValueError(
                "ninguna convencion de coordenadas convierte lo que apunta el "
                "mod en un tablero de %d casillas. Mira las posiciones crudas "
                % cuantas +
                "del fichero: puede que FacePosition no sea una rejilla "
                "hexagonal como se supone.")

        distintos = {}
        for c in candidatos:
            if c[1] not in distintos:
                distintos[c[1]] = c
        candidatos = sorted(distintos.values(), key=lambda c: -c[0])
        mejor = candidatos[0]
        segundo = candidatos[1][0] if len(candidatos) > 1 else 0
        if mejor[0] < minimo or mejor[0] - segundo < margen:
            raise ValueError(
                "no hay un ganador claro: el mejor cuadra en %d numeros de %d y "
                "el siguiente en %d. El tablero es simetrico, asi que si los "
                "numeros no deciden no hay nada que decida. Comprueba que la "
                "calibracion de esta partida es la de ESTE tablero."
                % (mejor[0], cuantas, segundo))

        alineador = Alineador(mejor[2], mejor[3], mejor[4], mejor[5],
                              aciertos=mejor[0], de_cuantas=cuantas,
                              segundo=segundo,
                              reticula=(None if cuantas == 19
                                        else reticula_de(list(mejor[1]))))
        alineador.vocabulario_terreno, alineador.terrenos_sin_traducir = (
            _aprender_terrenos(mejor[1], casillas_mod, casillas_tracker))
        return alineador


    @staticmethod
    def encajar_solo(casillas_mod):
        """Nombra los sitios cuando NO hay tablero del tracker con el que
        alinearse -- una partida que solo grabo el mod.

        `encajar` usa los numeros del tracker para elegir entre las 12
        simetrias. Aqui no hay con que elegir, y no hace falta: sin un
        segundo tablero al que pegarse, las 12 son igual de validas. El
        tablero de Catan no tiene arriba ni abajo, asi que "girado dos
        sextos" no es una lectura peor, es la misma lectura con otro nombre.

        Lo unico que hay que exigir -- y se exige -- es que la traduccion
        sea CONSISTENTE y BIYECTIVA: que las 19 casillas caigan exactamente
        sobre las 19 del tablero, sin dejar ninguna fuera ni pisar dos en la
        misma. Con eso, cada vertice y cada arista tienen un nombre unico
        dentro de la partida, que es para lo que sirve el nombre.

        Se elige la primera que encaja recorriendo siempre en el mismo orden,
        para que reimportar la misma grabacion de los mismos nombres."""
        tierra = [c for c in casillas_mod if c.get("terreno") != "Water"]
        cuantas = len(tierra)
        if cuantas < 19:
            raise ValueError("el mod apunto %d casillas de tierra: son pocas "
                             "para un tablero de Catan" % cuantas)

        for intercambio in (False, True):
            for convencion in CONVENCIONES:
                convertidas = []
                for casilla in tierra:
                    x, y = casilla["pos"]
                    if intercambio:
                        x, y = y, x
                    convertidas.append(convencion[1](int(x), int(y)))
                for simetria in _simetrias():
                    giradas = [_aplicar_simetria(qr, simetria) for qr in convertidas]
                    if cuantas == 19:
                        # Centrar en el origen, que es donde esta el tablero
                        # base. Si la suma no divide, esta simetria no puede
                        # colocarlo ahi y se prueba la siguiente.
                        sq = sum(qr[0] for qr in giradas)
                        sr = sum(qr[1] for qr in giradas)
                        if sq % cuantas or sr % cuantas:
                            continue
                        desplazamiento = (-sq // cuantas, -sr // cuantas)
                    else:
                        # Cualquier otro tablero NO tiene por que poder
                        # centrarse en el origen: el de 5-6 (filas
                        # 3-4-5-6-5-4-3) no es simetrico respecto de una
                        # casilla, asi que su centro cae entre dos y la suma
                        # no divide nunca. Exigirlo rechazaba las 12
                        # simetrias y las dos convenciones -- o sea el
                        # tablero entero.
                        #
                        # Y no hace falta centrarlo: la reticula se construye
                        # con las casillas que salgan, asi que lo unico que
                        # importa es que la traslacion sea SIEMPRE la misma.
                        # Se ancla en la esquina, que no depende de la forma.
                        desplazamiento = (-min(qr[0] for qr in giradas),
                                          -min(qr[1] for qr in giradas))
                    colocadas = [(qr[0] + desplazamiento[0], qr[1] + desplazamiento[1])
                                 for qr in giradas]
                    if cuantas == 19:
                        # El tablero base tiene forma conocida, asi que se
                        # exige que cuadre exactamente: es la comprobacion mas
                        # fuerte que hay y no se rebaja.
                        if set(colocadas) != CASILLAS_DEL_TABLERO:
                            continue
                        reticula = RETICULA_BASE
                    else:
                        # Cualquier otro tablero -- el de 5-6 son 30 casillas
                        # en filas 3-4-5-6-5-4-3 -- no tiene forma escrita en
                        # ningun sitio, y NO se inventa: se toma la que apunto
                        # el mod. Lo que si se exige es que la conversion sea
                        # sana, que es lo que de verdad se esta comprobando
                        # aqui: biyectiva (ninguna casilla encima de otra) y
                        # de una sola pieza (un tablero de Catan es conexo).
                        # Una convencion equivocada da casillas repetidas o
                        # desperdigadas, asi que estas dos condiciones la
                        # descartan igual de bien que comparar con una forma.
                        if not _es_un_tablero(colocadas):
                            continue
                        reticula = reticula_de(colocadas)
                    return Alineador(convencion, intercambio, simetria,
                                     desplazamiento, aciertos=None,
                                     de_cuantas=None, reticula=reticula)

        raise ValueError(
            "ninguna convencion de coordenadas convierte las %d casillas que "
            "apunto el mod en un tablero hexagonal de una pieza. Mira las "
            "posiciones crudas del fichero: puede que FacePosition no sea una "
            "rejilla hexagonal como se supone." % cuantas)


def _aprender_terrenos(colocadas, casillas_mod, casillas_tracker):
    """Como llama el juego a cada terreno. No hace falta escribirlo a mano:
    con la traduccion ya decidida, cada casilla del mod cae sobre una del
    tracker y el nombre del juego queda emparejado con el recurso que leyo
    la calibracion.

    Es una BIYECCION, y eso no es un detalle: los seis terrenos de Catan son
    seis cosas distintas, asi que dos nombres del juego no pueden significar
    el mismo recurso. Quedandose con el mas votado sin mas, en la primera
    partida grabada salio `Desert=Mineral` a la vez que `Ore=Mineral`:
    Desert sale UNA vez en el tablero, la calibracion leyo mal esa casilla,
    y con un solo voto el mas votado era el equivocado.

    Se reparte por votos de mas a menos y un recurso solo se asigna una vez.
    Asi Ore se queda Mineral con sus 8 votos y Desert, que solo tenia ese,
    se queda SIN traducir -- que es lo correcto: no se sabe. Los que quedan
    sin traducir los devuelve aparte para poder avisar."""
    votos = defaultdict(lambda: defaultdict(int))
    for qr, casilla in zip(colocadas, casillas_mod):
        i = INDICE_DE_CASILLA.get(qr)
        if i is None:
            continue
        recurso = (casillas_tracker[i] or {}).get("resource")
        terreno = casilla.get("terreno")
        if recurso and terreno:
            votos[terreno][recurso] += 1

    candidatos = []
    for terreno, cuenta in votos.items():
        for recurso, n in cuenta.items():
            candidatos.append((n, terreno, recurso))
    # de mas votos a menos; a igualdad, por nombre, para que no dependa del
    # orden en que se recorrio un diccionario
    candidatos.sort(key=lambda c: (-c[0], c[1], c[2]))

    vocabulario, usados = {}, set()
    for _n, terreno, recurso in candidatos:
        if terreno in vocabulario or recurso in usados:
            continue
        vocabulario[terreno] = recurso
        usados.add(recurso)
    sin_traducir = sorted(t for t in votos if t not in vocabulario)
    return vocabulario, sin_traducir


if __name__ == "__main__":
    # Autoprueba: que los nombres de sitio sean unicos es la condicion de
    # la que cuelga todo lo demas, asi que se comprueba con numeros a la
    # vista y no solo con un assert callado.
    print("vertices: %d, ternas de casillas distintas: %d"
          % (len(CARAS_DE_VERTICE), len(VERTICE_POR_CARAS)))
    print("aristas:  %d, parejas de casillas distintas: %d"
          % (len(CARAS_DE_ARISTA), len(ARISTA_POR_CARAS)))

    dentro = defaultdict(int)
    for caras in CARAS_DE_VERTICE.values():
        dentro[len(caras & CASILLAS_DEL_TABLERO)] += 1
    print("vertices por num. de casillas DENTRO del tablero: %s" % dict(sorted(dentro.items())))

    # Y esto es exactamente lo que obligo a inventar _clave_de_sitio: por
    # las casillas de dentro solas, los sitios NO son unicos.
    solo_dentro = {frozenset(c & CASILLAS_DEL_TABLERO) for c in CARAS_DE_VERTICE.values()}
    print("...si solo se miraran las de dentro, quedarian %d nombres para 54 vertices"
          % len(solo_dentro))
    solo_dentro_a = {frozenset(c & CASILLAS_DEL_TABLERO) for c in CARAS_DE_ARISTA.values()}
    print("...y %d nombres para 72 aristas" % len(solo_dentro_a))

    # Las 12 simetrias tienen que ser 12 de verdad (si _girar o _espejar
    # estuvieran mal, algunas coincidirian y el alineador buscaria menos
    # candidatos de los que cree).
    muestras = tuple(TILE_AXIAL)
    distintas = {tuple(_aplicar_simetria(qr, s) for qr in muestras) for s in _simetrias()}
    print("simetrias del hexagono distintas: %d (esperadas 12)" % len(distintas))
    assert len(distintas) == 12
    for s in _simetrias():
        assert {_aplicar_simetria(qr, s) for qr in TILE_AXIAL} == CASILLAS_DEL_TABLERO, \
            "una simetria saca el tablero de su sitio: %r" % (s,)
    print("las 12 dejan el tablero donde estaba: por eso la forma NO desempata.")

    print("\nOK: los sitios tienen nombre unico y las simetrias son las 12.")
