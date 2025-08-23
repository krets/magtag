import ssl
import wifi
import socketpool
import adafruit_requests
import displayio
import time
import alarm
import board
from adafruit_display_text import label
from adafruit_magtag.magtag import MagTag
import terminalio

# Get wifi details from secrets.py file
try:
    from secrets import secrets
except ImportError:
    print("WiFi secrets are kept in secrets.py, please add them there!")
    raise

# Initialize MagTag
print("Initializing MagTag...")
magtag = MagTag()

YR_API_URL = "https://api.met.no/weatherapi/locationforecast/2.0/compact"
USER_AGENT = "Magtag 0.1.2/ (jesse@krets.com)"

# Display constants
DISPLAY_WIDTH = 296
DISPLAY_HEIGHT = 128
ICON_SIZE = 64


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

        # Build URL with query parameters manually
        url = f"{YR_API_URL}?lat={lat}&lon={lon}"
        headers = {"User-Agent": USER_AGENT}

        print(f"Fetching weather for {lat}, {lon}...")
        print(f"URL: {url}")
        response = requests.get(url, headers=headers)
        data = response.json()
        print("Weather data received")

        # Clean up
        response.close()
        requests._session = None
        return data
    except Exception as e:
        print(f"Weather fetch error: {e}")
        return None


def format_updated_time(iso_time):
    """Format ISO time to readable format"""
    try:
        # Extract date and time parts (simplified parsing)
        date_part = iso_time[:10]  # YYYY-MM-DD
        time_part = iso_time[11:16]  # HH:MM
        return f"{date_part} {time_part}Z"
    except:
        return iso_time


def wind_direction_text(degrees):
    """Convert wind direction degrees to compass direction"""
    directions = ["N", "NNE", "NE", "ENE", "E", "ESE", "SE", "SSE",
                  "S", "SSW", "SW", "WSW", "W", "WNW", "NW", "NNW"]
    idx = int((degrees + 11.25) / 22.5) % 16
    return directions[idx]


def create_weather_display(weather_data):
    """Create the weather display layout"""
    # Clear existing display
    for _ in range(len(magtag.splash)):
        magtag.splash.pop()

    # Add white background - INSERT THIS CODE
    color_bitmap = displayio.Bitmap(DISPLAY_WIDTH, DISPLAY_HEIGHT, 1)
    color_palette = displayio.Palette(1)
    color_palette[0] = 0xFFFFFF  # White background
    bg_sprite = displayio.TileGrid(color_bitmap, pixel_shader=color_palette)
    magtag.splash.append(bg_sprite)

    if not weather_data:
        # Error display
        error_label = label.Label(
            terminalio.FONT,
            text="Weather data\nunavailable",
            color=0x000000,
            x=DISPLAY_WIDTH // 2 - 60,
            y=DISPLAY_HEIGHT // 2
        )
        magtag.splash.append(error_label)
        return

    try:
        # Get first timeseries entry
        current_data = weather_data["properties"]["timeseries"][0]
        instant_details = current_data["data"]["instant"]["details"]
        forecast_6h = current_data["data"]["next_6_hours"]
        updated_time = weather_data["properties"]["meta"]["updated_at"]

        # Extract data
        temperature = instant_details["air_temperature"]
        symbol_code = forecast_6h["summary"]["symbol_code"]
        precipitation = forecast_6h["details"].get("precipitation_amount", 0)
        wind_speed = instant_details["wind_speed"]
        wind_direction = instant_details["wind_from_direction"]
        humidity = instant_details["relative_humidity"]
        pressure = instant_details["air_pressure_at_sea_level"]

        print(f"Symbol code: {symbol_code}")
        print(f"Temperature: {temperature}°C")

        # Create main group
        main_group = displayio.Group()
        symbol_code_short, *_ = symbol_code.split("_")
        # Weather icon (center top)
        try:
            icon_file = f"icons/{symbol_code_short}.bmp"
            print(f"Looking for icon: {icon_file}")
            icon_bitmap = displayio.OnDiskBitmap(icon_file)
            icon_sprite = displayio.TileGrid(
                icon_bitmap,
                pixel_shader=icon_bitmap.pixel_shader,
                x=(DISPLAY_WIDTH - ICON_SIZE) // 2,
                y=5
            )
            main_group.append(icon_sprite)
            icon_loaded = True
            print("Icon loaded successfully")
        except Exception as icon_error:
            print(f"Could not load icon: {symbol_code}, error: {icon_error}")
            icon_loaded = False

        # If icon didn't load, show symbol code as text
        if not icon_loaded:
            icon_text = label.Label(
                terminalio.FONT,
                text=symbol_code[:12],  # Truncate if too long
                color=0x000000,
                x=(DISPLAY_WIDTH - len(symbol_code[:12]) * 6) // 2,
                y=30
            )
            main_group.append(icon_text)

        # Temperature (large, below icon)
        temp_text = f"{temperature:.1f}C"
        temp_label = label.Label(
            terminalio.FONT,
            text=temp_text,
            color=0x000000,
            scale=2,
            x=(DISPLAY_WIDTH - len(temp_text) * 12) // 2,
            y=80
        )
        main_group.append(temp_label)

        # Weather details (bottom section)
        details_y = 95

        # Precipitation
        precip_text = f"Rain: {precipitation}mm"
        precip_label = label.Label(
            terminalio.FONT,
            text=precip_text,
            color=0x000000,
            x=5,
            y=details_y
        )
        main_group.append(precip_label)

        # Wind
        wind_dir = wind_direction_text(wind_direction)
        wind_text = f"Wind: {wind_speed}m/s {wind_dir}"
        wind_label = label.Label(
            terminalio.FONT,
            text=wind_text,
            color=0x000000,
            x=5,
            y=details_y + 12
        )
        main_group.append(wind_label)

        # Humidity and Pressure
        humid_text = f"RH: {humidity:.0f}%"
        humid_label = label.Label(
            terminalio.FONT,
            text=humid_text,
            color=0x000000,
            x=160,
            y=details_y
        )
        main_group.append(humid_label)

        pressure_text = f"P: {pressure:.0f}hPa"
        pressure_label = label.Label(
            terminalio.FONT,
            text=pressure_text,
            color=0x000000,
            x=160,
            y=details_y + 12
        )
        main_group.append(pressure_label)

        # Updated time (top right corner)
        updated_text = format_updated_time(updated_time)
        updated_label = label.Label(
            terminalio.FONT,
            text=updated_text[-8:],  # Show just time part
            color=0x000000,
            x=DISPLAY_WIDTH - 50,
            y=10
        )
        main_group.append(updated_label)

        magtag.splash.append(main_group)

    except Exception as e:
        print(f"Display creation error: {e}")
        error_label = label.Label(
            terminalio.FONT,
            text="Display error",
            color=0x000000,
            x=DISPLAY_WIDTH // 2 - 40,
            y=DISPLAY_HEIGHT // 2
        )
        magtag.splash.append(error_label)


def main():
    """Main program loop"""
    print("Starting weather display...")

    # Connect to WiFi
    if not connect_wifi():
        # Show error and sleep
        error_label = label.Label(
            terminalio.FONT,
            text="WiFi connection failed",
            color=0x000000,
            x=50,
            y=DISPLAY_HEIGHT // 2
        )
        magtag.splash.append(error_label)
        magtag.refresh()
        time.sleep(5)
    else:
        # Get and display weather data
        weather_data = get_weather_data()
        create_weather_display(weather_data)
        magtag.refresh()

        # Disconnect WiFi to save power
        wifi.radio.enabled = False

    print("Entering deep sleep for 3 hours...")

    # Deep sleep for 3 hours (10800 seconds)
    time_alarm = alarm.time.TimeAlarm(monotonic_time=time.monotonic() + 10800)
    alarm.exit_and_deep_sleep_until_alarms(time_alarm)


# Run the main program
if __name__ == "__main__":
    main()
