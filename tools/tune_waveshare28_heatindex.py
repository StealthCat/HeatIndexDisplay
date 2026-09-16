from pathlib import Path

p = Path('Waveshare-ESP32-S3-Touch-LCD-2.8/src/display_ui.cpp')
s = p.read_text()

replacements = {
    '  const int groupW = valueW + 12 + fW;\n  const int startX = 94 - groupW / 2;\n  const int topY = 112;\n':
    '  const int groupW = valueW + 9 + fW;\n  const int startX = 86 - groupW / 2;\n  const int topY = 109;\n',
    '  const int degreeX = startX + valueW + 3;\n  gfx->drawCircle(degreeX, topY + 7, 3, C_WHITE);\n  drawTDisplayTextAt(degreeX + 7, topY + 13, "F", C_WHITE, unitFont);\n':
    '  const int degreeX = startX + valueW + 2;\n  gfx->drawCircle(degreeX, topY + 7, 3, C_WHITE);\n  drawTDisplayTextAt(degreeX + 6, topY + 13, "F", C_WHITE, unitFont);\n',
    '  centerBoldText(apparentTitle(), 94, 66, 2, C_WHITE);\n':
    '  centerBoldText(apparentTitle(), 88, 64, 2, C_WHITE);\n',
    '  gfx->fillRoundRect(18, 170, 112, 24, 12, risk.status);\n  gfx->drawRoundRect(18, 170, 112, 24, 12, risk.accent);\n  centerBoldText(apparentRiskLabel(), 74, 174, 2, risk.accent);\n':
    '  gfx->fillRoundRect(20, 168, 108, 24, 12, risk.status);\n  gfx->drawRoundRect(20, 168, 108, 24, 12, risk.accent);\n  centerBoldText(apparentRiskLabel(), 74, 172, 2, risk.accent);\n',
}

for old, new in replacements.items():
    if s.count(old) != 1:
        raise SystemExit(f'Expected exactly one match for:\n{old}')
    s = s.replace(old, new, 1)

p.write_text(s)
print('Tuned Waveshare 2.8 heat-index hero geometry')
