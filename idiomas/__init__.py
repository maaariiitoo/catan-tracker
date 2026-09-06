# -*- coding: utf-8 -*-
"""El panel en otros idiomas. Un fichero por idioma, en esta misma carpeta.

CÓMO SE AÑADE UNO. Se copia `en.py`, se traduce y se llama `fr.py`. Nada más:
esto lo encuentra solo, el botón del panel lo mete en la vuelta y
`db/pruebas.py` empieza a exigirle que esté completo. No hay ninguna lista
que actualizar, que es justo el sitio donde alguien se olvidaría.

CÓMO SE APLICA, que no es de una sola forma:

  TEXTO     la página se recorre separando etiquetas de texto y sólo se toca
            el texto. El CSS y el JavaScript van dentro de <style> y <script>
            y ésos se apartan antes. Un `replace` a ciegas sobre la página
            entera rompería el panel: palabras como «dentro» o «nunca»
            aparecen también en el código.
  GUION     dentro del <script>, pero SIEMPRE con las comillas incluidas.
            Buscando `"EL MOD ESTA ENCENDIDO"` con sus comillas no hay forma
            de tocar un nombre de variable por accidente.
  FRASES    las manda el servidor ya traducidas. Los titulares se traducen
            ANTES de rellenarlos: para cuando el panel los ve, `{victorias}
            de {partidas}` ya es `7 of 10`.
  COLUMNAS  la etiqueta que se pinta encima de cada columna. El nombre de SQL
            no se toca: con él se ordena, se filtra y se busca.

EL CASTELLANO NO TIENE FICHERO. Es el original: la página tal cual está
escrita. Por eso `frase()` y compañía devuelven lo que les llega cuando el
idioma es `es` o no existe.
"""
import importlib
import os
import pkgutil
import re
import unicodedata

ORIGINAL = "es"
NOMBRE_ORIGINAL = "Castellano"
BOTON_ORIGINAL = "ES  Castellano"
DECIMAL_ORIGINAL = ","


def _un_solo_barrido(giros):
    """Los giros, listos para aplicarse TODOS DE UNA PASADA.

    Uno a uno no vale, y no es una cuestión de velocidad. `sur qui` se
    convierte en `a quien`, y ese resultado contiene `a qui`, que es OTRO
    giro: la segunda pasada lo vuelve a tocar y sale `a quienen`. Con una
    sola pasada, lo que ya se ha sustituido no se vuelve a mirar.

    Van de más largo a más corto para que `combien de fois` gane a
    `combien de`, que es la mitad del mismo giro.
    """
    pares = sorted(giros, key=lambda p: -len(p[0]))
    if not pares:
        return None, {}
    cual = {viejo: nuevo for viejo, nuevo in pares}
    patron = re.compile("|".join(re.escape(v) for v, _n in pares))
    return patron, cual

def _cargar():
    """Todos los `.py` de esta carpeta que no empiecen por `_`.

    Se descubren solos en vez de llevar una lista escrita: una lista es un
    segundo sitio que actualizar, y el día que alguien añada un idioma y se
    olvide de apuntarlo, el fichero estaría ahí y no saldría en el botón --
    sin dar ningún error.
    """
    fuera = {}
    for _cargador, nombre, _paquete in pkgutil.iter_modules(
            [os.path.dirname(os.path.abspath(__file__))]):
        if nombre.startswith("_"):
            continue
        modulo = importlib.import_module("%s.%s" % (__name__, nombre))
        # Un módulo de esta carpeta es un IDIOMA sólo si dice cómo se llama.
        # Sin esta línea, `catalogEN.py` --que es la referencia de columnas,
        # no un idioma-- saldría en el botón como un idioma más.
        if not hasattr(modulo, "NOMBRE"):
            continue
        fuera[nombre] = {
            "nombre": getattr(modulo, "NOMBRE", nombre),
            "boton": getattr(modulo, "BOTON", nombre),
            "decimal": getattr(modulo, "DECIMAL", DECIMAL_ORIGINAL),
            "texto": getattr(modulo, "TEXTO", {}),
            "guion": getattr(modulo, "GUION", {}),
            "frases": getattr(modulo, "FRASES", {}),
            "columnas": getattr(modulo, "COLUMNAS", {}),
            # La caja de preguntas. Los giros se guardan de mas largo a mas
            # corto: aplicando «combien de» antes que «combien de fois» se
            # comeria la mitad del segundo y quedaria un «fois» suelto.
            "giros": _un_solo_barrido(getattr(modulo, "GIROS", ())),
            "preguntas": getattr(modulo, "PREGUNTAS", {}),
            # Y con lo que CONTESTA. Son plantillas de `%`, no de
            # `{}`: los huecos van por orden y no por nombre.
            "respuestas": getattr(modulo, "RESPUESTAS", {}),
            # Las fichas de columna, con la MISMA forma que
            # `db/columnas.py`: las comunes por un lado y las propias de cada
            # vista por otro. Así el fichero de un idioma y el original se
            # pueden leer uno al lado del otro.
            "comunes": getattr(modulo, "COMUNES", {}),
            "por_vista": getattr(modulo, "POR_VISTA", {}),
            "fila_es": getattr(modulo, "FILA_ES", {}),
        }
    return fuera


IDIOMAS = _cargar()


def la_vuelta():
    """Los idiomas que hay, el original el primero, para el desplegable.

    Era un botón que los recorría en círculo, como el de claro/oscuro. Con
    dos vale; a la tercera deja de valer, porque para llegar al último hay
    que pasar por los de en medio y cada paso recarga la página.
    """
    vuelta = [{"id": ORIGINAL, "nombre": NOMBRE_ORIGINAL,
               "boton": BOTON_ORIGINAL}]
    for clave in sorted(IDIOMAS):
        vuelta.append({"id": clave, "nombre": IDIOMAS[clave]["nombre"],
                       "boton": IDIOMAS[clave]["boton"]})
    return vuelta


def pregunta(texto, idioma):
    """Una pregunta en otro idioma, dicha con las palabras que ya entiende
    la caja.

    NO la traduce, la reescribe. El emparejador de `panel.preguntar` no
    entiende ningún idioma: parte la pregunta en palabras y las compara con
    los nombres, títulos y columnas de las vistas, que están escritos en
    castellano. Así que no hay que enseñarle inglés, hay que darle las
    palabras en castellano.

    El resultado no es castellano correcto y no tiene por qué serlo: «who
    wins most» sale como «quien victoria mas», que no se lee bien y empareja
    igual de bien. Lo único que importa es la bolsa de palabras.

    Los acentos se quitan aquí porque `_pelado` los quita después de todas
    formas, y así los giros y las palabras se pueden escribir sin ellos.
    """
    lengua = IDIOMAS.get(idioma)
    if lengua is None or not lengua["preguntas"]:
        return texto
    t = unicodedata.normalize("NFD", str(texto).lower())
    t = "".join(c for c in t if not 0x300 <= ord(c) <= 0x36f)
    patron, cual = lengua["giros"]
    if patron is not None:
        t = patron.sub(lambda m: cual[m.group(0)], t)
    # Se parte conservando los separadores para no pegar dos palabras al
    # borrar una vacía: «how many games» tiene que quedar «cuantas partida»
    # y no «cuantaspartida».
    return "".join(lengua["preguntas"].get(x, x)
                   for x in re.findall(r"[a-z0-9]+|[^a-z0-9]+", t))


def decimal(idioma):
    """Con qué se escribe la coma decimal en este idioma."""
    lengua = IDIOMAS.get(idioma)
    return DECIMAL_ORIGINAL if lengua is None else lengua["decimal"]


def frase(cadena, idioma):
    """Una frase del servidor en otro idioma, o tal cual si no hay traducción.

    Devolver el original en vez de fallar es a propósito: un idioma a medias
    se ve raro pero se usa, y `db/pruebas.py` no deja que llegue a estarlo.
    """
    lengua = IDIOMAS.get(idioma)
    if lengua is None or not isinstance(cadena, str):
        return cadena
    return lengua["frases"].get(cadena, cadena)


def respuesta(frase, idioma):
    """Una frase de la caja de preguntas. Devuelve el original si no la hay.

    Son PLANTILLAS de `%`, con los huecos por orden: si una traducción se
    come un `%s` o le cambia el orden, la frase revienta al pintarla o dice
    otra cosa. `db/pruebas.py` compara los huecos uno a uno.
    """
    lengua = IDIOMAS.get(idioma)
    if lengua is None or not isinstance(frase, str):
        return frase
    return lengua["respuestas"].get(frase, frase)


def columna(nombre, idioma):
    """La etiqueta que se pinta encima de una columna.

    Sin traducción se devuelve el nombre de SQL con los guiones bajos
    cambiados por espacios, que es lo que hacía la página antes de que esto
    existiera. Así una columna nueva sale fea pero sale.
    """
    lengua = IDIOMAS.get(idioma)
    if lengua is None:
        return nombre.replace("_", " ")
    return lengua["columnas"].get(nombre, nombre.replace("_", " "))


def doc(vista, col, idioma):
    """Qué quiere decir una columna, para el catálogo. `None` si no se sabe.

    No lo usa el panel: sale en el `VISTAS.md` que escribe `db/catalogo.py`.
    """
    lengua = IDIOMAS.get(idioma)
    if lengua is None:
        return None
    propias = lengua["por_vista"].get(vista) or {}
    # Lo propio de la vista gana a lo común: mismo nombre, otro significado.
    return propias.get(col) or lengua["comunes"].get(col)


def fila_es(vista, idioma):
    """Qué es una fila en esa tabla. `None` si no se sabe."""
    lengua = IDIOMAS.get(idioma)
    return None if lengua is None else lengua["fila_es"].get(vista)
