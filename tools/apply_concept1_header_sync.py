from pathlib import Path


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"{label}: expected exactly one match, found {count}")
    return text.replace(old, new, 1)


# LILYGO T-Display S3: add the same date string used by Waveshare at top-right.
path = Path("T-Display-S3/src/display_ui.cpp")
text = path.read_text(encoding="utf-8")
text = replace_once(
    text,
    '''void drawHeader() {
  display.setTextDatum(textdatum_t::middle_left);
  String station = cfg.stationName.length() ? cfg.stationName : "Weather Station";

  if (station.length() <= 12) {
    display.setFont(&fonts::Font4);
  } else {
    display.setFont(&fonts::Font2);
    if (station.length() > 18) station = station.substring(0, 18);
  }
  drawBoldText(station, 8, 18, C_WHITE);

  display.setFont(&fonts::Font0);
  display.setTextSize(0.72f);
  display.setTextColor(rgb565(159, 190, 209));
  display.drawString("CURRENT CONDITIONS", 27, 34);
  display.setTextSize(1.0f);
  display.drawFastHLine(8, 34, 12, rgb565(126, 200, 232));
}
''',
    '''void drawHeader() {
  String station = cfg.stationName.length() ? cfg.stationName : "Weather Station";

  // Leave enough room for the full date at upper-right, matching Waveshare.
  // Short station names can keep the larger face; typical names such as
  // "Cronin Farm" use Font2 so the header remains clean at 170 px wide.
  display.setTextDatum(textdatum_t::middle_left);
  if (station.length() <= 7) {
    display.setFont(&fonts::Font4);
  } else {
    display.setFont(&fonts::Font2);
    if (station.length() > 14) station = station.substring(0, 14);
  }
  drawBoldText(station, 8, 18, C_WHITE);

  String dateStr = currentDateText();
  display.setFont(&fonts::Font0);
  display.setTextSize(0.62f);
  display.setTextDatum(textdatum_t::middle_right);
  display.setTextColor(rgb565(219, 231, 238));
  display.drawString(dateStr, 162, 18);

  display.setTextDatum(textdatum_t::middle_left);
  display.setTextSize(0.72f);
  display.setTextColor(rgb565(159, 190, 209));
  display.drawString("CURRENT CONDITIONS", 27, 34);
  display.setTextSize(1.0f);
  display.drawFastHLine(8, 34, 12, rgb565(126, 200, 232));
}
''',
    "T-Display header date",
)
path.write_text(text, encoding="utf-8")


# Waveshare: use the same Current Conditions subtitle as the LILYGO.
path = Path("Waveshare-ESP32-S3-Touch-LCD-2.8/src/display_ui.cpp")
text = path.read_text(encoding="utf-8")
text = replace_once(
    text,
    '  printBoldAt(12, 34, "WEATHER STATION", rgb565(157, 184, 202), 1);\n',
    '  printBoldAt(12, 34, "CURRENT CONDITIONS", rgb565(157, 184, 202), 1);\n',
    "Waveshare Current Conditions subtitle",
)
path.write_text(text, encoding="utf-8")

print("Synchronized Concept 1 headers across both production targets.")
