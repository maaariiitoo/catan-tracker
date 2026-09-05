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

ORIGINAL = "es"
NOMBRE_ORIGINAL = "Castellano"
BOTON_ORIGINAL = "ES  Castellano"
DECIMAL_ORIGINAL = ","


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
    """Los idiomas en el orden en que los recorre el botón, el original el
    primero. Cada uno con el texto del botón que TRAE a él."""
    vuelta = [{"id": ORIGINAL, "nombre": NOMBRE_ORIGINAL,
               "boton": BOTON_ORIGINAL}]
    for clave in sorted(IDIOMAS):
        vuelta.append({"id": clave, "nombre": IDIOMAS[clave]["nombre"],
                       "boton": IDIOMAS[clave]["boton"]})
    return vuelta


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
