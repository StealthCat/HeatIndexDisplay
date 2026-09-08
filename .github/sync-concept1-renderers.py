from pathlib import Path
import re
import json
import hashlib

p = Path('emulator/concept-1/emulator/display_ui.py')
s = p.read_text()

# Production cards are flat RGB565 fills, not decorative gradients.
s = re.sub(
    r'def card\(x, y, w, h, r=7, highlight=False\):\n.*?\n\ndef _updated_text',
    '''def card(x, y, w, h, r=7, highlight=False):
    fill = "#071d2c" if highlight else "#041622"
    return (
        f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{r}" '
        f'fill="{fill}" stroke="#174e6c" stroke-width="1"/>'
    )

def _updated_text''',
    s,
    flags=re.S,
)

# Legacy alert icon is no longer used by production risk pills.
s = re.sub(
    r'\n    elif kind == "alert":\n        body = \(.*?\n        \)\n',
    '\n',
    s,
    flags=re.S,
)

# Production hero gradient is vertical. Risk pills are solid status color.
s = re.sub(
    r'def _hero_gradient_defs\(style\):\n.*?\n\ndef _apparent_parts',
    '''def _hero_gradient_defs(style):
    return (
        '<defs>'
        '<linearGradient id="heroCurrent" x1="0" y1="0" x2="0" y2="1">'
        f'<stop offset="0" stop-color="{style["top"]}"/>'
        f'<stop offset="1" stop-color="{style["bottom"]}"/>'
        '</linearGradient>'
        '</defs>'
    )


def _hero_icon(layout, cold):
    if layout == "tdisplay":
        if cold:
            x, y = 18, 82
            return (
                f'<path d="M{x} {y}H{x+30} M{x+24} {y-4}L{x+30} {y}L{x+24} {y+4} '
                f'M{x-3} {y+9}H{x+25} M{x+19} {y+5}L{x+25} {y+9}L{x+19} {y+13} '
                f'M{x+3} {y+18}H{x+29}" fill="none" stroke="#52beff" stroke-width="1"/>'
            )
        cx, cy, r = 32, 88, 10
        rays = [(12,88,17,88),(47,88,52,88),(32,68,32,73),(32,103,32,108),
                (19,75,23,79),(41,97,45,101),(19,101,23,97),(41,79,45,75)]
    elif layout == "waveshare":
        if cold:
            x, y = 20, 88
            return (
                f'<path d="M{x} {y}H{x+36} M{x+29} {y-5}L{x+36} {y}L{x+29} {y+5} '
                f'M{x-2} {y+11}H{x+30} M{x+23} {y+6}L{x+30} {y+11}L{x+23} {y+16} '
                f'M{x+4} {y+22}H{x+35}" fill="none" stroke="#52beff" stroke-width="1"/>'
            )
        cx, cy, r = 36, 96, 13
        rays = [(14,96,21,96),(52,96,59,96),(36,74,36,81),(36,112,36,119),
                (19,79,24,84),(48,108,53,113),(19,113,24,108),(48,84,53,79)]
    else:
        if cold:
            x, y = 66, 143
            return (
                f'<path d="M{x} {y}H{x+78} M{x+63} {y-10}L{x+78} {y}L{x+63} {y+10} '
                f'M{x-5} {y+25}H{x+65} M{x+50} {y+15}L{x+65} {y+25}L{x+50} {y+35} '
                f'M{x+10} {y+50}H{x+76}" fill="none" stroke="#52beff" stroke-width="1.5"/>'
            )
        cx, cy, r = 110, 160, 28
        rays = [(60,160,74,160),(147,160,161,160),(110,110,110,124),(110,197,110,211),
                (71,121,83,133),(137,187,149,199),(71,199,83,187),(137,133,149,121)]
    lines = ''.join(
        f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="#ffc12b" stroke-width="1.5"/>'
        for x1, y1, x2, y2 in rays
    )
    return f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="#ffc12b" stroke="#ffdc60" stroke-width="1"/>{lines}'


def _clock_icon(cx, cy, r):
    return (
        f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="none" stroke="#a8c6d8" stroke-width="1.5"/>'
        f'<line x1="{cx}" y1="{cy-r+3}" x2="{cx}" y2="{cy}" stroke="#a8c6d8" stroke-width="1.5"/>'
        f'<line x1="{cx}" y1="{cy}" x2="{cx + max(3, r//2)}" y2="{cy + max(2, r//3)}" stroke="#a8c6d8" stroke-width="1.5"/>'
    )


def _apparent_parts''',
    s,
    flags=re.S,
)

# Match the production apparent-temperature placement for T-Display and 2.8.
s = re.sub(
    r'def _apparent_parts\(value, layout\):\n.*?\n\ndef _metric',
    '''def _apparent_parts(value, layout):
    value_s = str(value)
    if layout == "tdisplay":
        if len(value_s) >= 3:
            number_x, degree_x, f_x = 98, 133, 145
        else:
            number_x, degree_x, f_x = 102, 132, 144
        return "".join([
            text(number_x, 98, value_s, 35, "middle", WHITE, "900"),
            f'<circle cx="{degree_x}" cy="83" r="3" fill="none" stroke="{WHITE}" stroke-width="1"/>',
            text(f_x, 101, "F", 14, "middle", WHITE, "800"),
        ])
    if len(value_s) >= 3:
        return "".join([
            text(55, 138, value_s, 32, "start", WHITE, "900"),
            f'<circle cx="119" cy="123" r="3" fill="none" stroke="{WHITE}" stroke-width="1"/>',
            text(125, 142, "F", 16, "start", WHITE, "800"),
        ])
    return "".join([
        text(57, 136, value_s, 40, "start", WHITE, "900"),
        f'<circle cx="118" cy="119" r="3" fill="none" stroke="{WHITE}" stroke-width="1"/>',
        text(124, 140, "F", 16, "start", WHITE, "800"),
    ])


def _metric''',
    s,
    flags=re.S,
)

# Match the production 7C GFX group calculation around centerX=320.
s = re.sub(
    r'def _apparent_parts_7c\(value\):\n.*?\n\ndef waveshare_7c_svg',
    '''def _apparent_parts_7c(value):
    value_s = str(value)
    text_size = 8 if len(value_s) >= 3 else 9
    number_font = text_size * 8
    number_w = len(value_s) * 6 * text_size
    group_w = number_w + 18 + 24
    start_x = 320 - group_w / 2
    degree_x = start_x + number_w + 7
    f_x = start_x + number_w + 16
    return "".join([
        text(start_x, 143 + number_font / 2, value_s, number_font, "start", WHITE, "900"),
        f'<circle cx="{degree_x}" cy="150" r="4" fill="none" stroke="{WHITE}" stroke-width="1.5"/>',
        text(f_x, 179, "F", 32, "start", WHITE, "800"),
    ])


def waveshare_7c_svg''',
    s,
    flags=re.S,
)

# Solid black display background, as in firmware fillScreen(C_BLACK).
s = s.replace('<rect width="170" height="320" fill="url(#bg)"/>', '<rect width="170" height="320" fill="#000000"/>')
s = s.replace('<rect width="240" height="320" fill="url(#bg)"/>', '<rect width="240" height="320" fill="#000000"/>')

# T-Display header: station sizing/truncation and current date at upper right.
s = s.replace(
    'station = (cfg.station_name or "Weather Station")[:18]',
    'station = cfg.station_name or "Weather Station"\n    if len(station) > 14:\n        station = station[:14]\n    station_size = 14 if len(station) <= 7 else 9',
)
s = s.replace(
    'text(8, 18, station, 14, "start", WHITE, "900"),',
    'text(8, 18, station, station_size, "start", WHITE, "900"),',
)
marker = '''    ]

    if not wx.valid:
        out += [
            card(8, 48, 154, 95, 11, True),'''
repl = '''    ]
    date_s = datetime.now().strftime("%a, %b %d, %Y").replace(" 0", " ")
    out.append(text(162, 18, date_s, 4.6, "end", "#dbe7ee", "500"))

    if not wx.valid:
        out += [
            card(8, 48, 154, 95, 11, True),'''
if marker not in s:
    raise SystemExit('T-Display header marker not found')
s = s.replace(marker, repl, 1)

# Waveshare 2.8 header changed from WEATHER STATION to CURRENT CONDITIONS.
s = s.replace(
    'station = (cfg.station_name or "Weather Station")[:20]',
    'station = (cfg.station_name or "Weather Station")[:16]',
    1,
)
s = s.replace(
    'text(12, 38, "WEATHER STATION", 5.2, "start", "#9db8ca", "600", 1.55)',
    'text(12, 38, "CURRENT CONDITIONS", 5.2, "start", "#9db8ca", "800", 1.55)',
)

# Header dates use current local date like firmware currentDateText().
s = re.sub(
    r'if wx\.date_utc_ms:\n        dt = datetime\.fromtimestamp\(wx\.date_utc_ms / 1000\)\n        date_s = dt\.strftime\("%a, %b %d, %Y"\)\.replace\(" 0", " "\)\n        out\.append\(text\(229, 22, date_s, 6\.6, "end", "#dbe7ee", "500"\)\)',
    'date_s = datetime.now().strftime("%a, %b %d, %Y").replace(" 0", " ")\n    out.append(text(229, 22, date_s, 6.6, "end", "#dbe7ee", "500"))',
    s,
    count=1,
)
s = re.sub(
    r'if wx\.date_utc_ms:\n        dt = datetime\.fromtimestamp\(wx\.date_utc_ms / 1000\)\n        date_s = dt\.strftime\("%a, %b %d, %Y"\)\.replace\(" 0", " "\)\n        out\.append\(text\(770, 35, date_s, 16, "end", "#dbe7ee", "500"\)\)',
    'date_s = datetime.now().strftime("%a, %b %d, %Y").replace(" 0", " ")\n    out.append(text(770, 35, date_s, 16, "end", "#dbe7ee", "500"))',
    s,
    count=1,
)

# Production hero icons and risk pills.
s = s.replace('icon(risk["icon"], 17, 70, 1.72),', '_hero_icon("tdisplay", wind_chill_applies(wx)),')
s = s.replace('icon(risk["icon"], 22, 73, 1.82),', '_hero_icon("waveshare", wind_chill_applies(wx)),')
s = s.replace(
    'icon(risk["icon"], 60 if not cold else 62, 110 if not cold else 135, 5.0 if not cold else 4.1),',
    '_hero_icon("7c", cold),',
)
s = s.replace('fill="url(#riskCurrent)"', 'fill="{risk["status"]}"')
s = s.replace('            icon("alert", 30, 119, .55),\n', '')
s = s.replace(
    '            text(90, 126, apparent_risk_label(wx), 6.8, "middle", risk["accent"], "900"),',
    '            text(85, 126, apparent_risk_label(wx), 6.8, "middle", risk["accent"], "900"),',
)
s = s.replace('            icon("alert", 31, 174, .65),\n', '')
s = s.replace(
    '            text(85, 182, apparent_risk_label(wx), 7.2, "middle", risk["accent"], "900"),',
    '            text(74, 182, apparent_risk_label(wx), 7.2, "middle", risk["accent"], "900"),',
)

# Footer clock geometry and no decorative status-dot glow.
s = s.replace('icon("clock", 12, 294, .65),', '_clock_icon(18, 304, 6),')
s = s.replace('icon("clock", 17, 280, .78),', '_clock_icon(24, 290, 7),')
s = s.replace('icon("clock", 55, 424, 1.2),', '_clock_icon(67, 436, 12),')
s = s.replace(' fill="{rc}" filter="url(#softGlow)"/>', ' fill="{rc}"/>')
s = s.replace('<g filter="url(#sunGlow)">', '<g>')

p.write_text(s)

# Update display tests for current production coordinates and wording.
t = Path('emulator/concept-1/tests/test_display_concept1.py')
ts = t.read_text()
ts = ts.replace('"WEATHER STATION", ">TEMP</text>', '"CURRENT CONDITIONS", ">TEMP</text>')
ts = re.sub(
    r'    def test_waveshare_100_does_not_use_old_overlapping_group\(self\):.*?\n    def test_tdisplay_100_keeps_unit_inside_panel',
    '''    def test_waveshare_100_matches_firmware_group(self):
        self.set_100_heat_index()
        svg = waveshare_svg(self.app.config, self.app.wx, forecast_elapsed_seconds=0)
        self.assertIn('>100</text>', svg)
        self.assertIn('cx="119" cy="123" r="3"', svg)
        self.assertIn('x="125" y="142"', svg)
        self.assertNotIn('M10 2L18 17H2z', svg)

    def test_tdisplay_100_keeps_unit_inside_panel''',
    ts,
    flags=re.S,
)
ts = re.sub(
    r'    def test_tdisplay_100_keeps_unit_inside_panel\(self\):.*?\n    def test_forecast_alternates',
    '''    def test_tdisplay_100_keeps_unit_inside_panel(self):
        self.set_100_heat_index()
        svg = tdisplay_svg(self.app.config, self.app.wx, forecast_elapsed_seconds=0)
        self.assertIn('x="98" y="98"', svg)
        self.assertIn('cx="133" cy="83" r="3"', svg)
        self.assertIn('x="145" y="101"', svg)
        self.assertNotIn('M10 2L18 17H2z', svg)

    def test_forecast_alternates''',
    ts,
    flags=re.S,
)
t.write_text(ts)

# Cross-check important current firmware display contracts in the test suite.
parity = Path('emulator/concept-1/tests/test_firmware_visual_parity.py')
parity.write_text('''import unittest
from pathlib import Path
from emulator.app_controller import EmulatorApp
from emulator.display_ui import tdisplay_svg, waveshare_svg, waveshare_7c_svg

ROOT = Path(__file__).resolve().parents[3]

class FirmwareVisualParityTests(unittest.TestCase):
    def setUp(self):
        self.app = EmulatorApp(verbose=False)
        self.app.apply_preset("heat")

    def test_risk_pills_have_no_legacy_warning_icon(self):
        for render in (tdisplay_svg, waveshare_svg, waveshare_7c_svg):
            svg = render(self.app.config, self.app.wx, forecast_elapsed_seconds=0)
            self.assertNotIn("M10 2L18 17H2z", svg)

    def test_current_conditions_headers_match_firmware(self):
        self.assertIn("CURRENT CONDITIONS", tdisplay_svg(self.app.config, self.app.wx, forecast_elapsed_seconds=0))
        self.assertIn("CURRENT CONDITIONS", waveshare_svg(self.app.config, self.app.wx, forecast_elapsed_seconds=0))
        self.assertIn("CURRENT CONDITIONS", waveshare_7c_svg(self.app.config, self.app.wx, forecast_elapsed_seconds=0))
        self.assertNotIn(">WEATHER STATION</text>", waveshare_svg(self.app.config, self.app.wx, forecast_elapsed_seconds=0))

    def test_production_card_and_pill_fills(self):
        for render in (tdisplay_svg, waveshare_svg, waveshare_7c_svg):
            svg = render(self.app.config, self.app.wx, forecast_elapsed_seconds=0)
            self.assertIn("#041622", svg)
            self.assertIn("#071d2c", svg)
            self.assertIn('x2="0" y2="1"', svg)
            self.assertNotIn('fill="url(#riskCurrent)"', svg)

    def test_firmware_sources_contain_current_pill_contract(self):
        targets = [
            ROOT / "T-Display-S3/src/display_ui.cpp",
            ROOT / "Waveshare-ESP32-S3-Touch-LCD-2.8/src/display_ui.cpp",
            ROOT / "Waveshare-ESP32-S3-Touch-LCD-7C-BOX/src/display_ui.cpp",
        ]
        for path in targets:
            src = path.read_text()
            self.assertIn("apparentRiskLabel()", src)
            self.assertNotIn("ICON_ALERT", src)
        self.assertIn('"CURRENT CONDITIONS"', targets[1].read_text())

if __name__ == "__main__":
    unittest.main()
''')

# Regenerate representative static previews from the synchronized renderers.
import sys
sys.path.insert(0, str(Path('emulator/concept-1').resolve()))
from emulator.app_controller import EmulatorApp
from emulator.display_ui import tdisplay_svg, waveshare_svg, waveshare_7c_svg
from emulator.weather_math import recompute

app = EmulatorApp(verbose=False)
app.apply_preset('heat')
cfg, wx = app.config, app.wx
previews = {
    'preview_tdisplay.svg': tdisplay_svg(cfg, wx, forecast_elapsed_seconds=0),
    'preview_tdisplay_concept1.svg': tdisplay_svg(cfg, wx, forecast_elapsed_seconds=0),
    'preview_tdisplay_today.svg': tdisplay_svg(cfg, wx, forecast_elapsed_seconds=0),
    'preview_tdisplay_tomorrow.svg': tdisplay_svg(cfg, wx, forecast_elapsed_seconds=30),
    'preview_waveshare.svg': waveshare_svg(cfg, wx, forecast_elapsed_seconds=0),
    'preview_waveshare_concept1.svg': waveshare_svg(cfg, wx, forecast_elapsed_seconds=0),
    'preview_waveshare_today.svg': waveshare_svg(cfg, wx, forecast_elapsed_seconds=0),
    'preview_waveshare_tomorrow.svg': waveshare_svg(cfg, wx, forecast_elapsed_seconds=30),
    'preview_waveshare_concept1_tomorrow.svg': waveshare_svg(cfg, wx, forecast_elapsed_seconds=30),
    'preview_waveshare_7c_box.svg': waveshare_7c_svg(cfg, wx, forecast_elapsed_seconds=0),
}
for name, data in previews.items():
    Path('emulator/concept-1', name).write_text(data)

app.wx.temp_f = 88.2
app.wx.humidity = 68.0
app.wx.wind_mph = 0.0
recompute(app.wx)
Path('emulator/concept-1/preview_waveshare_100F_alignment.svg').write_text(
    waveshare_svg(app.config, app.wx, forecast_elapsed_seconds=0)
)
Path('emulator/concept-1/emulator_config.json').unlink(missing_ok=True)

# Refresh functional-file hashes and pin firmware sources that define parity.
manifest_path = Path('.github/concept1-emulator-v7.11.10-manifest.json')
manifest = json.loads(manifest_path.read_text())
root = Path('emulator/concept-1')
files = {}
for f in root.rglob('*'):
    if f.is_file() and '__pycache__' not in f.parts and f.suffix != '.pyc':
        files[f.relative_to(root).as_posix()] = hashlib.sha256(f.read_bytes()).hexdigest()
manifest['archive'] = 'Concept-1 emulator synchronized to production firmware'
manifest['documentation'] = 'Repository emulator is the source of truth; hashes include current production-firmware parity updates.'
manifest['file_count'] = len(files)
manifest['files'] = dict(sorted(files.items()))
firmware_paths = [
    'T-Display-S3/src/display_ui.cpp',
    'T-Display-S3/src/weather_math.cpp',
    'T-Display-S3/src/ambient_weather.cpp',
    'T-Display-S3/src/wunderground_weather.cpp',
    'T-Display-S3/src/forecast_weather.cpp',
    'T-Display-S3/include/config.h',
    'Waveshare-ESP32-S3-Touch-LCD-2.8/src/display_ui.cpp',
    'Waveshare-ESP32-S3-Touch-LCD-7C-BOX/src/display_ui.cpp',
]
manifest['firmware_sources'] = {
    x: hashlib.sha256(Path(x).read_bytes()).hexdigest() for x in firmware_paths
}
manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + '\n')

print('Concept-1 emulator renderers patched to current firmware contract.')
