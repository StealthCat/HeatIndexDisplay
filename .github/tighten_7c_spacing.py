from pathlib import Path
import hashlib
import json

fw = Path('Waveshare-ESP32-S3-Touch-LCD-7C-BOX/src/display_ui.cpp')
src = fw.read_text(encoding='utf-8')
old = '''  const int groupW = (int)numberW + 18 + (int)fW;
  const int startX = centerX - groupW / 2;
  printBoldAt(startX, topY, value, C_WHITE, numberSize);
  const int unitX = startX + (int)numberW + 4;
  gfx->drawCircle(unitX + 3, topY + 7, 4, C_WHITE);
  printBoldAt(unitX + 12, topY + 20, "F", C_WHITE, unitSize);'''
new = '''  // Arduino_GFX text bounds include the final character-cell spacing. Pull the
  // degree/F unit into that trailing space so the temperature reads as one
  // compact value instead of leaving a large visual gap after the digits.
  const int groupW = (int)numberW + 10 + (int)fW;
  const int startX = centerX - groupW / 2;
  printBoldAt(startX, topY, value, C_WHITE, numberSize);
  const int unitX = startX + (int)numberW - 4;
  gfx->drawCircle(unitX + 3, topY + 7, 4, C_WHITE);
  printBoldAt(unitX + 12, topY + 20, "F", C_WHITE, unitSize);'''
if old not in src:
    raise SystemExit('Expected 7C apparent-temperature spacing block not found')
fw.write_text(src.replace(old, new, 1), encoding='utf-8')

emu = Path('emulator/concept-1/emulator/display_ui.py')
esrc = emu.read_text(encoding='utf-8')
old_e = '''    group_w = number_w + 18 + 24
    start_x = 320 - group_w / 2
    degree_x = start_x + number_w + 7
    f_x = start_x + number_w + 16'''
new_e = '''    # Match the production display: use the trailing character-cell spacing
    # after the final digit to tuck the degree/F unit closer to the number.
    group_w = number_w + 10 + 24
    start_x = 320 - group_w / 2
    degree_x = start_x + number_w - 1
    f_x = start_x + number_w + 8'''
if old_e not in esrc:
    raise SystemExit('Expected emulator 7C spacing block not found')
emu.write_text(esrc.replace(old_e, new_e, 1), encoding='utf-8')

test = Path('emulator/concept-1/tests/test_waveshare_7c_box.py')
tsrc = test.read_text(encoding='utf-8')
marker = '''    def test_controller_exposes_renderer(self):
        svg = self.app.render_waveshare_7c()
        self.assertIn('viewBox="0 0 800 480"', svg)
'''
addition = '''    def test_apparent_temperature_unit_spacing_matches_firmware(self):
        from emulator.display_ui import _apparent_parts_7c
        svg = _apparent_parts_7c(100)
        self.assertIn('x="231.0"', svg)
        self.assertIn('cx="374.0" cy="150" r="4"', svg)
        self.assertIn('x="383.0" y="179"', svg)

'''
if 'test_apparent_temperature_unit_spacing_matches_firmware' not in tsrc:
    if marker not in tsrc:
        raise SystemExit('Expected 7C test insertion marker not found')
    test.write_text(tsrc.replace(marker, addition + marker, 1), encoding='utf-8')

manifest_path = Path('.github/concept1-emulator-v7.11.10-manifest.json')
manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
for rel in ['emulator/display_ui.py', 'tests/test_waveshare_7c_box.py']:
    p = Path('emulator/concept-1') / rel
    manifest['files'][rel] = hashlib.sha256(p.read_bytes()).hexdigest()
manifest['firmware_sources'][fw.as_posix()] = hashlib.sha256(fw.read_bytes()).hexdigest()
manifest['file_count'] = len(manifest['files'])
manifest_path.write_text(json.dumps(manifest, indent=2) + '\n', encoding='utf-8')
