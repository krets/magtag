import time
import ssl
import wifi
import socketpool
import adafruit_requests
from adafruit_magtag.magtag import MagTag
import gc

# Get wifi details from secrets.py file
try:
    from secrets import secrets
except ImportError:
    print("WiFi secrets are kept in secrets.py, please add them there!")
    raise

# Initialize MagTag
print("Initializing MagTag...")
magtag = MagTag(auto_refresh=False)

# IMPORTANT: Track last refresh time
last_refresh_time = None
MIN_REFRESH_INTERVAL = 5

# yr.no API Configuration
YR_API_URL = "https://api.met.no/weatherapi/locationforecast/2.0/compact"
USER_AGENT = "Magtag 0.1.0/ (jesse@krets.com)"

# Weather symbol mapping
WEATHER_SYMBOLS = {
    "clearsky": "CLEAR",
    "cloudy": "CLOUD",
    "fair": "FAIR",
    "fog": "FOG",
    "heavyrain": "RAIN+",
    "heavyrainandthunder": "STORM",
    "heavyrainshowers": "RAIN+",
    "heavysleet": "SLEET",
    "heavysleetshowers": "SLEET",
    "heavysnow": "SNOW+",
    "heavysnowshowers": "SNOW+",
    "lightrain": "RAIN",
    "lightrainshowers": "RAIN",
    "lightrainandthunder": "STORM",
    "lightsleet": "SLEET",
    "lightsleetshowers": "SLEET",
    "lightsnow": "SNOW",
    "lightsnowshowers": "SNOW",
    "partlycloudy": "P.CLD",
    "rain": "RAIN",
    "rainandthunder": "STORM",
    "rainshowers": "RAIN",
    "sleet": "SLEET",
    "sleetshowers": "SLEET",
    "snow": "SNOW",
    "snowshowers": "SNOW",
    "thunder": "STORM",
}

def safe_refresh():
    """Safely refresh the display with timing check"""
    global last_refresh_time
    current_time = time.monotonic()

    # If first refresh, always wait the minimum interval
    if last_refresh_time is None:
        print(f"First refresh - waiting {MIN_REFRESH_INTERVAL}s...")
        time.sleep(MIN_REFRESH_INTERVAL)
    else:
        # Check if enough time has passed
        time_since_last = current_time - last_refresh_time
        if time_since_last < MIN_REFRESH_INTERVAL:
            wait_time = MIN_REFRESH_INTERVAL - time_since_last
            print(f"Waiting {wait_time:.1f}s before refresh...")
            time.sleep(wait_time)

    print("Refreshing display...")
    max_retries = 3
    for attempt in range(max_retries):
        try:
            magtag.graphics.display.refresh()
            last_refresh_time = time.monotonic()
            time.sleep(0.5)  # Small delay after refresh
            print("Refresh successful!")
            return True
        except RuntimeError as e:
            print(f"Refresh attempt {attempt + 1} failed: {e}")
            if attempt < max_retries - 1:
                wait_time = MIN_REFRESH_INTERVAL * (attempt + 1)
                print(f"Waiting {wait_time}s before retry...")
                time.sleep(wait_time)
            else:
                print("All refresh attempts failed")
                return False
    return False


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


def get_weather_data():
    """Fetch weather data from yr.no"""
    try:
        pool = socketpool.SocketPool(wifi.radio)
        requests = adafruit_requests.Session(pool, ssl.create_default_context())

        lat = secrets.get("latitude", 47.6062)
        lon = secrets.get("longitude", -122.3321)

        params = {"lat": lat, "lon": lon}
        headers = {"User-Agent": USER_AGENT}

        print(f"Fetching weather for {lat}, {lon}...")
        response = requests.get(YR_API_URL, params=params, headers=headers)
        data = response.json()
        print("Weather data received")

        # Clean up
        response.close()
        requests._session = None
        gc.collect()

        return data
    except Exception as e:
        print(f"Weather fetch error: {e}")
        return None


def parse_weather_data(data):
    """Parse weather data - simplified"""
    try:
        if not data or "properties" not in data:
            return None

        timeseries = data["properties"]["timeseries"]
        if not timeseries:
            return None

        # Just get current conditions
        current = timeseries[0]["data"]
        instant = current["instant"]["details"]

        # Get weather symbol - check different time periods
        symbol = "unknown"
        for period in ["next_1_hours", "next_6_hours", "next_12_hours"]:
            if period in current:
                symbol = current[period].get("summary", {}).get("symbol_code", "unknown")
                break

        weather_info = {
            "temp": instant["air_temperature"],
            "symbol": symbol.split("_")[0]  # Remove _day/_night
        }

        print(f"Weather: {weather_info['temp']}°C, {weather_info['symbol']}")
        return weather_info

    except Exception as e:
        print(f"Parse error: {e}")
        return None


def setup_display():
    """Setup simple display layout"""
    print("Setting up display...")

    # IMPORTANT: Disable console output to display
    import displayio
    displayio.release_displays()

    # Re-initialize the display for graphics
    from adafruit_magtag.magtag import MagTag
    global magtag
    magtag = MagTag()

    # Clear display
    while len(magtag.graphics.splash) > 0:
        magtag.graphics.splash.pop()

    # Set background - try black background with white text for better visibility
    magtag.graphics.set_background(0x000000)  # Black background

    # Main temperature - large, centered
    magtag.add_text(
        text_position=(148, 50),
        text_scale=4,
        text_anchor_point=(0.5, 0.5),
        text_color=0xFFFFFF,  # WHITE text on black background
    )

    # Weather condition - above temperature
    magtag.add_text(
        text_position=(148, 20),
        text_scale=2,
        text_anchor_point=(0.5, 0.5),
        text_color=0xFFFFFF,  # WHITE text
    )

    # Status line - bottom
    magtag.add_text(
        text_position=(148, 90),
        text_scale=1,
        text_anchor_point=(0.5, 0.5),
        text_color=0xFFFFFF,  # WHITE text
    )

    print("Display setup complete")

def update_display(weather_info):
    """Update display with weather"""
    try:
        if weather_info:
            # Convert temperature
            use_fahrenheit = secrets.get("use_fahrenheit", False)
            if use_fahrenheit:
                temp = (weather_info["temp"] * 9 / 5) + 32
                unit = "F"
            else:
                temp = weather_info["temp"]
                unit = "C"

            # Update text elements
            magtag.set_text(f"{int(temp)}°{unit}", 0)

            symbol_text = WEATHER_SYMBOLS.get(weather_info["symbol"], weather_info["symbol"][:5].upper())
            magtag.set_text(symbol_text, 1)

            # Add timestamp
            current_time = time.localtime()
            magtag.set_text(f"{current_time.tm_hour:02d}:{current_time.tm_min:02d}", 2)
        else:
            magtag.set_text("--°", 0)
            magtag.set_text("NO DATA", 1)
            magtag.set_text("", 2)

        return safe_refresh()

    except Exception as e:
        print(f"Display update error: {e}")
        return False


def show_message(message, index=0):
    """Show a simple message"""
    try:
        magtag.set_text(message, index)
        return safe_refresh()
    except:
        pass


def main():
    """Main program"""
    print("\n=== MagTag Weather Starting ===\n")
    print(f"Free memory: {gc.mem_free()} bytes")

    try:
        # Setup display first
        setup_display()

        # Show initial message
        magtag.set_text("WEATHER", 1)
        magtag.set_text("Loading...", 0)
        safe_refresh()

        # Connect to WiFi
        if not connect_wifi():
            magtag.set_text("WIFI", 1)
            magtag.set_text("ERROR", 0)
            safe_refresh()
            time.sleep(10)
            magtag.exit_and_deep_sleep(60)
            return

        # Get weather
        weather_data = get_weather_data()
        if not weather_data:
            magtag.set_text("DATA", 1)
            magtag.set_text("ERROR", 0)
            safe_refresh()
            time.sleep(10)
            magtag.exit_and_deep_sleep(60)
            return

        # Parse and display
        weather_info = parse_weather_data(weather_data)
        update_display(weather_info)

        # Clean up memory
        weather_data = None
        gc.collect()
        print(f"Free memory after: {gc.mem_free()} bytes")

        # Wait a moment to see the display
        print("Success! Sleeping in 10 seconds...")
        time.sleep(10)

    except Exception as e:
        print(f"Error in main: {e}")
        try:
            magtag.set_text("ERROR", 0)
            magtag.set_text(str(e)[:10], 1)
            safe_refresh()
        except:
            pass
        time.sleep(10)

    # Deep sleep for 30 minutes
    print("Entering deep sleep for 30 minutes...")
    magtag.exit_and_deep_sleep(30 * 60)


def test_display():
    """Test the display with a simple message"""
    setup_display()
    magtag.set_text("TEST", 0)
    magtag.set_text("123", 1)
    magtag.set_text("OK", 2)
    safe_refresh()
    time.sleep(5)

if __name__ == "__main__":
    test_display()
    # main()