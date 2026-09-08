from __future__ import annotations
import json
from http.server import BaseHTTPRequestHandler
from urllib.parse import urlparse

HTML = r'''<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>HeatIndexDisplay V7.11.9 Concept 1 Emulator</title>
<style>
:root{color-scheme:dark;--bg:#07131d;--panel:#0b1f2c;--panel2:#0d2838;--line:#17445d;--cyan:#41cdff;--text:#edf8ff;--muted:#9cb3c2}
*{box-sizing:border-box}body{margin:0;font:14px system-ui,Segoe UI,Arial;background:linear-gradient(180deg,#061019,#0a1b27);color:var(--text)}
header{padding:18px 24px;border-bottom:1px solid var(--line);background:#07131dee;position:sticky;top:0;z-index:5}
h1{font-size:20px;margin:0}header p{margin:4px 0 0;color:var(--muted)}
main{display:grid;grid-template-columns:minmax(470px,1fr) minmax(380px,520px);gap:18px;padding:18px;max-width:1500px;margin:auto}
section{background:var(--panel);border:1px solid var(--line);border-radius:12px;padding:16px}
.preview-grid{display:flex;gap:22px;align-items:flex-start;justify-content:center;flex-wrap:wrap}
.device{background:linear-gradient(145deg,#0b1116,#020508);border:1px solid #6e8291;border-radius:24px;padding:16px;box-shadow:0 18px 45px #000b,inset 0 0 0 3px #111b22}
.device h3{text-align:center;font-size:13px;margin:0 0 12px;color:#adc7da;letter-spacing:.25px;font-weight:700}
.device img{display:block;background:#000;border-radius:3px;box-shadow:0 0 0 1px #0a1117,0 0 28px #00121f66}
#tdisplay{width:255px;height:480px}#waveshare{width:360px;height:480px}
h2{font-size:14px;margin:0 0 12px;color:var(--cyan)}
.controls{display:grid;gap:14px}.group{background:var(--panel2);border:1px solid var(--line);border-radius:10px;padding:12px}
.grid{display:grid;grid-template-columns:1fr 1fr;gap:8px}.grid3{display:grid;grid-template-columns:1fr 1fr 1fr;gap:8px}
label{display:grid;gap:4px;color:var(--muted);font-size:12px}input,select{width:100%;background:#06141d;color:var(--text);border:1px solid #24516a;border-radius:7px;padding:8px}
button{background:#12384b;color:#eafbff;border:1px solid #2c6c88;border-radius:8px;padding:8px 10px;cursor:pointer;font-weight:600}
button:hover{background:#18506b}.primary{background:#0c6688}
.buttons{display:flex;gap:7px;flex-wrap:wrap}.status{font-family:ui-monospace,Consolas,monospace;white-space:pre-wrap;color:#bdefff;font-size:12px;min-height:42px}
small{color:var(--muted)}@media(max-width:980px){main{grid-template-columns:1fr}.preview-grid{justify-content:flex-start}}
</style>
</head>
<body>
<header><h1>HeatIndexDisplay V7.11.9 Concept 1 Emulator</h1><p>V7.11.6: provider observations/history plus Open-Meteo forecast high/low, alternating Today/Tomorrow every 30 seconds.</p></header>
<main>
<section>
<h2>Live display previews</h2>
<div class="preview-grid">
  <div class="device"><h3>LILYGO T-Display S3 · 170×320</h3><img id="tdisplay" src="/render/tdisplay.svg"></div>
  <div class="device"><h3>Waveshare 2.8 · 240×320</h3><img id="waveshare" src="/render/waveshare.svg"></div>
</div>
</section>
<section class="controls">
<div class="group"><h2>Data mode</h2>
<div class="grid">
<label>Display data source<select id="data_mode" onchange="switchDataMode()"><option value="preset">Preset / Test Data</option><option value="live">Live Weather Data</option></select></label>
<label>Preset<select id="preset_name" onchange="switchPreset()"><option value="heat">Heat Index</option><option value="wind">Wind Chill</option><option value="normal">Normal</option><option value="stale">Stale</option><option value="waiting">Waiting</option><option value="manual" disabled>Manual values</option></select></label>
</div>
<div class="buttons" style="margin-top:10px">
<button onclick="preset('heat')">Heat Index</button><button onclick="preset('wind')">Wind Chill</button>
<button onclick="preset('normal')">Normal</button><button onclick="preset('stale')">Stale</button><button onclick="preset('waiting')">Waiting</button>
</div>
<small><b>Preset / Test Data</b> never contacts a weather provider. <b>Live Weather Data</b> polls the selected provider automatically at the configured interval.</small>
</div>
<div class="group"><h2>Manual weather values</h2>
<div class="grid3">
<label>Temperature °F<input id="temp_f" type="number" step="0.1"></label><label>Humidity %<input id="humidity" type="number" step="0.1"></label>
<label>Dew point °F<input id="dew_point_f" type="number" step="0.1"></label><label>Wind mph<input id="wind_mph" type="number" step="0.1"></label>
<label>Gust mph<input id="gust_mph" type="number" step="0.1"></label><label>Direction °<input id="wind_dir_deg" type="number" step="1"></label>
<label>From yesterday °F<input id="from_yesterday_f" type="number" step="0.1"></label><label>Observed today high °F<input id="today_high_f" type="number" step="0.1"></label>
<label>Observed today low °F<input id="today_low_f" type="number" step="0.1"></label>
<label>Forecast today high °F<input id="forecast_today_high_f" type="number" step="0.1"></label>
<label>Forecast today low °F<input id="forecast_today_low_f" type="number" step="0.1"></label>
<label>Forecast tomorrow high °F<input id="forecast_tomorrow_high_f" type="number" step="0.1"></label>
<label>Forecast tomorrow low °F<input id="forecast_tomorrow_low_f" type="number" step="0.1"></label>
</div><div class="buttons" style="margin-top:10px"><button class="primary" onclick="applyManual()">Apply manual values</button></div></div>
<div class="group"><h2>Live provider configuration</h2>
<div class="grid">
<label>Station name<input id="station_name"></label><label>Weather source<select id="weather_source"><option value="ambient">Ambient Weather</option><option value="wunderground">Weather Underground</option></select></label>
<label>Ambient Application Key<input id="ambient_application_key" type="password" placeholder="blank keeps saved value"></label>
<label>Ambient API Key<input id="ambient_api_key" type="password" placeholder="blank keeps saved value"></label>
<label>Ambient station MAC<input id="ambient_mac_address"></label><label>WU PWS Station ID<input id="wu_station_id"></label>
<label>WU API Key<input id="wu_api_key" type="password" placeholder="blank keeps saved value"></label>
<label>Poll seconds<input id="poll_seconds" type="number" min="15"></label><label>Stale seconds<input id="stale_seconds" type="number" min="30"></label>

</div><div class="buttons" style="margin-top:10px"><button onclick="saveConfig()">Save configuration</button><button class="primary" onclick="pollProvider()">Use Live Data + Poll Now</button></div>
<small>Secrets are stored only in local <code>emulator_config.json</code> and are not echoed back into this page.</small></div>
<div class="group"><h2>Live provider / forecast status</h2><small>From Yesterday and observed summary values come from the configured weather provider. The display High/Low card comes from Open-Meteo using the station coordinates supplied by Ambient Weather or Weather Underground. The card automatically alternates Today's/Tomorrow every 30 seconds.</small><div id="status" class="status" style="margin-top:10px"></div></div>
</section>
</main>
<script>
const ids=['temp_f','humidity','dew_point_f','wind_mph','gust_mph','wind_dir_deg','from_yesterday_f','today_high_f','today_low_f','forecast_today_high_f','forecast_today_low_f','forecast_tomorrow_high_f','forecast_tomorrow_low_f'];
async function jfetch(url,opts){const r=await fetch(url,opts);const j=await r.json();if(!r.ok)throw new Error(j.error||r.statusText);return j}
function refreshImages(){const t=Date.now();tdisplay.src='/render/tdisplay.svg?t='+t;waveshare.src='/render/waveshare.svg?t='+t}
async function refresh(){try{const s=await jfetch('/api/state');for(const id of ids){const v=s.weather[id];if(v!==null&&document.activeElement.id!==id)document.getElementById(id).value=v}status.textContent=JSON.stringify(s.status,null,2);refreshImages()}catch(e){status.textContent=e.message}}
async function loadConfig(){const c=await jfetch('/api/config');for(const k of ['station_name','weather_source','ambient_mac_address','wu_station_id','poll_seconds','stale_seconds','data_mode','preset_name'])if(document.getElementById(k))document.getElementById(k).value=c[k]??'';updateModeUi()}
async function applyManual(){const p={};for(const id of ids){const v=document.getElementById(id).value;p[id]=v===''?null:Number(v)}await jfetch('/api/manual',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(p)});data_mode.value='preset';preset_name.value='manual';updateModeUi();await refresh()}
async function preset(name){await jfetch('/api/preset',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({name})});data_mode.value='preset';preset_name.value=name;updateModeUi();await refresh()}
function updateModeUi(){const live=data_mode.value==='live';preset_name.disabled=live;for(const id of ids)document.getElementById(id).disabled=live}
async function switchPreset(){if(data_mode.value!=='preset')return;await preset(preset_name.value)}
async function switchDataMode(){const mode=data_mode.value;try{await jfetch('/api/mode',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({mode:mode,preset_name:preset_name.value})});await loadConfig();await refresh()}catch(e){status.textContent=e.message;await loadConfig();await refresh()}}
async function saveConfig(){const p={station_name:station_name.value,weather_source:weather_source.value,ambient_application_key:ambient_application_key.value,ambient_api_key:ambient_api_key.value,ambient_mac_address:ambient_mac_address.value,wu_api_key:wu_api_key.value,wu_station_id:wu_station_id.value,poll_seconds:Number(poll_seconds.value),stale_seconds:Number(stale_seconds.value),data_mode:data_mode.value,preset_name:preset_name.value};await jfetch('/api/config',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(p)});ambient_application_key.value='';ambient_api_key.value='';wu_api_key.value='';await loadConfig();await refresh()}
async function pollProvider(){data_mode.value='live';updateModeUi();try{await jfetch('/api/poll',{method:'POST'});await loadConfig();await refresh()}catch(e){status.textContent=e.message;await loadConfig();await refresh()}}
loadConfig().then(refresh);setInterval(refresh,1500);
</script></body></html>'''

def handler_factory(app):
    class Handler(BaseHTTPRequestHandler):
        server_version = "HeatIndexDisplayEmulator/7.11.6"

        def log_message(self, fmt, *args):
            if app.verbose:
                super().log_message(fmt, *args)

        def _send(self, data: bytes, content_type: str, status=200):
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(data)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(data)

        def _json(self, obj, status=200):
            self._send(json.dumps(obj).encode("utf-8"), "application/json; charset=utf-8", status)

        def _body_json(self):
            length = int(self.headers.get("Content-Length", "0"))
            raw = self.rfile.read(length) if length else b"{}"
            return json.loads(raw.decode("utf-8") or "{}")

        def do_GET(self):
            path = urlparse(self.path).path
            if path == "/":
                return self._send(HTML.encode("utf-8"), "text/html; charset=utf-8")
            if path == "/api/state":
                return self._json(app.state_payload())
            if path == "/api/config":
                return self._json(app.config.public_dict())
            if path == "/api/status":
                return self._json(app.status_payload())
            if path == "/render/tdisplay.svg":
                return self._send(app.render_tdisplay().encode("utf-8"), "image/svg+xml; charset=utf-8")
            if path == "/render/waveshare.svg":
                return self._send(app.render_waveshare().encode("utf-8"), "image/svg+xml; charset=utf-8")
            return self._json({"error": "not found"}, 404)

        def do_POST(self):
            path = urlparse(self.path).path
            try:
                if path == "/api/manual":
                    app.apply_manual(self._body_json())
                    return self._json(app.state_payload())
                if path == "/api/preset":
                    app.apply_preset(str(self._body_json().get("name", "")))
                    return self._json(app.state_payload())
                if path == "/api/mode":
                    body = self._body_json()
                    app.set_data_mode(
                        str(body.get("mode", "preset")),
                        str(body.get("preset_name", "heat")),
                        poll_now=True
                    )
                    return self._json(app.state_payload())
                if path == "/api/config":
                    app.apply_config(self._body_json())
                    return self._json(app.config.public_dict())
                if path == "/api/poll":
                    app.poll_provider()
                    return self._json(app.state_payload())
                return self._json({"error": "not found"}, 404)
            except Exception as exc:
                return self._json({"error": str(exc)}, 500)
    return Handler
