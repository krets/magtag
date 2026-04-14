import time
import ssl

## CircuitPython
import board
import alarm
import wifi
import socketpool
import displayio
import terminalio
import io

## Adafruit
import adafruit_requests
import adafruit_imageload

# Get wifi details from secrets.py file
try:
    from secrets import secrets
except ImportError:
    print("WiFi secrets are kept in secrets.py, please add them there!")
    raise

# Display constants
DISPLAY_WIDTH = 296
DISPLAY_HEIGHT = 128

# Battery tracking variables (reset on each boot since filesystem is read-only)
BATTERY_THRESHOLD = 4.1
battery_drop_time = None
last_battery_voltage = 4.2

def connect_wifi():
    """Connect to WiFi network"""
    try:
        print(f"Connecting to {secrets['ssid']}...")
        wifi.radio.connect(secrets["ssid"], secrets["password"])
        print(f"Connected! IP: {wifi.radio.ipv4_address}")
        return True
    except Exception as e:
        print(f"WiFi failed: {e}")
        return False

def get_orientation():
    """Detect MagTag orientation using accelerometer"""
    try:
        import adafruit_lis3dh
        import busio
        
        # Initialize I2C and accelerometer
        i2c = busio.I2C(board.SCL, board.SDA)
        
        # Try different I2C addresses that LIS3DH might use
        addresses_to_try = [0x18, 0x19]  # 0x18 is default, 0x19 is alternate
        
        lis3dh = None
        for addr in addresses_to_try:
            try:
                lis3dh = adafruit_lis3dh.LIS3DH_I2C(i2c, address=addr)
                print(f"Found accelerometer at address 0x{addr:02X}")
                break
            except ValueError as addr_error:
                print(f"No accelerometer at address 0x{addr:02X}: {addr_error}")
                continue
        
        if lis3dh is None:
            print("Could not find accelerometer at any address")
            return "landscape_left"
        
        # Get acceleration values
        x, y, z = lis3dh.acceleration
        print(f"Acceleration: x={x:.2f}, y={y:.2f}, z={z:.2f}")
        
        # Determine orientation based on which axis has strongest gravity
        # MagTag coordinate system: when in default landscape_left position (USB on left):
        # - x points right (positive when tilted right)
        # - y points up (positive when tilted up/back)
        # - z points out of screen (positive when face up)
        
        if abs(y) > abs(x):
            if y > 0:
                return "landscape_right"  # USB port on right (y+ = gravity pulling right)
            else:
                return "landscape_left"   # USB port on left (y- = gravity pulling left)
        else:
            if x > 0:
                return "portrait_left"    # USB port on top (x+ = gravity pulling down in portrait)
            else:
                return "portrait_up"      # USB port on bottom (x- = gravity pulling up in portrait)
                
    except ImportError:
        print("adafruit_lis3dh library not available")
        return "landscape_left"
    except Exception as e:
        print(f"Could not read orientation: {e}")
        return "landscape_left"  # Default orientation

def update_battery_tracking(current_voltage):
    """Update battery tracking and return hours since drop below threshold"""
    global battery_drop_time, last_battery_voltage
    
    current_time = time.monotonic()
    
    # Check if voltage dropped below threshold for the first time
    if (battery_drop_time is None and 
        current_voltage < BATTERY_THRESHOLD and 
        last_battery_voltage >= BATTERY_THRESHOLD):
        
        battery_drop_time = current_time
        print(f"Battery dropped below {BATTERY_THRESHOLD}V at {current_time}")
    
    # Reset tracking if voltage goes back above threshold
    elif current_voltage >= BATTERY_THRESHOLD and battery_drop_time is not None:
        battery_drop_time = None
        print(f"Battery recovered above {BATTERY_THRESHOLD}V, resetting tracking")
    
    last_battery_voltage = current_voltage
    
    # Calculate hours since drop
    if battery_drop_time is not None:
        hours_elapsed = (current_time - battery_drop_time) / 3600
        return int(hours_elapsed)
    
    return None


def download_and_display_image():
    """Download BMP image from PHP endpoint and display it"""
    try:
        from adafruit_display_text import label
        # Get location and battery info
        lat = secrets.get("latitude", 52.5)
        lon = secrets.get("longitude", 13.45)
        timezone_offset = secrets.get("timezone_offset", 0)

        # Get battery voltage
        battery_voltage = 3.8  # Default value
        try:
            import analogio
            battery_pin = analogio.AnalogIn(board.BATTERY)
            # Convert ADC reading to voltage (MagTag specific calculation)
            battery_voltage = (battery_pin.value * 3.3) / 65536 * 2
            battery_pin.deinit()
        except Exception as e:
            print(f"Could not read battery voltage: {e}")

        # Update battery tracking
        hours_since_drop = update_battery_tracking(battery_voltage)
        if hours_since_drop is not None:
            print(f"Battery tracking: {hours_since_drop}h since drop below {BATTERY_THRESHOLD}V")
        else:
            print("Battery tracking: no drop detected")

        # Get orientation
        orientation = get_orientation()
        print(f"Detected orientation: {orientation}")

        # Build URL for PHP endpoint (using %.2f for precision)
        php_url = secrets.get("php_endpoint", "https://krets.com/magtag/")
        url = f"{php_url}?lat={lat}&lon={lon}&battery={battery_voltage:.2f}&timezone={timezone_offset:+d}&orientation={orientation}"

        print(f"Downloading image from: {url}")

        # Create HTTP session
        pool = socketpool.SocketPool(wifi.radio)
        requests = adafruit_requests.Session(pool, ssl.create_default_context())

        # Download the BMP image
        response = requests.get(url)

        if response.status_code != 200:
            print(f"HTTP error: {response.status_code}")
            return False

        print("Image downloaded successfully")

        # Get the BMP data
        bmp_data = response.content
        response.close()

        bitmap, palette = adafruit_imageload.load(io.BytesIO(bmp_data))

        # Create display group
        tile_grid = displayio.TileGrid(bitmap, pixel_shader=palette)
        group = displayio.Group()
        group.append(tile_grid)

        # Add battery tracking overlay if tracking is active
        if hours_since_drop is not None:
            # Create battery tracking text
            battery_text = f"(since {hours_since_drop}h)"

            # Position text at bottom center
            text_width = len(battery_text) * 6  # Approximate width for small font
            text_x = (bitmap.width - text_width) // 2
            text_y = bitmap.height - 15

            battery_label = label.Label(
                terminalio.FONT,
                text=battery_text,
                color=0x000000,  # Black
                x=text_x,
                y=text_y
            )
            group.append(battery_label)
            print(f"Added battery tracking text: {battery_text}")

        # Atomic display update: Only set root and refresh once everything is ready
        board.DISPLAY.root_group = group
        board.DISPLAY.refresh()

        print("Image displayed successfully")
        return True

    except Exception as e:
        print(f"Error downloading/displaying image: {e}")
        return False

def show_error_message(message):
    """Display an error message as a non-destructive overlay on the current screen"""
    try:
        from adafruit_display_text import label
        display = board.DISPLAY
        
        # Create overlay group
        overlay = displayio.Group()
        
        # Dimensions for a central box
        w, h = 240, 60
        x, y = (DISPLAY_WIDTH - w) // 2, (DISPLAY_HEIGHT - h) // 2
        
        # Black background box
        bg_bitmap = displayio.Bitmap(w, h, 1)
        bg_palette = displayio.Palette(1)
        bg_palette[0] = 0x000000 # Black
        bg_sprite = displayio.TileGrid(bg_bitmap, pixel_shader=bg_palette, x=x, y=y)
        overlay.append(bg_sprite)
        
        # White text
        error_label = label.Label(
            terminalio.FONT,
            text=message,
            color=0xFFFFFF, # White
            x=x + 10,
            y=y + h // 2
        )
        overlay.append(error_label)
        
        # Append to current root if possible, otherwise replace it
        if isinstance(display.root_group, displayio.Group):
            display.root_group.append(overlay)
        else:
            display.root_group = overlay
            
        display.refresh()
        print(f"Error overlay shown: {message}")
        
    except Exception as e:
        print(f"Error showing error message: {e}")

def main():
    """Main program loop"""
    print("MagTag Image Display Starting...")
    
    # Connect to WiFi
    if not connect_wifi():
        show_error_message("WiFi connection failed")
        time.sleep(5)
    else:
        # Download and display the weather image
        if not download_and_display_image():
            show_error_message("Failed to load weather image")
            time.sleep(5)
        
        # Disconnect WiFi to save power
        wifi.radio.enabled = False

    print("Going to deep sleep...")
    
    # Deep sleep for 3 hours
    time_alarm = alarm.time.TimeAlarm(monotonic_time=time.monotonic() + 3 * 60 * 60)
    alarm.exit_and_deep_sleep_until_alarms(time_alarm)

# Run the main program
if __name__ == "__main__":
    main()
