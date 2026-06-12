"""
create_arcade_sprites.py
------------------------------------------------------------------
Generates chunky, 80s-arcade-style pixel-art spritesheets for the
player classes and the dungeon monsters.

Everything is authored on a coarse 16x16 logical grid and blown up so
each "art pixel" becomes a fat block -- the look you'd get on an Atari
or early-NES era machine.  A tight, limited palette keeps the retro
feel consistent across every sprite.

Output (run this file to (re)generate):
    assets/players/<class>.png   128x128  (4 dirs x 4 walk frames, 32px cells)
    assets/sprites/<monster>.png 64x32    (2-frame idle animation, 32px cells)

The renderer loads these and animates them.  Frames are generated
programmatically from hand-authored body art + procedural legs so we
get a full walk cycle without authoring every frame by hand.
"""

import os
import pygame

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
pygame.init()

CELL = 32          # output cell size in screen pixels
GRID = 16          # logical art grid (16x16)
PIX = CELL // GRID  # size of one art-pixel block (2)

# ------------------------------------------------------------------
# Limited retro palette.  '.' = transparent.
# ------------------------------------------------------------------
PALETTE = {
    '.': None,
    'K': (16, 14, 24),     # near-black outline
    'W': (236, 236, 242),  # white
    'S': (176, 186, 202),  # steel
    'D': (96, 106, 128),   # dark steel
    'L': (222, 230, 242),  # light steel highlight
    'R': (214, 48, 48),    # red
    'r': (150, 28, 28),    # dark red
    'G': (246, 206, 54),   # gold
    'g': (182, 140, 22),   # dark gold
    'B': (56, 112, 216),   # blue
    'b': (34, 68, 150),    # dark blue
    'P': (150, 64, 214),   # purple
    'p': (96, 36, 160),    # dark purple
    'C': (78, 216, 255),   # cyan gem / glow
    'N': (52, 168, 80),    # green
    'n': (28, 104, 50),    # dark green
    'k': (242, 188, 138),  # skin
    'j': (202, 142, 98),   # skin shadow
    'w': (122, 80, 40),    # wood / brown
    'o': (236, 124, 42),   # orange
    'y': (250, 236, 124),  # light yellow
    'M': (190, 74, 152),   # magenta / tongue
    'E': (236, 42, 42),    # glowing eye
    'F': (122, 128, 140),  # gray
    'f': (58, 62, 72),     # dark gray
    'A': (132, 206, 255),  # ghost blue
    'a': (74, 150, 210),   # ghost blue shadow
    'h': (118, 80, 44),    # hair / hide brown
    'O': (60, 64, 40),     # olive (goblin)
    'q': (40, 44, 26),     # dark olive
    'T': (120, 150, 90),   # troll green
    't': (78, 104, 56),    # troll dark
    'z': (150, 158, 168),  # bone
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
    (0, 0),    # stand
    (-1, 1),   # left foot up, right planted forward
    (0, 0),    # stand
    (1, -1),   # right foot up
]
# Body bob (art-pixels) per frame -- gentle up/down while walking.
BOB = [0, -1, 0, -1]


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
            blit_pixmap(cell, body, 0, bob)
            draw_legs(cell, 0, bob, direction, f, art["boot"], art["boot_hi"])
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


def make_monster_sheet(name, art):
    """2-frame idle: frame 0 normal, frame 1 squashed+bobbed 1px."""
    sheet = pygame.Surface((CELL * 2, CELL), pygame.SRCALPHA)
    # frame 0
    f0 = pygame.Surface((CELL, CELL), pygame.SRCALPHA)
    blit_pixmap(f0, art, 0, 0)
    sheet.blit(f0, (0, 0))
    # frame 1: nudge down 1 art-pixel for a breathing/hover wobble
    f1 = pygame.Surface((CELL, CELL), pygame.SRCALPHA)
    blit_pixmap(f1, art, 0, PIX)
    sheet.blit(f1, (CELL, 0))
    os.makedirs("assets/sprites", exist_ok=True)
    safe = name.replace(" ", "_")
    pygame.image.save(sheet, f"assets/sprites/{safe}.png")


def main():
    for name, art in CLASS_ART.items():
        make_player_sheet(name, art)
        print(f"  player  -> assets/players/{name}.png")
    for name, art in MONSTERS.items():
        make_monster_sheet(name, art)
        print(f"  monster -> assets/sprites/{name.replace(' ', '_')}.png")
    print("Arcade sprites generated.")


if __name__ == "__main__":
    main()
