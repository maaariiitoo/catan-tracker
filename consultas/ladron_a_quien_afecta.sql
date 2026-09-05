-- A quien le ha costado mas el ladron, en recursos que dejo de recibir.
--
--   python sql.py -f consultas\ladron_a_quien_afecta.sql
--
-- 'perdido' son recursos que NO se produjeron porque el ladron estaba encima
-- de una casilla suya cuando salio ese numero. No son robos de la mano: eso
-- es la tabla `steals`, y ahi el mod no apunta que carta se llevaron.
--
-- 'cobrado' es lo que el tablero si le dio: tiradas mas colocacion inicial.
-- Sin comercios ni robos, que el mod no lee las manos de nadie.
--
-- Se ordena por el PORCENTAJE y no por el bruto a proposito: al que mas
-- produce le bloquean mas sin que le duela igual.
WITH persona AS (
    SELECT player_id, COALESCE(person_name, name) AS quien FROM players
),
bloqueado AS (
    SELECT pe.quien, COUNT(*) AS veces, SUM(b.amount) AS perdido
    FROM robber_blocks b
    JOIN persona pe ON pe.player_id = b.victim_id
    GROUP BY pe.quien
),
producido AS (
    SELECT pe.quien, SUM(g.amount) AS cobrado
    FROM resource_gains g
    JOIN persona pe ON pe.player_id = g.player_id
    WHERE g.source = 'produccion'
    GROUP BY pe.quien
)
SELECT b.quien,
       b.veces,
       b.perdido,
       COALESCE(pr.cobrado, 0) AS cobrado,
       ROUND(100.0 * b.perdido / (b.perdido + COALESCE(pr.cobrado, 0)), 1)
           AS pct_robado
FROM bloqueado b
LEFT JOIN producido pr ON pr.quien = b.quien
ORDER BY pct_robado DESC;
