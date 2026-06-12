import pygame

# 8-bit retro color palette
PALETTE = {
    ".": None,                  # Transparent
    "k": (12, 12, 16),          # Black
    "w": (230, 230, 235),        # White
    "r": (210, 55, 55),         # Red
    "g": (46, 196, 120),        # Green
    "b": (40, 100, 200),        # Blue
    "y": (235, 195, 45),        # Yellow
    "m": (155, 80, 230),        # Purple
    "c": (45, 175, 205),        # Cyan
    "o": (250, 100, 20),        # Orange
    "p": (240, 150, 150),       # Pink
    "d": (60, 60, 65),          # Dark Gray
    "l": (150, 155, 165),       # Light Gray
    "s": (240, 200, 160),       # Skin tone / Peach
    "e": (120, 75, 35),         # Brown
    "n": (70, 45, 25),          # Dark Brown
    "B": (24, 32, 60),          # Dark Blue (explored wall)
    "G": (20, 50, 25),          # Dark Green (grass/hedge)
    "C": (24, 75, 80),          # Dark Cyan (visible wall)
    "Y": (110, 85, 30),         # Dark Yellow
}

# --- PLAYER CLASSES (16x16 standing patterns) ---
PLAYER_PATTERNS = {
    "knight_down": [
        "....rrrrrr......",
        "...rrlllllrr....",
        "..rllllllllllr..",
        "..rllkkkkkkllr..",
        "..rllllllllllr..",
        "...rllllllll....",
        "....llllll......",
        "..ddllllllss....",
        ".dddllllllsss...",
        "bdddllllllsssb..",
        "b..dllllllss..b.",
        "b..dllllllss..b.",
        "....llllll......",
        "....ll..ll......",
        "...lll..lll.....",
        "...kk....kk....."
    ],
    "knight_up": [
        "....rrrrrr......",
        "...rrlllllrr....",
        "..rllllllllllr..",
        "..rllllllllllr..",
        "..rllllllllllr..",
        "...rllllllll....",
        "....llllll......",
        "..ddllllllss....",
        ".dddllllllsss...",
        "bdddllllllsssb..",
        "b..dllllllss..b.",
        "b..dllllllss..b.",
        "....llllll......",
        "....ll..ll......",
        "...lll..lll.....",
        "...kk....kk....."
    ],
    "knight_left": [
        "......rrrrrr....",
        ".....rrlllllrr..",
        "....rllllllllllr",
        "...rllkkkkllll..",
        "....rllllllllllr",
        ".....rllllllll..",
        "......llllll....",
        ".....bbddddd....",
        "....bbbddddd....",
        "....bbbddddd....",
        "....b..ddddd....",
        ".......ddddd....",
        "......llllll....",
        "......ll..ll....",
        ".....lll..lll...",
        ".....kk....kk..."
    ],
    "knight_right": [
        "....rrrrrr......",
        "...rrlllllrr....",
        "..rllllllllllr..",
        "....llllkkkllr..",
        "..rllllllllllr..",
        "...rllllllll....",
        "....llllll......",
        "....dddddbb.....",
        "....dddddbbb....",
        "....dddddbbb....",
        "....ddddd..b....",
        "....ddddd.......",
        "....llllll......",
        "....ll..ll......",
        "...lll..lll.....",
        "...kk....kk....."
    ],
    "wizard_down": [
        ".......b........",
        "......bbb.......",
        ".....bbbbb......",
        "....bbbbbbb.....",
        "...bbbbbbbbb....",
        "..yyyyyyyyyyy...",
        "....ssXXss......",
        "....sYXXYs......",
        "....sXXXXs......",
        "..w.mmmmmm......",
        ".wwwmmmmmm......",
        "e.wemmmmmm......",
        ".e..mm..mm......",
        ".e..mm..mm......",
        ".e.mmm..mmm.....",
        "...kk....kk....."
    ],
    "wizard_up": [
        ".......b........",
        "......bbb.......",
        ".....bbbbb......",
        "....bbbbbbb.....",
        "...bbbbbbbbb....",
        "..yyyyyyyyyyy...",
        "....ssssss......",
        "....ssssss......",
        "....ssssss......",
        "....mmmmmm......",
        "....mmmmmm......",
        "....mmmmmm......",
        "....mm..mm......",
        "....mm..mm......",
        "...mmm..mmm.....",
        "...kk....kk....."
    ],
    "wizard_left": [
        "......b.........",
        ".....bbb........",
        "....bbbbb.......",
        "...bbbbbbb......",
        "..bbbbbbbbb.....",
        ".yyyyyyyyyyy....",
        "....ssXXss......",
        "...sYXXXXs......",
        "....sXXXXs......",
        "..w.mmmmmm......",
        ".wwwmmmmmm......",
        "e.wemmmmmm......",
        ".e..mm..mm......",
        ".e..mm..mm......",
        ".e.mmm..mmm.....",
        "...kk....kk....."
    ],
    "wizard_right": [
        "........b.......",
        ".......bbb......",
        "......bbbbb.....",
        ".....bbbbbbb....",
        "....bbbbbbbbb...",
        "....yyyyyyyyyyy.",
        "......ssXXss....",
        "......sXXXXYs...",
        "......sXXXXs....",
        "......mmmmmm.w..",
        "......mmmmmmwww.",
        "......mmmmmmew.e",
        "......mm..mm..e.",
        "......mm..mm..e.",
        ".....mmm..mmme..",
        ".....kk....kk..."
    ],
    "rogue_down": [
        ".....ggggg......",
        "....ggggggg.....",
        "...ggggggggg....",
        "...ggkkkkkgg....",
        "...ggYkkKYgg....",
        "...ggkkkkkgg....",
        "....ggggggg.....",
        "....eeeeee......",
        "..h.eeeeee......",
        ".hhheeeeee......",
        "p.hpeeeeee......",
        "p.h.ee..ee......",
        "p...ee..ee......",
        "....ee..ee......",
        "...eee..eee.....",
        "...kk....kk....."
    ],
    "rogue_up": [
        ".....ggggg......",
        "....ggggggg.....",
        "...ggggggggg....",
        "...ggggggggg....",
        "...ggggggggg....",
        "...ggggggggg....",
        "....ggggggg.....",
        "....eeeeee......",
        "....eeeeee......",
        "....eeeeee......",
        "....eeeeee......",
        "....ee..ee......",
        "....ee..ee......",
        "....ee..ee......",
        "...eee..eee.....",
        "...kk....kk....."
    ],
    "rogue_left": [
        "......ggggg.....",
        ".....ggggggg....",
        "....ggggggggg...",
        "....ggkkkkkgg...",
        "....gYkkkkkgg...",
        "....ggkkkkkgg...",
        ".....ggggggg....",
        ".....eeeeee.....",
        "..h..eeeeee.....",
        ".hhh.eeeeee.....",
        "p.hp.eeeeee.....",
        "p.h..ee..ee.....",
        "p....ee..ee.....",
        ".....ee..ee.....",
        "....eee..eee....",
        "....kk....kk...."
    ],
    "rogue_right": [
        "....ggggg.......",
        "...ggggggg......",
        "..ggggggggg.....",
        "..ggkkkkkgg.....",
        "..ggkkkkkYg.....",
        "..ggkkkkkgg.....",
        "...ggggggg......",
        "....eeeeee......",
        "....eeeeee..h...",
        "....eeeeee.hhh..",
        "....eeeeee.php..",
        "....ee..ee..h.p.",
        "....ee..ee....p.",
        "....ee..ee......",
        "...eee..eee.....",
        "...kk....kk....."
    ],
}

# --- MONSTER & NPC CLASSES (16x16 patterns, 2 frames each) ---
MONSTER_PATTERNS = {
    "rat": [
        [
            "................",
            "................",
            "................",
            "................",
            "................",
            "........dd......",
            "......ddccdd....",
            "....ddccccccdd..",
            "....dcccccckcd..",
            "...dcccccccaad..",
            "..dccccccccad...",
            "..dccccccccad...",
            "..ddccccccddd...",
            "...dd..dd..dd...",
            "....a...a...a...",
            "....a...a...a..."
        ],
        [
            "................",
            "................",
            "................",
            "................",
            "........d.......",
            "......ddcdd.....",
            "....ddccccccdd..",
            "....dcccccckcd..",
            "...dcccccccaad..",
            "..dccccccccad...",
            "..dccccccccad...",
            "..ddccccccddd...",
            "...dd..dd..dd...",
            "....a...a...aa..",
            "....a...a....a..",
            "....a...a....a.."
        ]
    ],
    "goblin": [
        [
            "......gggg......",
            "....gggggggg....",
            "...gkkggggkkg...",
            "...gkrggggkrg...",
            "...gggggggggg...",
            "....gggggggg....",
            "......gggg......",
            "....eeddddee....",
            "...eeeddddeee...",
            "...eeddddddee...",
            "...e.dddddde.e..",
            ".....dddddd.....",
            ".....dd..dd.....",
            "....ddd..ddd....",
            "....ee....ee....",
            "....kk....kk...."
        ],
        [
            "......gggg......",
            "....gggggggg....",
            "...gkkggggkkg...",
            "...gkrggggkrg...",
            "...gggggggggg...",
            "....gggggggg....",
            "......gggg......",
            "....eeddddee....",
            "...eeeddddeee...",
            "...eeddddddee...",
            "...e.dddddde.e..",
            ".....dddddd.....",
            ".....dd..dd.....",
            ".....dd..dd.....",
            ".....ee..ee.....",
            ".....kk..kk....."
        ]
    ],
    "orc": [
        [
            ".....ggggg......",
            "....ggggggg.....",
            "...ggkkkGGkg....",
            "...gkykkkykg....",
            "...ggwwGwwgg....",
            "....ggggggg.....",
            "....ddddddd.....",
            "...ddddddddd....",
            "..ldddddddddl...",
            "..ldddddddddl...",
            "..ldddddddddl...",
            "...ddddddddd....",
            "....dd...dd.....",
            "....dd...dd.....",
            "....ee...ee.....",
            "....kk...kk....."
        ],
        [
            ".....ggggg......",
            "....ggggggg.....",
            "...ggkkkGGkg....",
            "...gkykkkykg....",
            "...ggwwGwwgg....",
            "....ggggggg.....",
            "....ddddddd.....",
            "...ddddddddd....",
            "..ldddddddddl...",
            "..ldddddddddl...",
            "..ldddddddddl...",
            "...ddddddddd....",
            "....dd...dd.....",
            "....dd...dd.....",
            "....ee...ee.....",
            "....kk...kk....."
        ]
    ],
    "troll": [
        [
            "...ddddddddd....",
            "..ddddddddddd...",
            ".ddkkdddddkkdd..",
            ".ddyydddddyydd..",
            ".ddddddddddddd..",
            "..ddddddddddd...",
            "...ddddddddd....",
            "....eeeeeee.....",
            "...eeeeeeeee.a..",
            "..eeeeeeeeee.a..",
            "..eeeeeeeeee.a..",
            "...eeeeeeeee.a..",
            "....eeeeeee..a..",
            "....ee...ee.....",
            "....ee...ee.....",
            "....kk...kk....."
        ],
        [
            "...ddddddddd....",
            "..ddddddddddd...",
            ".ddkkdddddkkdd..",
            ".ddyydddddyydd..",
            ".ddddddddddddd..",
            "..ddddddddddd...",
            "...ddddddddd....",
            "....eeeeeee..a..",
            "...eeeeeeeee.a..",
            "..eeeeeeeeee.a..",
            "..eeeeeeeeee.a..",
            "...eeeeeeeee....",
            "....eeeeeee.....",
            "....ee...ee.....",
            "....ee...ee.....",
            "....kk...kk....."
        ]
    ],
    "wraith": [
        [
            ".....ccccc......",
            "....cccccccc....",
            "...cckkcckkcc...",
            "...ccwwccwwcc...",
            "...cccccccccc...",
            "....cccccccc....",
            ".....cccccc.....",
            ".....cccccc.....",
            "....cccccccc....",
            "....cccccccc....",
            ".....cccccc.....",
            ".....cccccc.....",
            "......cccc......",
            "......cccc......",
            ".......cc.......",
            "................"
        ],
        [
            ".....ccccc......",
            "....cccccccc....",
            "...cckkcckkcc...",
            "...ccwwccwwcc...",
            "...cccccccccc...",
            "....cccccccc....",
            ".....cccccc.....",
            ".....cccccc.....",
            "....cccccccc....",
            ".....ccccccc....",
            "......cccccc....",
            "......cccccc....",
            ".......cccc.....",
            ".......cccc.....",
            "........cc......",
            "................"
        ]
    ],
    "dread_knight": [
        [
            "....kkkkkk......",
            "...kkddddkk.....",
            "..kkddddddkk....",
            "..kkdrrrrdkk....",
            "..kkddddddkk....",
            "...kkddddkk.....",
            "....kkkkkk......",
            "....llllll......",
            "...llllllll.....",
            "..llllllllll....",
            "..llllllllll....",
            "...llllllll.....",
            "....llllll......",
            "....ll..ll......",
            "...lll..lll.....",
            "...kk....kk....."
        ],
        [
            "....kkkkkk......",
            "...kkddddkk.....",
            "..kkddddddkk....",
            "..kkdrrrrdkk....",
            "..kkddddddkk....",
            "...kkddddkk.....",
            "....kkkkkk......",
            "....llllll......",
            "...llllllll.....",
            "..llllllllll....",
            "..llllllllll....",
            "...llllllll.....",
            "....llllll......",
            "....ll..ll......",
            "....ll..ll......",
            "....kk..kk......"
        ]
    ],
    "dragon": [
        [
            "......rrrrrr....",
            "....rrrrrrrrrr..",
            "...rrkkrrrkkrrr.",
            "..rryyrrryyrrr..",
            "..rrrrrrrrrrrr..",
            "...rrrrrrrrrr...",
            "....rrrrrrrr....",
            "....yyyyyyyy....",
            "...yyyyyyyyy....",
            "..yyyyyyyyyy....",
            "..yyyyyyyyyy....",
            "...yyyyyyyyy....",
            "....yyyyyy......",
            "....yy..yy......",
            "....yy..yy......",
            "....kk..kk......"
        ],
        [
            "......rrrrrr....",
            "....rrrrrrrrrr..",
            "...rrkkrrrkkrrr.",
            "..rryyrrryyrrr..",
            "..rrrrrrrrrrrr..",
            "...rrrrrrrrrr...",
            "....rrrrrrrr....",
            "....yyyyyyyy....",
            "...yyyyyyyyy....",
            "..yyyyyyyyyy....",
            "..yyyyyyyyyy....",
            "...yyyyyyyyy....",
            "....yyyyyy......",
            "....yy..yy......",
            "...yyy..yyy.....",
            "...kk....kk....."
        ]
    ],
    "merchant": [
        [
            ".....nnnnn......",
            "....nnnnnnn.....",
            "...nnkkkkknn....",
            "...nkykkkyn.....",
            "...nnkkkkknn....",
            "....nnnnnnn.....",
            ".....eeeee......",
            "....eeeeeee.....",
            "...eeeeeeeee....",
            "...eeeeeeeee.y..",
            "...eeeeeeeee.y..",
            "....eeeeeee.....",
            ".....ee.ee......",
            ".....ee.ee......",
            "....eee.eee.....",
            "....kk...kk....."
        ],
        [
            ".....nnnnn......",
            "....nnnnnnn.....",
            "...nnkkkkknn....",
            "...nkykkkyn.....",
            "...nnkkkkknn....",
            "....nnnnnnn.....",
            ".....eeeee......",
            "....eeeeeee.....",
            "...eeeeeeeee.y..",
            "...eeeeeeeee.y..",
            "...eeeeeeeee....",
            "....eeeeeee.....",
            ".....ee.ee......",
            ".....ee.ee......",
            ".....ee.ee......",
            ".....kk.kk......"
        ]
    ],
    "villager": [
        [
            ".....nnnnn......",
            "....nnnnnnn.....",
            "...nnssXssnn....",
            "...nssXkkXssn...",
            "...nssXXXXssn...",
            "....sssssss.....",
            ".....bbbbb......",
            "....bbbbbbb.....",
            "...bbbbbbbbb....",
            "...bbbbbbbbb....",
            "....bbbbbbb.....",
            ".....bb.bb......",
            ".....ee.ee......",
            ".....ee.ee......",
            "....eee.eee.....",
            "....kk...kk....."
        ],
        [
            ".....nnnnn......",
            "....nnnnnnn.....",
            "...nnssXssnn....",
            "...nssXkkXssn...",
            "...nssXXXXssn...",
            "....sssssss.....",
            ".....bbbbb......",
            "....bbbbbbb.....",
            "...bbbbbbbbb....",
            "...bbbbbbbbb....",
            "....bbbbbbb.....",
            ".....bb.bb......",
            ".....ee.ee......",
            ".....ee.ee......",
            ".....ee.ee......",
            ".....kk.kk......"
        ]
    ],
    "farmer": [
        [
            ".....yyyyy......",
            "....yyyyyyy.....",
            "...yyssXssyy....",
            "..yyssXkkXssyy..",
            "...yysXXXXsyy...",
            "....sssssss.....",
            ".....rrrrr......",
            "....bbbbbbb.....",
            "...bbbbbbbbb.w..",
            "...bbbbbbbbb.w..",
            "....bbbbbbb..w..",
            ".....bb.bb......",
            ".....ee.ee......",
            ".....ee.ee......",
            "....eee.eee.....",
            "....kk...kk....."
        ],
        [
            ".....yyyyy......",
            "....yyyyyyy.....",
            "...yyssXssyy....",
            "..yyssXkkXssyy..",
            "...yysXXXXsyy...",
            "....sssssss.....",
            ".....rrrrr......",
            "....bbbbbbb..w..",
            "...bbbbbbbbb.w..",
            "...bbbbbbbbb.w..",
            "....bbbbbbb.....",
            ".....bb.bb......",
            ".....ee.ee......",
            ".....ee.ee......",
            ".....ee.ee......",
            ".....kk.kk......"
        ]
    ],
    "ghost_npc": [
        [
            ".....ccccc......",
            "....cccccccc....",
            "...cckkcckkcc...",
            "...ccwwccwwcc...",
            "...cccccccccc...",
            "....cccccccc....",
            ".....cccccc.....",
            ".....cccccc.....",
            "....cccccccc....",
            "....cccccccc....",
            ".....cccccc.....",
            ".....cccccc.....",
            "......cccc......",
            "......cccc......",
            ".......cc.......",
            "................"
        ],
        [
            ".....ccccc......",
            "....cccccccc....",
            "...cckkcckkcc...",
            "...ccwwccwwcc...",
            "...cccccccccc...",
            "....cccccccc....",
            ".....cccccc.....",
            ".....cccccc.....",
            "....cccccccc....",
            ".....ccccccc....",
            "......cccccc....",
            "......cccccc....",
            ".......cccc.....",
            ".......cccc.....",
            "........cc......",
            "................"
        ]
    ],
    "druid": [
        [
            ".....ggggg......",
            "....ggggggg.....",
            "...ggssXssgg....",
            "...gssXkkXssg...",
            "...gwwwwwgwwg...",
            "....wwwwwww.....",
            ".....ggggg......",
            "....ggggggg.....",
            "...ggggggggg.a..",
            "...ggggggggg.a..",
            "...ggggggggg.a..",
            "....ggggggg.....",
            ".....gg.gg......",
            ".....gg.gg......",
            "....ggg.ggg.....",
            "....kk...kk....."
        ],
        [
            ".....ggggg......",
            "....ggggggg.....",
            "...ggssXssgg....",
            "...gssXkkXssg...",
            "...gwwwwwgwwg...",
            "....wwwwwww.....",
            ".....ggggg......",
            "....ggggggg..a..",
            "...ggggggggg.a..",
            "...ggggggggg.a..",
            "...ggggggggg....",
            "....ggggggg.....",
            ".....gg.gg......",
            ".....gg.gg......",
            ".....gg.gg......",
            ".....kk.kk......"
        ]
    ],
    "chest": [
        [
            "................",
            "................",
            "....eeeeeeee....",
            "...eeeeeeeeee...",
            "..ellleeeellle..",
            "..ellleeeellle..",
            "..ellleeeellle..",
            "..eeeeeeeeeeee..",
            "..ekkkkkkkkkke..",
            "..ekllllllekke..",
            "..eklkkkkllekke.",
            "..ekkkkkkkkkke..",
            "..eeeeeeeeeeee..",
            "..eeeeeeeeeeee..",
            "...eeeeeeeeee...",
            "....eeeeeeee...."
        ],
        [
            "................",
            "................",
            "....eeeeeeee....",
            "...eeeeeeeeee...",
            "..ellleeeellle..",
            "..ellleeeellle..",
            "..ellleeeellle..",
            "..eeeeeeeeeeee..",
            "..ekkkkkkkkkke..",
            "..ekllllllekke..",
            "..eklkkkkllekke.",
            "..ekkkkkkkkkke..",
            "..eeeeeeeeeeee..",
            "..eeeeeeeeeeee..",
            "...eeeeeeeeee...",
            "....eeeeeeee...."
        ]
    ],
    "locked_chest": [
        [
            "................",
            "................",
            "....eeeeeeee....",
            "...eeeeeeeeee...",
            "..eyyyeeeeyyye..",
            "..eyyyeeeeyyye..",
            "..eyyyeeeeyyye..",
            "..eeeeeeeeeeee..",
            "..ekkkkkkkkkke..",
            "..ekyyyyyyekke..",
            "..ekykkkkyyekke.",
            "..ekkkkkkkkkke..",
            "..eeeeeeeeeeee..",
            "..eeeeeeeeeeee..",
            "...eeeeeeeeee...",
            "....eeeeeeee...."
        ],
        [
            "................",
            "................",
            "....eeeeeeee....",
            "...eeeeeeeeee...",
            "..eyyyeeeeyyye..",
            "..eyyyeeeeyyye..",
            "..eyyyeeeeyyye..",
            "..eeeeeeeeeeee..",
            "..ekkkkkkkkkke..",
            "..ekyyyyyyekke..",
            "..ekykkkkyyekke.",
            "..ekkkkkkkkkke..",
            "..eeeeeeeeeeee..",
            "..eeeeeeeeeeee..",
            "...eeeeeeeeee...",
            "....eeeeeeee...."
        ]
    ],
    "mimic": [
        [
            "....eeeeeeee....",
            "...eeeeeeeeee...",
            "..ellleeeellle..",
            "..ellleeeellle..",
            "..ellleeeellle..",
            "..eeeeeeeeeeee..",
            "..errrrrrrrrre..",
            "..erwkwkwkwrre..",
            "..errrrrrrrrre..",
            "..erpprrpprrre..",
            "..erpprrpprrre..",
            "..ekkkkkkkkkke..",
            "..eeeeeeeeeeee..",
            "..eeeeeeeeeeee..",
            "...eeeeeeeeee...",
            "....eeeeeeee...."
        ],
        [
            "....eeeeeeee....",
            "...eeeeeeeeee...",
            "..ellleeeellle..",
            "..ellleeeellle..",
            "..ellleeeellle..",
            "..eeeeeeeeeeee..",
            "..errrrrrrrrre..",
            "..erwkwkwkwrre..",
            "..errrrrrrrrre..",
            "..erpprrpprrre..",
            "..erpprrpprrre..",
            "..ekkkkkkkkkke..",
            "..eeeeeeeeeeee..",
            "..eeeeeeeeeeee..",
            "...eeeeeeeeee...",
            "....eeeeeeee...."
        ]
    ]
}

# --- ITEM CLASSES (16x16 patterns) ---
ITEM_PATTERNS = {
    "potion": [
        "......ee........",
        "......ee........",
        ".....llll.......",
        ".....llll.......",
        "....llllll......",
        "...llllllll.....",
        "..llllllllll....",
        "..llrrrrrrll....",
        "..lrrrrrrrrl....",
        "..lrrrrrrrrl....",
        "..lrrrrrrrrl....",
        "..llrrrrrrll....",
        "...llllllll.....",
        "....llllll......",
        "................",
        "................"
    ],
    "weapon": [
        "..........ll....",
        ".........lll....",
        "........llll....",
        ".......llll.....",
        "......llll......",
        ".....llll.......",
        "....llll........",
        "...llll.........",
        "..llll..........",
        ".yyyy...........",
        "..ee............",
        ".e..............",
        "................",
        "................",
        "................",
        "................"
    ],
    "bow": [
        "......eeee......",
        "....ee....pp....",
        "...e......pp....",
        "..e.......pp....",
        ".e........pp....",
        ".e........pp....",
        ".e........pp....",
        ".e........pp....",
        ".e........pp....",
        ".e........pp....",
        "..e.......pp....",
        "...e......pp....",
        "....ee....pp....",
        "......eeee......",
        "................",
        "................"
    ],
    "wand": [
        "..........ss....",
        ".........sss....",
        "........ee......",
        ".......ee.......",
        "......ee........",
        ".....ee.........",
        "....ee..........",
        "...ee...........",
        "..ee............",
        ".ee.............",
        "................",
        "................",
        "................",
        "................",
        "................",
        "................"
    ],
    "key": [
        ".....yyyyy......",
        "....yy...yy.....",
        "....yy...yy.....",
        ".....yyyyy......",
        ".......yy.......",
        ".......yy.......",
        ".......yyyy.....",
        ".......yy.......",
        ".......yyyy.....",
        "................",
        "................",
        "................",
        "................",
        "................",
        "................",
        "................"
    ],
    "arrow": [
        "..........ss....",
        ".........ss.....",
        "........ee......",
        ".......ee.......",
        "......ee........",
        ".....ee.........",
        "....ee..........",
        "...ee...........",
        "..ee......aa....",
        ".ee......aa.....",
        "................",
        "................",
        "................",
        "................",
        "................",
        "................"
    ],
}

# --- SPINNING COIN PATTERNS (4 frames) ---
COIN_PATTERNS = [
    [
        "......yyyy......",
        "....yyyyyyyy....",
        "...yyyyyyyyyy...",
        "..yyyyyyyyyyyy..",
        "..yyyyyyyyyyyy..",
        "..yyyyyyyyyyyy..",
        "...yyyyyyyyyy...",
        "....yyyyyyyy....",
        "......yyyy......",
        "................",
        "................",
        "................",
        "................",
        "................",
        "................",
        "................"
    ],
    [
        ".......yy.......",
        "......yyyy......",
        ".....yyyyyy.....",
        "....yyyyyyyy....",
        "....yyyyyyyy....",
        "....yyyyyyyy....",
        ".....yyyyyy.....",
        "......yyyy......",
        ".......yy.......",
        "................",
        "................",
        "................",
        "................",
        "................",
        "................",
        "................"
    ],
    [
        "................",
        ".......yy.......",
        ".......yy.......",
        "......yyyy......",
        "......yyyy......",
        "......yyyy......",
        ".......yy.......",
        ".......yy.......",
        "................",
        "................",
        "................",
        "................",
        "................",
        "................",
        "................",
        "................"
    ],
    [
        ".......yy.......",
        "......yyyy......",
        ".....yyyyyy.....",
        "....yyyyyyyy....",
        "....yyyyyyyy....",
        "....yyyyyyyy....",
        ".....yyyyyy.....",
        "......yyyy......",
        ".......yy.......",
        "................",
        "................",
        "................",
        "................",
        "................",
        "................",
        "................"
    ]
]

# --- MAP TILE PATTERNS (16x16) ---
TILE_PATTERNS = {
    "wall_dungeon": [
        "kkkkkkkkkkkkkkkk",
        "kCCCCCCCCCCCCCCk",
        "kCllllllllllllCk",
        "kClddddddddddlCk",
        "kClddddddddddlCk",
        "kClddddddddddlCk",
        "kCllllllllllllCk",
        "kkkkkkkkkkkkkkkk",
        "kkkkkkkkkkkkkkkk",
        "kCCCCCCCCCCCCCCk",
        "kCllllllllllllCk",
        "kClddddddddddlCk",
        "kClddddddddddlCk",
        "kClddddddddddlCk",
        "kCllllllllllllCk",
        "kkkkkkkkkkkkkkkk"
    ],
    "floor_dungeon": [
        "dddddddddddddddd",
        "dddddddddddddddd",
        "dddkkddddddkkddd",
        "dddkkddddddkkddd",
        "dddddddddddddddd",
        "dddddddddddddddd",
        "dddddddddddddddd",
        "dddddddddddddddd",
        "dddddddddddddddd",
        "dddddddddddddddd",
        "dddkkddddddkkddd",
        "dddkkddddddkkddd",
        "dddddddddddddddd",
        "dddddddddddddddd",
        "dddddddddddddddd",
        "dddddddddddddddd"
    ],
    "wall_wood": [
        "nnnnnnnnnnnnnnnn",
        "neeeeeeeeeeeeeen",
        "neeeeeeeeeeeeeen",
        "nnnnnnnnnnnnnnnn",
        "nnnnnnnnnnnnnnnn",
        "neeeeeeeeeeeeeen",
        "neeeeeeeeeeeeeen",
        "nnnnnnnnnnnnnnnn",
        "nnnnnnnnnnnnnnnn",
        "neeeeeeeeeeeeeen",
        "neeeeeeeeeeeeeen",
        "nnnnnnnnnnnnnnnn",
        "nnnnnnnnnnnnnnnn",
        "neeeeeeeeeeeeeen",
        "neeeeeeeeeeeeeen",
        "nnnnnnnnnnnnnnnn"
    ],
    "wall_fence": [
        "................",
        "....e......e....",
        "....e......e....",
        "eeeeeeeeeeeeeeee",
        "eeeeeeeeeeeeeeee",
        "....e......e....",
        "....e......e....",
        "eeeeeeeeeeeeeeee",
        "eeeeeeeeeeeeeeee",
        "....e......e....",
        "....e......e....",
        "....e......e....",
        "....e......e....",
        "....e......e....",
        "................",
        "................"
    ],
    "wall_stone": [
        "kkkkkkkkkkkkkkkk",
        "kllllllllllllllk",
        "klddddddddddddlk",
        "klddddddddddddlk",
        "kllllllllllllllk",
        "kkkkkkkkkkkkkkkk",
        "kkkkkkkkkkkkkkkk",
        "kllllllllllllllk",
        "klddddddddddddlk",
        "klddddddddddddlk",
        "kllllllllllllllk",
        "kkkkkkkkkkkkkkkk",
        "kkkkkkkkkkkkkkkk",
        "kllllllllllllllk",
        "klddddddddddddlk",
        "kkkkkkkkkkkkkkkk"
    ],
    "wall_hedge": [
        ".....GGGGGG.....",
        "...GGGGGGGGGG...",
        "..GGGGGGGGGGGG..",
        ".GGGGggggGGGGGG.",
        "GGGGggggggggGGGG",
        "GGGGggggggggGGGG",
        "GGGGggggggggGGGG",
        "GGGGggggggggGGGG",
        "GGGGggggggggGGGG",
        "GGGGggggggggGGGG",
        "GGGGggggggggGGGG",
        "GGGGggggggggGGGG",
        ".GGGGggggGGGGGG.",
        "..GGGGGGGGGGGG..",
        "...GGGGGGGGGG...",
        ".....GGGGGG....."
    ],
    "floor_cobble": [
        "dddddddddddddddd",
        "ddlllllddllllldd",
        "dllkkklldlkkklld",
        "dllkddklldkddkld",
        "ddllkkklldlkkldd",
        "ddddlllllddllldd",
        "dddddddddddddddd",
        "dddddddddddddddd",
        "ddlllllddllllldd",
        "dllkkklldlkkklld",
        "dllkddklldkddkld",
        "ddllkkklldlkkldd",
        "ddddlllllddllldd",
        "dddddddddddddddd",
        "dddddddddddddddd",
        "dddddddddddddddd"
    ],
    "floor_soil": [
        "nnnnnnnnnnnnnnnn",
        "nnnnnnnnnnnnnnnn",
        "nnnnnnnnnnnnnnnn",
        "kkkkkkkkkkkkkkkk",
        "....g......g....",
        "nnnnnnnnnnnnnnnn",
        "nnnnnnnnnnnnnnnn",
        "nnnnnnnnnnnnnnnn",
        "kkkkkkkkkkkkkkkk",
        "....g......g....",
        "nnnnnnnnnnnnnnnn",
        "nnnnnnnnnnnnnnnn",
        "nnnnnnnnnnnnnnnn",
        "kkkkkkkkkkkkkkkk",
        "................",
        "................"
    ],
    "floor_cemetery": [
        "GGGGGGGGGGGGGGGG",
        "GGGGGGGGGGGGGGGG",
        "GGGGGGGGGGGGGGGG",
        "GGGGGGGGGGGGGGGG",
        "GGGGGGGGGGGGGGGG",
        "GGGGGGGGGGGGGGGG",
        "GGGGGGGGGGGGGGGG",
        "GGGGGGGGGGGGGGGG",
        "GGGGGGGGGGGGGGGG",
        "GGGGGGGGGGGGGGGG",
        "GGGGGGGGGGGGGGGG",
        "GGGGGGGGGGGGGGGG",
        "GGGGGGGGGGGGGGGG",
        "GGGGGGGGGGGGGGGG",
        "GGGGGGGGGGGGGGGG",
        "GGGGGGGGGGGGGGGG"
    ],
    "floor_grass": [
        "gggggggggggggggg",
        "gggggggggggggggg",
        "ggggGggggggGgggg",
        "ggggGGggggGGgggg",
        "gggggggggggggggg",
        "gggggggggggggggg",
        "gggggggggggggggg",
        "gggggggggggggggg",
        "gggggggggggggggg",
        "gggggggggggggggg",
        "ggggGggggggGgggg",
        "ggggGGggggGGgggg",
        "gggggggggggggggg",
        "gggggggggggggggg",
        "gggggggggggggggg",
        "gggggggggggggggg"
    ],
    "stairs_down": [
        "kkkkkkkkkkkkkkkk",
        "kkkkkkkkkkkkkkkk",
        "kkyyyyyyyyyyyykk",
        "kkyyyyyyyyyyyykk",
        "kkkkkkkkkkkkkkkk",
        "kkkkkkkkkkkkkkkk",
        "kkkkyyyyyyyykkkk",
        "kkkkyyyyyyyykkkk",
        "kkkkkkkkkkkkkkkk",
        "kkkkkkkkkkkkkkkk",
        "kkkkkkyyyykkkkkk",
        "kkkkkkyyyykkkkkk",
        "kkkkkkkkkkkkkkkk",
        "kkkkkkkkkkkkkkkk",
        "kkkkkkkkkkkkkkkk",
        "kkkkkkkkkkkkkkkk"
    ],
    "stairs_up": [
        "kkkkkkkkkkkkkkkk",
        "kkkkkkkkkkkkkkkk",
        "kkkkkkyyyykkkkkk",
        "kkkkkkyyyykkkkkk",
        "kkkkkkkkkkkkkkkk",
        "kkkkkkkkkkkkkkkk",
        "kkkkyyyyyyyykkkk",
        "kkkkyyyyyyyykkkk",
        "kkkkkkkkkkkkkkkk",
        "kkkkkkkkkkkkkkkk",
        "kkyyyyyyyyyyyykk",
        "kkyyyyyyyyyyyykk",
        "kkkkkkkkkkkkkkkk",
        "kkkkkkkkkkkkkkkk",
        "kkkkkkkkkkkkkkkk",
        "kkkkkkkkkkkkkkkk"
    ],
    "stairs_cellar": [
        "eeeeeeeeeeeeeeee",
        "eeeeeeeeeeeeeeee",
        "eekkkkkkkkkkkkee",
        "eekkneeeeeeennkk",
        "eekkneeeeeeennkk",
        "eekkneeeeeeennkk",
        "eekkneeeeeeennkk",
        "eekkneeeeeeennkk",
        "eekkneeeeeeennkk",
        "eekkneeeeeeennkk",
        "eekkneeeeeeennkk",
        "eekkneeeeeeennkk",
        "eekkkkkkkkkkkkee",
        "eeeeeeeeeeeeeeee",
        "eeeeeeeeeeeeeeee",
        "................"
    ],
    "stairs_crypt": [
        ".....llllll.....",
        "....llllllll....",
        "...lllkkkklll...",
        "..llkkkkkkkkll..",
        "..llkkkkkkkkll..",
        ".llkkkkkkkkkkll.",
        ".llkkkkkkkkkkll.",
        ".llkkkkkkkkkkll.",
        ".llkkkkkkkkkkll.",
        ".llkkkkkkkkkkll.",
        ".llkkkkkkkkkkll.",
        ".llkkkkkkkkkkll.",
        ".llkkkkkkkkkkll.",
        ".llkkkkkkkkkkll.",
        "llllllllllllllll",
        "llllllllllllllll"
    ],
    "stairs_cave": [
        "....dddddddd....",
        "...dddddddddd...",
        "..ddkkkkkkkkdd..",
        ".ddkkkkkkkkkkdd.",
        ".ddkkkkkkkkkkdd.",
        "ddkkkkkkkkkkkkdd",
        "ddkkkkkkkkkkkkdd",
        "ddkkkkkkkkkkkkdd",
        "ddkkkkkkkkkkkkdd",
        "ddkkkkkkkkkkkkdd",
        "ddkkkkkkkkkkkkdd",
        "ddkkkkkkkkkkkkdd",
        ".ddkkkkkkkkkkdd.",
        ".ddkkkkkkkkkkdd.",
        "..dddddddddddd..",
        "...dddddddddd..."
    ],
    "fountain_0": [
        "................",
        ".....bb..bb.....",
        "....bbbbbbbb....",
        "....bbbbbbbb....",
        "....bbbbbbbb....",
        ".....bb..bb.....",
        "......bbbb......",
        ".....llllll.....",
        "....llllllll....",
        "....llddddll....",
        "....llddddll....",
        "....llllllll....",
        "....llddddll....",
        "....llddddll....",
        "....llllllll....",
        "................"
    ],
    "fountain_1": [
        "................",
        ".....ww..ww.....",
        "....wwwwwwww....",
        "....wbbbbbbw....",
        "....bbbbbbbb....",
        ".....bb..bb.....",
        "......bbbb......",
        ".....llllll.....",
        "....llllllll....",
        "....llddddll....",
        "....llddddll....",
        "....llllllll....",
        "....llddddll....",
        "....llddddll....",
        "....llllllll....",
        "................"
    ]
}

# --- projectile patterns ---
PROJ_PATTERNS = {
    "fireball_0": [
        ".......oo.......",
        ".....oooooo.....",
        "....oorrrroo....",
        "...oorrrrryyo...",
        "...oorrrrryyo...",
        "....oorrrroo....",
        ".....oooooo.....",
        ".......oo.......",
        "................",
        "................",
        "................",
        "................",
        "................",
        "................",
        "................",
        "................"
    ],
    "fireball_1": [
        ".......oo.......",
        ".....oooooo.....",
        "....ooyyyyoo....",
        "...ooyyrrrryoo..",
        "...ooyyrrrryoo..",
        "....ooyyyyoo....",
        ".....oooooo.....",
        ".......oo.......",
        "................",
        "................",
        "................",
        "................",
        "................",
        "................",
        "................",
        "................"
    ]
}

def compile_sprite(pattern, scale=2):
    """Parses a 16x16 character-grid pattern and compiles it into a 32x32 pygame.Surface."""
    surf = pygame.Surface((16, 16), pygame.SRCALPHA)
    for y in range(16):
        for x in range(16):
            char = pattern[y][x]
            color = PALETTE.get(char)
            if color is not None:
                surf.set_at((x, y), color)
    return pygame.transform.scale(surf, (16 * scale, 16 * scale))

def create_walk_frame(stand_surf, frame_idx):
    """Programmatically shifts feet and bobs head/body to create dynamic walking frames."""
    if frame_idx in (0, 2):
        return stand_surf
        
    walk_surf = stand_surf.copy()
    
    # Lift the corresponding foot
    if frame_idx == 1:
        # Clear left foot: x from 6 to 15, y from 26 to 31
        for y in range(26, 32):
            for x in range(6, 16):
                walk_surf.set_at((x, y), (0, 0, 0, 0))
    elif frame_idx == 3:
        # Clear right foot: x from 16 to 25, y from 26 to 31
        for y in range(26, 32):
            for x in range(16, 26):
                walk_surf.set_at((x, y), (0, 0, 0, 0))
                
    # Bob down by 2 pixels to give a realistic retro bounce
    bobbed_surf = pygame.Surface((32, 32), pygame.SRCALPHA)
    bobbed_surf.blit(walk_surf, (0, 2))
    return bobbed_surf

def get_game_sprites():
    """Compiles and yields all game textures and sprites as pygame.Surfaces."""
    sprites = {}
    
    # 1. Compile player class sprites & walk frame variations
    for name, pattern in PLAYER_PATTERNS.items():
        # compile the standing surface
        stand_surf = compile_sprite(pattern, scale=2)
        # populate the 4 animation frames (0: stand, 1: left step, 2: stand, 3: right step)
        for frame_idx in range(4):
            sprites[f"player_{name}_{frame_idx}"] = create_walk_frame(stand_surf, frame_idx)
            
    # 2. Compile monster sprites (2 frames each)
    for name, frames in MONSTER_PATTERNS.items():
        for frame_idx, pattern in enumerate(frames):
            sprites[f"monster_{name}_{frame_idx}"] = compile_sprite(pattern, scale=2)
            
    # 3. Compile item sprites
    for name, pattern in ITEM_PATTERNS.items():
        sprites[f"item_{name}"] = compile_sprite(pattern, scale=2)
        
    # 4. Compile spinning coin frames (4 frames)
    for frame_idx, pattern in enumerate(COIN_PATTERNS):
        sprites[f"item_coin_{frame_idx}"] = compile_sprite(pattern, scale=2)
        
    # 5. Compile tile textures
    for name, pattern in TILE_PATTERNS.items():
        sprites[f"tile_{name}"] = compile_sprite(pattern, scale=2)
        
    # 6. Compile projectile fireballs
    for name, pattern in PROJ_PATTERNS.items():
        sprites[f"proj_{name}"] = compile_sprite(pattern, scale=2)
        
    return sprites
