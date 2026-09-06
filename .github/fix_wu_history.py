from pathlib import Path

projects = [Path('T-Display-S3'), Path('Waveshare-ESP32-S3-Touch-LCD-2.8')]

for project in projects:
    path = project / 'src' / 'wunderground_weather.cpp'
    text = path.read_text()

    old = '''  filter["observations"][0]["imperial"]["temp"] = true;\n  filter["observations"][0]["imperial"]["windGust"] = true;'''
    new = '''  filter["observations"][0]["imperial"]["tempHigh"] = true;\n  filter["observations"][0]["imperial"]["tempLow"] = true;\n  filter["observations"][0]["imperial"]["tempAvg"] = true;\n  filter["observations"][0]["imperial"]["windgustHigh"] = true;'''
    if old not in text:
        raise RuntimeError(f'{path}: history filter block not found')
    text = text.replace(old, new, 1)

    old = '''  for (JsonObject point : todayDoc["observations"].as<JsonArray>()) {\n    JsonObject imperial = point["imperial"].as<JsonObject>();\n    float pointTemp = wuFloat(imperial["temp"]);\n    float pointGust = wuFloat(imperial["windGust"]);\n\n    if (isfinite(pointTemp)) {\n      if (!isfinite(high) || pointTemp > high) high = pointTemp;\n      if (!isfinite(low) || pointTemp < low) low = pointTemp;\n    }\n    if (isfinite(pointGust) && (!isfinite(maxGust) || pointGust > maxGust)) {\n      maxGust = pointGust;\n    }\n  }\n\n  todayDoc.clear();\n\n  DynamicJsonDocument yesterdayDoc(32768);\n  String yesterdayError;\n  if (!fetchHistoryDate(yesterdayYmd, yesterdayDoc, yesterdayError)) {'''
    new = '''  for (JsonObject point : todayDoc["observations"].as<JsonArray>()) {\n    JsonObject imperial = point["imperial"].as<JsonObject>();\n    float pointHigh = wuFloat(imperial["tempHigh"]);\n    float pointLow = wuFloat(imperial["tempLow"]);\n    float pointGust = wuFloat(imperial["windgustHigh"]);\n\n    if (isfinite(pointHigh) && (!isfinite(high) || pointHigh > high)) high = pointHigh;\n    if (isfinite(pointLow) && (!isfinite(low) || pointLow < low)) low = pointLow;\n    if (isfinite(pointGust) && (!isfinite(maxGust) || pointGust > maxGust)) {\n      maxGust = pointGust;\n    }\n  }\n\n  todayDoc.clear();\n\n  String yesterdayError;\n  if (!fetchHistoryDate(yesterdayYmd, todayDoc, yesterdayError)) {'''
    if old not in text:
        raise RuntimeError(f'{path}: today/yesterday history block not found')
    text = text.replace(old, new, 1)

    old = '''  for (JsonObject point : yesterdayDoc["observations"].as<JsonArray>()) {\n    uint64_t epoch = point["epoch"] | 0ULL;\n    JsonObject imperial = point["imperial"].as<JsonObject>();\n    float pointTemp = wuFloat(imperial["temp"]);'''
    new = '''  for (JsonObject point : todayDoc["observations"].as<JsonArray>()) {\n    uint64_t epoch = point["epoch"] | 0ULL;\n    JsonObject imperial = point["imperial"].as<JsonObject>();\n    float pointTemp = wuFloat(imperial["tempAvg"]);'''
    if old not in text:
        raise RuntimeError(f'{path}: yesterday loop not found')
    text = text.replace(old, new, 1)
    path.write_text(text)

    web = project / 'src' / 'web_ui.cpp'
    html = web.read_text()
    marker = '''  html += htmlEscape(cfg.macAddress);\n  html += F("' placeholder='Leave blank to auto-select first station'></label>");\n\n\n  html += F("<div class='card'><h2>Weather Underground</h2>");'''
    replacement = '''  html += htmlEscape(cfg.macAddress);\n  html += F("' placeholder='Leave blank to auto-select first station'></label>");\n  html += F("</div>");\n\n  html += F("<div class='card'><h2>Weather Underground</h2>");'''
    if marker not in html:
        raise RuntimeError(f'{web}: Ambient card close marker not found')
    web.write_text(html.replace(marker, replacement, 1))

print('Corrected Weather Underground historical field mapping and configuration card layout')
