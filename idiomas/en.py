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

# Lo que pone el botón que TRAE a este idioma. Dice a dónde vas, no dónde
# estás, igual que el de claro/oscuro.
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
    "El mod no guarda nombres, guarda el identificador de cada cuenta &mdash; "
    "que es estable, asi que reconoce a la misma persona partida tras partida. "
    "La primera vez que juegue alguien nuevo saldra con un nombre provisional "
    "(":
        "The mod doesn't store names, it stores each account's identifier "
        "&mdash; which is stable, so it recognises the same person game after "
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
    ", y eso no se nota en la tabla &mdash; se nota en las medias. Antes de "
    "borrar hace una":
        ", and that doesn't show up in the table &mdash; it shows up in the "
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
    "que pinta la tabla de abajo &mdash; dale al enlace de cada uno y la "
    "tienes delante.":
        "that draws the table below &mdash; click each one's link and there it "
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
    "O preguntalo en cristiano y te lo busco en las tablas &mdash;":
        "Or just ask in plain language and it looks it up in the tables "
        "&mdash;",
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
    ", as&iacute; que de serie salen todas &mdash; separarlas lo decides "
    "t&uacute;.":
        ", so by default you get all of them &mdash; splitting them up is your "
        "call.",
    "Sale de las mismas vistas que": "This comes from the same views as",
    'py sql.py "SELECT * FROM amigos_marcador"':
        'py sql.py "SELECT * FROM amigos_marcador"',
    "&mdash; no hay dos consultas que puedan decir cosas distintas. La base se "
    "abre aqui en":
        "&mdash; there aren't two queries that could disagree. The database is "
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
    "preguntame algo &mdash; cuantos caballeros le han caido a elGato":
        "ask me something &mdash; how many knights has elGato had",
    "filtrar &mdash; un texto busca por dentro (carla, 2:1); un numero busca "
    "exacto (4)":
        "filter &mdash; text searches inside (carla, 2:1); a number matches "
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
    ", solo hace capturas. No hay nada que configurar &mdash; dale y ya.":
        ", it only takes screenshots. There's nothing to configure &mdash; "
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
    "si puedes: la referencia del sitio vacio &mdash; la mitad de lo que se "
    "mira &mdash; se toma de las primeras fotos y se congela con la primera "
    "pieza. Arrancando a mitad de partida, lo que ya estuviera puesto se toma "
    "por tablero y no se ve. Ademas de las piezas se lee":
        "if you can: the reference for an empty spot &mdash; half of what gets "
        "looked at &mdash; is taken from the first frames and frozen with the "
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
    ") &mdash; lee que hay en cada vertice y cada arista. Es la que se entrena "
    "con el boton de aqui abajo.":
        ") &mdash; reads what's on each vertex and each edge. This is the one "
        "the button below trains.",
    "Las plantillas": "The templates",
    "plantillas_puntos.npz": "plantillas_puntos.npz",
    "plantillas_cartas.npz": "plantillas_cartas.npz",
    ", los digitos) &mdash; no son una red: son el promedio de miles de "
    "recortes ya etiquetados. De ahi salen los contadores de los paneles, con "
    "97,3% en caballeros y 98,9% en desarrollo.":
        ", the digits) &mdash; these aren't a network: they're the average of "
        "thousands of already-labelled crops. The panel counters come from "
        "them, at 97.3% on knights and 98.9% on development.",
    "El aviso de la esquina": "The corner ticker",
    "ocr/ticker.py": "ocr/ticker.py",
    ") &mdash; ese usa Tesseract y": ") &mdash; that one uses Tesseract and",
    "no se entrena": "isn't trained",
    ". Las capturas sirven para MEDIRLO (20 robos de 20, 23 comercios de 30) "
    "y para ajustar el recorte y el umbral de tinta.":
        ". The screenshots are for MEASURING it (20 steals out of 20, 23 "
        "trades out of 30) and for tuning the crop and the ink threshold.",
    "Entrenar la red con lo grabado":
        "Train the network on what's been recorded",
    "Un boton. Convierte lo grabado,": "One button. It converts the recording,",
    "examina": "tests",
    "el modelo de antes con la partida nueva &mdash; que no ha visto &mdash; y "
    "solo entonces entrena con ella. En ese orden, porque al reves el numero "
    "sale inflado y no avisa de nada.":
        "the previous model on the new game &mdash; which it hasn't seen "
        "&mdash; and only then trains on it. In that order, because the other "
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
    '"✕ sin panel — Catan Tracker"': '"✕ no panel — Catan Tracker"',
    '"☀︎  Claro"': '"☀︎  Light"',
    '"☽  Oscuro"': '"☽  Dark"',
    '"● MOD ENCENDIDO — Catan Tracker"': '"● MOD ON — Catan Tracker"',
    '"El mod no esta instalado en el juego."':
        '"The mod is not installed in the game."',
    '"<small>Dale a <b>Dejarlo listo</b>, aqui debajo.</small>"':
        '"<small>Press <b>Get it ready</b>, just below.</small>"',
    '"EL MOD ESTA ENCENDIDO"': '"THE MOD IS ON"',
    '" y grabando"': '" and recording"',
    '" &mdash; apuntando: <b>"': '" &mdash; recording: <b>"',
    '" &mdash; ultima partida apuntada: "':
        '" &mdash; last game recorded: "',
    '" acciones"': '" actions"',
    '"</b> acciones"': '"</b> actions"',
    '"El interruptor esta apagado, pero Catan esta abierto."':
        '"The switch is off, but Catan is open."',
    '"Registro · lo que apunta el mod"': '"Log · what the mod is recording"',
    '"Registro · grabacion"': '"Log · recording"',
    '"Registro · "': '"Log · "',
    # Estas dos van con comilla SIMPLE en el guion, porque llevan HTML con
    # comillas dobles dentro. La clave tiene que ser el literal tal cual.
    "'<p class=\"vacio\">No hay ninguna partida guardada.</p>'":
        "'<p class=\"vacio\">No games saved yet.</p>'",
    '"Todavia no hay ninguna partida guardada."': '"No games saved yet."',
    '"Todas las partidas"': '"All games"',
    "'<p class=\"vacio\">buscando...</p>'":
        "'<p class=\"vacio\">searching...</p>'",
    '"no se ha podido"': '"it didn\'t work"',
    '"No se ha podido quitar: "': '"Could not remove it: "',
    '"Ahora mismo llegan "': '"Right now that\'s "',
    '"Todavia no llega nadie: el que mas lleva es "':
        '"Nobody qualifies yet: the highest is "',
    # Las cuatro veces que sale «En la ventana negra», con su espaciado y su
    # <code> tal cual: son literales distintos aunque digan lo mismo.
    '"En la ventana negra:  "': '"In the black window:  "',
    '".  En la ventana negra:  <code>"': '".  In the black window:  <code>"',
    '"En la ventana negra: <code>py db/vistas.py --crear</code></p>"':
        '"In the black window: <code>py db/vistas.py --crear</code></p>"',
    # El contador de filas de debajo del filtro.
    '" fila" : " filas"': '" row" : " rows"',
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
    # --- los siete grupos de tablas ---------------------------------------
    "Las partidas": "The games",
    "Puntos y ritmo": "Score and pace",
    "Cartas de desarrollo": "Development cards",
    "El ladrón": "The robber",
    "Comercio": "Trade",
    "Puertos": "Ports",
    "El tablero y los dados": "The board and the dice",

    # --- las 32 tablas: título y qué contesta ------------------------------
    "Partidas": "Games",
    "una por partida, con quién ganó, cuántas casillas tenía el tablero y si "
    "eran todos personas":
        "one row per game, with who won, how many tiles the board had and "
        "whether everyone was human",
    "Jugadores": "Players",
    "una fila por jugador y partida, con el nombre ya resuelto":
        "one row per player per game, with the name already resolved",
    "Marcador": "Scoreboard",
    "partidas, victorias y puntos medios de cada uno, por tamaño de mesa":
        "games, wins and average score for each player, by table size",
    "El orden de salida": "Turn order",
    "en qué puesto salió cada uno y en cuál acabó":
        "which seat each player started from and where they finished",
    "¿Importa salir primero?": "Does going first matter?",
    "qué tal le va a cada puesto de salida, sumando todas las partidas":
        "how each starting seat does, across every game",
    "Con qué salida le toca a cada uno": "Which seat each player gets",
    "cuántas veces ha salido primero, segundo, tercero… cada persona":
        "how many times each person has started first, second, third…",
    "De cada salida, cómo acabó": "From each seat, how it ended",
    "de las veces que salió en cada puesto, en cuáles acabó":
        "of the times they started from each seat, where they finished",
    "De dónde salió cada punto": "Where each point came from",
    "edificios, premios y — por resta — las cartas de punto":
        "buildings, awards and — by subtraction — the victory point cards",
    "qué le tocó a cada uno de las cartas que compró":
        "what each player got out of the cards they bought",
    "El mazo": "The deck",
    "qué salió contra lo que el mazo lleva dentro":
        "what came out against what the deck actually holds",
    "Los monopolios": "The monopolies",
    "quién tiró cada monopolio y qué recurso pidió":
        "who played each monopoly and which resource they called",
    "El monopolio, uno a uno": "Monopolies, one by one",
    "cuántas cartas de cada recurso le ha sacado cada uno a cada uno":
        "how many cards of each resource each player has taken off each other",
    "recursos que no dejó producir, contra los que sí se cobraron":
        "resources it stopped from being produced, against the ones that were "
        "collected anyway",
    "¿A quién se ceba el ladrón?": "Who does the robber pick on?",
    "si a alguien le ponen el ladrón más de lo que le toca, descontando "
    "cuánto juega y cuántas casillas tiene":
        "whether anyone gets the robber more than their share, allowing for "
        "how much they play and how many tiles they hold",
    "El ladrón, uno a uno": "The robber, one by one",
    "quién se lo puso a quién, cuántas veces le tocó y qué le costó":
        "who put it on whom, how many times it landed and what it cost them",
    "El ladron: a quien y en que numero": "The robber: on whom and on which "
                                          "number",
    "a quien se lo puso cada uno y sobre que numero":
        "who each player put it on and on which number",
    "Dónde pone el ladrón cada uno": "Where each player puts the robber",
    "a qué número lo manda cada uno, cuántas veces, y si por el 7 o con un "
    "caballero":
        "which number each player sends it to, how often, and whether by a 7 "
        "or with a knight",
    "Los números que más tapa el ladrón": "The numbers the robber blocks most",
    "a qué números va el ladrón, sumando a todo el mundo":
        "which numbers the robber goes to, adding everyone together",
    "Producción": "Production",
    "qué recursos le dio el tablero a cada uno, y de qué anda corto":
        "which resources the board gave each player, and what they're short of",
    "Los números de cada uno": "Each player's numbers",
    "en qué números se puso, cuántas veces salieron y qué sacó":
        "which numbers they settled on, how often those came up and what they "
        "got",
    "La suerte de cada uno": "Everyone's dice luck",
    "de las casillas donde está puesto, cuántas veces le pagó el tablero "
    "contra las que le debía. 100 es la suerte normal":
        "for the tiles they're on, how many times the board paid out against "
        "how many it owed. 100 is normal luck",
    "Quién propone tratos a quién": "Who proposes trades to whom",
    "quién mueve ficha: sólo los tratos que propuso cada uno, y cómo le "
    "salieron ESOS":
        "who makes the first move: only the trades each player proposed, and "
        "how THOSE went for them",
    "El saldo con cada uno": "The balance with each player",
    "quién gana cartas con quién y quién las pierde: el saldo de verdad, con "
    "TODOS sus tratos dentro, los propusiera quien los propusiera (sin la "
    "banca)":
        "who gains cards off whom and who loses them: the real balance, with "
        "ALL their trades in it, whoever proposed them (bank trades excluded)",
    "Trato a trato": "Trade by trade",
    "cada intercambio con los dos lados: quién dio qué y a cambio de qué":
        "every trade with both sides: who gave what and in exchange for what",
    "Qué se comercia": "What gets traded",
    "qué recurso da y cuál recibe cada uno, y con quién":
        "which resource each player gives and which they get, and with whom",
    "Puerto a puerto": "Port by port",
    "una fila por puerto usado: cuál, cuántas veces y entre qué turnos":
        "one row per port used: which one, how many times and between which "
        "turns",
    "Quién pilló cada puerto": "Who claimed each port",
    "los nueve puertos del mapa y quién se quedó cada uno, incluidos los que "
    "no pilló nadie":
        "the nine ports on the map and who ended up with each, including the "
        "ones nobody took",
    "Cuántos, por jugador": "How many, per player",
    "una fila por jugador: cuántos puertos se le pueden contar y cuáles":
        "one row per player: how many ports can be counted for them, and "
        "which",
    "El ritmo de cada uno": "Everyone's pace",
    "en qué turno llegó a su primera ciudad, su primera carta...":
        "which turn they reached their first city, their first card...",
    "Robos de la mano": "Steals from the hand",
    "cuántos hizo y cuántos sufrió cada uno (cuántos, no cuáles)":
        "how many each player made and how many they suffered (how many, not "
        "which)",
    "Las tiradas": "The dice rolls",
    "qué salió contra lo que debería haber salido":
        "what came up against what should have come up",
    "Los sietes de cada uno": "Everyone's sevens",
    "quién saca más sietes al tirar, contra el 16,7% que toca":
        "who rolls the most sevens, against the 16.7% that's expected",

    # --- lo que dice una tabla cuando no tiene filas -----------------------
    "Ninguno todavía. Si en la partida se jugó alguno y aquí no sale, es que "
    "la carta no llegó a apuntarse: el recurso sólo se engancha a una jugada "
    "del mismo jugador y el mismo turno.":
        "None yet. If one was played in the game and doesn't show up here, "
        "the card never got recorded: the resource is only tied to a play by "
        "the same player on the same turn.",
    "Aquí sólo entran los monopolios de los que se sabe cuánto se llevaron. "
    "Si en esta partida se jugó alguno y no sale, es de antes del 22/8/2026: "
    "el mod no leía el reparto todavía. Están en «Los monopolios», con quién "
    "lo tiró y qué pidió.":
        "Only monopolies whose haul is known get in here. If one was played "
        "in this game and doesn't show up, it's from before 22/8/2026: the mod "
        "wasn't reading the handover yet. They're in «The monopolies», with "
        "who played it and what they called.",
    "De esta partida no se puede saber. Que alguien USE un puerto se deduce "
    "de los comercios y eso está en «Puerto a puerto»; PILLARLO es otra cosa "
    "y necesita saber dónde está cada puerto en el tablero. El mod no lo leía "
    "bien hasta el 22/8/2026 -- la posición viene en una `EdgePosition` y se "
    "estaba leyendo como si fuera otra clase, así que llegaba vacía -- y eso "
    "no se puede recuperar sin volver a jugar la partida.":
        "There's no way to know for this game. That someone USES a port is "
        "deduced from their trades and that's in «Port by port»; CLAIMING one "
        "is a different thing and needs to know where each port sits on the "
        "board. The mod wasn't reading that correctly until 22/8/2026 -- the "
        "position comes in an `EdgePosition` and was being read as if it were "
        "another class, so it arrived empty -- and that can't be recovered "
        "without playing the game again.",

    # --- los dos filtros ----------------------------------------------------
    "solo con amigos (sin la IA)": "only with friends (no AI)",
    "todas, la IA incluida": "all of them, AI included",
    "solo las partidas contra la IA": "only the games against the AI",
    "mesas de cualquier tamaño": "tables of any size",
    "solo mesas de 4": "only 4-player tables",
    "solo mesas de 5 y 6": "only 5- and 6-player tables",

    # --- los titulares. OJO CON LAS LLAVES ---------------------------------
    # Las dos parejas: el titular no es una persona, son dos.
    "{quien} a {a_quien}": "{quien} on {a_quien}",
    "{quien} con {con_quien}": "{quien} with {con_quien}",
    "Quién gana más": "Who wins most",
    "{victorias} de {partidas}": "{victorias} of {partidas}",
    "en mesa de {eran}. Acaba de media en el puesto {puesto_medio}, con "
    "{puntos_medios} puntos.":
        "at a {eran}-player table. Finishes {puesto_medio} on average, with "
        "{puntos_medios} points.",
    "En mesa de 5 y 6 manda {quien}, con {victorias} de {partidas}.":
        "At 5- and 6-player tables {quien} leads, with {victorias} of "
        "{partidas}.",
    "En mesa de 5 y 6 no ha ganado todavía ninguno de los que llegan al "
    "mínimo.":
        "At 5- and 6-player tables none of the players who reach the minimum "
        "has won yet.",
    "Quién saca más sietes": "Who rolls the most sevens",
    "{porcentaje}%": "{porcentaje}%",
    "de sus tiradas: {sietes} sietes en {tiros} tiros. Lo normal es "
    "{porcentaje_normal}%.":
        "of their rolls: {sietes} sevens in {tiros} throws. Normal is "
        "{porcentaje_normal}%.",
    "Quién compra más cartas de desarrollo":
        "Who buys the most development cards",
    "{por_partida} por partida": "{por_partida} per game",
    "{compradas} cartas en {partidas} partidas, {caballero} de ellas "
    "caballeros.":
        "{compradas} cards in {partidas} games, {caballero} of them knights.",
    "Quién elige mejor las casillas": "Who picks the best tiles",
    "{por_casilla} puntitos": "{por_casilla} pips",
    "de media por casilla suya, cuando un sitio cualquiera de sus tableros "
    "vale {lo_normal}. Con eso le tocaron {le_toco} cobros de los {le_tocaba} "
    "que le tocaban.":
        "on average per tile of theirs, when any spot on their boards is worth "
        "{lo_normal}. That earned them {le_toco} payouts of the {le_tocaba} "
        "they were due.",
    "Con quién se ceba el ladrón": "Who the robber picks on, and by whom",
    "{se_lo_puso} veces": "{se_lo_puso} times",
    "{con_7} veces obligado por un 7 y {con_caballero} eligiéndolo con un "
    "caballero. En {le_bloqueo} de esas veces salió el número y {a_quien} no "
    "cobró: son {le_costo} cartas que se quedó sin producir. Y aparte le "
    "quitó {le_robo} cartas de la mano.":
        "{con_7} times forced by a 7 and {con_caballero} by choice with a "
        "knight. On {le_bloqueo} of those the number came up and {a_quien} "
        "collected nothing: {le_costo} cards never produced. And on top of "
        "that took {le_robo} cards out of their hand.",
    "Quién va más en positivo, y con quién":
        "Who comes out most ahead, and with whom",
    "{neto} cartas": "{neto} cards",
    "de más en los {tratos} tratos entre los dos: se llevó {recibio} y soltó "
    "{dio}. Son cartas, no acierto — dar tres por una puede ser el mejor "
    "trato de la partida.":
        "up across the {tratos} trades between the two: took {recibio} and "
        "gave up {dio}. That's cards, not judgement — giving three for one can "
        "be the best trade of the game.",
    "Quién tiene más suerte": "Who has the most luck",
    "{suerte}%": "{suerte}%",
    "de lo que le tocaba — cobró {le_toco} veces contra las {le_tocaba} que "
    "le debía el tablero, y 100% es lo normal. Se sale {se_sale} márgenes: "
    "hace falta pasar de 2 para que sea suerte y no ruido.":
        "of what they were due — collected {le_toco} times against the "
        "{le_tocaba} the board owed them, and 100% is normal. That's {se_sale} "
        "margins out: it takes more than 2 for it to be luck and not noise.",

    # --- los records --------------------------------------------------------
    "La mejor suerte en una partida": "Best luck in a single game",
    "cobró {le_toco} veces contra las {le_tocaba} que le tocaban, y con sólo "
    "{casillas} casillas. Se sale {se_sale} márgenes de lo normal — el azar "
    "por sí solo ya mueve un {margen}%.":
        "collected {le_toco} times against the {le_tocaba} they were due, and "
        "with only {casillas} tiles. That's {se_sale} margins out from normal "
        "— chance alone already moves it {margen}%.",
    "Más ladrones en una partida": "Most robbers in a single game",
    "{se_lo_pusieron} ladrones": "{se_lo_pusieron} robbers",
    "se lo pusieron encima. En {le_bloquearon} de esas veces salió el número "
    "y no cobró: {perdido} cartas que se quedó sin producir. Más "
    "{le_robaron} que le robaron de la mano, {en_total} cartas en total.":
        "were put on them. On {le_bloquearon} of those the number came up and "
        "they collected nothing: {perdido} cards never produced. Plus "
        "{le_robaron} taken out of their hand, {en_total} cards in total.",

    # --- los nombres de tarea, que salen en el titulo del registro ---------
    "comprobar lo grabado": "check the recording",
    "preparar los datos": "prepare the data",
    "el ciclo entero (convertir, examinar, entrenar)":
        "the whole cycle (convert, test, train)",
    "como va mejorando": "how it's improving",
    "medir la red, foto a foto": "measure the network, frame by frame",
    "medir el tablero entero, como lo leeria jugando":
        "measure the whole board, as it would read it in play",
    "mirar la pantalla": "watch the screen",
    "probar la lectura en vivo sobre una partida grabada":
        "try live reading on a recorded game",
    "medir el ladron y los dados contra lo que dice el mod":
        "measure the robber and the dice against what the mod says",
    "entrenar (apartando una partida para medir)":
        "train (holding one game back to measure)",
    "reentrenar con todo (para jugar)": "retrain on everything (to play with)",
    "pruebas de la red": "network tests",
    "dejar el mod listo": "get the mod ready",
    "guardar las partidas en la base de datos":
        "save the games to the database",
    "el informe de las partidas": "the games report",
    "pruebas de las vistas": "view tests",
    "rehacer las vistas de la base": "rebuild the database views",
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
