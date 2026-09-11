from pathlib import Path

path = Path('T-Display-S3/src/display_ui.cpp')
text = path.read_text()


def swap(old, new, name):
    global text
    if old not in text:
        raise SystemExit(f'{name}: source block not found')
    text = text.replace(old, new, 1)

# Metric-card labels: use native Font0 size 1.0 instead of fractional scaling.
swap('''  display.setTextDatum(textdatum_t::middle_center);\n  display.setFont(&fonts::Font0);\n  display.setTextSize(label.length() > 9 ? 0.62f : 0.70f);\n  drawBoldText(label, x + w / 2, y + 10, cyan);\n  display.setTextSize(1.0f);\n''', '''  display.setTextDatum(textdatum_t::middle_center);\n  display.setFont(&fonts::Font0);\n  display.setTextSize(1.0f);\n  drawBoldText(label, x + w / 2, y + 10, cyan);\n''', 'metric label font')

# Header date: native Font2, no scaled Font0.
swap('''  display.setTextDatum(textdatum_t::middle_right);\n  display.setFont(&fonts::Font0);\n  display.setTextSize(0.78f);\n  display.setTextColor(rgb565(231, 241, 247));\n  display.drawString(currentDateText(), 309, 15);\n  display.setTextSize(1.0f);\n''', '''  display.setTextDatum(textdatum_t::middle_right);\n  display.setFont(&fonts::Font2);\n  display.setTextColor(rgb565(231, 241, 247));\n  display.drawString(currentDateText(), 309, 15);\n''', 'header date font')

# Status bar: use readable native fonts and shorter button hints.
swap('''  drawClockIcon(13, 147, muted);\n  display.setTextDatum(textdatum_t::middle_left);\n  display.setFont(&fonts::Font0);\n  display.setTextSize(0.74f);\n  display.setTextColor(C_WHITE);\n  display.drawString(left, 25, 147);\n\n  // Fixed left-anchored status geometry prevents ONLINE/OFFLINE from\n  // crowding or clipping against the physical right edge.\n  display.fillCircle(267, 147, 2, stateColor);\n  display.setTextDatum(textdatum_t::middle_left);\n  display.setTextSize(0.74f);\n  drawBoldText(state, 274, 147, stateColor);\n\n  if (buttonHint && buttonHint[0]) {\n    display.setTextDatum(textdatum_t::middle_center);\n    display.setTextSize(0.68f);\n    display.setTextColor(muted);\n    display.drawString(buttonHint, 160, 162);\n  }\n  display.setTextSize(1.0f);\n''', '''  drawClockIcon(13, 147, muted);\n  display.setTextDatum(textdatum_t::middle_left);\n  display.setFont(&fonts::Font2);\n  display.setTextColor(C_WHITE);\n  display.drawString(left, 25, 147);\n\n  // Fixed left-anchored status geometry prevents ONLINE/OFFLINE from\n  // crowding or clipping against the physical right edge.\n  display.fillCircle(259, 147, 2, stateColor);\n  display.setTextDatum(textdatum_t::middle_left);\n  display.setFont(&fonts::Font2);\n  drawBoldText(state, 266, 147, stateColor);\n\n  if (buttonHint && buttonHint[0]) {\n    display.setTextDatum(textdatum_t::middle_center);\n    display.setFont(&fonts::Font0);\n    display.setTextSize(1.0f);\n    display.setTextColor(muted);\n    display.drawString(buttonHint, 160, 163);\n  }\n''', 'status bar fonts')

# Shorter footer hints so native Font0 remains clear.
text = text.replace('"EITHER BUTTON: HEAT INDEX"', '"BUTTON: HEAT INDEX"')
text = text.replace('"EITHER BUTTON: DETAILS"', '"BUTTON: DETAILS"')

# Waiting-screen supporting text: native Font2/Font0 only.
text = text.replace('''    display.setFont(&fonts::Font0);\n    display.setTextSize(0.82f);\n    display.setTextColor(rgb565(114, 202, 255));\n    display.drawString(setupApName(), 160, 109);\n''', '''    display.setFont(&fonts::Font2);\n    display.setTextColor(rgb565(114, 202, 255));\n    display.drawString(setupApName(), 160, 109);\n''', 1)
text = text.replace('''    display.setFont(&fonts::Font0);\n    display.setTextSize(0.82f);\n    display.setTextColor(rgb565(114, 202, 255));\n''', '''    display.setFont(&fonts::Font2);\n    display.setTextColor(rgb565(114, 202, 255));\n''', 1)

# Hero header date and right-side labels: native fonts only.
swap('''  display.setTextDatum(textdatum_t::middle_right);\n  display.setFont(&fonts::Font0);\n  display.setTextSize(0.78f);\n  display.setTextColor(rgb565(241, 247, 250));\n  display.drawString(currentDateText(), 310, 14);\n  display.setTextSize(1.0f);\n''', '''  display.setTextDatum(textdatum_t::middle_right);\n  display.setFont(&fonts::Font2);\n  display.setTextColor(rgb565(241, 247, 250));\n  display.drawString(currentDateText(), 310, 14);\n''', 'hero date font')

swap('''  display.setFont(&fonts::Font0);\n  display.setTextSize(0.72f);\n  display.setTextColor(rgb565(245, 249, 252));\n  display.drawString("CURRENT RISK", 249, 41);\n  display.setTextSize(1.0f);\n\n  display.fillRoundRect(188, 52, 124, 37, 18, risk.status);\n  display.drawRoundRect(188, 52, 124, 37, 18, risk.accent);\n  display.setFont(&fonts::Font4);\n  String riskLabel = apparentRiskLabel();\n  if (display.textWidth(riskLabel) > 112) {\n    display.setFont(&fonts::Font2);\n  }\n  drawBoldText(riskLabel, 250, 70, risk.accent);\n\n  display.setFont(&fonts::Font0);\n  display.setTextSize(0.78f);\n  display.setTextColor(rgb565(245, 249, 252));\n  display.drawString(cold ? "APPARENT COLD" : "APPARENT HEAT", 250, 103);\n  display.setTextSize(0.72f);\n  display.drawString("LIVE CONDITIONS", 250, 119);\n  display.setTextSize(1.0f);\n''', '''  display.setFont(&fonts::Font2);\n  display.setTextColor(rgb565(245, 249, 252));\n  display.drawString("RISK", 250, 41);\n\n  display.fillRoundRect(191, 53, 118, 35, 17, risk.status);\n  display.drawRoundRect(191, 53, 118, 35, 17, risk.accent);\n  display.setFont(&fonts::Font2);\n  drawBoldText(apparentRiskLabel(), 250, 70, risk.accent);\n\n  display.setFont(&fonts::Font2);\n  display.setTextColor(rgb565(245, 249, 252));\n  display.drawString(cold ? "APPARENT COLD" : "APPARENT HEAT", 250, 105);\n  display.setFont(&fonts::Font0);\n  display.setTextSize(1.0f);\n  display.drawString("LIVE", 250, 121);\n''', 'hero risk fonts')

# Verify no fractional Font0 sizing remains in the landscape implementation.
for bad in ('0.54f', '0.58f', '0.62f', '0.68f', '0.70f', '0.72f', '0.74f', '0.78f', '0.80f', '0.82f'):
    text = text.replace(f'display.setTextSize({bad});', 'display.setTextSize(1.0f);')

path.write_text(text)
