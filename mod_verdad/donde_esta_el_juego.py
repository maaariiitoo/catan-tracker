# -*- coding: utf-8 -*-
"""Encuentra Catan Universe, este donde este.

Steam permite mover un juego a otro disco desde el propio programa, y
entonces la carpeta cambia de sitio. Tener la ruta escrita a mano en los
scripts significa que el dia que Mario mueva el juego, todo esto deja de
funcionar sin decir por que.

Se busca como lo hace Steam: en `libraryfolders.vdf` estan todas las
bibliotecas (una por disco), y dentro de cada una, el fichero
`appmanifest_544730.acf` dice en que carpeta esta instalado el juego.
"""
import os
import re

APPID = "544730"  # Catan Universe en Steam

_POSIBLES_STEAM = [
    r"C:\Program Files (x86)\Steam",
    r"C:\Program Files\Steam",
    os.path.expandvars(r"%ProgramFiles(x86)%\Steam"),
    os.path.expandvars(r"%ProgramFiles%\Steam"),
]


def _raiz_de_steam():
    try:
        import winreg
        for vista in (winreg.KEY_WOW64_32KEY, winreg.KEY_WOW64_64KEY):
            try:
                k = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Valve\Steam",
                                   0, winreg.KEY_READ | vista)
                ruta, _ = winreg.QueryValueEx(k, "InstallPath")
                if os.path.isdir(ruta):
                    return ruta
            except OSError:
                pass
    except ImportError:
        pass
    for p in _POSIBLES_STEAM:
        if os.path.isdir(p):
            return p
    return None


def _bibliotecas(raiz):
    """Todas las carpetas steamapps que conoce Steam, en todos los discos."""
    salida = []
    if not raiz:
        return salida
    principal = os.path.join(raiz, "steamapps")
    if os.path.isdir(principal):
        salida.append(principal)
    vdf = os.path.join(principal, "libraryfolders.vdf")
    if os.path.isfile(vdf):
        try:
            texto = open(vdf, encoding="utf-8", errors="replace").read()
        except OSError:
            texto = ""
        # el .vdf lleva lineas del estilo:   "path"   "H:\\SteamLibrary"
        for ruta in re.findall(r'"path"\s+"([^"]+)"', texto):
            ruta = ruta.replace("\\\\", "\\")
            carpeta = os.path.join(ruta, "steamapps")
            if os.path.isdir(carpeta) and carpeta not in salida:
                salida.append(carpeta)
    return salida


def carpeta_del_juego():
    """Ruta de Catan Universe, o None si no se encuentra."""
    for steamapps in _bibliotecas(_raiz_de_steam()):
        acf = os.path.join(steamapps, "appmanifest_%s.acf" % APPID)
        if not os.path.isfile(acf):
            continue
        try:
            texto = open(acf, encoding="utf-8", errors="replace").read()
        except OSError:
            continue
        m = re.search(r'"installdir"\s+"([^"]+)"', texto)
        if not m:
            continue
        ruta = os.path.join(steamapps, "common", m.group(1))
        if os.path.isdir(ruta):
            return ruta
    # ultimo recurso: buscar la carpeta a mano en las bibliotecas conocidas
    for steamapps in _bibliotecas(_raiz_de_steam()):
        ruta = os.path.join(steamapps, "common", "Catan Universe")
        if os.path.isdir(ruta):
            return ruta
    return None


def carpeta_de_verdad():
    """Donde escribe el mod sus anotaciones."""
    juego = carpeta_del_juego()
    return os.path.join(juego, "verdad_catan") if juego else None


if __name__ == "__main__":
    j = carpeta_del_juego()
    print("Catan Universe:", j or "NO ENCONTRADO")
    if j:
        for f in ("winhttp.dll", "doorstop_config.ini",
                  r"BepInEx\plugins\CatanVerdad.dll"):
            print("   %s %s" % ("SI " if os.path.exists(os.path.join(j, f)) else "no ", f))
