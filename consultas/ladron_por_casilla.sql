-- Que casillas te ha estado bloqueando el ladron, y cuanto te ha costado.
--
--   python sql.py -f consultas\ladron_por_casilla.sql
--
-- Cambia el nombre de la ultima linea por el de otro jugador para verlo suyo.
SELECT COALESCE(p.person_name, p.name) AS quien,
       t.number   AS numero,
       t.resource AS terreno,
       COUNT(*)      AS veces,
       SUM(b.amount) AS sin_recolectar
FROM robber_blocks b
JOIN players p ON p.player_id = b.victim_id
JOIN tiles   t ON t.tile_id   = b.tile_id
WHERE COALESCE(p.person_name, p.name) = 'PON_AQUI_UN_NOMBRE'
GROUP BY quien, t.number, t.resource
ORDER BY sin_recolectar DESC;
