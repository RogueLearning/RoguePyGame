import os
import pygame

# Initialize Pygame and set headless mode
os.environ["SDL_VIDEODRIVER"] = "dummy"
pygame.init()

# Create a 128x128 surface (4 columns of 32x32 frames, 4 rows of directions)
sheet = pygame.Surface((128, 128), pygame.SRCALPHA)

# Color constants
STEEL = (150, 155, 165)
DARK_STEEL = (90, 95, 105)
LIGHT_STEEL = (200, 205, 215)
PLUME = (210, 40, 40)
BLACK = (20, 20, 25)
BLUE = (40, 100, 200)
GOLD = (245, 200, 30)
BROWN = (100, 65, 30)

def draw_frame(x_offset, y_offset, direction, frame_idx):
    # Create a local 32x32 frame surface to draw on
    frame = pygame.Surface((32, 32), pygame.SRCALPHA)
    
    # Calculate step animation offsets
    # frame_idx 0 = stand, 1 = left step, 2 = stand, 3 = right step
    left_y_off = -2 if frame_idx == 1 else 0
    right_y_off = -2 if frame_idx == 3 else 0
    
    if direction == "DOWN":
        # Feet (BROWN)
        pygame.draw.rect(frame, BROWN, (11, 24 + left_y_off, 3, 2))
        pygame.draw.rect(frame, BROWN, (18, 24 + right_y_off, 3, 2))
        
        # Torso / Breastplate (STEEL)
        pygame.draw.rect(frame, STEEL, (9, 15, 14, 9), border_radius=2)
        pygame.draw.rect(frame, LIGHT_STEEL, (9, 15, 14, 2))  # Highlight
        
        # Shoulders / Pauldrons
        pygame.draw.rect(frame, DARK_STEEL, (7, 15, 2, 4))
        pygame.draw.rect(frame, DARK_STEEL, (23, 15, 2, 4))
        
        # Shield (BLUE) on left arm (visual left, screen left)
        pygame.draw.rect(frame, BLUE, (5, 17, 3, 7), border_radius=1)
        pygame.draw.rect(frame, LIGHT_STEEL, (5, 17, 3, 1))
        
        # Sword (STEEL/GOLD) on right arm
        pygame.draw.line(frame, STEEL, (25, 12), (25, 19), 2)
        pygame.draw.line(frame, GOLD, (24, 19), (26, 19), 2)  # Crossguard
        pygame.draw.rect(frame, BROWN, (25, 20, 1, 2))        # Handle
        
        # Helmet (STEEL)
        pygame.draw.rect(frame, STEEL, (11, 7, 10, 8), border_radius=2)
        # Visor slit (BLACK)
        pygame.draw.rect(frame, BLACK, (12, 10, 8, 2))
        # Plume (PLUME / RED)
        pygame.draw.rect(frame, PLUME, (14, 4, 4, 3), border_radius=1)
        
    elif direction == "UP":
        # Feet
        pygame.draw.rect(frame, BROWN, (11, 24 + left_y_off, 3, 2))
        pygame.draw.rect(frame, BROWN, (18, 24 + right_y_off, 3, 2))
        
        # Torso (Back Armor - DARK_STEEL)
        pygame.draw.rect(frame, DARK_STEEL, (9, 15, 14, 9), border_radius=2)
        
        # Shoulders
        pygame.draw.rect(frame, DARK_STEEL, (7, 15, 2, 4))
        pygame.draw.rect(frame, DARK_STEEL, (23, 15, 2, 4))
        
        # Shield on back profile
        pygame.draw.rect(frame, BLUE, (5, 16, 3, 6))
        
        # Helmet
        pygame.draw.rect(frame, STEEL, (11, 7, 10, 8), border_radius=2)
        # Plume on back (Larger plume red)
        pygame.draw.rect(frame, PLUME, (13, 3, 6, 4), border_radius=1)
        
    elif direction == "LEFT":
        # Feet
        pygame.draw.rect(frame, BROWN, (12, 24 + left_y_off, 3, 2))
        pygame.draw.rect(frame, BROWN, (17, 24 + right_y_off, 3, 2))
        
        # Torso (Profile view is narrower)
        pygame.draw.rect(frame, STEEL, (11, 15, 10, 9), border_radius=2)
        pygame.draw.rect(frame, LIGHT_STEEL, (11, 15, 10, 2))
        
        # Shoulder (Just one prominent shoulder)
        pygame.draw.rect(frame, DARK_STEEL, (15, 15, 3, 4))
        
        # Shield held forward (screen left)
        pygame.draw.rect(frame, BLUE, (7, 16, 4, 8), border_radius=1)
        pygame.draw.rect(frame, LIGHT_STEEL, (7, 16, 4, 2))
        
        # Helmet
        pygame.draw.rect(frame, STEEL, (11, 7, 10, 8), border_radius=2)
        # Visor slit shifted to left
        pygame.draw.rect(frame, BLACK, (9, 10, 4, 2))
        # Plume shifted right
        pygame.draw.rect(frame, PLUME, (15, 4, 3, 3), border_radius=1)
        
    elif direction == "RIGHT":
        # Feet
        pygame.draw.rect(frame, BROWN, (12, 24 + left_y_off, 3, 2))
        pygame.draw.rect(frame, BROWN, (17, 24 + right_y_off, 3, 2))
        
        # Torso
        pygame.draw.rect(frame, STEEL, (11, 15, 10, 9), border_radius=2)
        pygame.draw.rect(frame, LIGHT_STEEL, (11, 15, 10, 2))
        
        # Shoulder
        pygame.draw.rect(frame, DARK_STEEL, (14, 15, 3, 4))
        
        # Shield held forward (screen right)
        pygame.draw.rect(frame, BLUE, (21, 16, 4, 8), border_radius=1)
        pygame.draw.rect(frame, LIGHT_STEEL, (21, 16, 4, 2))
        
        # Helmet
        pygame.draw.rect(frame, STEEL, (11, 7, 10, 8), border_radius=2)
        # Visor slit shifted to right
        pygame.draw.rect(frame, BLACK, (19, 10, 4, 2))
        # Plume shifted left
        pygame.draw.rect(frame, PLUME, (14, 4, 3, 3), border_radius=1)
        
    # Blit frame onto the sheet
    sheet.blit(frame, (x_offset, y_offset))

# Populate sheet:
# Row 0: DOWN, Row 1: UP, Row 2: LEFT, Row 3: RIGHT
directions = ["DOWN", "UP", "LEFT", "RIGHT"]
for row, direction in enumerate(directions):
    for col in range(4):
        draw_frame(col * 32, row * 32, direction, col)

# Ensure assets dir exists and save
os.makedirs("assets", exist_ok=True)
pygame.image.save(sheet, "assets/knight_spritesheet.png")
print("Spritesheet successfully generated at assets/knight_spritesheet.png")
