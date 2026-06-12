import os
import pygame

# Initialize Pygame and set headless mode
os.environ["SDL_VIDEODRIVER"] = "dummy"
pygame.init()

# Create a 192x128 surface (6 columns of 32x32 frames, 4 rows of directions)
sheet = pygame.Surface((192, 128), pygame.SRCALPHA)

# Atari-inspired palette
STEEL = (168, 176, 196)
DARK_STEEL = (92, 104, 132)
LIGHT_STEEL = (226, 234, 246)
PLUME = (236, 64, 52)
BLACK = (14, 16, 26)
BLUE = (72, 152, 240)
GOLD = (236, 184, 54)
BROWN = (126, 88, 44)

def draw_frame(x_offset, y_offset, direction, frame_idx):
    # Create a local 32x32 frame surface to draw on
    frame = pygame.Surface((32, 32), pygame.SRCALPHA)

    # frame 0-3 walk cycle, frame 4-5 idle blink cycle
    left_y_off = -2 if frame_idx in (1, 4) else 0
    right_y_off = -2 if frame_idx == 3 else 0
    visor_on = frame_idx != 5

    def block(x, y, w, h, c):
        pygame.draw.rect(frame, c, (x, y, w, h))
    
    if direction == "DOWN":
        block(11, 24 + left_y_off, 3, 2, BROWN)
        block(18, 24 + right_y_off, 3, 2, BROWN)

        block(9, 15, 14, 9, STEEL)
        block(9, 15, 14, 2, LIGHT_STEEL)

        block(7, 15, 2, 4, DARK_STEEL)
        block(23, 15, 2, 4, DARK_STEEL)

        block(5, 17, 3, 7, BLUE)
        block(5, 17, 3, 1, LIGHT_STEEL)

        block(24, 12, 2, 8, STEEL)
        block(23, 19, 4, 1, GOLD)
        block(24, 20, 2, 2, BROWN)

        block(11, 7, 10, 8, STEEL)
        if visor_on:
            block(12, 10, 8, 2, BLACK)
        else:
            block(12, 10, 8, 1, LIGHT_STEEL)
        block(14, 4, 4, 3, PLUME)
        
    elif direction == "UP":
        block(11, 24 + left_y_off, 3, 2, BROWN)
        block(18, 24 + right_y_off, 3, 2, BROWN)
        block(9, 15, 14, 9, DARK_STEEL)
        block(7, 15, 2, 4, DARK_STEEL)
        block(23, 15, 2, 4, DARK_STEEL)
        block(5, 16, 3, 6, BLUE)
        block(11, 7, 10, 8, STEEL)
        block(13, 3, 6, 4, PLUME)
        
    elif direction == "LEFT":
        block(12, 24 + left_y_off, 3, 2, BROWN)
        block(17, 24 + right_y_off, 3, 2, BROWN)
        block(11, 15, 10, 9, STEEL)
        block(11, 15, 10, 2, LIGHT_STEEL)
        block(15, 15, 3, 4, DARK_STEEL)
        block(7, 16, 4, 8, BLUE)
        block(7, 16, 4, 2, LIGHT_STEEL)
        block(11, 7, 10, 8, STEEL)
        if visor_on:
            block(9, 10, 4, 2, BLACK)
        block(15, 4, 3, 3, PLUME)
        
    elif direction == "RIGHT":
        block(12, 24 + left_y_off, 3, 2, BROWN)
        block(17, 24 + right_y_off, 3, 2, BROWN)
        block(11, 15, 10, 9, STEEL)
        block(11, 15, 10, 2, LIGHT_STEEL)
        block(14, 15, 3, 4, DARK_STEEL)
        block(21, 16, 4, 8, BLUE)
        block(21, 16, 4, 2, LIGHT_STEEL)
        block(11, 7, 10, 8, STEEL)
        if visor_on:
            block(19, 10, 4, 2, BLACK)
        block(14, 4, 3, 3, PLUME)
        
    # Blit frame onto the sheet
    sheet.blit(frame, (x_offset, y_offset))

# Populate sheet:
# Row 0: DOWN, Row 1: UP, Row 2: LEFT, Row 3: RIGHT
directions = ["DOWN", "UP", "LEFT", "RIGHT"]
for row, direction in enumerate(directions):
    for col in range(6):
        draw_frame(col * 32, row * 32, direction, col)

# Ensure assets dir exists and save
os.makedirs("assets", exist_ok=True)
pygame.image.save(sheet, "assets/knight_atari_spritesheet.png")
print("Spritesheet successfully generated at assets/knight_atari_spritesheet.png")
