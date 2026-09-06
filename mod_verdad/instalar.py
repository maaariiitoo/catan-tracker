# -*- coding: utf-8 -*-
"""Deja el mod listo para usar, de una sola vez.

Antes de esto, el camino real de alguien que se bajara el repositorio era:
instalar las dependencias de Python, ir a la web de BepInEx, elegir el
paquete bueno de entre seis, saber si su juego es de 32 o de 64 bits,
descomprimirlo en la carpeta correcta de Steam, y sólo entonces compilar el
plugin. Seis pasos, y el tercero se falla siempre: Catan Universe es de
**32 bits** aunque el ordenador sea de 64, así que el paquete que uno coge
por instinto es el que no vale.

Esto lo hace entero:

  1. las dependencias de Python
  2. encuentra Catan Universe preguntándoselo a Steam
  3. mira si el juego es de 32 o de 64 bits y **descarga el BepInEx que toca**
  4. lo verifica por SHA-256 antes de tocar nada
  5. lo descomprime en la carpeta del juego
  6. compila el plugin contra las librerías del juego
  7. **lo deja apagado**

El paso 7 no es un descuido. El mod modifica el cliente, y las condiciones
de uso de Catan Universe no lo permiten: instalarlo y encenderlo son dos
decisiones distintas, y ésta sólo toma la primera.

Uso:
    py mod_verdad/instalar.py          # o doble clic en instalar.bat
    py mod_verdad/instalar.py --ver    # dice qué falta, sin tocar nada
"""
import argparse
import hashlib
import io
import os
import re
import shutil
import subprocess
import sys
import zipfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from mod_verdad.donde_esta_el_juego import carpeta_del_juego
import idiomas  # noqa: E402

AQUI = os.path.dirname(os.path.abspath(__file__))
RAIZ = os.path.dirname(AQUI)

# BepInEx, clavado a una versión concreta y con su huella.
#
# Clavado porque un instalador que se baje «la última» se rompe solo el día
# que salga otra, y quien lo sufra no va a saber por qué. Y con la huella
# porque esto descarga un binario de terceros y lo mete en la carpeta del
# juego: comprobar que es exactamente el que se probó cuesta tres líneas.
#
# Es la misma versión que se usó para medir todo lo que dice el README.
BEPINEX = "5.4.23.2"
DESCARGA = ("https://github.com/BepInEx/BepInEx/releases/download/v%s/%s")
PAQUETES = {
    "x86": ("BepInEx_win_x86_5.4.23.2.zip",
            "7dd51193587a86c11a58530aeeb4789b15763cc6cf2c55e71785cef4ef214253"),
    "x64": ("BepInEx_win_x64_5.4.23.2.zip",
            "f752ce4e838f4c305b9da1404b6745f2cff23b8bfd494f79f0c84d0a01f59b46"),
}


def _t(frase):
    """Una línea de salida, en el idioma que le haya dicho el panel.

    Se envuelve la PLANTILLA y no la frase montada: para cuando está
    montada lleva dentro rutas y números, y buscarla en el diccionario no
    la encontraría nunca.
    """
    return idiomas.consola(frase)


def _di(texto=""):
    print(texto)
    sys.stdout.flush()


def arquitectura(juego):
    """32 o 64 bits, mirando lo que hay en la carpeta del juego.

    Catan Universe es de 32 bits, y ésa es la trampa: en un Windows de 64
    cualquiera coge el paquete x64, el juego arranca igual y el mod no carga
    nunca -- sin un solo error, que es lo peor que puede pasar. Se mira el
    ejecutable del gestor de fallos de Unity, que lleva el número en el
    nombre, y si no está se mira el tamaño de puntero del propio .exe."""
    if os.path.isfile(os.path.join(juego, "UnityCrashHandler32.exe")):
        return "x86"
    if os.path.isfile(os.path.join(juego, "UnityCrashHandler64.exe")):
        return "x64"
    exe = os.path.join(juego, "CatanUniverse.exe")
    if os.path.isfile(exe):
        with open(exe, "rb") as f:
            cabecera = f.read(1024)
        # firma PE: 'PE\0\0' y luego la maquina (0x014c = 32 bits)
        i = cabecera.find(b"PE\0\0")
        if i > 0 and len(cabecera) > i + 6:
            return "x86" if cabecera[i + 4:i + 6] == b"\x4c\x01" else "x64"
    return "x86"


def ya_esta(juego):
    """(bepinex, plugin) -- qué hay puesto ya."""
    hay_bep = os.path.isfile(os.path.join(juego, "winhttp.dll")) and \
        os.path.isfile(os.path.join(juego, "BepInEx", "core", "BepInEx.dll"))
    hay_plug = os.path.isfile(os.path.join(juego, "BepInEx", "plugins",
                                           "CatanVerdad.dll"))
    return hay_bep, hay_plug


def dependencias():
    """Las de `requirements.txt`, si es que hay alguna.

    NUNCA tumba la instalacion, y por eso esta escrita asi. Lo unico que se
    instalaria aqui es de la mitad de vision, que hoy no se publica: el mod,
    el importador y el panel van con la biblioteca estandar. Antes devolvia
    False cuando `pip` fallaba y `main` cortaba ahi, asi que un ordenador
    sin red, detras de un proxy o sin pip se quedaba sin BepInEx y sin
    plugin por unas librerias que su mitad ni toca.

    Y con el requirements.txt de hoy, que es todo comentarios, ni siquiera
    hay nada que pedir. Se dice y se sigue, en vez de anunciar cuatro que
    faltan y decir despues que se han instalado, que era mentira: pip
    devuelve 0 sin hacer nada cuando el fichero no pide nada.
    """
    req = os.path.join(RAIZ, "requirements.txt")
    pedidas = []
    if os.path.isfile(req):
        with io.open(req, encoding="utf-8", errors="replace") as f:
            pedidas = [l.strip() for l in f
                       if l.strip() and not l.strip().startswith("#")]
    if not pedidas:
        return True, _t("ninguna: esto va con la biblioteca estandar")
    faltan = []
    for modulo, nombre in (("cv2", "opencv-python"), ("numpy", "numpy"),
                           ("PIL", "pillow"), ("mss", "mss")):
        try:
            __import__(modulo)
        except ImportError:
            faltan.append(nombre)
    if not faltan:
        return True, _t("ya estan")
    _di(_t("   faltan: %s") % ", ".join(faltan))
    r = subprocess.run([sys.executable, "-m", "pip", "install", "-r", req])
    return True, ("instaladas" if r.returncode == 0
                  else "pip ha fallado, y se sigue igual: eso es de la mitad"
                       " de vision y el mod no lo necesita")


def bajar_bepinex(juego, arq):
    nombre, huella = PAQUETES[arq]
    _di(_t("   bajando %s ...") % nombre)
    import urllib.request
    with urllib.request.urlopen(DESCARGA % (BEPINEX, nombre), timeout=180) as r:
        datos = r.read()
    suya = hashlib.sha256(datos).hexdigest()
    if suya != huella:
        return False, ("la descarga NO cuadra con la huella conocida.\n"
                       "        esperaba %s\n        ha venido %s\n"
                       "        No se toca nada." % (huella, suya))
    z = zipfile.ZipFile(io.BytesIO(datos))
    dentro = z.namelist()
    if "winhttp.dll" not in dentro:
        return False, _t("el paquete no trae winhttp.dll; no se toca nada")
    z.extractall(juego)
    # BepInEx viene ENCENDIDO de fabrica (`enabled = true`). Descomprimirlo y
    # ya esta dejaria el mod cargandose en la siguiente partida sin que nadie
    # lo haya decidido -- justo lo contrario de lo que promete este fichero, y
    # de lo unico que sujeta la parte de las condiciones de uso. Se apaga
    # aqui, antes de decir que esta puesto.
    apagar(juego)
    return True, _t("puesto en %s, y APAGADO") % juego


def apagar(juego):
    """`enabled = false` en doorstop_config.ini. Idempotente."""
    cfg = os.path.join(juego, "doorstop_config.ini")
    if not os.path.isfile(cfg):
        return False
    with io.open(cfg, encoding="utf-8", errors="replace") as f:
        texto = f.read()
    # Se conserva el `enabled = ` y solo se cambia el valor. La primera
    # version se comio el grupo y dejaba la linea en un `false` suelto:
    # el fichero seguia teniendo buena pinta, BepInEx no encontraba la
    # clave y se quedaba con su valor por defecto, que es ENCENDIDO. O
    # sea, exactamente lo contrario de lo que este metodo promete.
    nuevo = re.sub(r"(?mi)^(\s*enabled\s*=\s*)true", r"\g<1>false", texto)
    if nuevo != texto:
        with io.open(cfg, "w", encoding="utf-8", newline="") as f:
            f.write(nuevo)
    return True


def compilar():
    ps1 = os.path.join(AQUI, "compilar.ps1")
    r = subprocess.run(["powershell", "-ExecutionPolicy", "Bypass",
                        "-File", ps1, "-python", sys.executable],
                       capture_output=True, text=True)
    salida = (r.stdout or "") + (r.stderr or "")
    return r.returncode == 0 and "compilado" in salida, salida.strip()


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--ver", action="store_true",
                    help="di que falta, sin tocar nada")
    args = ap.parse_args()

    _di(_t("Dejar el mod listo"))
    _di("=" * 52)

    _di()
    _di(_t("1. Catan Universe"))
    juego = carpeta_del_juego()
    if not juego:
        _di(_t("   NO LO ENCUENTRO. Se le pregunta a Steam, asi que:"))
        _di(_t("   abre Steam una vez, o instala el juego, y vuelve a pasar esto."))
        return 1
    arq = arquitectura(juego)
    _di(_t("   %s") % juego)
    _di(_t("   es de %s") % (_t("32 bits") if arq == "x86" else _t("64 bits")))

    hay_bep, hay_plug = ya_esta(juego)
    if args.ver:
        _di()
        _di(_t("2. BepInEx          %s") % (_t("ya esta") if hay_bep else _t("FALTA")))
        _di(_t("3. el plugin        %s") % (_t("ya esta") if hay_plug else _t("FALTA")))
        _di()
        _di(_t("Nada tocado (--ver). Pasa esto sin --ver para dejarlo listo."))
        return 0

    _di()
    _di(_t("2. Dependencias de Python"))
    ok, detalle = dependencias()
    _di(_t("   %s") % detalle)

    _di()
    _di(_t("3. BepInEx %s") % BEPINEX)
    if hay_bep:
        _di(_t("   ya esta puesto, no se toca"))
    else:
        ok, detalle = bajar_bepinex(juego, arq)
        _di(_t("   %s") % detalle)
        if not ok:
            return 1

    _di()
    _di(_t("4. El plugin"))
    ok, detalle = compilar()
    for linea in detalle.splitlines():
        _di(_t("   %s") % linea)
    if not ok:
        _di(_t("   No ha compilado. Hace falta el csc que trae Windows, en"))
        _di(_t("   C:\\Windows\\Microsoft.NET\\Framework\\v4.0.30319\\csc.exe"))
        return 1

    _di()
    _di("=" * 52)
    _di(_t("Listo, y APAGADO."))
    _di()
    _di(_t("El mod modifica el cliente del juego, y las condiciones de uso de"))
    _di(_t("Catan Universe no lo permiten. Instalarlo y encenderlo son dos"))
    _di(_t("decisiones distintas, y esto solo ha tomado la primera. Lee el"))
    _di(_t("apartado del README antes de encenderlo."))
    _di()
    _di(_t("Cuando quieras:"))
    _di(_t("   py panel.py                        y el boton «Encender el mod»"))
    _di(_t("o a mano:"))
    _di(_t("   .\\mod_verdad\\interruptor.ps1 on        y DESPUES abrir Catan"))
    _di(_t("   ... jugar ..."))
    _di(_t("   .\\mod_verdad\\interruptor.ps1 off"))
    _di(_t("   py mod_verdad\\importar.py"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
