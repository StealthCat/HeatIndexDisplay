# Production Release V7.8.1 — Live Provider Summary Fix

V7.8.1 ports the emulator live-summary fixes back to both production ESP32 targets.

- Weather Underground uses `/v2/pws/observations/hourly/7day` as the primary live REST source for Today High/Low and the observation nearest the same provider-local time yesterday.
- Weather Underground uses `obsTimeLocal` from the provider response rather than assuming the configured/device timezone matches the PWS station timezone.
- `/v2/pws/observations/all/1day` is the current-day fallback before archived `/history/daily` and `/history/all` data.
- The current observation is included in today's extrema so the newest provider sample is represented before it rolls into an hourly/history aggregate.
- Ambient Weather retains `/v1/devices/{MAC}` as its provider-history source and widens the same-time-yesterday search window to 30 minutes beyond the target with 24 returned records, selecting the nearest stored observation.
- A successful Today High/Low refresh is committed before a separate yesterday lookup can fail, preserving useful provider summary data.

Both production targets are built with PlatformIO before this release is committed.
