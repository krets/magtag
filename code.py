from adafruit_datetime import datetime
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
    """Format ISO time to local timezone HH:MM format"""
    try:
        updated_time = datetime.fromisoformat(iso_time)
        # Get timezone offset from secrets (in hours, e.g., -8 for PST, -7 for PDT)
        timezone_offset = secrets.get("timezone_offset", 0)

        # Apply timezone offset
        hour = (updated_time.hour + timezone_offset) % 24

        return f"{hour:02d}:{updated_time.minute:02d}"
    except Exception as e:
        print(f"Time formatting error: {e}")
        return "??:??"


def get_current_date(updated_at):
    """Get current date formatted as day of week and month/date"""
    try:
        current_time = datetime.fromisoformat(updated_at)

        # Days of week (starting from Monday = 0)
        days = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
        months = ["", "Jan", "Feb", "Mar", "Apr", "May", "Jun",
                  "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]

        # current_time is (year, month, date, hour, minute, second, weekday, yearday)
        # weekday: 0 = Monday, 6 = Sunday
        weekday = current_time.weekday()
        month = current_time.month
        date = current_time.day

        day_name = days[weekday]
        month_name = months[month]

        return day_name, f"{month_name} {date}"
    except Exception as e:
        print(f"Date formatting error: {e}")
        return "???", "??? ??"


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

    # Add white background
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

        # Get current date
        day_name, month_date = get_current_date(updated_time)

        # Date display (left side, big text)
        day_label = label.Label(
            terminalio.FONT,
            text=day_name,
            color=0x000000,
            scale=3,
            x=10,
            y=25
        )
        main_group.append(day_label)

        date_label = label.Label(
            terminalio.FONT,
            text=month_date,
            color=0x000000,
            scale=2,
            x=10,
            y=50
        )
        main_group.append(date_label)

        # Weather icon (right side)
        symbol_code_short, *_ = symbol_code.split("_")
        try:
            icon_file = f"icons/{symbol_code_short}.bmp"
            print(f"Looking for icon: {icon_file}")
            icon_bitmap = displayio.OnDiskBitmap(icon_file)
            icon_sprite = displayio.TileGrid(
                icon_bitmap,
                pixel_shader=icon_bitmap.pixel_shader,
                x=DISPLAY_WIDTH - ICON_SIZE - 10,  # Right aligned with margin
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
                x=DISPLAY_WIDTH - 80,
                y=30
            )
            main_group.append(icon_text)

        # Temperature (right side, below icon)
        temp_text = f"{temperature:.1f}C"
        temp_label = label.Label(
            terminalio.FONT,
            text=temp_text,
            color=0x000000,
            scale=2,
            x=DISPLAY_WIDTH - 80,  # Right aligned
            y=80
        )
        main_group.append(temp_label)

        # Weather details (center section)
        details_y = 95

        # Precipitation
        precip_text = f"Rain: {precipitation}mm"
        precip_label = label.Label(
            terminalio.FONT,
            text=precip_text,
            color=0x000000,
            x=10,
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
            x=10,
            y=details_y + 12
        )
        main_group.append(wind_label)

        # Humidity
        humid_text = f"RH: {humidity:.0f}%"
        humid_label = label.Label(
            terminalio.FONT,
            text=humid_text,
            color=0x000000,
            x=150,
            y=details_y
        )
        main_group.append(humid_label)

        # Pressure
        pressure_text = f"P: {pressure:.0f}hPa"
        pressure_label = label.Label(
            terminalio.FONT,
            text=pressure_text,
            color=0x000000,
            x=150,
            y=details_y + 12
        )
        main_group.append(pressure_label)

        # Updated time (bottom right corner)
        updated_text = format_updated_time(updated_time)
        updated_label = label.Label(
            terminalio.FONT,
            text=updated_text,
            color=0x000000,
            x=DISPLAY_WIDTH - 35,
            y=DISPLAY_HEIGHT - 8
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

    # Deep sleep for 3 hours
    time_alarm = alarm.time.TimeAlarm(monotonic_time=time.monotonic() + 3 * 60 * 60)
    alarm.exit_and_deep_sleep_until_alarms(time_alarm)


# Run the main program
if __name__ == "__main__":
    main()