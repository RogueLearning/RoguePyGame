"""
create_arcade_sprites.py
------------------------------------------------------------------
Builds crunchy late-70s/early-80s arcade pixel art for classes and
monsters with a small, saturated palette and exaggerated silhouettes.

Output (run this file to regenerate):
    assets/players/<class>.png   128x128  (4 dirs x 4 frames)
    assets/sprites/<monster>.png 64x32    (2-frame idle loop)
"""

import os
import pygame

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
pygame.init()

CELL = 32          # output cell size in screen pixels
GRID = 16          # logical art grid (16x16)
PIX = CELL // GRID  # size of one art-pixel block (2)

# ------------------------------------------------------------------
# Atari-inspired palette. '.' = transparent.
# ------------------------------------------------------------------
PALETTE = {
    '.': None,
    'K': (14, 16, 24),
    'W': (236, 236, 228),
    'S': (166, 174, 190),
    'D': (86, 98, 124),
    'L': (220, 228, 246),
    'R': (220, 66, 52),
    'r': (146, 34, 24),
    'G': (248, 204, 78),
    'g': (172, 122, 36),
    'B': (64, 128, 214),
    'b': (36, 74, 144),
    'P': (140, 78, 216),
    'p': (92, 48, 158),
    'C': (96, 216, 255),
    'N': (64, 176, 92),
    'n': (34, 108, 56),
    'k': (238, 184, 132),
    'j': (188, 132, 90),
    'w': (126, 84, 46),
    'o': (238, 136, 50),
    'y': (248, 228, 112),
    'M': (194, 78, 154),
    'E': (252, 60, 48),
    'F': (124, 130, 142),
    'f': (62, 66, 76),
    'A': (140, 212, 255),
    'a': (76, 154, 212),
    'h': (128, 88, 48),
    'O': (72, 74, 46),
    'q': (42, 46, 28),
    'T': (126, 154, 94),
    't': (82, 108, 60),
    'z': (154, 160, 170),
}


def blit_pixmap(surf, rows, ox, oy, pix=PIX):
    """Draw a list-of-strings pixel map onto surf at (ox, oy)."""
    for gy, line in enumerate(rows):
        for gx, ch in enumerate(line):
            color = PALETTE.get(ch)
            if color is None:
                continue
            surf.fill(color, (ox + gx * pix, oy + gy * pix, pix, pix))


# ==================================================================
#  PLAYER CLASSES
#  Author the BODY (head + torso, rows 0..11). Legs are drawn
#  procedurally per frame so we get a real walk cycle.
# ==================================================================

# Each class supplies body art for DOWN / UP / SIDE (side faces right;
# we flip it for left).  Plus a boot color and a "torso bottom" row used
# to attach the legs cleanly.

KNIGHT_DOWN = [
    "................",
    ".....KRRK.......",
    ".....RRRR.......",
    "....KSSSSK......",
    "...KSLLLLSK.....",
    "...DKWWWWKD.....",
    "...DKKEEKKD.....",
    "....SLLLLS......",
    "..BBKSSSSKGG....",
    ".BBBDSSSSDgGG...",
    ".bBB.SSSS.GgG...",
    "....DSSSSD......",
]
KNIGHT_UP = [
    "................",
    "....KRRRRK......",
    "....RRRRRR......",
    "....KSSSSK......",
    "...KSSSSSSK.....",
    "...DSSSSSSD.....",
    "...DSSSSSSD.....",
    "....SSSSSS......",
    "..bbDSSSSDgg....",
    ".bbbDSSSSDggg...",
    ".bb..SSSS..gg...",
    "....DSSSSD......",
]
KNIGHT_SIDE = [
    "................",
    ".....KRRK.......",
    ".....RRRR.......",
    "....KSSSSK......",
    "...KSLLLSKK.....",
    "...DKWWKKSD.....",
    "...DKEKKKSD.....",
    "....SLLLS.......",
    "...GKSSSSK......",
    "..GgDSSSSD......",
    ".BBb.SSSS.......",
    ".BB.DSSSSD......",
]

WIZARD_DOWN = [
    ".......G........",
    "......GhG.......",
    ".....phhhp......",
    "....pphhhpp.....",
    "...ppGGGGGpp....",
    "....kkkkkk......",
    "....kCkkCk......",
    "....kkkkkk......",
    "...PPPPPPPP.....",
    "..wPPGGGGPP.....",
    "..CPPPPPPPP.....",
    "...PPPPPPPP.....",
]
WIZARD_UP = [
    ".......G........",
    "......GhG.......",
    ".....phhhp......",
    "....pphhhpp.....",
    "...ppppppppp....",
    "....pppppp......",
    "....pppppp......",
    "....pppppp......",
    "...PPPPPPPP.....",
    "..wPPPPPPPP.....",
    "..CPPPPPPPP.....",
    "...PPPPPPPP.....",
]
WIZARD_SIDE = [
    ".....G..........",
    "....GhhG........",
    "...phhhhp.......",
    "..pphhhhGp......",
    "..ppGGGGpp......",
    "...kkkkk........",
    "...kCkkk........",
    "...kkkkk........",
    "...PPPPPP.......",
    "..wPPGGPP.......",
    "..CPPPPPP.......",
    "...PPPPPP.......",
]

ROGUE_DOWN = [
    "................",
    "....nnnnnn......",
    "...nNNNNNNn.....",
    "...nNnnnnNn.....",
    "....kCkCk.......",
    "....kkkkk.......",
    "...nNNNNNn......",
    "..nnNNNNNnn.....",
    "..nNNNNNNNn.....",
    "..SnNNNNNNn.....",
    ".SSwNNNNNN......",
    "...nNNNNNn......",
]
ROGUE_UP = [
    "................",
    "....nnnnnn......",
    "...nNNNNNNn.....",
    "...nNNNNNNn.....",
    "...nNNNNNNn.....",
    "....NNNNN.......",
    "...nNNNNNn......",
    "..nnNNNNNnn.....",
    "..nNNNNNNNn.....",
    "..nNNNNNNNn.....",
    "...NNNNNNN......",
    "...nNNNNNn......",
]
ROGUE_SIDE = [
    "................",
    "...nnnnn........",
    "..nNNNNNn.......",
    "..nNnnnNn.......",
    "...kCkk........",
    "...kkkk........",
    "..nNNNNn.......",
    ".nnNNNNnn......",
    ".nNNNNNNwSS....",
    ".nNNNNNNNwS....",
    "..NNNNNN.......",
    "..nNNNNn.......",
]

CLASS_ART = {
    "knight": dict(down=KNIGHT_DOWN, up=KNIGHT_UP, side=KNIGHT_SIDE,
                   boot=(60, 64, 72), boot_hi=(110, 116, 128)),
    "wizard": dict(down=WIZARD_DOWN, up=WIZARD_UP, side=WIZARD_SIDE,
                   boot=(92, 60, 36), boot_hi=(138, 92, 52)),
    "rogue":  dict(down=ROGUE_DOWN, up=ROGUE_UP, side=ROGUE_SIDE,
                   boot=(46, 40, 32), boot_hi=(78, 66, 52)),
}

# Walk cycle: foot vertical offsets per frame (in art-pixels) for L/R foot.
#   frame 0: stand   1: left-step   2: stand   3: right-step
WALK = [
    (0, 0),
    (-1, 1),
    (0, 0),
    (1, -1),
]
BOB = [0, -1, 0, -1]


def draw_class_fx(surf, cls_name, direction, frame, ox=0, oy=0):
    """Small per-frame accents that sell animation at low resolution."""
    # Weapon glint / robe flicker every other frame.
    if cls_name == "knight" and frame % 2 == 0:
        surf.fill(PALETTE['y'], (ox + 11 * PIX, oy + 7 * PIX, PIX, PIX))
    if cls_name == "wizard":
        flame = PALETTE['C'] if frame % 2 == 0 else PALETTE['W']
        surf.fill(flame, (ox + 2 * PIX, oy + 10 * PIX, PIX, PIX))
    if cls_name == "rogue" and direction in ("down", "up"):
        blink = PALETTE['C'] if frame in (1, 3) else PALETTE['W']
        surf.fill(blink, (ox + 7 * PIX, oy + 4 * PIX, PIX, PIX))


def draw_legs(surf, ox, oy, direction, frame, boot, boot_hi):
    """Procedurally draw animated boots below the body (rows ~11-14)."""
    lo, ro = WALK[frame]
    base_y = oy + 12 * PIX

    def foot(cx, dy):
        x = ox + cx * PIX
        y = base_y + dy * PIX
        surf.fill(boot, (x, y, 2 * PIX, 2 * PIX))
        surf.fill(boot_hi, (x, y, 2 * PIX, PIX))

    if direction in ("down", "up"):
        foot(5, lo)
        foot(9, ro)
    else:  # side view: front + back foot
        foot(6, lo)
        foot(9, ro)


def make_player_sheet(name, art):
    sheet = pygame.Surface((CELL * 4, CELL * 4), pygame.SRCALPHA)
    # Row order must match renderer: DOWN, UP, LEFT, RIGHT
    rows = [
        ("down", art["down"], False),
        ("up", art["up"], False),
        ("side", art["side"], True),    # LEFT  = flipped side
        ("side", art["side"], False),   # RIGHT = side
    ]
    for r, (direction, body, flip) in enumerate(rows):
        for f in range(4):
            cell = pygame.Surface((CELL, CELL), pygame.SRCALPHA)
            bob = BOB[f] * PIX
            sway = (-1 if f == 1 else (1 if f == 3 else 0)) * PIX
            blit_pixmap(cell, body, sway, bob)
            draw_legs(cell, sway, bob, direction, f, art["boot"], art["boot_hi"])
            draw_class_fx(cell, name, direction, f, sway, bob)
            if flip:
                cell = pygame.transform.flip(cell, True, False)
            sheet.blit(cell, (f * CELL, r * CELL))
    os.makedirs("assets/players", exist_ok=True)
    pygame.image.save(sheet, f"assets/players/{name}.png")


# ==================================================================
#  MONSTERS  (single authored pose; 2-frame idle wobble generated)
# ==================================================================

MONSTERS = {
    "rat": [
        "................",
        "................",
        "................",
        "................",
        "...........FF...",
        "..F.......FffF..",
        ".FfF.....FfffF..",
        ".FffFFFFFffffF..",
        ".FffffffffffEF..",
        ".FffffffffffjF..",
        "..FffffffffFF...",
        "...FFFFFFFF.....",
        "...j..j.j..j....",
        "................",
        "................",
        "................",
    ],
    "goblin": [
        "................",
        "................",
        "..q..........q..",
        "..Oq........qO..",
        "..OOq......qOO..",
        "...OOqqqqqqOO...",
        "...OOEqqqEqOO...",
        "....OqqqqqqO....",
        "....OqWWWqqO....",
        "...OOOOOOOOOO...",
        "..OqOOOOOOOOqO..",
        "..q.OOOOOOOO.q..",
        "....OOO..OOO....",
        "....qq....qq....",
        "................",
        "................",
    ],
    "orc": [
        "................",
        "................",
        "...nn....nn.....",
        "..nNNn..nNNn....",
        "..nNNNNNNNNNn...",
        "..nNyNNNNyNn....",
        "..nNNNNNNNNNn...",
        "..nNWNNNNWNn....",
        "...nNNNNNNn.....",
        "..NNNNNNNNNN....",
        ".NnNNNNNNNNnN...",
        ".N..NNNNNN..N...",
        "....NNN.NNN.....",
        "....nn...nn.....",
        "................",
        "................",
    ],
    "troll": [
        "................",
        "................",
        "...tt....tt.....",
        "..tTTttttTTt....",
        "..tTWtTTtTWt....",
        "..tTTTTTTTTt....",
        "..tTTTWWTTTt....",
        "...tTTTTTTt.....",
        "..TTTTTTTTTT....",
        ".TtTTTTTTTTtT...",
        ".Tt.TTTTTT.tT...",
        ".t..TTTTTT..t...",
        "....TTT.TTT.....",
        "....tt...tt.....",
        "................",
        "................",
    ],
    "wraith": [
        "................",
        ".....aaaa.......",
        "....aAAAAa......",
        "...aAWAAWAa.....",
        "...aAAAAAAa.....",
        "...aAEAAEAa.....",
        "...aAAAAAAa.....",
        "...aAAAAAAa.....",
        "...aAAAAAAa.....",
        "...aAAAAAAa.....",
        "...aAaAaAaa.....",
        "...a.a.a.a......",
        "....a.a.a.......",
        "................",
        "................",
        "................",
    ],
    "dread knight": [
        "................",
        "...K.....K......",
        "...KK...KK......",
        "...fKKKKKKf.....",
        "..fSSSSSSSSf....",
        "..fSKKKKKKSf....",
        "..fSEEKKEESf....",
        "..fSKKKKKKSf....",
        "...fSSSSSSf.....",
        "..rfSSSSSSfr....",
        ".rRfSSSSSSfRr...",
        ".rR.fSSSSf.Rr...",
        "....ff..ff......",
        "...KK....KK.....",
        "................",
        "................",
    ],
    "dragon": [
        "................",
        ".r......rr......",
        ".Rr....rRRr.....",
        "..Rr..rRRRr.....",
        "...RRRRRRRr.....",
        "..RRRRRRRRRr....",
        "..RRyRRRRRRr....",
        "..RRRRRRRRoo....",
        "...RRRRRRoooo...",
        "....RRRRRoo.....",
        "...RRRRRRR......",
        "..Rr..RRRRr.....",
        ".rr....rRRr.....",
        ".........rr.....",
        "................",
        "................",
    ],
    "mimic": [
        "................",
        "................",
        "..wwwwwwwwww....",
        ".wWwWwWwWwWww...",
        ".wwwwwwwwwwww...",
        "..MMMMMMMMMM....",
        "..MWMWMWMWMM....",
        "..MMMMMMMMMM....",
        ".wwwwwwwwwwww...",
        ".wGwwwwwwwwGw...",
        ".wwwwwwwwwwww...",
        ".wwwwwwwwwwww...",
        "..w..w..w..w....",
        "................",
        "................",
        "................",
    ],
    "chest": [
        "................",
        "................",
        "................",
        "...wwwwwwww.....",
        "..wGGGGGGGGw....",
        "..whhhhhhhhw....",
        "..wwwwwwwwww....",
        "..whhhGGhhhw....",
        "..whhhGGhhhw....",
        "..whhhhhhhhw....",
        "..wwwwwwwwww....",
        "................",
        "................",
        "................",
        "................",
        "................",
    ],
    "locked chest": [
        "................",
        "................",
        "................",
        "...wwwwwwww.....",
        "..wGGGGGGGGw....",
        "..whhhhhhhhw....",
        "..wwwwwwwwww....",
        "..whhhGGhhhw....",
        "..whhKGGKhhw....",
        "..whhhKKhhhw....",
        "..wwwwwwwwww....",
        "................",
        "................",
        "................",
        "................",
        "................",
    ],
}


# Closed-jaw pose so the mimic can chomp between frames.
MIMIC_CLOSED = [
    "................",
    "................",
    "................",
    "..wwwwwwwwww....",
    ".wWwWwWwWwWww...",
    ".wWWWWWWWWWWw...",
    ".wwwwwwwwwwww...",
    "..wwwwwwwwww....",
    ".wwwwwwwwwwww...",
    ".wGwwwwwwwwGw...",
    ".wwwwwwwwwwww...",
    ".wwwwwwwwwwww...",
    "..w..w..w..w....",
    "................",
    "................",
    "................",
]

# Per-monster idle animation: vertical bob + horizontal sway across the 4
# frames, an optional alternate pose (`alt` on `alt_frames`), and a named
# flourish so every bad guy moves in its own way.
MONSTER_ANIM = {
    "rat":          dict(bob=[0, 0, 0, 0],    sway=[0, 1, 0, -1], fx="rat"),
    "goblin":       dict(bob=[0, -1, 0, -1],  sway=[0, 0, 0, 0],  fx="blink"),
    "orc":          dict(bob=[0, -1, -1, 0],  sway=[0, 0, 0, 0],  fx=None),
    "troll":        dict(bob=[0, 0, -1, 0],   sway=[-1, 0, 1, 0], fx=None),
    "wraith":       dict(bob=[0, -1, -2, -1], sway=[0, 1, 0, -1], fx="flare"),
    "dread knight": dict(bob=[0, -1, 0, -1],  sway=[0, 0, 0, 0],  fx="flare"),
    "dragon":       dict(bob=[0, -1, 0, -1],  sway=[0, 0, 0, 0],  fx="wing"),
    "mimic":        dict(bob=[0, 0, 0, 0],    sway=[0, 0, 0, 0],  fx=None,
                         alt=MIMIC_CLOSED, alt_frames=(2, 3)),
    "chest":        dict(bob=[0, 0, 0, 0],    sway=[0, 0, 0, 0],  fx="gleam"),
    "locked chest": dict(bob=[0, 0, 0, 0],    sway=[0, 0, 0, 0],  fx="gleam"),
}


def _recolor(surf, frm, to):
    """Swap every art-pixel of color `frm` to `to` (used for eye blinks)."""
    for x in range(0, CELL, PIX):
        for y in range(0, CELL, PIX):
            if surf.get_at((x, y))[:3] == frm:
                surf.fill(to, (x, y, PIX, PIX))


def draw_monster_fx(surf, fx, frame, ox, oy):
    """Signature per-frame flourish for each bad guy."""
    P = PALETTE
    if fx == "blink":
        # Eyes shut briefly on one beat.
        if frame == 2:
            _recolor(surf, P['E'], P['q'])
    elif fx == "flare":
        # Glowing eyes pulse brighter on the off-beats.
        if frame in (1, 3):
            _recolor(surf, P['E'], (255, 176, 96))
    elif fx == "wing":
        # Membrane wings flap up and down, plus a drifting smoke wisp.
        wy = 1 if frame in (1, 2) else 4
        surf.fill(P['r'], (ox + 0 * PIX, oy + wy * PIX, 2 * PIX, PIX))
        surf.fill(P['r'], (ox + 13 * PIX, oy + wy * PIX, 2 * PIX, PIX))
        if frame in (0, 2):
            surf.fill(P['F'], (ox + 13 * PIX, oy + 8 * PIX, PIX, PIX))
    elif fx == "rat":
        # Twitchy tail that wags up and down off the left flank.
        ty = 6 if frame in (1, 3) else 8
        surf.fill(P['j'], (ox + 0 * PIX, oy + ty * PIX, PIX, PIX))
        surf.fill(P['j'], (ox + 1 * PIX, oy + (ty + 1) * PIX, PIX, PIX))
    elif fx == "gleam":
        # A sparkle travelling across the gold band.
        sx = 4 + frame * 2
        surf.fill(P['W'], (ox + sx * PIX, oy + 4 * PIX, PIX, PIX))


def make_monster_sheet(name, art):
    """4-frame idle loop (128x32) saved to assets/sprites/<name>.png."""
    cfg = MONSTER_ANIM.get(name, dict(bob=[0, -1, 0, -1], sway=[0, 0, 0, 0], fx=None))
    bob = cfg.get("bob", [0, 0, 0, 0])
    sway = cfg.get("sway", [0, 0, 0, 0])
    alt = cfg.get("alt")
    alt_frames = cfg.get("alt_frames", ())

    sheet = pygame.Surface((CELL * 4, CELL), pygame.SRCALPHA)
    for f in range(4):
        cell = pygame.Surface((CELL, CELL), pygame.SRCALPHA)
        body = alt if (alt is not None and f in alt_frames) else art
        ox = sway[f] * PIX
        oy = bob[f] * PIX
        blit_pixmap(cell, body, ox, oy)
        if cfg.get("fx"):
            draw_monster_fx(cell, cfg["fx"], f, ox, oy)
        sheet.blit(cell, (f * CELL, 0))
    os.makedirs("assets/sprites", exist_ok=True)
    safe = name.replace(" ", "_")
    pygame.image.save(sheet, f"assets/sprites/{safe}.png")


# ==================================================================
#  NPCs  (town/overworld folk -- animated like the player classes:
#  authored body + procedural legs + a 4-frame idle loop with a small
#  per-NPC flourish so they feel alive while standing around)
# ==================================================================

VILLAGER = [
    "................",
    "................",
    ".....hhhhh......",
    "....hkkkkkh.....",
    "....kkkkkkk.....",
    "....kKkkKkk.....",
    "....kkkkkkk.....",
    "....BBBBBBB.....",
    "...BBBBBBBBB....",
    "...BBwwwwwBB....",
    "...BBBBBBBBB....",
    "...BBBBBBBBB....",
]
FARMER = [
    "................",
    "...GGGGGGGG.....",
    "....GGGGGG......",
    "....kkkkkk......",
    "....kKkkKk......",
    "....kkkkkk......",
    "....RRRRRR......",
    "...RRBBBBRR.....",
    "...RBBBBBBR.....",
    "...RBBBBBBR.....",
    "...BBBBBBBB.....",
    "...BBBBBBBB.....",
]
DRUID = [
    "................",
    ".....nnnnn......",
    "....nNNNNNn.....",
    "....nkkkkkn.....",
    "....nkNkNkn.....",
    "....kWWWWWk.....",
    "....WWWWWWW.....",
    "...NNNNNNNNN....",
    "..NNNNNNNNNNN...",
    "..NNNGGGNNNN....",
    "..NNNNNNNNNN....",
    "..NNNNNNNNNN....",
]
MERCHANT = [
    "................",
    ".....wwww.......",
    "....whhhhw......",
    "....wKKKKw......",
    "....wGKKGw......",
    "....wKKKKw......",
    "...wwwwwwww.....",
    "..wwwwwwwwww....",
    "..wwwGGwwwww....",
    "..wwwwwwwwww....",
    "..wwwwwwwwww....",
    "..wwwwwwwwww....",
]
GHOST = [
    "................",
    ".....AAAA.......",
    "....AAAAAA......",
    "...AAAAAAAA.....",
    "...AAKAAKAA.....",
    "...AAAAAAAA.....",
    "...AAAAAAAA.....",
    "...AAAAAAAA.....",
    "...AAAAAAAA.....",
    "...AaAaAaAa.....",
    "...a.a.a.a......",
    "....a.a.a.......",
]

NPC_ART = {
    "villager": dict(body=VILLAGER, boot=(80, 50, 30), boot_hi=(120, 78, 46),
                     fx="wave", float=False),
    "farmer":   dict(body=FARMER, boot=(90, 60, 30), boot_hi=(132, 92, 48),
                     fx="wheat", float=False),
    "druid":    dict(body=DRUID, boot=(60, 45, 25), boot_hi=(96, 72, 40),
                     fx="staff", float=False),
    "merchant": dict(body=MERCHANT, boot=(60, 40, 22), boot_hi=(96, 64, 36),
                     fx="coin", float=False),
    "ghost_npc": dict(body=GHOST, boot=None, boot_hi=None,
                      fx="ghost", float=True),
}

# Idle loop: gentle bob/sway in place instead of a full stride.
NPC_BOB = [0, -1, -1, 0]
NPC_FLOAT_BOB = [0, -1, -2, -1]


def draw_npc_legs(surf, ox, oy, frame, boot, boot_hi):
    """Planted feet with a subtle weight shift (one foot lifts per beat)."""
    base_y = oy + 12 * PIX
    lo = -1 if frame == 1 else 0
    ro = -1 if frame == 3 else 0

    def foot(cx, dy):
        x = ox + cx * PIX
        y = base_y + dy * PIX
        surf.fill(boot, (x, y, 2 * PIX, 2 * PIX))
        surf.fill(boot_hi, (x, y, 2 * PIX, PIX))

    foot(5, lo)
    foot(9, ro)


def draw_npc_fx(surf, fx, frame, ox=0, oy=0):
    """Per-frame flourish that gives each NPC a bit of arcade life."""
    if fx == "wave":
        # Right hand raised on the off-beats -- a friendly wave.
        raised = frame in (1, 3)
        hy = 6 if raised else 8
        surf.fill(PALETTE['B'], (ox + 11 * PIX, oy + 7 * PIX, PIX, PIX))   # arm
        surf.fill(PALETTE['k'], (ox + 11 * PIX, oy + hy * PIX, PIX, PIX))  # hand
    elif fx == "wheat":
        # Wheat stalk that sways side to side.
        sway = (1 if frame in (1, 2) else 0) * PIX
        surf.fill(PALETTE['n'], (ox + 12 * PIX + sway, oy + 7 * PIX, PIX, 3 * PIX))
        surf.fill(PALETTE['G'], (ox + 12 * PIX + sway, oy + 5 * PIX, PIX, 2 * PIX))
    elif fx == "staff":
        # Wooden staff with a gem that flickers cyan/white.
        surf.fill(PALETTE['w'], (ox + 12 * PIX, oy + 5 * PIX, PIX, 8 * PIX))
        gem = PALETTE['C'] if frame % 2 == 0 else PALETTE['W']
        surf.fill(gem, (ox + 12 * PIX - (PIX // 1), oy + 4 * PIX, 2 * PIX, PIX))
        surf.fill(gem, (ox + 12 * PIX, oy + 3 * PIX, PIX, PIX))
    elif fx == "coin":
        # Gold coin tossed/bobbing in the merchant's hand.
        cy = 6 if frame in (1, 2) else 8
        surf.fill(PALETTE['k'], (ox + 12 * PIX, oy + 9 * PIX, PIX, PIX))  # hand
        surf.fill(PALETTE['G'], (ox + 12 * PIX, oy + cy * PIX, PIX, PIX))
        surf.fill(PALETTE['y'], (ox + 12 * PIX, oy + cy * PIX, PIX, PIX // 1))
    elif fx == "ghost":
        # Eyes glimmer; the float bob carries the rest of the motion.
        glow = PALETTE['W'] if frame % 2 == 0 else PALETTE['C']
        surf.fill(glow, (ox + 5 * PIX, oy + 4 * PIX, PIX, PIX))
        surf.fill(glow, (ox + 8 * PIX, oy + 4 * PIX, PIX, PIX))


def make_npc_sheet(name, art):
    """4-frame idle loop (128x32) saved to assets/npcs/<name>.png."""
    sheet = pygame.Surface((CELL * 4, CELL), pygame.SRCALPHA)
    is_float = art["float"]
    bobs = NPC_FLOAT_BOB if is_float else NPC_BOB
    for f in range(4):
        cell = pygame.Surface((CELL, CELL), pygame.SRCALPHA)
        bob = bobs[f] * PIX
        sway = (-1 if f == 1 else (1 if f == 3 else 0)) * (PIX if not is_float else 0)
        blit_pixmap(cell, art["body"], sway, bob)
        if not is_float:
            draw_npc_legs(cell, sway, bob, f, art["boot"], art["boot_hi"])
        draw_npc_fx(cell, art["fx"], f, sway, bob)
        sheet.blit(cell, (f * CELL, 0))
    os.makedirs("assets/npcs", exist_ok=True)
    pygame.image.save(sheet, f"assets/npcs/{name}.png")


def main():
    for name, art in CLASS_ART.items():
        make_player_sheet(name, art)
        print(f"  player  -> assets/players/{name}.png")
    for name, art in MONSTERS.items():
        make_monster_sheet(name, art)
        print(f"  monster -> assets/sprites/{name.replace(' ', '_')}.png")
    for name, art in NPC_ART.items():
        make_npc_sheet(name, art)
        print(f"  npc     -> assets/npcs/{name}.png")
    print("Arcade sprites generated.")


if __name__ == "__main__":
    main()
