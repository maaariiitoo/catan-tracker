"""What each column of each view means. The one place where it's said.

    py db/catalog.py            writes VIEWS.md with all of this inside
    py db/catalog.py --missing  which columns aren't explained yet

WHY THIS IS IN A .py FILE AND NOT IN THE MARKDOWN. This used to live inside
PROJECT.md, which is where it was originally written. It was pulled out here
on September 2, 2026, when `VIEWS.md` was created: as soon as two files
explain the same columns, sooner or later they say different things --
which is exactly the bug that got fixed that same day with `cost_them`,
which meant two different things in two different views. Here the text
exists once, `VIEWS.md` is generated from it, and a test checks that the
generated file is up to date.

And that's how the machine can check it: `db/tests.py` requires that every
column the database returns is explained here, and that nothing explained
here no longer exists. A `.md` file can't do that.
"""

# Columns that show up in several views and mean the same thing in all of
# them. The list of which ones repeat -- and why -- is in `views.SHARED`.
SHARED = {
    "who"               : "the person, already resolved to a name. It's the same person across games even if they change color or seat",
    "to_whom"           : "the other person in the pair: the one on the receiving end of what this row is about",
    "with_whom"         : "the other person in the pair. `the bank` isn't a person: it's trading with the bank or through a port",
    "game"              : "the game number",
    "game_id"           : "the game number",
    "player_id"         : "this person's internal number **in that game**. It's not the person: the same person has a different one in each game",
    "day"               : "the day it was played",
    "hour"              : "what time it started",
    "turn"              : "which turn it happened on. Turn **0** is the initial setup",
    "rank"              : "what rank they finished in. 1 means they won",
    "points"            : "how many points they finished with",
    "color"             : "which color they played that game",
    "start_order"       : "turn order: 1 is whoever starts",
    "number"            : "the tile's number, from 2 to 12",
    "resource"          : "wood, brick, wool, grain, or ore",
    "produced"          : "cards that came in from PRODUCTION: what the board paid out when its number rolled. No trades, no monopolies, and not counting the initial setup -- that's what `from_setup` is for. Confirmed that the three views carrying this give the same number",
    "robber_put_on_them": "times **someone else** moved the robber onto one of their tiles. This is what people remember, and it's more than double the next one. Putting it there yourself doesn't count here -- if you put it there, nobody 'put it on you' -- and it shows up in \"The robber, pair by pair\", in the row where the same person appears in both columns",
    "with_friends"      : "1 if all four were people; 0 if there were bots",
}


# And the columns specific to each view, in the order they appear.
BY_VIEW = {
    "games": {
        "winner"      : "who won",
        "player_count": "how many were playing",
        "target_points": "how many points the game was played to: **10 for base Catan, 12 for the 5-6 player expansion**. It isn't stored anywhere directly because it doesn't need to be: you can tell from how many were playing",
        "board_tiles" : "how many tiles the board had: **19 for the base game, 30 for the 5-6 player one**. It's the fastest way to see which games used the big board",
        "bots"        : "how many of the players were the computer",
        "rolls"       : "how many times the dice were rolled in that game",
        "minutes"     : "minutes between the start and the end of the game. **Empty** if it has no recorded end: either it was abandoned, or it's still being played right now",
        "issues"      : "whatever went wrong when importing it, if anything did -- or actions the parser doesn't understand, if you played an expansion. Empty is normal. This lives in the table instead of a log because **it changes what the other rows say**: game 11 has its production counted as if there were no robber, and without this column that's invisible -- it looks like a perfectly believable game",
    },
    "players": {
        "is_bot"       : "1 if it's the computer",
        "player_count" : "how many were playing that game",
        "target_points": "how many points the game was played to (10 or 12)",
    },
    "friends_scoreboard": {
        "games_played": "how many they've played **at tables of that size**",
        "table_size"  : "how many were playing. This is what splits the table into blocks",
        "wins"        : "how many of those they won",
        "avg_points"  : "average points they finish with",
        "played_to"   : "how many points the game was played to: 10 up to four players, 12 with five or six. It sits next to `avg_points` because you can't read that column without it: 9 points at a table of six is much further from winning than 9 at a table of four",
        "avg_rank"    : "average finishing rank. Lower is better",
        "best_points" : "their best score at that table size",
    },
    "friends_points": {
        "settlements"        : "settlements they had at the end. Each is **1 point**",
        "cities"             : "cities at the end. Each is **2 points**",
        "longest_road"       : "1 if they held longest road. That's **2 points**",
        "largest_army"       : "1 if they held largest army. That's **2 points**",
        "victory_point_cards": "points they had hidden away in cards. **This comes out by subtraction**, not by reading the cards: final points minus settlements, cities, and the two bonuses. Whatever's left over had to be victory point cards. Empty when one of those terms is missing and the subtraction can't be done",
    },
    "friends_pace": {
        "third_settlement": "the turn of their **third** settlement, which is the first one they actually built during play: the first two go down before the game starts and both land on turn 0, so they don't say anything about anyone. It's called by the number it is rather than 'first' so it isn't confused with those two",
        "first_city"      : "the turn they upgraded their first settlement to a city",
        "first_dev_card"  : "the turn they bought their first development card",
        "first_knight"    : "the turn they played their first knight",
        "lasted_until"    : "the last turn of the game, so there's something to compare the others against",
    },
    "friends_start": {
        "ranks_gained": "`start_order` minus `rank`. Positive means they finished better than they started",
    },
    "friends_by_start": {
        "times"       : "how many times someone has started in that position",
        "wins"        : "how many of those times they won",
        "avg_rank"    : "average finishing rank for whoever starts there",
        "avg_points"  : "average points for whoever starts there",
        "ranks_gained": "average ranks gained or lost starting there",
    },
    "friends_start_by_player": {
        "games_played"  : "how many games they've played",
        "started_1st"   : "how many times they got to **start** first. Careful, this is the most commonly confused column in the whole table: it says where they STARTED, not where they finished. It used to be called `first` and got read backwards -- for where they finished, see `wins` in \"The scoreboard\" and the \"How each starting position finished\" table",
        "started_2nd"   : "how many times they started second",
        "started_3rd"   : "how many times they started third",
        "started_4th"   : "how many times they started fourth",
        "started_5th"   : "how many times they started fifth. Only at tables of 5 or 6",
        "started_6th"   : "how many times they started sixth. Only at tables of 6",
        "started_last"  : "how many times they started last, whatever the table size. A 4th out of four isn't the same as a 4th out of six, and in Catan starting last has a perk: you place two settlements in a row and choose last",
        "avg_start_order": "the average of their starting order. **Not something you sum**",
        "expected"      : "how many first starts they'd get by pure chance. It's added up as 1/players in that game, game by game, so a table of six doesn't skew the count for tables of four. Compared against `started_1st`, it shows whether the draw has been kind to them",
    },
    "friends_finish_from_start": {
        "times"      : "how many games they started in that position. It's the sum of the six columns next to it",
        "finished_1st": "of those times, how many they **finished** first -- in other words, won starting from that position",
        "finished_2nd": "how many they finished second",
        "finished_3rd": "how many they finished third",
        "finished_4th": "how many they finished fourth",
        "finished_5th": "how many they finished fifth. Only at tables of 5 or 6",
        "finished_6th": "how many they finished sixth. Only at tables of 6",
    },
    "friends_development": {
        "games_played" : "how many of their games are on record. It's here because without it the next column can't be compared: 61 cards over 12 games and 37 over 11 don't mean what they look like stacked one under the other",
        "bought"       : "development cards they bought, across all their games",
        "per_game"     : "development cards **per game**: `bought` divided by `games_played`. This is the one you can actually compare between people, because it doesn't reward whoever has played the most",
        "knight"       : "of those, how many were knights. A development card is hidden until it's played, so this only counts the ones they actually played -- the ones left in hand are in `unknown`",
        "year_of_plenty": "how many were Year of Plenty cards",
        "monopoly"     : "how many were Monopoly cards",
        "road_building": "how many were Road Building cards",
        "victory_point": "how many were Victory Point cards. These are never played, so they never show up on the table -- they come from subtracting everything visible (settlements, cities, and the two bonuses) from their final points",
        "unknown"      : "bought cards that were neither played nor victory points. They stayed in someone's hand and there's no way to know which ones they were",
    },
    "friends_deck": {
        "card"              : "the development card type: knight, victory point, monopoly, year of plenty, or road building",
        "drawn"             : "how many of those have been seen. The last rows **aren't card types**: they're cards that were bought and never played (still sitting in someone's hand), cards nobody ever bought and stayed in the deck, and -- only if it ever happens -- cards bought by someone outside the group. All together they add up to the whole deck: in a four-player game 10 were drawn, 4 were left in hand, 11 were never bought, and the deck had 25",
        "expected_draws"    : "how many of those **should have** been drawn. This comes from two things: how many cards were bought in total and what share of the deck this type is. If 10 cards were drawn and 56% of the deck is knights, you'd expect 5.6 knights. Read it against `drawn`, right next to it",
        "expected_percentage": "what share of the deck this card is, which is the share it's owed. 14 knights out of 25 is 56%; with 5 or 6 players it's 20 out of 35, 57.1%. It's named the same as in \"The rolls\" because it's the same idea with cards instead of dice: 70 against 56 means more knights came out than the deck actually contains",
        "percentage"        : "what share of all the cards seen this one was. **This is not the odds of drawing it** -- it's what actually happened. Of the 10 drawn, 7 were knights, i.e. 70%. Read it against `expected_percentage`",
    },
    "friends_monopolies": {
        "requested"  : "the resource they called. `unknown` if that recording didn't capture it",
        "total_taken": "cards they took in total. **NULL** means that recording didn't log it, not that they took nothing",
        "from_whom"  : "who lost how much, on one line: `Bruno 2, Carla 0`. The 0 shows up too, because 'had none' is still information. **Empty** for games before August 22, 2026, when the mod wasn't yet recording who paid what",
    },
    "friends_monopolies_to_whom": {
        "monopolies": "how many monopolies they threw at that person",
        "turns"     : "which turns it happened on. A pair can have several, so they're all listed in order: you can see whether it was a streak or whether someone's had it in for them from the start",
        "wood"      : "wood cards they took off them with those",
        "brick"     : "brick cards they took off them",
        "wool"      : "wool cards they took off them",
        "grain"     : "grain cards they took off them",
        "ore"       : "ore cards they took off them",
        "cards"     : "the total of the five columns next to it",
    },
    "friends_robber": {
        "stolen_from_them": "cards stolen from their hand when the robber landed next to them. One per steal: which card it was isn't recorded, that's hidden information",
        "times_blocked"   : "**times**, not cards: the times the number also came up and they missed out on payment. Almost half the time the robber just sits there and the number never comes up again, so it costs nothing. This can be higher than the count above: if it sits there and the number rolls three times, that's three blocks from a single placement",
        "lost"            : "**cards**, not times: what those blocks actually cost them. It's the same number as `lost_to_robber` in \"Production\". It doesn't match `times_blocked` because a city pays double -- a block on a settlement is 1 card, on a city it's 2",
        "wood"            : "of `lost`, how many were wood",
        "brick"           : "of `lost`, how many were brick",
        "wool"            : "of `lost`, how many were wool",
        "grain"           : "of `lost`, how many were grain",
        "ore"             : "of `lost`, how many were ore",
        "total"           : "**what the robber cost them altogether**: `lost` + `stolen_from_them`. It's the number people actually keep in their head, and the one that was missing -- 'I've lost 4' meant 4 from production and 6 stolen. It's called this instead of `cost_them` because that name is already taken in \"The robber, pair by pair\", where it's **only** the blocked resources",
    },
    "friends_robber_ratio": {
        "moves"             : "how many times **other people** moved the robber in their games. Everything next to it is measured against this, and it comes first for the same reason `rolls_counted` does in luck: a 116 and a 63 look comparable, but one comes from 197 moves and the other from 7",
        "robber_put_on_them": "of those moves, how many landed on them. It's the same number as in \"The robber\", and a test enforces that",
        "percentage"        : "`robber_put_on_them` divided by `moves`. **Nothing is discounted here**: having lots of tiles is also part of the game, and if all you want to know is who gets hit by the robber the most -- full stop -- this is your column. The only thing it filters out is what says nothing about anyone: how many games someone's played and how long they lasted",
        "expected"          : "how many they **should** have gotten, phrased as a count rather than a percentage so it reads at a glance against `robber_put_on_them` right next to it: 109 against 94.3 speaks for itself. It comes from splitting each move among the players by how many tiles each one had **at that moment**, giving proper credit for who actually got caught. Add the whole column up and you get exactly the total number of robber placements -- 352.9 against 353 -- and that's what makes the 100 next to it mean 100",
        "pile_on"           : "`robber_put_on_them` divided by `expected`, as a percentage. **This is the column that tells you whether people are piling on you**: 100 is what's expected, above that they're targeting you more than they should, below it they're leaving you alone. It's read the same way as `luck` in \"Everyone's luck\" on purpose, because it's the same shape -- what happened against what was owed. **The first version of this table compared against a blind robber and it was wrong**: against that baseline everyone came out above normal, which is impossible for a whole group. Measured: a robber placed on purpose catches 1.49 people per move versus 1.14 for a random one, 31% more. Of course everyone looked high -- the robber targets *someone* on purpose. With the current baseline some people are above and some below, which is how it should be",
    },
    "friends_robber_to_whom": {
        "placed_on_them" : "times they moved the robber onto a tile where the other person already had something. This is the intent. **If both people in the row are the same person, they put it on themselves**: it's legal and it happens -- sometimes a 7 just doesn't leave anywhere better, and sometimes it's deliberate, to rob from someone who shares that tile without handing the block to a rival",
        "with_7"         : "of those, how many were **forced** by rolling a 7",
        "with_knight"    : "of those, how many were **chosen**, by playing a knight",
        "blocked_them"   : "**times**, not cards: of those placements, how many also had the number come up so the other person missed a payment. This is the damage that actually landed, versus `placed_on_them`, which is only intent",
        "cost_them"      : "**cards**, not times: what the other person failed to collect from those blocks. It doesn't match `blocked_them` because a city pays double. Note: this is **only** the blocked cards -- what got stolen from their hand is separate, in `stole_from_them`",
        "wood"           : "of `cost_them`, how many were wood",
        "brick"          : "of `cost_them`, how many were brick",
        "wool"           : "of `cost_them`, how many were wool",
        "grain"          : "of `cost_them`, how many were grain",
        "ore"            : "of `cost_them`, how many were ore",
        "stole_from_them": "cards they took from the other person's hand. **How many, not which ones**: nobody reads the stolen card",
    },
    "friends_robber_to_whom_number": {
        "number"       : "the number of the tile where they placed the robber on them",
        "placed_on_them": "times they moved the robber onto that specific tile while the other person had something on it. Here it's only the intent: what it actually cost is in \"The robber, pair by pair\"",
        "with_7"       : "of those, how many were **forced** by rolling a 7",
        "with_knight"  : "of those, how many were **chosen**, by playing a knight. With a big number, this is the column that separates bad luck from bad intentions",
    },
    "friends_robber_numbers": {
        "times"      : "how many times the robber has gone to that number, across everyone",
        "with_7"     : "of those, how many were forced by a 7",
        "with_knight": "of those, how many were chosen, with a knight",
        "people"     : "how many different people have covered it",
    },
    "friends_robber_where": {
        "times"      : "how many times they sent the robber to that number",
        "with_7"     : "of those, how many were forced by a 7",
        "with_knight": "of those, how many were chosen, with a knight",
        "to_self"    : "of those times, how many landed on **their own** tile. It's legal and it happens: sometimes a 7 just doesn't leave a better spot, and sometimes it's deliberate, to rob from someone who also shares that tile without handing the block to a rival. It doesn't appear in \"The robber, pair by pair\" because that one works in pairs and a row against yourself is confusing; it shows up here instead",
    },
    "friends_steals": {
        "stole"           : "cards they stole from other people's hands",
        "stolen_from_them": "cards that were stolen from them",
    },
    "friends_trade": {
        "deals"             : "deals **they proposed** to that person. The ones the other person proposed are in the return row",
        "gave"              : "cards they gave up in those deals",
        "received"          : "cards that came to them in those deals",
        "net_when_proposing": "`received` minus `gave` **only in the deals they proposed**. **This is not their balance with that person** -- that's `net` in \"The balance with each person\", which comes out different in 16 of the 26 pairs, several with the sign flipped. The table itself carries the warning: the two rows of a pair can be **both negative**, and in a real balance that's impossible -- cards don't vanish when they change hands. They can be here because these are different sets of deals. And there's a reason most of them are: out of 141 proposed deals, whoever proposes ends up **30 cards short**",
        "deals_between_them": "how many deals the two of them have made, whoever proposed them. **The same figure in both rows of the pair**",
        "games_together"    : "how many games the two of them have played together. This is what gives the column next to it meaning: two deals between two people who've only played two games together and two deals between two who've played thirteen look the same in the table and aren't",
    },
    "friends_balance": {
        "deals"   : "deals between the two of them, whoever proposed them",
        "gave"    : "cards they gave them in total",
        "received": "cards that came to them from that person",
        "net"     : "`received` minus `gave`. The return row carries the same number with the sign flipped",
    },
    "friends_deals": {
        "gave"        : "what they gave up, written as-is: `1 Wood + 1 Wool`",
        "to"          : "who they gave it to",
        "and_received": "what they got back for it",
    },
    "friends_trade_resource": {
        "gave"    : "how many cards of that resource they gave them",
        "received": "how many of that resource came to them from that person",
        "net"     : "`received` minus `gave` for that resource. Who they're running short with, on what",
    },
    "friends_ports": {
        "port"      : "which one they used: `Wood 2:1` or `generic 3:1`. Trades at 4:1 -- the ones anyone without a port makes -- aren't included: this table is specifically about ports, and all of them show up in \"Deal by deal\"",
        "times"     : "how many bank trades they made there, **across all their games**. To see in how many different games that port could actually be credited to them, see \"How many, by player\"",
        "first_used": "the **earliest** they've ever used it: the lowest turn number across all their games. It's a ceiling on when they got it, not when they got it -- they could have had it as early as that, but maybe earlier",
        "last_used" : "the **latest** they've used it, across all their games. Not the other end of the same game as `first_used`",
    },
    "friends_ports_count": {
        "games_played" : "how many of their games are on record. It comes first because without it nothing else can be compared: using the wood port four times in twenty games isn't the same as four times in six",
        "wood_port"    : "in how many games the 2:1 wood port could be credited to them. **How many games, not how many times they used it**: using it fifteen times in one game counts once, because what's being measured is having it. And 'could be credited' rather than 'had it', because **this is deduced from the trades they made**, not from looking at the board, so a port they had but never used doesn't show up",
        "brick_port"   : "same, for the 2:1 brick port",
        "wool_port"    : "same, for the 2:1 wool port",
        "grain_port"   : "same, for the 2:1 grain port",
        "ore_port"     : "same, for the 2:1 ore port",
        "generic_ports": "in how many games a generic port (3:1) could be credited to them. Generic ports can't be told apart from each other: one already covers all five resources, so having two leaves no trace distinct from having one",
    },
    "friends_ports_claimed": {
        "port"    : "which one it is, with its trade rate",
        "who"     : "who settled on it. **`nobody`** means a port nobody ever claimed, and that's half the reason this table exists",
        "turn"    : "the turn they placed the piece there. Upgrading to a city doesn't count: the port is claimed when you first settle there",
        "building": "what that spot ended up as, settlement or city",
    },
    "friends_production": {
        "wood"          : "wood the board gave them",
        "brick"         : "brick the board gave them",
        "wool"          : "wool the board gave them",
        "grain"         : "grain the board gave them",
        "ore"           : "ore the board gave them",
        "total"         : "the sum of all five. **Includes the initial setup**, which the board also hands out; if you want only what came from rolls, subtract `from_setup`",
        "from_setup"    : "the cards they collected **when placing their second settlement**: one for each adjacent tile. It's the only part of `total` that didn't come from a roll, and it's around 3 per game. It's kept separate because it's the difference from `produced`, which only counts what the board paid out when a number rolled",
        "lost_to_robber": "**cards** they missed out on because the robber was sitting on the tile. It's the same number as `lost` in \"The robber\", under a different name: that row is about the robber, this one is about production, and each reads better with its own name",
    },
    "friends_numbers": {
        "buildings"       : "how many of their pieces touch that number, across all their games. Thirteen settlements on the 6 could be thirteen games with one, or two games with six",
        "first_settlement": "which turn they first placed a piece there. **`0` is the initial setup**, and a dash (—) means they never placed anything on that number -- these mean opposite things, be careful. Within a single game it's the **first** one: two settlements on the same number, turns 0 and 41, give 0 and not 20, because from turn 0 they were already collecting there. Across games it's the **average** of those firsts, which is why it carries a decimal: a 13.8 is a reminder that it's an average and not literally turn 13. It's read next to `times_rolled`, because that column counts rolls across the whole game: having the 6 since turn 0 and having it since turn 30 look the same there, and they're not worth the same. Upgrading to a city doesn't move it -- it counts when the settlement was placed",
        "pips"            : "the pips printed under the number on the tile: how many of the 36 two-dice combinations produce it. The 6 has five, the 2 has one. **This isn't summed**: it's a property of the number, not a running count, so it comes out the same whether you're looking at one game or all of them",
        "times_rolled"    : "how many times that number came up, counting only the games where they had something placed on it. In a game where that number wasn't theirs, none of its rolls count",
        "expected_rolls"  : "how many times it should have come up, based on its pips: pips divided by 36, times how many rolls there were. It's counted game by game and summed, the same way as `times_rolled`, so the two can be compared directly",
    },
    "friends_sevens": {
        "games_played"      : "how many of their games are on record",
        "rolls_by_them"     : "how many times they personally rolled the dice. This is what makes the next column comparable: games don't all last the same length. It's called `rolls_by_them` rather than `rolls` on purpose -- the question box up top translates 'comes up' and 'die' into 'roll', and under that name this table kept getting trade questions",
        "sevens"            : "how many of those rolls came up 7",
        "percentage"        : "what share of **their** rolls was a 7",
        "expected_percentage": "the 16.7% anyone should expect: 6 of the 36 combinations. Above that means 7 comes up for them more than it should -- and the 7 is the only number that depends on who's rolling: it moves the robber and forces a discard",
    },
    "friends_rolls": {
        "times"              : "how many times that number came up",
        "expected_times"     : "how many times it should have come up, based on its pips over 36. The 7 is 6 of every 36 rolls; the 2 is one",
        "percentage"         : "what share of all rolls was that number",
        "expected_percentage": "what share it should have been: that number's pips over 36. Read next to `percentage`, which is what actually happened",
    },
    "friends_luck": {
        "tiles"        : "**their own spots that pay out**, not distinct board tiles. If they have two pieces touching the same tile, that tile counts twice -- because when the number comes up, they get paid twice. This happens a lot: 159 cases in the current games. What does **not** count twice is upgrading to a city: the dice don't know what's built there, and this column measures how often the number will come up for you, not how many cards you're paid",
        "pips"         : "the pips of those spots, added up. **This is where a 6 weighs five times what a 2 does.** Careful with the math: a 6 is **5** pips, not 6, so two spots on a 6 add up to 10. And it doesn't matter whether they're two different 6 tiles or two of your own pieces on the same one -- either way you get paid twice",
        "pips_per_tile": "`pips` divided by `tiles`: **what one of their spots is worth on average**. This is what lets you compare two people, because raw pips reward whoever's played more games",
        "baseline"     : "what an average tile would be worth on the boards they played -- 3.22 for the classic board. Above that means they pick good spots; below it, they're settling for less. **This isn't luck, it's judgment**: the luck part is those numbers actually coming up, and that's `luck`",
        "cards_per_tile": "cards each of their spots has paid them, on average. **Don't compare this to `pips_per_tile`** -- that one's pips, this one's cards. Cities pay double here, and the robber pays nothing",
        "rolls_by_them": "**how many times they personally rolled the dice.** Don't confuse this with the one next to it: `rolls_counted` is every roll at the table that could have paid them -- whoever rolled it -- while this is only their own rolls, so at a table of four it's roughly a quarter of the total. **It doesn't factor into the luck calculation**, because the dice don't care whose turn it is: if a 6 comes up, whoever has something on the 6 gets paid, not whoever rolled it. The only number that does depend on who's rolling is the 7, and that's in \"Everyone's sevens\" -- where this same column is the denominator",
        "rolls_counted": "**how many rolls everything else is measured against.** Without it, a 108% and a 99% look like comparable results, and one could come from 53 rolls and the other from 837. These are the rolls where they had something placed -- which today is every roll in their games, since the two starting settlements go down before the first die is ever rolled. **This is not the multiplier behind `expected`** -- that one uses each tile's own window separately, so this one, worked out from pips, won't match it and doesn't need to. It's the sample size, not a factor",
        "got"          : "**payouts, not rolls**. Every time one of their numbers comes up it counts once **per spot they have on it**: three spots on the 4 and a 4 comes up means *one roll and three payouts*. In a base-game game: 46 rolls, 28 landed on one of their numbers, and they got paid 41 times. This is what the board actually paid them",
        "expected"     : "the payouts they should have gotten: for each of their spots, its pips over 36, times each roll. It's counted the same way as `got` -- with the same *per spot* rule -- which is why the two are comparable. This is what the board owed them",
        "surplus"      : "`got` minus `expected`, in payouts",
        "luck"         : "`got` divided by `expected`, as a percentage. **100 is normal luck**",
        "margin"       : "how much randomness normally moves this, as a percentage. With nine tiles, chance alone moves you ±17%; with fifty, ±6%",
        "margins_off"  : "how many margins off it is, with a sign. **This is the number that actually ranks people**: below 2, none of it means anything, whatever the percentage says",
    },
}


# What ONE ROW means in each view, and what it's useful for.
#
# It's the first thing you need to know to read a table, and the one thing
# you can't work out from the column names. In "The robber" a row is a
# person; in "The robber, pair by pair" it's a PAIR; in "The numbers" it's a
# single number from 2 to 12. With the same columns in front of you, the
# three read completely differently.
#
# The text has two parts:
#   row  -- "one row per...", so you know what you're looking at
#   for  -- what question it answers, phrased the way people actually ask it
ROW_IS = {
    "games": {
        "row": "each game played",
        "for": "see at a glance how many you've played, how long they last, and which ones were against the computer",
    },
    "players": {
        "row": "each player in each game",
        "for": "this is the table almost everything else is built from: name, color, what position they started in and what position they finished in",
    },
    "friends_scoreboard": {
        "row": "each person",
        "for": "the classic scoreboard: who wins the most and who ends up ranked highest",
    },
    "friends_start": {
        "row": "each player in each game",
        "for": "see game by game who started first and whether it did them any good",
    },
    "friends_by_start": {
        "row": "each starting position (1st, 2nd, 3rd...)",
        "for": "the age-old question: does starting first pay off, or is last actually better because you place two settlements in a row?",
    },
    "friends_start_by_player": {
        "row": "each person",
        "for": "whether the draw treats you well: how many times you've gotten to start first, against how many you should have. **Every column in this table is about where you started, not where you finished**",
    },
    "friends_finish_from_start": {
        "row": "each person **and starting position**",
        "for": "whether starting first actually helps you. Someone starting first a lot and winning a lot doesn't tell you they win WHEN they start first, and no other table crosses those two things person by person. With few games it comes out very scattered: that's just how it is, and it reads well once there are more games",
    },
    "friends_points": {
        "row": "each player in each game",
        "for": "where their points came from: settlements, cities, the two bonuses, and -- by subtraction -- hidden cards",
    },
    "friends_development": {
        "row": "each person",
        "for": "what the deck gives each person: whether they get a lot of knights or a lot of victory points",
    },
    "friends_deck": {
        "row": "each development card type",
        "for": "whether the deck behaves: what's actually come out against what the deck holds",
    },
    "friends_monopolies": {
        "row": "each monopoly played",
        "for": "see them one by one: who played it, what they asked for, and how much they took",
    },
    "friends_monopolies_to_whom": {
        "row": "each pair of players",
        "for": "whose monopolies hurt whom, and in what resource",
    },
    "friends_robber": {
        "row": "each person",
        "for": "how much the robber costs you over a whole game: what you missed out on plus what got stolen",
    },
    "friends_robber_ratio": {
        "row": "each person",
        "for": "find out who really gets targeted more, not just who's played the most games. It's \"The robber\" as a ratio, and it changes the ranking",
    },
    "friends_robber_to_whom": {
        "row": "each pair of players",
        "for": "the grudges: if someone puts the robber on you a lot more than on everyone else, it shows up here",
    },
    "friends_robber_to_whom_number": {
        "row": "each pair of players **and number**",
        "for": "whether they put it where it hurts. It's not the same to get hit on an 11 -- with a 7 you have to move it somewhere, and sometimes it's just about stealing a card without more thought -- as on a 6, which comes up two and a half times more. It's the finest-grained of the four robber tables: with few games you'll see a lot of rows with just 1, and that's not a bug",
    },
    "friends_robber_where": {
        "row": "each person and number",
        "for": "which numbers each person sends the robber to. Almost everyone has a favorite",
    },
    "friends_robber_numbers": {
        "row": "each board number",
        "for": "which numbers end up blocked the most, adding up everyone's moves",
    },
    "friends_production": {
        "row": "each person",
        "for": "what resources the board gives each person, and how much was lost along the way",
    },
    "friends_numbers": {
        "row": "each person and **each of the ten numbers**, across all their games. All ten always show up, even if they never placed anything there: an empty 6 says more than half the table. The 7 isn't included because no tile carries a 7",
        "for": "what numbers each person builds around, how much they were owed, and how much actually came in. For one specific board, the dropdown filters this same table",
    },
    "friends_luck": {
        "row": "each person",
        "for": "who's actually lucky. It compares what they got against what they should have gotten, and says whether the difference is real or just noise",
    },
    "friends_trade": {
        "row": "each pair **and who proposed**. The return row is a DIFFERENT set of deals: 3 and 1 means one side asked three times and the other once, four total",
        "for": "who proposes deals to whom, and whether they come out ahead or behind on cards",
    },
    "friends_balance": {
        "row": "each pair **seen from each side**. Careful, this is the one people mix up most: `who` does NOT mean who proposed the deal -- that's in \"Who proposes deals to whom\" -- it's whose point of view the row is told from. The two rows of a pair are **the same deals**, which is why they carry the same `deals` and `net` with the sign flipped",
        "for": "the plain balance with each person: how many cards you've given them and how many they've given you",
    },
    "friends_deals": {
        "row": "each deal closed",
        "for": "see them one by one, what was given for what was received",
    },
    "friends_trade_resource": {
        "row": "each pair and resource",
        "for": "which resource each one comes out ahead on: 'I always end up giving this person wood'",
    },
    "friends_ports": {
        "row": "each person and port, across all their games",
        "for": "who uses the ports and from what turn onward. Deduced from bank trades. For one specific board, the dropdown filters this same table",
    },
    "friends_ports_claimed": {
        "row": "each port on the map",
        "for": "who ended up with each port, including the ones nobody claimed",
    },
    "friends_ports_count": {
        "row": "each person, across all their games",
        "for": "which port each person builds around. Board by board this is four mostly-empty rows; across all of them the pattern shows up. To see it game by game, the dropdown filters this same table, and \"Who claimed each port\" shows it board by board",
    },
    "friends_pace": {
        "row": "each player in each game",
        "for": "who gets going earliest: what turn they reached their first city, their first development card, their first knight",
    },
    "friends_steals": {
        "row": "each person",
        "for": "how many cards they've stolen from hands, and how many have been stolen from them",
    },
    "friends_rolls": {
        "row": "each number, from 2 to 12",
        "for": "whether the dice are fair: what actually came up against what should have",
    },
    "friends_sevens": {
        "row": "each person, across all their games",
        "for": "who rolls more 7s than they should when it's their turn. \"The rolls\" checks whether the dice are fair to the table; this one checks whether they're fair to each person",
    },
}
