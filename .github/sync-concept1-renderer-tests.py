from pathlib import Path

p = Path('emulator/concept-1/tests/test_display_concept1_palettes.py')
s = p.read_text()
s = s.replace(
    "            self.assertIn('id=\"riskCurrent\"', svg)\n            self.assertIn('stop-color=\"#52120e\"', svg)\n",
    "            self.assertNotIn('id=\"riskCurrent\"', svg)\n            self.assertIn('fill=\"#52120e\"', svg)\n",
)
p.write_text(s)
