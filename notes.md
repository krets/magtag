Magtag with circuitpy 9.2.8
https://circuitpython.org/board/adafruit_magtag_2.9_grayscale/


296x128

got icons from here:
https://github.com/lmarzen/esp32-weather-epd



I have a circuitpy magtag from adafruit. I would like to get it to display weather information. I have a server that I can fill with relevant data

---
Based on the conditions from the [yr.no weather icons](https://github.com/metno/weathericons/blob/main/weather/legend.csv?plain=1)
```
cp wi-day-sunny.png conditions/clearsky.png
cp wi-day-sunny-overcast.png conditions/fair.png
cp wi-day-cloudy.png conditions/partlycloudy.png
cp wi-cloudy.png conditions/cloudy.png
cp wi-day-sprinkle.png conditions/lightrainshowers.png
cp wi-day-showers.png conditions/rainshowers.png
cp wi-day-rain.png conditions/heavyrainshowers.png
cp wi-day-storm-showers.png conditions/lightrainshowersandthunder.png
cp wi-day-thunderstorm.png conditions/rainshowersandthunder.png
cp wi-day-thunderstorm.png conditions/heavyrainshowersandthunder.png
cp wi-day-sleet.png conditions/lightsleetshowers.png
cp wi-day-sleet-storm.png conditions/sleetshowers.png
cp wi-day-sleet-storm.png conditions/heavysleetshowers.png
cp wi-day-sleet-storm.png conditions/lightssleetshowersandthunder.png
cp wi-day-sleet-storm.png conditions/sleetshowersandthunder.png
cp wi-day-sleet-storm.png conditions/heavysleetshowersandthunder.png
cp wi-day-snow.png conditions/lightsnowshowers.png
cp wi-day-snow-wind.png conditions/snowshowers.png
cp wi-day-snow-wind.png conditions/heavysnowshowers.png
cp wi-day-snow-thunderstorm.png conditions/lightssnowshowersandthunder.png
cp wi-day-snow-thunderstorm.png conditions/snowshowersandthunder.png
cp wi-day-snow-thunderstorm.png conditions/heavysnowshowersandthunder.png
cp wi-raindrops.png conditions/lightrain.png
cp wi-rain.png conditions/rain.png
cp wi-rain-wind.png conditions/heavyrain.png
cp wi-thunderstorm.png conditions/lightrainandthunder.png
cp wi-thunderstorm.png conditions/rainandthunder.png
cp wi-thunderstorm.png conditions/heavyrainandthunder.png
cp wi-sleet.png conditions/lightsleet.png
cp wi-sleet.png conditions/sleet.png
cp wi-day-sleet-storm.png conditions/heavysleet.png
cp wi-day-sleet-storm.png conditions/lightsleetandthunder.png
cp wi-day-sleet-storm.png conditions/sleetandthunder.png
cp wi-day-sleet-storm.png conditions/heavysleetandthunder.png
cp wi-day-snow.png conditions/lightsnow.png
cp wi-snow.png conditions/snow.png
cp wi-snow-wind.png conditions/heavysnow.png
cp wi-day-snow-thunderstorm.png conditions/lightsnowandthunder.png
cp wi-day-snow-thunderstorm.png conditions/snowandthunder.png
cp wi-day-snow-thunderstorm.png conditions/heavysnowandthunder.png
cp wi-day-fog.png conditions/fog.png
```
```
cp wi-night-clear.png conditions/clearsky_night.png
cp wi-night-alt-partly-cloudy.png conditions/fair_night.png
cp wi-night-alt-cloudy.png conditions/partlycloudy_night.png
cp wi-cloudy.png conditions/cloudy_night.png
cp wi-night-alt-sprinkle.png conditions/lightrainshowers_night.png
cp wi-night-alt-showers.png conditions/rainshowers_night.png
cp wi-night-alt-rain.png conditions/heavyrainshowers_night.png
cp wi-night-alt-storm-showers.png conditions/lightrainshowersandthunder_night.png
cp wi-night-alt-thunderstorm.png conditions/rainshowersandthunder_night.png
cp wi-night-alt-thunderstorm.png conditions/heavyrainshowersandthunder_night.png
cp wi-night-alt-sleet.png conditions/lightsleetshowers_night.png
cp wi-night-alt-sleet-storm.png conditions/sleetshowers_night.png
cp wi-night-alt-sleet-storm.png conditions/heavysleetshowers_night.png
cp wi-night-alt-sleet-storm.png conditions/lightssleetshowersandthunder_night.png
cp wi-night-alt-sleet-storm.png conditions/sleetshowersandthunder_night.png
cp wi-night-alt-sleet-storm.png conditions/heavysleetshowersandthunder_night.png
cp wi-night-alt-snow.png conditions/lightsnowshowers_night.png
cp wi-night-alt-snow-thunderstorm.png conditions/snowshowers_night.png
cp wi-night-alt-snow-thunderstorm.png conditions/heavysnowshowers_night.png
cp wi-night-alt-snow-thunderstorm.png conditions/lightssnowshowersandthunder_night.png
cp wi-night-alt-snow-thunderstorm.png conditions/snowshowersandthunder_night.png
cp wi-night-alt-snow-thunderstorm.png conditions/heavysnowshowersandthunder_night.png
cp wi-raindrops.png conditions/lightrain_night.png
cp wi-rain.png conditions/rain_night.png
cp wi-rain.png conditions/heavyrain_night.png
cp wi-thunderstorm.png conditions/lightrainandthunder_night.png
cp wi-thunderstorm.png conditions/rainandthunder_night.png
cp wi-thunderstorm.png conditions/heavyrainandthunder_night.png
cp wi-sleet.png conditions/lightsleet_night.png
cp wi-sleet.png conditions/sleet_night.png
cp wi-night-alt-sleet-storm.png conditions/heavysleet_night.png
cp wi-night-alt-sleet-storm.png conditions/lightsleetandthunder_night.png
cp wi-night-alt-sleet-storm.png conditions/sleetandthunder_night.png
cp wi-night-alt-sleet-storm.png conditions/heavysleetandthunder_night.png
cp wi-night-alt-snow.png conditions/lightsnow_night.png
cp wi-snow.png conditions/snow_night.png
cp wi-night-alt-snow-thunderstorm.png conditions/heavysnow_night.png
cp wi-night-alt-snow-thunderstorm.png conditions/lightsnowandthunder_night.png
cp wi-night-alt-snow-thunderstorm.png conditions/snowandthunder_night.png
cp wi-night-alt-snow-thunderstorm.png conditions/heavysnowandthunder_night.png
cp wi-night-fog.png conditions/fog_night.png
```

Need to budget the icons better; 

... 
made some fonts, and decided to just use roboto 24pt for most of the screen then terminalio for the other text.

battery icon; scaling down was also ugly, so I decided that a 16x16 battery icon was necessary. 

## Set palette
```bash
for file in *.png; do
    if [ -f "$file" ]; then
        magick "$file" \
            -colorspace Gray \
            -colors 4 \
            -normalize \
            -type Palette \
            -depth 2 \
            "${file%.*}.bmp"
    fi
done
```