from pathlib import Path

# Small fit/readability corrections applied after the main V7.10 patch.
t = Path('T-Display-S3/src/display_ui.cpp')
s = t.read_text()
s = s.replace('drawBoldText("WIND / GUST", 32, 228, cyan);', 'drawBoldText("W/G MPH", 29, 228, cyan);')
s = s.replace('drawBoldText(windLine + " mph", 32, 245, C_WHITE);', 'drawBoldText(windLine, 29, 245, C_WHITE);')
s = s.replace('drawBoldText("DIRECTION", 115, 228, cyan);', 'drawBoldText("DIR", 115, 228, cyan);')
t.write_text(s)

w = Path('Waveshare-ESP32-S3-Touch-LCD-2.8/src/display_ui.cpp')
s = w.read_text()
s = s.replace('centerBoldText(apparentRiskLabel(), 74, 161, 2, C_WHITE);', 'centerBoldText(apparentRiskLabel(), 74, 162, 1, C_WHITE);')
s = s.replace('printBoldAt(170, 67, "TEMP", cyan, 1);', 'printBoldAt(169, 67, "TEMP", cyan, 1);')
s = s.replace('printBoldAt(170, 77, String(wx.tempF, 1) + "F", C_WHITE, 2);', 'printBoldAt(169, 77, String(wx.tempF, 1) + "F", C_WHITE, 2);')
s = s.replace('printBoldAt(170, 100, "HUMIDITY", cyan, 1);', 'printBoldAt(169, 100, "HUMIDITY", cyan, 1);')
s = s.replace('printBoldAt(170, 110, String((int)lroundf(wx.humidity)) + "%", C_WHITE, 2);', 'printBoldAt(169, 110, String((int)lroundf(wx.humidity)) + "%", C_WHITE, 2);')
s = s.replace('printBoldAt(170, 133, "DEW POINT", cyan, 1);', 'printBoldAt(169, 133, "DEW POINT", cyan, 1);')
s = s.replace('printBoldAt(170, 143, isfinite(wx.dewPointF) ? String(wx.dewPointF, 1) + "F" : "--", C_WHITE, 2);', 'printBoldAt(169, 143, isfinite(wx.dewPointF) ? String(wx.dewPointF, 1) + "F" : "--", C_WHITE, 2);')
s = s.replace('printBoldAt(170, 166, "FROM YDAY", cyan, 1);', 'printBoldAt(169, 166, "FROM YDAY", cyan, 1);')
s = s.replace('printBoldAt(170, 176, signedTempDelta(wx.fromYesterdayF), C_WHITE, 2);', 'printBoldAt(169, 178, signedTempDelta(wx.fromYesterdayF), C_WHITE, 1);')
s = s.replace('hl = String(high, 1) + "/" + String(low, 1) + "F";', 'hl = String((int)lroundf(high)) + "/" + String((int)lroundf(low)) + "F";')
w.write_text(s)
