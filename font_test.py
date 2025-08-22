import time
from adafruit_magtag.magtag import MagTag
import displayio

magtag = MagTag()

# White background
color_bitmap = displayio.Bitmap(magtag.graphics.display.width, magtag.graphics.display.height, 1)
color_palette = displayio.Palette(1)
color_palette[0] = 0xFFFFFF
bg_sprite = displayio.TileGrid(color_bitmap, pixel_shader=color_palette)
magtag.splash.append(bg_sprite)

# Test specific character ranges
character_sets = [
    (32, 47, "Symbols & Numbers"),  # Space ! " # $ % & ' ( ) * + , - . /
    (48, 57, "Numbers"),  # 0-9
    (58, 64, "More Symbols"),  # : ; < = > ? @
    (65, 90, "Uppercase Letters"),  # A-Z
    (91, 96, "Brackets & Symbols"),  # [ \ ] ^ _ `
    (97, 122, "Lowercase Letters"),  # a-z
    (123, 126, "Final Symbols")  # { | } ~
]

current_page = 0


def display_character_set(start_ascii, end_ascii, title):
    # Clear existing text properly
    bg_sprite = displayio.TileGrid(color_bitmap, pixel_shader=color_palette)
    magtag.splash.append(bg_sprite)

    # Add title with page info
    page_info = f"{title} ({current_page + 1}/{len(character_sets)})"
    magtag.add_text(
        text=page_info,
        text_position=(10, 15),
        text_scale=1,
        text_color=0x000000
    )

    # Display characters with smaller scale to prevent overlap
    chars_text = ""
    ascii_text = ""

    for ascii_val in range(start_ascii, end_ascii + 1):
        char = chr(ascii_val)
        # Handle space character visibility
        if char == ' ':
            chars_text += "SP "  # Show "SP" for space
        else:
            chars_text += char + "  "
        ascii_text += f"{ascii_val:3d} "

        # Line break every 8 characters for better readability
        if (ascii_val - start_ascii + 1) % 8 == 0:
            chars_text += "\n"
            ascii_text += "\n"

    # Use smaller scale for character display to prevent overlap
    magtag.add_text(
        text=chars_text.strip(),
        text_position=(10, 40),
        text_scale=1,  # Reduced from 2 to 1
        text_color=0x000000
    )

    magtag.add_text(
        text=ascii_text.strip(),
        text_position=(10, 90),
        text_scale=1,
        text_color=0x666666
    )

    # Add button instructions at bottom
    magtag.add_text(
        text="C: Prev  D: Next",
        text_position=(10, 150),
        text_scale=1,
        text_color=0x888888
    )


def next_page():
    global current_page
    current_page = (current_page + 1) % len(character_sets)
    update_display()


def prev_page():
    global current_page
    current_page = (current_page - 1) % len(character_sets)
    update_display()


def update_display():
    start_ascii, end_ascii, title = character_sets[current_page]
    display_character_set(start_ascii, end_ascii, title)
    print(f"Displaying: {title} (Page {current_page + 1}/{len(character_sets)})")
    # Single refresh call at the end
    magtag.refresh()


# Display initial page
update_display()

# Main loop with button handling
button_pressed = [False, False, False, False]

while True:
    # Button D (rightmost) - Next page
    if not magtag.peripherals.buttons[3].value and not button_pressed[3]:
        button_pressed[3] = True
        next_page()

    elif magtag.peripherals.buttons[3].value and button_pressed[3]:
        button_pressed[3] = False

    # Button C (3rd) - Previous page
    if not magtag.peripherals.buttons[2].value and not button_pressed[2]:
        button_pressed[2] = True
        prev_page()

    elif magtag.peripherals.buttons[2].value and button_pressed[2]:
        button_pressed[2] = False

    time.sleep(0.1)  # Small delay to prevent excessive CPU usage
