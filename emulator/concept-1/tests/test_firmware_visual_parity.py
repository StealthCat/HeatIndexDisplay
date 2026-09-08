import unittest
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

    def test_waiting_state_matches_firmware_contract(self):
        self.app.wx.valid = False
        renders = [
            (tdisplay_svg, 'x="8" y="43" width="154" height="244"'),
            (waveshare_svg, 'x="10" y="54" width="220" height="208"'),
            (waveshare_7c_svg, 'x="33" y="82" width="734" height="310"'),
        ]
        for render, geometry in renders:
            svg = render(self.app.config, self.app.wx, forecast_elapsed_seconds=0)
            self.assertIn('WAITING', svg)
            self.assertIn('Preparing display', svg)
            self.assertIn('Fetching weather...', svg)
            self.assertIn(geometry, svg)

            error_svg = render(self.app.config, self.app.wx, api_error='provider failed', forecast_elapsed_seconds=0)
            self.assertIn('Weather API error', error_svg)
            self.assertIn('Check provider configuration', error_svg)

    def test_footer_state_badge_spacing_matches_lilygo_reference(self):
        self.app.wx.valid = False
        renders = [
            tdisplay_svg(self.app.config, self.app.wx),
            waveshare_svg(self.app.config, self.app.wx),
            waveshare_7c_svg(self.app.config, self.app.wx),
        ]
        expected = [
            ('cx="130" cy="304" r="2.4"', 'x="136" y="304"', '>OFFLINE</text>'),
            ('cx="187" cy="290" r="3"', 'x="194" y="290"', '>OFFLINE</text>'),
            ('cx="664" cy="436" r="5"', 'x="677" y="436"', '>OFFLINE</text>'),
        ]
        for svg, parts in zip(renders, expected):
            for part in parts:
                self.assertIn(part, svg)

        sources = [
            (ROOT / "T-Display-S3/src/display_ui.cpp", 'fillCircle(130, 304, 2', 'drawBoldText(state, 136, 304'),
            (ROOT / "Waveshare-ESP32-S3-Touch-LCD-2.8/src/display_ui.cpp", 'fillCircle(172, 290, 3', 'printBoldAt(179, 286, state'),
            (ROOT / "Waveshare-ESP32-S3-Touch-LCD-7C-BOX/src/display_ui.cpp", 'fillCircle(649, 436, 5', 'printBoldAt(662, 427, state'),
        ]
        for path, dot, label in sources:
            src = path.read_text()
            self.assertIn(dot, src)
            self.assertIn(label, src)

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
            self.assertIn('"Preparing display"', src)
            self.assertIn('"Fetching weather..."', src)
        self.assertIn('"CURRENT CONDITIONS"', targets[1].read_text())
        self.assertIn("drawConceptCard(8, 43, 154, 244", targets[0].read_text())
        self.assertIn("drawConceptCard(10, 54, 220, 208", targets[1].read_text())
        self.assertIn("drawConceptCard(33, 82, 734, 310", targets[2].read_text())

if __name__ == "__main__":
    unittest.main()
