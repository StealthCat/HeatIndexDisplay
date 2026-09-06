# Production Release V7.5 — asset-based mockup icon match

This release replaces the earlier primitive-drawn weather icons with a fixed RGB565 asset set designed to visually match the approved mockup more closely.

Both boards now include `include/ui_assets.h` with 20x20 transparent RGB565 sprites for Wi-Fi, thermometer/temperature, water drop/humidity, leaf/dew point, trend/from yesterday, wind, compass/direction, and sun/today's high-low.

The rendering helpers now blit these assets directly to the display instead of constructing simplified icons from lines, circles, and triangles.

All V7.4 firmware behavior is retained, including compile-time first-boot defaults with persistent `/config` overrides, T-Display native LovyanGFX, Waveshare Arduino_GFX 1.6.0, Heat Index/Wind Chill switching, AmbientWeather current/history data, and performance optimizations.
