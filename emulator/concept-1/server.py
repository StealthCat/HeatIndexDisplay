#!/usr/bin/env python3
"""Concept-1 emulator local server. Standard-library only; credentials remain in memory."""
from __future__ import annotations
import json, math, os, threading, time
from datetime import datetime, timedelta
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError
from zoneinfo import ZoneInfo

HERE = Path(__file__).resolve().parent
AMBIENT_DEVICES_URL = "https://rt.ambientweather.net/v1/devices"
WU_CURRENT_URL = "https://api.weather.com/v2/pws/observations/current"
WU_RECENT_1DAY_URL = "https://api.weather.com/v2/pws/observations/all/1day"
WU_RECENT_7DAY_HOURLY_URL = "https://api.weather.com/v2/pws/observations/hourly/7day"
WU_HISTORY_URL = "https://api.weather.com/v2/pws/history/all"
WU_DAILY_HISTORY_URL = "https://api.weather.com/v2/pws/history/daily"
OPEN_METEO_FORECAST_URL = "https://api.open-meteo.com/v1/forecast"
SUMMARY_REFRESH_SECONDS = 300
FORECAST_REFRESH_SECONDS = 900
STALE_SECONDS = 180
USER_AGENT = "WS5000-ApparentTemp-Emulator/7.9-concept1"

CONFIG = {
    "provider": "ambient",
    "timezone": "America/New_York",
    "ambient": {"apiKey": "", "applicationKey": "", "macAddress": ""},
    "wunderground": {"apiKey": "", "stationId": ""},
}
STATE = {"summary": {}, "summary_at": 0.0, "forecast": {}, "forecast_at": 0.0, "coords": None}
LOCK = threading.Lock()
LAST_REQUEST = {"ambient": 0.0, "wunderground": 0.0}

def finite(v):
    try: return math.isfinite(float(v))
    except (TypeError, ValueError): return False

def f(v):
    return float(v) if finite(v) else None

def norm_mac(s): return "".join(c for c in str(s or "").upper() if c in "0123456789ABCDEF")

def request_json(url, provider=None, timeout=15):
    if provider:
        wait = 1.1 - (time.monotonic() - LAST_REQUEST[provider])
        if wait > 0: time.sleep(wait)
    req = Request(url, headers={"User-Agent": USER_AGENT, "Accept": "application/json"})
    try:
        with urlopen(req, timeout=timeout) as r:
            raw = r.read()
        if provider: LAST_REQUEST[provider] = time.monotonic()
        return json.loads(raw)
    except HTTPError as e:
        if provider: LAST_REQUEST[provider] = time.monotonic()
        body = e.read(160).decode("utf-8", "replace")
        raise RuntimeError(f"HTTP {e.code}: {body}") from e
    except (URLError, TimeoutError, json.JSONDecodeError) as e:
        raise RuntimeError(str(e)) from e

def local_dt(epoch_ms, tzname):
    return datetime.fromtimestamp(epoch_ms / 1000, ZoneInfo(tzname))

def ambient_current(cfg):
    a = cfg["ambient"]
    if not a["apiKey"] or not a["applicationKey"]:
        raise RuntimeError("Ambient API Key and Application Key are required")
    url = AMBIENT_DEVICES_URL + "?" + urlencode({"apiKey": a["apiKey"], "applicationKey": a["applicationKey"]})
    devices = request_json(url, "ambient")
    if not isinstance(devices, list) or not devices: raise RuntimeError("Ambient returned no devices")
    wanted = norm_mac(a.get("macAddress"))
    selected = next((d for d in devices if norm_mac(d.get("macAddress")) == wanted), None) if wanted else devices[0]
    if not selected: raise RuntimeError("Configured Ambient station MAC was not found")
    last = selected.get("lastData") or {}
    temp, rh = f(last.get("tempf")), f(last.get("humidity"))
    if temp is None or rh is None or not 0 <= rh <= 100: raise RuntimeError("Ambient returned invalid tempf/humidity")
    info = selected.get("info") or {}
    coords = ((info.get("coords") or {}).get("coords") or {})
    lat, lon = f(coords.get("lat")), f(coords.get("lon"))
    if lat is None or lon is None:
        geo = ((info.get("coords") or {}).get("geo") or {}).get("coordinates") or []
        if len(geo) >= 2: lon, lat = f(geo[0]), f(geo[1])
    return {
        "provider":"ambient","providerLabel":"Ambient Weather","station":info.get("name") or selected.get("macAddress") or "Ambient Weather",
        "tempF":temp,"humidity":rh,"windMph":f(last.get("windspeedmph")),
        "gustMph":f(last.get("windgustmph") if last.get("windgustmph") is not None else last.get("gustmph")),
        "maxDailyGustMph":f(last.get("maxdailygust")),"windDirDeg":f(last.get("winddir")),
        "latitude":lat,"longitude":lon,"observationMs":int(last.get("dateutc") or 0),
    }

def ambient_history(cfg, end_ms, limit):
    a=cfg["ambient"]; mac=a.get("macAddress")
    if not mac: raise RuntimeError("Ambient MAC Address is required for history")
    q={"apiKey":a["apiKey"],"applicationKey":a["applicationKey"],"endDate":str(int(end_ms)),"limit":str(limit)}
    data=request_json(f"{AMBIENT_DEVICES_URL}/{mac}?{urlencode(q)}","ambient")
    if not isinstance(data,list) or not data: raise RuntimeError("Ambient REST history returned no observations")
    return data

def ambient_summary(cfg, current):
    tzname=cfg["timezone"]; obs_ms=current["observationMs"]
    if not obs_ms: raise RuntimeError("Ambient current observation has no dateutc")
    today=local_dt(obs_ms,tzname).date()
    points=ambient_history(cfg,obs_ms,288)
    temps=[float(p["tempf"]) for p in points if finite(p.get("tempf")) and p.get("dateutc") and local_dt(int(p["dateutc"]),tzname).date()==today]
    if not temps: raise RuntimeError("Ambient history did not contain today's temperatures")
    result={"providerTodayHighF":max(temps),"providerTodayLowF":min(temps)}
    target_local=local_dt(obs_ms,tzname)-timedelta(days=1)
    target_ms=int(target_local.timestamp()*1000)
    yesterday_points=ambient_history(cfg,target_ms+1800000,24)
    candidates=[(abs(int(p.get("dateutc",0))-target_ms),float(p["tempf"])) for p in yesterday_points if p.get("dateutc") and finite(p.get("tempf"))]
    if not candidates: raise RuntimeError("Ambient history did not contain yesterday temperature")
    yesterday=min(candidates,key=lambda x:x[0])[1]
    result.update({"yesterdayTempF":yesterday,"fromYesterdayF":current["tempF"]-yesterday})
    return result

def wu_url(base,cfg,extra=None):
    w=cfg["wunderground"]
    if not w["apiKey"] or not w["stationId"]: raise RuntimeError("Weather Underground API Key and Station ID are required")
    q={"stationId":w["stationId"],"format":"json","units":"e","numericPrecision":"decimal","apiKey":w["apiKey"]}
    if extra:q.update(extra)
    return base+"?"+urlencode(q)

def wu_current(cfg):
    data=request_json(wu_url(WU_CURRENT_URL,cfg),"wunderground")
    obs=(data.get("observations") or [None])[0]
    if not obs: raise RuntimeError("Weather Underground returned no current observation")
    imp=obs.get("imperial") or {}; temp,rh=f(imp.get("temp")),f(obs.get("humidity"))
    if temp is None or rh is None or not 0<=rh<=100: raise RuntimeError("Weather Underground returned invalid temperature/humidity")
    epoch=int(obs.get("epoch") or 0)
    return {"provider":"wunderground","providerLabel":"Weather Underground",
      "station":obs.get("neighborhood") or obs.get("stationID") or cfg["wunderground"]["stationId"],
      "tempF":temp,"humidity":rh,"windMph":f(imp.get("windSpeed")),"gustMph":f(imp.get("windGust")),
      "maxDailyGustMph":f(imp.get("windGust")),"windDirDeg":f(obs.get("winddir")),
      "latitude":f(obs.get("lat")),"longitude":f(obs.get("lon")),"observationMs":epoch*1000,
      "obsTimeLocal":str(obs.get("obsTimeLocal") or "")}

def parse_provider_local(s):
    s=(s or "").strip()
    for candidate in (s[:19],s[:16]):
        try:return datetime.fromisoformat(candidate.replace(" ","T"))
        except ValueError: pass
    return None

def wu_recent(cfg,base):
    data=request_json(wu_url(base,cfg),"wunderground")
    obs=data.get("observations") or []
    if not obs: raise RuntimeError("Weather Underground recent history returned no observations")
    return obs

def wu_history_date(cfg,ymd,base=WU_HISTORY_URL):
    data=request_json(wu_url(base,cfg,{"date":ymd}),"wunderground")
    obs=data.get("observations") or []
    if not obs: raise RuntimeError(f"Weather Underground history returned no observations for {ymd}")
    return obs

def wu_point_values(p):
    imp=p.get("imperial") or {}
    hi,lo,avg,gust=f(imp.get("tempHigh")),f(imp.get("tempLow")),f(imp.get("tempAvg")),f(imp.get("windgustHigh"))
    if hi is None: hi=avg
    if lo is None: lo=avg
    return hi,lo,avg,gust

def wu_summarize_day(obs, ymd):
    highs=[]; lows=[]; gusts=[]
    for p in obs:
        dt=parse_provider_local(p.get("obsTimeLocal"))
        if not dt or dt.strftime("%Y%m%d")!=ymd: continue
        hi,lo,_,gust=wu_point_values(p)
        if hi is not None:highs.append(hi)
        if lo is not None:lows.append(lo)
        if gust is not None:gusts.append(gust)
    return (max(highs) if highs else None,min(lows) if lows else None,max(gusts) if gusts else None)

def wu_nearest_temp(obs,ymd,target_seconds):
    best=None
    for p in obs:
        dt=parse_provider_local(p.get("obsTimeLocal"))
        if not dt or dt.strftime("%Y%m%d")!=ymd:continue
        hi,lo,avg,_=wu_point_values(p)
        temp=avg if avg is not None else ((hi+lo)/2 if hi is not None and lo is not None else hi if hi is not None else lo)
        if temp is None:continue
        sec=dt.hour*3600+dt.minute*60+dt.second
        item=(abs(sec-target_seconds),temp)
        if best is None or item[0]<best[0]:best=item
    return best[1] if best else None

def wu_summary(cfg,current):
    local=parse_provider_local(current.get("obsTimeLocal"))
    if local is None: local=local_dt(current["observationMs"],cfg["timezone"]).replace(tzinfo=None)
    today=local.strftime("%Y%m%d"); yesterday=(local-timedelta(days=1)).strftime("%Y%m%d")
    target_seconds=local.hour*3600+local.minute*60+local.second
    recent_error=None; recent=[]
    try: recent=wu_recent(cfg,WU_RECENT_7DAY_HOURLY_URL)
    except Exception as e: recent_error=e
    hi,lo,gust=wu_summarize_day(recent,today) if recent else (None,None,None)
    ytemp=wu_nearest_temp(recent,yesterday,target_seconds) if recent else None
    if hi is None or lo is None:
        try:
            one=wu_recent(cfg,WU_RECENT_1DAY_URL); h2,l2,g2=wu_summarize_day(one,today)
            hi=hi if hi is not None else h2; lo=lo if lo is not None else l2
            if g2 is not None: gust=max(gust,g2) if gust is not None else g2
        except Exception: pass
    if hi is None or lo is None:
        try:
            daily=wu_history_date(cfg,today,WU_DAILY_HISTORY_URL); vals=[wu_point_values(p) for p in daily]
            hs=[v[0] for v in vals if v[0] is not None]; ls=[v[1] for v in vals if v[1] is not None]; gs=[v[3] for v in vals if v[3] is not None]
            if hs:hi=max(hs)
            if ls:lo=min(ls)
            if gs:gust=max(gs)
        except Exception: pass
    if hi is None or lo is None:
        archived=wu_history_date(cfg,today); vals=[wu_point_values(p) for p in archived]
        hs=[v[0] for v in vals if v[0] is not None];ls=[v[1] for v in vals if v[1] is not None];gs=[v[3] for v in vals if v[3] is not None]
        if hs:hi=max(hs)
        if ls:lo=min(ls)
        if gs:gust=max(gs)
    if hi is None or lo is None: raise RuntimeError(str(recent_error or "WU history did not contain today high/low"))
    if ytemp is None:
        yesterday_obs=wu_history_date(cfg,yesterday); ytemp=wu_nearest_temp(yesterday_obs,yesterday,target_seconds)
        if ytemp is None:
            target=(local_dt(current["observationMs"],cfg["timezone"])-timedelta(days=1)).timestamp()*1000
            candidates=[]
            for p in yesterday_obs:
                epoch=int(p.get("epoch") or 0); avg=wu_point_values(p)[2]
                if epoch and avg is not None:candidates.append((abs(epoch*1000-target),avg))
            if candidates:ytemp=min(candidates,key=lambda x:x[0])[1]
    if ytemp is None: raise RuntimeError("Weather Underground REST data did not contain yesterday temperature")
    return {"providerTodayHighF":hi,"providerTodayLowF":lo,"maxDailyGustMph":gust,
            "yesterdayTempF":ytemp,"fromYesterdayF":current["tempF"]-ytemp}

def forecast(current):
    lat,lon=current.get("latitude"),current.get("longitude")
    if lat is None or lon is None: raise RuntimeError("Weather station coordinates are not available")
    q={"latitude":f"{lat:.6f}","longitude":f"{lon:.6f}","daily":"temperature_2m_max,temperature_2m_min",
       "temperature_unit":"fahrenheit","timezone":"auto","forecast_days":"2"}
    data=request_json(OPEN_METEO_FORECAST_URL+"?"+urlencode(q)); daily=data.get("daily") or {}
    highs=daily.get("temperature_2m_max") or []; lows=daily.get("temperature_2m_min") or []
    if len(highs)<2 or len(lows)<2: raise RuntimeError("Forecast response did not contain today and tomorrow high/low")
    return {"forecastTodayHighF":float(highs[0]),"forecastTodayLowF":float(lows[0]),
            "forecastTomorrowHighF":float(highs[1]),"forecastTomorrowLowF":float(lows[1])}

def live_payload():
    with LOCK: cfg=json.loads(json.dumps(CONFIG))
    current=ambient_current(cfg) if cfg["provider"]=="ambient" else wu_current(cfg)
    now=time.monotonic(); summary_warning=None; forecast_warning=None
    with LOCK:
        summary=dict(STATE["summary"]); sat=STATE["summary_at"]; fc=dict(STATE["forecast"]); fat=STATE["forecast_at"]; oldcoords=STATE["coords"]
    if now-sat>=SUMMARY_REFRESH_SECONDS or not summary:
        try:
            fresh=ambient_summary(cfg,current) if cfg["provider"]=="ambient" else wu_summary(cfg,current)
            summary.update(fresh)
            with LOCK: STATE["summary"]=dict(summary);STATE["summary_at"]=now
        except Exception as e: summary_warning=str(e)
    coords=(current.get("latitude"),current.get("longitude"))
    if now-fat>=FORECAST_REFRESH_SECONDS or not fc or coords!=oldcoords:
        try:
            fc=forecast(current)
            with LOCK: STATE["forecast"]=dict(fc);STATE["forecast_at"]=now;STATE["coords"]=coords
        except Exception as e: forecast_warning=str(e)
    out={**current,**summary,**fc}
    if summary.get("maxDailyGustMph") is not None: out["maxDailyGustMph"]=summary["maxDailyGustMph"]
    out["summaryWarning"]=summary_warning;out["forecastWarning"]=forecast_warning
    out["observationTime"]=datetime.fromtimestamp(current["observationMs"]/1000).astimezone().isoformat() if current.get("observationMs") else datetime.now().astimezone().isoformat()
    age=max(0,time.time()-current["observationMs"]/1000) if current.get("observationMs") else 0
    out["stale"]=age>STALE_SECONDS
    return out

class Handler(SimpleHTTPRequestHandler):
    def __init__(self,*args,**kwargs): super().__init__(*args,directory=str(HERE),**kwargs)
    def log_message(self,fmt,*args): print("[emulator]",fmt%args)
    def json_response(self,status,obj):
        body=json.dumps(obj,separators=(",",":")).encode(); self.send_response(status)
        self.send_header("Content-Type","application/json");self.send_header("Cache-Control","no-store");self.send_header("Content-Length",str(len(body)));self.end_headers();self.wfile.write(body)
    def do_GET(self):
        if self.path.split("?",1)[0]=="/api/live":
            try:self.json_response(200,live_payload())
            except Exception as e:self.json_response(502,{"error":str(e)})
            return
        return super().do_GET()
    def do_POST(self):
        if self.path!="/api/config":self.json_response(404,{"error":"Not found"});return
        try:
            n=int(self.headers.get("Content-Length","0")); incoming=json.loads(self.rfile.read(n) or b"{}")
            provider=incoming.get("provider")
            if provider not in ("ambient","wunderground"):raise ValueError("provider must be ambient or wunderground")
            tzname=incoming.get("timezone") or "America/New_York"; ZoneInfo(tzname)
            clean={"provider":provider,"timezone":tzname,
                   "ambient":{k:str((incoming.get("ambient") or {}).get(k,"")).strip() for k in ("apiKey","applicationKey","macAddress")},
                   "wunderground":{k:str((incoming.get("wunderground") or {}).get(k,"")).strip() for k in ("apiKey","stationId")}}
            with LOCK:
                CONFIG.clear();CONFIG.update(clean);STATE.update({"summary":{},"summary_at":0.0,"forecast":{},"forecast_at":0.0,"coords":None})
            self.json_response(200,{"ok":True,"provider":provider,"credentialsPersisted":False})
        except Exception as e:self.json_response(400,{"error":str(e)})

if __name__=="__main__":
    host=os.environ.get("EMULATOR_HOST","127.0.0.1"); port=int(os.environ.get("EMULATOR_PORT","8080"))
    print(f"Concept-1 emulator: http://{host}:{port}"); print("Live provider credentials are kept in memory only.")
    ThreadingHTTPServer((host,port),Handler).serve_forever()
