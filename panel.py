# -*- coding: utf-8 -*-
"""Un panel en el navegador para no tener que escribir comandos.

    py panel.py

Abre http://127.0.0.1:8731 y desde ahi se hace todo lo de entrenar la red:
encender el mod, grabar una partida, preparar los datos, medir y entrenar.

Por que un panel local y no una aplicacion de ventanas: esto no ejecuta
nada nuevo, solo lanza los MISMOS comandos de siempre y ensena su salida
tal cual. Si algo falla, se ve el mismo texto que se veria en la consola, y
cualquiera de los pasos se puede seguir haciendo a mano. El panel es una
comodidad, no una capa que tape lo que pasa por debajo.

Tres decisiones que importan:

- **Solo escucha en 127.0.0.1.** Esto enciende un mod y arranca procesos;
  no tiene por que estar accesible desde la red de casa, y menos desde
  fuera.

- **El estado del mod se ensena a gritos.** El interruptor esta escrito para
  que encenderlo sea una decision consciente cada vez: las condiciones de uso
  de Catan Universe prohiben modificar el cliente, y un boton hace demasiado
  facil olvidarse de eso. Asi que el panel compensa: cuando esta encendido,
  la pagina entera lo dice y el titulo de la pestana tambien. Que este
  encendido no se pueda pasar por alto es media garantia.

- **No se reimplementa nada.** El interruptor se enciende y se apaga
  llamando a `interruptor.ps1`, que es donde vive esa logica; los pasos de
  datos son `py -m red.dataset` y compania. Si el panel y la consola
  dijeran cosas distintas, el panel seria una fuente de errores nueva.
"""
import ast
import hashlib
import importlib
import json
import os
import re
import sqlite3
import subprocess
import sys
import threading
import time
import unicodedata
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import unquote

RAIZ = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, RAIZ)

from mod_verdad.donde_esta_el_juego import carpeta_del_juego, carpeta_de_verdad
import idiomas
from db import vistas as _vistas
from db import titulares as _titulares

# El puerto se puede cambiar por variable de entorno para poder levantar un
# panel de prueba sin echar abajo el que este en marcha (que puede llevar
# media hora preparando datos).
PUERTO = int(os.environ.get("CATAN_PANEL_PUERTO") or 8731)
DATOS_GRABADOS = os.path.join(RAIZ, "mod_verdad", "datos")
DATOS_RED = os.path.join(RAIZ, "red", "datos")
# Dos modelos y no uno: el de JUGAR se entrena con todo y el de MEDIR deja
# fuera las dos ultimas partidas, que son las que le hacen el examen. Medir
# el de jugar no diria nada -- se le examinaria de lo que ha estudiado.
MODELO = os.path.join(RAIZ, "red", "modelos", "red_de_sitios.pt")
MODELO_MEDIDO = os.path.join(RAIZ, "red", "modelos", "medido.pt")
REGISTROS = os.path.join(RAIZ, "registros")
CANDADO = os.path.join(DATOS_GRABADOS, ".recopilando")
PARAR = os.path.join(DATOS_GRABADOS, ".parar")
INTERRUPTOR = os.path.join(RAIZ, "mod_verdad", "interruptor.ps1")

# Lo mismo que usa recopilar.py para saber si otro esta trabajando: el
# candado se toca cada 5 s, asi que si lleva mas de esto sin tocarse es que
# el proceso ya no esta.
_PACIENCIA = 20.0


def _entorno_hijo():
    """Para que los hijos escriban en UTF-8 y sin buffer.

    Sin PYTHONIOENCODING, un `print` con acentos por una tuberia revienta o
    sale mal en Windows. Sin PYTHONUNBUFFERED, la salida llega toda de golpe
    al final y el registro del panel se queda vacio mientras algo tarda diez
    minutos, que es justo cuando hace falta verlo."""
    env = dict(os.environ)
    env["PYTHONIOENCODING"] = "utf-8"
    env["PYTHONUNBUFFERED"] = "1"
    return env


class Proceso:
    """Un comando corriendo, con su salida guardada linea a linea.

    Las lineas se numeran para que la pagina pueda pedir "dame de la 340 en
    adelante" en vez de recargar todo el registro cada segundo."""

    def __init__(self):
        self.cerrojo = threading.Lock()
        self.proc = None
        self.nombre = None
        self.lineas = []
        self.primera = 0        # numero de la primera linea que queda guardada
        self.acabado_en = None
        self.codigo = None
        self.tope = 4000        # no crecer sin limite en un entrenamiento largo
        self.fichero = None

    @property
    def vivo(self):
        return self.proc is not None and self.proc.poll() is None

    def arrancar(self, nombre, orden, cwd=RAIZ):
        with self.cerrojo:
            if self.vivo:
                return False, "ya hay algo corriendo: %s" % self.nombre
            self.nombre = nombre
            self.lineas = []
            self.primera = 0
            self.acabado_en = None
            self.codigo = None
            # Cada tarea deja su salida en un fichero. Lo de memoria se borra
            # al empezar la siguiente, y eso costo caro: el informe de un
            # entrenamiento -- que es el unico numero honesto que da este
            # proyecto -- se perdio entero por darle al boton de al lado.
            try:
                os.makedirs(REGISTROS, exist_ok=True)
                self.fichero = open(
                    os.path.join(REGISTROS, "tarea_%s_%s.log" % (
                        re.sub(r"[^a-z0-9]+", "_", nombre.lower()).strip("_"),
                        time.strftime("%Y%m%d_%H%M%S"))),
                    "w", encoding="utf-8")
            except OSError:
                self.fichero = None
            try:
                self.proc = subprocess.Popen(
                    orden, cwd=cwd, stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT, env=_entorno_hijo(),
                    creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
            except OSError as e:
                self.proc = None
                return False, "no se ha podido lanzar: %s" % e
        self.escribir("$ " + " ".join(orden))
        threading.Thread(target=self._leer, daemon=True).start()
        return True, None

    def _leer(self):
        proc = self.proc
        for cruda in iter(proc.stdout.readline, b""):
            self.escribir(cruda.decode("utf-8", "replace").rstrip("\r\n"))
        proc.stdout.close()
        codigo = proc.wait()
        self.codigo = codigo
        self.acabado_en = time.time()
        self.escribir("")
        self.escribir("--- terminado (codigo %d) ---" % codigo)
        with self.cerrojo:
            if self.fichero is not None:
                try:
                    self.fichero.close()
                except Exception:
                    pass
                self.fichero = None

    def escribir(self, texto):
        with self.cerrojo:
            self.lineas.append(texto)
            if len(self.lineas) > self.tope:
                sobran = len(self.lineas) - self.tope
                self.lineas = self.lineas[sobran:]
                self.primera += sobran
            if self.fichero is not None:
                try:
                    self.fichero.write(texto + "\n")
                    self.fichero.flush()
                except Exception:
                    self.fichero = None    # que un fallo de disco no pare nada

    def desde(self, n):
        with self.cerrojo:
            if n < self.primera:
                n = self.primera
            return self.primera + len(self.lineas), self.lineas[n - self.primera:]

    def matar(self):
        with self.cerrojo:
            if self.vivo:
                self.proc.terminate()


# Dos huecos: uno para la grabacion (dura toda la partida) y otro para las
# tareas de datos. Son independientes a proposito -- se puede preparar el
# dataset de una partida anterior mientras se graba otra -- pero de tareas
# solo cabe una, porque dos entrenamientos a la vez se pelearian por la CPU
# y no hay ninguna razon para quererlo.
grabacion = Proceso()
tarea = Proceso()


# --- estado ------------------------------------------------------------

def _mod_encendido(juego):
    """Lee `doorstop_config.ini`. Solo LEER: encender y apagar se hace
    llamando al interruptor, que es donde vive esa decision."""
    if not juego:
        return None
    cfg = os.path.join(juego, "doorstop_config.ini")
    if not os.path.isfile(cfg):
        return None
    try:
        texto = open(cfg, encoding="utf-8", errors="replace").read()
    except OSError:
        return None
    m = re.search(r"(?mi)^\s*enabled\s*=\s*(\w+)", texto)
    return bool(m and m.group(1).lower() == "true")


_EXE = "CatanUniverse.exe"
_cache_juego = {"cuando": 0.0, "abierto": False}


def _juego_abierto():
    """Si Catan esta corriendo ahora mismo.

    Hace falta para un aviso que no es evidente y que importa: el mod se
    inyecta cuando ARRANCA el juego (winhttp.dll + doorstop), asi que
    apagar el interruptor con Catan ya abierto no lo descarga. El proceso
    que hay abierto sigue teniendo el mod dentro hasta que se cierre. Sin
    decirlo, "apagado" en el panel se lee como "ya no esta cargado", y no es
    verdad: lo esta hasta que cierres el juego.

    Se pregunta con tasklist y se guarda unos segundos: la pagina refresca
    cada dos y no hace falta lanzar un proceso cada vez."""
    ahora = time.time()
    if ahora - _cache_juego["cuando"] < 3.0:
        return _cache_juego["abierto"]
    abierto = False
    try:
        r = subprocess.run(["tasklist", "/FI", "IMAGENAME eq " + _EXE, "/NH"],
                           capture_output=True, timeout=10,
                           creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        abierto = _EXE.lower() in r.stdout.decode("utf-8", "replace").lower()
    except Exception:
        abierto = False
    _cache_juego["cuando"] = ahora
    _cache_juego["abierto"] = abierto
    return abierto


def _recopilando():
    if not os.path.isfile(CANDADO):
        return False
    try:
        return (time.time() - os.path.getmtime(CANDADO)) < _PACIENCIA
    except OSError:
        return False


# Lo que el mod lleva apuntado de la partida que se esta jugando ahora.
#
# Es la unica prueba que ve quien juega de que el mod hace algo. La banda
# decia «EL MOD ESTA ENCENDIDO» igual estuviera apuntando o no, y el «y
# grabando» que llevaba al lado NO era de esto: es de la captura de pantalla
# de la vision, que ni siquiera se publica. Asi que en un clon recien bajado
# esa palabra no salia nunca aunque el mod estuviera funcionando.
_candado_apuntes = threading.Lock()
_cuenta_apuntes = {"ruta": None, "byte": 0, "lineas": 0}


def _apuntando():
    """El .jsonl que el mod esta escribiendo, y cuantas acciones lleva.

    La pagina pregunta cada 2 segundos y el fichero llega a varios MB, asi
    que NO se relee entero: se recuerda por donde iba y solo se cuentan los
    saltos de linea de los bytes NUEVOS. Cortar a mitad de linea no descuadra
    la cuenta, porque el salto que falta se cuenta en la lectura siguiente.
    Si el fichero cambia o encoge --otra partida, o se borro-- se reinicia.
    """
    carpeta = carpeta_de_verdad()
    if not carpeta or not os.path.isdir(carpeta):
        return None
    nueva, cuando = None, -1
    try:
        nombres = os.listdir(carpeta)
    except OSError:
        return None
    for nombre in nombres:
        if not nombre.endswith(".jsonl"):
            continue
        ruta = os.path.join(carpeta, nombre)
        try:
            m = os.path.getmtime(ruta)
        except OSError:
            continue
        if m > cuando:
            nueva, cuando = ruta, m
    if not nueva:
        return None
    c = _cuenta_apuntes
    try:
        tam = os.path.getsize(nueva)
    except OSError:
        return None
    if c["ruta"] != nueva or tam < c["byte"]:
        c.update({"ruta": nueva, "byte": 0, "lineas": 0})
    if tam > c["byte"]:
        try:
            with open(nueva, "rb") as f:
                f.seek(c["byte"])
                trozo = f.read(tam - c["byte"])
            c["lineas"] += trozo.count(b"\n")
            c["byte"] = tam
        except OSError:
            pass
    return {"fichero": os.path.basename(nueva),
            "acciones": c["lineas"],
            # 30 s sin crecer y ya no es «ahora mismo»: es la de antes.
            "viva": (time.time() - cuando) < 30}


# Cuantas acciones se mandan de golpe la primera vez. Sin tope, abrir el
# panel a mitad de partida volcaria tres mil lineas en el registro.
_TOPE_APUNTES = 300

_cola_apuntes = {"ruta": None, "byte": 0, "n": 0}


def _como_se_lee(cruda):
    """Una linea del .jsonl, en algo que se entienda de un vistazo.

    `CatanBase_StartPhase_BuildRoad_GameAction` no lo lee nadie: se le quita
    el envoltorio que le pone el juego y queda `StartPhase BuildRoad`. La
    primera linea del fichero es el esquema y no una accion, asi que se cae
    sola al no tener `accion`.
    """
    try:
        d = json.loads(cruda)
    except ValueError:
        return None
    nombre = d.get("accion")
    if not nombre:
        return None
    if nombre.startswith("CatanBase_"):
        nombre = nombre[len("CatanBase_"):]
    if nombre.endswith("_GameAction"):
        nombre = nombre[:-len("_GameAction")]
    turno = d.get("turno")
    quien = d.get("accion_de")
    linea = "t%-3s j%-3s %s" % ("?" if turno is None else turno,
                                "?" if quien is None else quien,
                                nombre.replace("_", " "))
    # Los dados SOLO en la tirada. `dados` lleva el estado de la mesa, no lo
    # que hizo esta accion: pintarlo en todas dejaba cosas como
    # «BuildCity (2+3 = 5)», que se lee como que construir tiro los dados.
    dados = d.get("dados") or []
    if len(dados) == 2 and nombre.startswith("RollDice"):
        linea += "   (%s+%s = %s)" % (dados[0], dados[1], dados[0] + dados[1])
    return linea


def _apuntes_desde(desde):
    """Lo apuntado a partir de la accion numero `desde`.

    Mismo contrato que el registro de una tarea --devuelve (hasta, lineas)--
    para que la pagina pida solo lo nuevo, y por eso se puede enchufar en la
    misma caja sin tocar nada del otro lado.

    El fichero llega a varios MB y esto se pregunta cada 0,7 s, asi que se
    recuerda en que byte se quedo: si la pagina viene por donde la dejamos,
    solo se lee la cola. Y una linea a medio escribir --el juego esta
    escribiendo mientras leemos-- se deja para la vuelta siguiente en vez de
    contarla a medias.
    """
    carpeta = carpeta_de_verdad()
    with _candado_apuntes:
        ahora = _apuntando()
        if not carpeta or not ahora:
            return 0, []
        ruta = os.path.join(carpeta, ahora["fichero"])
        c = _cola_apuntes
        if c["ruta"] != ruta or c["n"] != desde:
            c.update({"ruta": ruta, "byte": 0, "n": 0})
        lineas, byte, n = [], c["byte"], c["n"]
        try:
            with open(ruta, "rb") as f:
                f.seek(byte)
                for cruda in f:
                    if not cruda.endswith(b"\n"):
                        break
                    byte += len(cruda)
                    n += 1
                    if n <= desde:
                        continue
                    dicho = _como_se_lee(cruda.decode("utf-8", "replace"))
                    if dicho:
                        lineas.append(dicho)
        except OSError:
            return desde, []
        c.update({"byte": byte, "n": n})
    # Las repetidas seguidas, en una sola con su cuenta. El mod apunta una
    # foto por cada metodo que engancha, asi que la misma accion sale entre
    # 5 y 30 veces seguidas -- es normal, viene de siempre, y el importador
    # las agrupa al guardar. Aqui son ruido: cinco `BuildRoad` iguales tapan
    # lo que pasa despues.
    apretadas = []
    for dicho in lineas:
        if apretadas and apretadas[-1][0] == dicho:
            apretadas[-1][1] += 1
        else:
            apretadas.append([dicho, 1])
    lineas = [d if veces == 1 else "%s   x%d" % (d, veces)
              for d, veces in apretadas]

    if len(lineas) > _TOPE_APUNTES:
        cuantas = len(lineas) - _TOPE_APUNTES
        lineas = (["... %d acciones anteriores, no caben" % cuantas]
                  + lineas[-_TOPE_APUNTES:])
    return n, lineas


_cache_partidas = {}


def _partidas_grabadas():
    """Las carpetas de mod_verdad/datos con cuantas fotos tiene cada una.

    Contar las lineas de un indice de 2600 se hace una vez y se guarda: la
    pagina pregunta cada segundo y no hace falta releer el fichero si no ha
    cambiado."""
    salida = []
    if not os.path.isdir(DATOS_GRABADOS):
        return salida
    for nombre in sorted(os.listdir(DATOS_GRABADOS)):
        carpeta = os.path.join(DATOS_GRABADOS, nombre)
        indice = os.path.join(carpeta, "indice.jsonl")
        if not os.path.isdir(carpeta) or not os.path.isfile(indice):
            continue
        try:
            firma = os.path.getmtime(indice), os.path.getsize(indice)
        except OSError:
            continue
        if _cache_partidas.get(nombre, (None,))[0] != firma:
            n = 0
            try:
                with open(indice, encoding="utf-8", errors="replace") as f:
                    for linea in f:
                        if linea.strip():
                            n += 1
            except OSError:
                n = 0
            _cache_partidas[nombre] = (firma, n)
        salida.append({
            "nombre": nombre,
            "fotos": _cache_partidas[nombre][1],
            "preparada": os.path.isfile(os.path.join(DATOS_RED, nombre + ".npz")),
        })
    return salida


# Lo que sabe el modelo se saca llamando a `py -m red.inferencia` en vez
# de cargando el .pt aqui: importar torch en el panel serian dos segundos de
# arranque y varios cientos de MB de memoria para ensenar seis lineas de
# texto. Se pide una vez y se vuelve a pedir cuando acaba un entrenamiento.
_modelo = {"texto": "leyendo...", "sello": None}


def _refrescar_modelo():
    def trabajo():
        if not os.path.isfile(MODELO):
            _modelo["texto"] = "todavia no hay ningun modelo entrenado."
            _modelo["sello"] = None
            return
        try:
            r = subprocess.run([sys.executable, "-u", "-m", "red.inferencia"],
                               cwd=RAIZ, capture_output=True, env=_entorno_hijo(),
                               creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
                               timeout=120)
            _modelo["texto"] = (r.stdout + r.stderr).decode("utf-8", "replace").strip()
        except Exception as e:
            _modelo["texto"] = "no se ha podido leer el modelo: %s" % e
        try:
            _modelo["sello"] = os.path.getmtime(MODELO)
        except OSError:
            _modelo["sello"] = None
    threading.Thread(target=trabajo, daemon=True).start()


# Lo pone `--como-usuario` en main(). No es una constante: es un ajuste de
# esta ejecucion, y por eso se mira cada vez y no se congela al arrancar.
MODO_USUARIO = False


def hay_vision():
    """¿Esta `mirar.py`, que es lo que lee el tablero de la pantalla?"""
    return os.path.isfile(os.path.join(RAIZ, "mirar.py"))


def hay_desarrollo():
    """¿Esta en esta copia la mitad de entrenar, y se quiere ver?

    Dos motivos para que no: que quien clono el repositorio no se llevara esa
    mitad --y entonces los ficheros no estan-- o que se pida la vista de
    siempre con `--simple`."""
    if MODO_USUARIO:
        return False
    return all(os.path.isfile(os.path.join(RAIZ, f))
               for f in ("red/entrenar.py", "red/dataset.py", "red/rutina.py"))


def vistas_viejas():
    """Las vistas guardadas en la base que ya no son las que dice el codigo.

    LAS VISTAS VIVEN DENTRO DEL .db, no en `db/vistas.py`. Ese fichero es lo
    que genera los CREATE VIEW; el resultado se queda en la base de quien lo
    use. Asi que al bajarse una version nueva del proyecto, las vistas siguen
    siendo las viejas hasta que alguien las rehace.

    Y no falla: si la columna ya existia, se ven numeros de la version
    anterior con el codigo nuevo delante y nada lo dice. Solo daba error
    cuando la columna era nueva del todo, que es el caso facil.

    Desde el 2 de septiembre de 2026 el importador las rehace al terminar,
    asi que en la practica esto solo se enciende entre bajarse el codigo y
    importar la primera partida. Se comprueba igual: «en la practica» no es
    una garantia, y esto cuesta un SELECT.

    Se puede mirar en SOLO LECTURA -- es comparar texto con `sqlite_master`
    -- que es justo lo que hace falta aqui: el panel nunca escribe."""
    conn = _abrir_base()
    if conn is None:
        return []
    try:
        guardadas = dict(conn.execute(
            "SELECT name, sql FROM sqlite_master WHERE type='view'"))
    except sqlite3.Error:
        return []
    finally:
        conn.close()
    viejas = []
    for v in _vistas.VISTAS:
        try:
            sql, _args = _vistas.sql_de(v)
        except Exception:
            continue
        quiere = "CREATE VIEW %s AS %s" % (v["nombre"], sql.strip())
        if guardadas.get(v["nombre"]) != quiere:
            viejas.append(v["nombre"])
    return viejas


def estado(idioma=None):
    juego = carpeta_del_juego()
    plugin = (os.path.isfile(os.path.join(juego, "BepInEx", "plugins",
                                          "CatanVerdad.dll")) if juego else False)
    # BepInEx aparte del plugin: son dos cosas y fallan por separado. Sin
    # esto, «no esta instalado» no distinguia entre «falta la plataforma, que
    # hay que bajarla» y «falta compilar», que se arreglan distinto.
    bepinex = (os.path.isfile(os.path.join(juego, "winhttp.dll"))
               and os.path.isfile(os.path.join(juego, "BepInEx", "core",
                                               "BepInEx.dll"))) if juego else False
    # si el modelo ha cambiado en el disco (acaba de entrenarse), releerlo
    try:
        sello = os.path.getmtime(MODELO) if os.path.isfile(MODELO) else None
    except OSError:
        sello = None
    if sello != _modelo["sello"]:
        _refrescar_modelo()
    return {
        "juego": juego,
        "verdad": carpeta_de_verdad(),
        "plugin": plugin,
        "bepinex": bepinex,
        # Que la pagina pueda avisar de que el servidor se ha quedado atras.
        "codigo_viejo": _codigo_viejo(),
        # Y de que las vistas de SU base no son las de este codigo.
        "vistas_viejas": vistas_viejas(),
        # Si sale la mitad de abajo, la de entrenar la vision.
        "desarrollo": hay_desarrollo(),
        "mod": _mod_encendido(juego),
        "juego_abierto": _juego_abierto(),
        "grabando": _recopilando(),
        # Lo que el mod lleva apuntado de la partida de ahora mismo.
        "apunta": _apuntando(),
        "grabacion_viva": grabacion.vivo,
        "tarea": (idiomas.frase(tarea.nombre, idioma)
                  if (tarea.vivo or tarea.acabado_en) else None),
        "tarea_viva": tarea.vivo,
        "tarea_codigo": tarea.codigo,
        "partidas": _partidas_grabadas(),
        "modelo": _modelo["texto"],
        "hay_modelo": os.path.isfile(MODELO),
        # Cuando cambio la base por ultima vez. Sirve para que la lista de
        # partidas se entere de una importacion hecha DESDE FUERA del panel
        # -- por consola -- que es el caso que se quedaba colgado: el
        # catalogo solo se releia al acabar una tarea, asi que importando a
        # mano el panel seguia enseniando las partidas de antes y no habia
        # nada que dijera por que.
        "sello_base": (os.path.getmtime(BASE_DATOS)
                       if os.path.isfile(BASE_DATOS) else None),
    }


# --- las vistas de la base ---------------------------------------------
#
# La base se abre en SOLO LECTURA. Esto es para mirar, y el panel lo puede
# tener abierto cualquiera en la red de casa; que una pagina web pueda
# escribir en el historico no aporta nada y puede costar mucho.
#
# Las consultas no se montan aqui: se piden a `db/vistas.py`, que es donde
# estan escritas una sola vez y donde el global y el detalle por partida
# salen del mismo texto. Si el panel se hiciera las suyas, un dia diria una
# cosa distinta de la que dice `py sql.py` y no habria forma de saber
# cual de las dos esta mal.

BASE_DATOS = os.path.join(RAIZ, "catan_stats.db")

# La lista de vistas se lee al importar el modulo, asi que anadir una y darle
# a «rehacer las vistas» dejaba la pagina enseniando la lista vieja hasta
# reiniciar el panel -- y sin decir por que. Se relee cuando el fichero
# cambia, igual que se relee el modelo cuando se reentrena.
_sello_vistas = {"cuando": None}

# `db/titulares.py` va en la misma lista y por el mismo motivo. Ahi es peor
# todavia: una vista vieja al menos ensena datos, y un titular viejo ensena
# una FRASE, que se lee como si alguien la hubiera escrito hoy.
_sello_titulares = {"cuando": None}


def _releer(modulo, sello, contar):
    try:
        ahora = os.path.getmtime(modulo.__file__)
    except OSError:
        return
    if sello["cuando"] is None:
        sello["cuando"] = ahora
        return
    if ahora != sello["cuando"]:
        sello["cuando"] = ahora
        try:
            # `reload` reescribe el modulo QUE YA HAY, no crea otro, asi que
            # quien lo tenga importado (`titulares` tiene `vistas` dentro) se
            # queda apuntando al bueno sin hacer nada.
            importlib.reload(modulo)
            print("[panel] %s ha cambiado: %s"
                  % (os.path.basename(modulo.__file__), contar()))
        except Exception as e:
            print("[panel] %s no se ha podido releer: %s"
                  % (os.path.basename(modulo.__file__), e))


def _vistas_al_dia():
    _releer(_vistas, _sello_vistas, lambda: "%d vistas" % len(_vistas.VISTAS))
    _releer(_titulares, _sello_titulares,
            lambda: "%d titulares" % len(_titulares.TITULARES))


# Y lo mismo con la página, que vive dentro de ESTE fichero.
#
# `db/vistas.py` se relee sola y `panel.py` no, y esa mitad es la que engaña:
# tocas la tabla, no pasa nada, y no hay ninguna señal de que estés mirando
# una página de hace media hora. Pasó con el orden por cabecera -- estaba
# escrito, probado y servido en la suite, y en el panel de Mario no existía.
#
# Se saca con `ast` y no reejecutando el módulo: ejecutarlo otra vez mientras
# atiende peticiones redefine el servidor por debajo. `ast` sólo lee el texto
# de la constante, que es todo lo que hace falta.
_sello_pagina = {"cuando": None, "html": None}

# La otra mitad del engaño, y la que costó una tarde: la PÁGINA se relee, el
# CÓDIGO no. Así que un panel abierto desde hace rato sirve botones nuevos
# contra un servidor viejo, y el botón nuevo pega contra una ruta que en ese
# proceso no existe. Devuelve 404 y no pasa nada -- ni un mensaje.
#
# Pasó con «Quitar una partida»: el botón salía, se pulsaba, y la partida
# seguía ahí. Todo estaba bien escrito; lo que estaba viejo era el proceso.
#
# Recargar el módulo en caliente no vale (redefine el servidor mientras
# atiende). Lo que sí vale es DECIRLO, que es lo único que faltaba.
def _sin_la_pagina(texto):
    """El fichero con el texto de `PAGINA` en blanco.

    Lo que queda es lo que NO se puede recargar solo: las rutas, las
    funciones, el servidor. `PAGINA` se relee del fichero en cada visita, asi
    que un cambio que solo la toque se arregla con F5 y no hay nada que
    reiniciar."""
    arbol = ast.parse(texto)
    lineas = texto.splitlines(True)
    for nodo in arbol.body:
        if (isinstance(nodo, ast.Assign)
                and any(getattr(d, "id", None) == "PAGINA"
                        for d in nodo.targets)
                and isinstance(nodo.value, ast.Constant)
                and isinstance(nodo.value.value, str)):
            for i in range(nodo.lineno - 1, nodo.end_lineno):
                lineas[i] = "\n"
            break
    return "".join(lineas)


def _huella_del_codigo(texto=None):
    """Un sello de lo que hay que reiniciar. `None` si no se puede leer."""
    try:
        if texto is None:
            with open(__file__, encoding="utf-8") as fh:
                texto = fh.read()
        return hashlib.sha1(_sin_la_pagina(texto).encode("utf-8")).hexdigest()
    except Exception:
        # A medio guardar, el fichero no compila. Eso no es que el codigo
        # haya cambiado: es que todavia no esta entero.
        return None


try:
    _ARRANQUE = os.path.getmtime(__file__)
except OSError:
    _ARRANQUE = None
_HUELLA = _huella_del_codigo()
_sello_codigo = {"cuando": None, "huella": None}


def _codigo_viejo():
    """¿Ha cambiado el CÓDIGO de `panel.py` desde que arrancó este proceso?

    LA PÁGINA NO CUENTA, y esa es toda la diferencia. Antes se comparaba la
    fecha del fichero, asi que el aviso rojo salia por cualquier cambio --
    tambien por los que se arreglan solos dando a F5, que son la mayoria
    mientras se toca la pantalla. Un aviso que salta cuando no hace falta
    ensenia a no leer los avisos, y este avisa de algo de verdad: que los
    botones nuevos estan pegando contra un servidor viejo.

    Se compara una huella del fichero SIN el texto de `PAGINA`. La fecha
    sigue delante como atajo: mientras no cambie, no hay nada que mirar y no
    se vuelve a leer el fichero cada dos segundos."""
    if _ARRANQUE is None or _HUELLA is None:
        return False
    try:
        ahora = os.path.getmtime(__file__)
    except OSError:
        return False
    if ahora == _ARRANQUE:
        return False
    if _sello_codigo["cuando"] != ahora:
        huella = _huella_del_codigo()
        if huella is not None:
            _sello_codigo["cuando"] = ahora
            _sello_codigo["huella"] = huella
    return (_sello_codigo["huella"] is not None
            and _sello_codigo["huella"] != _HUELLA)


def _pagina_al_dia():
    try:
        ahora = os.path.getmtime(__file__)
    except OSError:
        return PAGINA
    if _sello_pagina["cuando"] == ahora and _sello_pagina["html"] is not None:
        return _sello_pagina["html"]
    html = PAGINA
    try:
        import ast
        with open(__file__, encoding="utf-8") as fh:
            arbol = ast.parse(fh.read())
        for nodo in arbol.body:
            if (isinstance(nodo, ast.Assign)
                    and any(getattr(d, "id", None) == "PAGINA"
                            for d in nodo.targets)
                    and isinstance(nodo.value, ast.Constant)
                    and isinstance(nodo.value.value, str)):
                html = nodo.value.value
                break
        if _sello_pagina["cuando"] is not None and html != _sello_pagina["html"]:
            print("[panel] panel.py ha cambiado: pagina recargada")
    except Exception as e:
        # Si el fichero está a medio guardar, se sirve la de memoria y ya.
        print("[panel] panel.py no se ha podido releer: %s" % e)
        html = _sello_pagina["html"] or PAGINA
    _sello_pagina["cuando"] = ahora
    _sello_pagina["html"] = html
    return html


_ATRIBUTOS_QUE_SE_LEEN = ("placeholder", "title", "alt", "aria-label")


def _traducir(html, idioma):
    """La pagina en otro idioma. El porque de todo esto vive en `idiomas.py`.

    Lo importante: NO es un `replace` sobre la pagina entera. El CSS, el
    JavaScript y los identificadores van dentro de la misma cadena, y una
    palabra como «dentro» o «nunca» aparece tambien ahi. Aqui se separa:

      - los <style> no se tocan,
      - los <script> se traducen SOLO con las cadenas entrecomilladas de
        `guion`, comillas incluidas, que no pueden chocar con codigo,
      - y en el resto se toca unicamente lo que hay ENTRE etiquetas.

    Un idioma que no exista devuelve la pagina tal cual, sin quejarse: el
    parametro puede venir de una cookie vieja o de alguien probando a mano.
    """
    lengua = idiomas.IDIOMAS.get(idioma)
    if lengua is None:
        return html
    texto, guion = lengua["texto"], lengua["guion"]
    salida = []
    for i, trozo in enumerate(re.split(
            r"(<script[^>]*>.*?</script>|<style[^>]*>.*?</style>)",
            html, flags=re.S)):
        if i % 2:                      # un <script> o un <style> ENTERO
            if trozo.lstrip().lower().startswith("<script"):
                for es in sorted(guion, key=len, reverse=True):
                    trozo = trozo.replace(es, guion[es])
            salida.append(trozo)
            continue
        partes = re.split(r"(<[^>]+>)", trozo)
        for j, parte in enumerate(partes):
            if j % 2:
                # Una etiqueta. Dentro NO se traduce nada menos los atributos
                # que se LEEN: el texto gris de una caja de busqueda y el
                # globo que sale al pasar el raton. Se quedaban en castellano
                # y no se notaba, porque no son texto de la pagina.
                for atributo in _ATRIBUTOS_QUE_SE_LEEN:
                    for valor in re.findall(r'\b%s="([^"]*)"' % atributo,
                                            parte):
                        if valor in texto:
                            parte = parte.replace(
                                '%s="%s"' % (atributo, valor),
                                '%s="%s"' % (atributo, texto[valor]))
                partes[j] = parte
                continue
            clave = " ".join(parte.split())
            if clave and clave in texto:
                # Se conserva el blanco de los bordes: sin el, una palabra se
                # pegaria a la etiqueta de al lado y saldrian juntas.
                izq = parte[:len(parte) - len(parte.lstrip())]
                der = parte[len(parte.rstrip()):]
                partes[j] = izq + texto[clave] + der
        salida.append("".join(partes))
    return "".join(salida)


def _idioma_pedido(cabeceras, consulta):
    """El idioma de esta visita: primero lo que diga la URL, y si no la cookie.

    Cookie y no `localStorage` como el tema, porque esto lo decide el SERVIDOR
    antes de mandar nada: con localStorage habria que recargar la pagina una
    segunda vez y se veria el cambio a medias.
    """
    for par in consulta.split("&"):
        if par.startswith("idioma="):
            return par[len("idioma="):]
    for galleta in (cabeceras.get("Cookie") or "").split(";"):
        nombre, _, valor = galleta.strip().partition("=")
        if nombre == "idioma":
            return valor
    return idiomas.ORIGINAL


def _con_idioma(html, idioma):
    """La pagina traducida y con la lista de idiomas dentro, para el boton.

    La lista la manda el servidor y no la escribe la pagina, por lo mismo que
    los ambitos: si anadir un idioma obligara a tocar dos sitios, el que se
    olvide seria este.
    """
    vuelta = idiomas.la_vuelta()
    if idioma not in [lengua["id"] for lengua in vuelta]:
        idioma = idiomas.ORIGINAL      # cookie vieja, o alguien probando
    html = _traducir(html, idioma)
    dentro = ("<script>window.IDIOMAS_HAY=%s;window.IDIOMA_AHORA=%s;</script>"
              % (json.dumps(vuelta, ensure_ascii=False), json.dumps(idioma)))
    return html.replace("<!--idiomas-->", dentro)


# Los trozos entre <!--dev--> y <!--/dev--> se QUITAN de la pagina, no se
# esconden con CSS. La diferencia importa: escondido, el que mire el codigo
# fuente ve una lista de botones que no tiene, y la pagina que recibe no es
# la que ve. Quitado, lo que llega es un panel entero y coherente.
# Dos marcas, porque son dos cosas que van y vienen por separado:
#
#   <!--dev-->      entrenar la red. Solo si esta `red/entrenar.py` y compania.
#   <!--vision-->   leer el tablero de la pantalla. Solo si esta `mirar.py`.
#
# La segunda hace falta porque «Mirar la pantalla» es de la mitad de la
# vision pero se ENSENA: es lo que mas se quiere que se vea el dia que
# funcione bien. Mientras esa mitad no suba, el bloque no existe.
_MARCA_DEV = re.compile(r"<!--dev-->.*?<!--/dev-->", re.S)
_MARCA_VISION = re.compile(r"<!--vision-->.*?<!--/vision-->", re.S)
_MARCAS_SUELTAS = re.compile(r"<!--/?(?:dev|vision)-->")


def _pagina_para(html, con_desarrollo, con_vision=True):
    if not con_vision:
        html = _MARCA_VISION.sub("", html)
    if not con_desarrollo:
        html = _MARCA_DEV.sub("", html)
    # Las que sobrevivan se quitan igual: son andamios, no contenido, y en
    # el codigo fuente de la pagina delatan que hay algo que no se manda.
    return _MARCAS_SUELTAS.sub("", html)


def _abrir_base():
    if not os.path.isfile(BASE_DATOS):
        return None
    return sqlite3.connect("file:%s?mode=ro" % BASE_DATOS.replace("\\", "/"),
                           uri=True)


# --- preguntar en cristiano --------------------------------------------
#
# Una caja donde se escribe «cuantos caballeros le han caido a elGato» y sale
# el numero. No hay ningun modelo de lenguaje detras y no hace falta: la
# pregunta no se entiende, se EMPAREJA. Las vistas ya traen titulo,
# resumen y nombres de columna en cristiano, asi que el catalogo de lo que se
# puede preguntar ya estaba escrito -- solo hay que buscar dentro.
#
# Lo que esto NO hace, y conviene saberlo: no inventa consultas. Si la
# respuesta no esta en ninguna columna de ninguna vista, lo dice en vez de
# apanar algo. Y ensena SIEMPRE de donde ha sacado el numero, porque un
# numero suelto sin poder comprobarlo es peor que no tenerlo.
_PISTAS_TOTAL = {"cuantos", "cuantas", "cuanto", "total", "suma", "sumando"}
_PISTAS_QUIEN = {"quien", "cual", "mas", "menos", "mejor", "peor"}
# HACIA QUE LADO SE MIRA: al que mas o al que menos. Sin esto, «quien ha
# tardado MENOS en poner una ciudad» contestaba con el maximo, que es justo
# el contrario.
#
# Y hay dos clases de pista, que es lo que estaba mezclado. Unas lo DICEN --
# «mas», «menos» -- y otras solo lo insinuan: «antes», «primero», «pronto»
# quieren decir «cuanto mas bajo el turno, mejor». Estaban en el mismo saco,
# asi que «quien ha salido mas veces PRIMERO» contestaba con el que menos
# veces habia salido primero: la palabra «primero» tapaba al «mas» de al
# lado, y encima la vista y la columna eran las correctas.
#
# La regla, que no es de esta pregunta sino de todas: lo que se dice gana a
# lo que se insinua.
_MENOS_DICHO = {"menos", "menor"}
_MAS_DICHO = {"mas", "mayor"}
_MENOS_INSINUADO = {"antes", "primero", "pronto", "rapido", "peor"}
_PISTAS_MENOS = _MENOS_DICHO | _MENOS_INSINUADO


def _mira_al_que_menos(pistas):
    """Si la pregunta busca el extremo de abajo en vez del de arriba."""
    if pistas & _MENOS_DICHO:
        return True
    if pistas & _MAS_DICHO:
        return False
    return bool(pistas & _MENOS_INSINUADO)
# Preguntas de CUANDO. Las columnas de turno no compiten bien por nombre --
# `primera_ciudad` no se llama «turno» -- y sin este empujon «quien tardo
# menos en poner una ciudad» se iba a contar ciudades.
_PISTAS_TIEMPO = {"turno", "turnos", "tardado", "tarda", "tardo", "tardan",
                  "cuando", "antes", "pronto", "rapido", "primero", "empezo",
                  "tardar"}
_COLUMNAS_TURNO = {"turno", "primera_ciudad", "primera_carta",
                   "primer_caballero", "tercer_poblado", "duro_hasta",
                   "primer_uso", "ultimo_uso", "primer_poblado"}
# Palabras que no dicen de que va la pregunta. Van fuera ANTES de emparejar:
# dejarlas dentro es lo que hacia que «cuantos caballeros le han caido a
# elGato» acabara en la columna `robo_el` -- «elgato» empieza por «el», que es
# un trozo del nombre de esa columna. Un emparejador flojo no da una respuesta
# floja: da una respuesta segura y equivocada, que es mucho peor.
_DE_PASO = {"de", "del", "la", "el", "los", "las", "en", "a", "al", "que",
            "y", "o", "un", "una", "unos", "unas", "su", "sus", "me", "le",
            "les", "se", "han", "ha", "hay", "he", "es", "son", "con", "por",
            "para", "todos", "todas", "todo", "toda", "tiene", "tienen",
            "caido", "caidos", "sacado", "jugado", "jugados", "hecho",
            "hechos", "sido", "esta", "estan", "como", "cuando", "donde",
            "partida", "partidas", "juego", "jugador", "jugadores", "veces"}
# Auxiliares: lo que va detras es un verbo, no un nombre. «ha PUESTO el
# ladron» no habla de la columna `puesto` (en que puesto quedo), y esa
# confusion mandaba la pregunta del ladron a la tabla del orden de salida.
_AUXILIARES = {"ha", "han", "he", "has", "hemos", "habia", "habian"}
# Solo los que son OTRA COSA como nombre. `puesto` es una columna -- en que
# puesto quedo -- y tambien el participio de poner, y por eso «quien ha PUESTO
# el ladron» acababa en la tabla del orden de salida. Con la lista larga se
# rompia lo contrario: «han ROBADO» perdia la unica palabra que decia de que
# iba la pregunta.
_PARTICIPIOS = {"puesto"}

_SINONIMOS = {
    "gana": "victoria", "ganar": "victoria", "ganado": "victoria",
    "ganadas": "victoria", "ganada": "victoria", "gano": "victoria",
    "media": "medio", "promedio": "medio",
    "robar": "robo", "robado": "robo", "roban": "robo", "robaron": "robo",
    "robados": "robo", "quitado": "robo",
    "tirar": "tirada", "tirado": "tirada", "dado": "tirada",
    "dados": "tirada",
    "sale": "tirada", "salen": "tirada", "salio": "tirada",
    "salido": "tirada", "roba": "robo", "roben": "robo",
    "durado": "minuto", "dura": "minuto", "duracion": "minuto",
    "empieza": "salida", "empiezan": "salida", "empezo": "salida",
    "cambiar": "comercio", "cambiado": "comercio", "comerciar": "comercio",
    # «Intercambio» es como se dice un trato la mitad de las veces, y sin
    # esto «quien gana mas en los INTERCAMBIOS» no encontraba ninguna vista
    # de comercio -- ni una las lleva en el nombre -- y se iba al Marcador a
    # contestar con las victorias.
    "intercambio": "trato", "intercambios": "trato",
    "intercambiar": "trato", "intercambia": "trato",
    "construir": "edificio", "construido": "edificio",
    "pillado": "pillo", "cogido": "pillo",
    "pierde": "perdido", "perder": "perdido", "pierden": "perdido",
    # La columna se llama `producido`, pero nadie pregunta «cuanto ha
    # producido»: se dice cobrar. Las dos formas tienen que llevar al mismo
    # sitio o la caja de preguntas contesta que no lo sabe.
    "cobra": "producido", "cobrar": "producido", "cobrado": "producido",
    "produce": "producido", "producir": "producido", "produjo": "producido",
    "bloquea": "bloqueo", "bloquear": "bloqueo", "bloqueado": "bloqueo",
    "tapa": "bloqueo", "tapado": "bloqueo", "tapan": "bloqueo",
    "tapo": "bloqueo", "taparon": "bloqueo",
    "puso": "puso", "pone": "puso", "ponen": "puso", "pusieron": "puso",

    # LOS RECURSOS, COMO LOS DICE LA GENTE. En la base son «Madera»,
    # «Arcilla», «Lana», «Cereales» y «Mineral», y nadie habla asi: se dice
    # oveja, barro, trigo y piedra. Sin esto, «cuanto barro ha producido
    # carlarr» no fallaba -- que seria lo correcto -- sino que contestaba
    # con el total de TODO lo producido, ignorando el barro. Peor que
    # callarse.
    "oveja": "lana", "ovejas": "lana", "borrego": "lana", "borregos": "lana",
    "barro": "arcilla", "ladrillo": "arcilla", "ladrillos": "arcilla",
    "adobe": "arcilla",
    "trigo": "cereales", "grano": "cereales", "cereal": "cereales",
    "espiga": "cereales", "espigas": "cereales",
    "piedra": "mineral", "piedras": "mineral", "roca": "mineral",
    "mena": "mineral", "montana": "mineral",
    "lena": "madera", "bosque": "madera", "troncos": "madera",
    "tronco": "madera",

    # LOS NUMEROS EN LETRA. «cuantas veces ha salido el siete» contestaba
    # 541, que es la suma de todas las tiradas: no encontraba el 7 por
    # ninguna parte y acababa sumando la columna entera.
    "dos": "2", "tres": "3", "cuatro": "4", "cinco": "5", "seis": "6",
    "siete": "7", "ocho": "8", "nueve": "9", "diez": "10", "once": "11",
    "doce": "12",

    # UNA CASILLA SE NOMBRA POR SU NUMERO. Es como se habla en la mesa: «el
    # 8 de trigo». Sin esto, «en que casilla se pone mas el ladron» se iba a
    # «Partidas, columna casillas» --que son cuantas casillas tiene el
    # tablero, 19 o 30-- porque el nombre pegaba exacto y ganaba a cualquier
    # vista del ladron. La respuesta era de otra pregunta.
    "casilla": "numero", "casillas": "numero", "hexagono": "numero",
    "hex": "numero", "ficha": "numero",
}

# Cuando una columna NO se puede leer a pelo, y por cual hay que leerla.
#
# `suerte` es el caso que lo destapo: es un porcentaje de lo que te tocaba, y
# con nueve casillas de UNA partida se dispara. La caja contestaba «el que
# mas suerte: Bruno, con 108,7» -- Bruno jugo una partida, y su margen de
# error es +-17,6, o sea que 108,7 esta dentro de lo normal.
#
# La vista YA trae la respuesta buena al lado (`se_sale`, la desviacion
# tipica), y la caja la ignoraba. Eso no es no saber: es dar un numero malo
# teniendo el bueno en la misma tabla, que en un proyecto que va de rigor es
# lo peor que puede pasar.
_ORDENAR_POR = {
    "suerte": "se_sale",
    "de_mas": "se_sale",
    "le_toco": "se_sale",
}


def _pelado(texto):
    """Sin acentos, en minusculas y partido en palabras."""
    limpio = unicodedata.normalize("NFD", str(texto).lower())
    limpio = "".join(c for c in limpio if not 0x300 <= ord(c) <= 0x36f)
    # El guion bajo TAMBIEN parte. Es lo que hace que `amigos_robos` sean dos
    # palabras y no una: dejandolo dentro, ni un nombre de vista ni uno de
    # columna se encontraba nunca.
    return [p for p in re.split(r"[^a-z0-9]+", limpio) if p]


def _raiz(palabra):
    """El plural y el singular tienen que encontrarse: «caballeros» busca
    `caballero`. No es un lematizador y no hace falta que lo sea: los nombres
    de las columnas los escribimos nosotros."""
    if len(palabra) > 4 and palabra.endswith("es"):
        return palabra[:-2]
    if len(palabra) > 3 and palabra.endswith("s"):
        return palabra[:-1]
    return palabra


def _pega(a, b):
    """Cuanto se parecen dos palabras. 1 es la misma; 0,5 es «se parece».

    El medio punto es por las cuatro primeras letras y solo entre palabras
    largas: «producido» encuentra `produccion` y «robado» encuentra `robo`,
    pero «carta» no encuentra `carretera`. Vale la mitad para que una
    coincidencia de verdad siempre gane a un parecido."""
    if a == b:
        return 1.0
    if len(a) >= 5 and len(b) >= 5 and a[:4] == b[:4]:
        return 0.5
    return 0.0


def _cuanto(utiles, catalogo):
    """Lo que pegan las palabras de la pregunta con las de un sitio."""
    return sum(max((_pega(u, c) for c in catalogo), default=0.0)
               for u in utiles)


# Un nombre de columna con un numero de puesto dentro vale tambien por su
# ordinal. `salio_1` tiene que encontrarse preguntando «salio primero», que es
# como se dice.
#
# Va AQUI y no en `_SINONIMOS`, y la diferencia importa: los sinonimos los usa
# tambien la lista de CIFRAS de la pregunta -- la que hace que «cuantas veces
# ha salido el siete» busque la fila del 7 -- asi que metiendo «primero» -> 1
# ahi, «a quien le toca salir primero» se iba a la tabla que tiene una columna
# con el valor 1 dentro. Medido: costaba una pregunta del examen.
_ORDINALES = {"1": "primero", "2": "segundo", "3": "tercero",
              "4": "cuarto", "5": "quinto", "6": "sexto"}

# Palabras que valen para encontrar una columna y NO estan en su nombre. Va
# aqui por lo mismo que `_ORDINALES`: es del lado del catalogo, no de la
# pregunta, asi que anadir una no cambia lo que significa esa palabra cuando
# alguien la escribe.
#
# `neto` es el caso que lo pide. La columna se llama asi en las cuatro vistas
# de comercio, pero nadie pregunta «cual es el neto»: se dice «quien GANA en
# los intercambios», «quien sale ganando cartas», «quien va POSITIVO». Sin
# esto, «quien gana mas en los intercambios» se iba al Marcador y contestaba
# «carlarr, con 7 victorias» -- la vista buena ni siquiera era candidata,
# porque una columna solo entra en la lista si alguna palabra de la pregunta
# pega con su nombre.
#
# Y NO le quita «gana» al Marcador, que es lo que habria pasado tocando
# `_SINONIMOS`. El reparto lo hace la division por `len(trozos)` que ya
# estaba: `victorias` trae una sola palabra y se lleva los 12 puntos enteros;
# `neto` trae tres y se lleva 4. O sea que en «quien gana mas» sigue ganando
# el Marcador de calle, y en «quien gana mas en los intercambios» decide el
# titulo de la vista, que es quien tiene que decidirlo.
_TAMBIEN_SE_DICE = {
    "neto": ("victoria", "positivo", "saldo"),
}


def _catalogo(texto):
    """Las palabras de un titulo o de un nombre, listas para comparar.

    Pasan por los MISMOS sinonimos que la pregunta, y eso no es simetria
    porque si: la vista se titula «Los números que más TAPA el ladrón» y la
    gente pregunta «qué números BLOQUEA más». Traduciendo solo un lado, el
    titulo que mejor describe la pregunta era el que menos puntuaba."""
    salida = set()
    for p in _pelado(texto):
        salida.add(_SINONIMOS.get(p, _raiz(_SINONIMOS.get(_raiz(p), p))))
        if p in _ORDINALES:
            salida.add(_ORDINALES[p])
        salida.update(_TAMBIEN_SE_DICE.get(p, ()))
    return salida


# Columnas que son el EJE de la tabla, no la respuesta. Nadie pregunta
# «cuanto game_id tiene elGato».
_NO_SON_RESPUESTA = {"quien", "a_quien", "con_quien", "partida", "game_id",
                     "player_id", "dia", "hora"}
# Columnas que SI se pueden nombrar en la pregunta pero que no son una
# cantidad: son de que va cada fila. «El que mas numero: LoboEstepario, con
# 11» es lo que salia antes de tener esto, y no quiere decir nada.
_EJES = {"numero", "recurso", "puerto", "carta", "pieza", "color", "salida",
         "terrenos", "cuales", "pidio", "de_quien"}
# Columnas por las que tiene sentido FILTRAR con un numero de la pregunta.
# «El 11» de «quien puso el ladron en el 11» es un valor, no una cantidad --
# y contarlo como cantidad daba «el que mas caballero: carlarr, con 11»,
# que es la clase de respuesta que parece buena y esta mal del todo.
#
# La lista es corta a proposito: si se dejara filtrar por cualquier columna,
# un 11 encontraria un `veces = 11` en cualquier tabla y volveriamos a lo
# mismo por otro camino.
_FILTRABLES = ("numero", "turno", "partida", "game_id", "salida")
# Los cinco recursos, para poder decir «sobre todo arcilla».
_RECURSOS = ("madera", "arcilla", "lana", "cereales", "mineral")
# Columnas que NO se pueden sumar aunque sean numeros. Un porcentaje, una
# media o un turno no se suman: sumar `puesto_medio` de cuatro filas da un
# numero que no existe.
# `casillas_tablero` es cuantas tenia el tablero: 19 o 30. Sumarlas da 182,
# que es la suma de catorce tableros y no es un numero que exista. Ojo: la
# `casillas` de `amigos_suerte` son las de cada jugador y esas SI se suman;
# por eso la del tablero se llama distinto.
_NO_SE_SUMAN = {"casillas_tablero",
                "porcentaje", "porcentaje_normal", "en_el_mazo", "suerte",
                "margen", "se_sale", "puesto_medio", "puntos_medios",
                "salida_media", "por_casilla", "lo_normal", "cada_casilla",
                "puesto", "puntos", "salida", "puestos_ganados", "su_mejor",
                "turno", "primer_uso", "ultimo_uso", "tercer_poblado",
                "primera_ciudad", "primera_carta", "primer_caballero",
                "duro_hasta", "al_menos", "le_tocaba", "deberia_salir",
                "salieron_normales", "veces_normales", "puntitos", "minutos"}
# Con menos que esto no se contesta. Mas vale decir «no se» que dar el numero
# de una columna que se parecia de lejos.
_MINIMO = 8


def _agrupar(cols, filas, eje):
    """Colapsa una vista por una de sus columnas, sumando lo que se puede.

    Es lo que deja contestar preguntas que NO estan en ninguna vista sin
    escribir SQL nuevo: «Donde pone el ladron cada uno» es por persona y
    numero, y agrupada por recurso contesta otra cosa. La vista sigue siendo
    la de siempre -- ya revisada, ya con su filtro de amigos puesto -- y aqui
    solo se suman filas que ya estaban.

    Lo que no se suma se tira, y eso es a proposito: dejar la primera persona
    de cada grupo en la columna `quien` daria una tabla que parece decir algo
    y no lo dice."""
    suma_i = [k for k, c in enumerate(cols)
              if c != eje and c not in _NO_SE_SUMAN
              and any(isinstance(f[k], int) and not isinstance(f[k], bool)
                      for f in filas)
              and all(f[k] is None or (isinstance(f[k], int)
                                       and not isinstance(f[k], bool))
                      for f in filas)]
    if not suma_i:
        return None, None
    e = cols.index(eje)
    juntas = {}
    for f in filas:
        caja = juntas.setdefault(f[e], [0] * len(suma_i))
        for n, k in enumerate(suma_i):
            if f[k] is not None:
                caja[n] += f[k]
    nuevas_cols = [eje] + [cols[k] for k in suma_i]
    nuevas = [[clave] + caja for clave, caja in juntas.items()]
    nuevas.sort(key=lambda f: -(f[1] or 0))
    return nuevas_cols, nuevas


def _y_que_recursos(cols, filas):
    """«...sobre todo arcilla (23)», si la fila trae el desglose.

    Media pregunta se quedaba sin contestar: «quien ha perdido mas recursos
    por el ladron Y QUE RECURSOS» daba el total y se callaba la segunda mitad,
    teniendo las cinco columnas al lado."""
    if not all(r in cols for r in _RECURSOS):
        return ""
    suma = {}
    for r in _RECURSOS:
        k = cols.index(r)
        vals = [f[k] for f in filas if isinstance(f[k], (int, float))]
        if vals:
            suma[r] = sum(vals)
    if not suma or not max(suma.values()):
        return ""
    cual = max(suma, key=lambda r: suma[r])
    otros = sum(v for r, v in suma.items() if r != cual)
    if suma[cual] <= otros / 2.0:          # repartido: decirlo seria mentir
        return "  Repartido: " + ", ".join(
            "%s %d" % (r, suma[r]) for r in _RECURSOS if suma.get(r))
    return "  Sobre todo %s (%d de %d)." % (cual, suma[cual],
                                            sum(suma.values()))


def _palabras_utiles(palabras, suyas):
    """Lo que queda para emparejar: ni muletillas, ni la persona, ni las
    palabras que solo dicen QUE FORMA tiene la pregunta, ni los participios
    que van detras de un auxiliar -- «ha PUESTO» es un verbo, no la columna
    `puesto`."""
    utiles = set()
    anterior = ""
    for p in palabras:
        previa, anterior = anterior, p
        if p in _DE_PASO or p in suyas or p.isdigit():
            continue
        if p in _PARTICIPIOS and previa in _AUXILIARES:
            continue
        if p in _PISTAS_TOTAL or p in _PISTAS_QUIEN:
            # «gana» es pista de pregunta Y palabra de contenido, asi que se
            # mira el sinonimo antes de tirarla.
            if p not in _SINONIMOS:
                continue
        utiles.add(_SINONIMOS.get(p, _raiz(_SINONIMOS.get(_raiz(p), p))))
    return utiles


def preguntar(texto, ambito="amigos"):
    """Busca la respuesta en las vistas y la dice con una frase.

    No hay ningun modelo de lenguaje detras y no hace falta: la pregunta no se
    entiende, se EMPAREJA contra los nombres, titulos y resumenes que las
    vistas ya traen escritos en cristiano.

    Lo que NO hace: inventar consultas. Si la respuesta no esta en ninguna
    columna de ninguna vista, lo dice. Y ensena siempre de donde ha sacado el
    numero y con que comando se saca por consola, porque un numero que no se
    puede comprobar es peor que no tenerlo."""
    conn = _abrir_base()
    if conn is None:
        return {"error": "Todavia no hay base de datos."}
    try:
        palabras = _pelado(texto)
        if not palabras:
            return {"error": "Preguntame algo."}
        pistas = set(palabras)
        # «A QUIEN» y «CON QUIEN» piden un nombre, no un total, y solo lo
        # pueden contestar las vistas de parejas. Hay que mirarlo en las
        # palabras SEGUIDAS y no en `pistas`, que es un conjunto: ahi «a» y
        # «quien» estan sueltas y aparecen en media pregunta.
        #
        # Sin esto, «a quien le pone mas el ladron carla» se iba a «El
        # ladron» -- que puntua altisimo porque se llama igual -- y contestaba
        # cuantas veces se lo pusieron A EL. La pregunta era la contraria.
        pide_pareja = any(palabras[k] in ("a", "con") and palabras[k + 1] == "quien"
                          for k in range(len(palabras) - 1))
        # Y con un pronombre, que es la misma relacion dicha corta: «quien ME
        # quita mas ovejas» pide exactamente lo mismo que «a quien le quita
        # mas ovejas», y sin esto se iba a la vista sin parejas. No se meten
        # «le» ni «les» aunque tambien valdrian: salen en media pregunta
        # («cuantas cartas LE ha dado») y disparan de mas.
        pide_pareja = pide_pareja or any(p in ("me", "nos", "conmigo")
                                         for p in palabras)
        # Y «TOCAR» lo cancela, porque en castellano «a quien le toca» no
        # pide una pareja: pide una persona sola. «A quien le toca salir
        # primero» es «quien sale primero mas veces», no «quien se lo hace a
        # quien». El verbo es la pista buena y no el «a quien», que es igual
        # en los dos casos -- compara «a quien le pone mas el ladron carla»,
        # que si es de parejas y tambien lleva «le».
        #
        # Medido: sin esto son 35 de 60 y con esto 36, y no rompe ninguna.
        if any(p in ("toca", "tocan", "tocar", "toco") for p in palabras):
            pide_pareja = False
        # Los numeros escritos con letra cuentan igual. «cuantas veces ha
        # salido el SIETE» no encontraba ningun 7 y acababa sumando la
        # columna entera: 541 tiradas, que no contesta nada.
        cifras = []
        for pal in palabras:
            crudo = _SINONIMOS.get(pal, pal)
            if crudo.isdigit() and len(crudo) <= 4:
                cifras.append(int(crudo))

        # 1. Que persona nombra, si nombra alguna. Por trozos: «carla» tiene
        #    que encontrar a «carlarr», que es como se escribe de verdad.
        gente = [r[0] for r in conn.execute(
            "SELECT DISTINCT COALESCE(person_name, name) FROM players")]
        # Pueden ser DOS: «cuantas veces le ha puesto lobo el ladron a
        # bruno» necesita las dos puntas, y con una sola la pregunta no se
        # puede contestar -- las vistas de parejas tienen `quien` y `a_quien`.
        # Se empareja PALABRA A PALABRA y no persona a persona, y la
        # diferencia importa: antes se recorria la gente y cada uno se quedaba
        # con la primera palabra que le pegara, asi que quien saliera antes en
        # la lista ganaba. Con apodos distintos no se notaba nunca; con los
        # nombres provisionales que pone el importador --`jugador_4645eb8a`,
        # `jugador_21edc045`, todos con el mismo principio-- contestaba sobre
        # dos personas que no eran, y con la misma seguridad que si acertara.
        # Justo lo que este proyecto no hace.
        #
        # Ahora, si una palabra le pega a mas de uno, NO se elige: se dice.
        nombrados, suyas, ambiguas = [], set(), []
        planos = [(q, "".join(_pelado(q))) for q in gente]
        for k, p in enumerate(palabras):
            if p in suyas or len(p) < 3 or p.isdigit():
                continue
            candidatos = [q for q, plano in planos if p in plano or plano in p]
            if not candidatos:
                continue
            if len(candidatos) > 1:
                # Puede que uno encaje EXACTO y los demas solo por trozos:
                # «bruno» contra `Bruno` es exacto y no hay duda.
                exactos = [q for q in candidatos
                           if "".join(_pelado(q)) == p]
                if len(exactos) == 1:
                    candidatos = exactos
                else:
                    ambiguas.append((p, sorted(candidatos)))
                    suyas.add(p)
                    continue
            # Una persona se nombra UNA vez. `LaNube-ESP` se parte en dos
            # palabras y las dos le pegan; sin esto salia nombrado dos veces y
            # la pregunta se iba a una vista de PAREJAS -- «TheClonne a
            # TheClonne: ninguna vez». El bucle viejo lo evitaba con un
            # `break` por persona, y al darle la vuelta se perdio.
            if candidatos[0] in [q for _k, q in nombrados]:
                suyas.add(p)
                continue
            nombrados.append((k, candidatos[0]))
            suyas.add(p)
        if ambiguas:
            p, quienes = ambiguas[0]
            return {"sin_respuesta": True,
                    "respuesta": "«%s» me vale para %d personas (%s). "
                                 "Dime cual, o ponles nombre en el paso 2: "
                                 "mientras se llamen todos «jugador_algo» no "
                                 "los puedo distinguir."
                                 % (p, len(quienes), ", ".join(quienes[:4]))}
        # En el orden en que salen en la frase: el primero es quien hace la
        # accion y el segundo quien la recibe, que es como se habla.
        nombrados.sort()
        persona = nombrados[0][1] if nombrados else None
        segunda = nombrados[1][1] if len(nombrados) > 1 else None

        utiles = _palabras_utiles(palabras, suyas)
        if not utiles:
            return {"sin_respuesta": True,
                    "respuesta": "No se de que me hablas. Nombra algo: "
                                 "caballeros, monopolios, puertos, robos, "
                                 "suerte, tiradas, puntos, ladron...",
                    "columnas": [], "filas": [], "otras": []}

        # 2. Puntuar cada columna de cada vista. Tres clases de respuesta:
        #      columna  -- el valor de una columna  («cuantos caballeros»)
        #      filas    -- cuantas filas hay        («cuantos monopolios tiro»)
        #      vista    -- la tabla entera, de ultimo recurso
        candidatos = []
        for v in _vistas.VISTAS:
            try:
                cols, filas = _vistas.consultar(conn, v["nombre"], None, ambito)
            except sqlite3.Error:
                continue
            del_nombre = _catalogo(v["nombre"]) - {"amigo"}
            del_titulo = _catalogo(v["titulo"])
            del_que = _catalogo(v["que"])
            # El nombre de la vista puntua como la columna: dividido por lo
            # que tiene y no se ha preguntado. `amigos_tiradas` es TODO
            # tiradas; `amigos_ladron_numeros` es ladron Y numeros.
            pegan = _cuanto(utiles, del_nombre)
            punto_vista = (8 * pegan * pegan / max(1, len(del_nombre))
                           + 5 * _cuanto(utiles, del_titulo)
                           + 2 * _cuanto(utiles, del_que))

            # ¿Se puede filtrar por alguna cifra de la pregunta?
            filtro = None
            for nombre_col in _FILTRABLES:
                if nombre_col not in cols or filtro:
                    continue
                # Filtrar por PARTIDA solo si la pregunta dice «partida». Un
                # numero suelto es casi siempre una casilla: «cuantos 7 han
                # salido» acababa filtrando la partida 7 y contestando 64, que
                # son sus tiradas totales.
                if nombre_col in ("partida", "game_id") and not (
                        pistas & {"partida", "partidas", "juego"}):
                    continue
                k = cols.index(nombre_col)
                valores = set(f[k] for f in filas)
                for n in cifras:
                    if n in valores:
                        filtro = (k, n, nombre_col)
                        break
            if filtro:
                punto_vista += 10
            # Con dos personas nombradas, la vista de PAREJAS es la unica que
            # puede contestar.
            if segunda and "a_quien" in cols and "quien" in cols:
                punto_vista += 12
            # Y con «a quien» o «con quien», tambien: la respuesta es un
            # nombre y solo lo tienen las de parejas.
            if pide_pareja and ("a_quien" in cols or "con_quien" in cols):
                punto_vista += 12
            elif pide_pareja and "quien" in cols:
                # Y las que NO son de parejas, penalizadas. Solo premiar no
                # bastaba: «a quien le roba mas carla» se iba a «Robos de la
                # mano», que se llama igual que la pregunta y gana por nombre
                # aunque no tenga a quien. Contestaba 48, que es todo lo que
                # ha robado en su vida y a nadie en concreto.
                punto_vista -= 8
            elif not segunda and ("a_quien" in cols or "con_quien" in cols):
                # LA MITAD QUE FALTABA, y es simetrica de la de arriba: si NO
                # se pide una pareja, una vista de parejas es peor respuesta
                # que la equivalente sin parejas, porque reparte la cuenta
                # entre varias filas y ninguna contesta sola.
                #
                # Faltaba porque hasta ahora ninguna vista de parejas competia
                # de verdad con otra. El 2 de septiembre de 2026 aparecio
                # `amigos_ladron_a_quien_numero` -- quien, a quien y en que
                # numero -- y le robo «quien tapo el 11» a la que contesta eso
                # de verdad: la de persona y numero. Las dos tienen `numero`,
                # pero la de parejas parte el 11 de cada uno entre todos sus
                # rivales.
                punto_vista -= 8

            # Una vista con `quien` contesta POR PERSONA. Si nadie ha
            # nombrado a nadie y la pregunta no dice «quien», lo que se busca
            # es de la mesa entera. Y al reves: preguntando «quien», una vista
            # SIN esa columna no puede contestar por mucho que puntue -- «quien
            # puso el ladron en el 11» se iba a la tabla por numeros, que sabe
            # cuantas veces pero no de quien.
            if not (persona or "quien" in pistas) and "quien" in cols:
                punto_vista -= 4

            for i, c in enumerate(cols):
                if c in _NO_SON_RESPUESTA:
                    continue
                trozos = _catalogo(c)
                pega_col = _cuanto(utiles, trozos)
                if not pega_col:
                    continue
                # Dividido por lo que la columna tiene y no se ha preguntado:
                # si no, `con_caballero` empata con `caballero`.
                punto_col = 12 * pega_col * pega_col / max(1, len(trozos))
                if (pistas & _PISTAS_TIEMPO) and c in _COLUMNAS_TURNO:
                    punto_col += 8
                candidatos.append({"punto": punto_col + punto_vista,
                                   "clase": "columna", "v": v, "cols": cols,
                                   "filas": filas, "i": i, "col": c,
                                   "filtro": filtro})
            # Contar filas: solo si la pregunta va de contar, lo nombrado es
            # el nombre de la vista, Y la vista es una LISTA DE COSAS QUE
            # PASARON -- las que llevan `turno`.
            if (punto_vista >= 8 and (pistas & _PISTAS_TOTAL)
                    and "turno" in cols):
                candidatos.append({"punto": punto_vista + 4, "clase": "filas",
                                   "v": v, "cols": cols, "filas": filas,
                                   "i": None, "col": None, "filtro": filtro})
            # Con un filtro puesto, la vista entera ya es una respuesta:
            # «quien puso el ladron en el 11» no necesita ninguna columna que
            # se llame como la pregunta, necesita la fila del 11.
            if punto_vista >= 8:
                candidatos.append({"punto": punto_vista - (6 if filtro else 100),
                                   "clase": "vista", "v": v, "cols": cols,
                                   "filas": filas, "i": None, "col": None,
                                   "filtro": filtro})

        candidatos = [c for c in candidatos
                      if c["punto"] >= _MINIMO or c["clase"] == "vista"]
        if not candidatos:
            return {"sin_respuesta": True,
                    "respuesta": "Eso no lo tengo guardado en ninguna vista. "
                                 "Prueba con otra palabra: caballeros, "
                                 "monopolios, puertos, robos, suerte, "
                                 "tiradas, puntos, ladron, comercio...",
                    "columnas": [], "filas": [], "otras": []}
        candidatos.sort(key=lambda c: (-c["punto"], c["v"]["nombre"]))

        def numero(x):
            return isinstance(x, (int, float)) and not isinstance(x, bool)

        def sabe_contar(c):
            if c["clase"] != "columna":
                return True
            if c["col"] in _EJES:
                return any(k for k, c2 in enumerate(c["cols"])
                           if c2 not in _EJES and c2 not in _NO_SON_RESPUESTA
                           and any(numero(f[k]) for f in c["filas"]))
            return any(numero(f[c["i"]]) for f in c["filas"])

        elegido = candidatos[0]

        # Preguntando «quien», la vista tiene que saber de gente. No basta con
        # puntuar bien: «quien tapo el 11» se iba a la tabla POR NUMEROS, que
        # sabe cuantas veces y no de quien, y contestaba «1 veces». Vale la
        # columna `quien` o cualquier otra cuyos valores sean nombres -- `gano`
        # lo es, y es la que contesta «en la partida 7 quien gano».
        nombres = set(gente)

        def sabe_de_gente(c):
            if "quien" in c["cols"]:
                return True
            k = c["cols"].index(c["col"]) if c["col"] in c["cols"] else None
            return k is not None and any(f[k] in nombres for f in c["filas"])

        if (persona or "quien" in pistas) and not sabe_de_gente(elegido):
            for c in candidatos:
                if sabe_de_gente(c):
                    elegido = c
                    break
        def columna_de_gente(c):
            if c["clase"] != "columna" or c["col"] not in c["cols"]:
                return False
            k = c["cols"].index(c["col"])
            return any(f[k] in nombres for f in c["filas"])

        # «Quien ... mas» pide un numero. Si la mejor candidata NO SABE dar
        # uno se busca la primera que sepa. Con tres frenos, y los tres
        # costaron una respuesta mala: no se aplica si hay un FILTRO puesto
        # -- ahi la respuesta es la fila, no un maximo --, ni si la columna
        # elegida YA es de nombres: «en la partida 7 quien gano» se iba de
        # `gano`, que es la respuesta literal, a `puestos_ganados`.
        if ((pistas & _PISTAS_QUIEN) and not persona
                and not elegido["filtro"] and not columna_de_gente(elegido)
                and not sabe_contar(elegido)):
            for c in candidatos:
                if c["clase"] == "columna" and sabe_contar(c):
                    elegido = c
                    break
        # Si se pregunta por alguien, la vista elegida tiene que TENERLO --
        # pero solo se busca otra si la que gana NO lo tiene. Buscando siempre,
        # la primera con esa persona se llevaba por delante a la que mejor
        # puntuaba: «cuanto mineral ha producido elGato» acababa en «El
        # ladron», que tambien tiene una columna `mineral` y tambien tiene a
        # elGato, y contestaba 3 en vez de 34.
        def _tiene_a(c):
            if "quien" not in c["cols"]:
                return False
            j2 = c["cols"].index("quien")
            return any(f[j2] == persona for f in c["filas"])

        if persona and not _tiene_a(elegido):
            for c in candidatos:
                if _tiene_a(c):
                    elegido = c
                    break

        v, cols, filas = elegido["v"], elegido["cols"], elegido["filas"]
        i, col, filtro = elegido["i"], elegido["col"], elegido["filtro"]
        agrupada = False

        def redondo(x):
            return round(x, 1) if isinstance(x, float) else x

        # 3. Filtrar y contestar. El numero sale de la tabla que se ensena
        #    debajo, asi que siempre se puede comprobar sin fiarse de esto.
        if persona and "quien" in cols:
            filas = [f for f in filas if f[cols.index("quien")] == persona] or filas
        pareja_vacia = False
        if segunda and "a_quien" in cols:
            # SIN vuelta atras. Si la pareja no tiene filas, la respuesta es
            # cero, no las filas de uno de los dos: «lobo le ha puesto el
            # ladron a bruno» contestaba 19 -- todas las de lobo con
            # cualquiera -- porque a Bruno no le ha puesto ninguna.
            filas = [f for f in filas if f[cols.index("a_quien")] == segunda]
            pareja_vacia = not filas
        if filtro:
            k, valor, como = filtro
            filas = [f for f in filas if f[k] == valor]

        if filtro:
            # Preguntando POR un valor: «quien puso el ladron en el 11». La
            # respuesta es quien sale en esas filas, no una cuenta.
            k, valor, como = filtro
            medida = None
            if col and col not in _EJES and numero_col(cols, filas, cols.index(col)):
                medida = cols.index(col)
            else:
                medida = mejor_medida(cols, filas, utiles)
            if "quien" not in cols and col and filas:
                # Sin columna de personas pero con una columna preguntada:
                # «en la partida 7 quien gano» -> `gano` de esa fila.
                sueltos = [str(f[cols.index(col)]) for f in filas
                           if f[cols.index(col)] is not None]
                frase = ("En el %s: %s." % (valor, ", ".join(sueltos[:5]))
                         if sueltos else
                         "En el %s no hay %s." % (valor, col.replace("_", " ")))
            elif "quien" in cols and filas:
                j = cols.index("quien")
                if medida is not None:
                    vivos = [f for f in filas if numero(f[medida]) and f[medida]]
                    if not vivos:
                        frase = "En el %s no hay ninguno: %s es 0." % (
                            valor, cols[medida].replace("_", " "))
                    elif len(vivos) == 1:
                        frase = "%s, en el %s (%s: %s)." % (
                            vivos[0][j], valor,
                            cols[medida].replace("_", " "), vivos[0][medida])
                    else:
                        vivos.sort(key=lambda f: -f[medida])
                        frase = "En el %s: %s." % (valor, ", ".join(
                            "%s (%s)" % (f[j], f[medida]) for f in vivos[:5]))
                else:
                    frase = "En el %s: %s." % (valor, ", ".join(
                        sorted(set(str(f[j]) for f in filas))[:5]))
            elif filas:
                k2 = mejor_medida(cols, filas, utiles)
                if k2 is not None and numero(filas[0][k2]):
                    frase = "En el %s: %s %s." % (
                        valor, filas[0][k2], cols[k2].replace("_", " "))
                else:
                    frase = "Lo del %s esta aqui debajo." % valor
            else:
                frase = "En el %s no hay nada en «%s»." % (valor, v["titulo"])
        elif pareja_vacia:
            frase = "%s a %s: ninguna vez, en «%s»." % (persona, segunda,
                                                        v["titulo"])
        elif segunda and "a_quien" in cols and filas:
            # Los dos nombrados y la vista de parejas: la fila ya esta
            # filtrada, solo falta decir el numero. Sin esto se contestaba
            # «lo que preguntas esta en El ladron uno a uno», teniendo la
            # fila delante.
            k = (cols.index(col) if col and col not in _EJES and col in cols
                 else mejor_medida(cols, filas, utiles))
            if k is None:
                frase = "Lo de %s con %s esta aqui debajo." % (persona, segunda)
            else:
                total = sum(f[k] for f in filas if numero(f[k]))
                frase = "%s a %s: %s de %s." % (
                    persona, segunda, total, cols[k].replace("_", " "))
        elif elegido["clase"] == "vista":
            frase = ("Eso no lo tengo en una columna, pero lo que preguntas "
                     "esta en «%s», aqui debajo." % v["titulo"])
        elif elegido["clase"] == "filas":
            frase = ("%s: %d en «%s»." % (persona, len(filas), v["titulo"])
                     if persona else "%d, en «%s»." % (len(filas), v["titulo"]))
        else:
            legible = col.replace("_", " ")
            valores = [f[i] for f in filas if numero(f[i])]
            if persona and "quien" in cols and not filas:
                frase = "%s no sale en «%s»." % (persona, v["titulo"])
            elif (col in _EJES and not persona
                  and (pistas & (_PISTAS_QUIEN | _PISTAS_TOTAL))):
                # Lo preguntado es un eje. Si la vista tiene MAS de una fila
                # por valor del eje se agrupa antes: si no, la respuesta seria
                # el maximo de una fila suelta y no el de la mesa.
                if not persona and len(set(f[i] for f in filas)) < len(filas):
                    c2, f2 = _agrupar(cols, filas, col)
                    if c2:
                        cols, filas, i = c2, f2, 0
                        agrupada = True
                k = mejor_medida(cols, filas, utiles)
                if k is None:
                    agrupada = False
                    frase = "Lo tienes en «%s», aqui debajo." % v["titulo"]
                else:
                    al_reves = _mira_al_que_menos(pistas)
                    utiles_f = [f for f in filas if numero(f[k])]
                    mejor = (min(utiles_f, key=lambda f: f[k]) if al_reves
                             else max(utiles_f, key=lambda f: f[k]))
                    frase = "%s con %s %s: %s, con %s." % (
                        legible.capitalize(), "menos" if al_reves else "mas",
                        cols[k].replace("_", " "), mejor[i], mejor[k])
            elif segunda and "a_quien" in cols and valores:
                frase = "%s a %s: %s de %s." % (persona, segunda,
                                                redondo(sum(valores)), legible)
            elif persona and not valores:
                # Columna de texto y una persona: se lee la lista.
                sueltos = [str(f[i]) for f in filas if f[i] is not None]
                frase = "%s, %s: %s" % (persona, legible,
                                        ", ".join(sueltos[:8]) or "nada")
            elif persona and col in _NO_SE_SUMAN and len(valores) > 1:
                # Turnos, medias y porcentajes NO se suman. «En que turno hizo
                # su primera ciudad elGato» contestaba 131, que es la suma de
                # cinco turnos y no significa nada.
                frase = "%s, %s: %s  (una por partida)" % (
                    persona, legible, ", ".join(str(redondo(x))
                                                for x in valores))
            elif (persona and valores and len(filas) > 1
                  and pistas & _PISTAS_QUIEN
                  and ("con_quien" in cols or "a_quien" in cols)):
                # «CON QUIEN ha hecho mas tratos carla» contestaba «carlarr:
                # 39 de tratos», que es la suma de sus cuatro filas. El numero
                # esta bien y no es lo que se preguntaba: la pregunta pedia un
                # NOMBRE y la tabla ya lo tenia delante.
                #
                # Pasaba porque la rama de «hay una persona» iba antes que la
                # de «piden un quien», asi que en cuanto se nombraba a alguien
                # ya no se miraba que se preguntaba de esa persona. Con una
                # vista de parejas eso se come justo la mitad interesante.
                cual = "con_quien" if "con_quien" in cols else "a_quien"
                como = cual.replace("_", " ")
                j = cols.index(cual)
                al_reves = _mira_al_que_menos(pistas)
                utiles_f = [f for f in filas if numero(f[i])]
                mejor = (min(utiles_f, key=lambda f: f[i]) if al_reves
                         else max(utiles_f, key=lambda f: f[i]))
                frase = "%s, %s %s %s: %s, con %s de %s." % (
                    persona, como, "menos" if al_reves else "mas", legible,
                    mejor[j], redondo(mejor[i]), redondo(sum(valores)))
            elif persona:
                frase = "%s: %s de %s." % (persona, redondo(sum(valores)),
                                           legible)
                if len(valores) > 1:
                    frase += "  (sumando %d filas)" % len(valores)
                if col not in _RECURSOS:
                    frase += _y_que_recursos(cols, filas)
            elif pistas & _PISTAS_QUIEN and "quien" in cols and valores:
                j = cols.index("quien")
                # «Menos» no es «mas» al reves de decirlo: es el otro extremo.
                # «Quien ha tardado MENOS en poner una ciudad» contestaba con
                # el que mas tardo. Y los NULL se quedan fuera: en una columna
                # de turnos, NULL es «no llego a hacerlo», no el turno 0.
                al_reves = _mira_al_que_menos(pistas)
                utiles_f = [f for f in filas if numero(f[i])]
                # Ordenar por la columna que toca, no por la preguntada. Ver
                # `_ORDENAR_POR`: `suerte` con nueve casillas de una partida
                # dispara el porcentaje, y la vista ya trae la desviacion al
                # lado. Se ordena por ella y se contesta con las dos, que es
                # lo que deja ver POR QUE gana ese.
                por = _ORDENAR_POR.get(col)
                k = cols.index(por) if por and por in cols else i
                utiles_f = [f for f in utiles_f if numero(f[k])]
                if not utiles_f:
                    k = i
                    utiles_f = [f for f in filas if numero(f[i])]
                mejor = (min(utiles_f, key=lambda f: f[k]) if al_reves
                         else max(utiles_f, key=lambda f: f[k]))
                # EN UNA VISTA DE PAREJAS, EL NOMBRE SON DOS. Sin esto, «cual
                # es el saldo con cada uno» contestaba «el que mas neto:
                # LoboEstepario, con 4» -- y el 4 no es de LoboEstepario, es
                # de LoboEstepario CON carlarr. Una fila de pareja no tiene
                # dueno unico, asi que decir solo la mitad izquierda es dar un
                # numero que no se puede volver a encontrar en la tabla.
                #
                # La rama de arriba ya lo hacia bien, pero solo cuando la
                # pregunta nombraba a alguien; sin nombre se caia aqui y se
                # perdia la otra mitad.
                quienes = mejor[j]
                for otro, palabra in (("con_quien", "con"), ("a_quien", "a")):
                    if otro in cols and mejor[cols.index(otro)] is not None:
                        quienes = "%s %s %s" % (mejor[j], palabra,
                                                mejor[cols.index(otro)])
                        break
                frase = "El que %s %s: %s, con %s." % (
                    "menos" if al_reves else "mas", legible, quienes, mejor[i])
                if k != i:
                    frase = ("El que %s %s: %s, con %s (%s de %s)." % (
                        "menos" if al_reves else "mas", legible, quienes,
                        mejor[i], mejor[k], cols[k].replace("_", " ")))
                    # Y si NADIE se sale del margen, eso es la respuesta: la
                    # tabla ordenada tiene siempre un primero, y llamarle
                    # «el que mas suerte» a una diferencia que cabe en el
                    # error es inventarse un hallazgo.
                    if "margen" in cols and abs(numero(mejor[k]) or 0) < 2:
                        frase += ("  Aunque con estos datos no se sale nadie "
                                  "del margen: la diferencia cabe en el error.")
                if col not in _RECURSOS:
                    frase += _y_que_recursos(cols, [mejor])
            elif pistas & _PISTAS_TOTAL and valores and col in _NO_SE_SUMAN:
                # «Cuantas casillas tiene el tablero» sumaba las de las
                # catorce partidas: 182. La cuenta esta bien y el numero no
                # existe. Se dicen los valores distintos, que es la respuesta.
                distintos = sorted(set(redondo(x) for x in valores))
                frase = "%s: %s%s" % (
                    legible.capitalize(),
                    " o ".join(str(x) for x in distintos[:4]),
                    "" if len(distintos) <= 4 else ", y mas")
            elif pistas & _PISTAS_TOTAL and valores:
                frase = "En total, %s de %s." % (redondo(sum(valores)), legible)
            elif not valores:
                # Columna de texto. Con una persona delante se puede leer;
                # sin nadie, una lista de veinte nombres no contesta nada.
                if persona:
                    sueltos = [str(f[i]) for f in filas if f[i] is not None][:6]
                    frase = "%s, %s: %s" % (persona, legible,
                                            ", ".join(sueltos) or "nada")
                else:
                    frase = ("Eso no sale en un numero. Lo tienes en «%s», "
                             "aqui debajo." % v["titulo"])
            else:
                frase = "Lo que preguntas esta en «%s», columna «%s»." % (
                    v["titulo"], legible)

        if agrupada:
            frase += "  (juntando las filas de «%s»)" % v["titulo"]

        otras, vistos = [], {(v["nombre"], col)}
        for c in candidatos[1:]:
            clave = (c["v"]["nombre"], c["col"])
            if clave in vistos:
                continue
            vistos.add(clave)
            otras.append({"vista": c["v"]["nombre"], "titulo": c["v"]["titulo"],
                          "columna": c["col"] or ""})
            if len(otras) == 4:
                break

        return {"respuesta": frase, "vista": v["nombre"],
                "titulo": v["titulo"], "columna": col, "persona": persona,
                "columnas": cols, "filas": [list(f) for f in filas[:40]],
                "de_donde": "py db/vistas.py --ver %s%s"
                            % (v["nombre"],
                               "" if ambito == "amigos" else " --ambito " + ambito),
                "otras": otras}
    except sqlite3.Error as e:
        return {"error": "no se ha podido leer la base: %s" % e}
    finally:
        conn.close()


def numero_col(cols, filas, k):
    return any(isinstance(f[k], (int, float)) and not isinstance(f[k], bool)
               for f in filas)


def mejor_medida(cols, filas, utiles):
    """De las columnas que se pueden contar, la que mas se parezca a lo
    preguntado -- y antes que nada, una que se pueda SUMAR.

    «Que carta sale mas del mazo» contestaba «Caballero, con 56» leyendo
    `en_el_mazo`, que es el porcentaje que el mazo LLEVA DENTRO: ni siquiera
    es lo que salio, y encima parecia una cuenta."""
    medidas = [k for k, c in enumerate(cols)
               if c not in _EJES and c not in _NO_SON_RESPUESTA
               and numero_col(cols, filas, k)]
    if not medidas:
        return None
    return max(medidas, key=lambda k: (cols[k] not in _NO_SE_SUMAN,
                                       _cuanto(utiles, _catalogo(cols[k])),
                                       -k))


def _dia_es(iso):
    """`2026-08-31` -> `31/08/2026`. Solo para ensenar.

    En la base la fecha se queda en ISO, y no es capricho: es la unica forma
    que se ordena bien como texto, y media docena de vistas hacen
    `ORDER BY dia`. Con `31/08/2026` el orden alfabetico pondria el 31 de
    agosto antes que el 1 de septiembre -- y el resultado pareceria correcto,
    que es lo peor que le puede pasar a un dato.
    """
    m = re.match(r"^(\d{4})-(\d{2})-(\d{2})$", str(iso or ""))
    return "%s/%s/%s" % (m.group(3), m.group(2), m.group(1)) if m else iso


def catalogo(idioma=None):
    """Que vistas hay y que partidas se pueden elegir."""
    _vistas_al_dia()
    conn = _abrir_base()
    if conn is None:
        return {"error": "Todavia no hay base de datos. Guarda una partida "
                         "primero, en el paso 2.", "vistas": [], "partidas": []}
    try:
        faltan = [v["nombre"] for v in _vistas.VISTAS
                  if v["nombre"] not in _vistas.las_que_hay(conn)]
        # Cuantos jugaban va en la etiqueta de cada partida. Sin esto, para
        # saber si una era de cuatro o de seis habia que abrirla y contar --
        # y con el tablero de 5-6 (30 casillas, a 12 puntos en vez de 10) es
        # justo lo primero que se quiere saber al elegirla.
        partidas = [{"id": r[0],
                     "texto": "%s  ·  %d jug. a %d  ·  %s  ·  gano %s" % (
                        _dia_es(r[1]), r[4], r[5],
                        "amigos" if r[3] else "con la IA", r[2] or "?"),
                     "con_amigos": bool(r[3]),
                     "jugadores": r[4]}
                    for r in conn.execute(
                        "SELECT game_id, dia, gano, con_amigos, jugadores, "
                        "a_puntos FROM partidas ORDER BY game_id DESC")]             if not faltan else []
        return {
            # Agrupadas y en el orden en que se enseñan. Se manda ya ordenado
            # y no la lista cruda con una etiqueta: si el orden lo decidiera
            # el navegador, habría dos sitios donde cambiarlo.
            "vistas": [{"nombre": v["nombre"],
                        "titulo": idiomas.frase(v["titulo"], idioma),
                        "que": idiomas.frase(v["que"], idioma),
                        "vacio": idiomas.frase(v.get("vacio"), idioma),
                        "grupo": idiomas.frase(titulo, idioma)}
                       for titulo, vistas in _vistas.por_grupos()
                       for v in vistas],
            "partidas": partidas,
            # Los ambitos los manda el servidor y no los escribe la pagina:
            # si el dia que se anada uno hay que tocar dos sitios, el que se
            # olvide sera este.
            "ambitos": [{"id": a,
                         "texto": idiomas.frase(
                             _vistas.NOMBRE_DEL_AMBITO[a], idioma)}
                        for a in _vistas.AMBITOS],
            "mesas": [{"id": m,
                       "texto": idiomas.frase(
                           _vistas.NOMBRE_DE_LA_MESA[m], idioma)}
                      for m in _vistas.MESAS],
            "faltan": faltan,
        }
    except sqlite3.Error as e:
        return {"error": "no se ha podido leer la base: %s" % e,
                "vistas": [], "partidas": []}
    finally:
        conn.close()


# Un nombre provisional es el que se pone solo al ver una cuenta nueva:
# `jugador_` + los ocho primeros caracteres del identificador. Sale de
# `importar.nombre_automatico`, y esto lo reconoce por el prefijo en vez de
# preguntarselo a nadie -- es un detalle de ahi que no merece un campo en la
# base, pero si merece que el panel lo enseñe distinto: es justo lo que hay
# que arreglar.
PROVISIONAL = "jugador_"


def quitar_partida(gid, motivo=""):
    """Saca una partida del historico. Es lo unico del panel que borra.

    Se apoya en `db/quitar_partidas.py` en vez de repetir el borrado aqui:
    son diecisiete tablas y una de ellas (`building_tiles`) no tiene
    `game_id`, hay que ir por los edificios. Dos copias de eso se separan el
    dia que se anada una tabla, y la que se quede corta deja huerfanas que no
    se ven.

    Tres cosas que hace y que desde el boton no se ven:

      - **copia la base antes**, a `copias/`. No hay deshacer.
      - **apunta la carpeta en `mod_ignoradas`**, que es lo que impide que la
        siguiente pasada del importador la vuelva a meter. Borrar las filas y
        ya esta seria un borrado que se deshace solo.
      - **no toca las capturas**. Quitar una partida del historico no le hace
        perder un recorte a la vision.
    """
    import sqlite3 as _sq
    if not os.path.isfile(BASE_DATOS):
        return {"ok": False, "error": "no hay base de datos"}
    try:
        gid = int(gid)
    except (TypeError, ValueError):
        return {"ok": False, "error": "eso no es un numero de partida"}
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    try:
        from db import quitar_partidas as qp
    except Exception as e:
        return {"ok": False, "error": "no puedo cargar db/quitar_partidas: %s" % e}
    conn = _sq.connect(BASE_DATOS)
    try:
        fila = conn.execute("SELECT game_id FROM games WHERE game_id=?",
                            (gid,)).fetchone()
        if not fila:
            return {"ok": False, "error": "no existe la partida %d" % gid}
        descripcion = qp.ficha(conn, gid)
        copia = qp.copia_de_seguridad()
        qp.quitar(conn, gid, motivo or "quitada desde el panel")
        conn.commit()
    except Exception as e:
        conn.rollback()
        return {"ok": False, "error": str(e)}
    finally:
        conn.close()
    return {"ok": True, "partida": gid, "ficha": descripcion, "copia": copia}


def gente():
    """Quien es quien, para la lista del panel.

    Lo mismo que `importar.py --quien` escribe en la consola, pero en JSON.
    Se lee de la base en SOLO LECTURA: aqui no se toca nada, poner el nombre
    va por el otro camino."""
    conn = _abrir_base()
    if conn is None:
        return {"error": "Todavia no hay base de datos. Guarda una partida "
                         "primero, en el paso 2.", "gente": []}
    try:
        filas = conn.execute(
            "SELECT network_id, display_name, is_bot FROM mod_identities "
            "ORDER BY is_bot, display_name").fetchall()
        salida = []
        for red, nombre, es_bot in filas:
            n = conn.execute(
                "SELECT COUNT(*) FROM players p JOIN games g "
                "ON g.game_id = p.game_id "
                "WHERE g.source='mod' AND p.name = ?", (nombre,)).fetchone()[0]
            salida.append({"red": red, "nombre": nombre,
                           "es_ia": bool(es_bot), "partidas": n,
                           "provisional": bool(nombre.startswith(PROVISIONAL))})
        return {"gente": salida}
    except sqlite3.Error as e:
        # Lo tipico: una base de antes de que existiera `mod_identities`.
        return {"error": "no se ha podido leer quien es quien: %s" % e,
                "gente": []}
    finally:
        conn.close()


def poner_nombre(red, nombre):
    """Ponerle nombre a una cuenta, por el mismo camino que la consola.

    Llama a `importar.py --llamar`, que es donde vive esa logica: renombra la
    identidad, arregla las partidas YA guardadas -- si no, el historico se
    partiria en dos personas -- y limpia el nombre provisional. Reescribirlo
    aqui seria tener dos versiones de una operacion que toca el historico
    entero, y la que se quedaria vieja seria esta.

    El identificador se comprueba contra los que hay antes de salir de aqui.
    No es por el shell -- la orden va como lista, sin shell de por medio --
    sino para que un identificador mal escrito de un error claro en vez de
    arrancar un proceso que no va a hacer nada."""
    nombre = (nombre or "").strip()
    if not nombre:
        return False, "hace falta un nombre."
    if len(nombre) > 40 or any(c in nombre for c in "\r\n\t"):
        return False, "ese nombre no vale (max 40 caracteres, sin saltos)."
    if nombre.startswith(PROVISIONAL):
        return False, "ese es el nombre provisional, no uno de verdad."
    conocidos = gente().get("gente", [])
    fila = next((g for g in conocidos if g["red"] == red), None)
    if fila is None:
        return False, "no conozco el identificador %r." % red
    if fila["nombre"] == nombre:
        return False, "ya se llamaba asi."
    return tarea.arrancar(
        "ponerle nombre a %s" % red,
        [sys.executable, "-u", "mod_verdad/importar.py", "--llamar",
         red, nombre])


def titulares(idioma=None):
    """Los titulares de ahora mismo, recalculados en cada visita.

    Se piden a `db/titulares.py`, que a su vez lee las MISMAS vistas que
    pinta la tabla de abajo. Aqui no hay ni una consulta: el dia que el
    panel se hiciera la suya, el titular y la tabla podrian decir cosas
    distintas y no habria forma de saber cual esta mal."""
    _vistas_al_dia()
    conn = _abrir_base()
    if conn is None:
        return {"error": "Todavia no hay base de datos."}
    try:
        return _titulares.calcular(conn, idioma=idioma)
    except sqlite3.Error as e:
        return {"error": "%s  --  prueba con: py db/vistas.py --crear" % e}
    finally:
        conn.close()


def ver_vista(nombre, partida=None, ambito=None, mesa=None, idioma=None):
    # Releer aqui tambien, y no solo en `catalogo()`. Teniendolo en un solo
    # sitio pasaba lo peor que puede pasar: la lista de vistas se refrescaba
    # -- o sea que la pagina PARECIA al dia -- y la consulta seguia siendo la
    # vieja. Una vista recien cambiada devolvia 0 filas y eso se lee como «no
    # hay nada», que es una respuesta, no un error. Nadie iba a sospechar.
    _vistas_al_dia()
    conn = _abrir_base()
    if conn is None:
        return {"error": "Todavia no hay base de datos."}
    try:
        # Sin ambito y sin partida, AMIGOS. La garantia vive aqui y no en la
        # pagina: `partidas` y `jugadores` se guardan sin filtrar porque las
        # demas se apoyan en ellas, asi que su forma «de siempre» SI trae la
        # IA. Si el panel pudiera pedirla -- una URL a mano, un dia que el
        # javascript no mande el parametro -- saldrian los bots en la tabla
        # sin que nadie los haya pedido.
        if partida is None and ambito is None:
            ambito = "amigos"
        columnas, filas = _vistas.consultar(conn, nombre, partida, ambito,
                                            mesa)
        # `columnas` son los nombres de SQL y NO se tocan: con ellos se
        # ordena, se filtra y se casan las fichas de `db/columnas.py`.
        # `etiquetas` es lo que se PINTA encima, que es otra cosa y sí cambia
        # de idioma. Mezclarlas rompería el orden de las columnas en cuanto
        # alguien tradujera una.
        return {"columnas": columnas,
                "etiquetas": [idiomas.columna(c, idioma) for c in columnas],
                "filas": [list(f) for f in filas]}
    except ValueError:
        return {"error": "No existe el ambito '%s' o la mesa '%s'."
                         % (ambito, mesa)}
    except KeyError:
        return {"error": "No existe la vista '%s'." % nombre}
    except sqlite3.Error as e:
        # Lo mas probable: las vistas no estan creadas todavia.
        return {"error": "%s  --  prueba con: py db/vistas.py --crear" % e}
    finally:
        conn.close()


# --- acciones ----------------------------------------------------------

def poner_mod(encendido):
    """Enciende o apaga llamando al interruptor de siempre.

    Con -ExecutionPolicy Bypass porque si no, en una instalacion de Windows
    recien puesta, PowerShell se niega a correr el .ps1 y el error que sale
    no dice nada util."""
    if not os.path.isfile(INTERRUPTOR):
        return False, "no encuentro %s" % INTERRUPTOR
    try:
        r = subprocess.run(
            ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass",
             "-File", INTERRUPTOR, "on" if encendido else "off",
             "-python", sys.executable],
            cwd=RAIZ, capture_output=True, timeout=120,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    except Exception as e:
        return False, "no se ha podido ejecutar el interruptor: %s" % e
    salida = (r.stdout + r.stderr).decode("utf-8", "replace").strip()
    return r.returncode == 0, salida


# Una sola API, no dos.
#
# La tentacion era montar dos paneles: el de trabajar, con todo, y otro con
# lo poco que le hace falta a quien se descargue esto. Pero el 90% es comun
# --el estado, las vistas, importar, quitar, la caja de preguntas-- y ese 90%
# se separa: arreglas algo en uno y en el otro sigue mal. Ya ha pasado dos
# veces en este proyecto (dos listas de tablas al borrar, dos extractores de
# sufijos en el importador) y las dos veces el fallo fue callado.
#
# Asi que el panel es uno y sabe lo que le falta. Una tarea es de la mitad de
# la vision si arranca algo de `red/` o `mirar.py`, y eso NO es una lista
# escrita a mano: se mira la orden. Si esos ficheros no estan --porque quien
# clono el repositorio no se llevo esa mitad-- los botones no salen, sin
# configurar nada.
#
# Y `--como-usuario` fuerza esa vista teniendolo todo, que es la unica forma
# de ver lo que ve otro sin borrarse los ficheros.
def _script_de(orden):
    """El fichero que una tarea arranca, o None si no se sabe."""
    for i, trozo in enumerate(orden):
        if trozo == "-m" and i + 1 < len(orden):
            return os.path.join(RAIZ, orden[i + 1].replace(".", os.sep) + ".py")
        if isinstance(trozo, str) and trozo.endswith(".py"):
            return os.path.join(RAIZ, trozo)
    return None


# Lo que se ve al descargarse esto. Esto SI es una lista escrita, y no por
# pereza: es una decision, no un dato que se pueda deducir del codigo. Se
# intento deducir --«todo lo de red/ y mirar.py es de trabajar»-- y no vale:
# «Mirar la pantalla» es de red/ y es justo lo que mas se quiere ensenar.
#
# La red esta en el lado seguro. Lo que NO este en esta lista queda fuera, asi
# que una tarea nueva que a nadie se le ocurra anadir aqui se queda dentro, no
# se publica sola. Hay una prueba que ademas exige que todo nombre de aqui
# exista de verdad: una errata dejaria el boton escondido sin decir nada.
A_LA_VISTA = frozenset((
    "instalar",   # dejar el mod listo -- sin esto no hay nada
    "importar",   # guardar las partidas en la base
    "analizar",   # el informe largo
    "mirar",      # leer el tablero de la pantalla
))


def _es_de_desarrollo(orden):
    """¿Se queda fuera? Por descarte: lo que no esta en `A_LA_VISTA`."""
    for nombre, (_titulo, suya) in TAREAS.items():
        if suya is orden:
            return nombre not in A_LA_VISTA
    return True


TAREAS = {
    "comprobar": ("comprobar lo grabado",
                  [sys.executable, "-u", "mod_verdad/comprobar.py"]),
    "dataset": ("preparar los datos",
                [sys.executable, "-u", "-m", "red.dataset"]),
    # El ciclo entero en uno: convertir lo grabado, EXAMINAR el modelo de
    # antes con la partida nueva y solo despues entrenar con ella. Es lo
    # unico que hay que tocar despues de jugar; lo demas de esta lista son
    # los pasos sueltos, por si hace falta uno solo.
    "rutina": ("el ciclo entero (convertir, examinar, entrenar)",
               [sys.executable, "-u", "-m", "red.rutina"]),
    "historial": ("como va mejorando",
                  [sys.executable, "-u", "-m", "red.rutina", "--historial"]),
    # Antes habia dos: una medía la vision por color y otra las dos a la vez.
    # Retirada la vision, queda una: cuanto acierta la red.
    "medir": ("medir la red, foto a foto",
              [sys.executable, "-u", "-m", "red.evaluar", "--red", MODELO_MEDIDO]),
    # Y la que de verdad importa: el tablero final acumulado, que es lo que
    # tendria delante quien juega. Ver red/acumular.py.
    "tablero": ("medir el tablero entero, como lo leeria jugando",
                [sys.executable, "-u", "-m", "red.acumular", "--todas"]),
    # Leer el tablero de la pantalla mientras se juega. No lleva colores: se
    # leen de los paneles de jugador (red/mesa.py), que es lo unico que
    # funciona jugando online -- los reparte el juego al empezar la partida,
    # asi que no hay nada que marcar antes.
    #
    # Va con el modelo de jugar, que es el que toca. Durante unas horas del 21
    # de agosto llevo `--red MODELO_MEDIDO` a la fuerza, porque el de jugar
    # inventaba 16 piezas de 90 leyendo de la pantalla; eso era la receta de
    # entrenamiento sin senal de parada (ver `entrenar_todo`). Arreglada la
    # receta y reentrenado, el mismo camino da 0 inventadas y 80 de 81, asi que
    # el apano sobra.
    "mirar": ("mirar la pantalla",
              [sys.executable, "-u", "-m", "mirar"]),
    # El mismo camino de jugar, pero sobre una partida que el modelo no vio y
    # con las capturas guardadas en vez de la pantalla. Es lo unico que dice
    # cuanto acierta LEYENDO DE LA PANTALLA sin tener que jugar una partida:
    # el examen de "medir el tablero entero" da por buenos el recorte y el
    # anclaje, porque se los da hechos el dataset.
    "ensayo": ("probar la lectura en vivo sobre una partida grabada",
               [sys.executable, "-u", "-m", "mirar", "--red", MODELO_MEDIDO,
                "--desde", "apartada", "--sin-ventana"]),
    # Y lo que no son piezas: el ladron y los dados. Va aparte porque no usa
    # la red -- son medidas del pixel -- y porque se mide contra TODAS las
    # partidas grabadas, no solo contra las apartadas: aqui no hay nada
    # entrenado que pueda haberse aprendido las respuestas.
    "mesa": ("medir el ladron y los dados contra lo que dice el mod",
             [sys.executable, "-u", "-m", "red.mesa", "--medir", "--limite", "250"]),
    "entrenar": ("entrenar (apartando una partida para medir)",
                 [sys.executable, "-u", "-m", "red.entrenar"]),
    # 20 vueltas. Se probo bajarlo a 10 y se volvio a subir a peticion de
    # Mario, que vio la nota subiendo todavia en la 14. Ojo con esa nota: con
    # --con-todo no hay partida apartada, asi que se calcula sobre recortes ya
    # estudiados y sube casi siempre -- no distingue aprender de memorizar.
    #
    # YA HAY FORMA DE MEDIRLO, y sale mal. El ensayo sobre capturas (mirar.py
    # --desde) pasa las dos partidas apartadas por el camino de jugar, que es
    # el unico que importa. El 21 de agosto de 2026, los dos modelos que habia
    # en disco -- mismo tamano, mismo recorte, mismo vocabulario, y el de
    # jugar ademas entrenado CON las dos partidas:
    #
    #                              bien      inventadas
    #     red_de_sitios.pt (25 v.)  77/90        16
    #     medido.pt (para en la 3)  87/90         2
    #
    # Ocho veces mas piezas inventadas, y una inventada no se quita nunca. El
    # de medir gana pese a examinarse con partidas que no vio, o sea que la
    # comparacion esta sesgada A FAVOR del de jugar y aun asi pierde. En el
    # examen offline los dos sacan 57/58 sobre esa partida: la diferencia solo
    # aparece leyendo de la pantalla, que es justo donde los recortes no son
    # los que se memorizaron.
    #
    # O sea que el problema no son las 20 vueltas por si solas, es que con
    # --con-todo no hay nada donde parar. Lo que hay que arreglar es la
    # receta: apartar tambien aqui para tener senal de parada, y despues
    # entrenar con todo el numero de vueltas que esa senal diga.
    "entrenar_todo": ("reentrenar con todo (para jugar)",
                      [sys.executable, "-u", "-m", "red.entrenar", "--con-todo",
                       "--vueltas", "20"]),
    "pruebas": ("pruebas de la red",
                [sys.executable, "-u", "-m", "red.pruebas"]),
    "instalar": ("dejar el mod listo",
                 [sys.executable, "-u", "mod_verdad/instalar.py"]),
    "importar": ("guardar las partidas en la base de datos",
                 [sys.executable, "-u", "mod_verdad/importar.py"]),
    "analizar": ("el informe de las partidas",
                 [sys.executable, "-u", "analizar.py"]),
    "pruebas_datos": ("pruebas de las vistas",
                      [sys.executable, "-u", "-m", "db.pruebas"]),
    "vistas": ("rehacer las vistas de la base",
               [sys.executable, "-u", "db/vistas.py", "--crear"]),
}


def empezar_a_grabar():
    """Enciende el mod y arranca recopilar.py, en ese orden.

    El orden no es cosmetico: `doorstop_config.ini` se lee cuando arranca el
    juego, asi que encenderlo con Catan ya abierto no hace nada hasta la
    siguiente vez. Y recopilar.py tiene que estar antes que la partida
    porque a una accion ya apuntada no se le puede hacer la foto despues."""
    if _recopilando():
        return False, "ya se esta grabando."
    ok, salida = poner_mod(True)
    if not ok:
        return False, salida or "no se ha podido encender el mod."
    ok, error = grabacion.arrancar(
        "grabando la partida", [sys.executable, "-u", "mod_verdad/recopilar.py"])
    if not ok:
        return False, error
    return True, None


def solo_encender_el_mod():
    """Enciende el mod sin arrancar el grabador de capturas.

    El mod escribe su fichero el solo en cuanto el juego arranca con el
    plugin cargado; recopilar.py no hace falta para eso. Lo que hace
    recopilar es sacar una foto por accion, y eso SOLO sirve para entrenar la
    red: son 2 GB por partida (16 GB en las ocho primeras) que no se van a
    mirar si la partida es de jugar, no de entrenar.

    El mismo boton de parar vale para las dos cosas: dejar_de_grabar apaga el
    mod aunque no hubiera nada grabando."""
    if _recopilando() or grabacion.vivo:
        return False, ("ya se esta grabando con capturas. Para eso primero si "
                       "querias solo el mod.")
    ok, salida = poner_mod(True)
    if not ok:
        return False, salida or "no se ha podido encender el mod."
    return True, None


def dejar_de_grabar():
    """Para la grabacion y apaga el mod.

    Se para con el fichero `.parar` y no matando el proceso: asi recopilar
    sale por su propio pie, cierra el indice y quita su candado. Si en cinco
    segundos no ha salido, entonces si se le mata -- pero eso ya seria un
    fallo, no lo normal."""
    if _recopilando() or grabacion.vivo:
        try:
            open(PARAR, "w", encoding="utf-8").write("panel\n")
        except OSError as e:
            return False, "no se ha podido pedir la parada: %s" % e
        for _ in range(50):
            if not grabacion.vivo and not _recopilando():
                break
            time.sleep(0.1)
        if grabacion.vivo:
            grabacion.matar()
    ok, salida = poner_mod(False)
    if not ok:
        return False, salida or "la grabacion se ha parado pero el mod NO se ha apagado."
    return True, None


# --- la pagina ---------------------------------------------------------

PAGINA = r"""<!doctype html>
<html lang="es"><head><meta charset="utf-8">
<title>Catan Tracker</title>
<meta name="viewport" content="width=device-width,initial-scale=1">
<style>
/* CLARO por defecto y OSCURO en un solo bloque, no dos.
   Lo natural seria poner el oscuro tambien dentro de un
   `@media (prefers-color-scheme:dark)`, y entonces la paleta estaria escrita
   dos veces: la del sistema y la del boton. Dos copias de ocho colores que un
   dia dejan de ser la misma. En vez de eso el tema lo pone SIEMPRE el
   atributo `data-tema`, y quien lo decide la primera vez es el guioncillo de
   ahi abajo, que mira lo que prefiere el sistema. Un sitio, una paleta. */
:root{--fondo:#f6f5f2;--papel:#fff;--tinta:#1c1b19;--suave:#6b6862;
      --borde:#dcd8d0;--acento:#2f6f4e;--alerta:#b3261e;--aviso:#8a5a00}
:root[data-tema="oscuro"]{--fondo:#16151a;--papel:#1f1e24;--tinta:#eceaf2;
      --suave:#9c98a6;--borde:#34323c;--acento:#5fb98a;--alerta:#ff6b5e;
      --aviso:#e0a13a}
*{box-sizing:border-box}
body{margin:0;background:var(--fondo);color:var(--tinta);
     font:15px/1.55 "Segoe UI",system-ui,sans-serif}
/* 1400 y no 960: lo que ocupa sitio aqui son las tablas y la rejilla de
   fichas, y con 960 sobraba media pantalla a los lados mientras una tabla de
   ocho columnas se apretaba. */
.envoltorio{max-width:1400px;margin:0 auto;padding:24px 20px 60px}
h1{font-size:22px;margin:0 0 4px}
.sub{color:var(--suave);font-size:13px;margin:0 0 20px}
/* El titulo a la izquierda y el interruptor de tema a la derecha, en la
   misma linea. `align-items:start` y no `center`: el subtitulo hace que el
   bloque de la izquierda sea alto y centrado el boton se queda flotando. */
.cabecera{display:flex;justify-content:space-between;align-items:flex-start;
          gap:16px}
#bTema{font-size:13px;font-weight:600;padding:7px 12px;margin:0;flex:none;
       color:var(--suave)}
#bTema:hover{color:var(--tinta)}
/* El de idioma es un desplegable y no un boton, asi que hay que bajarle el
   tamanio para que los dos de la cabecera midan lo mismo. */
#selIdioma{font-size:13px;font-weight:600;padding:6px 10px;flex:none;
           color:var(--suave)}
.bloque{background:var(--papel);border:1px solid var(--borde);border-radius:10px;
        padding:16px 18px;margin-bottom:14px}
.bloque h2{font-size:13px;text-transform:uppercase;letter-spacing:.07em;
           color:var(--suave);margin:0 0 12px;font-weight:600}
button{font:inherit;font-weight:600;padding:9px 16px;border-radius:7px;
       border:1px solid var(--borde);background:var(--papel);color:var(--tinta);
       cursor:pointer;margin:0 8px 8px 0}
button:hover:not(:disabled){border-color:var(--suave)}
button:disabled{opacity:.4;cursor:default}
button.principal{background:var(--acento);border-color:var(--acento);color:#fff}
button.parar{background:var(--alerta);border-color:var(--alerta);color:#fff}
.banda{border-radius:10px;padding:14px 18px;margin-bottom:14px;font-weight:600}
.banda.on{background:var(--alerta);color:#fff}
.banda.off{background:var(--papel);border:1px solid var(--borde);color:var(--suave);
           font-weight:500}
.banda.ojo{background:var(--aviso);color:#1c1b19}
.banda small{display:block;font-weight:400;opacity:.9;margin-top:4px;font-size:13px}
pre{background:#0f0e13;color:#d6d3dd;border-radius:8px;padding:12px 14px;margin:0;
    font:12px/1.5 Consolas,monospace;max-height:340px;overflow:auto;
    white-space:pre-wrap;word-break:break-word}
table{width:100%;border-collapse:collapse;font-size:14px}
td{padding:5px 0;border-bottom:1px solid var(--borde)}
td:last-child{text-align:right;color:var(--suave)}
tr:last-child td{border-bottom:none}
/* Los parrafos NO se estiran con la pagina. Ensanchar sirve para las tablas;
   una linea de texto de 1400 px se lee fatal -- al saltar de renglon pierdes
   por donde ibas. Las tablas y las fichas si usan todo el ancho. */
.paso{color:var(--suave);font-size:13px;margin:0 0 12px;max-width:90ch}
.pista{color:var(--suave);font-size:13px;margin:10px 0 0;max-width:90ch}
.ok{color:var(--acento);font-weight:600}
.mal{color:var(--alerta);font-weight:600}
#vistasviejas{display:none;background:var(--aviso);color:#1c1b19;
       padding:12px 18px;border-radius:10px;margin-bottom:14px;font-weight:600}
#vistasviejas small{display:block;font-weight:400;opacity:.9;
       margin-top:4px;font-size:13px}
#caido,#desfase{display:none;background:var(--alerta);color:#fff;
       padding:12px 18px;
       border-radius:10px;margin-bottom:14px;font-weight:600}
#caido small,#desfase small{display:block;font-weight:400;opacity:.9;
       margin-top:4px;font-size:13px}
#recado{display:none;border:1px solid var(--alerta);color:var(--alerta);
        border-radius:8px;padding:10px 14px;margin:4px 0 12px;font-size:14px}
.mando{display:flex;align-items:center;gap:10px;margin-bottom:12px;flex-wrap:wrap}
.mando label{color:var(--suave);font-size:13px;font-weight:600;
             text-transform:uppercase;letter-spacing:.06em}
select{font:inherit;padding:8px 12px;border-radius:7px;border:1px solid var(--borde);
       background:var(--papel);color:var(--tinta);cursor:pointer;max-width:100%}
/* Cada vista es una ficha con su titulo y lo que hace debajo. Antes eran
   botones sueltos y el resumen solo salia de la ya elegida: con 24 vistas eso
   obliga a pulsarlas una a una para enterarte de cual quieres. */
.grupo{font-size:12px;font-weight:700;text-transform:uppercase;
       letter-spacing:.07em;color:var(--suave);margin:18px 0 8px}
.grupo:first-child{margin-top:2px}
.fichas{display:grid;gap:8px;margin-bottom:4px;
        grid-template-columns:repeat(auto-fill,minmax(240px,1fr))}
.fichas button{margin:0;font-size:13px;padding:9px 13px;text-align:left;
               display:flex;flex-direction:column;gap:3px;height:100%;
               white-space:normal}
.fichas button b{font-weight:600;line-height:1.25}
.fichas button small{color:var(--suave);font-size:12px;line-height:1.35;
                     font-weight:400}
.fichas button.elegida{background:var(--acento);border-color:var(--acento);color:#fff}
.fichas button.elegida small{color:#fff;opacity:.85}
/* Los titulares. Mas anchos que las fichas de vista (300 y no 240) porque
   lo que llevan es una frase entera y no un nombre, y a 240 se parten en
   seis renglones. */
.titulares{display:grid;gap:10px;
           grid-template-columns:repeat(auto-fill,minmax(300px,1fr))}
/* LA PORTADA VA EN DOS COLUMNAS: los titulares a la izquierda y los records
   a la derecha, no debajo. Puestos uno detras de otro habia que bajar seis
   fichas enteras para llegar a los records, y son la mitad de la portada --
   la que ademas no tiene minimo de partidas, o sea la unica que dice algo el
   primer dia.
   La columna de la derecha es fija (320px) y la izquierda se come el resto:
   asi las frases largas de los titulares siguen entrando en dos renglones y
   los records, que son tres, no se estiran a lo ancho de la pantalla.
   Por debajo de 860px se apilan -- en el movil dos columnas de 320 no caben
   y partirlas en una sola es mejor que encoger las dos. */
.portada{display:grid;gap:24px;align-items:start;
         grid-template-columns:minmax(0,1fr) minmax(0,320px)}
@media (max-width:860px){.portada{grid-template-columns:1fr}}
/* Cada columna, sus fichas una debajo de otra y pegadas arriba: sin
   `align-content` la columna corta reparte su hueco y las fichas quedan
   separadas de las de al lado. */
.portada > div{display:grid;gap:10px;align-content:start}
/* El titulo de los records, sin el hueco de arriba que lleva `.grupo`: aqui
   empieza columna, no separa dos bloques. */
.portada h3.grupo{margin-top:0}
.titular{border:1px solid var(--borde);border-radius:9px;padding:12px 14px;
         display:flex;flex-direction:column;gap:6px}
.titular .pregunta{font-size:11px;font-weight:700;text-transform:uppercase;
                   letter-spacing:.07em;color:var(--suave)}
.titular .quien{font-size:17px;font-weight:700;line-height:1.2}
/* La cifra en el color de acento y en tabular-nums: son numeros que se leen
   uno debajo de otro en la rejilla y con la fuente normal bailan. */
.titular .cifra{color:var(--acento);font-weight:700;
                font-variant-numeric:tabular-nums}
.titular .detalle{font-size:13px;color:var(--suave);line-height:1.45}
.titular .falta{font-size:13px;color:var(--suave);font-style:italic}
/* La segunda mesa, en la misma ficha. Separada por una raya y no por otro
   parrafo: es el mismo titular contado para el otro bloque, no un titular
   nuevo, y a la misma altura los dos se leen como dos cosas sueltas. */
.titular .tambien{font-size:13px;color:var(--suave);line-height:1.45;
                  border-top:1px solid var(--borde);padding-top:6px}
.titular .cuando{font-size:12px;color:var(--suave);font-variant-numeric:tabular-nums}
/* El enlace a la tabla va abajo del todo y pegado al borde inferior de la
   ficha (`margin-top:auto`), para que todas lo tengan a la misma altura
   aunque los detalles midan distinto. */
.titular button{margin:auto 0 0;align-self:flex-start;font-size:12px;
                padding:6px 11px;color:var(--suave)}
.titular button:hover{color:var(--tinta)}
/* La tabla puede ser mas ancha que el movil; que se desplace ella sola y no
   la pagina entera, que es lo que la deja inservible en el telefono. */
.rejilla{overflow-x:auto;margin-top:10px}
.rejilla table{min-width:100%;width:auto;font-variant-numeric:tabular-nums}
.rejilla th{text-align:left;padding:6px 14px 6px 0;border-bottom:2px solid var(--borde);
            color:var(--suave);font-size:12px;text-transform:uppercase;
            letter-spacing:.05em;white-space:nowrap}
.rejilla td{padding:6px 14px 6px 0;border-bottom:1px solid var(--borde);
            text-align:left;color:var(--tinta);white-space:nowrap}
.rejilla td.num{text-align:right;padding-right:20px}
.rejilla th.num{text-align:right;padding-right:20px}
/* La cabecera ordena. Tiene que PARECER que se puede tocar, o nadie la toca. */
.rejilla th.orden{cursor:pointer;user-select:none}
.rejilla th.orden:hover{color:var(--tinta)}
.rejilla th.activa{color:var(--acento)}
.rejilla th .flecha{font-size:10px;letter-spacing:0}
.rejilla td.nada{color:var(--suave)}
.rejilla tr:last-child td{border-bottom:none}
.vacio{color:var(--suave);font-size:14px;padding:8px 0}
/* La respuesta de la caja de preguntas. Grande, porque es lo que se ha
   preguntado; y con la procedencia debajo en pequeno, porque un numero que no
   se puede comprobar es peor que no tenerlo. */
#respuesta:not(:empty){margin:2px 0 14px;padding:12px 16px;border-radius:9px;
  background:var(--fondo2, rgba(127,127,127,.08));
  border:1px solid var(--borde)}
#respuesta .dice{font-size:17px;color:var(--tinta);font-weight:600}
#respuesta .fuente{font-size:12px;color:var(--suave);margin-top:6px}
#respuesta .fuente code{font-size:12px}
#respuesta .otras{font-size:13px;color:var(--suave);margin-top:8px}
#respuesta .otras button{margin:3px 6px 0 0;font-size:12px;padding:4px 10px}
/* Quien es quien. Los que no tienen nombre van marcados: despues de una
   partida nueva puede haber uno solo entre siete que ya lo tienen, y es el
   unico que hay que tocar. */
table.gente{border-collapse:collapse;margin:10px 0 4px;font-size:14px}
table.gente td{padding:5px 14px 5px 0;border-bottom:1px solid var(--borde);
               vertical-align:middle}
table.gente td.id code{font-size:12px;color:var(--suave)}
table.gente input{font:inherit;padding:5px 9px;border-radius:6px;width:190px;
                  border:1px solid var(--borde);background:var(--papel);
                  color:var(--tinta)}
table.gente input:focus{outline:none;border-color:var(--acento)}
table.gente button{margin:0;font-size:13px;padding:5px 12px}
table.gente tr.sinNombre td:first-child{color:var(--acento);font-weight:600}
.paginas{display:flex;align-items:center;gap:10px;flex-wrap:wrap;
         padding:10px 0 2px}
.paginas button{margin:0;font-size:13px;padding:6px 12px}
.paginas button:disabled{opacity:.4;cursor:default}
input[type=search]{font:inherit;padding:8px 12px;border-radius:7px;flex:1 1 260px;
  border:1px solid var(--borde);background:var(--papel);color:var(--tinta);min-width:0}
input[type=search]:focus{outline:none;border-color:var(--acento)}
.cuantas{color:var(--suave);font-size:13px;white-space:nowrap}
mark{background:var(--acento);color:#fff;border-radius:3px;padding:0 2px}
</style>
<script>
// EN LA CABEZA Y NO ABAJO, a proposito. Si el tema se pusiera con el resto
// del guion, la pagina se pintaria primero en claro y cambiaria a oscuro un
// instante despues: el fogonazo blanco que dan las paginas mal hechas. Aqui
// se resuelve antes de que se dibuje nada.
//
// El orden es: lo que eligio quien lo usa, y si no ha elegido, lo que
// prefiere su sistema. Elegir gana siempre; no elegir no es elegir claro.
(function(){
  var t = null;
  try { t = localStorage.getItem("tema"); } catch(e) {}   // modo privado
  if (t !== "claro" && t !== "oscuro")
    t = (window.matchMedia
         && matchMedia("(prefers-color-scheme:dark)").matches)
        ? "oscuro" : "claro";
  document.documentElement.setAttribute("data-tema", t);
})();
</script>
<!--idiomas--></head><body><div class="envoltorio">

<div class="cabecera">
  <div>
    <h1>Catan Tracker</h1>
    <p class="sub" id="donde">buscando el juego...</p>
  </div>
  <select id="selIdioma" title="Cambiar de idioma"></select>
  <button id="bTema" type="button" title="Cambiar entre claro y oscuro"></button>
</div>

<div id="caido">El panel no responde.
  <small>La ventana negra en la que arrancaste <b>panel.py</b> se ha
  cerrado, o
  nunca llegó a abrirse. Vuelve a abrirla y recarga esta página; mientras
  tanto los botones de aquí no hacen nada.</small></div>
<div id="desfase" style="display:none">El panel se ha quedado atr&aacute;s.
  <small>Ha cambiado el <b>c&oacute;digo</b> de <b>panel.py</b>, no s&oacute;lo
  la p&aacute;gina. La p&aacute;gina se relee sola y con <b>F5</b> basta; el
  servidor no, as&iacute; que los botones nuevos pegan contra uno viejo y no
  hacen nada. Aqu&iacute; s&iacute; hay que cerrar la ventana negra y volver a
  abrirla.</small></div>
<div id="vistasviejas" style="display:none">Las tablas de tu base son de
  una versi&oacute;n anterior.
  <small>Las 28 vistas se guardan <b>dentro</b> de tu fichero de datos, no en
  el c&oacute;digo, as&iacute; que al bajarte una versi&oacute;n nueva siguen
  siendo las de antes. No se pierde nada y no hace falta borrar nada: dale a
  <b>Rehacer las vistas de la base</b>, o importa una partida, que ya lo hace
  solo. <span id="vistasviejasq"></span></small></div>
<div id="recado"></div>

<div class="banda off" id="banda">...</div>

<div class="bloque" id="bloqueInstalar" style="display:none">
  <h2>0 &middot; Dejar el mod listo</h2>
  <p class="paso" id="pasoInstalar">Falta algo por instalar.</p>
  <button class="principal" id="bInstalar">Dejarlo listo</button>
  <p class="pista">Busca Catan pregunt&aacute;ndoselo a Steam, mira si es de 32
  o de 64 bits, <b>se descarga el BepInEx que toca</b>, comprueba su SHA-256
  antes de tocar nada y compila el plugin. Lo deja <b>apagado</b>: instalarlo
  y encenderlo son dos decisiones distintas, y esto solo toma la primera.</p>
  <p class="pista">Lo de 32 bits no es un detalle. Catan Universe es de 32
  aunque tu Windows sea de 64, y con el paquete equivocado el juego arranca
  igual y el mod no carga <b>nunca</b>, sin dar un solo error.</p>
</div>

<div class="bloque">
  <h2>1 &middot; Jugar</h2>
  <p class="paso" id="paso1">Enciende el mod y <b>despues</b> abre Catan, que
  el mod se carga al arrancar el juego. Juega lo que quieras: no hace falta
  cerrar Catan entre partidas, cambia de fichero solo. Al terminar, apagalo.</p>
  <button class="principal" id="bSoloMod">Encender el mod</button>
<!--dev-->  <button id="bEmpezar">&hellip;y grabar capturas</button>
<!--/dev-->  <button class="parar" id="bParar">Parar y apagar el mod</button>
<!--dev-->  <button id="bComprobar">Comprobar que ha apuntado bien</button>
<!--/dev-->
  <p class="pista">El mod apunta <b>solo informacion publica</b>: lo que ven
  todos los que estan en la mesa. Ni las manos de nadie, ni los puntos
  escondidos de las cartas, ni que carta se lleva un robo. Y no guarda ni una
  captura de pantalla: son unos pocos KB por partida.</p>
<!--dev-->  <p class="pista"><b>&hellip;y grabar capturas</b> saca ademas una
  foto por accion, para tener la pantalla y la verdad emparejadas. Es lo que
  alimenta la red y las plantillas, y <b>solo sirve para eso</b>: ocupa <b>2 GB
  por partida</b>. Si lo que quieres son tus estadisticas, el primer boton
  apunta exactamente igual de bien.</p>
<!--/dev-->
</div>

<div class="bloque">
  <h2>2 &middot; Guardar en la base de datos</h2>
  <p class="paso">Pasa lo que apunto el mod a las tablas de siempre: quien
  construyo que y cuando, las tiradas, el ladron, los robos, los comercios y
  la produccion de cada uno. Se puede dar tantas veces como quieras: las
  partidas que ya estan no se repiten.</p>
  <button class="principal" id="bImportar">Guardar en la base de datos</button>
  <button id="bNombres">Ponerle nombre a alguien</button>
  <button id="bQuitar">Quitar una partida</button>
  <div id="gente"></div>
  <div id="quitables"></div>
  <p class="pista">El mod no guarda nombres, guarda el identificador de cada
  cuenta &mdash; que es estable, asi que reconoce a la misma persona partida
  tras partida. La primera vez que juegue alguien nuevo saldra con un nombre
  provisional (<code>jugador_4645eb8a</code>); ponle el suyo ahi arriba y se
  arreglan tambien <b>las partidas ya guardadas</b>, que si no el historico se
  parte en dos personas. Por consola es
  <code>py mod_verdad/importar.py --llamar &lt;identificador&gt; Pedro</code>,
  que es exactamente lo que hace el boton.</p>
  <p class="pista"><b>Quitar una partida</b> es para las que no deberian
  contar: una que se cancelo a medias entra <b>sin ganador y sin puntos</b>, y
  eso no se nota en la tabla &mdash; se nota en las medias. Antes de borrar
  hace una <b>copia de la base</b> en <code>copias/</code>, y apunta la
  grabacion para que el importador no la vuelva a meter. <b>No borra las
  capturas</b>: quitar una partida del historico no le hace perder un recorte
  a la vision. Y no hay deshacer, asi que pregunta.</p>
</div>

<div class="bloque">
  <h2>Los titulares</h2>
  <p class="paso">Lo que dicen las tablas <b>ahora mismo</b>. No hay ni un
  nombre ni un n&uacute;mero escritos a mano: se recalculan en cada visita,
  as&iacute; que el d&iacute;a que alguien adelante a otro el titular cambia
  solo. Y el n&uacute;mero <b>sale de la misma consulta</b> que pinta la
  tabla de abajo &mdash; dale al enlace de cada uno y la tienes delante.</p>
  <p class="paso">Solo entra quien lleve <b id="titMinimo">10</b> partidas o
  m&aacute;s. Sin ese corte el titular se lo lleva siempre el que
  jug&oacute; una vez y tuvo un buen d&iacute;a, y en las tablas de abajo
  est&aacute;n todos igual. <span id="titQuienes"></span></p>
  <div class="portada">
    <div id="titulares">cargando...</div>
    <div>
      <h3 class="grupo">R&eacute;cords de una sola partida</h3>
      <p class="paso">La mejor marca de un d&iacute;a, y en qu&eacute; partida
      fue. <b>Aqu&iacute; no hay m&iacute;nimo</b>, a prop&oacute;sito: un
      titular es una costumbre y pide partidas; un r&eacute;cord es de un
      d&iacute;a, y si en tu primera te pusieron veintiún ladrones, te los
      pusieron. El enlace abre esa tabla <b>ya filtrada por esa
      partida</b>.</p>
      <div id="records">cargando...</div>
    </div>
  </div>
</div>

<div class="bloque">
  <h2>3 &middot; Mirar los datos</h2>
  <p class="paso">Elige que partidas quieres mirar y dale a lo que sea. De
  serie salen <b>solo las de amigos</b>: una partida contra la IA es otro
  juego -- la maquina no propone tratos ni bloquea igual -- y mezclarla con
  las de la mesa no ensucia un poco la media, la deja sin significado. Las
  otras dos opciones estan para cuando SI las quieres.</p>
  <p class="paso">O preguntalo en cristiano y te lo busco en las tablas
  &mdash; <i>cuantos caballeros le han caido a elGato</i>, <i>quien ha tenido
  mas suerte</i>, <i>cuanto mineral ha producido carla</i>. No hay ninguna
  inteligencia artificial detras y no sale nada de este ordenador: la pregunta
  se parte en palabras y se busca entre los nombres de las vistas. Debajo
  de la respuesta sale siempre <b>de donde ha salido el numero</b>.</p>
  <div class="mando">
    <input id="pregunta" type="search" placeholder="preguntame algo &mdash; cuantos caballeros le han caido a elGato">
    <button id="bPreguntar">Buscar</button>
  </div>
  <div id="respuesta"></div>
  <div class="mando">
    <label for="selPartida">Que partidas</label>
    <select id="selPartida">
      <option value="amigos">solo con amigos (sin la IA)</option>
    </select>
    <label for="selMesa">De cuantos</label>
    <select id="selMesa">
      <option value="todas">mesas de cualquier tama&ntilde;o</option>
    </select>
  </div>
  <p class="pista">Una partida de <b>5 o 6</b> no es la misma con dos sillas
  m&aacute;s: el tablero tiene 30 casillas en vez de 19 y no reparte los
  n&uacute;meros igual, y se juega a 12 puntos y no a 10. Mezclarlas es el
  mismo problema que mezclar las de la IA, por eso el filtro se parece.
  Ahora mismo son <b>3 de 18</b>, as&iacute; que de serie salen todas
  &mdash; separarlas lo decides t&uacute;.</p>
  <div id="botonesVista">cargando...</div>
  <p class="pista" id="queEs"></p>
  <div class="mando">
    <input id="filtro" type="search" placeholder="filtrar &mdash; un texto busca por dentro (carla, 2:1); un numero busca exacto (4)">
    <span class="cuantas" id="cuantas"></span>
  </div>
  <div id="tablaVista" class="rejilla"></div>
  <p class="pista">Sale de las mismas vistas que <code>py sql.py "SELECT *
  FROM amigos_marcador"</code> &mdash; no hay dos consultas que puedan decir
  cosas distintas. La base se abre aqui en <b>solo lectura</b>.</p>
<!--dev-->  <button id="bVistas">Rehacer las vistas</button>
  <button id="bPruebasDatos">Comprobar que cuadran</button>
  <p class="pista"><b>Comprobar que cuadran</b> mira que el total y cada
  partida por separado digan lo mismo, que los robos hechos sean los mismos
  que los sufridos y que nadie tenga puntos tapados imposibles. Es lo que
  avisaria si al tocar una consulta se colara un error callado.</p>
<!--/dev-->
</div>

<div class="bloque">
  <h2>3b &middot; El informe largo</h2>
  <p class="paso">El de siempre, en texto: quien construyo que, en que numeros
  se puso cada uno, el ladron, los comercios y las tiradas.</p>
  <button class="principal" id="bAnalizar">Ver el informe</button>
</div>

<!--vision--><div class="bloque">
  <h2>4 &middot; Leer el tablero de la pantalla</h2>
  <p class="paso">Mira la pantalla y lee el tablero: <b>no toca el juego</b>,
  solo hace capturas. No hay nada que configurar &mdash; dale y ya. <b>Los
  colores de la mesa los lee solo</b>, de los paneles de jugador de las
  esquinas, que es de donde los lees tu. Se abre una ventana con lo que va
  viendo.</p>
  <button class="principal" id="bMirar">Mirar la pantalla</button>
<!--dev-->  <button id="bEnsayo">Probarlo sobre una partida grabada</button>
  <button id="bMesa">Medir el ladron y los dados</button>
<!--/dev-->  <p class="pista">Empieza con el <b>tablero vacio</b> si puedes: la
  referencia del sitio vacio &mdash; la mitad de lo que se mira &mdash; se toma
  de las primeras fotos y se congela con la primera pieza. Arrancando a mitad
  de partida, lo que ya estuviera puesto se toma por tablero y no se ve.
  Ademas de las piezas se lee <b>donde esta el ladron</b> y <b>la ultima
  tirada</b>.</p>
</div>
<!--/vision-->

<!--dev-->

<div class="bloque" style="opacity:.75">
  <h2>Para desarrollar el proyecto</h2>
  <p class="paso">De aqui para abajo <b>no hace falta nada</b> para tener tus
  estadisticas. Es la otra mitad del proyecto: una red que aprende a leer el
  tablero de una captura, con las etiquetas que escribe el propio juego, para
  ver cuanto se puede saber <b>sin tocar el cliente</b>.</p>
</div>

<div class="bloque">
  <h2>Que alimentan las capturas</h2>
  <p class="paso">Se graban con <b>&laquo;&hellip;y grabar capturas&raquo;</b>,
  arriba del todo, junto al boton de encender. Cada foto va emparejada con el
  estado exacto que apunto el mod en ese instante, asi que las etiquetas las
  escribe el juego y no hay que anotar nada a mano. Alimentan tres cosas
  distintas, y solo la primera se &laquo;entrena&raquo;:</p>
  <p class="pista"><b>La red</b> (<code>red_de_sitios.pt</code>) &mdash; lee
  que hay en cada vertice y cada arista. Es la que se entrena con el boton de
  aqui abajo.<br>
  <b>Las plantillas</b> (<code>plantillas_puntos.npz</code>,
  <code>plantillas_cartas.npz</code>, los digitos) &mdash; no son una red: son
  el promedio de miles de recortes ya etiquetados. De ahi salen los
  contadores de los paneles, con 97,3% en caballeros y 98,9% en desarrollo.<br>
  <b>El aviso de la esquina</b> (<code>ocr/ticker.py</code>) &mdash; ese usa
  Tesseract y <b>no se entrena</b>. Las capturas sirven para MEDIRLO (20 robos
  de 20, 23 comercios de 30) y para ajustar el recorte y el umbral de tinta.</p>
</div>

<div class="bloque">
  <h2>Entrenar la red con lo grabado</h2>
  <p class="paso">Un boton. Convierte lo grabado, <b>examina</b> el modelo de
  antes con la partida nueva &mdash; que no ha visto &mdash; y solo entonces
  entrena con ella. En ese orden, porque al reves el numero sale inflado y no
  avisa de nada.</p>
  <button class="principal" id="bRutina">Hacerlo todo</button>
  <button id="bHistorial">Como va mejorando</button>
  <p class="pista">Tarda cerca de media hora: son dos entrenamientos, el que
  se mide (aparta dos partidas) y el que se juega (con todo dentro).</p>
  <p class="paso" style="margin-top:1em">Y los pasos sueltos, por si hace falta
  uno solo:</p>
  <button id="bDataset">Preparar los datos</button>
  <button id="bTablero">Medir el tablero entero</button>
  <button id="bMedir">Medir foto a foto</button>
  <button id="bEntrenar">Entrenar</button>
  <button id="bEntrenarTodo">Reentrenar con todo (para jugar)</button>
  <button id="bPruebas">Pruebas</button>
  <p class="pista">&laquo;Medir el tablero entero&raquo; es el numero que
  importa: cuanto del tablero final queda bien leido, que es lo que tendria
  delante quien juega. &laquo;Foto a foto&raquo; mira recortes sueltos, donde
  el tablero vacio arrastra la media hacia arriba.</p>
</div>

<!--/dev-->

<div class="bloque">
  <h2 id="tituloReg">Registro</h2>
  <pre id="registro">(nada todavia)</pre>
  <!-- El boton de parar vive aqui y no en el bloque de cada tarea: es donde
       se ve correr lo que hay que parar, y hay una sola tarea a la vez. -->
  <button class="parar" id="bMatar">Parar la tarea</button>
</div>

<!--dev--><div class="bloque">
  <h2>Partidas grabadas</h2>
  <table id="partidas"><tr><td>...</td></tr></table>
</div>
<!--/dev-->

<!--dev--><div class="bloque" id="bloqueModelo">
  <h2>El modelo de ahora</h2>
  <pre id="modelo">...</pre>
</div>
<!--/dev-->

<script>
let fuente = "tarea", pos = 0, caido = false, tareaViva = null;

// Si el servidor no esta, TODOS los botones dejan de hacer nada y la pagina
// se queda igual que si estuvieran rotos. Paso justo eso la primera vez que
// se uso esto, asi que la caida tiene que verse.
function marcarCaido(si){
  if (caido === si) return;
  caido = si;
  document.getElementById("caido").style.display = si ? "block" : "none";
  if (si) document.title = "✕ sin panel — Catan Tracker";
}

function recado(texto, malo){
  const d = document.getElementById("recado");
  d.textContent = texto || "";
  d.style.display = texto ? "block" : "none";
  d.style.borderColor = malo === false ? "var(--borde)" : "var(--alerta)";
  d.style.color = malo === false ? "var(--tinta)" : "var(--alerta)";
}

async function pedir(ruta, cuerpo){
  const r = await fetch(ruta, cuerpo ? {method:"POST",
    headers:{"Content-Type":"application/json"}, body:JSON.stringify(cuerpo)} : {});
  if (!r.ok) throw new Error("el panel ha respondido " + r.status);
  const j = await r.json();
  marcarCaido(false);
  return j;
}

function boton(id, fn){
  // El boton puede no existir: hay trozos de la pagina que el servidor no
  // manda. Antes esto reventaba en la PRIMERA que faltara y dejaba sin
  // cablear todas las de despues -- el panel entero muerto, sin un error.
  if (!document.getElementById(id)) return;
  document.getElementById(id).onclick = async () => {
  const b = document.getElementById(id); b.disabled = true;
  recado("");
  try {
    const r = await fn();
    if (r && r.error) recado(r.error);
  } catch (e) {
    marcarCaido(true);
  } finally { b.disabled = false; refrescar(); }
};}

// El interruptor de tema. No pasa por `boton()` -- que deshabilita, pide al
// servidor y refresca -- porque esto no toca el servidor: cambia un atributo
// y lo apunta en el navegador. El servidor no sabe ni tiene por que saber de
// que color ves la pagina.
//
// El de idioma NO es un boton, a diferencia del de tema. Un boton que da la
// vuelta vale para dos cosas --claro y oscuro-- y deja de valer a la
// tercera: para llegar al aleman habria que pasar por el frances, y cada
// paso recarga la pagina. Y hasta que no pasas por ellos no sabes que
// existen. Un desplegable los ensena todos y llega a cualquiera en un clic,
// que es justo lo que hacia falta si esto va a crecer.
(function(){
  const s = document.getElementById("selIdioma");
  if (!s) return;
  const hay = window.IDIOMAS_HAY || [];
  if (hay.length < 2){ s.hidden = true; return; }
  s.innerHTML = hay.map(l => '<option value="' + escapar(l.id) + '"'
      + (l.id === window.IDIOMA_AHORA ? " selected" : "") + ">"
      + escapar(l.boton) + "</option>").join("");
  s.onchange = () => {
    // Un anio. Y `path=/` para que valga en todas las rutas del panel, no
    // solo en la que estabas.
    document.cookie = "idioma=" + s.value + ";path=/;max-age=31536000";
    location.reload();
  };
})();

// El boton dice A DONDE VAS, no donde estas: estando en claro pone «Oscuro».
// Al reves obliga a pensarlo, y es un boton para no pensarlo.
function pintarTema(){
  const b = document.getElementById("bTema");
  if (!b) return;
  const oscuro = document.documentElement.getAttribute("data-tema") === "oscuro";
  b.textContent = oscuro ? "☀︎  Claro" : "☽  Oscuro";
}
(function(){
  const b = document.getElementById("bTema");
  if (!b) return;
  b.onclick = () => {
    const nuevo = document.documentElement.getAttribute("data-tema") === "oscuro"
                  ? "claro" : "oscuro";
    document.documentElement.setAttribute("data-tema", nuevo);
    // Que falle guardarlo no puede impedir que cambie: en una ventana
    // privada `localStorage` lanza en vez de devolver null.
    try { localStorage.setItem("tema", nuevo); } catch(e) {}
    pintarTema();
  };
  pintarTema();
})();

// Aqui habia una lista de checkboxes para marcar los colores de la mesa.
// Ya no esta: los lee red/mesa.py de los paneles de jugador, que es el unico
// sitio de donde se pueden saber jugando online -- los reparte el juego al
// empezar la partida, asi que preguntarlos antes no era una opcion.
boton("bMirar", () => { fuente="tarea"; pos=0; return pedir("/tarea",{que:"mirar"}); });
boton("bEnsayo", () => { fuente="tarea"; pos=0; return pedir("/tarea",{que:"ensayo"}); });
boton("bMesa",   () => { fuente="tarea"; pos=0; return pedir("/tarea",{que:"mesa"}); });

boton("bInstalar", () => { fuente="tarea"; pos=0; return pedir("/tarea",{que:"instalar"}); });

// Quitar una partida. La lista sale del catalogo que ya se pide para el
// desplegable, asi que no hace falta otra ruta: son las mismas partidas y
// con el mismo texto, que es lo que evita que una diga una cosa y otra otra.
let quitablesAbierto = false;
function pintarQuitables(){
  const caja = document.getElementById("quitables");
  if (!quitablesAbierto){ caja.innerHTML = ""; return; }
  const ps = (catalogoVistas && catalogoVistas.partidas) || [];
  if (!ps.length){
    caja.innerHTML = '<p class="vacio">No hay ninguna partida guardada.</p>';
    return;
  }
  caja.innerHTML = '<table class="gente">' + ps.map(p =>
    "<tr><td>partida " + p.id + "</td><td>" + escapar(p.texto) + "</td>"
    + '<td><button data-id="' + p.id + '">quitar</button></td></tr>').join("")
    + "</table>";
  for (const b of caja.querySelectorAll("button")){
    b.onclick = async () => {
      const id = b.dataset.id;
      const fila = b.closest("tr").children[1].textContent;
      // Se pregunta con el TEXTO de la partida delante, no con el numero: el
      // numero no dice cual es y confirmar a ciegas no es confirmar.
      if (!confirm("Quitar la partida " + id + "?\n\n" + fila
                   + "\n\nSe hace una copia de la base antes, pero no hay "
                   + "deshacer.")) return;
      // Con su try: `pedir` LANZA si la respuesta no es 200, y este
      // manejador no pasa por `boton()`, que es quien recoge los errores en
      // el resto del panel. Sin esto la excepcion se pierde y el boton no
      // hace nada -- que es exactamente como se porto la primera vez.
      b.disabled = true;
      let r;
      try {
        r = await pedir("/quitar", {partida: Number(id)});
      } catch (e) {
        alert("No se ha podido quitar: " + e.message
              + "\n\nSi pone 404, este panel lleva abierto desde antes de que "
              + "el boton existiera. Cierra la ventana negra y vuelve a abrirla.");
        return;
      } finally { b.disabled = false; }
      if (!r.ok){ alert(r.error || "no se ha podido"); return; }
      // La base ha cambiado: hay que releer el catalogo (el desplegable y
      // esta lista) y la vista que se este mirando.

      await traerCatalogo();
      pintarQuitables();
      traerVista();
    };
  }
}
boton("bQuitar", async () => {
  quitablesAbierto = !quitablesAbierto;
  if (quitablesAbierto && !catalogoVistas) await traerCatalogo();
  pintarQuitables();
  return {ok: true};
});
boton("bEmpezar", () => { fuente="grabacion"; pos=0; return pedir("/grabar",{arrancar:true}); });
boton("bSoloMod", () => { fuente="mod"; pos=0;
  return pedir("/grabar",{arrancar:true, solo_mod:true}); });
boton("bParar",   () => pedir("/grabar",{arrancar:false}));
boton("bMatar",   () => pedir("/matar",{}));
for (const [id, que] of [["bComprobar","comprobar"],["bDataset","dataset"],
                         ["bRutina","rutina"],["bHistorial","historial"],
                         ["bTablero","tablero"],
                         ["bMedir","medir"],["bEntrenar","entrenar"],
                         ["bEntrenarTodo","entrenar_todo"],["bPruebas","pruebas"],
                         ["bImportar","importar"],
                         ["bAnalizar","analizar"],["bVistas","vistas"],
                         ["bPruebasDatos","pruebas_datos"]])
  boton(id, () => { fuente="tarea"; pos=0; return pedir("/tarea",{que}); });

// --- ponerle nombre a alguien ------------------------------------------
// Una fila por cuenta, con su nombre en una caja. Los provisionales primero
// y marcados: son los que hay que arreglar, y despues de una partida nueva
// puede haber uno solo entre siete que ya tienen nombre.
let genteAbierta = false;

function pintarGente(r){
  const caja = document.getElementById("gente");
  if (!genteAbierta){ caja.innerHTML = ""; return; }
  if (r.error){
    caja.innerHTML = '<p class="vacio">' + escapar(r.error) + "</p>";
    return;
  }
  const gente = (r.gente || []).slice().sort((a, b) =>
    (b.provisional - a.provisional) || (a.es_ia - b.es_ia)
    || a.nombre.localeCompare(b.nombre, "es"));
  if (!gente.length){
    caja.innerHTML = '<p class="vacio">Todavia no hay ninguna cuenta. '
      + "Guarda una partida primero.</p>";
    return;
  }
  caja.innerHTML = '<table class="gente">' + gente.map((g, i) =>
    '<tr class="' + (g.provisional ? "sinNombre" : "") + '">'
    + "<td>" + (g.provisional ? "sin nombre" : escapar(g.nombre))
    + (g.es_ia ? " <small>(IA)</small>" : "") + "</td>"
    + '<td class="id"><code>' + escapar(g.red) + "</code></td>"
    + "<td>" + g.partidas + (g.partidas === 1 ? " partida" : " partidas") + "</td>"
    + '<td><input type="text" maxlength="40" data-red="' + escapar(g.red)
    + '" value="' + (g.provisional ? "" : escapar(g.nombre))
    + '" placeholder="como se llama"></td>'
    + '<td><button data-i="' + i + '">guardar</button></td></tr>').join("")
    + "</table>";
  for (const b of caja.querySelectorAll("button")){
    b.onclick = async () => {
      const caja2 = b.closest("tr").querySelector("input");
      b.disabled = true;
      // La tarea escribe en la base, asi que despues hay que releer las dos
      // cosas que dependen de los nombres: esta lista y el catalogo (que
      // trae los ganadores de cada partida).
      fuente = "tarea"; pos = 0;
      const r2 = await pedir("/llamar", {red: caja2.dataset.red,
                                         nombre: caja2.value});
      b.disabled = false;
      if (!r2.ok){ alert(r2.error || "no se ha podido"); return; }
      setTimeout(async () => {
        pintarGente(await pedir("/gente"));
        traerCatalogo();
      }, 1200);
    };
  }
}

// --- preguntar en cristiano ---------------------------------------------
// La respuesta va arriba en grande y la tabla de la que sale, abajo. Sin la
// tabla esto seria un numero que hay que creerse; con ella, es un atajo para
// llegar a la vista que contesta.
async function preguntar(){
  const caja = document.getElementById("pregunta");
  const donde = document.getElementById("respuesta");
  const q = caja.value.trim();
  if (!q){ donde.innerHTML = ""; return {ok: true}; }
  donde.innerHTML = '<p class="vacio">buscando...</p>';
  let r;
  try {
    r = await pedir("/preguntar?q=" + encodeURIComponent(q)
                    + "&ambito=" + encodeURIComponent(ambitoElegido()));
  } catch (e) { marcarCaido(true); return {ok: false}; }
  if (r.error){ donde.innerHTML = '<p class="vacio">' + escapar(r.error)
                                  + "</p>"; return {ok: true}; }
  let html = '<div class="dice">' + escapar(r.respuesta) + "</div>";
  if (r.vista){
    html += '<div class="fuente">De «' + escapar(r.titulo) + "»"
          + (r.columna ? ", columna <code>" + escapar(r.columna) + "</code>" : "")
          + ".  En la ventana negra:  <code>" + escapar(r.de_donde)
          + "</code></div>";
  }
  if (r.otras && r.otras.length){
    html += '<div class="otras">Si no era eso: '
          + r.otras.map(o => '<button data-vista="' + escapar(o.vista) + '">'
              + escapar(o.titulo)
              + (o.columna ? " · " + escapar(o.columna) : "")
              + "</button>").join("") + "</div>";
  }
  donde.innerHTML = html;
  for (const b of donde.querySelectorAll("button[data-vista]"))
    b.onclick = () => { vistaElegida = b.dataset.vista; traerVista(); };
  // Y la tabla de la que sale el numero, en el sitio de siempre.
  if (r.vista){
    vistaElegida = r.vista;
    for (const x of document.querySelectorAll("#botonesVista button"))
      x.classList.toggle("elegida", x.dataset.vista === vistaElegida);
    pintarTabla({columnas: r.columnas, filas: r.filas});
    document.getElementById("queEs").textContent =
      "En la ventana negra:  " + r.de_donde;
  }
  return {ok: true};
}

function ambitoElegido(){
  const v = document.getElementById("selPartida").value;
  return /^[0-9]+$/.test(v) ? "amigos" : (v || "amigos");
}

boton("bPreguntar", preguntar);
document.getElementById("pregunta").addEventListener("keydown", e => {
  if (e.key === "Enter") preguntar();
});

boton("bNombres", async () => {
  genteAbierta = !genteAbierta;
  pintarGente(genteAbierta ? await pedir("/gente") : {});
  return {ok: true};
});

// --- las vistas de la base ---------------------------------------------
// El catalogo se pide una vez; las partidas solo cambian al importar, y
// entonces se vuelve a pedir. Lo que NO se hace es refrescar la tabla con el
// temporizador: si estas leyendola, que no se mueva sola.
let vistaElegida = null, catalogoVistas = null;

function esNumero(v){ return typeof v === "number"; }

// Los apodos de los rivales salen de una partida online: los escribe un
// desconocido y acaban aqui dentro de innerHTML. Uno que se llamara
// "<script>..." se ejecutaria solo al abrir el panel. Nada de meter texto de
// la base sin pasar por aqui.
const _ESCAPES = {"&":"&amp;", "<":"&lt;", ">":"&gt;", '"':"&quot;", "'":"&#39;"};
function escapar(s){
  return String(s).replace(/[&<>"']/g, c => _ESCAPES[c]);
}

// Sin acentos y en minusculas, para que "lobo" encuentre a "LoboEstepario"
// y "generico" encuentre a "genérico".
function normaliza(s){
  return String(s).toLowerCase().normalize("NFD").replace(/[\u0300-\u036f]/g, "");
}

// El resaltado se busca sobre el texto TAL CUAL, no sobre el normalizado:
// quitar acentos cambia la longitud de la cadena, asi que los indices del
// normalizado no valen para cortar el original. Si no lo encuentra asi, no
// resalta y ya -- la fila sale igual, solo sin marca.
function resaltar(texto, aguja){
  const t = String(texto);
  if (!aguja) return escapar(t);
  const i = t.toLowerCase().indexOf(aguja);
  if (i < 0) return escapar(t);
  return escapar(t.slice(0, i)) + "<mark>"
       + escapar(t.slice(i, i + aguja.length)) + "</mark>"
       + escapar(t.slice(i + aguja.length));
}

// Un NUMERO se busca entero; un TEXTO, por dentro.
//
// Buscar "4" en «las tiradas» tiene que dar la fila del 4, no ademas las que
// llevan un 4 escondido en un 30.4 o en un 14. Con el texto es al reves:
// "carla" tiene que encontrar a "carlarr", y "2:1" a "Mineral 2:1".
function coincide(v, clave, crudo){
  if (v === null) return false;
  if (esNumero(v)) return String(v) === crudo;
  return normaliza(v).includes(clave);
}

// Dia, mes y ano, que es como se lee una fecha. En la base se queda en ISO
// (2026-08-31) y no por gusto: es la unica forma que se ordena bien como
// TEXTO. Con 31/08/2026 el orden alfabetico pone el 31 de agosto antes que
// el 1 de septiembre, y lo peor es que el resultado parece correcto.
//
// Asi que se guarda en ISO y se le da la vuelta al pintar. Lo que se ordena
// y lo que se compara sigue siendo el valor de la fila, nunca esto.
function fecha(v){
  const m = /^(\d{4})-(\d{2})-(\d{2})$/.exec(String(v));
  return m ? m[3] + "/" + m[2] + "/" + m[1] : v;
}

let ultimaTabla = null;
let selloBase = null;

// Paginado de filas. `amigos_tratos` ya va por 100 filas y crece con cada
// partida, asi que la tabla entera de golpe es una lista que no se acaba.
//
// POR_PAGINA no es 11 porque once sea bonito: es que con menos la mitad de
// las vistas se parten en dos sin necesidad, y con mas vuelve el problema.
// Las que no llegan a 11 no ensenan ni un boton.
//
// Era 10, y 11 es el numero que hay que poner: los DADOS SON ONCE numeros,
// del 2 al 12. «Las tiradas» tiene once filas siempre -- no once hoy, once
// por construccion, que la vista las saca de un VALUES fijo para que un
// numero que no salio nunca tenga su fila igual. Con 10 esa tabla se partia
// en dos paginas y la segunda traia una fila. Y no es la unica que ronda
// ese tamanio: «El ladron, por numero» va por nueve.
const POR_PAGINA = 11;
let pagina = 0;
let verTodas = false;

// Ordenar tocando la cabecera. Vive aqui y no en el SQL de cada vista a
// proposito: asi lo tienen las 27 y las que vengan sin escribir una linea
// mas. Cada vista sigue trayendo SU orden, que es el que tiene sentido por
// defecto; esto es para la pregunta de al lado ("y de mayor a menor?").
// null = el orden que trae la vista.
let orden = null;

function engancharCabeceras(){
  for (const th of document.querySelectorAll("#tablaVista th.orden")){
    th.onclick = () => {
      const i = Number(th.dataset.col);
      const num = th.classList.contains("num");
      if (!orden || orden.i !== i){
        // Un numero se mira de mayor a menor; un nombre, de la A a la Z.
        orden = {i: i, desc: num};
      } else if (orden.desc === num){
        orden = {i: i, desc: !num};
      } else {
        // Tercer toque: se suelta y vuelve el orden de la vista.
        orden = null;
      }
      pagina = 0;
      dibujar();
    };
  }
}

function pintarTabla(r){
  ultimaTabla = r;
  // Vista nueva, se vuelve a la primera pagina. Sin esto, saltar de una de
  // 100 filas a una de 5 dejaba la tabla en blanco: seguia en la pagina 7.
  pagina = 0;
  // Y se suelta el orden: la columna 3 de una vista no es la 3 de la otra,
  // y arrastrarlo dejaba tablas ordenadas por una columna que no habias
  // tocado nunca.
  orden = null;
  dibujar();
}

function dibujar(){
  const caja = document.getElementById("tablaVista");
  const cuantas = document.getElementById("cuantas");
  const r = ultimaTabla;
  cuantas.textContent = "";
  if (!r) return;
  if (r.error){
    caja.innerHTML = '<p class="vacio">' + escapar(r.error) + '</p>';
    return;
  }
  if (!r.filas.length){
    // Cada vista puede explicar su propio vacio: "no hay datos" no dice lo
    // mismo en una que se llena sola que en una que espera a que el mod
    // aprenda a leer algo.
    const v = ((catalogoVistas && catalogoVistas.vistas) || [])
                .find(x => x.nombre === vistaElegida);
    caja.innerHTML = '<p class="vacio">' + escapar((v && v.vacio)
      || "No hay nada que enseñar aqui. Si has elegido una partida contra la "
       + "IA, las vistas de amigos salen vacias a proposito.") + "</p>";
    return;
  }
  const busca = document.getElementById("filtro").value.trim();
  const clave = normaliza(busca);
  // Se busca en las dos formas de la fecha: en la que se ve (31/08/2026) y
  // en la que hay debajo (2026-08-31). Si solo valiera una, escribir la que
  // tienes delante en los ojos no encontraria nada.
  let filas = clave
    ? r.filas.filter(f => f.some(v => coincide(v, clave, busca)
                                   || coincide(fecha(v), clave, busca)))
    : r.filas;
  cuantas.textContent = clave
    ? filas.length + " de " + r.filas.length
    : r.filas.length + (r.filas.length === 1 ? " fila" : " filas");

  // Una columna es de numeros si TODOS sus valores lo son. Asi los nombres no
  // se van a la derecha por tener un 4 suelto en medio. Se mira sobre TODAS
  // las filas y no sobre las filtradas: si no, la tabla se movia de sitio
  // sola segun lo que hubiera escrito en el filtro.
  const numerica = r.columnas.map((_c, i) =>
    r.filas.every(f => f[i] === null || esNumero(f[i])));
  const cab = r.columnas.map((c, i) => {
    const activa = orden && orden.i === i;
    return '<th class="orden' + (numerica[i] ? " num" : "")
      + (activa ? " activa" : "") + '" data-col="' + i
      + '" title="Ordenar por esta columna">'
      + escapar((r.etiquetas && r.etiquetas[i]) || c.replace(/_/g, " "))
      + '<span class="flecha">'
      + (activa ? (orden.desc ? " ▼" : " ▲") : "")
      + "</span></th>";
  }).join("");
  if (!filas.length){
    caja.innerHTML = '<table><thead><tr>' + cab + "</tr></thead></table>"
      + '<p class="vacio">Nada con «' + escapar(busca) + '».</p>';
    engancharCabeceras();
    return;
  }

  // El orden va sobre lo filtrado y ANTES de partir en paginas: ordenar solo
  // las diez que se ven no es ordenar nada.
  if (orden && orden.i < r.columnas.length){
    const i = orden.i, signo = orden.desc ? -1 : 1;
    // Copia: `filas` puede ser el propio `r.filas`, y ordenarlo por dentro
    // perderia el orden que trae la vista, que es al que se vuelve al soltar.
    filas = filas.slice().sort((a, b) => {
      const x = a[i], y = b[i];
      // Los NULL, siempre abajo. Son «no se puede saber», y de mayor a menor
      // se colarian arriba como si fueran el valor mas alto de todos.
      if (x === null && y === null) return 0;
      if (x === null) return 1;
      if (y === null) return -1;
      if (numerica[i]) return (x - y) * signo;
      // `numeric` para que "partida 10" no vaya detras de "partida 2", y
      // `base` para que los acentos y las mayusculas no barajen los apodos.
      return String(x).localeCompare(String(y), "es",
                {numeric: true, sensitivity: "base"}) * signo;
    });
  }
  // El paginado va sobre lo FILTRADO, no sobre el total: filtrar y que te
  // deje en una pagina vacia porque la 4 ya no existe es peor que no filtrar.
  const paginas = verTodas ? 1 : Math.ceil(filas.length / POR_PAGINA);
  if (pagina >= paginas) pagina = paginas - 1;
  if (pagina < 0) pagina = 0;
  const trozo = (verTodas || paginas <= 1)
    ? filas
    : filas.slice(pagina * POR_PAGINA, (pagina + 1) * POR_PAGINA);

  const aguja = busca.toLowerCase();
  const cuerpo = trozo.map(f => "<tr>" + f.map((v, i) => {
    const clases = (numerica[i] ? "num" : "") + (v === null ? " nada" : "");
    let texto;
    if (v === null){
      // NULL no es 0 ni cadena vacia y aqui importa: es "no se puede saber".
      texto = "—";
    } else if (esNumero(v)){
      // O coincide entero o no se marca: marcar el "4" de dentro de un 30.4
      // llena la tabla de verde sin querer decir nada.
      texto = coincide(v, clave, busca)
        ? "<mark>" + escapar(v) + "</mark>" : escapar(v);
    } else {
      texto = resaltar(fecha(v), aguja);
    }
    return '<td class="' + clases.trim() + '">' + texto + "</td>";
  }).join("") + "</tr>").join("");
  let pie = "";
  if (filas.length > POR_PAGINA){
    const desde = verTodas ? 1 : pagina * POR_PAGINA + 1;
    const hasta = verTodas ? filas.length
                           : Math.min(filas.length, (pagina + 1) * POR_PAGINA);
    pie = '<div class="paginas">'
        + '<button id="pAnt"' + ((verTodas || pagina === 0) ? " disabled" : "")
        + ">&lsaquo; anteriores</button>"
        + '<span class="cuantas">' + desde + "&ndash;" + hasta + " de "
        + filas.length + (verTodas ? "" : "  ·  pagina " + (pagina + 1)
                                          + " de " + paginas) + "</span>"
        + '<button id="pSig"'
        + ((verTodas || pagina >= paginas - 1) ? " disabled" : "")
        + ">siguientes &rsaquo;</button>"
        + '<button id="pTodas">' + (verTodas ? "de 10 en 10" : "ver todas")
        + "</button></div>";
  }
  caja.innerHTML = '<table><thead><tr>' + cab + "</tr></thead><tbody>"
    + cuerpo + "</tbody></table>" + pie;
  engancharCabeceras();
  const ant = document.getElementById("pAnt");
  const sig = document.getElementById("pSig");
  const tod = document.getElementById("pTodas");
  if (ant) ant.onclick = () => { pagina--; dibujar(); };
  if (sig) sig.onclick = () => { pagina++; dibujar(); };
  // «Ver todas» se queda puesto al cambiar de vista a proposito: si lo has
  // pedido una vez, es que prefieres la tabla entera.
  if (tod) tod.onclick = () => { verTodas = !verTodas; pagina = 0; dibujar(); };
}

async function traerVista(){
  if (!vistaElegida) return;
  // Un numero es una partida; cualquier otra cosa es el ambito.
  const elegido = document.getElementById("selPartida").value;
  const esPartida = /^[0-9]+$/.test(elegido);
  const partida = esPartida ? elegido : "";
  const ambito = esPartida ? "" : (elegido || "amigos");
  // Con una partida suelta, el tamanio de mesa no pinta nada: esa partida
  // era de los que era. Se apaga el desplegable en vez de ignorarlo por
  // dentro, que es la diferencia entre «no aplica» y «no funciona».
  const selMesa = document.getElementById("selMesa");
  selMesa.disabled = esPartida;
  const mesa = esPartida ? "" : (selMesa.value || "todas");
  const v = ((catalogoVistas && catalogoVistas.vistas) || [])
              .find(x => x.nombre === vistaElegida);
  // El resumen ya esta en la ficha, asi que aqui va lo otro que hace falta
  // saber y no se ve en ningun sitio: como pedir POR CONSOLA exactamente esto
  // que se esta viendo. La vista guardada en la base es la de amigos, asi que
  // para los otros dos ambitos el comando es otro -- y decir el de siempre
  // seria mandar a la consola a por una tabla distinta de la de la pantalla.
  let comando = "";
  if (v && esPartida){
    comando = "py db/vistas.py --ver " + v.nombre + " --partida " + partida;
  } else if (v && ambito === "amigos" && mesa === "todas"){
    // El atajo del `sql.py` solo vale para la vista TAL COMO ESTA GUARDADA,
    // que es la de amigos y todas las mesas. Con cualquier filtro encima hay
    // que pasar por `db/vistas.py`, o el comando daria una tabla distinta de
    // la que se esta mirando.
    comando = 'py sql.py "SELECT * FROM ' + v.nombre + '"';
  } else if (v){
    comando = "py db/vistas.py --ver " + v.nombre + " --ambito " + ambito
            + (mesa === "todas" ? "" : " --mesa " + mesa);
  }
  document.getElementById("queEs").textContent = comando
    ? "En la ventana negra:  " + comando : "";
  for (const b of document.querySelectorAll("#botonesVista button"))
    b.classList.toggle("elegida", b.dataset.vista === vistaElegida);
  document.getElementById("tablaVista").innerHTML =
    '<p class="vacio">leyendo...</p>';
  try {
    pintarTabla(await pedir("/vista?nombre=" + encodeURIComponent(vistaElegida)
                            + "&partida=" + encodeURIComponent(partida)
                            + "&ambito=" + encodeURIComponent(ambito)
                            + "&mesa=" + encodeURIComponent(mesa)));
  } catch (err) { marcarCaido(true); }
}

// --- los titulares ------------------------------------------------------
//
// Cinco frases con su numero y el enlace a la tabla de donde sale. El enlace
// NO abre otra pagina: elige esa vista ahi abajo y baja hasta la tabla, que
// es todo el enlace que hace falta y ademas deja el filtro y el desplegable
// de partida donde estaban.
async function traerTitulares(){
  const donde = document.getElementById("titulares");
  if (!donde) return;
  let t;
  try { t = await pedir("/titulares"); }
  catch (err) { marcarCaido(true); return; }
  if (t.error){
    donde.innerHTML = '<p class="vacio">' + escapar(t.error) + "</p>";
    const rec = document.getElementById("records");
    if (rec) rec.innerHTML = "";
    return;
  }
  const min = document.getElementById("titMinimo");
  if (min) min.textContent = t.minimo;
  // Cuando no llega nadie, el hueco tiene que explicarse. Un panel con las
  // fichas vacias y sin motivo se lee como que algo esta roto, y lo que pasa
  // es que todavia no hay partidas suficientes -- que es justo lo que se
  // quiere decir el primer dia que alguien clona esto.
  const quienes = document.getElementById("titQuienes");
  if (quienes){
    if (t.cuantos_llegan > 0){
      quienes.textContent = "Ahora mismo llegan " + t.cuantos_llegan + ".";
    } else if (t.el_que_mas){
      quienes.textContent = "Todavia no llega nadie: el que mas lleva es "
        + t.el_que_mas.quien + " con " + t.el_que_mas.partidas + ".";
    } else {
      quienes.textContent = "Todavia no hay ninguna partida guardada.";
    }
  }
  donde.innerHTML = t.titulares.map(ficha).join("");
  enganchar(donde);
  const rec = document.getElementById("records");
  if (rec){
    rec.innerHTML = (t.records || []).map(ficha).join("");
    enganchar(rec);
  }
}

// Titulares y records se pintan igual. La unica diferencia es que un record
// lleva partida, y eso son dos cosas: una linea mas en la ficha y un enlace
// que ademas FILTRA por ella.
function ficha(x){
  return '<div class="titular"><div class="pregunta">' + escapar(x.titulo)
    + "</div>"
    + (x.falta
        ? '<div class="falta">' + escapar(x.falta) + "</div>"
        : '<div class="quien">' + escapar(x.quien)
          + ' <span class="cifra">' + escapar(x.cifra) + "</span></div>"
          + '<div class="detalle">' + escapar(x.detalle) + "</div>"
          + (x.tambien ? '<div class="tambien">' + escapar(x.tambien) + "</div>" : "")
          + (x.partida === undefined ? ""
             : '<div class="cuando">partida ' + Number(x.partida)
               + " &middot; " + escapar(x.dia) + "</div>"))
    + '<button data-vista="' + escapar(x.vista) + '"'
    + (x.partida === undefined ? "" : ' data-partida="' + Number(x.partida) + '"')
    + ">" + escapar(x.vista_titulo) + " &rarr;</button></div>";
}

function enganchar(donde){
  for (const b of donde.querySelectorAll("button[data-vista]"))
    b.onclick = () => {
      const sel = document.getElementById("selPartida");
      // El desplegable tiene que acabar donde esta el numero que acabas de
      // leer. Un record es de UNA partida, asi que se filtra por ella; un
      // titular es de todas, y si el desplegable se habia quedado en una
      // sola, el numero de la ficha no estaria en la tabla de al lado.
      if (b.dataset.partida) sel.value = b.dataset.partida;
      else if (/^[0-9]+$/.test(sel.value)) sel.value = "amigos";
      vistaElegida = b.dataset.vista;
      traerVista();
      document.getElementById("tablaVista")
              .scrollIntoView({behavior: "smooth", block: "center"});
    };
}

async function traerCatalogo(){
  let c;
  try { c = await pedir("/vistas"); }
  catch (err) { marcarCaido(true); return; }
  catalogoVistas = c;
  const botones = document.getElementById("botonesVista");
  if (c.error || !c.vistas.length){
    botones.innerHTML = "";
    document.getElementById("tablaVista").innerHTML =
      '<p class="vacio">' + escapar(c.error || "no hay vistas") + "</p>";
    return;
  }
  // El desplegable lleva dos cosas que no son la misma: ARRIBA de que grupo
  // de partidas se saca el total, y ABAJO una partida suelta. Van juntos
  // porque son excluyentes -- una partida concreta es una partida, y el
  // grupo ya no pinta nada -- y en dos controles se podria dejar puesto uno
  // que no hace nada.
  const sel = document.getElementById("selPartida");
  const antes = sel.value;
  const ambitos = c.ambitos || [{id: "amigos", texto: "solo con amigos"}];
  sel.innerHTML = '<optgroup label="Todas las partidas">'
    + ambitos.map(a => '<option value="' + escapar(a.id) + '">'
        + escapar(a.texto) + "</option>").join("")
    + "</optgroup>"
    + (c.partidas.length ? '<optgroup label="Una sola partida">'
        + c.partidas.map(p => '<option value="' + Number(p.id) + '">partida '
            + Number(p.id) + "  ·  " + escapar(p.texto) + "</option>").join("")
        + "</optgroup>" : "");
  if (antes) sel.value = antes;
  if (!sel.value) sel.value = "amigos";
  const selMesa = document.getElementById("selMesa");
  const mesaAntes = selMesa.value;
  selMesa.innerHTML = (c.mesas || [{id: "todas", texto: "todas"}])
    .map(m => '<option value="' + escapar(m.id) + '">' + escapar(m.texto)
              + "</option>").join("");
  if (mesaAntes) selMesa.value = mesaAntes;
  if (!selMesa.value) selMesa.value = "todas";
  // Por grupos, cada uno con su titulo. Sin esto, la rejilla parte las
  // parejas entre filas segun lo ancha que sea la pantalla y «El ladron» y
  // «El ladron, uno a uno» acaban pareciendo cosas de temas distintos.
  //
  // Titulo y resumen en la propia ficha. `escapar` en los tres: salen de
  // db/vistas.py, pero el que escribe HTML sin escapar "porque este texto es
  // mio" es el que un dia mete uno que no lo es.
  let html = "", grupoActual = null;
  for (const v of c.vistas){
    if (v.grupo !== grupoActual){
      if (grupoActual !== null) html += "</div>";
      html += '<h3 class="grupo">' + escapar(v.grupo) + '</h3><div class="fichas">';
      grupoActual = v.grupo;
    }
    html += '<button data-vista="' + escapar(v.nombre) + '"><b>'
          + escapar(v.titulo) + "</b><small>" + escapar(v.que || "")
          + "</small></button>";
  }
  if (grupoActual !== null) html += "</div>";
  botones.innerHTML = html;
  for (const b of botones.querySelectorAll("button"))
    b.onclick = () => { vistaElegida = b.dataset.vista; traerVista(); };
  // Casi todas las consultas se apoyan en las vistas base, asi que si faltan
  // no hay nada que enseñar. Se dice y no se intenta: un error de SQLite en
  // crudo no le dice a nadie que lo que falta es crearlas.
  if (c.faltan && c.faltan.length){
    document.getElementById("tablaVista").innerHTML =
      '<p class="vacio">Faltan vistas por crear (' + c.faltan.length + '). '
      + "En la ventana negra: <code>py db/vistas.py --crear</code></p>";
    return;
  }
  if (!vistaElegida && c.vistas.length){
    vistaElegida = (c.vistas.find(v => v.nombre === "amigos_marcador")
                    || c.vistas[0]).nombre;
    traerVista();
  }
}

document.getElementById("selPartida").onchange = traerVista;
document.getElementById("selMesa").onchange = traerVista;
// El filtro no vuelve a preguntar al servidor: filtra lo que ya esta en la
// pagina. Asi va instantaneo mientras escribes y no manda una consulta por
// cada tecla.
// Y al escribir se vuelve a la primera pagina: filtrar desde la pagina 6 y
// quedarte mirando el hueco donde ya no hay nada es peor que no filtrar.
document.getElementById("filtro").oninput = () => { pagina = 0; dibujar(); };

async function refrescar(){
  let e;
  try { e = await pedir("/estado"); }
  catch (err) { marcarCaido(true); return; }
  document.getElementById("donde").textContent =
    e.juego ? (e.juego + (e.plugin ? "  ·  plugin instalado"
                                   : "  ·  SIN plugin instalado"))
            : "No encuentro Catan Universe. Abre Steam una vez si lo has movido.";

  // La mitad de abajo --leer el tablero de la pantalla y entrenar la red--
  // sale SOLO si esta en esta copia. Quien clone el repositorio sin ella no
  // ve botones que no llevan a ninguna parte, y no hay que configurar nada:
  // el panel mira si los ficheros estan. `--como-usuario` fuerza esta vista
  // teniendolo todo, para poder ver lo que ve otro.
  // La pagina se relee de panel.py en cada peticion; el codigo del servidor
  // no. Un panel abierto de antes sirve botones nuevos contra rutas que en
  // su proceso no existen, y eso da un 404 mudo. Aqui se dice.
  // Las vistas de SU base contra las de ESTE codigo. Va en ambar y no en
  // rojo a proposito: no esta roto nada, solo desactualizado, y se arregla
  // con un boton que esta ahi abajo.
  const vv = e.vistas_viejas || [];
  const cajaVV = document.getElementById("vistasviejas");
  if (cajaVV){
    cajaVV.style.display = vv.length ? "block" : "none";
    const q = document.getElementById("vistasviejasq");
    if (q) q.textContent = vv.length
      ? "Son " + vv.length + ": " + vv.slice(0, 4).join(", ")
        + (vv.length > 4 ? "..." : "") + "."
      : "";
  }
  document.getElementById("desfase").style.display =
    e.codigo_viejo ? "block" : "none";

  // El bloque 0 solo existe mientras falte algo. Cuando esta todo puesto
  // desaparece, y el panel empieza donde tiene que empezar: en jugar.
  const falta = !e.juego || !e.bepinex || !e.plugin;
  document.getElementById("bloqueInstalar").style.display = falta ? "" : "none";
  if (falta){
    document.getElementById("pasoInstalar").innerHTML =
      !e.juego ? "No encuentro Catan Universe. Abre Steam una vez, o instala " +
                 "el juego, y recarga esta pagina."
      : (!e.bepinex ? "Falta <b>BepInEx</b>, que es lo que deja que el mod se " +
                      "cargue, y el plugin. Un boton."
                    : "BepInEx ya esta; falta compilar el <b>plugin</b>. Un boton.");
  }

  const banda = document.getElementById("banda");
  if (e.mod === null){
    banda.className = "banda off";
    banda.innerHTML = "El mod no esta instalado en el juego." +
      "<small>Dale a <b>Dejarlo listo</b>, aqui debajo.</small>";
    document.title = "Catan Tracker";
  } else if (e.mod){
    banda.className = "banda on";
    let apunte = "";
    if (e.apunta && e.apunta.viva){
      apunte = " &mdash; apuntando: <b>" + e.apunta.acciones + "</b> acciones";
    } else if (e.apunta){
      apunte = " &mdash; ultima partida apuntada: " + e.apunta.acciones + " acciones";
    }
    banda.innerHTML = "EL MOD ESTA ENCENDIDO" + (e.grabando ? " y grabando" : "") + apunte +
      "<small>Modificar el cliente va contra las condiciones de uso de Catan " +
      "Universe, y esto se carga en todas las partidas mientras este puesto. " +
      "Apagalo al terminar.</small>";
    document.title = "● MOD ENCENDIDO — Catan Tracker";
  } else if (e.juego_abierto){
    // apagado en el fichero, pero el proceso que hay abierto pudo arrancar
    // con el mod dentro: el interruptor solo decide como arranca la
    // SIGUIENTE vez
    banda.className = "banda ojo";
    banda.innerHTML = "El interruptor esta apagado, pero Catan esta abierto." +
      "<small>El mod se mete dentro del juego al arrancarlo, asi que si abriste " +
      "esta partida con el mod encendido, sigue cargado. <b>Para descargarlo hay " +
      "que cerrar Catan y volver a abrirlo.</b></small>";
    document.title = "▲ cierra Catan — Catan Tracker";
  } else {
    banda.className = "banda off";
    banda.innerHTML = "El mod esta apagado y Catan cerrado. " +
      "El juego arrancara limpio.";
    document.title = "Catan Tracker";
  }

  const bE = document.getElementById("bEmpezar");
  if (bE) bE.disabled = e.grabando || !e.juego;
  document.getElementById("bParar").disabled   = !e.grabando && !e.mod;
  document.getElementById("bMatar").disabled   = !e.tarea_viva;
  // Con `?.` porque la mitad de estos botones puede no estar en la pagina:
  // los trozos marcados se quitan en el servidor, no se esconden.
  for (const id of ["bComprobar","bDataset","bRutina","bHistorial","bTablero",
                    "bMedir","bEntrenar","bEntrenarTodo","bPruebas",
                    "bMirar","bEnsayo","bMesa","bVistas","bPruebasDatos"]){
    const b = document.getElementById(id);
    if (b) b.disabled = e.tarea_viva;
  }

  document.getElementById("paso1").innerHTML = e.grabando
    ? "Grabando. Abre Catan y juega. Puedes encadenar <b>varias partidas "
      + "seguidas sin tocar nada</b>: cada una se guarda en su carpeta sola. "
      + "Cuando termines del todo, <b>Parar y apagar el mod</b>."
    : "Enciende el mod y se pone a grabar. Despues abre Catan y juega. ";
      

  // Al recargar la pagina, `fuente` vuelve a "tarea". Si el mod esta
  // encendido y no hay ninguna tarea de la que enseniar nada, el registro se
  // quedaba vacio teniendo cosas que contar: se engancha solo al mod. Con
  // una tarea detras NO se toca, que su log es lo que se ha ido a mirar.
  if (fuente === "tarea" && !e.tarea && e.mod){ fuente = "mod"; pos = 0; }

  const t = document.getElementById("tituloReg");
  t.textContent = fuente === "mod" ? "Registro · lo que apunta el mod"
    : fuente === "grabacion" ? "Registro · grabacion"
    : (e.tarea ? "Registro · " + e.tarea : "Registro");

  const filas = e.partidas.length
    ? e.partidas.map(p => "<tr><td>" + p.nombre + "</td><td>" + p.fotos +
        " fotos · " + (p.preparada ? "preparada" : "sin preparar") +
        "</td></tr>").join("")
    : "<tr><td>Ninguna todavia.</td></tr>";
  const tp = document.getElementById("partidas");
  if (tp) tp.innerHTML = filas;
  const tm = document.getElementById("modelo");
  if (tm) tm.textContent = e.modelo;

  // Al acabar una tarea puede haber partidas nuevas en la base (importar) o
  // vistas recien creadas. Se relee el catalogo, pero NO la tabla: si la
  // estabas leyendo, que no se te mueva debajo.
  if (tareaViva === true && e.tarea_viva === false) { traerCatalogo(); traerTitulares(); }
  // Y si la base ha cambiado por su cuenta -- una importacion por consola --
  // tambien. Sin esto habia que recargar la pagina y nada lo decia.
  if (selloBase !== null && e.sello_base !== selloBase) { traerCatalogo(); traerTitulares(); }
  selloBase = e.sello_base === undefined ? null : e.sello_base;
  tareaViva = e.tarea_viva;
}

async function traerRegistro(){
  let r;
  try { r = await pedir("/registro?fuente=" + fuente + "&desde=" + pos); }
  catch (err) { marcarCaido(true); return; }
  if (r.reinicio) { document.getElementById("registro").textContent = ""; pos = 0; }
  if (r.lineas.length){
    const pre = document.getElementById("registro");
    if (pre.textContent === "(nada todavia)") pre.textContent = "";
    const abajo = pre.scrollTop + pre.clientHeight >= pre.scrollHeight - 30;
    pre.textContent += r.lineas.join("\n") + "\n";
    if (abajo) pre.scrollTop = pre.scrollHeight;
  }
  pos = r.hasta;
}

refrescar(); traerRegistro(); traerCatalogo(); traerTitulares();
setInterval(refrescar, 2000);
setInterval(traerRegistro, 700);
</script>
</div></body></html>
"""


class Manejador(BaseHTTPRequestHandler):
    server_version = "CatanPanel/1.0"

    def log_message(self, *a):
        pass      # la consola es para lo que imprime el panel, no para cada GET

    def _responder(self, codigo, tipo, cuerpo):
        self.send_response(codigo)
        self.send_header("Content-Type", tipo)
        self.send_header("Content-Length", str(len(cuerpo)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(cuerpo)

    def _json(self, dato):
        self._responder(200, "application/json; charset=utf-8",
                        json.dumps(dato, ensure_ascii=False).encode("utf-8"))

    def do_GET(self):
        ruta, _, consulta = self.path.partition("?")
        if ruta == "/":
            pagina = _pagina_para(_pagina_al_dia(), hay_desarrollo(),
                                  hay_vision())
            pagina = _con_idioma(pagina,
                                 _idioma_pedido(self.headers, consulta))
            return self._responder(200, "text/html; charset=utf-8",
                                   pagina.encode("utf-8"))
        if ruta == "/estado":
            return self._json(
                estado(_idioma_pedido(self.headers, consulta)))
        if ruta == "/vistas":
            return self._json(
                catalogo(_idioma_pedido(self.headers, consulta)))
        if ruta == "/gente":
            return self._json(gente())
        if ruta == "/titulares":
            return self._json(
                titulares(_idioma_pedido(self.headers, consulta)))
        if ruta == "/preguntar":
            args = dict(p.split("=", 1) for p in consulta.split("&") if "=" in p)
            # La pregunta es texto libre, pero no toca SQL en ningun momento:
            # se parte en palabras y se compara con nombres de vistas y de
            # columnas. Lo unico que sale de aqui son vistas que ya existen.
            return self._json(preguntar(
                unquote(args.get("q", "")).replace("+", " "),
                unquote(args.get("ambito", "")) or "amigos"))
        if ruta == "/vista":
            args = dict(p.split("=", 1) for p in consulta.split("&") if "=" in p)
            partida = args.get("partida") or ""
            try:
                # "" es «todas»; cualquier otra cosa tiene que ser un numero,
                # que ademas es lo que impide que llegue SQL por aqui.
                partida = int(partida) if partida else None
            except ValueError:
                return self._json({"error": "la partida tiene que ser un numero"})
            # El ambito y la mesa llegan por su nombre, y las dos funciones
            # que los traducen solo aceptan los valores que hay: por aqui
            # tampoco entra SQL.
            ambito = unquote(args.get("ambito", "")) or None
            mesa = unquote(args.get("mesa", "")) or None
            return self._json(ver_vista(
                unquote(args.get("nombre", "")), partida, ambito, mesa,
                _idioma_pedido(self.headers, consulta)))
        if ruta == "/registro":
            args = dict(p.split("=", 1) for p in consulta.split("&") if "=" in p)
            # El mod no es una tarea del panel --escribe el juego, en un
            # fichero-- asi que no tiene un proceso del que leer la salida.
            # Se le da la misma forma para que la caja no note la diferencia.
            if args.get("fuente") == "mod":
                try:
                    desde = int(args.get("desde", 0))
                except ValueError:
                    desde = 0
                hasta, lineas = _apuntes_desde(desde)
                return self._json({"hasta": hasta, "lineas": lineas,
                                   "reinicio": desde > hasta})
            proceso = grabacion if args.get("fuente") == "grabacion" else tarea
            try:
                desde = int(args.get("desde", 0))
            except ValueError:
                desde = 0
            hasta, lineas = proceso.desde(desde)
            # si el proceso se ha reiniciado, la pagina va por delante del
            # registro y hay que decirle que lo borre y empiece de cero
            return self._json({"hasta": hasta, "lineas": lineas,
                               "reinicio": desde > hasta})
        return self._responder(404, "text/plain; charset=utf-8", b"no existe")

    def do_POST(self):
        largo = int(self.headers.get("Content-Length") or 0)
        try:
            cuerpo = json.loads(self.rfile.read(largo) or b"{}")
        except ValueError:
            cuerpo = {}

        if self.path == "/grabar":
            arrancar = bool(cuerpo.get("arrancar"))
            solo_mod = bool(cuerpo.get("solo_mod"))
            print("[panel] %s" % ("encender solo el mod" if arrancar and solo_mod
                                  else "empezar a grabar" if arrancar
                                  else "parar y apagar el mod"))
            if arrancar and solo_mod:
                ok, error = solo_encender_el_mod()
            elif arrancar:
                ok, error = empezar_a_grabar()
            else:
                ok, error = dejar_de_grabar()
            print("[panel]    %s" % ("hecho" if ok else "FALLO: %s" % error))
            return self._json({"ok": ok, "error": None if ok else error})

        # Va por POST y no por GET a proposito: es lo unico del panel que
        # BORRA. Un GET se puede disparar desde un enlace, desde el historial
        # o desde el precargado del navegador, y eso para algo sin deshacer
        # no vale.
        if self.path == "/quitar":
            r = quitar_partida(cuerpo.get("partida"), cuerpo.get("motivo", ""))
            print("[panel] quitar partida %s: %s"
                  % (cuerpo.get("partida"),
                     "hecho" if r.get("ok") else "FALLO: %s" % r.get("error")))
            return self._json(r)

        if self.path == "/tarea":
            que = cuerpo.get("que")
            if que not in TAREAS:
                return self._json({"ok": False, "error": "no se que es %r" % que})
            nombre, orden = TAREAS[que]
            # Esconder el boton no basta: la ruta sigue ahi y contesta a
            # cualquiera que la llame. Si esa mitad no esta, no se arranca.
            # Dos motivos para no arrancar algo, y los dos hay que
            # mirarlos: que sea de la mitad que no se ensena, o que
            # sencillamente no este su fichero. Lo segundo no es hipotetico:
            # `mirar` SI se ensena, y aun asi puede no estar.
            script = _script_de(orden)
            if ((_es_de_desarrollo(orden) and not hay_desarrollo())
                    or (script and not os.path.isfile(script))):
                return self._json({"ok": False, "error":
                                   "«%s» no esta disponible" % nombre})
            ok, error = tarea.arrancar(nombre, orden)
            print("[panel] %s%s" % (nombre, "" if ok else "  FALLO: %s" % error))
            return self._json({"ok": ok, "error": error})

        if self.path == "/llamar":
            red = str(cuerpo.get("red") or "")
            nombre = str(cuerpo.get("nombre") or "")
            ok, error = poner_nombre(red, nombre)
            print("[panel] ponerle nombre a %s: %s"
                  % (red, "hecho" if ok else "FALLO: %s" % error))
            return self._json({"ok": ok, "error": None if ok else error})

        if self.path == "/matar":
            print("[panel] parar la tarea")
            tarea.matar()
            return self._json({"ok": True})

        return self._responder(404, "text/plain; charset=utf-8", b"no existe")


def main():
    global MODO_USUARIO
    # `--simple` deja el panel en lo que hace falta para tener tus datos. Es
    # tambien lo que ve quien se descarga el proyecto sin la mitad de
    # entrenar, asi que sirve para comprobarlo sin borrarse nada.
    #
    # No se anuncia por consola a proposito: la pagina que sale tiene que
    # parecer entera, porque lo es -- no es una version recortada de nada,
    # es el panel de usar esto.
    #
    # Sin argparse: es un solo interruptor y meter una dependencia de sintaxis
    # en el arranque del panel no compensa.
    MODO_USUARIO = "--simple" in sys.argv
    juego = carpeta_del_juego()
    try:
        servidor = ThreadingHTTPServer(("127.0.0.1", PUERTO), Manejador)
    except OSError as e:
        # Lo tipico: ya hay otro panel abierto. Sin este mensaje el .bat
        # escupe un traceback y no se entiende que la solucion es usar la
        # pestana que ya esta abierta.
        print("No he podido abrir el panel en el puerto %d:" % PUERTO)
        print("   %s" % e)
        print()
        print("Casi seguro que ya tienes otro panel abierto. Mira si hay otra")
        print("ventana negra como esta, o abre http://127.0.0.1:%d" % PUERTO)
        return 1
    url = "http://127.0.0.1:%d" % PUERTO
    print("Panel de Catan Tracker")
    print("   %s" % url)
    print("   juego: %s" % (juego or "NO ENCONTRADO"))
    if _mod_encendido(juego):
        print("   AVISO: el mod esta ENCENDIDO ahora mismo.")
    print()
    print("Deja esta ventana abierta. Ctrl+C para cerrar el panel.")
    _refrescar_modelo()
    try:
        webbrowser.open(url)
    except Exception:
        pass
    try:
        servidor.serve_forever()
    except KeyboardInterrupt:
        print()
        print("Panel cerrado.")
        # lo que se dejo corriendo se deja corriendo: si el panel se cierra a
        # mitad de una partida, cortar la grabacion seria perderla entera.
        if grabacion.vivo or _recopilando():
            print("OJO: la grabacion sigue en marcha, y el mod encendido.")
            print("     Vuelve a abrir el panel para pararla, o:")
            print("     powershell -ExecutionPolicy Bypass -File "
                  ".\\mod_verdad\\interruptor.ps1 off")
    return 0


if __name__ == "__main__":
    sys.exit(main())
