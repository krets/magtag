import time
import ssl

## CircuitPython
import board
import alarm
import wifi
import socketpool
import displayio
import terminalio
import analogio
import digitalio

## Adafruit
from adafruit_datetime import datetime
import adafruit_requests
from adafruit_display_text import label
from adafruit_magtag.magtag import MagTag
from adafruit_bitmap_font import bitmap_font

# Get wifi details from secrets.py file
try:
    from secrets import secrets
except ImportError:
    print("WiFi secrets are kept in secrets.py, please add them there!")
    raise

try:
    FONT = bitmap_font.load_font("Roboto-Regular-25.bdf")
    BIG_FONT = bitmap_font.load_font("Roboto-Regular-50.bdf")
    print("Custom font loaded successfully")
except Exception as e:
    print(f"Could not load custom font: {e}")
    BIG_FONT = FONT = terminalio.FONT  # Fallback to default

# Initialize MagTag
print("Initializing MagTag...")
magtag = MagTag()

YR_API_URL = "https://api.met.no/weatherapi/locationforecast/2.0/compact"
USER_AGENT = "Magtag 0.1.2/ (jesse@krets.com)"

# Display constants
DISPLAY_WIDTH = 296
DISPLAY_HEIGHT = 128

WHITE = 0xFFFFFF
BLACK = 0x000000
GREY = 0x404040
LIGHT_GREY = 0xB0B0B0

# Set up VBUS detection for USB power # This does not work yet.
try:
    vbus_pin = digitalio.DigitalInOut(board.VBUS_SENSE)
    vbus_pin.direction = digitalio.Direction.INPUT
    has_vbus = True
    print("VBUS detection available")
except AttributeError:
    has_vbus = False
    print("VBUS detection not available, using voltage method")


WEATHER_ICON_NAMES = {
    "clearsky_day": "clear",
    "clearsky_night": "nt_clear",
    "cloudy": "cloudy",
    "fair_day": "partlysunny",
    "fair_night": "nt_partlysunny",
    "fog": "fog",
    "heavyrain": "rain",
    "heavyrainandthunder": "tstorms",
    "heavyrainshowers_day": "chancerain",
    "heavyrainshowers_night": "nt_chancerain",
    "heavyrainshowersandthunder_day": "chancetstorms",
    "heavyrainshowersandthunder_night": "nt_chancetstorms",
    "heavysleet": "sleet",
    "heavysleetandthunder": "tstorms",
    "heavysleetshowers_day": "chancesleet",
    "heavysleetshowers_night": "nt_chancesleet",
    "heavysleetshowersandthunder_day": "chancetstorms",
    "heavysleetshowersandthunder_night": "nt_chancetstorms",
    "heavysnow": "snow",
    "heavysnowandthunder": "tstorms",
    "heavysnowshowers_day": "chancesnow",
    "heavysnowshowers_night": "nt_chancesnow",
    "heavysnowshowersandthunder_day": "chancetstorms",
    "heavysnowshowersandthunder_night": "nt_chancetstorms",
    "lightrain": "rain",
    "lightrainandthunder": "tstorms",
    "lightrainshowers_day": "chancerain",
    "lightrainshowers_night": "nt_chancerain",
    "lightrainshowersandthunder_day": "chancetstorms",
    "lightrainshowersandthunder_night": "nt_chancetstorms",
    "lightsleet": "sleet",
    "lightsleetandthunder": "tstorms",
    "lightsleetshowers_day": "chancesleet",
    "lightsleetshowers_night": "nt_chancesleet",
    "lightsnow": "snow",
    "lightsnowandthunder": "tstorms",
    "lightsnowshowers_day": "chancesnow",
    "lightsnowshowers_night": "nt_chancesnow",
    "lightssleetshowersandthunder_day": "chancetstorms",
    "lightssleetshowersandthunder_night": "nt_chancetstorms",
    "lightssnowshowersandthunder_day": "chancetstorms",
    "lightssnowshowersandthunder_night": "nt_chancetstorms",
    "partlycloudy_day": "partlycloudy",
    "partlycloudy_night": "nt_partlycloudy",
    "rain": "rain",
    "rainandthunder": "tstorms",
    "rainshowers_day": "chancerain",
    "rainshowers_night": "nt_chancerain",
    "rainshowersandthunder_day": "chancetstorms",
    "rainshowersandthunder_night": "nt_chancetstorms",
    "sleet": "sleet",
    "sleetandthunder": "tstorms",
    "sleetshowers_day": "chancesleet",
    "sleetshowers_night": "nt_chancesleet",
    "sleetshowersandthunder_day": "chancetstorms",
    "sleetshowersandthunder_night": "nt_chancetstorms",
    "snow": "snow",
    "snowandthunder": "tstorms",
    "snowshowers_day": "chancesnow",
    "snowshowers_night": "nt_chancesnow",
    "snowshowersandthunder_day": "chancetstorms",
    "snowshowersandthunder_night": "nt_chancetstorms",
}


def get_battery_icon_name(voltage):
    """Determine which battery icon to use based on voltage level"""
    try:
        # Check if charging (USB connected)
        if has_vbus and vbus_pin.value:
            value = "charging_full"
        else:
            # Custom thresholds based on typical Li-ion discharge curve
            # 3.30V = empty, 4.20V = full

            if voltage >= 4.15:
                value = "full"  # ~95–100%
            elif voltage >= 4.05:
                value = "6_bar"  # ~85–95%
            elif voltage >= 3.95:
                value = "5_bar"  # ~70–85%
            elif voltage >= 3.87:
                value = "4_bar"  # ~55–70%
            elif voltage >= 3.82:
                value = "3_bar"  # ~40–55%
            elif voltage >= 3.77:
                value = "2_bar"  # ~25–40%
            elif voltage >= 3.70:
                value = "1_bar"  # ~10–25%
            elif voltage >= 3.50:
                value = "0_bar"  # ~5–10%, very low but not dead
            else:
                value = "alert"  # <3.5 V: effectively empty, may brownout

    except Exception as e:
        print(f"Error determining battery icon: {e}")
        value = "alert"
    return "battery_%s_90deg.bmp" % value


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
        print(f"Response Headers: {response.headers}")
        data['properties']['meta']['fetched_at'] = response.headers.get("date", '')
        print("Weather data received")

        # Clean up
        response.close()
        requests._session = None
        return data
    except Exception as e:
        print(f"Weather fetch error: {e}")
        return None

def rfc2822_to_iso(d):
    """
    Thu, 28 Aug 2025 19:57:24 GMT
    """
    if d is None:
        return ''
    months = {'Jan':1,'Feb':2,'Mar':3,'Apr':4,'May':5,'Jun':6,
              'Jul':7,'Aug':8,'Sep':9,'Oct':10,'Nov':11,'Dec':12}
    parts = d.replace(',', '').split()
    print(f"parsing datetime: {parts}")
    if len(parts) < 5:
        print(f"Ouch; no date: {d}")
        return ''
    day = int(parts[1])
    month = months[parts[2]]
    year = int(parts[3])
    h,m,s = map(int, parts[4].split(':'))
    dt = datetime(year, month, day, h, m, s)
    return dt.isoformat()

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
    timezone_offset = secrets.get("timezone_offset", 0)
    try:
        now = datetime.fromisoformat(updated_at).timestamp() + timezone_offset * 60 * 60
        current_time = datetime.fromtimestamp(now)
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

        return (f"{day_name}\n{month_name}\n{date}")
    except Exception as e:
        print(f"Date formatting error: {e}")
        return "???"


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
    color_palette[0] = WHITE
    bg_sprite = displayio.TileGrid(color_bitmap, pixel_shader=color_palette)
    magtag.splash.append(bg_sprite)

    if not weather_data:
        # Error display
        error_label = label.Label(
            terminalio.FONT,
            text="Weather data\nunavailable",
            color=BLACK,
            x=DISPLAY_WIDTH // 2 - 60,
            y=DISPLAY_HEIGHT // 2
        )
        magtag.splash.append(error_label)
        return

    # Get first timeseries entry
    timeseries = weather_data["properties"]["timeseries"]
    current_data = timeseries[0]
    instant_details = current_data["data"]["instant"]["details"]
    forecast_6h = current_data["data"]["next_12_hours"]
    updated_time = weather_data["properties"]["meta"]["updated_at"]
    fetched_at = rfc2822_to_iso(weather_data["properties"]["meta"].get("fetched_at"))
    if fetched_at:
        updated_time = fetched_at

    # Extract data
    temperature = instant_details["air_temperature"]
    symbol_code = forecast_6h["summary"]["symbol_code"]
    precipitation = forecast_6h["details"].get("precipitation_amount", 0)
    wind_speed = instant_details["wind_speed"]
    wind_direction = instant_details["wind_from_direction"]
    humidity = instant_details["relative_humidity"]
    pressure = instant_details["air_pressure_at_sea_level"]

    min_temperature = 50.0
    max_temperature = -50.0
    for entry in timeseries[:24]:
        entry_temp = entry["data"]["instant"]["details"]["air_temperature"]
        min_temperature = min(entry_temp, min_temperature)
        max_temperature = max(entry_temp, max_temperature)

    print(f"Symbol code: {symbol_code}")
    print(f"Temperature: {temperature}°C")

    # Create main group
    main_group = displayio.Group()


    icon_x = 50
    try:
        icon_file = f"icons/{WEATHER_ICON_NAMES.get(symbol_code, 'unknown')}.bmp"
        print(f"Looking for icon: {icon_file}")
        icon_bitmap = displayio.OnDiskBitmap(icon_file)
        icon_sprite = displayio.TileGrid(
            icon_bitmap,
            pixel_shader=icon_bitmap.pixel_shader,
            x=icon_x,
            y=-8
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
            text=f"ERROR:\n{symbol_code[:12]}\nIcon not found.",
            color=BLACK,
            x=icon_x,
            y=20
        )
        main_group.append(icon_text)
    # Date display (left side, big text)
    main_group.append(label.Label(
        FONT,
        text=get_current_date(updated_time),
        color=BLACK,
        x=5,
        y=25,
    ))

    main_group.append(label.Label(
        BIG_FONT,
        text=f"{max_temperature:.1f}º",
        color=BLACK,
        x=175,
        y=25
    ))
    main_group.append(label.Label(
        BIG_FONT,
        text=f"{min_temperature:.1f}º",
        color=GREY,
        x=175,
        y=90
    ))

    # Updated time (bottom right corner)
    updated_text = f"updated: {format_updated_time(fetched_at)}"
    updated_label = label.Label(
        terminalio.FONT,
        text=updated_text,
        color=GREY,
        x=DISPLAY_WIDTH - 90,
        y=DISPLAY_HEIGHT - 8
    )
    main_group.append(updated_label)

    # Battery icon (bottom left corner)
    battery_voltage = magtag.peripherals.battery
    battery_icon_name = get_battery_icon_name(battery_voltage)
    try:
        battery_icon_file = f"icons/{battery_icon_name}"
        print(f"Loading battery icon: {battery_icon_file} (voltage: {battery_voltage:.1f}V)")
        battery_bitmap = displayio.OnDiskBitmap(battery_icon_file)
        battery_sprite = displayio.TileGrid(
            battery_bitmap,
            pixel_shader=battery_bitmap.pixel_shader,
            x=2,
            y=DISPLAY_HEIGHT - 14
        )
        main_group.insert(1, battery_sprite)
        print("Battery icon loaded successfully")
    except Exception as battery_error:
        print(f"Could not load battery icon: {battery_error}")

    voltage_text = f"{battery_voltage:.1f}V"
    voltage_label = label.Label(
        terminalio.FONT,
        text=voltage_text,
        color=GREY,
        x=22,
        y=DISPLAY_HEIGHT - 8
    )
    main_group.append(voltage_label)

    magtag.splash.append(main_group)


def main():
    """Main program loop"""
    print("Starting weather display...")

    # Connect to WiFi
    if not connect_wifi():
        # Show error and sleep
        error_label = label.Label(
            terminalio.FONT,
            text="WiFi connection failed",
            color=BLACK,
            x=50,
            y=DISPLAY_HEIGHT // 2
        )
        magtag.splash.append(error_label)
        magtag.refresh()
        time.sleep(5)
    else:
        # Get and display weather data
        weather_data = get_weather_data()
        try:
            create_weather_display(weather_data)
        except Exception as error:
            print(f"Display creation error: {error}")
            error_label = label.Label(
                terminalio.FONT,
                text=f"Display error:\n{error}",
                color=BLACK,
                x=4,
                y=4
            )
            magtag.splash.append(error_label)
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