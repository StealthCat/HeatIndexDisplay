import fs from "node:fs";
import crypto from "node:crypto";
import path from "node:path";
import {fileURLToPath} from "node:url";
const here=path.dirname(fileURLToPath(import.meta.url)),root=path.resolve(here,"../..");
const manifest=JSON.parse(fs.readFileSync(path.join(here,"sync-manifest.json"),"utf8"));
const app=fs.readFileSync(path.join(here,"app.js"),"utf8"),css=fs.readFileSync(path.join(here,"styles.css"),"utf8"),html=fs.readFileSync(path.join(here,"index.html"),"utf8"),server=fs.readFileSync(path.join(here,"server.py"),"utf8");
function gitBlobSha(buffer){return crypto.createHash("sha1").update(Buffer.from(`blob ${buffer.length}\0`)).update(buffer).digest("hex");}
function fail(m){console.error(`SYNC FAIL: ${m}`);process.exitCode=1;}
function need(text,needle,label){if(!text.includes(needle))fail(`${label}: missing ${needle}`);}
if(process.env.SKIP_SOURCE_PIN!=="1")for(const source of manifest.productionSources){const p=path.join(root,source.path);if(!fs.existsSync(p)){fail(`missing production source ${source.path}`);continue;}const actual=gitBlobSha(fs.readFileSync(p));if(actual!==source.blobSha)fail(`${source.path} drifted: expected ${source.blobSha}, got ${actual}`);else console.log(`OK source ${source.path} ${actual}`);}
for(const [n,l] of [
 ["const DISPLAY_CONTRACT = \"concept-1-7c\"","contract"],["const FORECAST_SWITCH_MS = 30000","forecast rotation"],
 ["35.74+0.6215*tempF-35.75*v16+0.4275*tempF*v16","wind chill"],["if (averaged < 80) return averaged","simple heat index"],
 ["-42.379+2.04901523*T+10.14333127*R","Rothfusz"],["a=17.625, b=243.04","dew point"],
 ["if(value>=125)return \"EXTREME DANGER\"","heat risk"],["if(value<=-35)return \"EXTREME DANGER\"","cold risk"],
 ["Math.floor((n+11.25)/22.5)%16","direction"],["LIVE_POLL_MS = 60000","live polling"]])need(app,n,l);
for(const [n,l] of [["width:800px;height:480px","dimensions"],["left:33px;top:82px;width:427px;height:225px","hero"],["left:477px;width:290px;height:50px","metrics"],["top:316px;height:76px","bottom row"],["left:33px;top:410px;width:734px;height:52px","footer"]])need(css,n,l);
for(const n of ["Preset/Test Data","Live Weather Data","Ambient Weather","Weather Underground","ambientApiKey","wuStationId"])need(html,n,"live UI");
for(const [n,l] of [
 ["https://rt.ambientweather.net/v1/devices","Ambient endpoint"],["/v2/pws/observations/hourly/7day","WU hourly fallback"],
 ["/v2/pws/history/daily","WU daily fallback"],["/v2/pws/history/all","WU archive fallback"],
 ["https://api.open-meteo.com/v1/forecast","forecast endpoint"],["SUMMARY_REFRESH_SECONDS = 300","summary refresh"],
 ["FORECAST_REFRESH_SECONDS = 900","forecast refresh"],["target_local=local_dt(obs_ms,tzname)-timedelta(days=1)","DST-aware yesterday"],
 ["summary.update(fresh)","retain summary"],["fc=forecast(current)","forecast poll"]])need(server,n,l);
for(const rgb of ["178,21,133","216,59,53","221,117,29","197,155,23","40,122,69","108,58,168","37,105,184","78,166,218","18,79,134"])need(app,rgb,`palette ${rgb}`);
if(!process.exitCode)console.log(`SYNC OK: ${manifest.contract} emulator matches pinned production UI/math/provider/forecast contract.`);
