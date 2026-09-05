-- ============================================================
-- Catan Universe Stats Tracker - Esquema de Base de Datos
-- ============================================================

PRAGMA foreign_keys = ON;

-- Una partida completa
CREATE TABLE IF NOT EXISTS games (
    game_id     INTEGER PRIMARY KEY AUTOINCREMENT,
    started_at  TEXT NOT NULL,          -- ISO timestamp
    ended_at    TEXT,
    winner      TEXT,                   -- leido de la pantalla final (vision/results.py)
    notes       TEXT,
    -- De donde salieron los datos. 'mod' = los apunto el plugin leyendo el
    -- estado del juego, o sea que no tienen error; NULL o 'vision' = los
    -- leyo el tracker de la pantalla, con lo que eso implica. Importa
    -- separarlas: si se juega con las dos cosas encendidas, la MISMA partida
    -- esta dos veces, y mezclarlas al analizar contaria todo por duplicado.
    source      TEXT
);

-- Identidad estable de cada persona/bot real, para poder comparar entre
-- partidas. El propio alias es la clave primaria (asumimos que no se
-- repite entre personas distintas ni cambia de nombre).
CREATE TABLE IF NOT EXISTS people (
    display_name TEXT PRIMARY KEY
);

-- Jugadores dentro de una partida concreta (mismo humano puede
-- jugar como "Busi" en varias partidas -> se resuelve por person_name)
CREATE TABLE IF NOT EXISTS players (
    player_id     INTEGER PRIMARY KEY AUTOINCREMENT,
    game_id       INTEGER NOT NULL REFERENCES games(game_id),
    person_name   TEXT REFERENCES people(display_name),
    name          TEXT NOT NULL,          -- nombre tal cual aparece en el log
    color         TEXT,                   -- color detectado en la UI (para vision)
    -- Matiz/saturación/brillo MEDIDOS en la bandera, no el centro del rango
    -- de la etiqueta. Importa: el dorado real está en matiz 18 y el trigo
    -- también, así que buscar piezas con el centro de la etiqueta (19) en vez
    -- del color medido tira margen que no sobra (ver main._colores_bgr_de_jugadores).
    color_h       REAL,
    color_s       REAL,
    color_v       REAL,
    is_bot        INTEGER DEFAULT 0,
    turn_order    INTEGER,                -- orden de turno en esa partida
    final_rank    INTEGER,                -- posición final (1=ganador), leída de la pantalla de resultados
    final_points  INTEGER                 -- puntos de victoria finales, misma fuente
);

-- Las 19 casillas del tablero, calibradas una vez por partida
CREATE TABLE IF NOT EXISTS tiles (
    tile_id     INTEGER PRIMARY KEY AUTOINCREMENT,
    game_id     INTEGER NOT NULL REFERENCES games(game_id),
    axial_q     INTEGER,                -- coordenadas axiales del hex (opcional)
    axial_r     INTEGER,
    resource    TEXT,                   -- Madera, Arcilla, Lana, Cereales, Mineral, Desierto
    number      INTEGER,                -- 2-12, NULL si es desierto
    screen_x    INTEGER,                -- posición en pantalla al calibrar (debug/reuso)
    screen_y    INTEGER
);

-- Poblados / ciudades construidos, con las casillas que tocan
CREATE TABLE IF NOT EXISTS buildings (
    building_id INTEGER PRIMARY KEY AUTOINCREMENT,
    game_id     INTEGER NOT NULL REFERENCES games(game_id),
    player_id   INTEGER NOT NULL REFERENCES players(player_id),
    type        TEXT NOT NULL CHECK(type IN ('poblado','ciudad','carretera')),
    turn_number INTEGER,
    timestamp   TEXT,
    screen_x    INTEGER,
    screen_y    INTEGER,
    -- En qué vértice está, con un nombre que no depende de dónde esté el
    -- tablero en pantalla (ver _clave_de_vertice en main.py). Las casillas
    -- que toca no bastan para identificarlo: en las 6 puntas del tablero,
    -- los dos vértices de fuera no tocan ninguna otra casilla.
    vertex_key  TEXT
);

-- Relación N:M edificio <-> casillas que toca (2 o 3 por vértice)
CREATE TABLE IF NOT EXISTS building_tiles (
    building_id INTEGER NOT NULL REFERENCES buildings(building_id),
    tile_id     INTEGER NOT NULL REFERENCES tiles(tile_id),
    PRIMARY KEY (building_id, tile_id)
);

-- Carreteras vistas en el tablero por visión.
--
-- Van aparte de `buildings` porque lo que identifica una carretera no es un
-- vértice sino una ARISTA (el borde entre dos casillas), y con la clave de
-- `building_tiles` una carretera entre las casillas A y B y un poblado en un
-- vértice que toca A y B tendrían la misma clave y se pisarían.
--
-- `edge_key` identifica la arista sin depender de dónde esté el tablero en
-- pantalla: se arma con las casillas que toca la arista y las que tocan sus
-- dos extremos. Eso sobrevive a que el tablero se mueva o se haga zoom (que
-- pasa constantemente, ver main._reanclar_si_toca), a diferencia de guardar
-- unas coordenadas que quedarían obsoletas al primer desplazamiento.
--
-- UNIQUE(game_id, edge_key): una arista sostiene UNA carretera, de un solo
-- jugador. Es una regla del juego, igual que un vértice sostiene un solo
-- edificio.
CREATE TABLE IF NOT EXISTS roads (
    road_id     INTEGER PRIMARY KEY AUTOINCREMENT,
    game_id     INTEGER NOT NULL REFERENCES games(game_id),
    player_id   INTEGER NOT NULL REFERENCES players(player_id),
    edge_key    TEXT NOT NULL,
    turn_number INTEGER,
    timestamp   TEXT,
    UNIQUE (game_id, edge_key)
);

-- Cada tirada de dados
CREATE TABLE IF NOT EXISTS rolls (
    roll_id     INTEGER PRIMARY KEY AUTOINCREMENT,
    game_id     INTEGER NOT NULL REFERENCES games(game_id),
    player_id   INTEGER NOT NULL REFERENCES players(player_id),  -- quien tira
    turn_number INTEGER,
    value       INTEGER NOT NULL,       -- 2-12, la suma: es lo que cuenta para producir
    die1        INTEGER,                -- cada dado por separado, cuando se han podido leer
    die2        INTEGER,                -- (NULL si la tirada vino del texto del registro)
    timestamp   TEXT
);

-- Cómo leyó el OCR un nombre -> el nombre real. Los garabatos del OCR NO
-- son aleatorios: misma fuente, mismo renderizado y mismo tamaño producen
-- una y otra vez el mismo error ("Louis" leído como "Levís"). Así que uno
-- confirmado por una vía fiable sirve para siempre, también en partidas
-- futuras. Sin game_id a propósito: es conocimiento sobre la LECTURA, no
-- sobre una partida.
CREATE TABLE IF NOT EXISTS name_aliases (
    alias      TEXT PRIMARY KEY,       -- el texto leído, en minúsculas
    canonical  TEXT NOT NULL,          -- el nombre real
    seen_count INTEGER NOT NULL DEFAULT 1,
    last_seen  TEXT
);

-- Recursos ganados (producción, inicial, robo recibido...)
CREATE TABLE IF NOT EXISTS resource_gains (
    gain_id     INTEGER PRIMARY KEY AUTOINCREMENT,
    game_id     INTEGER NOT NULL REFERENCES games(game_id),
    player_id   INTEGER NOT NULL REFERENCES players(player_id),
    roll_id     INTEGER REFERENCES rolls(roll_id),  -- NULL si no viene de una tirada
    resource    TEXT NOT NULL,
    amount      INTEGER NOT NULL,
    source      TEXT CHECK(source IN ('inicial','produccion','robo','descarte','monopolio','otro')),
    timestamp   TEXT
);

-- Movimientos del ladrón (incluye la casilla destino via vision)
CREATE TABLE IF NOT EXISTS robber_moves (
    move_id     INTEGER PRIMARY KEY AUTOINCREMENT,
    game_id     INTEGER NOT NULL REFERENCES games(game_id),
    player_id   INTEGER NOT NULL REFERENCES players(player_id),  -- quien lo mueve
    tile_id     INTEGER REFERENCES tiles(tile_id),                -- destino (via vision)
    turn_number INTEGER,
    timestamp   TEXT
);

-- Veces que el ladrón de un jugador le ha bloqueado la producción a otro:
-- sale cuando la tirada coincide con el número de la casilla ocupada por
-- el ladrón (ver compute_production, que ya excluye esa casilla). Esto SÍ
-- es un hecho verificable con los datos rastreados, a diferencia de qué
-- recurso se llevó un robo de cartas entre dos rivales (eso solo se puede
-- estimar, ver steals.resource_probs_json).
CREATE TABLE IF NOT EXISTS robber_blocks (
    block_id      INTEGER PRIMARY KEY AUTOINCREMENT,
    game_id       INTEGER NOT NULL REFERENCES games(game_id),
    roll_id       INTEGER NOT NULL REFERENCES rolls(roll_id),
    tile_id       INTEGER NOT NULL REFERENCES tiles(tile_id),
    blocker_id    INTEGER REFERENCES players(player_id),  -- quien puso el ladrón ahí (NULL si no se sabe)
    victim_id     INTEGER NOT NULL REFERENCES players(player_id),
    building_type TEXT,   -- poblado/ciudad
    amount        INTEGER NOT NULL,  -- recursos perdidos: 1 poblado, 2 ciudad
    timestamp     TEXT
);

-- Robos de cartas entre jugadores
CREATE TABLE IF NOT EXISTS steals (
    steal_id    INTEGER PRIMARY KEY AUTOINCREMENT,
    game_id     INTEGER NOT NULL REFERENCES games(game_id),
    move_id     INTEGER REFERENCES robber_moves(move_id),
    thief_id    INTEGER NOT NULL REFERENCES players(player_id),
    victim_id   INTEGER NOT NULL REFERENCES players(player_id),
    resource    TEXT,                   -- normalmente desconocido salvo que seas tú
    resource_probs_json TEXT,           -- estimación por la mano rastreada de la víctima, ej. {"Mineral":0.25,"Lana":0.75}
    timestamp   TEXT
);

-- Intercambios entre jugadores
CREATE TABLE IF NOT EXISTS trades (
    trade_id    INTEGER PRIMARY KEY AUTOINCREMENT,
    game_id     INTEGER NOT NULL REFERENCES games(game_id),
    player_a_id INTEGER NOT NULL REFERENCES players(player_id),
    player_b_id INTEGER REFERENCES players(player_id),  -- NULL = intercambio con el banco
    gave_json   TEXT,   -- ej. [{"resource":"Cereales","amount":1}]
    received_json TEXT,
    timestamp   TEXT
);

-- Cartas de desarrollo: compra
CREATE TABLE IF NOT EXISTS dev_card_purchases (
    purchase_id INTEGER PRIMARY KEY AUTOINCREMENT,
    game_id     INTEGER NOT NULL REFERENCES games(game_id),
    player_id   INTEGER NOT NULL REFERENCES players(player_id),
    turn_number INTEGER,
    timestamp   TEXT
);

-- Cartas de desarrollo: uso (Caballero, Monopolio, Invención, etc.)
CREATE TABLE IF NOT EXISTS dev_card_plays (
    play_id     INTEGER PRIMARY KEY AUTOINCREMENT,
    game_id     INTEGER NOT NULL REFERENCES games(game_id),
    player_id   INTEGER NOT NULL REFERENCES players(player_id),
    card_type   TEXT,    -- Caballero, Monopolio, Invencion, Construccion de carreteras, Punto de Victoria
    turn_number INTEGER,
    timestamp   TEXT
);

-- Turnos, útil para ordenar todo cronológicamente por ronda
CREATE TABLE IF NOT EXISTS turns (
    turn_id     INTEGER PRIMARY KEY AUTOINCREMENT,
    game_id     INTEGER NOT NULL REFERENCES games(game_id),
    player_id   INTEGER NOT NULL REFERENCES players(player_id),
    turn_number INTEGER,
    phase       TEXT CHECK(phase IN ('setup','normal')),
    start_ts    TEXT,
    end_ts      TEXT
);

-- ============================================================
-- Índices para las consultas y joins más habituales.
-- ============================================================
CREATE INDEX IF NOT EXISTS idx_players_game_name ON players(game_id, name);
CREATE INDEX IF NOT EXISTS idx_players_person ON players(person_name);
CREATE INDEX IF NOT EXISTS idx_tiles_game ON tiles(game_id);
CREATE INDEX IF NOT EXISTS idx_buildings_player ON buildings(player_id);
CREATE INDEX IF NOT EXISTS idx_buildings_game ON buildings(game_id);
CREATE INDEX IF NOT EXISTS idx_rolls_player ON rolls(player_id);
CREATE INDEX IF NOT EXISTS idx_rolls_game ON rolls(game_id);
CREATE INDEX IF NOT EXISTS idx_resource_gains_player ON resource_gains(player_id);
CREATE INDEX IF NOT EXISTS idx_robber_moves_tile ON robber_moves(tile_id);
CREATE INDEX IF NOT EXISTS idx_steals_thief ON steals(thief_id);
CREATE INDEX IF NOT EXISTS idx_steals_victim ON steals(victim_id);
CREATE INDEX IF NOT EXISTS idx_trades_a ON trades(player_a_id);
CREATE INDEX IF NOT EXISTS idx_trades_b ON trades(player_b_id);
CREATE INDEX IF NOT EXISTS idx_dev_purchases_player ON dev_card_purchases(player_id);
CREATE INDEX IF NOT EXISTS idx_dev_plays_player ON dev_card_plays(player_id);
CREATE INDEX IF NOT EXISTS idx_turns_game_number ON turns(game_id, turn_number);

-- ============================================================
-- Vista de ejemplo: la pregunta que motivó todo esto ->
-- "¿Qué números toca cada jugador y con qué frecuencia salieron?"
--
-- OJO: esta y `v_player_turn_order` son las dos primeras vistas del
-- proyecto, y las de `db/vistas.py` las han alcanzado -- `amigos_numeros`
-- contesta lo mismo y de más (cuántas veces salió el número, cuánto cobró y
-- cuánto debería haber salido), y `jugadores.salida` sustituye a la del
-- orden de turno.
--
-- Se quedan porque funcionan y están documentadas, pero dos consultas que
-- contestan lo mismo son dos que un día pueden decir cosas distintas. Por eso
-- `db/pruebas.py` comprueba que sigan coincidiendo: si alguna vez dejan de
-- hacerlo, salta ahí y no en la cara de quien mire una tabla.
-- ============================================================
CREATE VIEW IF NOT EXISTS v_player_number_exposure AS
SELECT
    p.game_id,
    p.name          AS player_name,
    t.number,
    COUNT(DISTINCT bt.building_id) AS buildings_on_number,
    -- probabilidad teórica de ese número por tirada (combinaciones de 2d6 / 36)
    CASE t.number
        WHEN 2 THEN 1  WHEN 12 THEN 1
        WHEN 3 THEN 2  WHEN 11 THEN 2
        WHEN 4 THEN 3  WHEN 10 THEN 3
        WHEN 5 THEN 4  WHEN 9  THEN 4
        WHEN 6 THEN 5  WHEN 8  THEN 5
        WHEN 7 THEN 6
        ELSE 0
    END AS theoretical_pips
FROM players p
JOIN buildings b ON b.player_id = p.player_id
JOIN building_tiles bt ON bt.building_id = b.building_id
JOIN tiles t ON t.tile_id = bt.tile_id
WHERE t.number IS NOT NULL
GROUP BY p.game_id, p.name, t.number;

-- ============================================================
-- Vista: ¿en qué posición de turno suele empezar cada jugador?
-- ============================================================
CREATE VIEW IF NOT EXISTS v_player_turn_order AS
SELECT
    name        AS player_name,
    turn_order,
    COUNT(*)    AS veces
FROM players
WHERE turn_order IS NOT NULL
GROUP BY name, turn_order
ORDER BY name, turn_order;
