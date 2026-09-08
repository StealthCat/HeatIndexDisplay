import fs from "node:fs";
import crypto from "node:crypto";
import path from "node:path";
import {fileURLToPath} from "node:url";

const here=path.dirname(fileURLToPath(import.meta.url));
const root=path.resolve(here,"../..");
const manifest=JSON.parse(fs.readFileSync(path.join(here,"sync-manifest.json"),"utf8"));
const app=fs.readFileSync(path.join(here,"app.js"),"utf8");
const css=fs.readFileSync(path.join(here,"styles.css"),"utf8");
const html=fs.readFileSync(path.join(here,"index.html"),"utf8");

function gitBlobSha(buffer){
  const header=Buffer.from(`blob ${buffer.length}\0`);
  return crypto.createHash("sha1").update(header).update(buffer).digest("hex");
}
function fail(msg){console.error(`SYNC FAIL: ${msg}`);process.exitCode=1;}
function requireText(text,needle,label){if(!text.includes(needle))fail(`${label}: missing ${needle}`);}

if(process.env.SKIP_SOURCE_PIN!=="1"){
  for(const source of manifest.productionSources){
    const p=path.join(root,source.path);
    if(!fs.existsSync(p)){fail(`missing production source ${source.path}`);continue;}
    const actual=gitBlobSha(fs.readFileSync(p));
    if(actual!==source.blobSha) fail(`${source.path} drifted: expected ${source.blobSha}, got ${actual}`);
    else console.log(`OK source ${source.path} ${actual}`);
  }
} else {
  console.log("Source-pin check skipped by SKIP_SOURCE_PIN=1 (local emulator checks only).");
}

for(const [needle,label] of [
  ["const DISPLAY_CONTRACT = \"concept-1-7c\"","contract id"],
  ["const FORECAST_SWITCH_MS = 30000","forecast rotation"],
  ["35.74+0.6215*tempF-35.75*v16+0.4275*tempF*v16","wind chill formula"],
  ["if (averaged < 80) return averaged","simple heat index return"],
  ["-42.379+2.04901523*T+10.14333127*R","heat index regression"],
  ["const a=17.625,b=243.04","dew point constants"],
  ["if(value>=125)return \"EXTREME DANGER\"","heat risk threshold"],
  ["if(value<=-35)return \"EXTREME DANGER\"","cold risk threshold"],
  ["Math.floor((n+11.25)/22.5)%16","16-point direction"]
]) requireText(app,needle,label);

for(const [needle,label] of [
  ["width:800px;height:480px","display dimensions"],
  ["left:33px;top:82px;width:427px;height:225px","hero geometry"],
  ["left:477px;width:290px;height:50px","metric geometry"],
  ["top:316px;height:76px","bottom row geometry"],
  ["left:33px;top:410px;width:734px;height:52px","footer geometry"]
]) requireText(css,needle,label);

for(const id of ["apparentValue","tempValue","humidityValue","dewValue","ydayValue","windValue","directionValue","forecastValue","statusText"])
  requireText(html,`id=\"${id}\"`,`display field ${id}`);

const paletteTriples=["178,21,133","216,59,53","221,117,29","197,155,23","40,122,69","108,58,168","37,105,184","78,166,218","18,79,134"];
for(const rgb of paletteTriples)requireText(app,rgb,`palette ${rgb}`);

if(!process.exitCode) console.log(`SYNC OK: ${manifest.contract} emulator matches pinned production UI/math contract.`);
