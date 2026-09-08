# Emulator V7.8.1 — Live Provider Summary Fix

This release fixes live Today High/Low and From Yesterday values.

Weather Underground now uses the recent 7-day hourly PWS REST endpoint as the
primary source because it reliably covers both the current day and the same
time yesterday. Recent 1-day and archived history endpoints remain fallbacks.

Ambient Weather now preserves the MAC address delimiters in the history path
and searches a wider provider-history window around the same local time
yesterday.

The emulator exposes the exact summary REST source and resulting values in the
Status panel to make live API problems immediately visible.
