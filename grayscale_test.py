"""
Trying to determine how many shades are visible on the magtag
Only 4 distinct shades can be seen. This test revealed 4 shaded bars
"""

import time
from adafruit_magtag.magtag import MagTag
import displayio
from adafruit_display_text import label
import terminalio

magtag = MagTag()

# Display dimensions
DISPLAY_WIDTH = 296
DISPLAY_HEIGHT = 128
COLUMNS = 37
COLUMN_WIDTH = 8  # 37 * 8 = 296px


def create_greyscale_test():
    # Clear the splash group completely
    for _ in range(len(magtag.splash)):
        magtag.splash.pop()

    # Create separate bitmaps for each column
    main_group = displayio.Group()

    # Create 37 columns, each with its own greyscale value
    for col in range(COLUMNS):
        # Calculate greyscale value for this column (0-255)
        grey_value = int(255 * (1 - col / (COLUMNS - 1)))

        # Create bitmap for this column
        column_bitmap = displayio.Bitmap(COLUMN_WIDTH, DISPLAY_HEIGHT, 1)
        column_palette = displayio.Palette(1)
        column_palette[0] = (grey_value << 16) | (grey_value << 8) | grey_value

        # Fill the entire column
        for x in range(COLUMN_WIDTH):
            for y in range(DISPLAY_HEIGHT):
                column_bitmap[x, y] = 0

        # Create sprite for this column
        column_sprite = displayio.TileGrid(
            column_bitmap,
            pixel_shader=column_palette,
            x=col * COLUMN_WIDTH,
            y=0
        )
        main_group.append(column_sprite)

    # Add vertical lines between columns
    line_group = displayio.Group()

    # Create vertical lines (skip the last one since it would be at the edge)
    for col in range(1, COLUMNS):
        x_pos = col * COLUMN_WIDTH

        # Create a 1-pixel wide vertical line
        line_bitmap = displayio.Bitmap(1, DISPLAY_HEIGHT, 1)
        line_palette = displayio.Palette(1)
        line_palette[0] = 0x000000
        if col > COLUMNS / 2:
            line_palette[0] = 0xFFFFFF

            # Fill the line
        for y in range(DISPLAY_HEIGHT):
            line_bitmap[0, y] = 0

        # Create sprite for this line
        line_sprite = displayio.TileGrid(
            line_bitmap,
            pixel_shader=line_palette,
            x=x_pos - 1,  # Position just before the column boundary
            y=0
        )
        line_group.append(line_sprite)

    magtag.splash.append(main_group)
    magtag.splash.append(line_group)

    # Add title with white background
    title_label = label.Label(
        terminalio.FONT,
        text="37 Greyscale Levels (8px each)",
        color=0x000000,
        background_color=0xFFFFFF,
        x=10,
        y=15
    )
    magtag.splash.append(title_label)

# Create initial display
create_greyscale_test()
magtag.refresh()
while True:
    time.sleep(0.1)