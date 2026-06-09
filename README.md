# Terminal Roguelike

An emoji-glyph dungeon crawler in pure Python 3. Procedural rooms-and-corridors maps, persistent multi-level dungeons, fog of war, bump-to-attack melee combat, ranged magic via wands, a boss requiring magic or enchanted steel, and endless descent for high scores. No external dependencies — only the Python standard library.

![Game in progress on depth 1 — the witch 🧙 stands in a corridor with a healing potion 🧪 and a dagger 🗡️ nearby, stairs down `>>` to the south. Sidebar shows status, key bindings, and equipped gear.](screenshot.jpg)

---

## Run

```bash
python3 rogue.py
```

Requires Python 3.10+ and a real terminal (≥ **80×23** cells). The game puts the TTY in raw mode via `termios`/`tty`, so it cannot be driven from piped stdin.

---

## Controls

### Main loop

| Key             | Action                                              | Consumes a turn? |
| --------------- | --------------------------------------------------- | ---------------- |
| `↑ ↓ ← →`       | Move one tile; bump into a monster to melee-attack  | yes              |
| `g` / `G`       | Pick up the item under you                          | yes (if item)    |
| `i` / `I`       | Open the inventory menu                             | no               |
| `z` / `Z`       | Zap your readied wand (opens direction prompt)      | yes (if fired)   |
| `>`             | Descend stairs (must be standing on a `>>` tile)    | yes              |
| `<`             | Ascend stairs (must be standing on a `<<` tile)     | yes              |
| `q` / `Q`       | Quit immediately (no save, no high-score entry)     | n/a              |
| any other key   | ignored                                             | no               |

Letter commands (`g`, `i`, `z`, `q`) are case-insensitive. The stair commands `>` and `<` are read by character, not key, so any keyboard layout that produces those characters works.

### Inventory menu (after pressing `i`)

| Key             | Action                                              |
| --------------- | --------------------------------------------------- |
| `a` … `t`       | Use/equip the item with that letter                 |
| any other key   | Cancel and return to the map                        |

Effects by item kind:
- **Healing potion** — drunk, removed from inventory, heals up to its amount (capped at MaxHp).
- **Weapon** — equipped to the weapon slot (replaces previous equipped weapon, which stays in inventory).
- **Wand** — readied in the wand slot (replaces previously readied wand).

### Zap prompt (after pressing `z`)

| Key             | Action                                              |
| --------------- | --------------------------------------------------- |
| `↑ ↓ ← →`       | Fire fireball in that direction (consumes 1 charge) |
| any other key   | Cancel — no turn, no charge spent                   |

Requires a readied wand with at least one charge; otherwise pressing `z` just logs a message and consumes nothing.

### Game-over screen

| Key             | Action                                              |
| --------------- | --------------------------------------------------- |
| any key         | Acknowledge death (then any key again to exit)      |

---

## Glyph reference

The map is 30 tiles wide × 18 tall, with each tile rendered as **2 terminal cells wide** to accommodate emoji.

### Tiles

| Glyph | Meaning           | Visible color | Dim (explored) color |
| ----- | ----------------- | ------------- | -------------------- |
| `██`  | Wall              | DarkCyan      | DarkBlue             |
| `··`  | Floor             | DarkYellow    | DarkGray             |
| `>>`  | Stairs down       | Yellow        | DarkYellow           |
| `<<`  | Stairs up         | White         | Gray                 |
| ⛲   | Fountain          | Cyan          | DarkCyan             |

### Actors and items

| Glyph | Name             |
| ----- | ---------------- |
| 🧙    | Player (you)     |
| 🐀    | Rat              |
| 👺    | Goblin           |
| 👹    | Orc              |
| 🧌    | Troll            |
| 👻    | Wraith           |
| 💀    | Dread knight (boss) |
| 🧪    | Healing potion   |
| 🗡️    | Weapon (any kind) |
| 🪄    | Wand of fireball  |
| 🔥    | Fireball projectile (animation only) |

Visible tiles render in full color; explored-but-not-visible tiles render dim (fog of war). Unexplored tiles render as blank space.

---

## Requirements

### Technical requirements

| Concern            | Value                                                       |
| ------------------ | ----------------------------------------------------------- |
| Language           | Python 3.10+                                                |
| Framework          | Standard library only (`termios`, `tty`, `select`, `random`, …) |
| External libraries | None                                                        |
| Output encoding    | UTF-8 (assumed terminal default)                            |
| Terminal size      | At least 80 cols × 23 rows                                  |
| Input              | Raw-mode `sys.stdin.read(1)` via `termios`/`tty` — real TTY only |
| Persistence        | `highscores.txt` in the working directory (top 10 runs)     |

### Game loop (turn-based)

Each iteration of the main loop:

1. **Compute FOV** — 360-ray raycast from player position, radius 8 tiles. Sets each tile's `visible` flag; `explored` is sticky once set.
2. **Render** — draw map + entities + sidebar + log via a double-buffered renderer that only updates changed cells.
3. **Block on `read_key()`** (raw-mode `sys.stdin.read(1)`) for player input.
4. **Dispatch input.** Action returns `took_turn: bool`. Movement, attack, pickup, zap, descend/ascend each consume a turn; opening the inventory or pressing an unbound key does not.
5. **If turn was taken**, run monster AI.
6. **Loop** until player dies (`hp <= 0`) or quits (`q`).

If the player dies, the final frame is rendered with the death message in the log, then the **Game Over** screen is shown with the final score and an updated high-score table.

### Map generation

- Per-floor procedural generation in `MapGenerator.generate(width, height, depth, allow_boss_spawn)`.
- Up to **30 placement attempts** for rectangular rooms (size 4–9 on each axis).
- Each new room is rejected if it intersects an existing one.
- After placement, each new room is connected to the previously placed room via an **L-shaped corridor** (random order: horizontal-then-vertical or vertical-then-horizontal).
- **Spawn**: first room's center is the player spawn / stairs-up location.
- **Stairs down**: last room's center, tile becomes `TileType.STAIRS_DOWN`.
- **Stairs up**: depth > 1 only — first room's center, tile becomes `TileType.STAIRS_UP`. Tracked via `level.has_stairs_up`.
- **Fountains**: per non-spawn room, 20% chance to place a `FOUNTAIN` tile at a random interior point (not on stairs).
- **Monsters**: per non-spawn room, `rng.randrange(0, 2 + depth // 2)` monsters spawn (so depth scales count).
- **Items**: per non-spawn room, 60% chance for a primary item drop and an additional 20% chance for a bonus drop.
- **Boss**: at depth > 3, if no boss has been spawned in this run yet, 15% chance to place a dread knight in a random non-spawn room. Tracked via `Game._boss_spawned`; persists in the level cache.

### Level persistence

`Game` maintains a `dict[int, DungeonLevel]` keyed by depth.

- **First visit to a depth**: generate, cache.
- **Revisit (up or down)**: pull from cache. Killed monsters stay dead, dropped items stay where they were, explored tiles stay explored.
- This prevents farming the upper floors (monsters do not respawn) and also makes the boss permanent on its floor until killed.
- The cache lives only in memory; quitting or dying discards it.

### Movement & combat

- **4-directional** movement for player and monsters (no diagonals).
- **Bump-to-attack**: walking into a monster's tile triggers melee. Damage = `attacker.attack + rng[-1, 1]`, minimum 1.
- **Player attack stat**: `base_attack (4) + equipped weapon's attack_bonus`. Enchantment is a flag on the weapon (separate from the bonus).
- **Monster behavior**:
  - Only acts when in the player's FOV; otherwise idle (preserves state for level cache).
  - If orthogonally adjacent (`|dx| + |dy| == 1`), attacks for `monster.attack ± 1`.
  - Otherwise steps toward the player on the axis with the greater distance, falling back to the other axis if blocked.
  - Cannot step onto another monster or onto the player without attacking.
- **Death**: monster removed from the level. Player death ends the game.

### Field of view

`fov.compute(level, px, py, radius)`:

- Resets `visible` on every tile.
- Casts **360 rays** at evenly spaced angles around the player.
- Each ray marches up to `radius` (default 8) tiles, marking each `visible` and `explored`.
- A ray terminates after marking the first wall it hits (so wall faces are seen).

### Field elements

#### Stairs

- `>>` (descend) and `<<` (ascend) require `key == '>'` or `'<'` respectively AND the player standing on the matching tile.
- Descending to a new max depth grants +5 HP (clamped to MaxHp). Re-descending to an already-visited floor does not heal.
- Ascending from depth 1 is refused with a message ("You cannot leave the dungeon yet.").
- When entering a level via descent, the player lands on the destination's stairs-up if one exists, otherwise on the room-0 spawn.
- When entering via ascent, the player lands on the destination's stairs-down.

#### Fountains (`⛲`)

- Stepping onto a fountain attempts to **enchant your equipped weapon**.
- If no weapon equipped: log message, fountain unchanged.
- If weapon already enchanted: log message, fountain unchanged.
- Otherwise: weapon's `is_enchanted` flag is set; player glyph color shifts to Yellow via `Player.update_appearance()`; message logged.
- Fountains are single-use *per weapon* — but a fountain itself is not consumed, so re-stepping with a different weapon would still enchant. (Currently the only way to "lose" an enchantment is to drink a potion, which calls `update_appearance()`. Equipped enchanted weapons are stable.)

### Items

- All items live in `Items.item.Item` with a `kind` discriminator (`HEALING_POTION`, `WEAPON`, `WAND`).
- An `ItemEntity` wraps an `Item` with map coordinates for items lying on the floor.

#### Drop probabilities (when an item spawns)

| Item kind          | Probability                                |
| ------------------ | ------------------------------------------ |
| Wand of fireball   | 15% at depth ≥ 2; 0% otherwise             |
| Healing potion     | 55% of the remaining roll                  |
| Weapon             | 45% of the remaining roll                  |

#### Healing potion

- Heals `10 + rng[0, 5]` HP, capped at `max_hp`.
- Consumed on use (removed from inventory).

#### Weapon

- 5 tiered names: `dagger`, `shortsword`, `longsword`, `battle axe`, `warhammer`.
- `attack_bonus = 1 + depth // 2 + rng[0, 1]`, clamped to choose the name from the tier table.
- Equipped to `Inventory.equipped_weapon` slot. Replacing equipment is silent — old weapon stays in inventory.
- Can be enchanted by a fountain. Enchanted weapons display as `enchanted <name>` and can damage the boss.

#### Wand of fireball

- `wand_damage = 8 + depth // 3`
- `wand_range = 6` tiles
- `charges = 3 + rng[0, 2]`
- Equipped to a separate `Inventory.equipped_wand` slot.
- Zap mechanic (`z`):
  1. Refuse if no wand readied or charges == 0 (no turn consumed).
  2. Prompt "Zap which direction?" in the log, render to update display.
  3. Read next key; only arrow keys count. Non-arrow cancels (no turn, no charge consumed).
  4. Project a fireball in the chosen direction:
     - Steps tile-by-tile up to `wand_range`.
     - **Animation**: writes `🔥` at each step with a 40 ms pause (60 ms on wall impact).
     - On hitting a wall: log "bursts against the wall", spend a charge, end turn.
     - On hitting a monster: deals `wand_damage + rng[-1, 1]` damage. Kills increment `Player.kills`. End turn.
     - If it travels the full range without hitting anything: "fizzles in the air", spend a charge, end turn.
  5. Boss rule bypass: fireballs are magic and damage the dread knight regardless of weapon enchantment.

### Inventory

- Capacity: 20 items.
- Pick-up (`g`) succeeds if there's an item on your tile and capacity remaining.
- Inventory screen (`i`):
  - Renders directly to the terminal (full-screen overlay).
  - Lists items as `a)`, `b)`, ... in their natural color, with details (heal amount, atk bonus, dmg/range/charges) and an `(equipped)` marker.
  - Pressing a matching letter triggers `_use_item` (consume potion, equip weapon, or ready wand).
  - Any other key cancels.
  - After closing, `_renderer.reset()` forces a full redraw next frame.

### Bosses

- **Dread knight** (`💀`): hp 45, attack 11, `is_boss = True`.
- Spawns once per run at depth > 3 (15% per generated floor until placed).
- Spawn announcement: "An ominous presence stalks this floor..." (DarkRed).
- **Damage immunity**: melee attacks bounce off unless the player's equipped weapon is enchanted. Log: "Your attack glances off the dread knight. Only enchanted steel can harm it!" — no turn cost.
- Fireballs always damage the boss.

### Scoring

`score = max_depth × 100 + kills × 10`

- `max_depth` is the deepest floor ever reached this run; ascending does not reduce it.
- High scores persist in `highscores.txt` as `score|depth|kills|iso-date` per line.
- The Game Over screen loads, appends the new run, sorts descending, truncates to 10, and rewrites the file. Malformed lines are silently skipped on load.

### Rendering

- **Logical map**: 30 × 18 tiles. **Physical render**: each tile = 2 columns wide. Sidebar adds 20 cols. Total = 80 × 23 cells.
- **Buffer**: `str[80][23]` for glyphs + `Color[80][23]` for colors. Trailing half-cells of 2-wide glyphs are stored as `""` and skipped on flush.
- **Double-buffer diff**: only cells whose glyph or color changed since the last frame are redrawn (emitted as ANSI cursor-positioning + color escapes). Eliminates flicker.
- **Sidebar layout** (column 60 onward, rows 0–17):
  - Row 0: `-- STATUS --`
  - Row 1: `Depth: X (max Y)`
  - Row 2: `HP: X/Y` (red ≤⅓, yellow ≤⅔, green otherwise)
  - Row 3: `ATK: X`
  - Row 4: `Kills: X`
  - Row 5: `Score: X`
  - Row 7: `-- KEYS --`
  - Rows 8–14: 7 key hints (arrows, g, i, z, >, <, q)
  - Row 15: `Weapon:`
  - Row 16: equipped weapon name (or `(fists)`)
  - Row 17: `Wand: <name (charges)>` or `(none)`
- **Log**: rows 18–22, top row is a divider of `-` chars. Log holds up to 4 messages; oldest scroll off.
- **Transient overlay** (`draw_transient`): used for the fireball animation. Writes directly to the terminal at a tile coordinate and updates the prev-buffer so the next render correctly restores the underlying tile.

---

## Architecture

```mermaid
graph TD
    Program["rogue.py<br/><i>entry point</i>"] --> Game

    Game["Game<br/><i>turn loop + input + cache</i>"]

    subgraph Map["Map layer"]
        MapGenerator["map_generator<br/><i>rooms + corridors</i>"]
        DungeonLevel["DungeonLevel<br/><i>tiles[x][y] + actors</i>"]
        Tile["Tile<br/><i>type + visible/explored</i>"]
        Fov["fov<br/><i>raycast visibility</i>"]
    end

    subgraph Entities
        Entity["Entity<br/><i>base: x,y,glyph,color</i>"]
        Player["Player<br/><i>HP, depth, max_depth, score</i>"]
        Monster["Monster<br/><i>HP, attack, is_boss</i>"]
        MonsterFactory["monster_factory<br/><i>depth-weighted + boss</i>"]
    end

    subgraph Items
        Item["Item<br/><i>potion / weapon / wand</i>"]
        ItemEntity["ItemEntity<br/><i>item on the floor</i>"]
        Inventory["Inventory<br/><i>weapon + wand slots</i>"]
        ItemFactory["item.create"]
    end

    subgraph UI
        Renderer["Renderer<br/><i>double-width emoji draw</i>"]
        MessageLog["MessageLog<br/><i>rolling log</i>"]
    end

    Game --> Player
    Game --> DungeonLevel
    Game --> MapGenerator
    Game --> Fov
    Game --> Renderer
    Game --> MessageLog

    MapGenerator -->|builds| DungeonLevel
    MapGenerator --> MonsterFactory
    MapGenerator --> ItemFactory

    DungeonLevel --> Tile
    DungeonLevel -.contains.-> Monster
    DungeonLevel -.contains.-> ItemEntity

    Player --> Inventory
    Inventory --> Item
    ItemEntity --> Item

    MonsterFactory -->|creates| Monster
    ItemFactory -->|creates| ItemEntity

    Fov -.flags.-> Tile

    Player -.extends.-> Entity
    Monster -.extends.-> Entity

    Renderer -.reads.-> DungeonLevel
    Renderer -.reads.-> Player
    Renderer -.reads.-> MessageLog

    classDef core fill:#2d3142,stroke:#bfc0c0,color:#fff
    classDef factory fill:#4f5d75,stroke:#bfc0c0,color:#fff
    class Game,Program core
    class MapGenerator,MonsterFactory,ItemFactory factory
```

### Turn loop

```mermaid
flowchart LR
    A[Compute FOV] --> B[Render frame]
    B --> C[Read key]
    C --> D[Dispatch input]
    D --> E{Action took<br/>a turn?}
    E -->|no| F{Alive &<br/>not quit?}
    E -->|yes| G[Monsters act]
    G --> F
    F -->|yes| A
    F -->|dead| H[Game Over +<br/>high scores]
    F -->|quit| I([Exit])
```

### Level transition

```mermaid
flowchart TD
    A[Player on stairs] --> B{Direction}
    B -->|descend| C{Depth+1<br/>cached?}
    B -->|ascend| D{Depth-1<br/>cached?}
    C -->|no| E[Generate +<br/>cache new level]
    C -->|yes| F[Restore from<br/>cache]
    D -->|yes| F
    E --> G[Place player on<br/>StairsUp]
    F -->|came down| G
    F -->|came up| H[Place player on<br/>StairsDown]
    G --> I[Update<br/>MaxDepth + heal]
    H --> I
    I --> J[Resume turn loop]
```

---

## Project layout

```
rogue.py              entry point — runs Game().run()
game.py               turn loop, input dispatch, combat, inventory UI,
                      level cache, ascend/descend, zap, game over
Map/
  tile.py             TileType (WALL, FLOOR, STAIRS_DOWN, STAIRS_UP, FOUNTAIN)
                      + visible / explored flags
  dungeon_level.py    2D Tile grid + monsters list + items list +
                      stairs_up/stairs_down/player_spawn coords
  map_generator.py    procedural rooms + L-shaped corridors,
                      monster/item/fountain/boss placement
  fov.py              360-ray raycast field-of-view
Entities/
  entity.py           base class (x, y, glyph, color, name)
  player.py           HP, attack, depth, max_depth, kills, score,
                      inventory, appearance update on enchantment
  monster.py          HP, attack, is_boss flag
  monster_factory.py  depth-weighted spawn pool + create_boss
Items/
  item.py             Item + ItemEntity + create() factory (probabilities)
  inventory.py        items list + equipped weapon + equipped wand
UI/
  colors.py           16-entry Color IntEnum + ANSI escape helpers
  keyboard.py         RawTerminal context manager + read_key()
  renderer.py         double-buffered, double-width emoji-aware draw
  message_log.py      rolling buffer of recent messages
```

---

## Caveats & known limitations

- **Raw-mode input requires a real TTY.** `termios.tcsetattr` + `sys.stdin.read(1)` cannot be driven from piped stdin — the game must run in an interactive terminal.
- **Terminal must be ≥ 80 × 23.** Smaller windows will wrap or truncate the rendered frame.
- **Emoji width depends on the terminal.** All glyphs assume each emoji renders 2 cells wide (iTerm2, macOS Terminal, Windows Terminal, modern Linux terminals). On terminals that render emoji as 1 cell wide, the layout will misalign.
- **`termios`/`tty` is POSIX-only.** The game runs on macOS and Linux out of the box. Windows users will need WSL or to swap `UI/keyboard.py` for a `msvcrt`-based implementation.
- **No save/load**, only high scores. Quit (`q`) and death both end the run.
- **No diagonal movement** for any actor. Diagonally adjacent monsters must step before attacking.
- **High-score file is plain text** (`score|depth|kills|iso-date`). Easy to edit by hand; malformed lines are skipped silently on load.
- **Fountains aren't consumed.** Stepping on one with an unenchanted weapon enchants it; with an enchanted weapon nothing happens. This means a second pass with a different weapon would still enchant.
- **The boss check is per-run, not per-cache.** Once a boss has been placed on any floor in the run, no other floor will spawn another, even if you never visited the boss's floor — this is intentional but worth noting.
