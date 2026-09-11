from pathlib import Path

path = Path('T-Display-S3/src/display_ui.cpp')
text = path.read_text()
old = '''  // A single rectangular risk card is cleaner and avoids the crowded pill\n  // plus APPARENT/LIVE captions from the previous layout.\n  display.fillRoundRect(190, 47, 122, 70, 9, risk.status);\n  display.drawRoundRect(190, 47, 122, 70, 9, risk.accent);\n  display.setFont(&fonts::Font2);\n  display.setTextColor(C_WHITE);\n  display.drawString("HEAT RISK", 251, 62);\n  display.drawFastHLine(201, 75, 100, risk.accent);\n  drawBoldText(apparentRiskLabel(), 251, 94, risk.accent);\n'''
new = '''  // Keep the section title outside the pill. The pill itself contains only\n  // the category so the hierarchy stays clean and the label can be centered.\n  display.setTextDatum(textdatum_t::middle_center);\n  display.setFont(&fonts::Font2);\n  drawBoldText("HEAT RISK", 251, 48, C_WHITE);\n\n  display.fillRoundRect(193, 61, 116, 48, 24, risk.status);\n  display.drawRoundRect(193, 61, 116, 48, 24, risk.accent);\n  display.setFont(&fonts::Font2);\n  drawBoldText(apparentRiskLabel(), 251, 85, risk.accent);\n'''
if old not in text:
    raise SystemExit('Expected risk-card block not found')
path.write_text(text.replace(old, new, 1))
