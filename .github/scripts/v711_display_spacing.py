from pathlib import Path


def rep(path, old, new):
    p = Path(path)
    s = p.read_text()
    if old not in s:
        raise RuntimeError(f'pattern not found in {path}: {old[:80]}')
    p.write_text(s.replace(old, new))

# T-Display: degree units, lower labels/values, forecast emphasis, wind position.
t='T-Display-S3/src/display_ui.cpp'
rep(t, '  s += "F";\n  return s;\n}', '  s += String("\\xB0");\n  s += "F";\n  return s;\n}')
rep(t, '  drawBoldText(tomorrow ? "TOMORROW HIGH / LOW" : "TODAY HIGH / LOW", 37, 264, cyan);', '  drawBoldText(tomorrow ? "TOMORROW HIGH / LOW F" : "TODAY HIGH / LOW F", 37, 264, cyan);')
rep(t, '      hl = String(high, 1) + " / " + String(low, 1) + "F";', '      hl = String((int)lroundf(high)) + String("\\xB0") + " / " + String((int)lroundf(low)) + String("\\xB0");')
rep(t, '  display.setFont(&fonts::Font2);\n  drawBoldText(hl, 37, 278, C_WHITE);', '  display.setFont(&fonts::Font4);\n  drawBoldText(hl, 37, 278, C_WHITE);')
for a,b in [('29, 154','29, 157'),('29, 170','29, 173'),('113, 154','113, 157'),('113, 170','113, 173'),('31, 191','31, 194'),('31, 207','31, 210'),('113, 191','113, 194'),('113, 207','113, 210'),('29, 228','31, 231'),('29, 245','34, 242'),('115, 228','115, 231'),('115, 245','115, 248')]:
    rep(t,a,b)
rep(t, 'String(wx.tempF, 1) + "F"', 'String(wx.tempF, 1) + String("\\xB0") + "F"')
rep(t, 'String(wx.dewPointF, 1) + "F"', 'String(wx.dewPointF, 1) + String("\\xB0") + "F"')
rep(t, '  drawWindIcon(13, 231, cyan);', '  drawWindIcon(13, 232, cyan);')

# Waveshare: lower labels/values, degree units, larger forecast temps, wind alignment.
w='Waveshare-ESP32-S3-Touch-LCD-2.8/src/display_ui.cpp'
rep(w, '  s += "F";\n  return s;\n}', '  s += String((char)247);\n  s += "F";\n  return s;\n}')
# Forecast function: replace value block with individually-positioned larger high/low values.
old='''  String hl = "-- / --";\n  if (wx.forecastValid) {\n    float high = tomorrow ? wx.forecastTomorrowHighF : wx.forecastTodayHighF;\n    float low = tomorrow ? wx.forecastTomorrowLowF : wx.forecastTodayLowF;\n    if (isfinite(high) && isfinite(low)) {\n      hl = String((int)lroundf(high)) + "/" + String((int)lroundf(low)) + "F";\n    }\n  }\n  printBoldAt(174, 242, hl, C_WHITE, 1);'''
new='''  float high = tomorrow ? wx.forecastTomorrowHighF : wx.forecastTodayHighF;\n  float low = tomorrow ? wx.forecastTomorrowLowF : wx.forecastTodayLowF;\n  if (wx.forecastValid && isfinite(high) && isfinite(low)) {\n    String highText = String((int)lroundf(high)) + String((char)247);\n    String lowText = String((int)lroundf(low)) + String((char)247);\n    printBoldAt(146, 239, highText, C_WHITE, 2);\n    printBoldAt(183, 244, " / ", C_WHITE, 1);\n    printBoldAt(191, 239, lowText, C_WHITE, 2);\n  } else {\n    printBoldAt(166, 239, "-- / --", C_WHITE, 2);\n  }'''
rep(w,old,new)
rep(w, 'printBoldAt(174, 219, "HIGH / LOW", muted, 1);', 'printBoldAt(174, 219, "HIGH / LOW F", muted, 1);')
# Move right-card labels down 2px and values down 2px.
for a,b in [('169, 67','169, 69'),('169, 77','169, 79'),('169, 100','169, 102'),('169, 110','169, 112'),('169, 133','169, 135'),('169, 143','169, 145'),('169, 166','169, 168'),('169, 178','169, 180')]:
    rep(w,a,b)
rep(w, 'String(wx.tempF, 1) + "F"', 'String(wx.tempF, 1) + String((char)247) + "F"')
rep(w, 'String(wx.dewPointF, 1) + "F"', 'String(wx.dewPointF, 1) + String((char)247) + "F"')
# Wind icon lower, value rightward into the free area between icon and border.
rep(w, '  drawWindIcon(16, 219, cyan);', '  drawWindIcon(16, 223, cyan);')
rep(w, 'centerBoldText(isfinite(wx.windMph) ? String(wx.windMph, 1) : "--", 42, 220, 2, C_WHITE);', 'centerBoldText(isfinite(wx.windMph) ? String(wx.windMph, 1) : "--", 53, 220, 2, C_WHITE);')
rep(w, 'centerBoldText("mph", 41, 239, 1, muted);', 'centerBoldText("mph", 53, 239, 1, muted);')
