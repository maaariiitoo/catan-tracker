# -*- coding: utf-8 -*-
"""Escribe `VISTAS.md`: las vistas de la base y qué quiere decir cada columna.

    py db/catalogo.py              lo escribe
    py db/catalogo.py --ver        lo saca por pantalla, sin tocar nada
    py db/catalogo.py --comprobar  ¿está al día? (0 sí, 1 no)

NO SE ESCRIBE A MANO, Y POR ESO NO PUEDE ESTAR MAL. Los nombres, los títulos
y qué contesta cada vista salen de `db/vistas.py`; las columnas, de la base;
el texto de cada columna, de `db/columnas.py`. Cambiar una vista y olvidarse
del fichero no es posible: `db/pruebas.py` lo vuelve a generar y lo compara.

CONTRA UNA BASE VACÍA, a propósito. Las columnas se sacan creando las vistas
en una base en memoria con el esquema y ni una fila. Dos motivos:

  - Este fichero se publica. Una fila de ejemplo llevaría dentro los nombres
    de con quien juego y sus partidas, y el repositorio no trae datos de
    nadie.
  - Así el fichero sale igual en cualquier ordenador. Si dependiera de las
    partidas que hay, cambiaría al jugar y la prueba de que está al día
    fallaría sin que nadie haya tocado nada.
"""
import argparse
import io
import os
import sqlite3
import sys

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RAIZ)

from db import columnas as C          # noqa: E402
from db import vistas as V            # noqa: E402
from mod_verdad.importar import crear_tablas   # noqa: E402

DESTINO = os.path.join(RAIZ, "VISTAS.md")


MUESTRA = 4        # filas de ejemplo que se enseñan de cada vista
ANCHO = 8          # columnas que caben antes de que la tabla no se lea

# Lo de arriba del fichero. Va en capas a propósito: quien juega al Catan se
# salta las dos primeras y va al índice; quien no ha jugado nunca -- que es
# medio LinkedIn -- necesita las diez líneas de reglas o no entiende por qué
# «el ladrón» es una tabla. Lo que no se puede hacer es explicar el juego
# dentro de cada vista: son casi treinta y quedaría insoportable para el que
# sí juega.
#
# El número de tablas se pone solo (`{cuantas}`). Estaba escrito a mano, y el
# día que apareció la vista número 29 el fichero siguió diciendo 28 sin que
# nada avisara, que es justo lo que este fichero existe para evitar.
ENTRADA = """# Las vistas, una a una

Las {cuantas} tablas que salen de tus partidas, qué contesta cada una y qué
quiere decir cada columna.

Se miran desde el panel (**Mirar los datos**) o desde la consola:

```powershell
py sql.py "SELECT * FROM amigos_marcador"
```

> Este fichero **no está escrito a mano**: lo genera `py db/catalogo.py`, y
> hay una prueba que comprueba que está al día. Los ejemplos también se
> generan, y son las vistas de verdad ejecutadas sobre una partida inventada
> de cuatro jugadores (Ana, Bruno, Carla y Dani), así que los números no los
> ha puesto nadie a mano y no traen datos de nadie.

---

## Si no has jugado nunca al Catan

Diez líneas y ya se puede leer todo lo demás. Si juegas, sáltatelo.

Se juega en un tablero de 19 casillas hexagonales. Cada casilla da un
**material** (madera, arcilla, lana, cereales o mineral) y lleva un número
del 2 al 12.

En tu turno tiras dos dados. **Todo el que tenga un poblado tocando una
casilla con ese número cobra** una carta de ese material; si en vez de un
poblado tiene una ciudad, cobra dos. Con los materiales se construyen más
poblados, ciudades y carreteras, y cada cosa da puntos. Gana el primero que
llega a 10.

También se pueden **cambiar cartas** con los demás o con la banca, y comprar
**cartas de desarrollo**: la mayoría son caballeros, y las demás hacen cosas
sueltas: el *monopolio*, por ejemplo, te da todas las cartas de un material
que tenga la mesa.

Y está **el ladrón**. Quien saca un 7 (o juega un caballero) mueve una ficha
sobre una casilla: mientras esté ahí, **esa casilla no paga a nadie**, y
además le robas una carta al azar a alguien que tenga algo pegado. Es lo que
más discusiones da, y por eso tiene cuatro tablas para él solo.

---

## Cómo se lee una tabla de éstas

Tres cosas, y con eso valen las 28:

**1. Saber qué es una fila.** Es lo único que no se adivina mirando, así que
cada vista lo dice en negrita antes de nada. En «El ladrón» una fila es una
persona; en «El ladrón, uno a uno» es una **pareja** de personas; en «Las
tiradas» es un **número** del 2 al 12. Con las mismas columnas delante, las
tres se leen distinto.

**2. Todo se puede pedir de una partida suelta.** En el panel hay un
desplegable. Es el mismo SQL con el filtro cambiado, así que el total y una
partida no pueden decir cosas distintas: no son dos consultas, es una.

**3. Un guion (—) es que ahí no hay dato**, no un cero. «No compró ninguna
carta» y «no se sabe qué carta era» son cosas distintas y se ven distintas.

---
"""
ENTRADA = ENTRADA.format(cuantas=len(V.VISTAS)).split("\n")


def columnas_de_cada_vista():
    """Las columnas que devuelve cada vista, en su orden, sin datos."""
    conn = sqlite3.connect(":memory:")
    try:
        crear_tablas(conn)
        V.crear(conn)
        salida = {}
        for v in V.VISTAS:
            cur = conn.execute("SELECT * FROM %s LIMIT 0" % v["nombre"])
            salida[v["nombre"]] = [d[0] for d in cur.description]
        return salida
    finally:
        conn.close()


def _tabla(pares):
    filas = ["| columna | qué es |", "|---|---|"]
    filas += ["| `%s` | %s |" % (c, t) for c, t in pares]
    return filas


def _celda(valor):
    if valor is None:
        return "—"
    if isinstance(valor, float):
        # 2.0 se lee peor que 2, y 2.44 hay que dejarlo como está.
        return ("%g" % valor).replace(".", ",")
    return str(valor)


def _ejemplo(cols, filas):
    """Las primeras filas de una vista, tal cual las devuelve.

    Cortada a lo ancho si hace falta: una tabla de doce columnas en markdown
    no se lee, se sufre. Las que se quedan fuera igualmente están explicadas
    justo debajo, que es lo que importa."""
    visibles = cols[:ANCHO]
    l = ["| " + " | ".join(visibles) + " |",
         "|" + "|".join(["---"] * len(visibles)) + "|"]
    for f in filas[:MUESTRA]:
        l.append("| " + " | ".join(_celda(v) for v in f[:ANCHO]) + " |")
    if len(cols) > ANCHO:
        l.append("")
        l.append("*(y %d columnas más, que no caben a lo ancho: %s)*"
                 % (len(cols) - ANCHO,
                    ", ".join("`%s`" % c for c in cols[ANCHO:])))
    if len(filas) > MUESTRA:
        l.append("")
        l.append("*(y %d filas más)*" % (len(filas) - MUESTRA))
    return l


def ejemplos_de_cada_vista():
    """Las primeras filas de cada vista sobre la partida inventada.

    Se ejecutan las vistas DE VERDAD sobre una base de mentira, así que los
    números del ejemplo no los escribe nadie: los calcula el mismo SQL que
    contesta cuando miras tus partidas. Cambiar una vista cambia el ejemplo
    solo, y no puede quedarse diciendo algo que ya no es."""
    from db import muestra
    conn = muestra.construir()
    try:
        salida = {}
        for v in V.VISTAS:
            _cols, filas = V.consultar(conn, v["nombre"])
            salida[v["nombre"]] = filas
        return salida
    finally:
        conn.close()


def texto():
    cols = columnas_de_cada_vista()
    ejemplos = ejemplos_de_cada_vista()
    grupos = list(V.GRUPOS) + [(V.SIN_GRUPO, tuple(
        v["nombre"] for v in V.VISTAS
        if not V.grupo_de(v["nombre"])))]
    grupos = [(t, ns) for t, ns in grupos if ns]

    l = list(ENTRADA)
    l.append("## Qué hay")
    l.append("")
    for titulo, nombres in grupos:
        l.append("**%s**" % titulo)
        l.append("")
        l.append("| vista | qué contesta |")
        l.append("|---|---|")
        for n in nombres:
            v = V.POR_NOMBRE[n]
            l.append("| [`%s`](#%s) | %s |"
                     % (n, _ancla(_encabezado(n)), v["que"]))
        l.append("")
    l.append("---")
    l.append("")
    l.append("## Las columnas que salen en varias vistas")
    l.append("")
    l.append("Quieren decir lo mismo en todas, así que se explican una vez.")
    l.append("")
    l += _tabla(sorted(C.COMUNES.items()))
    l.append("")
    l.append("---")
    l.append("")

    faltan = []
    for titulo, nombres in grupos:
        l.append("## %s" % titulo)
        l.append("")
        for n in nombres:
            v = V.POR_NOMBRE[n]
            propias = C.POR_VISTA.get(n, {})
            l.append("### %s" % _encabezado(n))
            l.append("")
            l.append("**Una fila por %s.** %s%s."
                     % (C.FILA_ES[n]["fila"],
                        C.FILA_ES[n]["para"][0].upper(),
                        C.FILA_ES[n]["para"][1:]))
            l.append("")
            l += _ejemplo(cols[n], ejemplos[n])
            l.append("")
            mias, comunes = [], []
            for c in cols[n]:
                if c in propias:
                    mias.append((c, propias[c]))
                elif c in C.COMUNES:
                    comunes.append(c)
                else:
                    faltan.append("%s.%s" % (n, c))
            if mias:
                l += _tabla(mias)
                l.append("")
            if comunes:
                l.append("Y las de siempre: %s."
                         % ", ".join("`%s`" % c for c in comunes))
                l.append("")
    return "\n".join(l).rstrip("\n") + "\n", faltan


def _ancla(encabezado):
    """El ancla que GitHub le pone a un encabezado.

    Su regla: a minusculas, fuera todo lo que no sea letra, numero, guion o
    espacio -- las comillas y la raya se van -- y los espacios a guiones. Se
    copia aqui en vez de inventarse un ancla porque un enlace del indice que
    no lleva a ningun sitio es de las cosas que nadie prueba y todos ven.
    Hay una prueba que comprueba que cada enlace cae en un encabezado."""
    limpio = "".join(c for c in encabezado.lower()
                     if c.isalnum() or c in " -_")
    return limpio.replace(" ", "-")


def _encabezado(nombre):
    return "`%s`: %s" % (nombre, V.POR_NOMBRE[nombre]["titulo"])


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--ver", action="store_true", help="sacarlo por pantalla")
    ap.add_argument("--comprobar", action="store_true",
                    help="¿está al día? 0 sí, 1 no")
    args = ap.parse_args()

    nuevo, faltan = texto()
    if faltan:
        print("Sin explicar en db/columnas.py: %s" % ", ".join(faltan))
        return 1
    if args.ver:
        sys.stdout.write(nuevo)
        return 0
    viejo = None
    if os.path.isfile(DESTINO):
        with io.open(DESTINO, encoding="utf-8") as f:
            viejo = f.read()
    if args.comprobar:
        if viejo == nuevo:
            print("VISTAS.md esta al dia.")
            return 0
        print("VISTAS.md NO esta al dia. Vuelve a lanzar: py db/catalogo.py")
        return 1
    if viejo == nuevo:
        print("VISTAS.md ya estaba al dia.")
        return 0
    with io.open(DESTINO, "w", encoding="utf-8") as f:
        f.write(nuevo)
    print("Escrito %s (%d vistas)." % (DESTINO, len(V.VISTAS)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
