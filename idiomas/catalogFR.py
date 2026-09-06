# -*- coding: utf-8 -*-
"""Ce que veut dire chaque colonne de chaque vue. Le seul endroit où
c'est dit.

    py db/catalogo.py            écrit le catalogue avec tout ça dedans
    py db/catalogo.py --faltan   quelles colonnes ne sont pas encore
                                 expliquées

POURQUOI C'EST DANS UN FICHIER .py ET PAS DANS LE MARKDOWN. Dès que deux
fichiers expliquent les mêmes colonnes, tôt ou tard ils disent des
choses différentes. C'est exactement le bug qui a été corrigé avec
`le_costo`, qui voulait dire deux choses différentes dans deux vues. Ici
le texte existe une seule fois, le catalogue est généré à partir de là,
et un test vérifie que le fichier généré est à jour.

Et c'est comme ça que la machine peut le vérifier : `db/pruebas.py`
exige que chaque colonne que la base renvoie soit expliquée ici, et que
rien de ce qui est expliqué ici n'ait disparu. Un fichier `.md` ne peut
pas faire ça.

TOUT EST EN FRANÇAIS, y compris les noms de vue et de colonne. Qui ouvre
ce fichier lit déjà tout en français : on ne va pas lui mettre
`del_reparto` devant pour qu'il devine. Les mêmes mots que les en-têtes
du panneau, exprès : ce qui se voit au-dessus de la colonne est ce qui
se cherche ici.

Trois dictionnaires, les mêmes trois que dans la version espagnole :

  COMMUNES   les colonnes qui veulent dire la même chose dans toutes les
             vues, expliquées une seule fois
  PAR_VUE    les colonnes qui veulent dire quelque chose de particulier
             dans une vue, ou qui n'existent que là
  LA_LIGNE   ce qu'est une ligne dans chaque table, et à quoi elle sert
"""

# Les colonnes qui apparaissent dans plusieurs vues et veulent dire la
# même chose partout. Expliquées une seule fois ici pour ne pas être
# expliquées deux fois différemment.
COMMUNES = {
    "qui"                : "la personne, avec son nom déjà résolu. C'est la "
                           "même personne d'une partie à l'autre même si elle "
                           "change de couleur ou de place",
    "à_qui"              : "l'autre personne de la paire : celle qui reçoit "
                           "ce dont parle la ligne",
    "avec_qui"           : "l'autre personne de la paire. `la banque` n'est "
                           "pas une personne : c'est un échange avec la "
                           "banque ou par un port",
    "partie"             : "le numéro de la partie",
    "id_partie"          : "le numéro de la partie",
    "id_joueur"          : "le numéro interne de cette personne **dans cette "
                           "partie**. Ce n'est pas la personne : la même "
                           "personne en a un différent dans chaque partie",
    "jour"               : "le jour où elle a été jouée",
    "heure"              : "l'heure à laquelle elle a commencé",
    "tour"               : "à quel tour c'est arrivé. Le tour **0** est la "
                           "mise en place",
    "rang"               : "à quelle place elle a fini. 1 veut dire qu'elle a "
                           "gagné",
    "points"             : "avec combien de points elle a fini",
    "couleur"            : "de quelle couleur elle a joué cette partie",
    "ordre_de_départ"    : "l'ordre du tour : 1 est celui qui commence",
    "numéro"             : "le numéro de la tuile, de 2 à 12",
    "ressource"          : "bois, argile, laine, blé ou minerai",
    "produit"            : "cartes venues de la PRODUCTION : ce que le "
                           "plateau a payé quand son numéro est sorti. Pas "
                           "d'échanges, pas de monopoles, et sans compter la "
                           "mise en place, qui est ce que fait "
                           "`de_la_mise_en_place`. Vérifié que les trois vues "
                           "qui portent ça donnent le même chiffre",
    "voleur_posé_sur_eux": "fois où **quelqu'un d'autre** a déplacé le voleur "
                           "sur une de ses tuiles. C'est ce dont les gens se "
                           "souviennent, et c'est plus du double du suivant. "
                           "Se le poser à soi-même ne compte pas ici -- si tu "
                           "te le poses, personne ne 'te l'a posé' -- et ça "
                           "apparaît dans « Le voleur, un par un », dans la "
                           "ligne où la même personne figure dans les deux "
                           "colonnes",
    "entre_amis"         : "1 si les quatre étaient des personnes ; 0 s'il y "
                           "avait des bots",
}


# Et les colonnes propres à chaque vue, dans l'ordre où elles
# apparaissent. Quand un nom est aussi dans COMMUNES, ce qui est écrit
# ici gagne : même mot, autre sens, et c'est justement la confusion que
# ce fichier existe pour éviter.
PAR_VUE = {
    # --- Parties -----------------------------------------------------------
    "parties": {
        "gagnant"          : "qui a gagné",
        "nombre_de_joueurs": "combien jouaient",
        "points_visés"     : "en combien de points la partie se jouait : **10 "
                             "pour Catane de base, 12 pour l'extension 5-6 "
                             "joueurs**. Ce n'est stocké nulle part "
                             "directement parce que ce n'est pas nécessaire : "
                             "ça se déduit du nombre de joueurs",
        "tuiles_du_plateau": "combien de tuiles avait le plateau : **19 pour "
                             "le jeu de base, 30 pour celui à 5-6**. C'est le "
                             "moyen le plus rapide de voir quelles parties "
                             "utilisaient le grand plateau",
        "bots"             : "combien des joueurs étaient l'ordinateur",
        "jets"             : "combien de fois les dés ont été lancés dans "
                             "cette partie",
        "minutes"          : "minutes entre le début et la fin de la partie. "
                             "**Vide** si elle n'a pas de fin enregistrée : "
                             "soit elle a été abandonnée, soit elle est "
                             "encore en cours",
        "problèmes"        : "ce qui a mal tourné à l'import, s'il y a eu "
                             "quelque chose -- ou les actions que l'analyseur "
                             "ne comprend pas, si tu as joué une extension. "
                             "Vide est normal. Ça vit dans la table et pas "
                             "dans un journal parce que **ça change ce que "
                             "disent les autres lignes** : la partie 11 a sa "
                             "production comptée comme s'il n'y avait pas eu "
                             "de voleur, et sans cette colonne c'est "
                             "invisible, elle a l'air d'une partie "
                             "parfaitement crédible",
    },

    # --- Joueurs -----------------------------------------------------------
    "joueurs": {
        "est_un_bot"       : "1 si c'est l'ordinateur",
        "nombre_de_joueurs": "combien jouaient cette partie",
        "points_visés"     : "en combien de points la partie se jouait (10 ou "
                             "12)",
    },

    # --- Le tableau des scores ---------------------------------------------
    "amis_tableau_des_scores": {
        "parties_jouées" : "combien il en a jouées **aux tables de cette "
                           "taille**",
        "taille_de_table": "combien jouaient. C'est ce qui découpe la table "
                           "en blocs",
        "victoires"      : "combien de ces parties il a gagnées",
        "points_moyens"  : "les points moyens avec lesquels il finit",
        "partie_en"      : "en combien de points la partie se jouait : 10 "
                           "jusqu'à quatre joueurs, 12 à cinq ou six. Elle "
                           "est à côté de `points_moyens` parce qu'on ne peut "
                           "pas lire cette colonne sans elle : 9 points à une "
                           "table de six est bien plus loin de gagner que 9 à "
                           "une table de quatre",
        "rang_moyen"     : "le rang moyen à l'arrivée. Plus bas est meilleur",
        "meilleur_score" : "son meilleur score à cette taille de table",
    },

    # --- L'ordre du tour ---------------------------------------------------
    "amis_depart": {
        "rangs_gagnés": "les colonies qu'il avait à la fin. Chacune vaut **1 "
                        "point**",
    },

    # --- Est-ce que partir premier compte ? --------------------------------
    "amis_par_depart": {
        "fois"         : "les villes à la fin. Chacune vaut **2 points**",
        "victoires"    : "1 s'il tenait la route la plus longue. Ça fait **2 "
                         "points**",
        "rang_moyen"   : "1 s'il tenait l'armée la plus puissante. Ça fait "
                         "**2 points**",
        "points_moyens": "les points qu'il avait cachés dans des cartes. **Ça "
                         "sort par soustraction**, pas en lisant les cartes : "
                         "points finaux moins colonies, villes et les deux "
                         "bonus. Ce qui reste ne pouvait être que des cartes "
                         "point de victoire. Vide quand un de ces termes "
                         "manque et que la soustraction ne peut pas se faire",
        "rangs_gagnés" : "le tour de sa **troisième** colonie, qui est la "
                         "première qu'il a vraiment construite en jeu : les "
                         "deux premières se posent avant le début de la "
                         "partie et tombent toutes les deux au tour 0, donc "
                         "elles ne disent rien de personne. Elle porte son "
                         "numéro plutôt que 'première' pour ne pas la "
                         "confondre avec celles-là",
    },

    # --- Quelle place tombe à chacun ---------------------------------------
    "amis_depart_de_chacun": {
        "parties_jouées": "le tour où il a transformé sa première colonie en "
                          "ville",
        "parti_1er"     : "le tour où il a acheté sa première carte "
                          "développement",
        "parti_2e"      : "le tour où il a joué son premier chevalier",
        "parti_3e"      : "le dernier tour de la partie, pour avoir quelque "
                          "chose à quoi comparer les autres",
        "parti_4e"      : "`ordre_de_départ` moins `rang`. Positif veut dire "
                          "qu'il a fini mieux qu'il n'est parti",
        "parti_5e"      : "combien de fois quelqu'un est parti de cette "
                          "position",
        "parti_6e"      : "combien de ces fois il a gagné",
        "parti_dernier" : "le rang moyen à l'arrivée pour qui part de là",
        "départ_moyen"  : "les points moyens pour qui part de là",
        "attendu"       : "les rangs moyens gagnés ou perdus en partant de là",
    },

    # --- Depuis chaque place, comment ça a fini ----------------------------
    "amis_depart_comment_fini": {
        "fois"    : "combien de parties il a jouées",
        "fini_1er": "combien de fois il a pu **partir** premier. Attention, "
                    "c'est la colonne la plus confondue de toute la table : "
                    "elle dit d'où il est PARTI, pas où il a fini. Elle "
                    "s'appelait `premier` avant et se lisait à l'envers -- "
                    "pour où il a fini, voir `victoires` dans « Le tableau "
                    "des scores » et la table « Depuis chaque place, comment "
                    "ça a fini »",
        "fini_2e" : "combien de fois il est parti deuxième",
        "fini_3e" : "combien de fois il est parti troisième",
        "fini_4e" : "combien de fois il est parti quatrième",
        "fini_5e" : "combien de fois il est parti cinquième. Seulement aux "
                    "tables de 5 ou 6",
        "fini_6e" : "combien de fois il est parti sixième. Seulement aux "
                    "tables de 6",
    },

    # --- D'où venait chaque point ------------------------------------------
    "amis_points": {
        "colonies"                : "combien de fois il est parti dernier, "
                                    "quelle que soit la taille de la table. "
                                    "Un 4e sur quatre n'est pas la même chose "
                                    "qu'un 4e sur six, et à Catane partir "
                                    "dernier a un avantage : on pose deux "
                                    "colonies d'affilée et on choisit en "
                                    "dernier",
        "villes"                  : "la moyenne de son ordre de départ. **Ça "
                                    "ne s'additionne pas**",
        "route_la_plus_longue"    : "combien de départs en premier lui "
                                    "reviendraient par pur hasard. Ça "
                                    "s'additionne comme 1/joueurs de cette "
                                    "partie, partie par partie, pour qu'une "
                                    "table de six ne fausse pas le compte des "
                                    "tables de quatre. Comparé à `parti_1er`, "
                                    "ça montre si le tirage lui a été "
                                    "favorable",
        "armée_la_plus_puissante" : "combien de parties il a commencées à "
                                    "cette place. C'est la somme des six "
                                    "colonnes d'à côté",
        "cartes_point_de_victoire": "de ces fois-là, combien il a **fini** "
                                    "premier -- autrement dit, gagné en "
                                    "partant de cette place",
    },

    # --- Cartes développement ----------------------------------------------
    "amis_developpement": {
        "parties_jouées"        : "combien de fois il a fini deuxième",
        "achetées"              : "combien de fois il a fini troisième",
        "par_partie"            : "combien de fois il a fini quatrième",
        "chevalier"             : "combien de fois il a fini cinquième. "
                                  "Seulement aux tables de 5 ou 6",
        "invention"             : "combien de fois il a fini sixième. "
                                  "Seulement aux tables de 6",
        "monopole"              : "combien de ses parties sont enregistrées. "
                                  "C'est là parce que sans ça la colonne "
                                  "suivante ne se compare pas : 61 cartes sur "
                                  "12 parties et 37 sur 11 ne veulent pas "
                                  "dire ce qu'elles ont l'air de dire l'une "
                                  "sous l'autre",
        "construction_de_routes": "cartes développement qu'il a achetées, "
                                  "toutes parties confondues",
        "point_de_victoire"     : "cartes développement **par partie** : "
                                  "`achetées` divisé par `parties_jouées`. "
                                  "C'est celle qui se compare vraiment entre "
                                  "personnes, parce qu'elle ne récompense pas "
                                  "celui qui a le plus joué",
        "inconnues"             : "parmi elles, combien étaient des "
                                  "chevaliers. Une carte développement est "
                                  "cachée tant qu'elle n'est pas jouée, donc "
                                  "ça ne compte que celles qu'il a vraiment "
                                  "jouées -- celles restées en main sont dans "
                                  "`inconnues`",
    },

    # --- Le paquet ---------------------------------------------------------
    "amis_paquet": {
        "carte"              : "combien étaient des cartes Invention",
        "tirées"             : "combien étaient des cartes Monopole",
        "tirages_attendus"   : "combien étaient des cartes Construction de "
                               "routes",
        "pourcentage_attendu": "combien étaient des cartes Point de victoire. "
                               "Elles ne se jouent jamais, donc elles "
                               "n'apparaissent jamais sur la table -- elles "
                               "sortent en soustrayant tout ce qui est "
                               "visible (colonies, villes et les deux bonus) "
                               "de ses points finaux",
        "pourcentage"        : "cartes achetées qui n'étaient ni jouées ni "
                               "des points de victoire. Elles sont restées "
                               "dans une main et il n'y a aucun moyen de "
                               "savoir lesquelles c'étaient",
    },

    # --- Les monopoles -----------------------------------------------------
    "amis_monopoles": {
        "demandé"   : "le type de carte développement : chevalier, point de "
                      "victoire, monopole, invention ou construction de "
                      "routes",
        "total_pris": "combien de celles-là ont été vues. Les dernières "
                      "lignes **ne sont pas des types de carte** : ce sont "
                      "les cartes achetées et jamais jouées (encore dans une "
                      "main), les cartes que personne n'a achetées et qui "
                      "sont restées dans le paquet, et -- seulement si ça "
                      "arrive un jour -- les cartes achetées par quelqu'un "
                      "hors du groupe. Toutes ensemble elles font le paquet "
                      "entier : dans une partie à quatre, 10 ont été tirées, "
                      "4 sont restées en main, 11 n'ont jamais été achetées, "
                      "et le paquet en avait 25",
        "de_qui"    : "combien **auraient dû** être tirées. Ça vient de deux "
                      "choses : combien de cartes ont été achetées en tout et "
                      "quelle part du paquet ce type représente. Si 10 cartes "
                      "ont été tirées et que 56 % du paquet est en "
                      "chevaliers, on en attend 5,6. À lire contre `tirées`, "
                      "juste à côté",
    },

    # --- Les monopoles, un par un ------------------------------------------
    "amis_monopoles_a_qui": {
        "monopoles": "quelle part du paquet cette carte représente, qui est "
                     "la part qui lui revient. 14 chevaliers sur 25 font 56 % "
                     "; à 5 ou 6 joueurs c'est 20 sur 35, 57,1 %. Elle porte "
                     "le même nom que dans « Les jets de dés » parce que "
                     "c'est la même idée avec des cartes au lieu de dés : 70 "
                     "contre 56 veut dire qu'il est sorti plus de chevaliers "
                     "que le paquet n'en contient",
        "tours"    : "quelle part de toutes les cartes vues celle-ci "
                     "représentait. **Ce ne sont pas les chances de la "
                     "tirer** -- c'est ce qui est réellement arrivé. Sur les "
                     "10 tirées, 7 étaient des chevaliers, soit 70 %. À lire "
                     "contre `pourcentage_attendu`",
        "bois"     : "la ressource qu'il a demandée. `inconnu` si cet "
                     "enregistrement ne l'a pas capté",
        "argile"   : "cartes qu'il a prises en tout. **NULL** veut dire que "
                     "cet enregistrement ne l'a pas noté, pas qu'il n'a rien "
                     "pris",
        "laine"    : "qui a perdu combien, sur une ligne : `Bruno 2, Carla "
                     "0`. Le 0 apparaît aussi, parce que « n'en avait aucune "
                     "» est une information. **Vide** pour les parties "
                     "d'avant le 22 août 2026, quand le mod n'enregistrait "
                     "pas encore qui payait quoi",
        "blé"      : "combien de monopoles il a lancés sur cette personne",
        "minerai"  : "à quels tours c'est arrivé. Une paire peut en avoir "
                     "plusieurs, donc ils sont tous listés dans l'ordre : on "
                     "voit si c'était une série ou si quelqu'un l'a dans le "
                     "viseur depuis le début",
        "cartes"   : "cartes bois qu'il lui a prises avec ça",
    },

    # --- Le voleur ---------------------------------------------------------
    "amis_voleur": {
        "volé_chez_eux" : "cartes argile qu'il lui a prises",
        "fois_bloqué"   : "cartes laine qu'il lui a prises",
        "cartes_perdues": "cartes blé qu'il lui a prises",
        "bois"          : "cartes minerai qu'il lui a prises",
        "argile"        : "le total des cinq colonnes d'à côté",
        "laine"         : "cartes volées dans sa main quand le voleur s'est "
                          "posé à côté d'elle. Une par vol : quelle carte "
                          "c'était n'est pas enregistré, c'est de "
                          "l'information cachée",
        "blé"           : "**des fois**, pas des cartes : les fois où le "
                          "numéro est aussi sorti et où il n'a pas été payé. "
                          "Presque une fois sur deux le voleur reste là et le "
                          "numéro ne ressort jamais, donc ça ne coûte rien. "
                          "Ça peut être plus haut que le compte du dessus : "
                          "s'il reste là et que le numéro sort trois fois, ça "
                          "fait trois blocages pour une seule pose",
        "minerai"       : "**des cartes**, pas des fois : ce que ces blocages "
                          "lui ont vraiment coûté. C'est le même chiffre que "
                          "`perdu_au_voleur` dans « Production ». Ça ne colle "
                          "pas avec `fois_bloqué` parce qu'une ville paie "
                          "double -- un blocage sur une colonie fait 1 carte, "
                          "sur une ville il en fait 2",
        "total_voleur"  : "sur `cartes_perdues`, combien étaient du bois",
    },

    # --- Sur qui s'acharne le voleur ? -------------------------------------
    "amis_voleur_proportion": {
        "déplacements"       : "sur `cartes_perdues`, combien étaient de "
                               "l'argile",
        "voleur_posé_sur_eux": "sur `cartes_perdues`, combien étaient de la "
                               "laine",
        "pourcentage"        : "sur `cartes_perdues`, combien étaient du blé",
        "attendus"           : "sur `cartes_perdues`, combien étaient du "
                               "minerai",
        "acharnement"        : "**ce que le voleur lui a coûté en tout** : "
                               "`cartes_perdues` + `volé_chez_eux`. C'est le "
                               "chiffre que les gens gardent vraiment en "
                               "tête, et celui qui manquait -- « j'en ai "
                               "perdu 4 » voulait dire 4 en production et 6 "
                               "volées. Elle s'appelle `total_voleur` et pas "
                               "`leur_a_coûté` parce que ce nom est déjà pris "
                               "dans « Le voleur, un par un », où ce sont "
                               "**seulement** les ressources bloquées",
    },

    # --- Le voleur, un par un ----------------------------------------------
    "amis_voleur_a_qui": {
        "posé_sur_eux"  : "combien de fois **d'autres personnes** ont déplacé "
                          "le voleur dans ses parties. Tout ce qui est à côté "
                          "se mesure contre ça, et elle vient en premier pour "
                          "la même raison que `jets_comptés` dans la chance : "
                          "un 116 et un 63 ont l'air comparables, mais l'un "
                          "vient de 197 déplacements et l'autre de 7",
        "avec_un_7"     : "de ces déplacements, combien ont atterri sur elle. "
                          "C'est le même chiffre que dans « Le voleur », et "
                          "un test l'impose",
        "avec_chevalier": "`voleur_posé_sur_eux` divisé par `déplacements`. "
                          "**Rien n'est déduit ici** : avoir beaucoup de "
                          "tuiles fait aussi partie du jeu, et si tout ce que "
                          "tu veux savoir c'est qui reçoit le plus le voleur "
                          "-- point -- c'est ta colonne. La seule chose "
                          "qu'elle écarte est ce qui ne dit rien de personne "
                          ": combien de parties quelqu'un a jouées et combien "
                          "de temps elles ont duré",
        "les_a_bloqués" : "combien il **aurait dû** en recevoir, exprimé en "
                          "nombre plutôt qu'en pourcentage pour se lire d'un "
                          "coup d'œil contre `voleur_posé_sur_eux` juste à "
                          "côté : 109 contre 94,3 parle tout seul. Ça vient "
                          "de répartir chaque déplacement entre les joueurs "
                          "selon le nombre de tuiles que chacun avait **à ce "
                          "moment-là**, ce qui donne son dû à celui qui s'est "
                          "vraiment fait avoir. Additionne toute la colonne "
                          "et tu obtiens exactement le nombre total de poses "
                          "du voleur -- 352,9 contre 353 -- et c'est ce qui "
                          "fait que le 100 d'à côté veut dire 100",
        "leur_a_coûté"  : "`voleur_posé_sur_eux` divisé par `attendu`, en "
                          "pourcentage. **C'est la colonne qui dit si les "
                          "gens s'acharnent sur toi** : 100 est ce qui est "
                          "attendu, au-dessus ils te visent plus qu'ils ne "
                          "devraient, en dessous ils te laissent tranquille. "
                          "Elle se lit comme `chance` dans « La chance de "
                          "chacun aux dés », exprès, parce que c'est la même "
                          "forme : ce qui est arrivé contre ce qui était dû. "
                          "**La première version de cette table comparait à "
                          "un voleur aveugle et c'était faux** : contre cette "
                          "référence tout le monde sortait au-dessus du "
                          "normal, ce qui est impossible pour un groupe "
                          "entier. Mesuré : un voleur posé exprès attrape "
                          "1,49 personne par déplacement contre 1,14 pour un "
                          "voleur au hasard, 31 % de plus. Évidemment que "
                          "tout le monde avait l'air haut -- le voleur vise "
                          "*quelqu'un* exprès. Avec la référence actuelle "
                          "certains sont au-dessus et d'autres en dessous, ce "
                          "qui est comme ça doit être",
        "bois"          : "fois où il a déplacé le voleur sur une tuile où "
                          "l'autre personne avait déjà quelque chose. C'est "
                          "l'intention. **Si les deux personnes de la ligne "
                          "sont la même, il se l'est posé à lui-même** : "
                          "c'est légal et ça arrive -- parfois un 7 ne laisse "
                          "rien de mieux, et parfois c'est délibéré, pour "
                          "voler quelqu'un qui partage cette tuile sans "
                          "offrir le blocage à un rival",
        "argile"        : "de celles-là, combien étaient **forcées** par un 7",
        "laine"         : "de celles-là, combien étaient **choisies**, en "
                          "jouant un chevalier",
        "blé"           : "**des fois**, pas des cartes : sur ces poses, "
                          "combien de fois le numéro est aussi sorti et "
                          "l'autre personne a raté un paiement. C'est le "
                          "dégât qui est vraiment tombé, face à "
                          "`posé_sur_eux`, qui n'est que l'intention",
        "minerai"       : "**des cartes**, pas des fois : ce que l'autre "
                          "personne n'a pas pu encaisser à cause de ces "
                          "blocages. Ça ne colle pas avec `les_a_bloqués` "
                          "parce qu'une ville paie double. À noter : ce sont "
                          "**seulement** les cartes bloquées -- ce qui a été "
                          "volé dans la main est à part, dans `leur_a_volé`",
        "leur_a_volé"   : "sur `leur_a_coûté`, combien étaient du bois",
    },

    # --- Le voleur : sur qui et sur quel numéro ----------------------------
    "amis_voleur_a_qui_numero": {
        "numéro"        : "sur `leur_a_coûté`, combien étaient de l'argile",
        "posé_sur_eux"  : "sur `leur_a_coûté`, combien étaient de la laine",
        "avec_un_7"     : "sur `leur_a_coûté`, combien étaient du blé",
        "avec_chevalier": "sur `leur_a_coûté`, combien étaient du minerai",
    },

    # --- Où chacun envoie le voleur ----------------------------------------
    "amis_voleur_ou": {
        "fois"          : "cartes qu'il a prises dans la main de l'autre "
                          "personne. **Combien, pas lesquelles** : personne "
                          "ne lit la carte volée",
        "avec_un_7"     : "le numéro de la tuile où il lui a posé le voleur",
        "avec_chevalier": "fois où il a déplacé le voleur sur cette tuile "
                          "précise pendant que l'autre personne avait quelque "
                          "chose dessus. Ici c'est seulement l'intention : ce "
                          "que ça a vraiment coûté est dans « Le voleur, un "
                          "par un »",
        "à_soi-même"    : "de celles-là, combien étaient **forcées** par un 7",
    },

    # --- Les numéros que le voleur bloque le plus --------------------------
    "amis_voleur_numeros": {
        "fois"          : "de celles-là, combien étaient **choisies**, en "
                          "jouant un chevalier. Avec un grand nombre, c'est "
                          "la colonne qui sépare la malchance des mauvaises "
                          "intentions",
        "avec_un_7"     : "combien de fois le voleur est allé sur ce numéro, "
                          "tout le monde confondu",
        "avec_chevalier": "de celles-là, combien étaient forcées par un 7",
        "personnes"     : "de celles-là, combien étaient choisies, avec un "
                          "chevalier",
    },

    # --- Production --------------------------------------------------------
    "amis_production": {
        "bois"               : "combien de personnes différentes l'ont couvert",
        "argile"             : "combien de fois il a envoyé le voleur sur ce "
                               "numéro",
        "laine"              : "de celles-là, combien étaient forcées par un 7",
        "blé"                : "de celles-là, combien étaient choisies, avec "
                               "un chevalier",
        "minerai"            : "de ces fois-là, combien sont tombées sur **sa "
                               "propre** tuile. C'est légal et ça arrive : "
                               "parfois un 7 ne laisse pas de meilleur "
                               "endroit, et parfois c'est délibéré, pour "
                               "voler quelqu'un qui partage aussi cette tuile "
                               "sans offrir le blocage à un rival. Ça "
                               "n'apparaît pas dans « Le voleur, un par un » "
                               "parce que celle-là travaille par paires et "
                               "qu'une ligne contre soi-même prête à "
                               "confusion ; ça apparaît ici à la place",
        "total"              : "cartes qu'il a volées dans les mains des "
                               "autres",
        "de_la_mise_en_place": "cartes qui lui ont été volées",
        "perdu_au_voleur"    : "échanges **qu'il a proposés** à cette "
                               "personne. Ceux que l'autre a proposés sont "
                               "dans la ligne retour",
    },

    # --- Les numéros de chacun ---------------------------------------------
    "amis_numeros": {
        "constructions"   : "cartes qu'il a lâchées dans ces échanges",
        "première_colonie": "cartes qui lui sont revenues dans ces échanges",
        "pastilles"       : "`a_reçu` moins `a_donné` **seulement dans les "
                            "échanges qu'il a proposés**. **Ce n'est pas son "
                            "solde avec cette personne** -- ça c'est `net` "
                            "dans « Le solde avec chacun », qui sort "
                            "différent dans 16 des 26 paires, plusieurs avec "
                            "le signe inversé. La table porte l'avertissement "
                            "elle-même : les deux lignes d'une paire peuvent "
                            "être **toutes les deux négatives**, et dans un "
                            "vrai solde c'est impossible -- les cartes ne "
                            "disparaissent pas en changeant de main. Elles le "
                            "peuvent ici parce que ce sont des ensembles "
                            "d'échanges différents. Et il y a une raison pour "
                            "que la plupart le soient : sur 141 échanges "
                            "proposés, celui qui propose finit avec **30 "
                            "cartes de moins**",
        "fois_sorti"      : "combien d'échanges les deux ont faits, qui que "
                            "ce soit qui les ait proposés. **Le même chiffre "
                            "dans les deux lignes de la paire**",
        "jets_attendus"   : "combien de parties les deux ont jouées ensemble. "
                            "C'est ce qui donne son sens à la colonne d'à "
                            "côté : deux échanges entre deux personnes qui "
                            "n'ont joué que deux parties ensemble et deux "
                            "échanges entre deux qui en ont joué treize se "
                            "ressemblent dans la table et ne sont pas la même "
                            "chose",
    },

    # --- La chance de chacun aux dés ---------------------------------------
    "amis_chance": {
        "tuiles"             : "échanges entre les deux, qui que ce soit qui "
                               "les ait proposés",
        "pastilles"          : "cartes qu'il leur a données en tout",
        "pastilles_par_tuile": "cartes qui lui sont venues de cette personne",
        "référence"          : "`a_reçu` moins `a_donné`. La ligne retour "
                               "porte le même chiffre avec le signe inversé",
        "cartes_par_tuile"   : "ce qu'il a lâché, écrit tel quel : `1 Bois + "
                               "1 Laine`",
        "leurs_jets"         : "à qui il l'a donné",
        "jets_comptés"       : "ce qu'il a reçu en échange",
        "reçu"               : "combien de cartes de cette ressource il lui a "
                               "données",
        "attendu"            : "combien de cette ressource lui sont venues de "
                               "cette personne",
        "surplus"            : "`a_reçu` moins `a_donné` pour cette "
                               "ressource. Avec qui il est en manque, et sur "
                               "quoi",
        "chance"             : "lequel il a utilisé : `Bois 2:1` ou "
                               "`générique 3:1`. Les échanges à 4:1 -- ceux "
                               "que fait n'importe qui sans port -- ne sont "
                               "pas inclus : cette table parle précisément "
                               "des ports, et ils apparaissent tous dans « "
                               "Échange par échange »",
        "marge"              : "combien d'échanges avec la banque il y a "
                               "faits, **toutes parties confondues**. Pour "
                               "voir dans combien de parties différentes ce "
                               "port pouvait vraiment lui être compté, voir « "
                               "Combien, par joueur »",
        "écarts-types"       : "le **plus tôt** où il l'a utilisé : le plus "
                               "petit numéro de tour, toutes parties "
                               "confondues. C'est un plafond sur le moment où "
                               "il l'a eu, pas le moment où il l'a eu -- il a "
                               "pu l'avoir dès là, mais peut-être avant",
    },

    # --- Qui propose des échanges à qui ------------------------------------
    "amis_echanges": {
        "échanges"          : "le **plus tard** où il l'a utilisé, toutes "
                              "parties confondues. Ce n'est pas l'autre bout "
                              "de la même partie que `première_utilisation`",
        "a_donné"           : "combien de ses parties sont enregistrées. Elle "
                              "vient en premier parce que sans elle rien "
                              "d'autre ne se compare : utiliser le port bois "
                              "quatre fois en vingt parties n'est pas la même "
                              "chose que quatre fois en six",
        "a_reçu"            : "dans combien de parties le port bois 2:1 "
                              "pouvait lui être compté. **Combien de parties, "
                              "pas combien de fois il l'a utilisé** : "
                              "l'utiliser quinze fois dans une partie compte "
                              "une fois, parce que ce qui se mesure c'est de "
                              "l'avoir. Et « pouvait lui être compté » plutôt "
                              "que « l'avait », parce que **ça se déduit des "
                              "échanges qu'il a faits**, pas en regardant le "
                              "plateau : un port qu'il avait mais n'a jamais "
                              "utilisé n'apparaît pas",
        "net_en_proposant"  : "pareil, pour le port argile 2:1",
        "échanges_entre_eux": "pareil, pour le port laine 2:1",
        "parties_ensemble"  : "pareil, pour le port blé 2:1",
    },

    # --- Le solde avec chacun ----------------------------------------------
    "amis_solde": {
        "échanges": "pareil, pour le port minerai 2:1",
        "a_donné" : "dans combien de parties un port générique (3:1) pouvait "
                    "lui être compté. Les ports génériques ne se distinguent "
                    "pas les uns des autres : un seul couvre déjà les cinq "
                    "ressources, donc en avoir deux ne laisse aucune trace "
                    "différente d'en avoir un",
        "a_reçu"  : "lequel c'est, avec son taux d'échange",
        "net"     : "qui s'y est installé. **`personne`** veut dire un port "
                    "que personne n'a jamais pris, et c'est la moitié de la "
                    "raison d'être de cette table",
    },

    # --- Échange par échange -----------------------------------------------
    "amis_marches": {
        "a_donné"  : "le tour où il a posé la pièce là. Passer à la ville ne "
                     "compte pas : le port est pris quand on s'y installe la "
                     "première fois",
        "à"        : "ce que cet emplacement est devenu à la fin, colonie ou "
                     "ville",
        "et_a_reçu": "bois que le plateau lui a donné",
    },

    # --- Ce qui s'échange --------------------------------------------------
    "amis_echanges_ressource": {
        "a_donné": "argile que le plateau lui a donnée",
        "a_reçu" : "laine que le plateau lui a donnée",
        "net"    : "blé que le plateau lui a donné",
    },

    # --- Port par port -----------------------------------------------------
    "amis_ports": {
        "port"                : "minerai que le plateau lui a donné",
        "fois"                : "la somme des cinq. **Comprend la mise en "
                                "place**, que le plateau distribue aussi ; si "
                                "tu veux seulement ce qui vient des jets, "
                                "soustrais `de_la_mise_en_place`",
        "première_utilisation": "les cartes qu'il a encaissées **en posant sa "
                                "deuxième colonie** : une par tuile "
                                "adjacente. C'est la seule part de `total` "
                                "qui ne vient pas d'un jet, et c'est environ "
                                "3 par partie. Elle est gardée à part parce "
                                "que c'est la différence avec `produit`, qui "
                                "ne compte que ce que le plateau a payé quand "
                                "un numéro est sorti",
        "dernière_utilisation": "**des cartes** qu'il n'a pas encaissées "
                                "parce que le voleur était posé sur la tuile. "
                                "C'est le même chiffre que `cartes_perdues` "
                                "dans « Le voleur », sous un autre nom : "
                                "cette ligne-là parle du voleur, celle-ci "
                                "parle de production, et chacune se lit mieux "
                                "avec son propre nom",
    },

    # --- Qui s'est adjugé chaque port --------------------------------------
    "amis_ports_pris": {
        "port"        : "combien de ses pièces touchent ce numéro, toutes "
                        "parties confondues. Treize colonies sur le 6 peuvent "
                        "être treize parties avec une, ou deux parties avec "
                        "six",
        "qui"         : "à quel tour il a posé une pièce là pour la première "
                        "fois. **`0` est la mise en place**, et un tiret (—) "
                        "veut dire qu'il n'a jamais rien posé sur ce numéro "
                        "-- ces deux-là veulent dire le contraire l'un de "
                        "l'autre, attention. À l'intérieur d'une partie c'est "
                        "la **première** : deux colonies sur le même numéro, "
                        "tours 0 et 41, donnent 0 et pas 20, parce que dès le "
                        "tour 0 il encaissait déjà là. Entre parties c'est la "
                        "**moyenne** de ces premières, et c'est pour ça "
                        "qu'elle porte une décimale : un 13,8 rappelle que "
                        "c'est une moyenne et pas littéralement le tour 13. "
                        "Elle se lit à côté de `fois_sorti`, parce que cette "
                        "colonne compte les jets de toute la partie : avoir "
                        "le 6 depuis le tour 0 et l'avoir depuis le tour 30 "
                        "s'y ressemblent, et ça ne vaut pas pareil. Passer à "
                        "la ville ne la déplace pas -- elle compte quand la "
                        "colonie a été posée",
        "tour"        : "les pastilles imprimées sous le numéro de la tuile : "
                        "combien des 36 combinaisons de deux dés le "
                        "produisent. Le 6 en a cinq, le 2 en a une. **Ça ne "
                        "s'additionne pas** : c'est une propriété du numéro, "
                        "pas un compteur, donc ça sort pareil que tu regardes "
                        "une partie ou toutes",
        "construction": "combien de fois ce numéro est sorti, en ne comptant "
                        "que les parties où il avait quelque chose de posé "
                        "dessus. Dans une partie où ce numéro n'était pas à "
                        "lui, aucun de ses jets ne compte",
    },

    # --- Combien, par joueur -----------------------------------------------
    "amis_combien_de_ports": {
        "parties_jouées"  : "combien de fois il aurait dû sortir, d'après ses "
                            "pastilles : pastilles divisées par 36, fois le "
                            "nombre de jets. C'est compté partie par partie "
                            "et additionné, de la même façon que "
                            "`fois_sorti`, pour que les deux se comparent "
                            "directement",
        "port_bois"       : "combien de ses parties sont enregistrées",
        "port_argile"     : "combien de fois il a lancé les dés lui-même. "
                            "C'est ce qui rend la colonne suivante comparable "
                            ": les parties ne durent pas toutes pareil. Elle "
                            "s'appelle `leurs_jets` et pas `jets` exprès -- "
                            "la boîte à questions du haut traduit « sort » et "
                            "« dé » par « jet », et sous ce nom cette table "
                            "recevait sans arrêt des questions d'échanges",
        "port_laine"      : "combien de ces jets ont fait 7",
        "port_blé"        : "quelle part de **ses** jets était un 7",
        "port_minerai"    : "les 16,7 % que n'importe qui devrait attendre : "
                            "6 des 36 combinaisons. Au-dessus veut dire que "
                            "le 7 lui sort plus qu'il ne devrait -- et le 7 "
                            "est le seul numéro qui dépend de qui lance : il "
                            "déplace le voleur et force une défausse",
        "ports_génériques": "combien de fois ce numéro est sorti",
    },

    # --- Le rythme de chacun -----------------------------------------------
    "amis_rythme": {
        "troisième_colonie" : "combien de fois il aurait dû sortir, d'après "
                              "ses pastilles sur 36. Le 7 est 6 jets sur 36 ; "
                              "le 2 en est un",
        "première_ville"    : "quelle part de tous les jets était ce numéro",
        "première_carte_dév": "quelle part il aurait dû être : les pastilles "
                              "de ce numéro sur 36. À lire à côté de "
                              "`pourcentage`, qui est ce qui est réellement "
                              "arrivé",
        "premier_chevalier" : "**ses propres emplacements qui paient**, pas "
                              "des tuiles distinctes du plateau. S'il a deux "
                              "pièces qui touchent la même tuile, cette tuile "
                              "compte deux fois -- parce que quand le numéro "
                              "sort, il est payé deux fois. Ça arrive souvent "
                              ": 159 cas dans les parties actuelles. Ce qui "
                              "ne compte **pas** deux fois, c'est de passer à "
                              "la ville : les dés ne savent pas ce qui est "
                              "construit là, et cette colonne mesure la "
                              "fréquence à laquelle le numéro va sortir pour "
                              "toi, pas combien de cartes on te paie",
        "a_duré_jusqu'à"    : "les pastilles de ces emplacements, "
                              "additionnées. **C'est ici qu'un 6 pèse cinq "
                              "fois ce que pèse un 2.** Attention au calcul : "
                              "un 6 vaut **5** pastilles, pas 6, donc deux "
                              "emplacements sur un 6 font 10. Et peu importe "
                              "que ce soient deux tuiles 6 différentes ou "
                              "deux de tes pièces sur la même : dans les deux "
                              "cas tu es payé deux fois",
    },

    # --- Les vols dans la main ---------------------------------------------
    "amis_vols": {
        "cartes_volées": "`pastilles` divisé par `tuiles` : **ce que vaut un "
                         "de ses emplacements en moyenne**. C'est ce qui "
                         "permet de comparer deux personnes, parce que les "
                         "pastilles brutes récompensent celui qui a joué le "
                         "plus de parties",
        "volé_chez_eux": "ce que vaudrait une tuile moyenne sur les plateaux "
                         "où il a joué -- 3,22 pour le plateau classique. "
                         "Au-dessus veut dire qu'il choisit de bons "
                         "emplacements ; en dessous, qu'il se contente de "
                         "moins. **Ce n'est pas de la chance, c'est du "
                         "jugement** : la part de chance, c'est que ces "
                         "numéros sortent vraiment, et ça c'est `chance`",
    },

    # --- Les jets de dés ---------------------------------------------------
    "amis_jets": {
        "fois"               : "cartes que chacun de ses emplacements lui a "
                               "payées, en moyenne. **Ne compare pas ça à "
                               "`pastilles_par_tuile`** -- celle-là, ce sont "
                               "des pastilles, celle-ci des cartes. Les "
                               "villes paient double ici, et le voleur ne "
                               "paie rien",
        "fois_attendues"     : "**combien de fois il a lancé les dés "
                               "lui-même.** Ne confonds pas avec celle d'à "
                               "côté : `jets_comptés` est chaque jet de la "
                               "table qui pouvait le payer -- qui que ce soit "
                               "qui l'ait lancé -- tandis que celle-ci ne "
                               "compte que ses propres jets, donc à une table "
                               "de quatre c'est environ un quart du total. "
                               "**Elle n'entre pas dans le calcul de la "
                               "chance**, parce que les dés se fichent de "
                               "savoir à qui c'est le tour : si un 6 sort, "
                               "c'est celui qui a quelque chose sur le 6 qui "
                               "est payé, pas celui qui a lancé. Le seul "
                               "numéro qui dépend de qui lance, c'est le 7, "
                               "et c'est dans « Les sept de chacun » -- où "
                               "cette même colonne est le dénominateur",
        "pourcentage"        : "**combien de jets servent de référence à tout "
                               "le reste.** Sans elle, un 108 % et un 99 % "
                               "ont l'air de résultats comparables, et l'un "
                               "peut venir de 53 jets et l'autre de 837. Ce "
                               "sont les jets où il avait quelque chose de "
                               "posé -- ce qui est aujourd'hui tous les jets "
                               "de ses parties, puisque les deux colonies de "
                               "départ se posent avant le premier lancer. "
                               "**Ce n'est pas le multiplicateur derrière "
                               "`attendu`** -- celui-là utilise la fenêtre "
                               "propre à chaque tuile séparément, donc "
                               "celle-ci, calculée à partir des pastilles, ne "
                               "collera pas avec et n'a pas à le faire. C'est "
                               "la taille de l'échantillon, pas un facteur",
        "pourcentage_attendu": "**des encaissements, pas des jets**. Chaque "
                               "fois qu'un de ses numéros sort, ça compte une "
                               "fois **par emplacement qu'il a dessus** : "
                               "trois emplacements sur le 4 et un 4 qui sort, "
                               "ça fait *un jet et trois encaissements*. Dans "
                               "une partie de base : 46 jets, 28 sont tombés "
                               "sur un de ses numéros, et il a été payé 41 "
                               "fois. C'est ce que le plateau lui a vraiment "
                               "payé",
    },

    # --- Les sept de chacun ------------------------------------------------
    "amis_sept": {
        "parties_jouées"     : "les encaissements qu'il aurait dû avoir : "
                               "pour chacun de ses emplacements, ses "
                               "pastilles sur 36, fois chaque jet. C'est "
                               "compté de la même façon que `reçu` -- avec la "
                               "même règle *par emplacement* -- et c'est pour "
                               "ça que les deux sont comparables. C'est ce "
                               "que le plateau lui devait",
        "leurs_jets"         : "`reçu` moins `attendu`, en encaissements",
        "7_obtenus"          : "`reçu` divisé par `attendu`, en pourcentage. "
                               "**100 est la chance normale**",
        "pourcentage"        : "de combien le hasard déplace normalement ça, "
                               "en pourcentage. Avec neuf tuiles, le hasard "
                               "seul te déplace de ±17 % ; avec cinquante, de "
                               "±6 %",
        "pourcentage_attendu": "de combien d'écarts c'est décalé, avec un "
                               "signe. **C'est le chiffre qui classe vraiment "
                               "les gens** : en dessous de 2, rien de tout ça "
                               "ne veut dire quoi que ce soit, quoi que dise "
                               "le pourcentage",
    },
}


# Ce qu'est une ligne dans chaque table, et à quoi elle sert. Les deux
# phrases vont ensemble exprès : savoir qu'une ligne est « chaque
# paire » ne dit pas pourquoi tu voudrais regarder ça.
LA_LIGNE = {
    "parties": {
        "ligne": "chaque partie jouée",
        "pour": "voir d'un coup d'œil combien tu en as jouées, combien de "
                 "temps elles durent, et lesquelles étaient contre "
                 "l'ordinateur",
    },
    "joueurs": {
        "ligne": "chaque joueur dans chaque partie",
        "pour": "c'est la table à partir de laquelle presque tout le reste "
                 "est construit : nom, couleur, de quelle place il est parti "
                 "et à quelle place il a fini",
    },
    "amis_tableau_des_scores": {
        "ligne": "chaque personne",
        "pour": "le tableau des scores classique : qui gagne le plus et qui "
                 "finit le mieux classé",
    },
    "amis_depart": {
        "ligne": "chaque joueur dans chaque partie",
        "pour": "voir partie par partie qui est parti premier et si ça lui a "
                 "servi à quelque chose",
    },
    "amis_par_depart": {
        "ligne": "chaque position de départ (1re, 2e, 3e...)",
        "pour": "la question de toujours : est-ce que partir premier paie, "
                 "ou est-ce que dernier est en fait mieux parce qu'on pose "
                 "deux colonies d'affilée ?",
    },
    "amis_depart_de_chacun": {
        "ligne": "chaque personne",
        "pour": "si le tirage te traite bien : combien de fois tu as pu "
                 "partir premier, contre combien de fois tu aurais dû. "
                 "**Toutes les colonnes de cette table parlent d'où tu es "
                 "parti, pas d'où tu as fini**",
    },
    "amis_depart_comment_fini": {
        "ligne": "chaque personne **et position de départ**",
        "pour": "si partir premier aide vraiment. Quelqu'un qui part souvent "
                 "premier et gagne souvent ne te dit pas qu'il gagne QUAND il "
                 "part premier, et aucune autre table ne croise ces deux "
                 "choses personne par personne. Avec peu de parties ça sort "
                 "très dispersé : c'est comme ça, et ça se lit bien quand il "
                 "y a plus de parties",
    },
    "amis_points": {
        "ligne": "chaque joueur dans chaque partie",
        "pour": "d'où venaient ses points : colonies, villes, les deux bonus "
                 "et, par soustraction, les cartes cachées",
    },
    "amis_developpement": {
        "ligne": "chaque personne",
        "pour": "ce que le paquet donne à chacun : s'il tombe sur beaucoup "
                 "de chevaliers ou sur beaucoup de points de victoire",
    },
    "amis_paquet": {
        "ligne": "chaque type de carte développement",
        "pour": "si le paquet se comporte bien : ce qui est vraiment sorti "
                 "contre ce que le paquet contient",
    },
    "amis_monopoles": {
        "ligne": "chaque monopole joué",
        "pour": "les voir un par un : qui l'a joué, ce qu'il a demandé et "
                 "combien il a pris",
    },
    "amis_monopoles_a_qui": {
        "ligne": "chaque paire de joueurs",
        "pour": "les monopoles de qui font mal à qui, et sur quelle ressource",
    },
    "amis_voleur": {
        "ligne": "chaque personne",
        "pour": "ce que le voleur te coûte sur une partie entière : ce que "
                 "tu n'as pas encaissé plus ce qu'on t'a volé",
    },
    "amis_voleur_proportion": {
        "ligne": "chaque personne",
        "pour": "savoir qui est vraiment visé le plus, et pas seulement qui "
                 "a joué le plus de parties. C'est « Le voleur » en "
                 "proportion, et ça change le classement",
    },
    "amis_voleur_a_qui": {
        "ligne": "chaque paire de joueurs",
        "pour": "les rancunes : si quelqu'un te pose le voleur bien plus "
                 "souvent qu'aux autres, ça se voit ici",
    },
    "amis_voleur_a_qui_numero": {
        "ligne": "chaque paire de joueurs **et numéro**",
        "pour": "s'ils le posent là où ça fait mal. Ce n'est pas pareil de "
                 "le prendre sur un 11 -- avec un 7 il faut bien le déplacer "
                 "quelque part, et parfois c'est juste pour voler une carte "
                 "sans plus réfléchir -- que sur un 6, qui sort deux fois et "
                 "demie plus souvent. C'est la plus fine des quatre tables du "
                 "voleur : avec peu de parties tu verras beaucoup de lignes à "
                 "1, et ce n'est pas un défaut",
    },
    "amis_voleur_ou": {
        "ligne": "chaque personne et numéro",
        "pour": "vers quels numéros chacun envoie le voleur. Presque tout le "
                 "monde a un favori",
    },
    "amis_voleur_numeros": {
        "ligne": "chaque numéro du plateau",
        "pour": "quels numéros finissent le plus bloqués, en additionnant "
                 "les déplacements de tout le monde",
    },
    "amis_production": {
        "ligne": "chaque personne",
        "pour": "quelles ressources le plateau donne à chacun, et combien "
                 "s'est perdu en chemin",
    },
    "amis_numeros": {
        "ligne": "chaque personne et **chacun des dix numéros**, toutes "
                  "parties confondues. Les dix apparaissent toujours, même "
                  "s'il n'a jamais rien posé dessus : un 6 vide en dit plus "
                  "long que la moitié de la table. Le 7 n'est pas là parce "
                  "qu'aucune tuile ne porte un 7",
        "pour": "autour de quels numéros chacun construit, combien lui était "
                 "dû et combien est vraiment rentré. Pour un plateau précis, "
                 "le menu déroulant filtre cette même table",
    },
    "amis_chance": {
        "ligne": "chaque personne",
        "pour": "qui a vraiment de la chance. Ça compare ce qu'il a reçu à "
                 "ce qu'il aurait dû recevoir, et dit si la différence est "
                 "réelle ou juste du bruit",
    },
    "amis_echanges": {
        "ligne": "chaque paire **et qui a proposé**. La ligne retour est un "
                  "ensemble d'échanges DIFFÉRENT : 3 et 1 veut dire qu'un "
                  "côté a demandé trois fois et l'autre une, quatre en tout",
        "pour": "qui propose des échanges à qui, et s'il en sort gagnant ou "
                 "perdant en cartes",
    },
    "amis_solde": {
        "ligne": "chaque paire **vue de chaque côté**. Attention, c'est "
                  "celle qu'on confond le plus : `qui` ne veut PAS dire qui a "
                  "proposé l'échange -- ça c'est dans « Qui propose des "
                  "échanges à qui » -- c'est du point de vue de qui la ligne "
                  "est racontée. Les deux lignes d'une paire sont **les mêmes "
                  "échanges**, et c'est pour ça qu'elles portent les mêmes "
                  "`échanges` et le même `net` avec le signe inversé",
        "pour": "le solde simple avec chacun : combien de cartes tu lui as "
                 "données et combien il t'en a données",
    },
    "amis_marches": {
        "ligne": "chaque échange conclu",
        "pour": "les voir un par un, ce qui a été donné pour ce qui a été "
                 "reçu",
    },
    "amis_echanges_ressource": {
        "ligne": "chaque paire et ressource",
        "pour": "sur quelle ressource chacun sort gagnant : « je finis "
                 "toujours par donner du bois à cette personne »",
    },
    "amis_ports": {
        "ligne": "chaque personne et port, toutes parties confondues",
        "pour": "qui utilise les ports et à partir de quel tour. Déduit des "
                 "échanges avec la banque. Pour un plateau précis, le menu "
                 "déroulant filtre cette même table",
    },
    "amis_ports_pris": {
        "ligne": "chaque port de la carte",
        "pour": "qui a fini avec chaque port, y compris ceux que personne "
                 "n'a pris",
    },
    "amis_combien_de_ports": {
        "ligne": "chaque personne, toutes parties confondues",
        "pour": "autour de quel port chacun construit. Plateau par plateau "
                 "ce sont quatre lignes presque vides ; sur l'ensemble le "
                 "motif apparaît. Pour le voir partie par partie, le menu "
                 "déroulant filtre cette même table, et « Qui s'est adjugé "
                 "chaque port » le montre plateau par plateau",
    },
    "amis_rythme": {
        "ligne": "chaque joueur dans chaque partie",
        "pour": "qui démarre le plus tôt : à quel tour il a eu sa première "
                 "ville, sa première carte développement, son premier "
                 "chevalier",
    },
    "amis_vols": {
        "ligne": "chaque personne",
        "pour": "combien de cartes il a volées dans des mains, et combien on "
                 "lui en a volées",
    },
    "amis_jets": {
        "ligne": "chaque numéro, de 2 à 12",
        "pour": "si les dés sont justes : ce qui est vraiment sorti contre "
                 "ce qui aurait dû sortir",
    },
    "amis_sept": {
        "ligne": "chaque personne, toutes parties confondues",
        "pour": "qui sort plus de 7 qu'il ne devrait quand c'est son tour. « "
                 "Les jets de dés » vérifie si les dés sont justes envers la "
                 "table ; celle-ci vérifie s'ils sont justes envers chaque "
                 "personne",
    },
}
