import time
from adafruit_magtag.magtag import MagTag
import displayio
from adafruit_display_text import label
import terminalio

magtag = MagTag()

# White background
color_bitmap = displayio.Bitmap(magtag.graphics.display.width, magtag.graphics.display.height, 1)
color_palette = displayio.Palette(1)
color_palette[0] = 0xFFFFFF

# ASCII range for printable characters
START_ASCII = 32  # Space
END_ASCII = 126  # ~
CHARS_PER_LINE = 23
LINES_PER_PAGE = 6
CHARS_PER_PAGE = CHARS_PER_LINE * LINES_PER_PAGE

total_chars = END_ASCII - START_ASCII + 1
total_pages = (total_chars + CHARS_PER_PAGE - 1) // CHARS_PER_PAGE  # Ceiling division

current_page = 0


def display_character_page():
    # Clear the splash group completely
    for _ in range(len(magtag.splash)):
        magtag.splash.pop()

    # Add background
    bg_sprite = displayio.TileGrid(color_bitmap, pixel_shader=color_palette)
    magtag.splash.append(bg_sprite)

    # Calculate which characters to show on this page
    start_char_index = current_page * CHARS_PER_PAGE
    end_char_index = min(start_char_index + CHARS_PER_PAGE, total_chars)

    # Title with page info
    title_text = f"ASCII Characters ({current_page + 1}/{total_pages})"
    title_label = label.Label(
        terminalio.FONT,
        text=title_text,
        color=0x000000,
        x=10,
        y=15
    )
    magtag.splash.append(title_label)

    # Build lines of characters
    lines = []
    current_line = []

    for i in range(start_char_index, end_char_index):
        ascii_val = START_ASCII + i
        current_line.append(chr(ascii_val))

        if len(current_line) >= CHARS_PER_LINE:
            lines.append(' '.join(current_line))
            current_line = []

    # Add any remaining characters
    if current_line:
        lines.append(' '.join(current_line))

    # Create character display label
    chars_label = label.Label(
        terminalio.FONT,
        text="\n".join(lines),
        color=0x000000,
        x=10,
        y=40
    )
    magtag.splash.append(chars_label)

    # Create button instructions label
    instructions_label = label.Label(
        terminalio.FONT,
        text="C: Prev      D: Next",
        color=0x555555,
        x=145,
        y=120
    )
    magtag.splash.append(instructions_label)


def next_page():
    global current_page
    current_page = (current_page + 1) % total_pages
    update_display()


def prev_page():
    global current_page
    current_page = (current_page - 1) % total_pages
    update_display()


def update_display():
    display_character_page()
    print(f"Displaying page {current_page + 1}/{total_pages}")
    print(
        f"Characters {START_ASCII + current_page * CHARS_PER_PAGE} to {min(START_ASCII + (current_page + 1) * CHARS_PER_PAGE - 1, END_ASCII)}")
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

    time.sleep(0.1)