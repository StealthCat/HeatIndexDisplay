from pathlib import Path

PROJECTS = [Path('T-Display-S3'), Path('Waveshare-ESP32-S3-Touch-LCD-2.8')]

BAD_WAITING = '''    if (lastForecastHttpCode) {
    html += F("<tr><th>Forecast HTTP code</th><td>");
    html += String(lastForecastHttpCode);
    html += F("</td></tr>");
  }
  if (lastForecastError.length()) {
    html += F("<tr><th>Forecast warning</th><td class='bad'>");
    html += htmlEscape(lastForecastError);
    html += F("</td></tr>");
  }

  if (lastApiError.length()) {
      html += htmlEscape(lastApiError);
    } else {
      html += F("Waiting for the first successful weather-source poll.");
    }
'''

GOOD_WAITING = '''    if (lastApiError.length()) {
      html += htmlEscape(lastApiError);
    } else {
      html += F("Waiting for the first successful weather-source poll.");
    }
'''

STATUS_MARKER = '''  if (lastSummaryError.length()) {
    html += F("<tr><th>History warning</th><td class='bad'>");
    html += htmlEscape(lastSummaryError);
    html += F("</td></tr>");
  }

  if (lastApiError.length()) {
'''

STATUS_REPLACEMENT = '''  if (lastSummaryError.length()) {
    html += F("<tr><th>History warning</th><td class='bad'>");
    html += htmlEscape(lastSummaryError);
    html += F("</td></tr>");
  }

  if (lastForecastHttpCode) {
    html += F("<tr><th>Forecast HTTP code</th><td>");
    html += String(lastForecastHttpCode);
    html += F("</td></tr>");
  }
  if (lastForecastError.length()) {
    html += F("<tr><th>Forecast warning</th><td class='bad'>");
    html += htmlEscape(lastForecastError);
    html += F("</td></tr>");
  }

  if (lastApiError.length()) {
'''

for project in PROJECTS:
    p = project / 'src' / 'web_ui.cpp'
    text = p.read_text(encoding='utf-8')

    if BAD_WAITING not in text:
        raise RuntimeError(f'Bad waiting block not found in {p}')
    text = text.replace(BAD_WAITING, GOOD_WAITING, 1)

    if STATUS_MARKER not in text:
        raise RuntimeError(f'Status insertion marker not found in {p}')
    text = text.replace(STATUS_MARKER, STATUS_REPLACEMENT, 1)

    p.write_text(text, encoding='utf-8')
    print(f'Fixed web forecast status placement in {p}')

print('V7.9 web fixup applied successfully')
