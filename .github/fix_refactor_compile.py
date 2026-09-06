from pathlib import Path

for project in [
    'T-Display-S3',
    'Waveshare-ESP32-S3-Touch-LCD-2.8',
]:
    path = Path(project) / 'src' / 'ambient_weather.cpp'
    text = path.read_text(encoding='utf-8')

    declaration = 'static void respectAmbientRateLimit();\n\n'
    marker = '#include "config.h"\n\n'
    if declaration not in text:
        if marker not in text:
            raise RuntimeError(f'include marker not found in {path}')
        text = text.replace(marker, marker + declaration, 1)

    text = text.replace(
        'bool pollAmbient(bool forceRedraw = true) {',
        'bool pollAmbient(bool forceRedraw) {',
        1,
    )

    if 'static void respectAmbientRateLimit();' not in text:
        raise RuntimeError(f'rate-limit declaration missing in {path}')
    if 'bool pollAmbient(bool forceRedraw = true) {' in text:
        raise RuntimeError(f'duplicate default argument remains in {path}')

    path.write_text(text, encoding='utf-8')

print('Applied ambient_weather cross-translation-unit compile fixes')
