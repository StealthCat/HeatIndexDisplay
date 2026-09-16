from pathlib import Path

ROOT = Path('.')
T = ROOT / 'T-Display-S3/src/display_ui.cpp'
W28 = ROOT / 'Waveshare-ESP32-S3-Touch-LCD-2.8/src/display_ui.cpp'
W7 = ROOT / 'Waveshare-ESP32-S3-Touch-LCD-7C-BOX/src/display_ui.cpp'
MATH = [
    ROOT / 'T-Display-S3/src/weather_math.cpp',
    ROOT / 'Waveshare-ESP32-S3-Touch-LCD-2.8/src/weather_math.cpp',
    ROOT / 'Waveshare-ESP32-S3-Touch-LCD-7C-BOX/src/weather_math.cpp',
]

# Fix the one UI regression found during the audit: the T-Display's risk
# section title was hard-coded to HEAT RISK even when wind chill applied.
s = T.read_text()
old = 'drawBoldText("HEAT RISK", 251, 48, C_WHITE);'
new = 'drawBoldText(cold ? "COLD RISK" : "HEAT RISK", 251, 48, C_WHITE);'
if old in s:
    s = s.replace(old, new, 1)
elif new not in s:
    raise SystemExit('T-Display risk heading anchor not found')
T.write_text(s)

# Weather-mode selection and labels must remain byte-for-byte identical across
# all production targets.
math_blobs = [p.read_bytes() for p in MATH]
assert math_blobs[0] == math_blobs[1] == math_blobs[2], 'weather_math.cpp drift across targets'
math_text = math_blobs[0].decode()
assert 'wx.tempF <= 50.0f && wx.windMph > 3.0f' in math_text
assert 'return windChillApplies() ? wx.windChillF : wx.heatIndexF;' in math_text
assert 'return windChillApplies() ? "WIND CHILL" : "HEAT INDEX";' in math_text
assert 'return windChillApplies() ? coldRiskLabel(wx.windChillF) : riskLabel(wx.heatIndexF);' in math_text
for label in ('"CHILLY"', '"COLD"', '"VERY COLD"', '"DANGER"', '"EXTREME DANGER"'):
    assert label in math_text

# Every display must use the same cold-mode palette and dynamic title/risk path.
# These RGB triplets are the shared wind-chill progression used by all three
# production display implementations.
cold_palette_tokens = [
    '108, 58, 168', '31, 15, 67', '190, 132, 242', '39, 18, 79', '219, 172, 255',
    '37, 105, 184', '10, 34, 78', '99, 171, 255', '9, 30, 67', '139, 198, 255',
    '78, 166, 218', '13, 61, 96', '158, 223, 255', '11, 48, 76', '194, 235, 255',
    '18, 79, 134', '6, 25, 44', '88, 183, 255', '8, 28, 49', '123, 201, 255',
]
for p in (T, W28, W7):
    text = p.read_text()
    assert 'RiskStyle risk = riskFor(apparentF);' in text, f'missing dynamic risk style in {p}'
    assert 'const bool cold = windChillApplies();' in text, f'missing cold-mode switch in {p}'
    assert 'apparentTitle()' in text, f'missing dynamic apparent title in {p}'
    assert 'apparentRiskLabel()' in text, f'missing dynamic risk label in {p}'
    assert 'if (cold) drawHeroWind' in text, f'missing wind hero in {p}'
    for token in cold_palette_tokens:
        assert token in text, f'cold palette drift ({token}) in {p}'

assert new in T.read_text()
print('Wind-chill display contract verified across all three production targets')
