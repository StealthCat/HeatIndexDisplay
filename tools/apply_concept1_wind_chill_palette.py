from pathlib import Path

FILES = [
    Path("T-Display-S3/src/display_ui.cpp"),
    Path("Waveshare-ESP32-S3-Touch-LCD-2.8/src/display_ui.cpp"),
]

OLD = '''  if (windChillApplies()) {
    return {"", rgb565(18, 79, 134), rgb565(6, 25, 44),
            rgb565(88, 183, 255), rgb565(8, 28, 49), rgb565(123, 201, 255)};
  }
'''

NEW = '''  if (windChillApplies()) {
    // The NWS wind-chill chart colors indicate approximate frostbite time:
    // light blue = 30 minutes, deeper blue = 10 minutes, purple = 5 minutes.
    // The NWS threshold guidance is approximately -18F, -32F and -48F.
    // Concept 1 keeps its dark vertical-gradient treatment while following
    // that progression as the calculated wind chill becomes more dangerous.
    if (apparentF <= -48.0f) {
      return {"", rgb565(108, 58, 168), rgb565(31, 15, 67),
              rgb565(190, 132, 242), rgb565(39, 18, 79), rgb565(219, 172, 255)};
    }
    if (apparentF <= -32.0f) {
      return {"", rgb565(37, 105, 184), rgb565(10, 34, 78),
              rgb565(99, 171, 255), rgb565(9, 30, 67), rgb565(139, 198, 255)};
    }
    if (apparentF <= -18.0f) {
      return {"", rgb565(78, 166, 218), rgb565(13, 61, 96),
              rgb565(158, 223, 255), rgb565(11, 48, 76), rgb565(194, 235, 255)};
    }
    return {"", rgb565(18, 79, 134), rgb565(6, 25, 44),
            rgb565(88, 183, 255), rgb565(8, 28, 49), rgb565(123, 201, 255)};
  }
'''

for path in FILES:
    text = path.read_text(encoding="utf-8")
    count = text.count(OLD)
    if count != 1:
        raise SystemExit(f"{path}: expected one cold palette block, found {count}")
    text = text.replace(OLD, NEW, 1)

    text = text.replace(
        "// Concept 1 hero panel. In heat-index mode the gradient follows the\n"
        "  // NWS-inspired green/yellow/orange/red/magenta risk progression.",
        "// Concept 1 hero panel. Heat Index follows the NWS-inspired HeatRisk\n"
        "  // progression; Wind Chill follows the NWS frostbite-time chart colors."
    )

    path.write_text(text, encoding="utf-8")
    print(f"updated {path}")
