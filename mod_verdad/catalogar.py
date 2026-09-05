# -*- coding: utf-8 -*-
"""Saca del juego la lista COMPLETA de lo que puede pasar, y la guarda.

Por qué existe. Durante un tiempo el razonamiento fue «una partida sólo
enseña el 82% de las acciones, así que no se puede prever el 100%», y eso
mezclaba dos cosas que no son la misma:

  - QUÉ EXISTE          se sabe hoy, entero, leyendo el ensamblado del juego
  - QUÉ TRAE DENTRO     no se sabe hasta jugar

Lo segundo es donde han estado todos los fallos de este proyecto: el puerto
que se leía de `HarborType` cuando el bueno era `HarborTypeValue`; el ladrón
que estaba en `GamePiecesRobbers` y no en `GamePiecesRobber` -- el campo
existía y venía `null`. Que un nombre exista no dice qué lleva.

Pero lo PRIMERO no hay por qué adivinarlo, y adivinarlo era el error. Catan
Universe trae dentro las 433 acciones de todas sus expansiones, los 63
accesores de `CatanGameActionState` y las 31 colecciones de `BoardState`.
Están ahí, con su nombre y su tipo, se juegue o no se juegue a ellas.

Esto las lee en modo SOLO REFLEXIÓN -- los metadatos, sin ejecutar una línea
del juego ni cargar Unity -- y las deja en `catalogo.json`, que va al repo.
Así el resto del proyecto sabe qué existe aunque la máquina no tenga el
juego instalado, que es la mitad del sentido de esto.

Uso:
    py mod_verdad/catalogar.py            # lo rehace
    py mod_verdad/catalogar.py --ver      # lo enseña, sin tocarlo

Hay que volver a pasarlo cuando el juego se actualice. Si el catálogo se
queda viejo no se rompe nada: lo que aparezca y no esté saldrá como
desconocido, que es el comportamiento correcto.
"""
import argparse
import json
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

AQUI = os.path.dirname(os.path.abspath(__file__))
CATALOGO = os.path.join(AQUI, "catalogo.json")

# De qué es cada familia de acciones. El prefijo es del juego; el nombre, el
# de la caja. `Rivals*` es *Rivals for Catan*, el juego de cartas para dos:
# comparte ejecutable y no comparte nada más -- no tiene tablero.
FAMILIAS = {
    "CatanBase": "Catan, el basico",
    "CatanTrade": "Catan, el basico (comercio)",
    "CatanCak": "Ciudades y Caballeros",
    "CatanCakSf": "Ciudades y Caballeros + Navegantes",
    "CatanSeafarer": "Navegantes",
    "CatanInka": "El ascenso de los incas",
    "CatanEnchantedLand": "Tierra Encantada",
    "CatanGreatCanal": "El Gran Canal",
    "CatanBigGame": "El modo multitudinario",
    "CatanSpecialScenario": "Escenarios sueltos",
    "CatanTest": "Pruebas del juego",
}


def _dll():
    from mod_verdad.donde_esta_el_juego import carpeta_del_juego
    juego = carpeta_del_juego()
    if not juego:
        return None
    ruta = os.path.join(juego, "CatanUniverse_Data", "Managed",
                        "Assembly-CSharp.dll")
    return ruta if os.path.isfile(ruta) else None


def _acciones(datos):
    """Las acciones, por su nombre, sacadas del heap de cadenas.

    Los nombres de tipos de un ensamblado .NET viven como cadenas UTF-8
    dentro del fichero, así que para ESTO no hace falta ni reflexión: basta
    buscarlas. Se hace aparte de lo demás porque no depende de poder cargar
    el ensamblado, y así el catálogo sale aunque la reflexión falle."""
    import re
    # El `(?!State)` no es cosmético. Sin él, `Trade_Finish_GameActionState`
    # --que es la clase del PAYLOAD, no una acción-- entraba como si fuera una
    # acción llamada `Trade_Finish_GameAction`, que no existe. Salían cinco
    # familias inventadas (`Base`, `Trade`, `Seafarer`, `Shuffle`, `Using`) y
    # el catálogo habría hecho creer que hay acciones que no hay.
    fuera = set()
    for m in re.finditer(rb"[\x20-\x7e]{6,160}", datos):
        s = m.group().decode("ascii")
        for a, b in re.findall(
                r"([A-Za-z]+)_([A-Za-z0-9_]+)_GameAction(?![A-Za-z])", s):
            fuera.add(a + "_" + b + "_GameAction")
    return sorted(fuera)


def _por_reflexion(ruta):
    """Los accesores de la acción y las colecciones del tablero.

    Esto sí necesita reflexión, porque hacen falta los TIPOS y la relación
    campo-clase, y eso no está en el heap de cadenas. Se hace con un .exe de
    usar y tirar compilado con el csc que trae Windows -- el mismo truco con
    el que se encontró dónde estaba el ladrón."""
    exe = os.path.join(AQUI, "_mirar.exe")
    fuente = os.path.join(AQUI, "_mirar.cs")
    if not os.path.isfile(exe):
        with open(fuente, "w") as f:
            f.write(_FUENTE_MIRAR)
        csc = r"C:\Windows\Microsoft.NET\Framework\v4.0.30319\csc.exe"
        if not os.path.isfile(csc):
            return None
        r = subprocess.run([csc, "-nologo", "-out:" + exe, fuente],
                           capture_output=True, text=True)
        if r.returncode != 0:
            return None
    r = subprocess.run([exe, ruta], capture_output=True, text=True)
    if r.returncode != 0:
        return None
    fuera = {"accion": [], "tablero": []}
    for linea in r.stdout.splitlines():
        if linea.startswith("accion\t"):
            _q, n, t = linea.split("\t", 2)
            fuera["accion"].append({"campo": n, "tipo": t})
        elif linea.startswith("tablero\t"):
            _q, n, t = linea.split("\t", 2)
            fuera["tablero"].append({"campo": n, "tipo": t})
    return fuera


_FUENTE_MIRAR = r'''
using System;
using System.Reflection;
class Mirar {
  static void Uno(Assembly a, string tipo, string etiqueta) {
    Type t = a.GetType(tipo);
    if (t == null) return;
    BindingFlags C = BindingFlags.Public | BindingFlags.NonPublic
                   | BindingFlags.Instance | BindingFlags.DeclaredOnly;
    while (t != null) {
      FieldInfo[] fs;
      try { fs = t.GetFields(C); } catch { break; }
      for (int i = 0; i < fs.Length; i++) {
        string tn = "?";
        try { tn = fs[i].FieldType.FullName; } catch { }
        Console.WriteLine(etiqueta + "\t" + fs[i].Name + "\t" + tn);
      }
      try { t = t.BaseType; } catch { break; }
      if (t != null && t.FullName == "System.Object") break;
    }
  }
  static void Main(string[] args) {
    Assembly a = Assembly.ReflectionOnlyLoadFrom(args[0]);
    Uno(a, "Catan.GameLogic.Model.CatanGameActionState", "accion");
    Uno(a, "Catan.GameLogic.Model.BoardState", "tablero");
  }
}
'''


def familia_de(accion):
    """A qué expansión pertenece una acción, por su prefijo."""
    pref = accion.split("_", 1)[0]
    if pref.startswith("Rivals"):
        return "Rivals for Catan (el juego de cartas)"
    return FAMILIAS.get(pref, pref)


def cargar():
    """El catálogo guardado, o None si no está."""
    if not os.path.isfile(CATALOGO):
        return None
    with open(CATALOGO, encoding="utf-8") as f:
        return json.load(f)


def rehacer():
    ruta = _dll()
    if ruta is None:
        return None, "no encuentro Assembly-CSharp.dll (¿está Catan instalado?)"
    datos = open(ruta, "rb").read()
    cat = {"de": os.path.basename(ruta),
           "bytes": len(datos),
           "acciones": _acciones(datos)}
    refl = _por_reflexion(ruta)
    if refl:
        cat["accessores_de_accion"] = refl["accion"]
        cat["colecciones_del_tablero"] = refl["tablero"]
    with open(CATALOGO, "w", encoding="utf-8") as f:
        json.dump(cat, f, ensure_ascii=False, indent=1, sort_keys=True)
    return cat, None


def resumen(cat):
    import collections
    por = collections.Counter(familia_de(a) for a in cat["acciones"])
    fuera = ["Lo que Catan Universe puede hacer, sacado de su ensamblado",
             "",
             "   %d acciones de juego" % len(cat["acciones"])]
    for f, n in por.most_common():
        fuera.append("      %-42s %3d" % (f, n))
    if cat.get("accessores_de_accion"):
        fuera.append("")
        fuera.append("   %d accesores en CatanGameActionState"
                     % len(cat["accessores_de_accion"]))
    if cat.get("colecciones_del_tablero"):
        fuera.append("   %d campos en BoardState"
                     % len(cat["colecciones_del_tablero"]))
    return "\n".join(fuera)


def cobertura(cat):
    """Cuánto del catálogo entiende hoy el importador, expansión por expansión.

    Es la tabla que contesta «¿qué pasaría si me compro X?» sin comprar X.
    No mide si lo haría BIEN -- eso no se sabe hasta jugar -- sino cuánto
    reconocería siquiera."""
    import collections
    import inspect
    import re
    from mod_verdad import importar as _imp

    fuente = inspect.getsource(_imp)
    finales = set(re.findall(r'accion\.endswith\("([A-Za-z_]+)"\)', fuente))

    def estado(a):
        if a in _imp._REPARTOS_DE_VERDAD or any(a.endswith(f) for f in finales):
            return "la usa"
        if a in _imp._YA_SE_QUE_ESTAN:
            return "la ve y no le hace falta"
        return "no la conoce"

    por = collections.defaultdict(collections.Counter)
    ejemplos = collections.defaultdict(list)
    for a in cat["acciones"]:
        f = familia_de(a)
        e = estado(a)
        por[f][e] += 1
        if e == "no la conoce" and len(ejemplos[f]) < 3:
            ejemplos[f].append(a)

    fuera = ["Qué entendería el importador de cada expansión", ""]
    orden = sorted(por, key=lambda f: -sum(por[f].values()))
    fuera.append("   %-42s %5s %5s %5s" % ("", "usa", "ve", "nueva"))
    for f in orden:
        c = por[f]
        fuera.append("   %-42s %5d %5d %5d"
                     % (f, c["la usa"], c["la ve y no le hace falta"],
                        c["no la conoce"]))
    fuera.append("")
    fuera.append("   usa   = deja una fila en la base")
    fuera.append("   ve    = la conoce y hoy no aporta nada (barajar, repartir…)")
    fuera.append("   nueva = no la ha visto nunca; saltaría como desconocida y")
    fuera.append("           quedaría apuntada en `pegas`, con la grabación entera")
    fuera.append("           guardada para meterla luego con --rehacer")
    return "\n".join(fuera)


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--ver", action="store_true", help="enséñalo, no lo rehagas")
    ap.add_argument("--cobertura", action="store_true",
                    help="qué entendería el importador de cada expansión")
    args = ap.parse_args()
    if args.cobertura:
        cat = cargar()
        if cat is None:
            print("no hay catálogo. Pásalo sin argumentos para hacerlo.")
            return 1
        print(cobertura(cat))
        return 0
    if args.ver:
        cat = cargar()
        if cat is None:
            print("no hay catálogo. Pásalo sin --ver para hacerlo.")
            return 1
        print(resumen(cat))
        return 0
    cat, fallo = rehacer()
    if fallo:
        print(fallo)
        return 1
    print(resumen(cat))
    print()
    print("guardado en %s" % CATALOGO)
    return 0


if __name__ == "__main__":
    sys.exit(main())
