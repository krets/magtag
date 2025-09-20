import sys
import os
from PIL import Image, ImageDraw, ImageFont
from datetime import datetime
import requests

# Mock secrets for development - must be done before any imports
class MockSecrets:
    secrets = {
        "ssid": "dev_wifi",
        "password": "dev_password", 
        "latitude": 52.4204, 
        "longitude": 13.62,
        "timezone_offset": 1,
    }

sys.modules['secrets'] = MockSecrets()

# Display constants
DISPLAY_WIDTH = 296
DISPLAY_HEIGHT = 128

WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
GREY = (128, 128, 128)  # 50% gray to match physical display

# Mock CircuitPython/Adafruit modules
class MockModule:
    def __getattr__(self, name):
        return MockModule()
    
    def __call__(self, *args, **kwargs):
        return MockModule()

# Mock all the CircuitPython imports
sys.modules['board'] = MockModule()
sys.modules['alarm'] = MockModule()
sys.modules['alarm.time'] = MockModule()
sys.modules['wifi'] = MockModule()
sys.modules['socketpool'] = MockModule()
sys.modules['displayio'] = MockModule()
sys.modules['terminalio'] = MockModule()
sys.modules['analogio'] = MockModule()
sys.modules['digitalio'] = MockModule()
sys.modules['ssl'] = MockModule()
sys.modules['adafruit_datetime'] = MockModule()
sys.modules['adafruit_requests'] = MockModule()
sys.modules['adafruit_display_text'] = MockModule()
sys.modules['adafruit_display_text.label'] = MockModule()
sys.modules['adafruit_magtag'] = MockModule()
sys.modules['adafruit_magtag.magtag'] = MockModule()
sys.modules['adafruit_bitmap_font'] = MockModule()

# Mock classes to replace CircuitPython/Adafruit libraries
class MockMagTag:
    def __init__(self):
        self.splash = MockGroup()
        self.peripherals = MockPeripherals()
        self.image = Image.new('RGB', (DISPLAY_WIDTH, DISPLAY_HEIGHT), WHITE)
        self.draw = ImageDraw.Draw(self.image)
        
    def refresh(self):
        # Save the image for viewing
        self.image.save('weather_display.png')
        print("Display refreshed - saved to weather_display.png")

class MockPeripherals:
    @property
    def battery(self):
        # Mock battery voltage - you can change this for testing
        return 3.9

class MockGroup:
    def __init__(self):
        self.items = []
    
    def append(self, item):
        self.items.append(item)
    
    def insert(self, index, item):
        self.items.insert(index, item)
    
    def pop(self):
        if self.items:
            return self.items.pop()
    
    def __len__(self):
        return len(self.items)

class MockLabel:
    def __init__(self, font, text, color, x, y):
        self.font = font
        self.text = text
        self.color = color
        self.x = x
        self.y = y

class MockBitmap:
    def __init__(self, width, height, colors):
        pass

class MockPalette:
    def __init__(self, colors):
        pass
    
    def __setitem__(self, key, value):
        pass

class MockTileGrid:
    def __init__(self, bitmap, pixel_shader=None, x=0, y=0):
        pass

class MockOnDiskBitmap:
    def __init__(self, filename):
        self.pixel_shader = None

# Mock the specific modules and classes
sys.modules['displayio'].Bitmap = MockBitmap
sys.modules['displayio'].Palette = MockPalette
sys.modules['displayio'].TileGrid = MockTileGrid
sys.modules['displayio'].OnDiskBitmap = MockOnDiskBitmap
sys.modules['displayio'].Group = MockGroup
sys.modules['adafruit_display_text.label'].Label = MockLabel
sys.modules['adafruit_magtag.magtag'].MagTag = MockMagTag

# Mock terminalio.FONT
class MockFont:
    pass

sys.modules['terminalio'].FONT = MockFont()

# Mock bitmap_font
class MockBitmapFont:
    @staticmethod
    def load_font(filename):
        return MockFont()

sys.modules['adafruit_bitmap_font'].bitmap_font = MockBitmapFont()

# Mock wifi
class MockRadio:
    def __init__(self):
        self.ipv4_address = "192.168.1.100"
        self.enabled = True
    
    def connect(self, ssid, password):
        print(f"Mock: Connected to {ssid}")

sys.modules['wifi'].radio = MockRadio()

# Mock time
import time as real_time
sys.modules['time'] = real_time

# Mock datetime
from datetime import datetime as real_datetime
sys.modules['adafruit_datetime'].datetime = real_datetime

# Mock requests
class MockSession:
    def __init__(self, pool, context):
        pass
    
    def get(self, url, headers=None):
        response = requests.get(url, headers=headers)
        mock_response = MockResponse(response)
        return mock_response

class MockResponse:
    def __init__(self, real_response):
        self._real_response = real_response
        self.headers = real_response.headers
    
    def json(self):
        return self._real_response.json()
    
    def close(self):
        pass

sys.modules['adafruit_requests'].Session = MockSession

# Mock socketpool
class MockSocketPool:
    def __init__(self, radio):
        pass

sys.modules['socketpool'].SocketPool = MockSocketPool

# Mock ssl
import ssl as real_ssl
sys.modules['ssl'].create_default_context = real_ssl.create_default_context

# Mock alarm
class MockTimeAlarm:
    def __init__(self, monotonic_time):
        pass

class MockAlarm:
    time = type('time', (), {'TimeAlarm': MockTimeAlarm})()
    
    @staticmethod
    def exit_and_deep_sleep_until_alarms(alarm):
        print("Mock: Would enter deep sleep here")

sys.modules['alarm'] = MockAlarm()

# Font loading - use the same Roboto fonts as the MagTag
try:
    # Load the Roboto fonts from the magtag folder
    FONT = ImageFont.truetype("magtag/Roboto-Regular-25.bdf", 25)
    BIG_FONT = ImageFont.truetype("magtag/Roboto-Regular-50.bdf", 50)
    print("Roboto fonts loaded successfully")
except Exception as e:
    print(f"Could not load Roboto fonts: {e}")
    try:
        # Try system fonts as fallback
        FONT = ImageFont.truetype("arial.ttf", 20)
        BIG_FONT = ImageFont.truetype("arial.ttf", 40)
        print("System fonts loaded as fallback")
    except:
        # Final fallback to default font
        FONT = ImageFont.load_default()
        BIG_FONT = ImageFont.load_default()
        print("Using default fonts as final fallback")

# Small font for labels (mimicking terminalio.FONT which is ~8px tall)
# Use a monospace font for better matching
try:
    SMALL_FONT = ImageFont.truetype("DejaVuSansMono.ttf", 8)
except:
    try:
        SMALL_FONT = ImageFont.truetype("LiberationMono-Regular.ttf", 8)
    except:
        try:
            SMALL_FONT = ImageFont.truetype("courier.ttf", 8)
        except:
            SMALL_FONT = ImageFont.load_default()

# Create a custom create_weather_display that uses Pillow
def pillow_create_weather_display(weather_data, magtag_instance):
    """Create the weather display layout using Pillow"""
    # Clear the image
    magtag_instance.image = Image.new('RGB', (DISPLAY_WIDTH, DISPLAY_HEIGHT), WHITE)
    magtag_instance.draw = ImageDraw.Draw(magtag_instance.image)

    if not weather_data:
        # Error display
        magtag_instance.draw.text((DISPLAY_WIDTH // 2 - 60, DISPLAY_HEIGHT // 2), 
                        "Weather data\nunavailable", fill=BLACK, font=FONT)
        return

    # Import the actual functions from the magtag code
    import magtag.code as magtag_code

    # Get first timeseries entry
    timeseries = weather_data["properties"]["timeseries"]
    current_data = timeseries[0]
    instant_details = current_data["data"]["instant"]["details"]
    forecast_6h = current_data["data"]["next_12_hours"]
    updated_time = weather_data["properties"]["meta"]["updated_at"]
    fetched_at = magtag_code.rfc2822_to_iso(weather_data["properties"]["meta"].get("fetched_at"))
    if fetched_at:
        updated_time = fetched_at

    # Extract data
    temperature = instant_details["air_temperature"]
    symbol_code = forecast_6h["summary"]["symbol_code"]

    min_temperature = 50.0
    max_temperature = -50.0
    for entry in timeseries[:24]:
        entry_temp = entry["data"]["instant"]["details"]["air_temperature"]
        min_temperature = min(entry_temp, min_temperature)
        max_temperature = max(entry_temp, max_temperature)

    print(f"Symbol code: {symbol_code}")
    print(f"Temperature: {temperature}°C")

    # Weather icon
    icon_x = 50
    try:
        icon_file = f"magtag/icons/{magtag_code.WEATHER_ICON_NAMES.get(symbol_code, 'unknown')}.bmp"
        print(f"Looking for icon: {icon_file}")
        if os.path.exists(icon_file):
            icon_img = Image.open(icon_file)
            # Convert to RGB if needed
            if icon_img.mode != 'RGB':
                icon_img = icon_img.convert('RGB')
            magtag_instance.image.paste(icon_img, (icon_x, -8))
            print("Icon loaded successfully")
        else:
            # Draw placeholder text if icon not found
            magtag_instance.draw.text((icon_x, 20), f"ERROR:\n{symbol_code[:12]}\nIcon not found.", 
                           fill=BLACK, font=FONT)
    except Exception as icon_error:
        print(f"Could not load icon: {symbol_code}, error: {icon_error}")
        magtag_instance.draw.text((icon_x, 20), f"ERROR:\n{symbol_code[:12]}\nIcon not found.", 
                        fill=BLACK, font=FONT)

    # Date display (left side, centered) - adjusted positioning to match MagTag
    date_text = magtag_code.get_current_date(updated_time)
    # Split the date text and draw each line with proper spacing, centered
    date_lines = date_text.split('\n')
    y_start = 13
    line_spacing = int(25 * 1.35)  # 1.35x line spacing for 25pt font
    for i, line in enumerate(date_lines):
        # Get text width to center it
        bbox = magtag_instance.draw.textbbox((0, 0), line, font=FONT)
        text_width = bbox[2] - bbox[0]
        # Center within the left area (before icon at x=50)
        x_centered = (50 - text_width) // 2
        magtag_instance.draw.text((x_centered, y_start + i * line_spacing), line, fill=BLACK, font=FONT)

    # Temperature displays - adjusted positioning to match MagTag
    magtag_instance.draw.text((175, 7), f"{max_temperature:.1f}º", fill=BLACK, font=BIG_FONT)
    magtag_instance.draw.text((175, 72), f"{min_temperature:.1f}º", fill=GREY, font=BIG_FONT)

    # Updated time (bottom right corner) - using small font to match terminalio.FONT
    updated_text = f"updated: {magtag_code.format_updated_time(fetched_at)}"
    magtag_instance.draw.text((DISPLAY_WIDTH - 90, DISPLAY_HEIGHT - 12), updated_text, 
                    fill=GREY, font=SMALL_FONT)

    # Battery icon and voltage (bottom left corner)
    battery_voltage = magtag_instance.peripherals.battery
    battery_icon_name = magtag_code.get_battery_icon_name(battery_voltage)
    try:
        battery_icon_file = f"magtag/icons/{battery_icon_name}"
        print(f"Loading battery icon: {battery_icon_file} (voltage: {battery_voltage:.1f}V)")
        if os.path.exists(battery_icon_file):
            battery_img = Image.open(battery_icon_file)
            if battery_img.mode != 'RGB':
                battery_img = battery_img.convert('RGB')
            magtag_instance.image.paste(battery_img, (2, DISPLAY_HEIGHT - 14))
            print("Battery icon loaded successfully")
    except Exception as battery_error:
        print(f"Could not load battery icon: {battery_error}")

    voltage_text = f"{battery_voltage:.1f}V"
    magtag_instance.draw.text((22, DISPLAY_HEIGHT - 12), voltage_text, fill=GREY, font=SMALL_FONT)

    # Weather histogram (bottom 12 pixels, aligned with weather icon)
    histogram_height = 12
    histogram_y = DISPLAY_HEIGHT - histogram_height
    histogram_x = icon_x  # Align with weather icon
    histogram_width = 128  # Icon width
    column_width = 8  # 128 / 16 = 8 pixels per hour
    
    # Get next 16 hours of data
    hourly_data = []
    for i in range(min(16, len(timeseries))):
        entry = timeseries[i]
        temp = entry["data"]["instant"]["details"]["air_temperature"]
        precip = 0
        # Check for precipitation in next_1_hours
        if "next_1_hours" in entry["data"]:
            precip = entry["data"]["next_1_hours"]["details"].get("precipitation_amount", 0)
        hourly_data.append({"temp": temp, "precip": precip})
    
    if hourly_data:
        # Calculate temperature range for scaling
        temps = [h["temp"] for h in hourly_data]
        temp_min, temp_max = min(temps), max(temps)
        temp_range = temp_max - temp_min if temp_max != temp_min else 1
        temp_mid = (temp_min + temp_max) / 2
        
        # Calculate precipitation range for scaling
        precips = [h["precip"] for h in hourly_data]
        precip_max = max(precips) if precips else 1
        precip_max = precip_max if precip_max > 0 else 1
        
        # Draw temperature bars (grey)
        for i, data in enumerate(hourly_data):
            x = histogram_x + i * column_width
            temp = data["temp"]
            
            # Scale temperature to histogram height
            temp_offset = (temp - temp_mid) / temp_range * (histogram_height / 2)
            mid_y = histogram_y + histogram_height // 2
            
            if temp_offset > 0:
                # Temperature above average - bar goes up from middle
                bar_top = max(histogram_y, int(mid_y - temp_offset))
                bar_height = mid_y - bar_top
                if bar_height > 0:
                    magtag_instance.draw.rectangle([x, bar_top, x + column_width - 1, mid_y], fill=GREY)
            else:
                # Temperature below average - bar goes down from middle
                bar_bottom = min(histogram_y + histogram_height, int(mid_y - temp_offset))
                bar_height = bar_bottom - mid_y
                if bar_height > 0:
                    magtag_instance.draw.rectangle([x, mid_y, x + column_width - 1, bar_bottom], fill=GREY)
        
        # Draw precipitation bars (black, 4 pixels wide with 4 pixel gap)
        for i, data in enumerate(hourly_data):
            x = histogram_x + i * column_width
            precip = data["precip"]
            
            if precip > 0:
                # Scale precipitation to histogram height
                precip_height = int((precip / precip_max) * histogram_height)
                precip_height = max(1, precip_height)  # At least 1 pixel if there's precipitation
                
                # Draw 4-pixel wide black bar from bottom
                bar_top = histogram_y + histogram_height - precip_height
                magtag_instance.draw.rectangle([x, bar_top, x + 3, histogram_y + histogram_height - 1], fill=BLACK)

def main():
    """Main program loop"""
    print("Starting weather display development mode...")
    
    # Create mock magtag instance
    magtag_instance = MockMagTag()
    
    # Import and monkey patch the magtag code
    import magtag.code as magtag_code
    magtag_code.magtag = magtag_instance
    
    # Connect to WiFi
    if not magtag_code.connect_wifi():
        print("WiFi connection failed")
        return
    
    # Get and display weather data
    weather_data = magtag_code.get_weather_data()
    try:
        pillow_create_weather_display(weather_data, magtag_instance)
    except Exception as error:
        print(f"Display creation error: {error}")
        import traceback
        traceback.print_exc()
        magtag_instance.draw.text((4, 4), f"Display error:\n{str(error)[:50]}", fill=BLACK, font=FONT)
    
    magtag_instance.refresh()
    print("Development run complete!")

# Run the main program
if __name__ == "__main__":
    main()
