from pathlib import Path

PROJECTS = [Path('T-Display-S3'), Path('Waveshare-ESP32-S3-Touch-LCD-2.8')]


def rep(path, old, new, label):
    text = path.read_text(encoding='utf-8')
    if old not in text:
        raise RuntimeError(f'{label}: marker not found in {path}')
    path.write_text(text.replace(old, new, 1), encoding='utf-8')
    print(f'{label}: applied')

for project in PROJECTS:
    p = project / 'src' / 'web_ui.cpp'

    rep(p,
        '''    if (wx.summaryValid) {
      html += F("Today's high / low: <b>");
      html += String(wx.todayHighF, 1);
      html += F("&deg;F / ");
      html += String(wx.todayLowF, 1);
      html += F("&deg;F</b><br>");
    }
''',
        '''    if (wx.forecastValid) {
      html += F("Forecast today high / low: <b>");
      html += String(wx.forecastTodayHighF, 1);
      html += F("&deg;F / ");
      html += String(wx.forecastTodayLowF, 1);
      html += F("&deg;F</b><br>");
      html += F("Forecast tomorrow high / low: <b>");
      html += String(wx.forecastTomorrowHighF, 1);
      html += F("&deg;F / ");
      html += String(wx.forecastTomorrowLowF, 1);
      html += F("&deg;F</b><br>");
    }
''',
        f'{project}: root forecast high-low')

    rep(p,
        '''  html += F("<p class='muted'>The selected source is used for current conditions and its REST history API supplies From Yesterday and Today's High / Low.</p></div>");
''',
        '''  html += F("<p class='muted'>The selected source is used for current conditions and its REST history API supplies From Yesterday. Forecast High / Low uses the station coordinates with the Open-Meteo forecast REST API.</p></div>");
''',
        f'{project}: configuration forecast description')

    rep(p,
        '''    if (wx.summaryValid) {
      s += ",\\\"today_high_f\\\":" + String(wx.todayHighF, 2);
      s += ",\\\"today_low_f\\\":" + String(wx.todayLowF, 2);
    }
    s += ",\\\"observation_age_seconds\\\":" + String(observationAgeSeconds());
''',
        '''    if (wx.summaryValid) {
      s += ",\\\"observed_today_high_f\\\":" + String(wx.todayHighF, 2);
      s += ",\\\"observed_today_low_f\\\":" + String(wx.todayLowF, 2);
    }
    if (wx.forecastValid) {
      s += ",\\\"forecast_today_high_f\\\":" + String(wx.forecastTodayHighF, 2);
      s += ",\\\"forecast_today_low_f\\\":" + String(wx.forecastTodayLowF, 2);
      s += ",\\\"forecast_tomorrow_high_f\\\":" + String(wx.forecastTomorrowHighF, 2);
      s += ",\\\"forecast_tomorrow_low_f\\\":" + String(wx.forecastTomorrowLowF, 2);
    }
    s += ",\\\"observation_age_seconds\\\":" + String(observationAgeSeconds());
''',
        f'{project}: JSON forecast fields')

    rep(p,
        '''  if (lastApiError.length()) {
''',
        '''  if (lastForecastHttpCode) {
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
''',
        f'{project}: forecast status rows')

print('V7.9 web consistency patch applied successfully')
