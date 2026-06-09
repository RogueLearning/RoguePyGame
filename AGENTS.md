# Agents.md

## Project

A small turn-based ASCII roguelike. Pure Python terminal app, standard library only.

- Entry point: `rogue.py` → `Game().run()`
- Game class lives in `game.py`
- Requires Python 3.10+ (uses `X | None` union syntax, `match`-free)
- No third-party dependencies — only `random`, `math`, `sys`, `os`, `termios`, `tty`, `select`, `time`, `datetime`

## Run

```
python3 rogue.py
```

The game reads keys from the terminal in raw mode, so run it in a real TTY (not a piped or buffered output pane). It expects a terminal at least `TOTAL_WIDTH x TOTAL_HEIGHT` = 80 x 23 cells. The emoji glyphs assume a UTF-8 terminal that renders emoji as double-width cells (matches macOS Terminal, iTerm2, most Linux terminal emulators).

High scores persist to `highscores.txt` in the working directory, one entry per line as `score|depth|kills|date(ISO 8601)`.

## Folder Structure

```
rogue.py             bootstrap (entry point)
game.py              main loop, input dispatch, combat/turn orchestration
Entities/
  Game entity objects with position, health, etc.
Items/
  Inventory items with type/kind and use effects
Map/
  Map generator and tile definitions
UI/
  Rendering, colors, message log, raw-mode keyboard input
```

## Core loop (`Game.run`)

1. Compute FOV from player position.
2. Render (map, entities, sidebar, message log).
3. Read one key; `_handle_input` returns whether the action consumed a turn.
4. If a turn was taken and the player is alive, `_monsters_act()` runs every monster on a visible tile (monsters frozen outside FOV — intentional).
5. On death, show game-over screen and persist a high-score entry.

Monster AI: if adjacent to player, attack; otherwise step toward player on the longer axis, falling back to the other axis if blocked.

## Conventions

- Coordinates are `(x, y)` with `y` increasing downward (terminal convention). `level.tiles` is a 2-D list indexed `[x][y]`.
- All rendering goes through `Renderer` — don't call `sys.stdout.write` from gameplay code except in the dedicated screens (`_show_inventory`, `_show_game_over`). After any full-screen takeover, call `self._renderer.reset()` so the next frame fully repaints.
- One shared `random.Random` lives on `Game._rng` and is threaded into generators/factories. Don't `random.Random()` ad hoc — it breaks reproducibility if a seed is ever introduced.
- Monsters and items added to a level should go through `monster_factory.create` / `item.create` so depth-scaling stays in one place.
- `MessageLog.add` takes an optional `Color`; pick colors that match existing usage (red for damage to player, green for kills/heals, cyan for pickups/equip, yellow for prompts, dark gray for no-ops).
- `Renderer` constants (`MAP_WIDTH`, `MAP_HEIGHT`, `SIDEBAR_WIDTH`, `LOG_HEIGHT`) define the viewport — the map generator is told the viewport size, so resizing the UI also resizes generated levels.
- Color is a 16-entry `IntEnum` in `UI/colors.py` that maps to ANSI escape codes via `ansi_fg(color)`. Don't write raw ANSI from gameplay code.
- Raw keyboard mode is entered via the `RawTerminal` context manager in `UI/keyboard.py`. `read_key()` returns either a single character or the sentinel `UP`/`DOWN`/`LEFT`/`RIGHT` for arrow keys.

## Adding things

- **New monster**: extend the pool in `Entities/monster_factory.py::create` with a `(weight, factory)` tuple and a `depth >=` gate.
- **New item kind**: add to `ItemKind`, give it fields on `Item`, handle it in `Game._use_item` and in the inventory detail string in `Game._show_inventory`. Spawn it from `Items/item.py::create`.
- **New tile type**: add to `TileType`, update `Tile.is_walkable` / `blocks_sight` if needed, and add a draw case in `Renderer._draw_map`.
- **New command key**: add a case in `Game._handle_input` and return `True` only if it consumes a turn (movement, pickup, descend, attack do; opening inventory or quitting do not).
