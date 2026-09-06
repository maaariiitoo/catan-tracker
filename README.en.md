*[Léeme en castellano](README.md) · [Lisez-moi en français](README.fr.md).*

# Catan Tracker

Your **Catan Universe** games, recorded on their own and turned into stats:
who wins, whose dice are actually bad, where each person puts the robber, who
trades with whom and who comes out ahead.

Nothing gets typed by hand. You play, you press a button, and it's in.

---

## Getting started

You need **Python 3.7 or newer** and **Catan Universe** on Steam. Nothing else.

```powershell
py panel.py --simple
```

A page opens in your browser. Everything happens there, with buttons.

> `py` is not a typo: it's the Windows Python launcher, and it works even when
> `python` isn't on your PATH. If you get an error, that's usually why.

**There are no dependencies to install.** `requirements.txt` is empty on
purpose: this runs on the Python standard library and nothing else. There is
no `pip install` that can fail on you.

> **Windows only.** The mod hooks into the game through `winhttp.dll`, which
> is a Windows mechanism, and Catan Universe itself is a Windows game. The
> half that reads the data (the panel, the SQL, the views) is plain Python
> and runs anywhere, but you won't be able to record a game on Linux or macOS.

---

## The four steps

The panel gives them to you in order and tells you which one you're on.

### 0 · Get the mod ready

Only shows up if something is missing. One button: it finds Catan by asking
Steam, checks whether it's 32- or 64-bit, downloads what's needed, **verifies
the SHA-256 fingerprint** before touching anything, and leaves it **switched
off**.

### 1 · Play

**Switch the mod on** → open Catan → play whatever you like → **Stop and
switch the mod off**.

Order matters: the mod loads when the game starts, so switch it on *before*
opening Catan. You can play several games in a row without touching anything.

### 2 · Save to the database

Another button. Press it as often as you like: games already saved don't get
duplicated.

The first time someone new plays, they show up under a placeholder name
(`player_4645eb8a`). Give them their real one with **Name someone** and the
games already saved get fixed too.

### 3 · Look at the data

At the top, **the headlines**: conclusions already written out: who wins
most, who gets the 7 more often than they should, who picks the best tiles,
each with the number behind it and a link to the table it came from. Not one
name is hardcoded: they come from the same queries that draw the tables, they
are recomputed on every visit, and only people with 10 games or more get in,
so it isn't won by someone who played once and had a good day.

![The panel's headlines: conclusions already written, each with its number](docs/titulares.png)

Below that, the **records**: the best single-game mark, and which game it was.
No minimum there: a headline is a habit and needs games behind it; a record
is one good day.

![Single-game records, in dark mode](docs/records.png)

*The panel starts in light or dark depending on what your system prefers, and
there's a button to switch whenever you want.*

And two filters that combine: **who you played with** (by default only games
against people, because the AI doesn't propose trades or block the same way)
and **how big the table was**, because a 5–6 player game has 30 tiles instead
of 19 and is played to 12 points instead of 10. Mixing them doesn't make the
average slightly dirty: it makes it meaningless.

Then 32 tables. The scoreboard, everyone's dice luck, the robber, trades,
development cards, the numbers on each tile… And a box where you type the
question in plain language:

```
who has had the most luck?
how many knights has Pedro played?
who puts the robber on whom?
```

If the answer isn't in any table, it **says so** instead of making one up.

What each column means exactly, and what one row represents in each table, is
explained one by one, in English, in
[idiomas/catalogEN.py](idiomas/catalogEN.py). Look up the heading you see on
the table and it's there under that same name. More about it in [the
catalogue](#want-to-look-inside), further down.

---

## What it records, and what it doesn't

It records **only what everyone at the table can see**: buildings, dice rolls,
trades, the robber, who steals from whom, what each person produces.

**Never** anyone's hand, never the hidden victory points on development cards,
never which card a steal took, never what anyone discards on a 7. It isn't
that those aren't saved: they are **never even read**, and there are tests
that check it.

One game takes up a few KB. Not a single screenshot is stored.

**Your data is yours and it never leaves your machine.** The database
(`catan_stats.db`) is created in the project folder and isn't uploaded
anywhere. This repository doesn't ship a single game from anyone: you start
with an empty database and fill it by playing.

---

## Read this before switching the mod on

The mod modifies the Catan Universe client, and **the game's terms of use
don't allow that**. The fact that it only reads public information doesn't
change it.

It loads in **every** game while it's switched on, online games with other
people included. Which is why the switch:

- ships **off** and never turns itself on,
- is turned on by you, knowingly,
- and the panel puts a red band across the top of the screen the whole time
  it's on, so you don't forget to turn it off.

The decision is yours and so is the risk.

---

## If something doesn't work

| | |
|---|---|
| `py` is not recognised | install Python from python.org and tick «Add to PATH» |
| It can't find Catan | open Steam once and reload the page |
| The mod records nothing | did you switch it on **before** opening Catan? |
| The panel doesn't respond | the black window was closed; open it again |
| A red band says the panel is out of date | close the black window and open it again |

---

## How to know whether it's telling you the truth

This is a project about data, so the question matters:

```powershell
py db/pruebas.py
```

**Three hundred checks** against your own games: that the total and each
individual game say the same thing, that steals made reconcile with steals
suffered, that nobody has an impossible score, that the production deduced
from the board matches what was recorded.

The exact number is deliberately not promised: it goes up with every game you
play, because a good share of the checks run once per game. Yours is printed
at the end of the run.

And the database is opened **read-only** from the panel and from the queries.
The only thing that deletes anything is the button that removes a game, and it
makes a backup first.

---

## Want to look inside

It's all SQL, with nothing hidden:

```powershell
py sql.py "SELECT * FROM amigos_marcador"
py sql.py --tablas
```

And the full catalogue (the **32 views** grouped, what each one answers, what
each column means and a sample of every table) writes itself with:

```powershell
py db/catalogo.py
```

That leaves you a `VISTAS.md` of about fifty pages. **It isn't in the
repository and it isn't written by hand**: it's generated from
[db/columnas.py](db/columnas.py), which is the single place where each column
is explained, and a test checks that the generated file is up to date. The day
a view changes and the `.md` doesn't, the test says so.

**In English, every column is in
[idiomas/catalogEN.py](idiomas/catalogEN.py).** The same thing the catalogue
says, written in English throughout, the view and column names included,
because whoever opens it is already reading in English. It's the reference:
when a heading on a table doesn't tell you enough, that's where you look it
up. The panel's headings and that file use the same words on purpose, so
`rank` on the screen is `rank` in the file.

> The catalogue that `py db/catalogo.py` writes still comes out in Spanish.
> The panel does not: it has a language dropdown next to the light/dark
> button, with English and French in it.

## Licence

MIT. See [LICENSE](LICENSE).
