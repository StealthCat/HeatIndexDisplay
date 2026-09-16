from pathlib import Path

path = Path('Waveshare-ESP32-S3-Touch-LCD-2.8/src/display_ui.cpp')
text = path.read_text()
old = '  centerBoldText(apparentRiskLabel(), 74, 172, 2, risk.accent);\n'
new = '''  const String riskLabelText = apparentRiskLabel();\n  if (tDisplayTextWidth(riskLabelText, 2) <= 96) {\n    centerBoldText(riskLabelText, 74, 172, 2, risk.accent);\n  } else {\n    const int split = riskLabelText.indexOf(' ');\n    if (split > 0) {\n      centerBoldText(riskLabelText.substring(0, split), 74, 170, 1, risk.accent);\n      centerBoldText(riskLabelText.substring(split + 1), 74, 180, 1, risk.accent);\n    } else {\n      centerBoldText(riskLabelText, 74, 176, 1, risk.accent);\n    }\n  }\n'''
if old not in text:
    raise SystemExit('target risk pill line not found')
text = text.replace(old, new, 1)
path.write_text(text)

updated = path.read_text()
required = [
    'tDisplayTextWidth(riskLabelText, 2) <= 96',
    'riskLabelText.indexOf',
    'substring(0, split)',
    'substring(split + 1)',
    'centerBoldText(riskLabelText, 74, 172, 2, risk.accent);',
]
for item in required:
    if item not in updated:
        raise SystemExit(f'missing expected contract: {item}')
print('Waveshare 2.8 risk pill now adapts long status labels')
