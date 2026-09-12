# -*- coding: utf-8 -*-
"""Français.

Copia de `en.py` traducida. Para añadir el alemán se copia éste, se traduce y
se llama `de.py`: `idiomas/__init__.py` lo encuentra solo y el desplegable del
panel lo mete sin tocar nada.

Los cuatro diccionarios son cuatro sitios distintos de donde sale texto, y
ninguno avisa solo si se queda vacío -- por eso `db/pruebas.py` los exige los
cuatro enteros:

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
  FILA_ES    catálogo. No se escribe aquí: se trae de `catalogFR.py`, que
             está en francés entero, nombres de columna incluidos
"""

NOMBRE = "Français"

# Cómo se llama este idioma en el desplegable de la cabecera. Lleva delante
# el código de dos letras para que se reconozca de un vistazo aunque no
# entiendas la palabra de al lado.
BOTON = "FR  Français"

# La coma decimal. El francés la escribe igual que el castellano, así que
# aquí no cambia; el inglés sí, y por eso esto es una propiedad del idioma y
# no una constante del programa.
DECIMAL = ","


# Lo que se ve entre etiquetas de la página, y los cuatro atributos que
# lee un humano. La clave es el castellano tal cual está escrito.
TEXTO = {
    '&hellip;y grabar capturas': '&hellip;et enregistrer des captures',
    '&laquo;&hellip;y grabar capturas&raquo;':
        '&laquo;&hellip;et enregistrer des captures&raquo;',
    '&laquo;Medir el tablero entero&raquo; es el numero que importa: cuanto del tablero final queda bien leido, que es lo que tendria delante quien juega. &laquo;Foto a foto&raquo; mira recortes sueltos, donde el tablero vacio arrastra la media hacia arriba.':
        "&laquo;Mesurer le plateau entier&raquo; est le chiffre qui compte : quelle part du plateau final est lue correctement, ce qu'un joueur aurait devant lui. &laquo;Image par image&raquo; regarde des découpes isolées, où le plateau vide tire la moyenne vers le haut.",
    ', y no hay dos consultas que puedan decir cosas distintas. La base se abre aqui en':
        ", et il n'y a pas deux requêtes qui pourraient se contredire. La base s'ouvre ici",
    '(nada todavia)': "(rien pour l'instant)",
    ') usa Tesseract y': ') utilise Tesseract et',
    ') lee que hay en cada vertice y cada arista. Es la que se entrena con el boton de aqui abajo.':
        ") lit ce qu'il y a sur chaque sommet et chaque arête. C'est celui que le bouton ci-dessous entraîne.",
    '); ponle el suyo ahi arriba y se arreglan tambien':
        ') ; donne-lui son vrai nom là-haut et ça corrige aussi',
    ', a prop&oacute;sito: un titular es una costumbre y pide partidas; un r&eacute;cord es de un d&iacute;a, y si en tu primera te pusieron veintiún ladrones, te los pusieron. El enlace abre esa tabla':
        ", exprès : un titre est une habitude et demande des parties derrière ; un record est d'un jour, et si tu as reçu le voleur vingt et une fois dès ta première partie, eh bien c'est comme ça. Le lien ouvre cette table",
    ', arriba del todo, junto al boton de encender. Cada foto va emparejada con el estado exacto que apunto el mod en ese instante, asi que las etiquetas las escribe el juego y no hay que anotar nada a mano. Alimentan tres cosas distintas, y solo la primera se &laquo;entrena&raquo;:':
        ", tout en haut, à côté de l'interrupteur. Chaque image est appariée à l'état exact que le mod a enregistré à cet instant, donc les étiquettes sont écrites par le jeu et rien n'a à être annoté à la main. Elles alimentent trois choses différentes, et seule la première est &laquo;entraînée&raquo; :",
    ', as&iacute; que de serie salen todas. Separarlas lo decides t&uacute;.':
        ", donc par défaut tu les as toutes. Les séparer, c'est à toi de voir.",
    ', comprueba su SHA-256 antes de tocar nada y compila el plugin. Lo deja':
        ', vérifie son SHA-256 avant de toucher à quoi que ce soit et compile le plugin. Il le laisse',
    ', de los paneles de jugador de las esquinas, que es de donde los lees tu. Se abre una ventana con lo que va viendo.':
        ", depuis les panneaux des joueurs dans les coins, qui est là où tu les lis toi aussi. Une fenêtre s'ouvre avec ce qu'il voit.",
    ', los digitos) no son una red: son el promedio de miles de recortes ya etiquetados. De ahi salen los contadores de los paneles, con 97,3% en caballeros y 98,9% en desarrollo.':
        ", les chiffres) : ce n'est pas un réseau, c'est la moyenne de milliers de découpes déjà étiquetées. Les compteurs du panneau viennent de là, à 97,3 % sur les chevaliers et 98,9 % sur le développement.",
    ', no s&oacute;lo la p&aacute;gina. La p&aacute;gina se relee sola y con':
        'a changé, pas seulement la page. La page se recharge toute seule et',
    ', o importa una partida, que ya lo hace solo.':
        ', ou importe une partie, ce qui le fait tout seul.',
    ', que es exactamente lo que hace el boton.':
        ', ce qui est exactement ce que fait le bouton.',
    ', que si no el historico se parte en dos personas. Por consola es':
        ", parce que sinon son historique se coupe en deux personnes. Depuis la console c'est",
    ', sin dar un solo error.': 'se charge, sans une seule erreur.',
    ', solo hace capturas. No hay nada que configurar: dale y ya.':
        ", il prend seulement des captures. Il n'y a rien à configurer : appuie, c'est tout.",
    ', y apunta la grabacion para que el importador no la vuelva a meter.':
        ", et note l'enregistrement pour que l'importateur ne le remette pas.",
    ', y eso no se nota en la tabla: se nota en las medias. Antes de borrar hace una':
        ', et ça ne se voit pas dans la table : ça se voit dans les moyennes. Avant de supprimer il fait une',
    '. Las capturas sirven para MEDIRLO (20 robos de 20, 23 comercios de 30) y para ajustar el recorte y el umbral de tinta.':
        ". Les captures servent à le MESURER (20 vols sur 20, 23 échanges sur 30) et à régler la découpe et le seuil d'encre.",
    '. No hay ni un nombre ni un n&uacute;mero escritos a mano: se recalculan en cada visita, as&iacute; que el d&iacute;a que alguien adelante a otro el titular cambia solo. Y el n&uacute;mero':
        ". Pas un seul nom ni un seul chiffre n'est écrit en dur : ils sont recalculés à chaque visite, donc le jour où quelqu'un en dépasse un autre le titre change tout seul. Et le chiffre",
    '. No hay ninguna inteligencia artificial detras y no sale nada de este ordenador: la pregunta se parte en palabras y se busca entre los nombres de las vistas. Debajo de la respuesta sale siempre':
        ". Il n'y a aucune intelligence artificielle là-dedans et rien ne sort de cet ordinateur : la question est découpée en mots et rapprochée des noms des vues. Sous la réponse tu as toujours",
    '. Si lo que quieres son tus estadisticas, el primer boton apunta exactamente igual de bien.':
        '. Si ce que tu veux ce sont tes statistiques, le premier bouton enregistre tout aussi bien.',
    '0 &middot; Dejar el mod listo': '0 &middot; Préparer le mod',
    '1 &middot; Jugar': '1 &middot; Jouer',
    '2 &middot; Guardar en la base de datos':
        '2 &middot; Enregistrer dans la base',
    '2 GB por partida': '2 Go par partie',
    '3 &middot; Mirar los datos': '3 &middot; Regarder les données',
    '3 de 18': '3 sur 18',
    '3b &middot; El informe largo': '3b &middot; Le rapport long',
    '4 &middot; Leer el tablero de la pantalla':
        "4 &middot; Lire le plateau depuis l'écran",
    '5 o 6': '5 ou 6',
    ': instalarlo y encenderlo son dos decisiones distintas, y esto solo toma la primera.':
        " : l'installer et l'allumer sont deux décisions différentes, et celle-ci ne prend que la première.",
    ': lo que ven todos los que estan en la mesa. Ni las manos de nadie, ni los puntos escondidos de las cartas, ni que carta se lleva un robo. Y no guarda ni una captura de pantalla: son unos pocos KB por partida.':
        " : ce que tout le monde à la table peut voir. Jamais la main de personne, jamais les points de victoire cachés des cartes, jamais quelle carte un vol a prise. Et il n'enregistre aucune capture : quelques Ko par partie.",
    ': ocupa': ' : il prend',
    ': quitar una partida del historico no le hace perder un recorte a la vision. Y no hay deshacer, asi que pregunta.':
        " : retirer une partie de l'historique ne coûte pas une seule découpe à la moitié vision. Et il n'y a pas de retour en arrière, donc il demande d'abord.",
    ': una partida contra la IA es otro juego -- la maquina no propone tratos ni bloquea igual -- y mezclarla con las de la mesa no ensucia un poco la media, la deja sin significado. Las otras dos opciones estan para cuando SI las quieres.':
        " : une partie contre l'IA est une autre partie -- la machine ne propose pas d'échanges et ne bloque pas pareil -- et la mélanger avec la vraie table ne rend pas la moyenne un peu sale, elle la rend vide de sens. Les deux autres options sont là pour quand tu les veux VRAIMENT.",
    'Aqu&iacute; no hay m&iacute;nimo': "Ici il n'y a pas de minimum",
    'Busca Catan pregunt&aacute;ndoselo a Steam, mira si es de 32 o de 64 bits,':
        "Il trouve Catan en demandant à Steam, vérifie s'il est en 32 ou 64 bits,",
    'Buscar': 'Chercher',
    'Cambiar de idioma': 'Changer de langue',
    'Cambiar entre claro y oscuro': 'Basculer entre clair et sombre',
    'Catan Tracker': 'Catan Tracker',
    'Como va mejorando': "Comment ça s'améliore",
    'Comprobar que cuadran': 'Vérifier que ça se recoupe',
    'Comprobar que ha apuntado bien': "Vérifier que l'enregistrement est bon",
    'De aqui para abajo': "À partir d'ici",
    'De cuantos': 'Combien de joueurs',
    'Dejarlo listo': 'Tout préparer',
    'El aviso de la esquina': 'Le bandeau du coin',
    'El de siempre, en texto: quien construyo que, en que numeros se puso cada uno, el ladron, los comercios y las tiradas.':
        "Le classique, en texte : qui a construit quoi, sur quels numéros chacun s'est installé, le voleur, les échanges et les dés.",
    'El mod apunta': 'Le mod enregistre',
    'El mod no guarda nombres, guarda el identificador de cada cuenta, que es estable, asi que reconoce a la misma persona partida tras partida. La primera vez que juegue alguien nuevo saldra con un nombre provisional (':
        "Le mod ne stocke pas de noms, il stocke l'identifiant de chaque compte : il est stable, donc il reconnaît la même personne partie après partie. La première fois que quelqu'un de nouveau joue, il apparaît sous un nom provisoire (",
    'El modelo de ahora': 'Le modèle actuel',
    'El panel no responde.': 'Le panneau ne répond pas.',
    'El panel se ha quedado atr&aacute;s.': "Le panneau n'est plus à jour.",
    'Elige que partidas quieres mirar y dale a lo que sea. De serie salen':
        'Choisis quelles parties tu veux regarder et appuie sur ce que tu veux. Par défaut tu as',
    'Empieza con el': 'Commence par le',
    'Encender el mod': 'Allumer le mod',
    'Enciende el mod y': 'Allume le mod et',
    'Entrenar': 'Entraîner',
    'Entrenar la red con lo grabado':
        'Entraîner le réseau sur ce qui a été enregistré',
    'Falta algo por instalar.': 'Il reste quelque chose à installer.',
    'Guardar en la base de datos': 'Enregistrer dans la base',
    'Ha cambiado el': 'Le',
    'Hacerlo todo': 'Tout faire',
    'La mejor marca de un d&iacute;a, y en qu&eacute; partida fue.':
        "La meilleure marque d'un jour, et de quelle partie il s'agit.",
    'La red': 'Le réseau',
    'La ventana negra en la que arrancaste':
        'La fenêtre noire dans laquelle tu as lancé',
    'Las 28 vistas se guardan': 'Les 28 vues sont stockées',
    'Las plantillas': 'Les modèles',
    'Las tablas de tu base son de una versi&oacute;n anterior.':
        "Les tables de ta base viennent d'une version antérieure.",
    'Lo de 32 bits no es un detalle. Catan Universe es de 32 aunque tu Windows sea de 64, y con el paquete equivocado el juego arranca igual y el mod no carga':
        "Le coup des 32 bits n'est pas un détail. Catan Universe est en 32 bits même si ton Windows est en 64, et avec le mauvais paquet le jeu démarre très bien et le mod",
    'Lo que dicen las tablas': 'Ce que disent les tables',
    'Los colores de la mesa los lee solo':
        'Il déduit tout seul les couleurs de la table',
    'Los titulares': 'Les titres',
    'Medir el ladron y los dados': 'Mesurer le voleur et les dés',
    'Medir el tablero entero': 'Mesurer le plateau entier',
    'Medir foto a foto': 'Mesurer image par image',
    'Mira la pantalla y lee el tablero:':
        "Il regarde l'écran et lit le plateau :",
    'Mirar la pantalla': "Regarder l'écran",
    'No borra las capturas': 'Il ne supprime pas les captures',
    'O preguntalo en cristiano y te lo busco en las tablas:':
        'Ou demande simplement en langage courant et il le cherche dans les tables :',
    'Ordenar por esta columna': 'Trier par cette colonne',
    'Para desarrollar el proyecto': 'Pour travailler sur le projet',
    'Parar la tarea': 'Arrêter la tâche',
    'Parar y apagar el mod': 'Arrêter et éteindre le mod',
    'Partidas grabadas': 'Parties enregistrées',
    'Pasa lo que apunto el mod a las tablas de siempre: quien construyo que y cuando, las tiradas, el ladron, los robos, los comercios y la produccion de cada uno. Se puede dar tantas veces como quieras: las partidas que ya estan no se repiten.':
        'Déplace ce que le mod a enregistré vers les tables habituelles : qui a construit quoi et quand, les jets de dés, le voleur, les vols, les échanges et ce que chacun a produit. Appuie autant de fois que tu veux : les parties déjà enregistrées ne sont pas dupliquées.',
    'Ponerle nombre a alguien': "Nommer quelqu'un",
    'Preparar los datos': 'Préparer les données',
    'Probarlo sobre una partida grabada':
        "L'essayer sur une partie enregistrée",
    'Pruebas': 'Tests',
    'Que alimentan las capturas': 'Ce que nourrissent les captures',
    'Que partidas': 'Quelles parties',
    'Quitar una partida': 'Supprimer une partie',
    'Cargar una base de datos': 'Charger une base de données',
    'Descargar la base de datos': 'Télécharger la base de données',
    'Estos dos son para jugar en mas de un ordenador sin partir el historico '
    'en dos.':
        "Ces deux-là servent à jouer sur plus d'un ordinateur sans couper ton "
        'historique en deux.',
    'te da el fichero': 'te donne le fichier',
    'catan_stats.db': 'catan_stats.db',
    'para llevartelo, y': 'à emporter, et',
    'hace lo contrario: lo eliges aqui y este panel sigue con aquel '
    'historico.':
        "fait l'inverse : tu le choisis ici et ce panneau continue avec cet "
        'historique.',
    'Sustituye la base entera': 'Ça remplace toute la base',
    ', no junta las dos. Antes de hacerlo comprueba que el fichero es de '
    'verdad la base del Catan y guarda una':
        ', ça ne fusionne pas les deux. Avant de le faire, ça vérifie que le '
        'fichier est bien la base du Catan et ça garde une',
    'copia de la de aqui': "copie de celle d'ici",
    'dentro de': 'dans',
    ', que tampoco hay deshacer.':
        ", parce qu'ici non plus il n'y a pas de retour en arrière.",
    'R&eacute;cords de una sola partida': 'Records sur une partie',
    'Reentrenar con todo (para jugar)':
        'Réentraîner sur tout (pour jouer avec)',
    'Registro': 'Journal',
    'Rehacer las vistas': 'Refaire les vues',
    'Rehacer las vistas de la base': 'Refaire les vues de la base',
    'Sale de las mismas vistas que': 'Ça vient des mêmes vues que',
    'Se graban con': 'Elles sont enregistrées avec',
    'Solo entra quien lleve': 'Seules les personnes avec',
    'Tarda cerca de media hora: son dos entrenamientos, el que se mide (aparta dos partidas) y el que se juega (con todo dentro).':
        'Ça prend environ une demi-heure : deux entraînements, celui qui est mesuré (qui garde deux parties de côté) et celui avec lequel on joue (tout dedans).',
    'Un boton. Convierte lo grabado,':
        "Un bouton. Il convertit l'enregistrement,",
    'Una partida de': 'Une partie de',
    'Ver el informe': 'Voir le rapport',
    'Y los pasos sueltos, por si hace falta uno solo:':
        "Et les étapes une par une, au cas où tu n'en aurais besoin que d'une :",
    'abre Catan, que el mod se carga al arrancar el juego. Juega lo que quieras: no hace falta cerrar Catan entre partidas, cambia de fichero solo. Al terminar, apagalo.':
        "ouvre Catan, parce que le mod se charge au démarrage du jeu. Joue autant que tu veux : tu n'as pas à fermer Catan entre les parties, il change de fichier tout seul. Éteins-le quand tu as fini.",
    'ahora mismo': 'en ce moment',
    'apagado': 'éteint',
    'basta; el servidor no, as&iacute; que los botones nuevos pegan contra uno viejo y no hacen nada. Aqu&iacute; s&iacute; hay que cerrar la ventana negra y volver a abrirla.':
        'lui suffit ; le serveur non, donc les nouveaux boutons tapent sur un ancien et ne font rien. Cette fois il faut bien fermer la fenêtre noire et la rouvrir.',
    'buscando el juego...': 'recherche du jeu...',
    'c&oacute;digo': 'code',
    'cargando...': 'chargement...',
    'como se llama': 'son nom',
    'copia de la base': 'copie de la base',
    'copias/': 'copias/',
    'cuanto mineral ha producido carla': 'combien de minerai a produit carla',
    'cuantos caballeros le han caido a elGato':
        'combien de chevaliers a eus elGato',
    'de donde ha salido el numero': "d'où vient le chiffre",
    'de tu fichero de datos, no en el c&oacute;digo, as&iacute; que al bajarte una versi&oacute;n nueva siguen siendo las de antes. No se pierde nada y no hace falta borrar nada: dale a':
        "ton fichier de données, pas dans le code, donc télécharger une nouvelle version laisse les anciens en place. Rien n'est perdu et rien n'a besoin d'être supprimé : appuie sur",
    'dentro': 'dedans',
    'despues': 'ensuite',
    'donde esta el ladron': 'où est le voleur',
    'el modelo de antes con la partida nueva (que no ha visto) y solo entonces entrena con ella. En ese orden, porque al reves el numero sale inflado y no avisa de nada.':
        "le modèle précédent sur la nouvelle partie, qu'il n'a pas vue, et seulement après il s'entraîne dessus. Dans cet ordre, parce que dans l'autre sens le chiffre sort gonflé et n'avertit de rien.",
    'es para las que no deberian contar: una que se cancelo a medias entra':
        'sert à celles qui ne doivent pas compter : une partie abandonnée à moitié va dans',
    'examina': 'tests',
    'filtrar: un texto busca por dentro (carla, 2:1); un numero busca exacto (4)':
        "filtre : le texte cherche à l'intérieur (carla, 2:1) ; un nombre correspond exactement (4)",
    'jugador_4645eb8a': 'jugador_4645eb8a',
    'la ultima tirada': 'le dernier jet',
    'las partidas ya guardadas': 'les parties déjà enregistrées',
    'mesas de cualquier tama&ntilde;o': 'tables de toutes tailles',
    'mira que el total y cada partida por separado digan lo mismo, que los robos hechos sean los mismos que los sufridos y que nadie tenga puntos tapados imposibles. Es lo que avisaria si al tocar una consulta se colara un error callado.':
        "vérifie que le total et chaque partie séparément disent la même chose, que les vols faits correspondent aux vols subis et que personne n'a de points cachés impossibles. C'est ce qui t'avertirait si toucher à une requête laissait passer une erreur silencieuse.",
    'no es la misma con dos sillas m&aacute;s: el tablero tiene 30 casillas en vez de 19 y no reparte los n&uacute;meros igual, y se juega a 12 puntos y no a 10. Mezclarlas es el mismo problema que mezclar las de la IA, por eso el filtro se parece. Ahora mismo son':
        "n'est pas la même partie avec deux chaises de plus : le plateau a 30 tuiles au lieu de 19 et ne dispose pas les numéros pareil, et elle se joue en 12 points au lieu de 10. Les mélanger, c'est le même problème que mélanger les parties contre l'IA, et c'est pour ça que le filtre lui ressemble. En ce moment il y en a",
    'no hace falta nada': "tu n'as besoin de rien",
    'no se entrena': "n'est pas entraîné",
    'no toca el juego': 'il ne touche pas au jeu',
    'nunca': 'jamais',
    'ocr/ticker.py': 'ocr/ticker.py',
    'panel.py': 'panel.py',
    'para tener tus estadisticas. Es la otra mitad del proyecto: una red que aprende a leer el tablero de una captura, con las etiquetas que escribe el propio juego, para ver cuanto se puede saber':
        "pour avoir tes statistiques. C'est l'autre moitié du projet : un réseau qui apprend à lire le plateau depuis une capture, étiqueté par le jeu lui-même, pour voir combien on peut savoir",
    'partidas o m&aacute;s. Sin ese corte el titular se lo lleva siempre el que jug&oacute; una vez y tuvo un buen d&iacute;a, y en las tablas de abajo est&aacute;n todos igual.':
        'parties ou plus entrent. Sans cette coupure le titre revient toujours à celui qui a joué une fois et a eu un bon jour, et tout le monde est dans les tables ci-dessous de toute façon.',
    'plantillas_cartas.npz': 'plantillas_cartas.npz',
    'plantillas_puntos.npz': 'plantillas_puntos.npz',
    'preguntame algo: cuantos caballeros le han caido a elGato':
        'demande-moi quelque chose : combien de chevaliers a eus elGato',
    'py mod_verdad/importar.py --llamar &lt;identificador&gt; Pedro':
        'py mod_verdad/importar.py --llamar &lt;identifiant&gt; Pedro',
    'py sql.py "SELECT * FROM amigos_marcador"':
        'py sql.py "SELECT * FROM amigos_marcador"',
    'que pinta la tabla de abajo. Dale al enlace de cada uno y la tienes delante.':
        'qui dessine la table ci-dessous : clique sur le lien de chacun et la voilà.',
    'quien ha tenido mas suerte': 'qui a eu le plus de chance',
    'red_de_sitios.pt': 'red_de_sitios.pt',
    'saca ademas una foto por accion, para tener la pantalla y la verdad emparejadas. Es lo que alimenta la red y las plantillas, y':
        "prend aussi une capture par action, donc l'écran et la vérité terrain sont appariés. C'est ce qui nourrit le réseau et les modèles, et",
    'sale de la misma consulta': 'vient de la même requête',
    'se descarga el BepInEx que toca': 'télécharge le BepInEx qui convient',
    'se ha cerrado, o nunca llegó a abrirse. Vuelve a abrirla y recarga esta página; mientras tanto los botones de aquí no hacen nada.':
        "a été fermée, ou n'a jamais été ouverte. Rouvre-la et recharge cette page ; en attendant, les boutons ici ne font rien.",
    'si puedes: la referencia del sitio vacio (la mitad de lo que se mira) se toma de las primeras fotos y se congela con la primera pieza. Arrancando a mitad de partida, lo que ya estuviera puesto se toma por tablero y no se ve. Ademas de las piezas se lee':
        "si tu peux : la référence d'un emplacement vide, la moitié de ce qui est regardé, est prise dans les premières images et figée avec la première pièce. En commençant en cours de partie, tout ce qui était déjà construit est pris pour du plateau et jamais vu. En plus des pièces il lit aussi",
    'sin ganador y sin puntos': 'sans vainqueur et sans score',
    'sin tocar el cliente': 'sans toucher au client',
    'solo con amigos (sin la IA)': 'seulement entre amis (sans IA)',
    'solo informacion publica': "seulement de l'information publique",
    'solo las de amigos': 'seulement celles entre amis',
    'solo lectura': 'en lecture seule',
    'solo sirve para eso': "elle ne sert à rien d'autre",
    'tablero vacio': 'plateau vide',
    'ya filtrada por esa partida': 'déjà filtrée sur cette partie',
}

# Las cadenas que escribe el JavaScript, CON SUS COMILLAS. Con las
# comillas dentro no hay forma de tocar un nombre de variable por
# accidente.
GUION = {
    '"  ·  SIN plugin instalado"': '"  ·  SANS plugin installé"',
    '"  ·  pagina "': '"  ·  page "',
    '"  ·  plugin instalado"': '"  ·  plugin installé"',
    '" &middot; apuntando: <b>"': '" &middot; enregistre : <b>"',
    '" &middot; ultima partida apuntada: "':
        '" &middot; dernière partie enregistrée : "',
    '" <small>(IA)</small>"': '" <small>(IA)</small>"',
    '" acciones"': '" actions"',
    '" con "': '" avec "',
    '" de "': '" sur "',
    '" fila" : " filas"': '" ligne" : " lignes"',
    '" fotos · "': '" photos · "',
    '" partida"': '" partie"',
    '" partidas"': '" parties"',
    '" y grabando"': '" et enregistre"',
    '"(nada todavia)"': '"(rien pour l\'instant)"',
    '", columna <code>"': '", colonne <code>"',
    '".  En la ventana negra:  <code>"':
        '".  Dans la fenêtre noire :  <code>"',
    '"</b> acciones"': '"</b> actions"',
    '"<small>Dale a <b>Dejarlo listo</b>, aqui debajo.</small>"':
        '"<small>Appuie sur <b>Tout préparer</b>, juste en dessous.</small>"',
    '"<small>El mod se mete dentro del juego al arrancarlo, asi que si abriste "':
        '"<small>Le mod entre dans le jeu au démarrage, donc si tu as ouvert "',
    '"<small>Modificar el cliente va contra las condiciones de uso de Catan "':
        '"<small>Modifier le client va contre les conditions d\'utilisation de Catan "',
    '"<tr><td>Ninguna todavia.</td></tr>"':
        '"<tr><td>Aucune pour l\'instant.</td></tr>"',
    '"<tr><td>partida "': '"<tr><td>partie "',
    '">&lsaquo; anteriores</button>"': '">&lsaquo; précédentes</button>"',
    '">siguientes &rsaquo;</button>"': '">suivantes &rsaquo;</button>"',
    '"Ahora mismo llegan "': '"Pour l\'instant il y en a "',
    '"Apagalo al terminar.</small>"': '"Éteins-le quand tu as fini.</small>"',
    '"BepInEx ya esta; falta compilar el <b>plugin</b>. Un boton."':
        '"BepInEx est là ; il reste à compiler le <b>plugin</b>. Un bouton."',
    '"Cuando termines del todo, <b>Parar y apagar el mod</b>."':
        '"Quand tu as complètement fini, <b>Arrêter et éteindre le mod</b>."',
    '"EL MOD ESTA ENCENDIDO"': '"LE MOD EST ALLUMÉ"',
    '"El interruptor esta apagado, pero Catan esta abierto."':
        '"L\'interrupteur est éteint, mais Catan est ouvert."',
    '"El juego arrancara limpio."': '"Le jeu démarrera propre."',
    '"El mod esta apagado y Catan cerrado. "':
        '"Le mod est éteint et Catan est fermé. "',
    '"El mod no esta instalado en el juego."':
        '"Le mod n\'est pas installé dans le jeu."',
    '"En la ventana negra:  "': '"Dans la fenêtre noire :  "',
    '"En la ventana negra: <code>py db/vistas.py --crear</code></p>"':
        '"Dans la fenêtre noire : <code>py db/vistas.py --crear</code></p>"',
    '"Enciende el mod y se pone a grabar. Despues abre Catan y juega. "':
        '"Allume le mod et il se met à enregistrer. Ensuite ouvre Catan et joue. "',
    '"Falta <b>BepInEx</b>, que es lo que deja que el mod se "':
        '"Il manque <b>BepInEx</b>, qui est ce qui permet au mod de se "',
    '"Grabando. Abre Catan y juega. Puedes encadenar <b>varias partidas "':
        '"Enregistrement. Ouvre Catan et joue. Tu peux enchaîner <b>plusieurs parties "',
    '"Guarda una partida primero.</p>"':
        '"Enregistre d\'abord une partie.</p>"',
    '"IA, las vistas de amigos salen vacias a proposito."':
        '"IA, les vues entre amis sortent vides exprès."',
    '"No encuentro Catan Universe. Abre Steam una vez si lo has movido."':
        '"Catan Universe est introuvable. Ouvre Steam une fois si tu l\'as déplacé."',
    '"No encuentro Catan Universe. Abre Steam una vez, o instala "':
        '"Catan Universe est introuvable. Ouvre Steam une fois, ou installe "',
    '"No hay nada que enseñar aqui. Si has elegido una partida contra la "':
        '"Il n\'y a rien à montrer ici. Si tu as choisi une partie contre l\'"',
    '"No se ha podido quitar: "': '"Impossible de la supprimer : "',
    '"Quitar la partida "': '"Supprimer la partie "',
    '"Registro · "': '"Journal · "',
    '"Registro · grabacion"': '"Journal · enregistrement"',
    '"Registro · lo que apunta el mod"':
        '"Journal · ce que le mod enregistre"',
    '"Registro"': '"Journal"',
    '"Todas las partidas"': '"Toutes les parties"',
    '"Todavia no hay ninguna partida guardada."':
        '"Aucune partie enregistrée pour l\'instant."',
    '"Todavia no llega nadie: el que mas lleva es "':
        '"Personne n\'atteint le minimum : le plus haut en a "',
    '"Universe, y esto se carga en todas las partidas mientras este puesto. "':
        '"Universe, et ceci se charge dans toutes les parties tant que c\'est allumé. "',
    '"\\n\\nSe hace una copia de la base antes, pero no hay "':
        '"\\n\\nUne copie de la base est faite avant, mais on ne peut pas "',
    '"\\n\\nSi pone 404, este panel lleva abierto desde antes de que "':
        '"\\n\\nS\'il indique 404, ce panneau est ouvert depuis avant que "',
    '"cargue, y el plugin. Un boton."':
        '"charger, et le plugin aussi. Un bouton."',
    '"de 10 en 10"': '"par 10"',
    '"deshacer."': '"annuler."',
    '"el boton existiera. Cierra la ventana negra y vuelve a abrirla."':
        '"le bouton n\'existe. Ferme la fenêtre noire et rouvre-la."',
    '"el juego, y recarga esta pagina."':
        '"le jeu, puis recharge cette page."',
    '"el panel ha respondido "': '"le panneau a répondu "',
    '"esta partida con el mod encendido, sigue cargado. <b>Para descargarlo hay "':
        '"cette partie avec le mod allumé, il est toujours chargé. <b>Pour le décharger il faut "',
    '"no hay vistas"': '"aucune vue"',
    '"no se ha podido"': '"ça n\'a pas marché"',
    '"preparada"': '"prête"',
    '"que cerrar Catan y volver a abrirlo.</b></small>"':
        '"fermer Catan et le rouvrir.</b></small>"',
    '"seguidas sin tocar nada</b>: cada una se guarda en su carpeta sola. "':
        '"d\'affilée sans rien toucher</b> : chacune est enregistrée dans son propre dossier. "',
    '"sin nombre"': '"sans nom"',
    '"sin preparar"': '"pas prête"',
    '"solo con amigos"': '"entre amis uniquement"',
    '"ver todas"': '"tout voir"',
    '"»"': '"»"',
    '"▲ cierra Catan · Catan Tracker"': '"▲ ferme Catan · Catan Tracker"',
    '"● MOD ENCENDIDO · Catan Tracker"': '"● MOD ALLUMÉ · Catan Tracker"',
    '"☀︎  Claro"': '"☀︎  Clair"',
    '"☽  Oscuro"': '"☽  Sombre"',
    '"✕ sin panel · Catan Tracker"': '"✕ sans panneau · Catan Tracker"',
    '\'" placeholder="como se llama"></td>\'':
        '\'" placeholder="son nom"></td>\'',
    '\'" title="Ordenar por esta columna">\'':
        '\'" title="Trier par cette colonne">\'',
    '\'">guardar</button></td></tr>\'': '\'">enregistrer</button></td></tr>\'',
    '\'">partida \'': '\'">partie \'',
    '\'">quitar</button></td></tr>\'': '\'">supprimer</button></td></tr>\'',
    '\'<div class="cuando">partida \'': '\'<div class="cuando">partie \'',
    '\'<div class="fuente">De «\'': '\'<div class="fuente">De «\'',
    '\'<div class="otras">Si no era eso: \'':
        '\'<div class="otras">Si ce n\\\'était pas ça : \'',
    '\'<optgroup label="Una sola partida">\'':
        '\'<optgroup label="Une seule partie">\'',
    '\'<p class="vacio">Faltan vistas por crear (\'':
        '\'<p class="vacio">Vues encore à créer (\'',
    '\'<p class="vacio">Nada con «\'': '\'<p class="vacio">Rien avec «\'',
    '\'<p class="vacio">No hay ninguna partida guardada.</p>\'':
        '\'<p class="vacio">Aucune partie enregistrée.</p>\'',
    '\'<p class="vacio">Todavia no hay ninguna cuenta. \'':
        '\'<p class="vacio">Aucun compte pour l\\\'instant. \'',
    '\'<p class="vacio">buscando...</p>\'':
        '\'<p class="vacio">recherche...</p>\'',
    '\'<p class="vacio">leyendo...</p>\'':
        '\'<p class="vacio">lecture...</p>\'',
    "'».</p>'": "'».</p>'",
}

# Lo que manda el servidor ya traducido. Los titulares son PLANTILLAS: si
# la traducción se come un `{hueco}` o se inventa otro, en la pantalla sale
# un `{victorias}` en crudo o falta el número.
FRASES = {
    'Aquí sólo entran los monopolios de los que se sabe cuánto se llevaron. Si en esta partida se jugó alguno y no sale, es de antes del 22/8/2026: el mod no leía el reparto todavía. Están en «Los monopolios», con quién lo tiró y qué pidió.':
        "Ici n'entrent que les monopoles dont le butin est connu. Si un monopole a été joué dans cette partie et n'apparaît pas, c'est qu'il date d'avant le 22/8/2026 : le mod ne lisait pas encore le transfert. Ils sont dans « Les monopoles », avec qui l'a joué et ce qu'il a demandé.",
    'Cartas de desarrollo': 'Cartes développement',
    'Comercio': 'Échanges',
    'Con quién se ceba el ladrón':
        "Sur qui s'acharne le voleur, et de la main de qui",
    'Con qué salida le toca a cada uno': 'Quelle place tombe à chacun',
    'Cuántos, por jugador': 'Combien, par joueur',
    'De cada salida, cómo acabó': 'Depuis chaque place, comment ça a fini',
    'De dónde salió cada punto': "D'où venait chaque point",
    'De esta partida no se puede saber. Que alguien USE un puerto se deduce de los comercios y eso está en «Puerto a puerto»; PILLARLO es otra cosa y necesita saber dónde está cada puerto en el tablero. El mod no lo leía bien hasta el 22/8/2026 -- la posición viene en una `EdgePosition` y se estaba leyendo como si fuera otra clase, así que llegaba vacía -- y eso no se puede recuperar sin volver a jugar la partida.':
        "Impossible de le savoir pour cette partie. Qu'une personne UTILISE un port se déduit de ses échanges et c'est dans « Port par port » ; s'ATTRIBUER un port est autre chose et demande de savoir où chaque port se trouve sur le plateau. Le mod ne lisait pas ça correctement avant le 22/8/2026 -- la position arrive dans un `EdgePosition` et était lue comme si c'était une autre classe, donc elle arrivait vide -- et ça ne se récupère pas sans rejouer la partie.",
    'Dónde pone el ladrón cada uno': 'Où chacun envoie le voleur',
    'El ladron: a quien y en que numero':
        'Le voleur : sur qui et sur quel numéro',
    'El ladrón': 'Le voleur',
    'El ladrón, uno a uno': 'Le voleur, un par un',
    'El mazo': 'Le paquet',
    'El monopolio, uno a uno': 'Les monopoles, un par un',
    'El orden de salida': "L'ordre du tour",
    'El ritmo de cada uno': 'Le rythme de chacun',
    'El saldo con cada uno': 'Le solde avec chacun',
    'El tablero y los dados': 'Le plateau et les dés',
    'En mesa de 5 y 6 manda {quien}, con {victorias} de {partidas}.':
        'Aux tables de 5 et 6, {quien} mène, avec {victorias} sur {partidas}.',
    'En mesa de 5 y 6 no ha ganado todavía ninguno de los que llegan al mínimo.':
        "Aux tables de 5 et 6, aucun de ceux qui atteignent le minimum n'a encore gagné.",
    'Jugadores': 'Joueurs',
    'La mejor suerte en una partida': 'La meilleure chance en une partie',
    'La suerte de cada uno': 'La chance de chacun aux dés',
    'Las partidas': 'Les parties',
    'Las tiradas': 'Les jets de dés',
    'Los monopolios': 'Les monopoles',
    'Los números de cada uno': 'Les numéros de chacun',
    'Los números que más tapa el ladrón':
        'Les numéros que le voleur bloque le plus',
    'Los sietes de cada uno': 'Les sept de chacun',
    'Marcador': 'Le tableau des scores',
    'Más ladrones en una partida': 'Le plus de voleurs en une partie',
    'Ninguno todavía. Si en la partida se jugó alguno y aquí no sale, es que la carta no llegó a apuntarse: el recurso sólo se engancha a una jugada del mismo jugador y el mismo turno.':
        "Aucun pour l'instant. Si un monopole a été joué dans la partie et n'apparaît pas ici, la carte n'a jamais été enregistrée : la ressource n'est reliée à une carte jouée que par le même joueur et le même tour.",
    'Partidas': 'Parties',
    'Producción': 'Production',
    'Puerto a puerto': 'Port par port',
    'Puertos': 'Les ports',
    'Puntos y ritmo': 'Score et rythme',
    'Quién compra más cartas de desarrollo':
        'Qui achète le plus de cartes développement',
    'Quién elige mejor las casillas': 'Qui choisit le mieux ses tuiles',
    'Quién gana más': 'Qui gagne le plus',
    'Quién pilló cada puerto': "Qui s'est adjugé chaque port",
    'Quién propone tratos a quién': 'Qui propose des échanges à qui',
    'Quién saca más sietes': 'Qui sort le plus de 7',
    'Quién tiene más suerte': 'Qui a le plus de chance',
    'Quién va más en positivo, y con quién':
        "Qui s'en sort le mieux, et avec qui",
    'Qué se comercia': "Ce qui s'échange",
    'Robos de la mano': 'Les vols dans la main',
    'Trato a trato': 'Échange par échange',
    'a quien se lo puso cada uno y sobre que numero':
        "sur qui chacun l'a posé et sur quel numéro",
    'a qué número lo manda cada uno, cuántas veces, y si por el 7 o con un caballero':
        "vers quel numéro chacun l'envoie, combien de fois, et si c'est par un 7 ou avec un chevalier",
    'a qué números va el ladrón, sumando a todo el mundo':
        'vers quels numéros va le voleur, tout le monde confondu',
    'cada intercambio con los dos lados: quién dio qué y a cambio de qué':
        'chaque échange des deux côtés : qui a donné quoi et contre quoi',
    'cobró {le_toco} veces contra las {le_tocaba} que le tocaban, y con sólo {casillas} casillas. Se sale {se_sale} márgenes de lo normal: el azar por sí solo ya mueve un {margen}%.':
        'a encaissé {le_toco} fois contre les {le_tocaba} qui lui revenaient, et avec seulement {casillas} tuiles. Ça fait {se_sale} écarts hors du normal, et le hasard seul le déplace déjà de {margen} %.',
    'como va mejorando': "comment ça s'améliore",
    'comprobar lo grabado': "vérifier l'enregistrement",
    'cuántas cartas de cada recurso le ha sacado cada uno a cada uno':
        'combien de cartes de chaque ressource chacun a prises à chacun',
    'cuántas veces ha salido primero, segundo, tercero… cada persona':
        'combien de fois chacun est parti premier, deuxième, troisième…',
    'cuántos hizo y cuántos sufrió cada uno (cuántos, no cuáles)':
        'combien chacun en a fait et combien il en a subi (combien, pas lesquelles)',
    'de las casillas donde está puesto, cuántas veces le pagó el tablero contra las que le debía. 100 es la suerte normal':
        'pour les tuiles où il est, combien de fois le plateau a payé contre combien il devait. 100 est la chance normale',
    'de las veces que salió en cada puesto, en cuáles acabó':
        'sur les fois où il est parti de chaque place, où il a fini',
    'de lo que le tocaba: cobró {le_toco} veces contra las {le_tocaba} que le debía el tablero, y 100% es lo normal. Se sale {se_sale} márgenes: hace falta pasar de 2 para que sea suerte y no ruido.':
        'de ce qui lui revenait : a encaissé {le_toco} fois contre les {le_tocaba} que le plateau lui devait, et 100 % est normal. Ça fait {se_sale} écarts : il en faut plus de 2 pour que ce soit de la chance et pas du bruit.',
    'de media por casilla suya, cuando un sitio cualquiera de sus tableros vale {lo_normal}. Con eso le tocaron {le_toco} cobros de los {le_tocaba} que le tocaban.':
        "en moyenne par tuile à lui, quand n'importe quel emplacement de ses plateaux vaut {lo_normal}. Ça lui a valu {le_toco} encaissements sur les {le_tocaba} qui lui revenaient.",
    'de más en los {tratos} tratos entre los dos: se llevó {recibio} y soltó {dio}. Son cartas, no acierto: dar tres por una puede ser el mejor trato de la partida.':
        'de plus sur les {tratos} échanges entre les deux : a pris {recibio} et a lâché {dio}. Ce sont des cartes, pas un jugement : donner trois pour une peut être le meilleur échange de la partie.',
    'de sus tiradas: {sietes} sietes en {tiros} tiros. Lo normal es {porcentaje_normal}%.':
        'de ses jets : {sietes} sept sur {tiros} lancers. Le normal est {porcentaje_normal} %.',
    'dejar el mod listo': 'préparer le mod',
    'edificios, premios y, por resta, las cartas de punto':
        'constructions, récompenses et, par soustraction, les cartes point de victoire',
    'el ciclo entero (convertir, examinar, entrenar)':
        'le cycle entier (convertir, tester, entraîner)',
    'el informe de las partidas': 'le rapport des parties',
    'en mesa de {eran}. Acaba de media en el puesto {puesto_medio}, con {puntos_medios} puntos.':
        'à une table de {eran}. Finit {puesto_medio} en moyenne, avec {puntos_medios} points.',
    'en qué números se puso, cuántas veces salieron y qué sacó':
        "sur quels numéros il s'est installé, combien de fois ils sont sortis et ce qu'il a touché",
    'en qué puesto salió cada uno y en cuál acabó':
        'de quelle place chacun est parti et où il a fini',
    'en qué turno llegó a su primera ciudad, su primera carta...':
        'à quel tour il a eu sa première ville, sa première carte...',
    'entrenar (apartando una partida para medir)':
        'entraîner (en gardant une partie de côté pour mesurer)',
    'guardar las partidas en la base de datos':
        'enregistrer les parties dans la base',
    'los nueve puertos del mapa y quién se quedó cada uno, incluidos los que no pilló nadie':
        "les neuf ports de la carte et qui a fini avec chacun, y compris ceux que personne n'a pris",
    'medir el ladron y los dados contra lo que dice el mod':
        'mesurer le voleur et les dés contre ce que dit le mod',
    'medir el tablero entero, como lo leeria jugando':
        'mesurer le plateau entier, comme il le lirait en jeu',
    'medir la red, foto a foto': 'mesurer le réseau, image par image',
    'mesas de cualquier tamaño': 'tables de toutes tailles',
    'mirar la pantalla': "regarder l'écran",
    'partidas, victorias y puntos medios de cada uno, por tamaño de mesa':
        'parties, victoires et points moyens de chacun, par taille de table',
    'preparar los datos': 'préparer les données',
    'probar la lectura en vivo sobre una partida grabada':
        'essayer la lecture en direct sur une partie enregistrée',
    'pruebas de la red': 'tests du réseau',
    'pruebas de las vistas': 'tests des vues',
    'quién gana cartas con quién y quién las pierde: el saldo de verdad, con TODOS sus tratos dentro, los propusiera quien los propusiera (sin la banca)':
        "qui gagne des cartes sur qui et qui en perd : le vrai solde, avec TOUS ses échanges dedans, quel qu'en soit le proposeur (échanges avec la banque exclus)",
    'quién mueve ficha: sólo los tratos que propuso cada uno, y cómo le salieron ESOS':
        'qui fait le premier pas : seulement les échanges que chacun a proposés, et comment CEUX-LÀ ont tourné pour lui',
    'quién saca más sietes al tirar, contra el 16,7% que toca':
        'qui sort le plus de 7, contre les 16,7 % attendus',
    'quién se lo puso a quién, cuántas veces le tocó y qué le costó':
        "qui l'a posé sur qui, combien de fois il est tombé et ce que ça a coûté",
    'quién tiró cada monopolio y qué recurso pidió':
        'qui a joué chaque monopole et quelle ressource il a demandée',
    'qué le tocó a cada uno de las cartas que compró':
        "ce que chacun a tiré des cartes qu'il a achetées",
    'qué recurso da y cuál recibe cada uno, y con quién':
        'quelle ressource chacun donne et laquelle il reçoit, et avec qui',
    'qué recursos le dio el tablero a cada uno, y de qué anda corto':
        'quelles ressources le plateau a données à chacun, et lesquelles lui manquent',
    'qué salió contra lo que debería haber salido':
        'ce qui est sorti contre ce qui aurait dû sortir',
    'qué salió contra lo que el mazo lleva dentro':
        'ce qui est sorti contre ce que le paquet contient vraiment',
    'qué tal le va a cada puesto de salida, sumando todas las partidas':
        'comment se débrouille chaque place de départ, toutes parties confondues',
    'recursos que no dejó producir, contra los que sí se cobraron':
        "les ressources qu'il a empêché de produire, contre celles qui ont été encaissées quand même",
    'reentrenar con todo (para jugar)':
        'réentraîner sur tout (pour jouer avec)',
    'rehacer las vistas de la base': 'refaire les vues de la base',
    'se lo pusieron encima. En {le_bloquearon} de esas veces salió el número y no cobró: {perdido} cartas que se quedó sin producir. Más {le_robaron} que le robaron de la mano, {en_total} cartas en total.':
        "lui ont été posés dessus. Sur {le_bloquearon} d'entre eux le numéro est sorti et il n'a rien encaissé : {perdido} cartes jamais produites. Plus {le_robaron} prises dans sa main, {en_total} cartes au total.",
    'si a alguien le ponen el ladrón más de lo que le toca, descontando cuánto juega y cuántas casillas tiene':
        "si quelqu'un reçoit le voleur plus que sa part, en tenant compte de combien il joue et de combien de tuiles il tient",
    'solo con amigos (sin la IA)': 'seulement entre amis (sans IA)',
    'solo las partidas contra la IA': "seulement les parties contre l'IA",
    'solo mesas de 4': 'seulement les tables de 4',
    'solo mesas de 5 y 6': 'seulement les tables de 5 et 6',
    'todas, la IA incluida': 'toutes, IA comprise',
    'una fila por jugador y partida, con el nombre ya resuelto':
        'une ligne par joueur et par partie, avec le nom déjà résolu',
    'una fila por jugador: cuántos puertos se le pueden contar y cuáles':
        'une ligne par joueur : combien de ports peuvent lui être comptés, et lesquels',
    'una fila por puerto usado: cuál, cuántas veces y entre qué turnos':
        'une ligne par port utilisé : lequel, combien de fois et entre quels tours',
    'una por partida, con quién ganó, cuántas casillas tenía el tablero y si eran todos personas':
        'une ligne par partie, avec qui a gagné, combien de tuiles avait le plateau et si tout le monde était humain',
    '{compradas} cartas en {partidas} partidas, {caballero} de ellas caballeros.':
        '{compradas} cartes en {partidas} parties, dont {caballero} chevaliers.',
    '{con_7} veces obligado por un 7 y {con_caballero} eligiéndolo con un caballero. En {le_bloqueo} de esas veces salió el número y {a_quien} no cobró: son {le_costo} cartas que se quedó sin producir. Y aparte le quitó {le_robo} cartas de la mano.':
        "{con_7} fois forcé par un 7 et {con_caballero} par choix avec un chevalier. Sur {le_bloqueo} d'entre elles le numéro est sorti et {a_quien} n'a rien encaissé : {le_costo} cartes jamais produites. Et en plus il lui a pris {le_robo} cartes dans la main.",
    '{neto} cartas': '{neto} cartes',
    '{por_casilla} puntitos': '{por_casilla} pastilles',
    '{por_partida} por partida': '{por_partida} par partie',
    '{porcentaje}%': '{porcentaje} %',
    '{quien} a {a_quien}': '{quien} sur {a_quien}',
    '{quien} con {con_quien}': '{quien} avec {con_quien}',
    '{se_lo_pusieron} ladrones': '{se_lo_pusieron} voleurs',
    '{se_lo_puso} veces': '{se_lo_puso} fois',
    '{suerte}%': '{suerte} %',
    '{victorias} de {partidas}': '{victorias} sur {partidas}',
    '¿A quién se ceba el ladrón?': "Sur qui s'acharne le voleur ?",
    '¿Importa salir primero?': 'Est-ce que partir premier compte ?',
}

# La etiqueta que se pinta encima de cada columna. La clave es el nombre
# en SQL y no se traduce: con él se ordena, se filtra y se busca.
# Las mismas palabras que usa `catalogFR.py`, a propósito: lo que se ve
# arriba de la columna es lo que se busca en la referencia.
COLUMNAS = {
    'a': 'à',
    'a_puntos': 'points visés',
    'a_quien': 'à qui',
    'a_si_mismo': 'à soi-même',
    'arcilla': 'argile',
    'caballero': 'chevalier',
    'cada_casilla': 'cartes par tuile',
    'carretera_larga': 'route la plus longue',
    'carreteras': 'construction de routes',
    'carta': 'carte',
    'cartas': 'cartes',
    'cartas_de_punto': 'cartes point de victoire',
    'casillas': 'tuiles',
    'casillas_tablero': 'tuiles du plateau',
    'cereales': 'blé',
    'ciudades': 'villes',
    'color': 'couleur',
    'compradas': 'achetées',
    'con_7': 'avec un 7',
    'con_amigos': 'entre amis',
    'con_caballero': 'avec chevalier',
    'con_quien': 'avec qui',
    'de_mas': 'surplus',
    'de_quien': 'de qui',
    'deberia_salir': 'jets attendus',
    'deberian_salir': 'tirages attendus',
    'del_reparto': 'de la mise en place',
    'dia': 'jour',
    'dio': 'a donné',
    'duro_hasta': "a duré jusqu'à",
    'edificios': 'constructions',
    'en_total': 'total voleur',
    'eran': 'taille de table',
    'es_ia': 'est un bot',
    'esperado': 'attendu',
    'game_id': 'id partie',
    'gano': 'gagnant',
    'genericos': 'ports génériques',
    'hora': 'heure',
    'ias': 'bots',
    'invencion': 'invention',
    'jugadores': 'nombre de joueurs',
    'lana': 'laine',
    'le_bloquearon': 'fois bloqué',
    'le_bloqueo': 'les a bloqués',
    'le_costo': 'leur a coûté',
    'le_quito_el_ladron': 'perdu au voleur',
    'le_robaron': 'volé chez eux',
    'le_robo': 'leur a volé',
    'le_tocaba': 'attendu',
    'le_tocaban': 'attendus',
    'le_toco': 'reçu',
    'les_saco': 'total pris',
    'lo_normal': 'référence',
    'madera': 'bois',
    'margen': 'marge',
    'mayor_ejercito': 'armée la plus puissante',
    'mineral': 'minerai',
    'minutos': 'minutes',
    'monopolio': 'monopole',
    'monopolios': 'monopoles',
    'movimientos': 'déplacements',
    'neto': 'net',
    'neto_proponiendo': 'net en proposant',
    'numero': 'numéro',
    'partida': 'partie',
    'partidas': 'parties jouées',
    'partidas_juntos': 'parties ensemble',
    'pegas': 'problèmes',
    'perdido': 'cartes perdues',
    'personas': 'personnes',
    'pidio': 'demandé',
    'pieza': 'construction',
    'player_id': 'id joueur',
    'poblados': 'colonies',
    'por_casilla': 'pastilles par tuile',
    'por_partida': 'par partie',
    'porcentaje': 'pourcentage',
    'porcentaje_normal': 'pourcentage attendu',
    'primer_caballero': 'premier chevalier',
    'primer_poblado': 'première colonie',
    'primer_uso': 'première utilisation',
    'primera_carta': 'première carte dév',
    'primera_ciudad': 'première ville',
    'producido': 'produit',
    'puerto': 'port',
    'puerto_arcilla': 'port argile',
    'puerto_cereales': 'port blé',
    'puerto_lana': 'port laine',
    'puerto_madera': 'port bois',
    'puerto_mineral': 'port minerai',
    'puesto': 'rang',
    'puesto_medio': 'rang moyen',
    'puestos_ganados': 'rangs gagnés',
    'puntitos': 'pastilles',
    'punto_victoria': 'point de victoire',
    'puntos': 'points',
    'puntos_medios': 'points moyens',
    'quedo_1': 'fini 1er',
    'quedo_2': 'fini 2e',
    'quedo_3': 'fini 3e',
    'quedo_4': 'fini 4e',
    'quedo_5': 'fini 5e',
    'quedo_6': 'fini 6e',
    'quien': 'qui',
    'recibio': 'a reçu',
    'recurso': 'ressource',
    'robo_el': 'cartes volées',
    'salida': 'ordre de départ',
    'salida_media': 'départ moyen',
    'salieron': 'tirées',
    'salio_1': 'parti 1er',
    'salio_2': 'parti 2e',
    'salio_3': 'parti 3e',
    'salio_4': 'parti 4e',
    'salio_5': 'parti 5e',
    'salio_6': 'parti 6e',
    'salio_ultimo': 'parti dernier',
    'se_ceban': 'acharnement',
    'se_jugaba_a': 'partie en',
    'se_lo_pusieron': 'voleur posé sur eux',
    'se_lo_puso': "l'a posé sur eux",
    'se_sale': 'écarts-types',
    'sietes': '7 obtenus',
    'sin_saber': 'inconnues',
    'su_mejor': 'meilleur score',
    'suerte': 'chance',
    'tercer_poblado': 'troisième colonie',
    'tiradas': 'jets',
    'tiradas_contadas': 'jets comptés',
    'tiros': 'leurs jets',
    'total': 'total',
    'tratos': 'échanges',
    'tratos_entre_los_dos': 'échanges entre eux',
    'turno': 'tour',
    'turnos': 'tours',
    'ultimo_uso': 'dernière utilisation',
    'veces': 'fois',
    'veces_normales': 'fois attendues',
    'veces_salio': 'fois sorti',
    'victorias': 'victoires',
    'y_recibio': 'et a reçu',
}



# LA CAJA DE PREGUNTAS. Esto no traduce la pregunta: la reescribe con las
# palabras castellanas contra las que la caja empareja. El emparejador no
# entiende ningun idioma -- parte la pregunta en palabras y las compara con
# los nombres, titulos y columnas de las vistas, que estan escritos en
# castellano -- asi que lo unico que hace falta es que las palabras lleguen
# en castellano.
#
# Medido con el mismo examen de 68 preguntas que el castellano, traducido:
# acierta 39 de 68 en frances. El castellano acierta 40. O sea que no es peor en frances
# que en su propio idioma, que es el liston que importa: la caja falla lo que
# falla, y lo que no puede pasar es que falle MAS por el idioma.

# Los giros van ANTES de partir en palabras, porque solo quieren decir eso
# juntos. Se aplican de mas largo a mas corto, que es lo que hace que
# `combien de fois` se aplique antes que `combien de` no se coma la mitad del otro.
GIROS = (
    ("qu'est-ce qui", ''),
    ('qu est-ce qui', ''),
    ('est-ce que', ''),
    ('combien de fois', 'cuantas veces'),
    ('combien de temps', 'cuanto minuto'),
    ('combien de', 'cuantos'),
    ('combien d', 'cuantos '),
    ('a qui', 'a quien'),
    ('sur qui', 'a quien'),
    ('de qui', 'a quien'),
    ('avec qui', 'con quien'),
    ('route la plus longue', 'carretera larga'),
    ('armee la plus puissante', 'mayor ejercito'),
    ('construction de routes', 'carretera'),
    ('carte developpement', 'desarrollo carta'),
    ('cartes developpement', 'desarrollo carta'),
    ('point de victoire', 'punto victoria'),
    ('points de victoire', 'punto victoria'),
    ('ordre de depart', 'salida'),
    ('taille de table', 'mesa'),
    ('que ce qui lui revient', 'de lo que toca'),
    ('comme ils devraient', 'deberia'),
    ('le plus', 'mas'),
    ('le moins', 'menos'),
    ('le mieux', 'mejor'),
    ('les des', 'tirada'),
    ('aux des', 'tirada'),
    ('vaut le coup', 'compensa'),
)

# Y palabra a palabra. Las vacias se borran: no dicen nada de la pregunta y
# ensucian la bolsa con la que se puntua cada vista.
PREGUNTAS = {
    'achete': 'compro', 'acheter': 'compro', 'adjuge': 'pillo',
    'amis': 'amigo', 'argile': 'arcilla', 'armee': 'ejercito',
    'arrive': 'llego', 'attendu': 'esperado', 'au': '', 'aux': '',
    'avec': 'con', 'banque': 'banca', 'ble': 'cereales', 'bloque': 'bloqueo',
    'bloquer': 'bloqueo', 'bloques': 'bloqueo', 'bois': 'madera', 'bot': 'ias',
    'bots': 'ias', 'carte': 'carta', 'cartes': 'carta', 'cause': '', 'ce': '',
    'ces': '', 'cette': '', 'chacun': 'cada', 'chance': 'suerte',
    'chaque': 'cada', 'chevalier': 'caballero', 'chevaliers': 'caballero',
    'choisit': 'elige', 'cinquieme': 'quinto', 'classe': 'colocado',
    'colonie': 'poblado', 'colonies': 'poblado', 'combien': 'cuanto',
    'compensa': 'compensa', 'construction': 'edificio',
    'constructions': 'edificio', 'contre': 'contra', 'couleur': 'color',
    'cout': 'cuesta', 'coute': 'cuesta', 'd': '', 'dans': '', 'de': '',
    'demande': 'pidio', 'demandent': 'pidio', 'depart': 'salida',
    'dernier': 'ultimo', 'des': '', 'deuxieme': 'segundo',
    'developpement': 'desarrollo', 'donne': 'dio', 'donnees': 'dio',
    'donner': 'dio', 'du': '', 'dure': 'minuto', 'duree': 'minuto',
    'durent': 'minuto', 'echange': 'trato', 'echanger': 'trato',
    'echanges': 'trato', 'elle': '', 'elles': '', 'en': '', 'entre': 'entre',
    'envoie': 'manda', 'envoyer': 'manda', 'est': '', 'et': '',
    'eu': 'recibio', 'faire': '', 'fait': '', 'fini': 'acabo',
    'finir': 'acabo', 'finit': 'acabo', 'fois': 'veces', 'froment': 'cereales',
    'gagnant': 'victoria', 'gagne': 'victoria', 'gagner': 'victoria',
    'generique': 'generico', 'gens': 'persona', 'heure': 'hora',
    'humain': 'persona', 'humains': 'persona', 'ia': 'ias', 'il': '',
    'ils': '', 'installe': 'poblado', 'invention': 'invencion',
    'jet': 'tirada', 'jets': 'tirada', 'joue': 'juega', 'jouees': 'juega',
    'jouent': 'juega', 'jouer': 'juega', 'joueur': 'jugador',
    'joueurs': 'jugador', 'jour': 'dia', 'joué': 'juega', 'l': '', 'la': '',
    'laine': 'lana', 'lance': 'tirada', 'lancer': 'tirada', 'le': '',
    'les': '', 'leur': '', 'leurs': '', 'ma': 'mi', 'machine': 'ias',
    'main': 'mano', 'manque': 'corto', 'marge': 'margen', 'me': 'me',
    'meilleur': 'mejor', 'mes': 'mi', 'mieux': 'mejor', 'minerai': 'mineral',
    'minute': 'minuto', 'minutes': 'minuto', 'moi': 'me', 'moins': 'menos',
    'mon': 'mi', 'monopole': 'monopolio', 'monopoles': 'monopolio',
    'mouton': 'lana', 'moyenne': 'medio', 'ne': '', 'net': 'neto',
    'nom': 'nombre', 'normal': 'normal', 'nous': 'nos', 'numero': 'numero',
    'numeros': 'numero', 'on': '', 'ont': '', 'ordinateur': 'ias',
    'ou': 'donde', 'paquet': 'mazo', 'par': '', 'part': 'salida',
    'parti': 'salida', 'partie': 'partida', 'parties': 'partida', 'partir': '',
    'pas': '', 'pastilles': 'puntitos', 'perd': 'perdido', 'perdre': 'perdido',
    'perdu': 'perdido', 'perdues': 'perdido', 'personne': 'nadie',
    'personnes': 'persona', 'piece': 'pieza', 'pieces': 'pieza',
    'place': 'puesto', 'plateau': 'tablero', 'plateaux': 'tablero',
    'plus': 'mas', 'point': 'punto', 'points': 'punto', 'port': 'puerto',
    'ports': 'puerto', 'pose': 'pone', 'poser': 'pone', 'pour': '',
    'pourcentage': 'porcentaje', 'premier': 'primero', 'premiere': 'primero',
    'prend': 'saca', 'prendre': 'saca', 'pris': 'pillo',
    'production': 'produccion', 'produit': 'produccion',
    'produite': 'produccion', 'proportion': 'proporcion', 'propose': 'propone',
    'proposer': 'propone', 'qu': '', 'quand': 'cuando', 'quatrieme': 'cuarto',
    'que': '', 'quel': 'cual', 'quelle': 'cual', 'quelles': 'cual',
    'quelqu': 'alguien', 'quelquun': 'alguien', 'quels': 'cual',
    'qui': 'quien', 'rang': 'colocado', 'recevoir': 'recibio',
    'recoit': 'recibio', 'recu': 'recibio', 'ressource': 'recurso',
    'ressources': 'recurso', 'revient': 'toca', 'route': 'carretera',
    'routes': 'carretera', 'rythme': 'ritmo', 'sa': '', 'se': '',
    'second': 'segundo', 'sept': 'siete', 'ses': '', 'sixieme': 'sexto',
    'solde': 'saldo', 'son': '', 'sont': '', 'chiffre': 'numero', 'chiffres': 'numero', 'sort': 'salio',
    'vient': 'salio', 'viennent': 'salio',
    'sortent': 'salio', 'sorti': 'salio', 'sortir': 'salio',
    'souvent': 'veces', 'subi': 'sufrio', 't': '', 'table': 'mesa',
    'tables': 'mesa', 'tire': 'salieron', 'tires': 'salieron',
    'tombent': 'toca', 'total': 'total', 'toujours': '', 'tour': 'turno',
    'tours': 'turno', 'tous': 'todo', 'toutes': 'todo', 'troisieme': 'tercero',
    'truque': '', 'truques': '', 'tuile': 'casilla', 'tuiles': 'casilla',
    'un': '', 'une': '', 'utilise': 'uso', 'utiliser': 'uso', 'veut': 'mania',
    'victoire': 'victoria', 'ville': 'ciudad', 'villes': 'ciudad',
    'vole': 'robo', 'volees': 'robo', 'voler': 'robo', 'voles': 'robo',
    'voleur': 'ladron', 'voleurs': 'ladron', 'vols': 'robo', 'y': '',
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
    '  (juntando las filas de «%s»)': '  (en regroupant les lignes de « %s »)',
    '  (sumando %d filas)': '  (en additionnant %d lignes)',
    '  Aunque con estos datos no se sale nadie del margen: la diferencia cabe en el error.':
        "  Même si avec ces données personne ne sort de la marge : la différence tient dans l'erreur.",
    '  Repartido: ': '  Réparti : ',
    '  Sobre todo %s (%d de %d).': '  Surtout %s (%d sur %d).',
    '%d, en «%s».': '%d, dans « %s ».',
    '%s a %s: %s de %s.': '%s à %s : %s sur %s.',
    '%s a %s: ninguna vez, en «%s».': '%s à %s : aucune fois, dans « %s ».',
    '%s con %s %s: %s, con %s.': '%s avec %s %s : %s, avec %s.',
    '%s no sale en «%s».': "%s n'apparaît pas dans « %s ».",
    '%s, %s %s %s: %s, con %s de %s.': '%s, %s %s %s : %s, avec %s sur %s.',
    '%s, %s: %s': '%s, %s : %s',
    '%s, %s: %s  (una por partida)': '%s, %s : %s  (une par partie)',
    '%s, en el %s (%s: %s).': '%s, sur le %s (%s : %s).',
    '%s: %d en «%s».': '%s : %d dans « %s ».',
    '%s: %s de %s.': '%s : %s sur %s.',
    'El que %s %s: %s, con %s (%s de %s).':
        'Celui qui a le %s de %s : %s, avec %s (%s sur %s).',
    'El que %s %s: %s, con %s.': 'Celui qui a le %s de %s : %s, avec %s.',
    'En el %s no hay %s.': "Sur le %s il n'y a pas de %s.",
    'En el %s no hay nada en «%s».': "Sur le %s il n'y a rien dans « %s ».",
    'En el %s no hay ninguno: %s es 0.':
        "Sur le %s il n'y en a aucun : %s vaut 0.",
    'En el %s: %s %s.': 'Sur le %s : %s %s.',
    'En el %s: %s.': 'Sur le %s : %s.',
    'En total, %s de %s.': 'Au total, %s sur %s.',
    'Eso no lo tengo en una columna, pero lo que preguntas esta en «%s», aqui debajo.':
        "Je n'ai pas ça dans une colonne, mais ce que tu demandes est dans « %s », juste en dessous.",
    'Eso no lo tengo guardado en ninguna vista. Prueba con otra palabra: caballeros, monopolios, puertos, robos, suerte, tiradas, puntos, ladron, comercio...':
        "Je n'ai pas ça enregistré dans une vue. Essaie un autre mot : chevaliers, monopoles, ports, vols, chance, jets, points, voleur, échanges...",
    'Eso no sale en un numero. Lo tienes en «%s», aqui debajo.':
        "Ça ne sort pas en un chiffre. Tu l'as dans « %s », juste en dessous.",
    'Lo de %s con %s esta aqui debajo.':
        'Ce que %s a fait avec %s est juste en dessous.',
    'Lo del %s esta aqui debajo.': 'Le %s est juste en dessous.',
    'Lo que preguntas esta en «%s», columna «%s».':
        'Ce que tu demandes est dans « %s », colonne « %s ».',
    'Lo tienes en «%s», aqui debajo.':
        "Tu l'as dans « %s », juste en dessous.",
    'No se de que me hablas. Nombra algo: caballeros, monopolios, puertos, robos, suerte, tiradas, puntos, ladron...':
        'Je ne vois pas de quoi tu parles. Nomme quelque chose : chevaliers, monopoles, ports, vols, chance, jets, points, voleur...',
    'Preguntame algo.': 'Demande-moi quelque chose.',
    'Todavia no hay base de datos.': "Il n'y a pas encore de base de données.",
    'a': 'à',
    'con': 'avec',
    'mas': 'plus',
    'menos': 'moins',
    'no se ha podido leer la base: %s': 'impossible de lire la base : %s',
    '«%s» me vale para %d personas (%s). Dime cual, o ponles nombre en el paso 2: mientras se llamen todos «jugador_algo» no los puedo distinguir.':
        "« %s » correspond à %d personnes (%s). Dis-moi laquelle, ou donne-leur un nom à l'étape 2 : tant qu'elles s'appellent toutes « jugador_quelque_chose » je ne peux pas les distinguer.",
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
        "         L'enregistrement est entier et sauvegardé : quand",
    '         Le pasaba al tablero de 5-6 jugadores: ahí el juego deja':
        '         Ça arrivait au plateau 5-6 joueurs : là le jeu laisse',
    '         Sin su posición no hay bloqueos Y LA PRODUCCIÓN SALE DE MÁS:':
        "         Sans sa position il n'y a pas de blocages ET LA PRODUCTION SORT TROP HAUTE :",
    '         `GamePiecesRobber` vacío y guarda al ladrón en':
        '         `GamePiecesRobber` vide et garde le voleur dans',
    '         `GamePiecesRobbers[0]`. Ya arreglado -- el mod':
        '         `GamePiecesRobbers[0]`. Déjà corrigé : le mod',
    '         aprenda estas acciones, `--rehacer` mete la partida sin':
        "         l'importateur connaîtra ces actions, `--rehacer` remet la",
    '         en el .jsonl, que trae los nombres candidatos.':
        '         dans le .jsonl, qui porte les noms candidats.',
    '         juego ha vuelto a moverlo de sitio: mira `ladron_donde_buscar`':
        "         jeu l'a encore déplacé : regarde `ladron_donde_buscar`",
    '         jugando ahora mismo. Si era lo segundo, cuando acabe:':
        "         soit elle se joue en ce moment. Si c'est le second cas :",
    '         perder nada.': '         partie sans rien perdre.',
    '         propio juego. Si esto sale en una grabación NUEVA, el':
        '         du jeu lui-même. Si ça sort dans un enregistrement NEUF, le',
    '         py mod_verdad/importar.py --rehacer':
        '         py mod_verdad/importar.py --rehacer',
    '         se cuenta como si el ladrón no estuviera en el tablero.':
        "         c'est compté comme si le voleur n'était pas sur le plateau.",
    '         usa ya `BoardQuery.GetRobberTile`, que es el accesor del':
        "         utilise maintenant `BoardQuery.GetRobberTile`, l'accesseur",
    '        panel, o aqui:  py mod_verdad/importar.py --llamar %s Pedro':
        '        panneau, ou ici :  py mod_verdad/importar.py --llamar %s Pedro',
    '        ponle el suyo con el boton «Ponerle nombre a alguien» del':
        "        donne-lui le sien avec le bouton « Nommer quelqu'un » du",
    '       Hazlo a mano: py db/vistas.py --crear':
        '       Fais-le à la main : py db/vistas.py --crear',
    '     %s': '     %s',
    '     [!] %d acciones que no entiendo, de %d tipos distintos%s.':
        '     [!] %d actions que je ne comprends pas, de %d types différents%s.',
    '     [!] EL LADRON NO SE HA PODIDO LEER en %d movimientos.':
        "     [!] LE VOLEUR N'A PAS PU ÊTRE LU dans %d déplacements.",
    '     [!] esta partida no tiene final: o se abandonó o se está':
        "     [!] cette partie n'a pas de fin : soit elle a été abandonnée,",
    "    [!] identificador nuevo sin nombre: %s -> se ha llamado '%s'":
        "    [!] nouvel identifiant sans nom : %s -> il a été appelé '%s'",
    '   %s': '   %s',
    '   ... jugar ...': '   ... jouer ...',
    '   .\\mod_verdad\\interruptor.ps1 off':
        '   .\\mod_verdad\\interruptor.ps1 off',
    '   .\\mod_verdad\\interruptor.ps1 on        y DESPUES abrir Catan':
        '   .\\mod_verdad\\interruptor.ps1 on        et ENSUITE ouvrir Catan',
    '   C:\\Windows\\Microsoft.NET\\Framework\\v4.0.30319\\csc.exe':
        '   C:\\Windows\\Microsoft.NET\\Framework\\v4.0.30319\\csc.exe',
    '   NO LO ENCUENTRO. Se le pregunta a Steam, asi que:':
        "   INTROUVABLE. C'est à Steam qu'on le demande, donc :",
    '   No ha compilado. Hace falta el csc que trae Windows, en':
        '   Pas compilé. Il faut le csc fourni avec Windows, dans',
    '   abre Steam una vez, o instala el juego, y vuelve a pasar esto.':
        '   ouvre Steam une fois, ou installe le jeu, et relance ceci.',
    '   bajando %s ...': '   téléchargement de %s ...',
    '   es de %s': '   il est en %s',
    '   faltan: %s': '   il manque : %s',
    '   py mod_verdad\\importar.py': '   py mod_verdad\\importar.py',
    '   py panel.py                        y el boton «Encender el mod»':
        '   py panel.py                        et le bouton « Allumer le mod »',
    '   ya esta puesto, no se toca': "   déjà en place, on n'y touche pas",
    "  %s  (ahora '%s')": "  %s  (maintenant '%s')",
    '  -  %-28s %s': '  -  %-28s %s',
    '  OK %-28s partida %d: %s': '  OK %-28s partie %d : %s',
    '  py mod_verdad/importar.py --llamar <identificador> <nombre>':
        '  py mod_verdad/importar.py --llamar <identifiant> <nom>',
    '  py mod_verdad/importar.py --llamar <identificador> Pedro':
        '  py mod_verdad/importar.py --llamar <identifiant> Pedro',
    '%-40s %-16s %d%s': '%-40s %-16s %d%s',
    '%-40s %-16s %s': '%-40s %-16s %s',
    '%d eventos -> %s': '%d événements -> %s',
    '%d partidas importadas.': '%d parties importées.',
    "%s ahora se llama '%s' (antes '%s'); %d partidas actualizadas.":
        "%s s'appelle maintenant '%s' (avant '%s') ; %d parties mises à jour.",
    '1. Catan Universe': '1. Catan Universe',
    '2. BepInEx          %s': '2. BepInEx          %s',
    '2. Dependencias de Python': '2. Dépendances Python',
    '3. BepInEx %s': '3. BepInEx %s',
    '3. el plugin        %s': '3. le plugin        %s',
    '32 bits': '32 bits',
    '4. El plugin': '4. Le plugin',
    '64 bits': '64 bits',
    'Aviso: no se han podido rehacer las vistas (%s).':
        'Attention : impossible de refaire les vues (%s).',
    'Catan Universe no lo permiten. Instalarlo y encenderlo son dos':
        "de Catan Universe ne le permettent pas. L'installer et l'allumer",
    'Cuando quieras:': 'Quand tu veux :',
    'Dejar el mod listo': 'Préparer le mod',
    'El mod modifica el cliente del juego, y las condiciones de uso de':
        "Le mod modifie le client du jeu, et les conditions d'utilisation",
    'FALTA': 'MANQUE',
    'Hay %d persona(s) sin nombre de verdad:':
        'Il y a %d personne(s) sans vrai nom :',
    'Listo, y APAGADO.': 'Prêt, et ÉTEINT.',
    'Nada tocado (--ver). Pasa esto sin --ver para dejarlo listo.':
        'Rien touché (--ver). Relance ceci sans --ver pour tout préparer.',
    'No conozco el identificador %s. Míralos con --quien.':
        "Je ne connais pas l'identifiant %s. Liste-les avec --quien.",
    "No encuentro '%s'. Las que hay:":
        "Je ne trouve pas '%s'. Voici celles qu'il y a :",
    'No hay ficheros del mod en %s': "Il n'y a aucun fichier du mod dans %s",
    'Para ponerle nombre a alguien:': "Pour donner un nom à quelqu'un :",
    'Todavía no hay ningún identificador. Importa una partida primero.':
        "Il n'y a encore aucun identifiant. Importe une partie d'abord.",
    'Ya se llamaba así.': "Il s'appelait déjà comme ça.",
    'apartado del README antes de encenderlo.':
        "Lis la section du README avant de l'allumer.",
    'copia actualizada': 'copie mise à jour',
    'copia guardada': 'copie enregistrée',
    'decisiones distintas, y esto solo ha tomado la primera. Lee el':
        "sont deux décisions différentes, et ceci n'a pris que la première.",
    'el paquete no trae winhttp.dll; no se toca nada':
        "le paquet n'a pas de winhttp.dll ; rien touché",
    'identificador de la cuenta': 'identifiant du compte',
    'ninguna: esto va con la biblioteca estandar':
        'aucune : ça tourne avec la bibliothèque standard',
    'nombre': 'nom',
    'o a mano:': 'ou à la main :',
    'partidas': 'parties',
    'puesto en %s, y APAGADO': 'installé dans %s, et ÉTEINT',
    'ya esta': 'déjà là',
    'ya estan': 'déjà là',
    '¿Has jugado alguna partida con el mod encendido?':
        'As-tu joué une partie avec le mod allumé ?',
}


# Qué quiere decir cada columna y qué es una fila. NO está aquí: vive en
# `catalogFR.py`, al lado, y está escrito ENTERO en francés -- los nombres de
# vista y de columna incluidos. Quien lo abre ya está leyendo en francés; no
# se le pone `del_reparto` delante para que lo adivine.
#
# Aquí se traduce de vuelta, porque la base de datos sí habla en castellano:
# `VISTAS` casa cada vista con su nombre francés, y con eso las fichas se
# vuelven a guardar bajo la clave con la que el resto del programa pregunta.
from . import catalogFR                                      # noqa: E402
import db.columnas as _es                                    # noqa: E402

VISTAS = {
    "partidas": "parties",
    "jugadores": "joueurs",
    "amigos_marcador": "amis_tableau_des_scores",
    "amigos_puntos": "amis_points",
    "amigos_ritmo": "amis_rythme",
    "amigos_salida": "amis_depart",
    "amigos_por_salida": "amis_par_depart",
    "amigos_salida_de_cada_uno": "amis_depart_de_chacun",
    "amigos_salida_como_acabo": "amis_depart_comment_fini",
    "amigos_desarrollo": "amis_developpement",
    "amigos_mazo": "amis_paquet",
    "amigos_monopolios": "amis_monopoles",
    "amigos_monopolios_a_quien": "amis_monopoles_a_qui",
    "amigos_ladron": "amis_voleur",
    "amigos_ladron_proporcion": "amis_voleur_proportion",
    "amigos_ladron_a_quien": "amis_voleur_a_qui",
    "amigos_ladron_a_quien_numero": "amis_voleur_a_qui_numero",
    "amigos_ladron_numeros": "amis_voleur_numeros",
    "amigos_ladron_donde": "amis_voleur_ou",
    "amigos_robos": "amis_vols",
    "amigos_comercio": "amis_echanges",
    "amigos_saldo": "amis_solde",
    "amigos_tratos": "amis_marches",
    "amigos_comercio_material": "amis_echanges_ressource",
    "amigos_puertos": "amis_ports",
    "amigos_cuantos_puertos": "amis_combien_de_ports",
    "amigos_puertos_pillados": "amis_ports_pris",
    "amigos_produccion": "amis_production",
    "amigos_numeros": "amis_numeros",
    "amigos_sietes": "amis_sept",
    "amigos_tiradas": "amis_jets",
    "amigos_suerte": "amis_chance",
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
            "%s: la base tiene %d columnas y catalogFR.py explica %d. "
            "Sobra o falta una ficha, y hasta que no cuadren no se sabe "
            "cuál lleva cada texto." % (donde, len(aqui), len(alli)))
    return dict(zip(aqui, alli.values()))


COMUNES = _casar(_es.COMUNES, catalogFR.COMMUNES, "las comunes")
POR_VISTA = {_v: _casar(_es.POR_VISTA[_v], catalogFR.PAR_VUE[_en], _v)
             for _v, _en in VISTAS.items()}

# `fila` y `para` son los nombres que usa el programa; en el fichero francés
# se llaman `ligne` y `pour`, que es como los lee quien va a leerlos.
FILA_ES = {_v: {"fila": catalogFR.LA_LIGNE[_en]["ligne"],
                "para": catalogFR.LA_LIGNE[_en]["pour"]}
           for _v, _en in VISTAS.items() if _en in catalogFR.LA_LIGNE}

