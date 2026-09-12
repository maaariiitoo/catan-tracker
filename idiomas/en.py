# -*- coding: utf-8 -*-
"""English.

Un fichero por idioma, y todos con la misma forma. Para añadir el francés se
copia éste, se traduce y se llama `fr.py`: `idiomas/__init__.py` lo encuentra
solo y el botón del panel lo mete en la vuelta sin tocar nada.

Los cinco diccionarios son cinco sitios distintos de donde sale texto, y
ninguno avisa solo si se queda vacío -- por eso `db/pruebas.py` los exige los
cinco enteros:

  TEXTO      lo que hay entre etiquetas de la página, y los atributos que se
             leen (el gris de una caja de busqueda, el globo del ratón)
  GUION      las cadenas que escribe el JavaScript, con sus comillas
  FRASES     lo que manda el servidor: títulos de tabla, titulares, filtros,
             nombres de tarea. LAS LLAVES `{}` SE RESPETAN: son nombres de
             columna y se rellenan con números
  COLUMNAS   las cabeceras de las tablas. La clave es el nombre en SQL y no
             se traduce nunca; lo que cambia es la etiqueta que se pinta
  COMUNES    qué quiere decir cada columna y qué es una fila. Esto NO sale
  POR_VISTA  en el panel: es lo que escribe `py db/catalogo.py` en el
  FILA_ES    catálogo. No se escribe aquí: se trae de `catalogEN.py`, que
             está en inglés entero, nombres de columna incluidos
"""

NOMBRE = "English"

# Cómo se llama este idioma en el desplegable de la cabecera. Lleva delante
# el código de dos letras para que se reconozca de un vistazo aunque no
# entiendas la palabra de al lado.
BOTON = "EN  English"

# La coma decimal. Un inglés lee «3,18» como tres mil ciento dieciocho.
DECIMAL = "."

# El castellano es el original: no hay diccionario que valga, es la página tal
# cual está escrita. Aquí sólo van los DEMÁS.
TEXTO = {
    # --- la cabecera y los dos avisos de arriba -------------------------
    "Catan Tracker": "Catan Tracker",
    "buscando el juego...": "looking for the game...",
    "El panel no responde.": "The panel isn't responding.",
    "La ventana negra en la que arrancaste":
        "The black window you started",
    "panel.py": "panel.py",
    "se ha cerrado, o nunca llegó a abrirse. Vuelve a abrirla y recarga esta "
    "página; mientras tanto los botones de aquí no hacen nada.":
        "in has been closed, or never opened at all. Open it again and reload "
        "this page; until then the buttons here do nothing.",
    "El panel se ha quedado atr&aacute;s.":
        "The panel is out of date.",
    "Ha cambiado el": "The",
    "c&oacute;digo": "code",
    ", no s&oacute;lo la p&aacute;gina. La p&aacute;gina se relee sola y con":
        "has changed, not just the page. The page reloads itself and",
    "basta; el servidor no, as&iacute; que los botones nuevos pegan contra "
    "uno viejo y no hacen nada. Aqu&iacute; s&iacute; hay que cerrar la "
    "ventana negra y volver a abrirla.":
        "is enough for it; the server doesn't, so the new buttons hit an old "
        "one and do nothing. This time you do have to close the black window "
        "and open it again.",
    "Las tablas de tu base son de una versi&oacute;n anterior.":
        "The tables in your database are from an earlier version.",
    "Las 28 vistas se guardan": "The 28 views are stored",
    "dentro": "inside",
    "de tu fichero de datos, no en el c&oacute;digo, as&iacute; que al "
    "bajarte una versi&oacute;n nueva siguen siendo las de antes. No se "
    "pierde nada y no hace falta borrar nada: dale a":
        "your data file, not in the code, so downloading a new version leaves "
        "the old ones in place. Nothing is lost and nothing needs deleting: "
        "press",
    "Rehacer las vistas de la base": "Rebuild the database views",
    ", o importa una partida, que ya lo hace solo.":
        ", or import a game, which does it on its own.",

    # --- 0 · dejar el mod listo -----------------------------------------
    "0 &middot; Dejar el mod listo": "0 &middot; Get the mod ready",
    "Falta algo por instalar.": "Something still needs installing.",
    "Dejarlo listo": "Get it ready",
    "Busca Catan pregunt&aacute;ndoselo a Steam, mira si es de 32 o de 64 "
    "bits,":
        "It finds Catan by asking Steam, checks whether it's 32- or 64-bit,",
    "se descarga el BepInEx que toca": "downloads the right BepInEx",
    ", comprueba su SHA-256 antes de tocar nada y compila el plugin. Lo deja":
        ", verifies its SHA-256 before touching anything and compiles the "
        "plugin. It leaves it",
    "apagado": "switched off",
    ": instalarlo y encenderlo son dos decisiones distintas, y esto solo toma "
    "la primera.":
        ": installing it and switching it on are two different decisions, and "
        "this one only takes the first.",
    "Lo de 32 bits no es un detalle. Catan Universe es de 32 aunque tu Windows "
    "sea de 64, y con el paquete equivocado el juego arranca igual y el mod no "
    "carga":
        "The 32-bit thing is not a detail. Catan Universe is 32-bit even if "
        "your Windows is 64, and with the wrong package the game starts up "
        "fine and the mod",
    "nunca": "never",
    ", sin dar un solo error.": "loads, without a single error.",

    # --- 1 · jugar --------------------------------------------------------
    "1 &middot; Jugar": "1 &middot; Play",
    "Enciende el mod y": "Switch the mod on and",
    "despues": "then",
    "abre Catan, que el mod se carga al arrancar el juego. Juega lo que "
    "quieras: no hace falta cerrar Catan entre partidas, cambia de fichero "
    "solo. Al terminar, apagalo.":
        "open Catan, because the mod loads when the game starts. Play as much "
        "as you like: you don't have to close Catan between games, it switches "
        "files on its own. Switch it off when you're done.",
    "Encender el mod": "Switch the mod on",
    "Parar y apagar el mod": "Stop and switch the mod off",
    "El mod apunta": "The mod records",
    "solo informacion publica": "public information only",
    ": lo que ven todos los que estan en la mesa. Ni las manos de nadie, ni "
    "los puntos escondidos de las cartas, ni que carta se lleva un robo. Y no "
    "guarda ni una captura de pantalla: son unos pocos KB por partida.":
        ": what everyone at the table can see. Never anyone's hand, never the "
        "hidden victory points on cards, never which card a steal took. And it "
        "saves no screenshots at all: a few KB per game.",

    # --- 2 · guardar en la base -------------------------------------------
    "2 &middot; Guardar en la base de datos": "2 &middot; Save to the database",
    "Pasa lo que apunto el mod a las tablas de siempre: quien construyo que y "
    "cuando, las tiradas, el ladron, los robos, los comercios y la produccion "
    "de cada uno. Se puede dar tantas veces como quieras: las partidas que ya "
    "estan no se repiten.":
        "Moves what the mod recorded into the usual tables: who built what and "
        "when, the dice rolls, the robber, the steals, the trades and what "
        "each player produced. Press it as often as you like: games already "
        "saved don't get duplicated.",
    "Guardar en la base de datos": "Save to the database",
    "Ponerle nombre a alguien": "Name someone",
    "Quitar una partida": "Remove a game",
    "Cargar una base de datos": "Load a database",
    "Descargar la base de datos": "Download the database",
    "Estos dos son para jugar en mas de un ordenador sin partir el historico "
    "en dos.":
        "These two are for playing on more than one computer without "
        "splitting your history in two.",
    "te da el fichero": "hands you the",
    "catan_stats.db": "catan_stats.db",
    "para llevartelo, y": "file to take with you, and",
    "hace lo contrario: lo eliges aqui y este panel sigue con aquel "
    "historico.":
        "does the opposite: pick it here and this panel carries on with that "
        "history.",
    "Sustituye la base entera": "It replaces the whole database",
    ", no junta las dos. Antes de hacerlo comprueba que el fichero es de "
    "verdad la base del Catan y guarda una":
        ", it doesn't merge the two. Before doing it, it checks that the file "
        "really is the Catan database and keeps a",
    "copia de la de aqui": "backup of the one here",
    "dentro de": "inside",
    ", que tampoco hay deshacer. Las partidas que hubieras quitado a mano "
    "siguen fuera: eso es una decision tuya sobre tus grabaciones, no un dato "
    "de la base que llega.":
        ", because there's no undo here either. Games you removed by hand stay "
        "out: that's a decision you made about your own recordings, not a "
        "piece of data belonging to the database coming in.",
    "El mod no guarda nombres, guarda el identificador de cada cuenta, "
    "que es estable, asi que reconoce a la misma persona partida tras partida. "
    "La primera vez que juegue alguien nuevo saldra con un nombre provisional "
    "(":
        "The mod doesn't store names, it stores each account's identifier, "
        "which is stable, so it recognises the same person game after "
        "game. The first time someone new plays they show up under a "
        "placeholder name (",
    "jugador_4645eb8a": "jugador_4645eb8a",
    "); ponle el suyo ahi arriba y se arreglan tambien":
        "); give them their real one up there and it also fixes",
    "las partidas ya guardadas": "the games already saved",
    ", que si no el historico se parte en dos personas. Por consola es":
        ", because otherwise their history splits into two people. From the "
        "console it's",
    "py mod_verdad/importar.py --llamar &lt;identificador&gt; Pedro":
        "py mod_verdad/importar.py --llamar &lt;identifier&gt; Pedro",
    ", que es exactamente lo que hace el boton.":
        ", which is exactly what the button does.",
    "es para las que no deberian contar: una que se cancelo a medias entra":
        "is for the ones that shouldn't count: a game abandoned halfway goes "
        "in",
    "sin ganador y sin puntos": "with no winner and no score",
    ", y eso no se nota en la tabla: se nota en las medias. Antes de "
    "borrar hace una":
        ", and that doesn't show up in the table: it shows up in the "
        "averages. Before deleting it makes a",
    "copia de la base": "backup of the database",
    "copias/": "copias/",
    ", y apunta la grabacion para que el importador no la vuelva a meter.":
        ", and notes the recording down so the importer doesn't put it back.",
    "No borra las capturas": "It doesn't delete the screenshots",
    ": quitar una partida del historico no le hace perder un recorte a la "
    "vision. Y no hay deshacer, asi que pregunta.":
        ": removing a game from the history doesn't cost the vision half a "
        "single crop. And there's no undo, so it asks first.",

    # --- los titulares y los records --------------------------------------
    "Los titulares": "The headlines",
    "Lo que dicen las tablas": "What the tables say",
    "ahora mismo": "right now",
    ". No hay ni un nombre ni un n&uacute;mero escritos a mano: se recalculan "
    "en cada visita, as&iacute; que el d&iacute;a que alguien adelante a otro "
    "el titular cambia solo. Y el n&uacute;mero":
        ". Not one name and not one number is hardcoded: they are recomputed "
        "on every visit, so the day someone overtakes someone else the "
        "headline changes by itself. And the number",
    "sale de la misma consulta": "comes from the same query",
    "que pinta la tabla de abajo. Dale al enlace de cada uno y la "
    "tienes delante.":
        "that draws the table below. Click each one's link and there it "
        "is.",
    "Solo entra quien lleve": "Only people with",
    "partidas o m&aacute;s. Sin ese corte el titular se lo lleva siempre el "
    "que jug&oacute; una vez y tuvo un buen d&iacute;a, y en las tablas de "
    "abajo est&aacute;n todos igual.":
        "games or more get in. Without that cut-off the headline always goes "
        "to whoever played once and had a good day, and everyone is in the "
        "tables below regardless.",
    "cargando...": "loading...",
    "R&eacute;cords de una sola partida": "Single-game records",
    "La mejor marca de un d&iacute;a, y en qu&eacute; partida fue.":
        "The best mark from one day, and which game it was.",
    "Aqu&iacute; no hay m&iacute;nimo": "There's no minimum here",
    ", a prop&oacute;sito: un titular es una costumbre y pide partidas; un "
    "r&eacute;cord es de un d&iacute;a, y si en tu primera te pusieron "
    "veintiún ladrones, te los pusieron. El enlace abre esa tabla":
        ", on purpose: a headline is a habit and needs games behind it; a "
        "record is one day, and if you got the robber twenty-one times in your "
        "very first game, then you did. The link opens that table",
    "ya filtrada por esa partida": "already filtered to that game",

    # --- 3 · mirar los datos ----------------------------------------------
    "3 &middot; Mirar los datos": "3 &middot; Look at the data",
    "Elige que partidas quieres mirar y dale a lo que sea. De serie salen":
        "Choose which games you want to look at and press anything. By default "
        "you get",
    "solo las de amigos": "only the ones with friends",
    ": una partida contra la IA es otro juego -- la maquina no propone tratos "
    "ni bloquea igual -- y mezclarla con las de la mesa no ensucia un poco la "
    "media, la deja sin significado. Las otras dos opciones estan para cuando "
    "SI las quieres.":
        ": a game against the AI is a different game -- the machine doesn't "
        "propose trades or block the same way -- and mixing it in with the "
        "real table doesn't make the average slightly dirty, it makes it "
        "meaningless. The other two options are there for when you DO want "
        "them.",
    "O preguntalo en cristiano y te lo busco en las tablas:":
        "Or just ask in plain language and it looks it up in the tables"
        ":",
    "cuantos caballeros le han caido a elGato":
        "how many knights has elGato had",
    "quien ha tenido mas suerte": "who has had the most luck",
    "cuanto mineral ha producido carla": "how much ore has carla produced",
    ". No hay ninguna inteligencia artificial detras y no sale nada de este "
    "ordenador: la pregunta se parte en palabras y se busca entre los nombres "
    "de las vistas. Debajo de la respuesta sale siempre":
        ". There is no artificial intelligence behind this and nothing leaves "
        "this computer: the question is split into words and matched against "
        "the names of the views. Under the answer you always get",
    "de donde ha salido el numero": "where the number came from",
    "Buscar": "Search",
    "Que partidas": "Which games",
    "solo con amigos (sin la IA)": "only with friends (no AI)",
    "De cuantos": "How many players",
    "mesas de cualquier tama&ntilde;o": "tables of any size",
    "Una partida de": "A game of",
    "5 o 6": "5 or 6",
    "no es la misma con dos sillas m&aacute;s: el tablero tiene 30 casillas en "
    "vez de 19 y no reparte los n&uacute;meros igual, y se juega a 12 puntos y "
    "no a 10. Mezclarlas es el mismo problema que mezclar las de la IA, por "
    "eso el filtro se parece. Ahora mismo son":
        "is not the same game with two more chairs: the board has 30 tiles "
        "instead of 19 and doesn't lay the numbers out the same way, and it's "
        "played to 12 points instead of 10. Mixing them is the same problem as "
        "mixing in the AI games, which is why the filter looks alike. Right "
        "now that's",
    "3 de 18": "3 out of 18",
    ", as&iacute; que de serie salen todas. Separarlas lo decides "
    "t&uacute;.":
        ", so by default you get all of them. Splitting them up is your "
        "call.",
    "Sale de las mismas vistas que": "This comes from the same views as",
    'py sql.py "SELECT * FROM amigos_marcador"':
        'py sql.py "SELECT * FROM amigos_marcador"',
    ", y no hay dos consultas que puedan decir cosas distintas. La base se "
    "abre aqui en":
        ", and there aren't two queries that could disagree. The database is "
        "opened here",
    "solo lectura": "read-only",

    # --- 3b · el informe largo --------------------------------------------
    "3b &middot; El informe largo": "3b &middot; The long report",
    "El de siempre, en texto: quien construyo que, en que numeros se puso cada "
    "uno, el ladron, los comercios y las tiradas.":
        "The usual one, as text: who built what, which numbers each player "
        "settled on, the robber, the trades and the dice.",
    "Ver el informe": "See the report",

    # --- el registro -------------------------------------------------------
    "Registro": "Log",
    "(nada todavia)": "(nothing yet)",
    "Parar la tarea": "Stop the task",

    # --- los atributos que se LEEN -----------------------------------------
    # No son texto de la pagina, asi que se colaban sin que nadie los viera:
    # el gris de una caja de busqueda y el globo del raton.
    "Cambiar de idioma": "Change language",
    "Cambiar entre claro y oscuro": "Switch between light and dark",
    "preguntame algo: cuantos caballeros le han caido a elGato":
        "ask me something: how many knights has elGato had",
    "filtrar: un texto busca por dentro (carla, 2:1); un numero busca "
    "exacto (4)":
        "filter: text searches inside (carla, 2:1); a number matches "
        "exactly (4)",
    "como se llama": "their name",
    "Ordenar por esta columna": "Sort by this column",

    # --- los bloques de desarrollo -----------------------------------------
    # No se publican, pero quien desarrolla esto los ve, y media pagina en un
    # idioma y media en otro es peor que no traducir nada.
    "&hellip;y grabar capturas": "&hellip;and record screenshots",
    "Comprobar que ha apuntado bien": "Check that it recorded correctly",
    "saca ademas una foto por accion, para tener la pantalla y la verdad "
    "emparejadas. Es lo que alimenta la red y las plantillas, y":
        "also takes one screenshot per action, so the screen and the ground "
        "truth are paired up. That's what feeds the network and the templates, "
        "and",
    "solo sirve para eso": "it's good for nothing else",
    ": ocupa": ": it takes",
    "2 GB por partida": "2 GB per game",
    ". Si lo que quieres son tus estadisticas, el primer boton apunta "
    "exactamente igual de bien.":
        ". If what you want is your stats, the first button records exactly as "
        "well.",
    "Rehacer las vistas": "Rebuild the views",
    "Comprobar que cuadran": "Check that they reconcile",
    "mira que el total y cada partida por separado digan lo mismo, que los "
    "robos hechos sean los mismos que los sufridos y que nadie tenga puntos "
    "tapados imposibles. Es lo que avisaria si al tocar una consulta se "
    "colara un error callado.":
        "checks that the total and each game separately say the same thing, "
        "that steals made match steals suffered and that nobody has impossible "
        "hidden points. It's what would warn you if touching a query let a "
        "silent error through.",
    "4 &middot; Leer el tablero de la pantalla":
        "4 &middot; Read the board off the screen",
    "Mira la pantalla y lee el tablero:":
        "It watches the screen and reads the board:",
    "no toca el juego": "it doesn't touch the game",
    ", solo hace capturas. No hay nada que configurar: dale y ya.":
        ", it only takes screenshots. There's nothing to configure: "
        "just press it.",
    "Los colores de la mesa los lee solo":
        "It works out the table's colours on its own",
    ", de los paneles de jugador de las esquinas, que es de donde los lees tu. "
    "Se abre una ventana con lo que va viendo.":
        ", from the player panels in the corners, which is where you read them "
        "from too. A window opens with what it's seeing.",
    "Mirar la pantalla": "Watch the screen",
    "Probarlo sobre una partida grabada": "Try it on a recorded game",
    "Medir el ladron y los dados": "Measure the robber and the dice",
    "Empieza con el": "Start with the",
    "tablero vacio": "board empty",
    "si puedes: la referencia del sitio vacio (la mitad de lo que se "
    "mira) se toma de las primeras fotos y se congela con la primera "
    "pieza. Arrancando a mitad de partida, lo que ya estuviera puesto se toma "
    "por tablero y no se ve. Ademas de las piezas se lee":
        "if you can: the reference for an empty spot (half of what gets "
        "looked at) is taken from the first frames and frozen with the "
        "first piece. Starting mid-game, whatever was already built is taken "
        "for board and never seen. Besides the pieces it also reads",
    "donde esta el ladron": "where the robber is",
    "la ultima tirada": "the last roll",
    "Para desarrollar el proyecto": "For working on the project",
    "De aqui para abajo": "From here down",
    "no hace falta nada": "you need nothing",
    "para tener tus estadisticas. Es la otra mitad del proyecto: una red que "
    "aprende a leer el tablero de una captura, con las etiquetas que escribe "
    "el propio juego, para ver cuanto se puede saber":
        "to get your stats. This is the other half of the project: a network "
        "that learns to read the board off a screenshot, labelled by the game "
        "itself, to see how much can be known",
    "sin tocar el cliente": "without touching the client",
    "Que alimentan las capturas": "What the screenshots feed",
    "Se graban con": "They're recorded with",
    "&laquo;&hellip;y grabar capturas&raquo;":
        "&laquo;&hellip;and record screenshots&raquo;",
    ", arriba del todo, junto al boton de encender. Cada foto va emparejada "
    "con el estado exacto que apunto el mod en ese instante, asi que las "
    "etiquetas las escribe el juego y no hay que anotar nada a mano. "
    "Alimentan tres cosas distintas, y solo la primera se &laquo;entrena"
    "&raquo;:":
        ", right at the top, next to the switch. Each frame is paired with the "
        "exact state the mod recorded at that instant, so the labels are "
        "written by the game and nothing has to be annotated by hand. They "
        "feed three different things, and only the first is &laquo;trained"
        "&raquo;:",
    "La red": "The network",
    "red_de_sitios.pt": "red_de_sitios.pt",
    ") lee que hay en cada vertice y cada arista. Es la que se entrena "
    "con el boton de aqui abajo.":
        ") reads what's on each vertex and each edge. This is the one "
        "the button below trains.",
    "Las plantillas": "The templates",
    "plantillas_puntos.npz": "plantillas_puntos.npz",
    "plantillas_cartas.npz": "plantillas_cartas.npz",
    ", los digitos) no son una red: son el promedio de miles de "
    "recortes ya etiquetados. De ahi salen los contadores de los paneles, con "
    "97,3% en caballeros y 98,9% en desarrollo.":
        ", the digits) these aren't a network: they're the average of "
        "thousands of already-labelled crops. The panel counters come from "
        "them, at 97.3% on knights and 98.9% on development.",
    "El aviso de la esquina": "The corner ticker",
    "ocr/ticker.py": "ocr/ticker.py",
    ") usa Tesseract y": ") uses Tesseract and",
    "no se entrena": "isn't trained",
    ". Las capturas sirven para MEDIRLO (20 robos de 20, 23 comercios de 30) "
    "y para ajustar el recorte y el umbral de tinta.":
        ". The screenshots are for MEASURING it (20 steals out of 20, 23 "
        "trades out of 30) and for tuning the crop and the ink threshold.",
    "Entrenar la red con lo grabado":
        "Train the network on what's been recorded",
    "Un boton. Convierte lo grabado,": "One button. It converts the recording,",
    "examina": "tests",
    "el modelo de antes con la partida nueva (que no ha visto) y "
    "solo entonces entrena con ella. En ese orden, porque al reves el numero "
    "sale inflado y no avisa de nada.":
        "the previous model on the new game (which it hasn't seen) "
        "and only then trains on it. In that order, because the other "
        "way round the number comes out inflated and warns you of nothing.",
    "Hacerlo todo": "Do all of it",
    "Como va mejorando": "How it's improving",
    "Tarda cerca de media hora: son dos entrenamientos, el que se mide "
    "(aparta dos partidas) y el que se juega (con todo dentro).":
        "It takes about half an hour: two training runs, the measured one "
        "(which holds two games back) and the one you play with (everything "
        "in).",
    "Y los pasos sueltos, por si hace falta uno solo:":
        "And the individual steps, in case you only need one:",
    "Preparar los datos": "Prepare the data",
    "Medir el tablero entero": "Measure the whole board",
    "Medir foto a foto": "Measure frame by frame",
    "Entrenar": "Train",
    "Reentrenar con todo (para jugar)": "Retrain on everything (to play with)",
    "Pruebas": "Tests",
    "&laquo;Medir el tablero entero&raquo; es el numero que importa: cuanto "
    "del tablero final queda bien leido, que es lo que tendria delante quien "
    "juega. &laquo;Foto a foto&raquo; mira recortes sueltos, donde el tablero "
    "vacio arrastra la media hacia arriba.":
        "&laquo;Measure the whole board&raquo; is the number that matters: how "
        "much of the final board is read correctly, which is what a player "
        "would have in front of them. &laquo;Frame by frame&raquo; looks at "
        "loose crops, where the empty board drags the average up.",
    "Partidas grabadas": "Recorded games",
    "El modelo de ahora": "The current model",
}


# Las cadenas que escribe el JavaScript. Van CON las comillas: así no hay
# forma de que un reemplazo toque un nombre de variable por accidente.
GUION = {
    '"  ·  SIN plugin instalado"': '"  ·  NO plugin installed"',
    '"  ·  pagina "': '"  ·  page "',
    '"  ·  plugin instalado"': '"  ·  plugin installed"',
    '" &middot; apuntando: <b>"': '" &middot; recording: <b>"',
    '" &middot; ultima partida apuntada: "': '" &middot; last game recorded: "',
    '" <small>(IA)</small>"': '" <small>(AI)</small>"',
    '" acciones"': '" actions"',
    '" con "': '" with "',
    '" de "': '" of "',
    '" fila" : " filas"': '" row" : " rows"',
    '" fotos · "': '" photos · "',
    '" partida"': '" game"',
    '" partidas"': '" games"',
    '" y grabando"': '" and recording"',
    '"(nada todavia)"': '"(nothing yet)"',
    '", columna <code>"': '", column <code>"',
    '".  En la ventana negra:  <code>"': '".  In the black window:  <code>"',
    '"</b> acciones"': '"</b> actions"',
    '"<small>Dale a <b>Dejarlo listo</b>, aqui debajo.</small>"':
        '"<small>Press <b>Get it ready</b>, just below.</small>"',
    '"<small>El mod se mete dentro del juego al arrancarlo, asi que si abriste "':
        '"<small>The mod goes inside the game when the game starts, so if you opened "',
    '"<small>Modificar el cliente va contra las condiciones de uso de Catan "':
        '"<small>Modifying the client goes against Catan "',
    '"<tr><td>Ninguna todavia.</td></tr>"': '"<tr><td>None yet.</td></tr>"',
    '"<tr><td>partida "': '"<tr><td>game "',
    '">&lsaquo; anteriores</button>"': '">&lsaquo; previous</button>"',
    '">siguientes &rsaquo;</button>"': '">next &rsaquo;</button>"',
    '"Ahora mismo llegan "': '"Right now that\'s "',
    '"Apagalo al terminar.</small>"':
        '"Switch it off when you are done.</small>"',
    '"BepInEx ya esta; falta compilar el <b>plugin</b>. Un boton."':
        '"BepInEx is in; the <b>plugin</b> still needs compiling. One button."',
    '"Cuando termines del todo, <b>Parar y apagar el mod</b>."':
        '"When you are completely done, <b>Stop and switch the mod off</b>."',
    '"EL MOD ESTA ENCENDIDO"': '"THE MOD IS ON"',
    '"El interruptor esta apagado, pero Catan esta abierto."':
        '"The switch is off, but Catan is open."',
    '"El juego arrancara limpio."': '"The game will start clean."',
    '"El mod esta apagado y Catan cerrado. "':
        '"The mod is off and Catan is closed. "',
    '"El mod no esta instalado en el juego."':
        '"The mod is not installed in the game."',
    '"En la ventana negra:  "': '"In the black window:  "',
    '"En la ventana negra: <code>py db/vistas.py --crear</code></p>"':
        '"In the black window: <code>py db/vistas.py --crear</code></p>"',
    '"Enciende el mod y se pone a grabar. Despues abre Catan y juega. "':
        '"Switch the mod on and it starts recording. Then open Catan and play. "',
    '"Falta <b>BepInEx</b>, que es lo que deja que el mod se "':
        '"<b>BepInEx</b> is missing, which is what lets the mod "',
    '"Grabando. Abre Catan y juega. Puedes encadenar <b>varias partidas "':
        '"Recording. Open Catan and play. You can chain <b>several games "',
    '"Guarda una partida primero.</p>"': '"Save a game first.</p>"',
    '"IA, las vistas de amigos salen vacias a proposito."':
        '"AI, the friends views come out empty on purpose."',
    '"No encuentro Catan Universe. Abre Steam una vez si lo has movido."':
        '"Can\'t find Catan Universe. Open Steam once if you have moved it."',
    '"No encuentro Catan Universe. Abre Steam una vez, o instala "':
        '"Can\'t find Catan Universe. Open Steam once, or install "',
    '"No hay nada que enseñar aqui. Si has elegido una partida contra la "':
        '"There is nothing to show here. If you picked a game against the "',
    '"No se ha podido quitar: "': '"Could not remove it: "',
    '"Quitar la partida "': '"Remove game "',
    '"Registro · "': '"Log · "',
    '"Registro · grabacion"': '"Log · recording"',
    '"Registro · lo que apunta el mod"': '"Log · what the mod is recording"',
    '"Registro"': '"Log"',
    '"Todas las partidas"': '"All games"',
    '"Todavia no hay ninguna partida guardada."': '"No games saved yet."',
    '"Todavia no llega nadie: el que mas lleva es "':
        '"Nobody qualifies yet: the highest is "',
    '"Universe, y esto se carga en todas las partidas mientras este puesto. "':
        '"Universe\'s terms of use, and this loads in every game while it is on. "',
    '"\\n\\nSe hace una copia de la base antes, pero no hay "':
        '"\\n\\nA copy of the database is made first, but there is no "',
    '"\\n\\nSi pone 404, este panel lleva abierto desde antes de que "':
        '"\\n\\nIf it says 404, this panel has been open since before "',
    '"cargue, y el plugin. Un boton."':
        '"load, and the plugin too. One button."',
    '"de 10 en 10"': '"10 at a time"',
    '"deshacer."': '"undo."',
    '"el boton existiera. Cierra la ventana negra y vuelve a abrirla."':
        '"the button existed. Close the black window and open it again."',
    '"el juego, y recarga esta pagina."': '"the game, and reload this page."',
    '"el panel ha respondido "': '"the panel answered "',
    '"esta partida con el mod encendido, sigue cargado. <b>Para descargarlo hay "':
        '"this game with the mod on, it is still loaded. <b>To unload it you have "',
    '"no hay vistas"': '"no views"',
    '"no se ha podido"': '"it didn\'t work"',
    '"preparada"': '"ready"',
    '"que cerrar Catan y volver a abrirlo.</b></small>"':
        '"to close Catan and open it again.</b></small>"',
    '"seguidas sin tocar nada</b>: cada una se guarda en su carpeta sola. "':
        '"in a row without touching anything</b>: each one saves to its own folder. "',
    '"sin nombre"': '"unnamed"',
    '"sin preparar"': '"not ready"',
    '"solo con amigos"': '"friends only"',
    '"ver todas"': '"see all"',
    '"»"': '"”"',
    '"▲ cierra Catan · Catan Tracker"': '"▲ close Catan · Catan Tracker"',
    '"● MOD ENCENDIDO · Catan Tracker"': '"● MOD ON · Catan Tracker"',
    '"☀︎  Claro"': '"☀︎  Light"',
    '"☽  Oscuro"': '"☽  Dark"',
    '"✕ sin panel · Catan Tracker"': '"✕ no panel · Catan Tracker"',
    '\'" placeholder="como se llama"></td>\'':
        '\'" placeholder="their name"></td>\'',
    '\'" title="Ordenar por esta columna">\'':
        '\'" title="Sort by this column">\'',
    '\'">guardar</button></td></tr>\'': '\'">save</button></td></tr>\'',
    '\'">partida \'': '\'">game \'',
    '\'">quitar</button></td></tr>\'': '\'">remove</button></td></tr>\'',
    '\'<div class="cuando">partida \'': '\'<div class="cuando">game \'',
    '\'<div class="fuente">De «\'': '\'<div class="fuente">From “\'',
    '\'<div class="otras">Si no era eso: \'':
        '\'<div class="otras">If that was not it: \'',
    '\'<optgroup label="Una sola partida">\'':
        '\'<optgroup label="A single game">\'',
    '\'<p class="vacio">Faltan vistas por crear (\'':
        '\'<p class="vacio">Views still to create (\'',
    '\'<p class="vacio">Nada con «\'': '\'<p class="vacio">Nothing with “\'',
    '\'<p class="vacio">No hay ninguna partida guardada.</p>\'':
        '\'<p class="vacio">No games saved yet.</p>\'',
    '\'<p class="vacio">Todavia no hay ninguna cuenta. \'':
        '\'<p class="vacio">No accounts yet. \'',
    '\'<p class="vacio">buscando...</p>\'':
        '\'<p class="vacio">searching...</p>\'',
    '\'<p class="vacio">leyendo...</p>\'':
        '\'<p class="vacio">reading...</p>\'',
    "'».</p>'": "'”.</p>'",
}


# Lo que NO está en la página: lo que manda el servidor y la página sólo
# pinta. Los títulos de las 32 tablas, qué contesta cada una, los titulares y
# los filtros. Vive en `db/vistas.py` y `db/titulares.py`, no en `panel.py`.
#
# LAS LLAVES SE RESPETAN. Un titular no es una frase, es una plantilla:
# «{victorias} de {partidas}». Lo que va entre llaves es un nombre de columna
# y se rellena con la fila que gana, así que traducirlo rompe el titular y
# deja un `{victorias}` en crudo en la pantalla. `db/pruebas.py` comprueba que
# los huecos de la traducción son EXACTAMENTE los mismos que los del original.
FRASES = {
    'Aquí sólo entran los monopolios de los que se sabe cuánto se llevaron. Si en esta partida se jugó alguno y no sale, es de antes del 22/8/2026: el mod no leía el reparto todavía. Están en «Los monopolios», con quién lo tiró y qué pidió.':
        "Only monopolies whose haul is known get in here. If one was played in this game and doesn't show up, it's from before 22/8/2026: the mod wasn't reading the handover yet. They're in «The monopolies», with who played it and what they called.",
    'Cartas de desarrollo': 'Development cards',
    'Comercio': 'Trade',
    'Con quién se ceba el ladrón': 'Who the robber picks on, and by whom',
    'Con qué salida le toca a cada uno': 'Which seat each player gets',
    'Cuántos, por jugador': 'How many, per player',
    'De cada salida, cómo acabó': 'From each seat, how it ended',
    'De dónde salió cada punto': 'Where each point came from',
    'De esta partida no se puede saber. Que alguien USE un puerto se deduce de los comercios y eso está en «Puerto a puerto»; PILLARLO es otra cosa y necesita saber dónde está cada puerto en el tablero. El mod no lo leía bien hasta el 22/8/2026 -- la posición viene en una `EdgePosition` y se estaba leyendo como si fuera otra clase, así que llegaba vacía -- y eso no se puede recuperar sin volver a jugar la partida.':
        "There's no way to know for this game. That someone USES a port is deduced from their trades and that's in «Port by port»; CLAIMING one is a different thing and needs to know where each port sits on the board. The mod wasn't reading that correctly until 22/8/2026 -- the position comes in an `EdgePosition` and was being read as if it were another class, so it arrived empty -- and that can't be recovered without playing the game again.",
    'Dónde pone el ladrón cada uno': 'Where each player puts the robber',
    'El ladron: a quien y en que numero':
        'The robber: on whom and on which number',
    'El ladrón': 'The robber',
    'El ladrón, uno a uno': 'The robber, one by one',
    'El mazo': 'The deck',
    'El monopolio, uno a uno': 'Monopolies, one by one',
    'El orden de salida': 'Turn order',
    'El ritmo de cada uno': "Everyone's pace",
    'El saldo con cada uno': 'The balance with each player',
    'El tablero y los dados': 'The board and the dice',
    'En mesa de 5 y 6 manda {quien}, con {victorias} de {partidas}.':
        'At 5- and 6-player tables {quien} leads, with {victorias} of {partidas}.',
    'En mesa de 5 y 6 no ha ganado todavía ninguno de los que llegan al mínimo.':
        'At 5- and 6-player tables none of the players who reach the minimum has won yet.',
    'Jugadores': 'Players',
    'La mejor suerte en una partida': 'Best luck in a single game',
    'La suerte de cada uno': "Everyone's dice luck",
    'Las partidas': 'The games',
    'Las tiradas': 'The dice rolls',
    'Los monopolios': 'The monopolies',
    'Los números de cada uno': "Each player's numbers",
    'Los números que más tapa el ladrón': 'The numbers the robber blocks most',
    'Los sietes de cada uno': "Everyone's sevens",
    'Marcador': 'Scoreboard',
    'Más ladrones en una partida': 'Most robbers in a single game',
    'Ninguno todavía. Si en la partida se jugó alguno y aquí no sale, es que la carta no llegó a apuntarse: el recurso sólo se engancha a una jugada del mismo jugador y el mismo turno.':
        "None yet. If one was played in the game and doesn't show up here, the card never got recorded: the resource is only tied to a play by the same player on the same turn.",
    'Partidas': 'Games',
    'Producción': 'Production',
    'Puerto a puerto': 'Port by port',
    'Puertos': 'Ports',
    'Puntos y ritmo': 'Score and pace',
    'Quién compra más cartas de desarrollo':
        'Who buys the most development cards',
    'Quién elige mejor las casillas': 'Who picks the best tiles',
    'Quién gana más': 'Who wins most',
    'Quién pilló cada puerto': 'Who claimed each port',
    'Quién propone tratos a quién': 'Who proposes trades to whom',
    'Quién saca más sietes': 'Who rolls the most sevens',
    'Quién tiene más suerte': 'Who has the most luck',
    'Quién va más en positivo, y con quién':
        'Who comes out most ahead, and with whom',
    'Qué se comercia': 'What gets traded',
    'Robos de la mano': 'Steals from the hand',
    'Trato a trato': 'Trade by trade',
    'a quien se lo puso cada uno y sobre que numero':
        'who each player put it on and on which number',
    'a qué número lo manda cada uno, cuántas veces, y si por el 7 o con un caballero':
        'which number each player sends it to, how often, and whether by a 7 or with a knight',
    'a qué números va el ladrón, sumando a todo el mundo':
        'which numbers the robber goes to, adding everyone together',
    'cada intercambio con los dos lados: quién dio qué y a cambio de qué':
        'every trade with both sides: who gave what and in exchange for what',
    'cobró {le_toco} veces contra las {le_tocaba} que le tocaban, y con sólo {casillas} casillas. Se sale {se_sale} márgenes de lo normal: el azar por sí solo ya mueve un {margen}%.':
        "collected {le_toco} times against the {le_tocaba} they were due, and with only {casillas} tiles. That's {se_sale} margins out from normal, and chance alone already moves it {margen}%.",
    'como va mejorando': "how it's improving",
    'comprobar lo grabado': 'check the recording',
    'cuántas cartas de cada recurso le ha sacado cada uno a cada uno':
        'how many cards of each resource each player has taken off each other',
    'cuántas veces ha salido primero, segundo, tercero… cada persona':
        'how many times each person has started first, second, third…',
    'cuántos hizo y cuántos sufrió cada uno (cuántos, no cuáles)':
        'how many each player made and how many they suffered (how many, not which)',
    'de las casillas donde está puesto, cuántas veces le pagó el tablero contra las que le debía. 100 es la suerte normal':
        "for the tiles they're on, how many times the board paid out against how many it owed. 100 is normal luck",
    'de las veces que salió en cada puesto, en cuáles acabó':
        'of the times they started from each seat, where they finished',
    'de lo que le tocaba: cobró {le_toco} veces contra las {le_tocaba} que le debía el tablero, y 100% es lo normal. Se sale {se_sale} márgenes: hace falta pasar de 2 para que sea suerte y no ruido.':
        "of what they were due: collected {le_toco} times against the {le_tocaba} the board owed them, and 100% is normal. That's {se_sale} margins out: it takes more than 2 for it to be luck and not noise.",
    'de media por casilla suya, cuando un sitio cualquiera de sus tableros vale {lo_normal}. Con eso le tocaron {le_toco} cobros de los {le_tocaba} que le tocaban.':
        'on average per tile of theirs, when any spot on their boards is worth {lo_normal}. That earned them {le_toco} payouts of the {le_tocaba} they were due.',
    'de más en los {tratos} tratos entre los dos: se llevó {recibio} y soltó {dio}. Son cartas, no acierto: dar tres por una puede ser el mejor trato de la partida.':
        "up across the {tratos} trades between the two: took {recibio} and gave up {dio}. That's cards, not judgement: giving three for one can be the best trade of the game.",
    'de sus tiradas: {sietes} sietes en {tiros} tiros. Lo normal es {porcentaje_normal}%.':
        'of their rolls: {sietes} sevens in {tiros} throws. Normal is {porcentaje_normal}%.',
    'dejar el mod listo': 'get the mod ready',
    'edificios, premios y, por resta, las cartas de punto':
        'buildings, awards and, by subtraction, the victory point cards',
    'el ciclo entero (convertir, examinar, entrenar)':
        'the whole cycle (convert, test, train)',
    'el informe de las partidas': 'the games report',
    'en mesa de {eran}. Acaba de media en el puesto {puesto_medio}, con {puntos_medios} puntos.':
        'at a {eran}-player table. Finishes {puesto_medio} on average, with {puntos_medios} points.',
    'en qué números se puso, cuántas veces salieron y qué sacó':
        'which numbers they settled on, how often those came up and what they got',
    'en qué puesto salió cada uno y en cuál acabó':
        'which seat each player started from and where they finished',
    'en qué turno llegó a su primera ciudad, su primera carta...':
        'which turn they reached their first city, their first card...',
    'entrenar (apartando una partida para medir)':
        'train (holding one game back to measure)',
    'guardar las partidas en la base de datos':
        'save the games to the database',
    'los nueve puertos del mapa y quién se quedó cada uno, incluidos los que no pilló nadie':
        'the nine ports on the map and who ended up with each, including the ones nobody took',
    'medir el ladron y los dados contra lo que dice el mod':
        'measure the robber and the dice against what the mod says',
    'medir el tablero entero, como lo leeria jugando':
        'measure the whole board, as it would read it in play',
    'medir la red, foto a foto': 'measure the network, frame by frame',
    'mesas de cualquier tamaño': 'tables of any size',
    'mirar la pantalla': 'watch the screen',
    'partidas, victorias y puntos medios de cada uno, por tamaño de mesa':
        'games, wins and average score for each player, by table size',
    'preparar los datos': 'prepare the data',
    'probar la lectura en vivo sobre una partida grabada':
        'try live reading on a recorded game',
    'pruebas de la red': 'network tests',
    'pruebas de las vistas': 'view tests',
    'quién gana cartas con quién y quién las pierde: el saldo de verdad, con TODOS sus tratos dentro, los propusiera quien los propusiera (sin la banca)':
        'who gains cards off whom and who loses them: the real balance, with ALL their trades in it, whoever proposed them (bank trades excluded)',
    'quién mueve ficha: sólo los tratos que propuso cada uno, y cómo le salieron ESOS':
        'who makes the first move: only the trades each player proposed, and how THOSE went for them',
    'quién saca más sietes al tirar, contra el 16,7% que toca':
        "who rolls the most sevens, against the 16.7% that's expected",
    'quién se lo puso a quién, cuántas veces le tocó y qué le costó':
        'who put it on whom, how many times it landed and what it cost them',
    'quién tiró cada monopolio y qué recurso pidió':
        'who played each monopoly and which resource they called',
    'qué le tocó a cada uno de las cartas que compró':
        'what each player got out of the cards they bought',
    'qué recurso da y cuál recibe cada uno, y con quién':
        'which resource each player gives and which they get, and with whom',
    'qué recursos le dio el tablero a cada uno, y de qué anda corto':
        "which resources the board gave each player, and what they're short of",
    'qué salió contra lo que debería haber salido':
        'what came up against what should have come up',
    'qué salió contra lo que el mazo lleva dentro':
        'what came out against what the deck actually holds',
    'qué tal le va a cada puesto de salida, sumando todas las partidas':
        'how each starting seat does, across every game',
    'recursos que no dejó producir, contra los que sí se cobraron':
        'resources it stopped from being produced, against the ones that were collected anyway',
    'reentrenar con todo (para jugar)': 'retrain on everything (to play with)',
    'rehacer las vistas de la base': 'rebuild the database views',
    'se lo pusieron encima. En {le_bloquearon} de esas veces salió el número y no cobró: {perdido} cartas que se quedó sin producir. Más {le_robaron} que le robaron de la mano, {en_total} cartas en total.':
        'were put on them. On {le_bloquearon} of those the number came up and they collected nothing: {perdido} cards never produced. Plus {le_robaron} taken out of their hand, {en_total} cards in total.',
    'si a alguien le ponen el ladrón más de lo que le toca, descontando cuánto juega y cuántas casillas tiene':
        'whether anyone gets the robber more than their share, allowing for how much they play and how many tiles they hold',
    'solo con amigos (sin la IA)': 'only with friends (no AI)',
    'solo las partidas contra la IA': 'only the games against the AI',
    'solo mesas de 4': 'only 4-player tables',
    'solo mesas de 5 y 6': 'only 5- and 6-player tables',
    'todas, la IA incluida': 'all of them, AI included',
    'una fila por jugador y partida, con el nombre ya resuelto':
        'one row per player per game, with the name already resolved',
    'una fila por jugador: cuántos puertos se le pueden contar y cuáles':
        'one row per player: how many ports can be counted for them, and which',
    'una fila por puerto usado: cuál, cuántas veces y entre qué turnos':
        'one row per port used: which one, how many times and between which turns',
    'una por partida, con quién ganó, cuántas casillas tenía el tablero y si eran todos personas':
        'one row per game, with who won, how many tiles the board had and whether everyone was human',
    '{compradas} cartas en {partidas} partidas, {caballero} de ellas caballeros.':
        '{compradas} cards in {partidas} games, {caballero} of them knights.',
    '{con_7} veces obligado por un 7 y {con_caballero} eligiéndolo con un caballero. En {le_bloqueo} de esas veces salió el número y {a_quien} no cobró: son {le_costo} cartas que se quedó sin producir. Y aparte le quitó {le_robo} cartas de la mano.':
        '{con_7} times forced by a 7 and {con_caballero} by choice with a knight. On {le_bloqueo} of those the number came up and {a_quien} collected nothing: {le_costo} cards never produced. And on top of that took {le_robo} cards out of their hand.',
    '{neto} cartas': '{neto} cards',
    '{por_casilla} puntitos': '{por_casilla} pips',
    '{por_partida} por partida': '{por_partida} per game',
    '{porcentaje}%': '{porcentaje}%',
    '{quien} a {a_quien}': '{quien} on {a_quien}',
    '{quien} con {con_quien}': '{quien} with {con_quien}',
    '{se_lo_pusieron} ladrones': '{se_lo_pusieron} robbers',
    '{se_lo_puso} veces': '{se_lo_puso} times',
    '{suerte}%': '{suerte}%',
    '{victorias} de {partidas}': '{victorias} of {partidas}',
    '¿A quién se ceba el ladrón?': 'Who does the robber pick on?',
    '¿Importa salir primero?': 'Does going first matter?',
}


# Las cabeceras de las tablas. La clave es el nombre de la columna en SQL y
# NO se traduce nunca: `amigos_marcador.victorias` se llama así en la base, en
# `py sql.py` y en la caja de preguntas. Lo que se traduce es la etiqueta que
# se PINTA encima de la columna, que es otra cosa.
#
# Cortas a propósito: van en una cabecera y compiten por el ancho con el
# número de debajo. Lo que significan de verdad está en la ficha de la vista.
COLUMNAS = {
    "a": "to",
    "a_puntos": "target points",
    "a_quien": "to whom",
    "a_si_mismo": "to self",
    "arcilla": "brick",
    "caballero": "knight",
    "cada_casilla": "cards per tile",
    "carretera_larga": "longest road",
    "carreteras": "road building",
    "carta": "card",
    "cartas": "cards",
    "cartas_de_punto": "victory point cards",
    "casillas": "tiles",
    "casillas_tablero": "board tiles",
    "cereales": "grain",
    "ciudades": "cities",
    "color": "color",
    "compradas": "bought",
    "con_7": "with 7",
    "con_amigos": "with friends",
    "con_caballero": "with knight",
    "con_quien": "with whom",
    "de_mas": "surplus",
    "de_quien": "from whom",
    "deberia_salir": "expected rolls",
    "deberian_salir": "expected draws",
    "del_reparto": "from setup",
    "dia": "day",
    "dio": "gave",
    "duro_hasta": "lasted until",
    "edificios": "buildings",
    "en_total": "total",
    "eran": "table size",
    "es_ia": "is bot",
    "esperado": "expected",
    "game_id": "game id",
    "gano": "winner",
    "genericos": "generic ports",
    "hora": "hour",
    "ias": "bots",
    "invencion": "year of plenty",
    "jugadores": "player count",
    "lana": "wool",
    "le_bloquearon": "times blocked",
    "le_bloqueo": "blocked them",
    "le_costo": "cost them",
    "le_quito_el_ladron": "lost to robber",
    "le_robaron": "stolen from them",
    "le_robo": "stole from them",
    "le_tocaba": "expected",
    "le_tocaban": "expected",
    "le_toco": "got",
    "les_saco": "total taken",
    "lo_normal": "baseline",
    "madera": "wood",
    "margen": "margin",
    "mayor_ejercito": "largest army",
    "mineral": "ore",
    "minutos": "minutes",
    "monopolio": "monopoly",
    "monopolios": "monopolies",
    "movimientos": "moves",
    "neto": "net",
    "neto_proponiendo": "net when proposing",
    "numero": "number",
    "partida": "game",
    "partidas": "games played",
    "partidas_juntos": "games together",
    "pegas": "issues",
    "perdido": "lost",
    "personas": "people",
    "pidio": "requested",
    "pieza": "building",
    "player_id": "player id",
    "poblados": "settlements",
    "por_casilla": "pips per tile",
    "por_partida": "per game",
    "porcentaje": "percentage",
    "porcentaje_normal": "expected percentage",
    "primer_caballero": "first knight",
    "primer_poblado": "first settlement",
    "primer_uso": "first used",
    "primera_carta": "first dev card",
    "primera_ciudad": "first city",
    "producido": "produced",
    "puerto": "port",
    "puerto_arcilla": "brick port",
    "puerto_cereales": "grain port",
    "puerto_lana": "wool port",
    "puerto_madera": "wood port",
    "puerto_mineral": "ore port",
    "puesto": "rank",
    "puesto_medio": "avg rank",
    "puestos_ganados": "ranks gained",
    "puntitos": "pips",
    "punto_victoria": "victory point",
    "puntos": "points",
    "puntos_medios": "avg points",
    "quedo_1": "finished 1st",
    "quedo_2": "finished 2nd",
    "quedo_3": "finished 3rd",
    "quedo_4": "finished 4th",
    "quedo_5": "finished 5th",
    "quedo_6": "finished 6th",
    "quien": "who",
    "recibio": "received",
    "recurso": "resource",
    "robo_el": "stole",
    "salida": "start order",
    "salida_media": "avg start order",
    "salieron": "drawn",
    "salio_1": "started 1st",
    "salio_2": "started 2nd",
    "salio_3": "started 3rd",
    "salio_4": "started 4th",
    "salio_5": "started 5th",
    "salio_6": "started 6th",
    "salio_ultimo": "started last",
    "se_ceban": "pile on",
    "se_jugaba_a": "played to",
    "se_lo_pusieron": "robber put on them",
    "se_lo_puso": "placed on them",
    "se_sale": "margins off",
    "sietes": "sevens",
    "sin_saber": "unknown",
    "su_mejor": "best points",
    "suerte": "luck",
    "tercer_poblado": "third settlement",
    "tiradas": "rolls",
    "tiradas_contadas": "rolls counted",
    "tiros": "rolls by them",
    "total": "total",
    "tratos": "deals",
    "tratos_entre_los_dos": "deals between them",
    "turno": "turn",
    "turnos": "turns",
    "ultimo_uso": "last used",
    "veces": "times",
    "veces_normales": "expected times",
    "veces_salio": "times rolled",
    "victorias": "wins",
    "y_recibio": "and received",
}



# LA CAJA DE PREGUNTAS. Esto no traduce la pregunta: la reescribe con las
# palabras castellanas contra las que la caja empareja. El emparejador no
# entiende ningun idioma -- parte la pregunta en palabras y las compara con
# los nombres, titulos y columnas de las vistas, que estan escritos en
# castellano -- asi que lo unico que hace falta es que las palabras lleguen
# en castellano.
#
# Medido con el mismo examen de 68 preguntas que el castellano, traducido:
# acierta 39 de 68 en ingles. El castellano acierta 40. O sea que no es peor en ingles
# que en su propio idioma, que es el liston que importa: la caja falla lo que
# falla, y lo que no puede pasar es que falle MAS por el idioma.

# Los giros van ANTES de partir en palabras, porque solo quieren decir eso
# juntos. Se aplican de mas largo a mas corto, que es lo que hace que
# `how many` se aplique antes que `how` no se coma la mitad del otro.
GIROS = (
    ('to whom', 'a quien'),
    ('on whom', 'a quien'),
    ('with whom', 'con quien'),
    ('from whom', 'a quien'),
    ('year of plenty', 'invencion'),
    ('road building', 'carretera'),
    ('development card', 'desarrollo carta'),
    ('dev card', 'desarrollo carta'),
    ('victory point', 'punto victoria'),
    ('longest road', 'carretera larga'),
    ('largest army', 'mayor ejercito'),
    ('come up', 'salio'),
    ('comes up', 'salio'),
    ('came up', 'salio'),
    ('come out', 'salio'),
    ('comes out', 'salio'),
    ('came out', 'salio'),
    ('how many', 'cuantas'),
    ('how much', 'cuanto'),
    ('how long', 'cuanto minuto'),
    ('how often', 'cuantas veces'),
    ('than they should', 'de lo que toca'),
    ('table size', 'mesa'),
    ('start order', 'salida'),
    ('turn order', 'salida'),
)

# Y palabra a palabra. Las vacias se borran: no dicen nada de la pregunta y
# ensucian la bolsa con la que se puntua cada vista.
PREGUNTAS = {
    'against': 'contra', 'ahead': 'positivo', 'all': 'todo', 'always': '',
    'an': '', 'and': '', 'anyone': 'alguien', 'are': '', 'army': 'ejercito',
    'as': '', 'ask': 'pidio', 'asked': 'pidio', 'asking': 'pidio',
    'asks': 'pidio', 'at': '', 'average': 'medio', 'balance': 'saldo',
    'bank': 'banca', 'be': '', 'been': '', 'best': 'mejor', 'between': 'entre',
    'block': 'bloqueo', 'blocked': 'bloqueo', 'blocks': 'bloqueo',
    'board': 'tablero', 'boards': 'tablero', 'bot': 'ias', 'bots': 'ias',
    'bought': 'compro', 'brick': 'arcilla', 'building': 'edificio',
    'buildings': 'edificio', 'buy': 'compro', 'buys': 'compro',
    'card': 'carta', 'cards': 'carta', 'cities': 'ciudad', 'city': 'ciudad',
    'claim': 'pillo', 'claimed': 'pillo', 'clay': 'arcilla', 'came': 'salio', 'color': 'color', 'come': 'salio',
    'comes': 'salio',
    'colour': 'color', 'computer': 'ias', 'cost': 'cuesta', 'costs': 'cuesta',
    'day': 'dia', 'deal': 'trato', 'deals': 'trato', 'deck': 'mazo',
    'development': 'desarrollo', 'dice': 'tirada', 'did': '', 'die': 'tirada',
    'do': '', 'does': '', 'draw': 'salieron', 'drawn': 'salieron',
    'duration': 'minuto', 'each': 'cada', 'earliest': 'primero', 'end': '',
    'everyone': 'todos', 'exchange': 'trato', 'exchanges': 'trato',
    'expected': 'esperado', 'fewest': 'menos', 'fifth': 'quinto',
    'finish': 'acabo', 'finished': 'acabo', 'finishes': 'acabo',
    'first': 'primero', 'for': '', 'fourth': 'cuarto', 'friends': 'amigo',
    'from': '', 'gain': 'victoria', 'gains': 'victoria', 'game': 'partida',
    'games': 'partida', 'gave': 'dio', 'generic': 'generico', 'get': 'recibio',
    'gets': 'recibio', 'give': 'dio', 'given': 'dio', 'gives': 'dio',
    'got': 'recibio', 'grain': 'cereales', 'had': '', 'hand': 'mano',
    'harbor': 'puerto', 'harbors': 'puerto', 'harbour': 'puerto', 'has': '',
    'have': '', 'hex': 'casilla', 'hexes': 'casilla', 'hour': 'hora',
    'how': 'cuanto', 'human': 'persona', 'humans': 'persona', 'i': '',
    'in': '', 'invention': 'invencion', 'is': '', 'it': '', 'its': '',
    'knight': 'caballero', 'knights': 'caballero', 'last': 'minuto',
    'lasted': 'minuto', 'least': 'menos', 'less': 'menos', 'lose': 'perdido',
    'loses': 'perdido', 'lost': 'perdido', 'luck': 'suerte', 'lucky': 'suerte',
    'lumber': 'madera', 'machine': 'ias', 'made': '', 'make': '',
    'many': 'cuantos', 'margin': 'margen', 'match': 'partida',
    'matches': 'partida', 'me': 'me', 'minute': 'minuto', 'minutes': 'minuto',
    'missed': 'perdido', 'monopolies': 'monopolio', 'monopoly': 'monopolio',
    'more': 'mas', 'most': 'mas', 'much': 'cuanto', 'my': 'mi',
    'name': 'nombre', 'net': 'neto', 'nobody': 'nadie', 'normal': 'normal',
    'number': 'numero', 'numbers': 'numero', 'of': '', 'offer': 'propone',
    'often': 'veces', 'on': '', 'one': '', 'ones': '', 'or': '',
    'ore': 'mineral', 'our': 'nuestro', 'out': '', 'pace': 'ritmo',
    'people': 'persona', 'percentage': 'porcentaje', 'piece': 'pieza',
    'pieces': 'pieza', 'pip': 'puntitos', 'pips': 'puntitos',
    'place': 'puesto', 'placed': 'colocado', 'play': 'juega',
    'played': 'juega', 'player': 'jugador', 'players': 'jugador',
    'playing': 'juega', 'plays': 'juega', 'point': 'punto', 'points': 'punto',
    'port': 'puerto', 'ports': 'puerto', 'position': 'puesto',
    'produce': 'produccion', 'produced': 'produccion',
    'production': 'produccion', 'proportion': 'proporcion',
    'propose': 'propone', 'proposed': 'propone', 'proposes': 'propone',
    'put': 'pone', 'puts': 'pone', 'rank': 'colocado', 'ranked': 'colocado',
    'reach': 'llego', 'reached': 'llego', 'reaches': 'llego',
    'receive': 'recibio', 'received': 'recibio', 'receives': 'recibio',
    'resource': 'recurso', 'resources': 'recurso', 'road': 'carretera',
    'roads': 'carretera', 'rob': 'robo', 'robbed': 'robo', 'robber': 'ladron',
    'robbers': 'ladron', 'roll': 'tirada', 'rolled': 'tirada',
    'rolls': 'tirada', 'scoreboard': 'marcador', 'second': 'segundo',
    'send': 'manda', 'sends': 'manda', 'settle': 'poblado',
    'settled': 'poblado', 'settlement': 'poblado', 'settlements': 'poblado',
    'settles': 'poblado', 'seven': 'siete', 'sevens': 'siete', 'sheep': 'lana',
    'short': 'corto', 'should': 'deberia', 'sixth': 'sexto',
    'someone': 'alguien', 'soonest': 'primero', 'spot': 'casilla',
    'spots': 'casilla', 'start': 'salida', 'started': 'salida',
    'starting': 'salida', 'starts': 'salida', 'steal': 'robo',
    'steals': 'robo', 'stole': 'robo', 'stolen': 'robo', 'suffered': 'sufrio',
    'swap': 'trato', 'table': 'mesa', 'tables': 'mesa', 'take': 'saca',
    'taken': 'pillo', 'takes': 'saca', 'than': '', 'that': '', 'the': '',
    'their': '', 'them': '', 'there': '', 'they': '', 'thief': 'ladron',
    'third': 'tercero', 'this': '', 'throw': 'tirada', 'throws': 'tirada',
    'tile': 'casilla', 'tiles': 'casilla', 'time': 'veces', 'times': 'veces',
    'to': '', 'took': 'saca', 'total': 'total', 'trade': 'trato',
    'traded': 'trato', 'trades': 'trato', 'turn': 'turno', 'turns': 'turno',
    'up': '', 'us': 'nos', 'use': 'uso', 'used': 'uso', 'uses': 'uso',
    'victory': 'victoria', 'was': '', 'we': '', 'were': '', 'what': '',
    'wheat': 'cereales', 'when': 'cuando', 'where': 'donde', 'which': 'cual',
    'who': 'quien', 'whom': 'quien', 'whose': 'quien', 'win': 'victoria',
    'winner': 'victoria', 'wins': 'victoria', 'with': 'con', 'won': 'victoria',
    'wood': 'madera', 'wool': 'lana', 'worst': 'peor', 'you': '',
}

# Y con lo que CONTESTA la caja. Son plantillas de `%`, no de `{}`: los
# huecos van por ORDEN y no por nombre, asi que una traduccion que se coma un
# `%s` o que le cambie el orden no se ve rara, revienta al pintarla o dice
# otra cosa. `db/pruebas.py` los compara uno a uno.
#
# Las cuatro ultimas no son frases sino palabras que se meten DENTRO de las
# plantillas: «El que %s %s» se rellena con «mas» o «menos», y las vistas de
# parejas enlazan los dos nombres con «con» o con «a».
RESPUESTAS = {
    '  (juntando las filas de «%s»)': '  (merging the rows of “%s”)',
    '  (sumando %d filas)': '  (adding up %d rows)',
    '  Aunque con estos datos no se sale nadie del margen: la diferencia cabe en el error.':
        '  Though with this data nobody is outside the margin: the difference fits inside the error.',
    '  Repartido: ': '  Spread out: ',
    '  Sobre todo %s (%d de %d).': '  Mostly %s (%d of %d).',
    '%d, en «%s».': '%d, in “%s”.',
    '%s a %s: %s de %s.': '%s to %s: %s of %s.',
    '%s a %s: ninguna vez, en «%s».': '%s to %s: not once, in “%s”.',
    '%s con %s %s: %s, con %s.': '%s with %s %s: %s, with %s.',
    '%s no sale en «%s».': '%s does not show up in “%s”.',
    '%s, %s %s %s: %s, con %s de %s.': '%s, %s %s %s: %s, with %s of %s.',
    '%s, %s: %s': '%s, %s: %s',
    '%s, %s: %s  (una por partida)': '%s, %s: %s  (one per game)',
    '%s, en el %s (%s: %s).': '%s, on the %s (%s: %s).',
    '%s: %d en «%s».': '%s: %d in “%s”.',
    '%s: %s de %s.': '%s: %s of %s.',
    'El que %s %s: %s, con %s (%s de %s).':
        'The one with the %s %s: %s, with %s (%s of %s).',
    'El que %s %s: %s, con %s.': 'The one with the %s %s: %s, with %s.',
    'En el %s no hay %s.': 'On the %s there is no %s.',
    'En el %s no hay nada en «%s».': 'On the %s there is nothing in “%s”.',
    'En el %s no hay ninguno: %s es 0.': 'On the %s there are none: %s is 0.',
    'En el %s: %s %s.': 'On the %s: %s %s.',
    'En el %s: %s.': 'On the %s: %s.',
    'En total, %s de %s.': 'In total, %s of %s.',
    'Eso no lo tengo en una columna, pero lo que preguntas esta en «%s», aqui debajo.':
        'I do not have that in a column, but what you are asking about is in “%s”, just below.',
    'Eso no lo tengo guardado en ninguna vista. Prueba con otra palabra: caballeros, monopolios, puertos, robos, suerte, tiradas, puntos, ladron, comercio...':
        'I have not got that stored in any view. Try another word: knights, monopolies, ports, steals, luck, rolls, points, robber, trade...',
    'Eso no sale en un numero. Lo tienes en «%s», aqui debajo.':
        'That does not come out as a number. You have it in “%s”, just below.',
    'Lo de %s con %s esta aqui debajo.': 'What %s did with %s is just below.',
    'Lo del %s esta aqui debajo.': 'The %s is just below.',
    'Lo que preguntas esta en «%s», columna «%s».':
        'What you are asking about is in “%s”, column “%s”.',
    'Lo tienes en «%s», aqui debajo.': 'You have it in “%s”, just below.',
    'No se de que me hablas. Nombra algo: caballeros, monopolios, puertos, robos, suerte, tiradas, puntos, ladron...':
        'I do not know what you mean. Name something: knights, monopolies, ports, steals, luck, rolls, points, robber...',
    'Preguntame algo.': 'Ask me something.',
    'Todavia no hay base de datos.': 'There is no database yet.',
    'a': 'to',
    'con': 'with',
    'mas': 'most',
    'menos': 'least',
    'no se ha podido leer la base: %s': 'could not read the database: %s',
    '«%s» me vale para %d personas (%s). Dime cual, o ponles nombre en el paso 2: mientras se llamen todos «jugador_algo» no los puedo distinguir.':
        '“%s” matches %d people (%s). Tell me which one, or name them in step 2: while they are all called “jugador_something” I cannot tell them apart.',
}


# Y lo que escriben por pantalla el INSTALADOR y el IMPORTADOR. No son la
# pagina ni el servidor: son dos procesos aparte que el panel lanza, y su
# salida se ve tal cual en el registro de abajo. El instalador es el paso 0,
# lo primero que hace alguien que acaba de clonar esto, y ahi es donde lee
# por que no encuentra Catan o por que no ha compilado el plugin.
#
# Los comandos y las rutas se traducen a si mismos, a proposito: escritos de
# otra forma no existirian. Estan en la lista para que `db/pruebas.py` pueda
# exigirlas todas sin excepciones que alguien tenga que mantener.
CONSOLA = {
    '         %-58s x%d': '         %-58s x%d',
    '         La grabación está entera y guardada: cuando el importador':
        '         The recording is whole and saved: when the importer',
    '         Le pasaba al tablero de 5-6 jugadores: ahí el juego deja':
        '         It happened on the 5-6 player board: there the game leaves',
    '         Sin su posición no hay bloqueos Y LA PRODUCCIÓN SALE DE MÁS:':
        '         Without its position there are no blocks AND PRODUCTION COMES OUT HIGH:',
    '         `GamePiecesRobber` vacío y guarda al ladrón en':
        '         `GamePiecesRobber` empty and keeps the robber in',
    '         `GamePiecesRobbers[0]`. Ya arreglado -- el mod':
        '         `GamePiecesRobbers[0]`. Already fixed: the mod',
    '         aprenda estas acciones, `--rehacer` mete la partida sin':
        '         learns these actions, `--rehacer` brings the game in',
    '         en el .jsonl, que trae los nombres candidatos.':
        '         in the .jsonl, which carries the candidate names.',
    '         juego ha vuelto a moverlo de sitio: mira `ladron_donde_buscar`':
        '         game has moved it again: look at `ladron_donde_buscar`',
    '         jugando ahora mismo. Si era lo segundo, cuando acabe:':
        '         being played right now. If it was the latter, when it ends:',
    '         perder nada.': '         without losing anything.',
    '         propio juego. Si esto sale en una grabación NUEVA, el':
        '         own accessor. If this shows up in a NEW recording, the',
    '         py mod_verdad/importar.py --rehacer':
        '         py mod_verdad/importar.py --rehacer',
    '         se cuenta como si el ladrón no estuviera en el tablero.':
        '         it is counted as if the robber were not on the board.',
    '         usa ya `BoardQuery.GetRobberTile`, que es el accesor del':
        "         now uses `BoardQuery.GetRobberTile`, which is the game's",
    '        panel, o aqui:  py mod_verdad/importar.py --llamar %s Pedro':
        '        panel, or here:  py mod_verdad/importar.py --llamar %s Pedro',
    '        ponle el suyo con el boton «Ponerle nombre a alguien» del':
        '        give them theirs with the «Name someone» button on the',
    '       Hazlo a mano: py db/vistas.py --crear':
        '       Do it by hand: py db/vistas.py --crear',
    '     %s': '     %s',
    '     [!] %d acciones que no entiendo, de %d tipos distintos%s.':
        '     [!] %d actions I do not understand, of %d different kinds%s.',
    '     [!] EL LADRON NO SE HA PODIDO LEER en %d movimientos.':
        '     [!] THE ROBBER COULD NOT BE READ in %d moves.',
    '     [!] esta partida no tiene final: o se abandonó o se está':
        '     [!] this game has no ending: either it was abandoned or it is',
    "    [!] identificador nuevo sin nombre: %s -> se ha llamado '%s'":
        "    [!] new identifier with no name: %s -> it was called '%s'",
    '   %s': '   %s',
    '   ... jugar ...': '   ... play ...',
    '   .\\mod_verdad\\interruptor.ps1 off':
        '   .\\mod_verdad\\interruptor.ps1 off',
    '   .\\mod_verdad\\interruptor.ps1 on        y DESPUES abrir Catan':
        '   .\\mod_verdad\\interruptor.ps1 on        and THEN open Catan',
    '   C:\\Windows\\Microsoft.NET\\Framework\\v4.0.30319\\csc.exe':
        '   C:\\Windows\\Microsoft.NET\\Framework\\v4.0.30319\\csc.exe',
    '   NO LO ENCUENTRO. Se le pregunta a Steam, asi que:':
        '   CANNOT FIND IT. Steam is the one being asked, so:',
    '   No ha compilado. Hace falta el csc que trae Windows, en':
        '   It did not compile. It needs the csc that ships with Windows, at',
    '   abre Steam una vez, o instala el juego, y vuelve a pasar esto.':
        '   open Steam once, or install the game, and run this again.',
    '   bajando %s ...': '   downloading %s ...',
    '   es de %s': '   it is %s',
    '   faltan: %s': '   missing: %s',
    '   py mod_verdad\\importar.py': '   py mod_verdad\\importar.py',
    '   py panel.py                        y el boton «Encender el mod»':
        '   py panel.py                        and the «Switch the mod on» button',
    '   ya esta puesto, no se toca': '   already in place, not touched',
    "  %s  (ahora '%s')": "  %s  (now '%s')",
    '  -  %-28s %s': '  -  %-28s %s',
    '  OK %-28s partida %d: %s': '  OK %-28s game %d: %s',
    '  py mod_verdad/importar.py --llamar <identificador> <nombre>':
        '  py mod_verdad/importar.py --llamar <identifier> <name>',
    '  py mod_verdad/importar.py --llamar <identificador> Pedro':
        '  py mod_verdad/importar.py --llamar <identifier> Pedro',
    '%-40s %-16s %d%s': '%-40s %-16s %d%s',
    '%-40s %-16s %s': '%-40s %-16s %s',
    '%d eventos -> %s': '%d events -> %s',
    '%d partidas importadas.': '%d games imported.',
    "%s ahora se llama '%s' (antes '%s'); %d partidas actualizadas.":
        "%s is now called '%s' (was '%s'); %d games updated.",
    '1. Catan Universe': '1. Catan Universe',
    '2. BepInEx          %s': '2. BepInEx          %s',
    '2. Dependencias de Python': '2. Python dependencies',
    '3. BepInEx %s': '3. BepInEx %s',
    '3. el plugin        %s': '3. the plugin       %s',
    '32 bits': '32-bit',
    '4. El plugin': '4. The plugin',
    '64 bits': '64-bit',
    'Aviso: no se han podido rehacer las vistas (%s).':
        'Warning: could not rebuild the views (%s).',
    'Catan Universe no lo permiten. Instalarlo y encenderlo son dos':
        'Universe do not allow that. Installing it and switching it on are',
    'Cuando quieras:': 'Whenever you want:',
    'Dejar el mod listo': 'Get the mod ready',
    'El mod modifica el cliente del juego, y las condiciones de uso de':
        'The mod modifies the game client, and the terms of use of Catan',
    'FALTA': 'MISSING',
    'Hay %d persona(s) sin nombre de verdad:':
        'There are %d person(s) with no real name:',
    'Listo, y APAGADO.': 'Ready, and SWITCHED OFF.',
    'Nada tocado (--ver). Pasa esto sin --ver para dejarlo listo.':
        'Nothing touched (--ver). Run this without --ver to get it ready.',
    'No conozco el identificador %s. Míralos con --quien.':
        'I do not know the identifier %s. List them with --quien.',
    "No encuentro '%s'. Las que hay:":
        "I cannot find '%s'. The ones there are:",
    'No hay ficheros del mod en %s': 'There are no mod files in %s',
    'Para ponerle nombre a alguien:': 'To give someone a name:',
    'Todavía no hay ningún identificador. Importa una partida primero.':
        'There are no identifiers yet. Import a game first.',
    'Ya se llamaba así.': 'It was already called that.',
    'apartado del README antes de encenderlo.':
        'Read that section of the README before switching it on.',
    'copia actualizada': 'copy updated',
    'copia guardada': 'copy saved',
    'decisiones distintas, y esto solo ha tomado la primera. Lee el':
        'two different decisions, and this has only taken the first one.',
    'el paquete no trae winhttp.dll; no se toca nada':
        'the package has no winhttp.dll; nothing touched',
    'identificador de la cuenta': 'account identifier',
    'ninguna: esto va con la biblioteca estandar':
        'none: this runs on the standard library',
    'nombre': 'name',
    'o a mano:': 'or by hand:',
    'partidas': 'games',
    'puesto en %s, y APAGADO': 'installed in %s, and SWITCHED OFF',
    'ya esta': 'already there',
    'ya estan': 'already there',
    '¿Has jugado alguna partida con el mod encendido?':
        'Have you played a game with the mod switched on?',
}


# Qué quiere decir cada columna y qué es una fila. NO está aquí: vive en
# `catalogEN.py`, al lado, y está escrito ENTERO en inglés -- los nombres de
# vista y de columna incluidos. Quien lo abre ya está leyendo en inglés; no
# se le pone `del_reparto` delante para que lo adivine.
#
# Aquí se traduce de vuelta, porque la base de datos sí habla en castellano:
# `VISTAS` casa cada vista con su nombre inglés, y con eso las fichas se
# vuelven a guardar bajo la clave con la que el resto del programa pregunta.
# `db/pruebas.py` exige que el casamiento salga entero por los dos lados, así
# que el día que una vista cambie de nombre no se pierde en silencio.
from . import catalogEN                                      # noqa: E402
import db.columnas as _es                                    # noqa: E402

VISTAS = {
    "partidas": "games",
    "jugadores": "players",
    "amigos_marcador": "friends_scoreboard",
    "amigos_puntos": "friends_points",
    "amigos_ritmo": "friends_pace",
    "amigos_salida": "friends_start",
    "amigos_por_salida": "friends_by_start",
    "amigos_salida_de_cada_uno": "friends_start_by_player",
    "amigos_salida_como_acabo": "friends_finish_from_start",
    "amigos_desarrollo": "friends_development",
    "amigos_mazo": "friends_deck",
    "amigos_monopolios": "friends_monopolies",
    "amigos_monopolios_a_quien": "friends_monopolies_to_whom",
    "amigos_ladron": "friends_robber",
    "amigos_ladron_proporcion": "friends_robber_ratio",
    "amigos_ladron_a_quien": "friends_robber_to_whom",
    "amigos_ladron_a_quien_numero": "friends_robber_to_whom_number",
    "amigos_ladron_numeros": "friends_robber_numbers",
    "amigos_ladron_donde": "friends_robber_where",
    "amigos_robos": "friends_steals",
    "amigos_comercio": "friends_trade",
    "amigos_saldo": "friends_balance",
    "amigos_tratos": "friends_deals",
    "amigos_comercio_material": "friends_trade_resource",
    "amigos_puertos": "friends_ports",
    "amigos_cuantos_puertos": "friends_ports_count",
    "amigos_puertos_pillados": "friends_ports_claimed",
    "amigos_produccion": "friends_production",
    "amigos_numeros": "friends_numbers",
    "amigos_sietes": "friends_sevens",
    "amigos_tiradas": "friends_rolls",
    "amigos_suerte": "friends_luck",
}



def _casar(aqui, alli, donde):
    """Empareja columna a columna. Las dos listas van en el mismo orden.

    Con `zip` a secas, una lista más corta se recorta sola y una columna se
    quedaría sin explicación sin que nadie se entere. Y una más larga es
    peor: emparejaría la columna equivocada con el texto equivocado, que se
    lee como si fuera verdad. Por eso esto revienta al arrancar en vez de
    dejarlo pasar.
    """
    if len(aqui) != len(alli):
        raise ValueError(
            "%s: la base tiene %d columnas y catalogEN.py explica %d. "
            "Sobra o falta una ficha, y hasta que no cuadren no se sabe "
            "cuál lleva cada texto." % (donde, len(aqui), len(alli)))
    return dict(zip(aqui, alli.values()))


COMUNES = _casar(_es.COMUNES, catalogEN.SHARED, "las comunes")
POR_VISTA = {_v: _casar(_es.POR_VISTA[_v], catalogEN.BY_VIEW[_en], _v)
             for _v, _en in VISTAS.items()}

# `fila` y `para` son los nombres que usa el programa; en el fichero inglés
# se llaman `row` y `for`, que es como los lee quien va a leerlos.
FILA_ES = {_v: {"fila": catalogEN.ROW_IS[_en]["row"],
                "para": catalogEN.ROW_IS[_en]["for"]}
           for _v, _en in VISTAS.items() if _en in catalogEN.ROW_IS}
