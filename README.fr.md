*[Léeme en castellano](README.md) · [Read me in English](README.en.md).*

# Catan Tracker

Tes parties de **Catan Universe**, enregistrées toutes seules et transformées
en statistiques : qui gagne, qui a vraiment de mauvais dés, où chacun envoie
le voleur, qui échange avec qui et qui s'en sort le mieux.

Rien ne se tape à la main. Tu joues, tu appuies sur un bouton, et c'est
dedans.

---

## Pour commencer

Il te faut **Python 3.7 ou plus récent** et **Catan Universe** sur Steam.
Rien d'autre.

```powershell
py panel.py --simple
```

Une page s'ouvre dans ton navigateur. Tout se passe là, avec des boutons.

> `py` n'est pas une faute de frappe : c'est le lanceur Python de Windows, et
> il marche même quand `python` n'est pas dans ton PATH. Si tu as une
> erreur, c'est en général pour ça.

**Il n'y a aucune dépendance à installer.** `requirements.txt` est vide
exprès : tout tourne avec la bibliothèque standard de Python et rien d'autre.
Il n'y a pas de `pip install` qui puisse te planter.

> **Windows seulement.** Le mod s'accroche au jeu par `winhttp.dll`, qui est un
> mécanisme Windows, et Catan Universe est lui-même un jeu Windows. La moitié
> qui lit les données, le panneau, le SQL et les vues, est du Python simple et
> tourne partout, mais tu ne pourras pas enregistrer une partie sous Linux
> ou macOS.

---

## Les quatre étapes

Le panneau te les donne dans l'ordre et te dit où tu en es.

### 0 · Préparer le mod

N'apparaît que s'il manque quelque chose. Un bouton : il trouve Catan en
demandant à Steam, vérifie s'il est en 32 ou 64 bits, télécharge ce qu'il
faut, **vérifie l'empreinte SHA-256** avant de toucher à quoi que ce soit, et
le laisse **éteint**.

### 1 · Jouer

**Allumer le mod** → ouvrir Catan → jouer ce que tu veux → **Arrêter et
éteindre le mod**.

L'ordre compte : le mod se charge au démarrage du jeu, donc allume-le *avant*
d'ouvrir Catan. Tu peux enchaîner plusieurs parties sans rien toucher.

### 2 · Enregistrer dans la base

Un autre bouton. Appuie autant de fois que tu veux : les parties déjà
enregistrées ne sont pas dupliquées.

La première fois que quelqu'un de nouveau joue, il apparaît sous un nom
provisoire (`player_4645eb8a`). Donne-lui son vrai nom avec **Nommer
quelqu'un** et les parties déjà enregistrées sont corrigées aussi.

### 3 · Regarder les données

En haut, **les titres** : des conclusions déjà rédigées, qui gagne le plus,
qui sort le 7 plus souvent qu'il ne devrait, qui choisit les meilleures
tuiles, chacune avec le chiffre derrière et un lien vers la table d'où elle
vient. Pas un seul nom n'est écrit en dur : ils sortent des mêmes requêtes que
celles qui dessinent les tables, ils sont recalculés à chaque visite, et
seules les personnes avec 10 parties ou plus y entrent, pour que ce ne soit
pas gagné par quelqu'un qui a joué une fois et a eu un bon jour.

![Les titres du panneau : des conclusions déjà rédigées, chacune avec son chiffre](docs/titulares.png)

En dessous, les **records** : la meilleure marque sur une seule partie, et de
quelle partie il s'agit. Là il n'y a pas de minimum : un titre est une
habitude et demande des parties derrière, un record est d'un jour.

![Records sur une seule partie, en mode sombre](docs/records.png)

*Le panneau démarre en clair ou en sombre selon ce que préfère ton système,
et il y a un bouton pour basculer quand tu veux.*

Et deux filtres qui se combinent : **avec qui tu as joué**, par défaut
seulement les parties contre des personnes, parce que l'IA ne propose pas
d'échanges et ne bloque pas de la même façon, et **la taille de la table**,
parce qu'une partie à 5 ou 6 a 30 tuiles au lieu de 19 et se joue en 12 points
au lieu de 10. Les mélanger ne rend pas la moyenne un peu sale : ça la rend
vide de sens.

Ensuite 32 tables. Le tableau des scores, la chance de chacun aux dés, le
voleur, les échanges, les cartes développement, les numéros de chaque
tuile… Et une boîte où tu tapes la question en langage courant :

```
qui a eu le plus de chance ?
combien de chevaliers a joué Pedro ?
qui pose le voleur sur qui ?
```

Si la réponse n'est dans aucune table, il **le dit** au lieu d'en inventer
une.

Ce que veut dire exactement chaque colonne, et ce qu'une ligne représente dans
chaque table, est expliqué une par une, en français, dans
[idiomas/catalogFR.py](idiomas/catalogFR.py). Cherche l'en-tête que tu
vois sur la table et il est là sous ce même nom. Plus de détails dans [le
catalogue](#envie-de-regarder-dedans), plus bas.

---

## Ce qu'il enregistre, et ce qu'il n'enregistre pas

Il enregistre **seulement ce que tout le monde à la table peut voir** :
constructions, jets de dés, échanges, le voleur, qui vole qui, ce que chacun
produit.

**Jamais** la main de personne, jamais les points de victoire cachés des
cartes développement, jamais quelle carte un vol a prise, jamais ce que
quelqu'un défausse sur un 7. Ce n'est pas que ça n'est pas enregistré : ça
n'est **jamais lu**, et des tests le vérifient.

Une partie occupe quelques Ko. Pas une seule capture d'écran n'est stockée.

**Tes données sont à toi et elles ne quittent jamais ta machine.** La base
(`catan_stats.db`) est créée dans le dossier du projet et n'est envoyée nulle
part. Ce dépôt ne contient pas une seule partie de qui que ce soit : tu pars
d'une base vide et tu la remplis en jouant.

---

## À lire avant d'allumer le mod

Le mod modifie le client de Catan Universe, et **les conditions d'utilisation
du jeu ne le permettent pas**. Le fait qu'il ne lise que de l'information
publique n'y change rien.

Il se charge dans **toutes** les parties tant qu'il est allumé, y compris les
parties en ligne avec d'autres personnes. C'est pour ça que l'interrupteur :

- part **éteint** et ne s'allume jamais tout seul,
- est allumé par toi, en connaissance de cause,
- et le panneau met un bandeau rouge en haut de l'écran tout le temps qu'il
  est allumé, pour que tu n'oublies pas de l'éteindre.

La décision est la tienne, et le risque aussi.

---

## Si quelque chose ne marche pas

| | |
|---|---|
| `py` n'est pas reconnu | installe Python depuis python.org et coche « Add to PATH » |
| Il ne trouve pas Catan | ouvre Steam une fois et recharge la page |
| Le mod n'enregistre rien | tu l'as allumé **avant** d'ouvrir Catan ? |
| Le panneau ne répond pas | la fenêtre noire a été fermée ; rouvre-la |
| Un bandeau rouge dit que le panneau n'est plus à jour | ferme la fenêtre noire et rouvre-la |

---

## Comment savoir s'il te dit la vérité

C'est un projet sur les données, donc la question compte :

```powershell
py db/pruebas.py
```

**Trois cents vérifications** contre tes propres parties : que le total et
chaque partie séparément disent la même chose, que les vols faits
correspondent aux vols subis, que personne n'a un score impossible, que la
production déduite du plateau correspond à ce qui a été enregistré.

Le chiffre exact n'est délibérément pas promis : il monte à chaque partie que
tu joues, parce qu'une bonne partie des vérifications tourne une fois par
partie. Le tien s'affiche à la fin de l'exécution.

Et la base est ouverte **en lecture seule** depuis le panneau et depuis les
requêtes. La seule chose qui supprime quoi que ce soit est le bouton qui
retire une partie, et il fait une copie avant.

---

## Envie de regarder dedans

C'est du SQL, sans rien de caché :

```powershell
py sql.py "SELECT * FROM amigos_marcador"
py sql.py --tablas
```

Et le catalogue complet, les **32 vues** groupées, ce à quoi chacune répond,
ce que veut dire chaque colonne et un exemple de chaque table, s'écrit tout
seul avec :

```powershell
py db/catalogo.py
```

Ça te laisse un `VISTAS.md` d'une cinquantaine de pages. **Il n'est pas dans
le dépôt et il n'est pas écrit à la main** : il est généré à partir de
[db/columnas.py](db/columnas.py), qui est le seul endroit où chaque colonne
est expliquée, et un test vérifie que le fichier généré est à jour. Le jour où
une vue change et que le `.md` ne change pas, le test le dit.

**En français, chaque colonne est dans
[idiomas/catalogFR.py](idiomas/catalogFR.py).** La même chose que dit le
catalogue, écrite entièrement en français, noms de vue et de colonne compris,
parce que qui l'ouvre lit déjà tout en français. C'est la référence : quand un
en-tête de table ne t'en dit pas assez, c'est là que tu le cherches. Les
en-têtes du panneau et ce fichier utilisent les mêmes mots exprès, donc `rang`
à l'écran est `rang` dans le fichier.

> Le catalogue qu'écrit `py db/catalogo.py` sort encore en espagnol. Le
> panneau, non : il a un menu déroulant **FR**, à côté du bouton clair/sombre.

## Licence

MIT. Voir [LICENSE](LICENSE).
