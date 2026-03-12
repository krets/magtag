<?php
// error_reporting(E_ALL);
// ini_set('display_errors', 1);

header('Content-Type: image/bmp');

// Configuration
const DISPLAY_WIDTH = 296;
const DISPLAY_HEIGHT = 128;

function getWeatherData($lat, $lon) {
    $url = "https://api.met.no/weatherapi/locationforecast/2.0/compact?lat={$lat}&lon={$lon}";
    $context = stream_context_create([
        'http' => [
            'header' => "User-Agent: SimpleWeather/1.0\r\n"
        ]
    ]);
    
    $data = @file_get_contents($url, false, $context);
    return $data ? json_decode($data, true) : null;
}

function getBatteryLevel($voltage) {
    if ($voltage >= 4.15) return 100;
    if ($voltage >= 4.05) return 90;
    if ($voltage >= 3.95) return 80;
    if ($voltage >= 3.80) return 60;
    if ($voltage >= 3.7) return 40;
    if ($voltage >= 3.5) return 25;
    if ($voltage >= 3.3) return 10;
    return 0;
}

function formatTime($isoTime, $offset = 0) {
    try {
        $dt = new DateTime($isoTime);
        $dt->modify("{$offset} hours");
        return $dt->format('H:i');
    } catch (Exception $e) {
        return "??:??";
    }
}

function formatHour($isoTime, $offset = 0) {
    try {
        $dt = new DateTime($isoTime);
        $dt->modify("{$offset} hours");
        return $dt->format('G') . ':';
    } catch (Exception $e) {
        return "??:";
    }
}

function getDateInfo($isoTime, $offset = 0) {
    try {
        $dt = new DateTime($isoTime);
        $dt->modify("{$offset} hours");
        $day = $dt->format('j');
        $ordinal = getOrdinalSuffix($day);
        return [
            'day' => $day,
            'dayWithOrdinal' => $day . $ordinal,
            'dayname' => $dt->format('D'),
            'month' => $dt->format('M'),
            'date' => $dt->format('Y-m-d')
        ];
    } catch (Exception $e) {
        return ['day' => '?', 'dayWithOrdinal' => '?', 'dayname' => '???', 'month' => '???', 'date' => ''];
    }
}

function getOrdinalSuffix($day) {
    $day = (int)$day;
    if ($day >= 11 && $day <= 13) {
        return 'th';
    }
    switch ($day % 10) {
        case 1: return 'st';
        case 2: return 'nd';
        case 3: return 'rd';
        default: return 'th';
    }
}

function loadAndResizeIcon($iconPath, $targetWidth, $targetHeight) {
    if (!file_exists($iconPath)) {
        return null;
    }
    
    $source = imagecreatefrompng($iconPath);
    if (!$source) return null;
    
    $resized = imagecreatetruecolor($targetWidth, $targetHeight);
    imagealphablending($resized, false);
    imagesavealpha($resized, true);
    
    $transparent = imagecolorallocatealpha($resized, 255, 255, 255, 127);
    imagefill($resized, 0, 0, $transparent);
    
    imagecopyresampled($resized, $source, 0, 0, 0, 0, 
                      $targetWidth, $targetHeight, 
                      imagesx($source), imagesy($source));
    
    imagedestroy($source);
    return $resized;
}

function findPrecipitation($timeseries, $timezoneOffset = 0) {
    $precipEvents = [];
    
    for ($i = 0; $i < min(12, count($timeseries)); $i++) {
        $entry = $timeseries[$i];
        $time = $entry['time'];
        
        if (isset($entry['data']['next_1_hours']['details']['precipitation_amount'])) {
            $amount = $entry['data']['next_1_hours']['details']['precipitation_amount'];
            if ($amount > 0) {
                $precipEvents[] = [
                    'time' => formatHour($time, $timezoneOffset),
                    'amount' => $amount
                ];
            }
        }
    }
    
    return $precipEvents;
}

function getCalendarDayTempTimes($timeseries, $currentDate, $timezoneOffset = 0) {
    $cacheFile = __DIR__ . '/weather_cache.json';
    $dayTempsMap = [];
    
    // Load existing cache
    if (file_exists($cacheFile)) {
        $cacheData = json_decode(@file_get_contents($cacheFile), true);
        if ($cacheData && isset($cacheData['date']) && $cacheData['date'] === $currentDate) {
            $dayTempsMap = $cacheData['temps'] ?? [];
        }
    }
    
    $updated = false;
    foreach ($timeseries as $entry) {
        try {
            $dt = new DateTime($entry['time']);
            $dt->modify("{$timezoneOffset} hours");
            if ($dt->format('Y-m-d') === $currentDate) {
                $time = $entry['time'];
                $temp = $entry['data']['instant']['details']['air_temperature'];
                if (!isset($dayTempsMap[$time])) {
                    $dayTempsMap[$time] = $temp;
                    $updated = true;
                }
            }
        } catch (Exception $e) {
            continue;
        }
    }
    
    if ($updated) {
        @file_put_contents($cacheFile, json_encode([
            'date' => $currentDate,
            'temps' => $dayTempsMap
        ]));
    }
    
    $dayTemps = [];
    foreach ($dayTempsMap as $time => $temp) {
        $dayTemps[] = [
            'temp' => $temp,
            'time' => $time
        ];
    }
    
    // If we don't have enough calendar day data, use next 24 hours
    if (count($dayTemps) < 4) {
        $dayTemps = [];
        $count = 0;
        foreach ($timeseries as $entry) {
            if ($count >= 24) break;
            
            $dayTemps[] = [
                'temp' => $entry['data']['instant']['details']['air_temperature'],
                'time' => $entry['time']
            ];
            $count++;
        }
    }
    
    if (empty($dayTemps)) {
        return [null, null, null, null];
    }
    
    $minTemp = min(array_column($dayTemps, 'temp'));
    $maxTemp = max(array_column($dayTemps, 'temp'));
    
    $minTime = null;
    $maxTime = null;
    
    foreach ($dayTemps as $tempData) {
        if ($tempData['temp'] == $minTemp && !$minTime) {
            $minTime = formatHour($tempData['time'], $timezoneOffset);
        }
        if ($tempData['temp'] == $maxTemp && !$maxTime) {
            $maxTime = formatHour($tempData['time'], $timezoneOffset);
        }
    }
    
    return [$minTemp, $maxTemp, $minTime, $maxTime];
}

function getMoonPhase($timeseries) {
    foreach ($timeseries as $entry) {
        if (isset($entry['data']['instant']['details']['moon_phase'])) {
            $phase = $entry['data']['instant']['details']['moon_phase'];
            
            if ($phase < 0.0625) return 'wi-moon-alt-new.png';
            if ($phase < 0.1875) return 'wi-moon-alt-waxing-crescent-3.png';
            if ($phase < 0.3125) return 'wi-moon-alt-first-quarter.png';
            if ($phase < 0.4375) return 'wi-moon-alt-waxing-gibbous-3.png';
            if ($phase < 0.5625) return 'wi-moon-alt-full.png';
            if ($phase < 0.6875) return 'wi-moon-alt-waning-gibbous-3.png';
            if ($phase < 0.8125) return 'wi-moon-alt-third-quarter.png';
            if ($phase < 0.9375) return 'wi-moon-alt-waning-crescent-3.png';
            return 'wi-moon-alt-new.png';
        }
    }
    return null;
}

function getDailyForecasts($timeseries, $timezoneOffset = 0, $days = 5) {
    $dailyData = [];
    $processedDates = [];
    
    $todayDate = null;
    if (!empty($timeseries)) {
        $dt = new DateTime($timeseries[0]['time']);
        $dt->modify("{$timezoneOffset} hours");
        $todayDate = $dt->format('Y-m-d');
    }

    $cacheFile = __DIR__ . '/weather_cache.json';
    $todayCache = [];
    if ($todayDate && file_exists($cacheFile)) {
        $cacheData = json_decode(@file_get_contents($cacheFile), true);
        if ($cacheData && isset($cacheData['date']) && $cacheData['date'] === $todayDate) {
            $todayCache = $cacheData['temps'] ?? [];
        }
    }

    $cacheUpdated = false;
    foreach ($timeseries as $entry) {
        try {
            $dt = new DateTime($entry['time']);
            $dt->modify("{$timezoneOffset} hours");
            $date = $dt->format('Y-m-d');

            if ($date === $todayDate) {
                $time = $entry['time'];
                $temp = $entry['data']['instant']['details']['air_temperature'];
                if (!isset($todayCache[$time])) {
                    $todayCache[$time] = $temp;
                    $cacheUpdated = true;
                }
            }

            if (!isset($processedDates[$date])) {
                $processedDates[$date] = [
                    'date' => $date,
                    'dayname' => $dt->format('D'),
                    'day' => $dt->format('j'),
                    'month' => $dt->format('M'),
                    'temps' => ($date === $todayDate) ? array_values($todayCache) : [],
                    'symbols' => []
                ];
            }

            if (isset($entry['data']['instant']['details']['air_temperature'])) {
                $processedDates[$date]['temps'][] = $entry['data']['instant']['details']['air_temperature'];
            }

            $hour = (int)$dt->format('G');
            if ($hour >= 10 && $hour <= 14) {
                if (isset($entry['data']['next_6_hours']['summary']['symbol_code'])) {
                    $processedDates[$date]['symbols'][] = $entry['data']['next_6_hours']['summary']['symbol_code'];
                } elseif (isset($entry['data']['next_1_hours']['summary']['symbol_code'])) {
                    $processedDates[$date]['symbols'][] = $entry['data']['next_1_hours']['summary']['symbol_code'];
                }
            }
        } catch (Exception $e) {
            continue;
        }
    }

    if ($cacheUpdated && $todayDate) {
        @file_put_contents($cacheFile, json_encode([
            'date' => $todayDate,
            'temps' => $todayCache
        ]));
    }

    foreach ($processedDates as $date => $data) {
        if (!empty($data['temps'])) {
            $dailyData[] = [
                'date' => $date,
                'dayname' => $data['dayname'],
                'day' => $data['day'],
                'month' => $data['month'],
                'high' => round(max($data['temps'])),
                'low' => round(min($data['temps'])),
                'symbol' => !empty($data['symbols']) ? $data['symbols'][0] : 'clearsky_day'
            ];
        }

        if (count($dailyData) >= $days) break;
    }

    return $dailyData;
}

function drawLargeText($image, $text, $x, $y, $color, $size = 36, $bold = false) {
    $fontFile = $bold ? 'B612-Bold.ttf' : 'B612-Regular.ttf';
    $fontPath = __DIR__ . '/' . $fontFile;
    if (!file_exists($fontPath)) $fontPath = __DIR__ . '/B612-Regular.ttf';
    
    if (file_exists($fontPath)) {
        $adjustedY = $y + $size;
        imagettftext($image, $size, 0, $x, $adjustedY, $color, $fontPath, $text);
    } else {
        imagestring($image, 5, $x, $y, $text, $color);
    }
}

function drawText($image, $text, $x, $y, $color, $size = 12, $bold = false) {
    $fontFile = $bold ? 'B612-Bold.ttf' : 'B612-Regular.ttf';
    $fontPath = __DIR__ . '/' . $fontFile;
    if (!file_exists($fontPath)) $fontPath = __DIR__ . '/B612-Regular.ttf';

    if (file_exists($fontPath)) {
        $adjustedY = $y + $size;
        imagettftext($image, $size, 0, $x, $adjustedY, $color, $fontPath, $text);
    } else {
        imagestring($image, 3, $x, $y, $text, $color);
    }
}

function drawCenteredText($image, $text, $centerX, $y, $color, $size = 12, $bold = false) {
    $fontFile = $bold ? 'B612-Bold.ttf' : 'B612-Regular.ttf';
    $fontPath = __DIR__ . '/' . $fontFile;
    if (!file_exists($fontPath)) $fontPath = __DIR__ . '/B612-Regular.ttf';

    if (file_exists($fontPath)) {
        $bbox = imagettfbbox($size, 0, $fontPath, $text);
        $textWidth = $bbox[2] - $bbox[0];
        $x = $centerX - ($textWidth / 2);
        $adjustedY = $y + $size;
        imagettftext($image, $size, 0, $x, $adjustedY, $color, $fontPath, $text);
    } else {
        $textWidth = strlen($text) * 6;
        $x = $centerX - ($textWidth / 2);
        imagestring($image, 2, $x, $y, $text, $color);
    }
}

function drawDateWithOrdinal($image, $day, $ordinal, $x, $y, $color) {
    $fontPath = __DIR__ . '/B612-Regular.ttf';

    if (file_exists($fontPath)) {
        $mainSize = 36;
        $adjustedY = $y + $mainSize;
        imagettftext($image, $mainSize, 0, $x, $adjustedY, $color, $fontPath, $day);

        $bbox = imagettfbbox($mainSize, 0, $fontPath, $day);
        $dayWidth = $bbox[2] - $bbox[0];

        $ordinalSize = 18;
        $ordinalX = $x + $dayWidth + 2;
        $ordinalY = $y + $ordinalSize;
        imagettftext($image, $ordinalSize, 0, $ordinalX, $ordinalY, $color, $fontPath, $ordinal);
    } else {
        imagestring($image, 5, $x, $y, $day . $ordinal, $color);
    }
}

function drawRightAlignedText($image, $text, $rightX, $y, $color, $size = 40, $bold = false) {
    $fontFile = $bold ? 'B612-Bold.ttf' : 'B612-Regular.ttf';
    $fontPath = __DIR__ . '/' . $fontFile;
    if (!file_exists($fontPath)) $fontPath = __DIR__ . '/B612-Regular.ttf';

    if (file_exists($fontPath)) {
        $bbox = imagettfbbox($size, 0, $fontPath, $text);
        $textWidth = $bbox[2] - $bbox[0];
        $x = $rightX - $textWidth;

        $adjustedY = $y + $size;
        imagettftext($image, $size, 0, $x, $adjustedY, $color, $fontPath, $text);

        return $rightX;
    } else {
        $textWidth = strlen($text) * 12;
        $x = $rightX - $textWidth;
        imagestring($image, 5, $x, $y, $text, $color);
        return $rightX;
    }
}

function drawTimeLabel($image, $text, $rightX, $y, $color) {
    $fontPath = __DIR__ . '/B612-Regular.ttf';

    if (file_exists($fontPath)) {
        $size = 10;
        $bbox = imagettfbbox($size, 0, $fontPath, $text);
        $textWidth = $bbox[2] - $bbox[0];
        $x = $rightX - $textWidth;

        $adjustedY = $y + $size;
        imagettftext($image, $size, 0, $x, $adjustedY, $color, $fontPath, $text);
    } else {
        $textWidth = strlen($text) * 6;
        $x = $rightX - $textWidth;
        imagestring($image, 1, $x, $y, $text, $color);
    }
}

function drawBattery($batteryVoltage, $image){
    $height = imagesy($image);
    $width = imagesx($image);
    $black = imagecolorallocate($image, 0, 0, 0);
    $gray = imagecolorallocate($image, 128, 128, 128);
    
    $batteryPercent = getBatteryLevel($batteryVoltage);
    $batteryX = 2;
    $batteryY = $height - 9;
    $batteryWidth = 16;
    $batteryHeight = 6;

    imagerectangle($image, $batteryX, $batteryY, $batteryX + $batteryWidth, $batteryY + $batteryHeight, $black);

    $fillWidth = (int)(($batteryPercent / 100) * ($batteryWidth - 2));
    if ($fillWidth > 0) {
        imagefilledrectangle($image, $batteryX + 1, $batteryY + 1,
                           $batteryX + 1 + $fillWidth, $batteryY + $batteryHeight - 1,
                           $batteryPercent > 10 ? $black : $gray);
    }

    imagefilledrectangle($image, $batteryX + $batteryWidth, $batteryY + 2,
                        $batteryX + $batteryWidth + 1, $batteryY + $batteryHeight - 2, $black);

    imagestring($image, 1, $batteryX + 20, $batteryY, sprintf("%.1fV", $batteryVoltage), $gray);
}

function drawUpdated($updated, $timezoneOffset, $image){
    $gray = imagecolorallocate($image, 128, 128, 128);
    $height = imagesy($image);
    $width = imagesx($image);
    
    $time = formatTime($updated, $timezoneOffset);
    $timeText = "updated: ".$time;
    $textWidth = strlen($timeText) * 5;
    imagestring($image, 1, $width - $textWidth - 2, $height - 10, $timeText, $gray);
}

function createForecastDisplay($weatherData, $batteryVoltage = 3.8, $timezoneOffset = 0) {
    $width = DISPLAY_HEIGHT;  
    $height = DISPLAY_WIDTH;  

    $image = imagecreate($width, $height);

    $white = imagecolorallocate($image, 255, 255, 255);
    $black = imagecolorallocate($image, 0, 0, 0);
    $gray = imagecolorallocate($image, 128, 128, 128);
    $lightgray = imagecolorallocate($image, 170, 170, 170); // For contrast on black

    imagefill($image, 0, 0, $white);

    if (!$weatherData) {
        imagestring($image, 3, 5, 140, "Weather", $black);
        imagestring($image, 3, 5, 155, "unavailable", $black);
        return $image;
    }

    $timeseries = $weatherData['properties']['timeseries'];
    $updated = $weatherData['properties']['meta']['updated_at'];

    $forecasts = getDailyForecasts($timeseries, $timezoneOffset, 5);
    $currentDateInfo = getDateInfo($updated, $timezoneOffset);
    
    // Row 1: White background for Today's Info [Icon] [High] [Low]
    $headerHeight = 62; // Increased from 55
    
    $today = $forecasts[0];
    $baseSymbol = str_replace(['_day', '_night'], '', $today['symbol']);
    $iconPath = "icons/{$baseSymbol}.png";
    $weatherIcon = loadAndResizeIcon($iconPath, 52, 52); // Slightly larger
    if (!$weatherIcon) {
        $iconPath = "icons/{$today['symbol']}.png";
        $weatherIcon = loadAndResizeIcon($iconPath, 52, 52);
    }

    if ($weatherIcon) {
        // Far left, 0 margin, centered vertically in its row
        imagecopy($image, $weatherIcon, 0, 5, 0, 0, 52, 52);
        imagedestroy($weatherIcon);
    }

    // Today's High/Low in Header (Black/Gray) - Centered in remaining space
    $highText = sprintf('%d°', $today['high']);
    $lowText = sprintf('%d°', $today['low']);
    $fontPathReg = __DIR__ . '/B612-Regular.ttf';
    $fontPathBold = __DIR__ . '/B612-Bold.ttf';
    
    $fontSize = 18; // Reduced from 24 to prevent overflow in portrait mode
    $gap = 4;       // Reduced from 8
    $iconSpace = 52;

    // Calculate widths for precise centering
    $bboxHigh = imagettfbbox($fontSize, 0, $fontPathReg, $highText);
    $wH = $bboxHigh[2] - $bboxHigh[0];
    $bboxLow = imagettfbbox($fontSize, 0, $fontPathBold, $lowText);
    $wL = $bboxLow[2] - $bboxLow[0];
    
    $totalTWidth = $wH + $gap + $wL;
    $availableW = $width - $iconSpace;
    
    // Center the pair in the space to the right of the icon
    $startX = $iconSpace + ($availableW - $totalTWidth) / 2;
    
    // Ensure we don't overlap the icon or go off-screen
    if ($startX < $iconSpace) $startX = $iconSpace + 2;
    if ($startX + $totalTWidth > $width - 2) {
        $startX = $width - $totalTWidth - 2;
    }

    $textY = 18; // Adjusted vertical position for smaller font
    drawText($image, $highText, $startX, $textY, $black, $fontSize);
    drawText($image, $lowText, $startX + $wH + $gap, $textY, $gray, $fontSize, true);

    // Row 2: Black background for the Date
    $dateRowHeight = 30; // Increased from 28
    $dateY = $headerHeight - 2; // Moved up by 2px
    imagefilledrectangle($image, 0, $dateY, $width, $dateY + $dateRowHeight, $black);
    
    $dateText = $currentDateInfo['dayname'] . ' ' . $currentDateInfo['month'] . ' ' . $currentDateInfo['day'];
    drawCenteredText($image, $dateText, $width / 2, $dateY + 7, $white, 14, true);

    $startY = $dateY + $dateRowHeight;
    $rowHeight = 49; // Increased from 42 to fill the gap (49 * 4 = 196)

    foreach ($forecasts as $index => $forecast) {
        if ($index === 0) continue; 
        
        $y = $startY + (($index - 1) * $rowHeight);

        // Future days: Day name (left), Icon (center), right-aligned high/low (right)
        drawText($image, $forecast['dayname'], 5, $y + 5, $black, 12);

        $baseSymbol = str_replace(['_day', '_night'], '', $forecast['symbol']);
        $iconPath = "icons/{$baseSymbol}.png";
        $weatherIcon = loadAndResizeIcon($iconPath, 38, 38);

        if (!$weatherIcon) {
            $iconPath = "icons/{$forecast['symbol']}.png";
            $weatherIcon = loadAndResizeIcon($iconPath, 38, 38);
        }

        if ($weatherIcon) {
            imagecopy($image, $weatherIcon, ($width / 2) - 19, $y + 2, 0, 0, 38, 38);
            imagedestroy($weatherIcon);
        }

        // Right-aligned temperatures
        drawRightAlignedText($image, sprintf('%d°', $forecast['high']), $width - 5, $y + 4, $black, 14);
        drawRightAlignedText($image, sprintf('%d°', $forecast['low']), $width - 5, $y + 24, $gray, 14, true);

        if ($index < count($forecasts) - 1) {
            imageline($image, 5, $y + $rowHeight - 1, $width - 5, $y + $rowHeight - 1, $gray);
        }
    }

    drawBattery($batteryVoltage, $image);
    drawUpdated($updated, $timezoneOffset, $image);
    return $image;
}

function createWeatherDisplay($weatherData, $batteryVoltage = 3.8, $timezoneOffset = 0, $orientation = 'landscape_left') {
    if (in_array($orientation, ['portrait_up', 'portrait_down', 'portrait_left'])) {
        $width = DISPLAY_HEIGHT;  
        $height = DISPLAY_WIDTH;  
    } else {
        $width = DISPLAY_WIDTH;   
        $height = DISPLAY_HEIGHT; 
    }

    $image = imagecreate($width, $height);

    $white = imagecolorallocate($image, 255, 255, 255);
    $black = imagecolorallocate($image, 0, 0, 0);
    $gray = imagecolorallocate($image, 128, 128, 128);

    imagefill($image, 0, 0, $white);

    if (!$weatherData) {
        imagestring($image, 3, 5, 50, "Weather unavailable", $black);
        return $image;
    }

    $timeseries = $weatherData['properties']['timeseries'];
    $current = $timeseries[0]['data']['instant']['details'];
    $forecast = $timeseries[0]['data']['next_12_hours'];
    $updated = $weatherData['properties']['meta']['updated_at'];

    $humidity = round($current['relative_humidity']);
    $wind = $current['wind_speed'];
    $windDirection = round($current['wind_from_direction'] ?? 0);
    $symbol = $forecast['summary']['symbol_code'] ?? 'unknown';

    $dateInfo = getDateInfo($updated, $timezoneOffset);
    $currentDate = $dateInfo['date'];

    list($minTemp, $maxTemp, $minTime, $maxTime) = getCalendarDayTempTimes($timeseries, $currentDate, $timezoneOffset);

    $precipitation = findPrecipitation($timeseries, $timezoneOffset);
    $moonPhase = getMoonPhase($timeseries);

    $baseSymbol = str_replace(['_day', '_night'], '', $symbol);
    $iconPath = "icons/{$baseSymbol}.png";
    $weatherIcon = loadAndResizeIcon($iconPath, 128, 128);

    if (!$weatherIcon) {
        $iconPath = "icons/{$symbol}.png";
        $weatherIcon = loadAndResizeIcon($iconPath, 128, 128);
    }

    if ($weatherIcon) {
        imagecopy($image, $weatherIcon, 70, 0, 0, 0, 128, 128);

        if (!empty($precipitation)) {
            $startTime = $precipitation[0]['time'];
            $endTime = count($precipitation) > 1 ? end($precipitation)['time'] : $startTime;
            $amount = $precipitation[0]['amount'];
            $precipText = sprintf('%.1fmm %s', $amount, $startTime === $endTime ? $startTime : "$startTime-$endTime");

            $fontPath = __DIR__ . '/B612-Regular.ttf';
            if (file_exists($fontPath)) {
                $size = 10;
                $bbox = imagettfbbox($size, 0, $fontPath, $precipText);
                $textWidth = $bbox[2] - $bbox[0];
                $textHeight = $bbox[1] - $bbox[7];
                $textX = 134 - ($textWidth / 2);
                $textY = 60;

                imagefilledrectangle($image, $textX - 3, $textY - $textHeight - 3, $textX + $textWidth + 3, $textY + 3, $white);
                imagerectangle($image, $textX - 3, $textY - $textHeight - 3, $textX + $textWidth + 3, $textY + 3, $black);
                imagettftext($image, $size, 0, $textX, $textY, $black, $fontPath, $precipText);
            } else {
                $textWidth = strlen($precipText) * 7;
                $textX = 134 - ($textWidth / 2);
                $textY = 60;
                imagefilledrectangle($image, $textX - 3, $textY - 3, $textX + $textWidth + 3, $textY + 13, $white);
                imagerectangle($image, $textX - 3, $textY - 3, $textX + $textWidth + 3, $textY + 13, $black);
                imagestring($image, 2, $textX, $textY, $precipText, $black);
            }
        }
        imagedestroy($weatherIcon);
    }

    $leftEdge = 5;
    drawDateWithOrdinal($image, $dateInfo['day'], substr($dateInfo['dayWithOrdinal'], strlen($dateInfo['day'])), $leftEdge, 5, $black);
    imagestring($image, 3, $leftEdge, 50, $dateInfo['month'] . ', ' . $dateInfo['dayname'], $black);

    $humidityIcon = loadAndResizeIcon('icons/wi-humidity.png', 16, 16);
    if ($humidityIcon) {
        imagecopy($image, $humidityIcon, $leftEdge, 77, 0, 0, 16, 16);
        imagestring($image, 3, $leftEdge + 20, 79, $humidity . '%', $gray);
        imagedestroy($humidityIcon);
    } else {
        imagestring($image, 3, $leftEdge, 77, $humidity . '%', $gray);
    }

    $windIconPath = "icons/wind_direction_meteorological_{$windDirection}deg.png";
    $windIcon = loadAndResizeIcon($windIconPath, 12, 12);
    if ($windIcon) {
        imagecopy($image, $windIcon, $leftEdge, 92, 0, 0, 12, 12);
        imagestring($image, 3, $leftEdge + 15, 92, sprintf('%.1fm/s', $wind), $gray);
        imagedestroy($windIcon);
    } else {
        imagestring($image, 3, $leftEdge, 92, sprintf('%.1fm/s', $wind), $gray);
    }

    if ($moonPhase) {
        $moonIcon = loadAndResizeIcon("icons/{$moonPhase}", 16, 16);
        if ($moonIcon) {
            imagecopy($image, $moonIcon, $leftEdge, 112, 0, 0, 16, 16);
            imagedestroy($moonIcon);
        }
    }

    $rightEdge = DISPLAY_WIDTH - 5;
    if ($maxTemp !== null) {
        $highTempRightEdge = drawRightAlignedText($image, sprintf('%.0f°', $maxTemp), $rightEdge - 2, 10, $black, 40);
        if ($maxTime) drawTimeLabel($image, $maxTime, $highTempRightEdge + 2, 38, $black);
    }

    if ($minTemp !== null) {
        $lowTempStr = sprintf('%.0f°', $minTemp);
        $lowTempRightEdge = drawRightAlignedText($image, $lowTempStr, $rightEdge - 2, 70, $gray, 40, true);
        if ($minTime) drawTimeLabel($image, $minTime, $lowTempRightEdge + 2, 98, $black);
    }

    drawBattery($batteryVoltage, $image);
    drawUpdated($updated, $timezoneOffset, $image);
    return $image;
}

$lat = $_GET['lat'] ?? 52.5;
$lon = $_GET['lon'] ?? 13.45;
$batteryVoltage = (float)($_GET['battery'] ?? 3.8);
$timezoneOffset = (int)($_GET['timezone'] ?? 0);
$orientation = $_GET['orientation'] ?? 'landscape_left';

$weatherData = getWeatherData($lat, $lon);

if (in_array($orientation, ['portrait_up', 'portrait_down', 'portrait_left'])) {
    $image = createForecastDisplay($weatherData, $batteryVoltage, $timezoneOffset);
} else {
    $image = createWeatherDisplay($weatherData, $batteryVoltage, $timezoneOffset, $orientation);
}

$finalWidth = imagesx($image);
$finalHeight = imagesy($image);

try {
    if ($orientation === 'portrait_up') {
        // Standard portrait up
        $rotated = imagerotate($image, -90, imagecolorallocate($image, 255, 255, 255));
        if ($rotated !== false) {
            imagedestroy($image);
            $image = $rotated;
            $finalWidth = imagesx($image);
            $finalHeight = imagesy($image);
        }
    } elseif ($orientation === 'portrait_down' || $orientation === 'portrait_left') {
        // Consolidated logic for portrait_down and portrait_left
        $rotated = imagerotate($image, 90, imagecolorallocate($image, 255, 255, 255));
        if ($rotated !== false) {
            imagedestroy($image);
            $image = $rotated;
            $finalWidth = imagesx($image);
            $finalHeight = imagesy($image);
        }
    }
} catch (Exception $e) {
    error_log("Image rotation failed: " . $e->getMessage());
}

$indexed = imagecreate($finalWidth, $finalHeight);
$white = imagecolorallocate($indexed, 255, 255, 255);
$lightgray = imagecolorallocate($indexed, 170, 170, 170);
$darkgray = imagecolorallocate($indexed, 85, 85, 85);
$black = imagecolorallocate($indexed, 0, 0, 0);

for ($y = 0; $y < $finalHeight; $y++) {
    for ($x = 0; $x < $finalWidth; $x++) {
        $colorIndex = imagecolorat($image, $x, $y);
        $rgb = imagecolorsforindex($image, $colorIndex);
        $grayVal = (int)(0.299 * $rgb['red'] + 0.587 * $rgb['green'] + 0.114 * $rgb['blue']);

        if ($grayVal > 192) $color = $white;
        elseif ($grayVal > 128) $color = $lightgray;
        elseif ($grayVal > 64) $color = $darkgray;
        else $color = $black;

        imagesetpixel($indexed, $x, $y, $color);
    }
}

// Draw border directly on the final image
imagerectangle($indexed, 0, 0, $finalWidth - 1, $finalHeight - 1, $black);

imagebmp($indexed);
imagedestroy($indexed);
imagedestroy($image);
?>
