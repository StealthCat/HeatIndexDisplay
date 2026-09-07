# Production Release V7.8 — Provider REST Summary Data

V7.8 makes the display summary fields explicitly source-aware and REST-derived.

## Ambient Weather

- Current conditions continue to come from `/v1/devices`.
- Today High/Low come from `/v1/devices/{macAddress}` with an explicit `endDate` at the current observation and `limit=288`.
- From Yesterday is fetched with a second `/v1/devices/{macAddress}` REST request ending at the same local clock time on the prior calendar day.
- Requests retain the existing Ambient 1 request/second spacing.

## Weather Underground

- Current conditions continue to come from `/v2/pws/observations/current`.
- Today High/Low prefer `/v2/pws/history/daily` for the current local date.
- If the current-day daily summary is unavailable, firmware falls back to `/v2/pws/history/all`.
- From Yesterday uses `/v2/pws/history/all` for the prior local date and selects the observation nearest the same local clock time.

## Reliability

- Local-calendar arithmetic is used for yesterday so DST transitions do not shift the comparison by an hour.
- A failure of the separate yesterday REST request does not discard a successfully refreshed Today High/Low summary. Previously successful From Yesterday data is retained until the provider returns a new value.
- The configured weather source remains the dispatcher for both current and historical REST requests.
