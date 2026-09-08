"use strict";

// Sync contract: concept-1-7c / production display_ui.cpp + weather_math.cpp
const DISPLAY_CONTRACT = "concept-1-7c";
const FORECAST_SWITCH_MS = 30000;

const palettes = {
  heat: [
    {min:125, top:[178,21,133], bottom:[55,8,47], border:[244,87,204], status:[76,10,64], accent:[255,139,228]},
    {min:103, top:[216,59,53], bottom:[70,17,15], border:[255,113,104], status:[82,18,14], accent:[255,140,130]},
    {min:90, top:[221,117,29], bottom:[71,30,8], border:[255,173,75], status:[88,35,7], accent:[255,192,110]},
    {min:80, top:[197,155,23], bottom:[66,50,7], border:[255,228,94], status:[91,68,7], accent:[255,235,128]},
    {min:-Infinity, top:[40,122,69], bottom:[10,35,20], border:[97,216,137], status:[18,58,32], accent:[143,232,170]}
  ],
  cold: [
    {max:-48, top:[108,58,168], bottom:[31,15,67], border:[190,132,242], status:[39,18,79], accent:[219,172,255]},
    {max:-32, top:[37,105,184], bottom:[10,34,78], border:[99,171,255], status:[9,30,67], accent:[139,198,255]},
    {max:-18, top:[78,166,218], bottom:[13,61,96], border:[158,223,255], status:[11,48,76], accent:[194,235,255]},
    {max:Infinity, top:[18,79,134], bottom:[6,25,44], border:[88,183,255], status:[8,28,49], accent:[123,201,255]}
  ]
};

function dewPointF(tempF, rh) {
  const tC=(tempF-32)*5/9;
  const bounded=Math.max(0.1,Math.min(100,rh));
  const a=17.625,b=243.04;
  const gamma=Math.log(bounded/100)+(a*tC)/(b+tC);
  return ((b*gamma)/(a-gamma))*9/5+32;
}

function heatIndexF(tempF, rh) {
  // NWS simple heat-index estimate followed by Rothfusz regression.
  const simple=0.5*(tempF+61.0+((tempF-68.0)*1.2)+(rh*0.094));
  const averaged=(simple+tempF)/2;
  if (averaged < 80) return averaged;
  const T=tempF,R=rh;
  let hi=-42.379+2.04901523*T+10.14333127*R-0.22475541*T*R-0.00683783*T*T-0.05481717*R*R+0.00122874*T*T*R+0.00085282*T*R*R-0.00000199*T*T*R*R;
  if (R<13 && T>=80 && T<=112) hi-=((13-R)/4)*Math.sqrt((17-Math.abs(T-95))/17);
  else if (R>85 && T>=80 && T<=87) hi+=((R-85)/10)*((87-T)/5);
  return hi;
}

function windChillF(tempF, windMph) {
  if (!(tempF<=50 && windMph>3)) return null;
  const v16=Math.pow(windMph,0.16);
  return 35.74+0.6215*tempF-35.75*v16+0.4275*tempF*v16;
}

function apparentTemperature(tempF,rh,windMph){
  const wc=windChillF(tempF,windMph);
  return {value:wc===null?heatIndexF(tempF,rh):wc, mode:wc===null?"heat":"cold"};
}

function riskLabel(value,mode){
  if(mode==="cold"){
    if(value<=-35)return "EXTREME DANGER";
    if(value<=-20)return "DANGER";
    if(value<=0)return "VERY COLD";
    if(value<=20)return "COLD";
    return "CHILLY";
  }
  if(value>=125)return "EXTREME DANGER";
  if(value>=103)return "DANGER";
  if(value>=90)return "EXTREME CAUTION";
  if(value>=80)return "CAUTION";
  return "NORMAL";
}

function direction16(deg){
  const names=["N","NNE","NE","ENE","E","ESE","SE","SSE","S","SSW","SW","WSW","W","WNW","NW","NNW"];
  const n=((deg%360)+360)%360;
  return names[Math.floor((n+11.25)/22.5)%16];
}

function paletteFor(value,mode){
  if(mode==="cold") return palettes.cold.find(p=>value<=p.max);
  return palettes.heat.find(p=>value>=p.min);
}

function fmt(n,digits=0){return Number.isFinite(n)?n.toFixed(digits):"--";}
function number(id){return Number(document.getElementById(id).value);}
function setRgb(name,v){document.getElementById("display").style.setProperty(name,v.join(","));}

let forecastTomorrow=false;
let lastUpdated=new Date();

function render(){
  const temp=number("inputTemp"),rh=number("inputHumidity"),wind=number("inputWind"),gust=number("inputGust"),maxGust=number("inputMaxGust"),dir=number("inputDirection"),yday=number("inputYday");
  const apparent=apparentTemperature(temp,rh,wind);
  const p=paletteFor(apparent.value,apparent.mode);
  setRgb("--top",p.top);setRgb("--bottom",p.bottom);setRgb("--border",p.border);setRgb("--status",p.status);setRgb("--accent",p.accent);
  document.getElementById("stationName").textContent=(document.getElementById("inputStation").value.trim()||"Weather Station").slice(0,20);
  document.getElementById("dateText").textContent=new Date().toLocaleDateString(undefined,{weekday:"short",month:"short",day:"numeric"}).toUpperCase();
  document.getElementById("apparentLabel").textContent=apparent.mode==="cold"?"WIND CHILL":"HEAT INDEX";
  document.getElementById("apparentValue").textContent=fmt(apparent.value);
  document.querySelector(".hero").classList.toggle("cold",apparent.mode==="cold");
  document.getElementById("heroIcon").textContent=apparent.mode==="cold"?"≋":"☀";
  document.getElementById("riskBadge").textContent=riskLabel(apparent.value,apparent.mode);
  document.getElementById("tempValue").textContent=`${fmt(temp,1)}°F`;
  document.getElementById("humidityValue").textContent=`${fmt(rh)}%`;
  document.getElementById("dewValue").textContent=`${fmt(dewPointF(temp,rh),1)}°F`;
  document.getElementById("ydayValue").textContent=`${yday>=0?"+":""}${fmt(yday,1)}°F`;
  document.getElementById("ydayDetail").textContent=yday===0?"NO CHANGE":yday>0?"WARMER":"COOLER";
  document.getElementById("windValue").textContent=fmt(wind,1);
  document.getElementById("gustValue").textContent=`GUST ${fmt(gust,1)}`;
  document.getElementById("maxGustValue").textContent=`MAX ${fmt(maxGust,1)}`;
  document.getElementById("directionDegrees").textContent=`${fmt(((dir%360)+360)%360)}°`;
  document.getElementById("directionValue").textContent=direction16(dir);
  const high=number(forecastTomorrow?"inputTomorrowHigh":"inputTodayHigh"),low=number(forecastTomorrow?"inputTomorrowLow":"inputTodayLow");
  document.getElementById("forecastLabel").textContent=forecastTomorrow?"TOMORROW":"TODAY";
  document.getElementById("forecastValue").textContent=`H ${fmt(high)}° / L ${fmt(low)}°`;
  document.getElementById("forecastDetail").textContent=forecastTomorrow?"NEXT DAY FORECAST":"CURRENT DAY FORECAST";
  const stale=document.getElementById("inputStale").checked;
  const status=document.getElementById("statusText"); status.textContent=stale?"STALE":"ONLINE";status.classList.toggle("stale",stale);
  document.getElementById("updatedText").textContent=`Updated ${lastUpdated.toLocaleTimeString([],{hour:"numeric",minute:"2-digit"})}`;
}

const presets={
  normal:{inputTemp:78,inputHumidity:55,inputWind:4,inputGust:8,inputMaxGust:12,inputDirection:180},
  caution:{inputTemp:88,inputHumidity:60,inputWind:4,inputGust:8,inputMaxGust:13,inputDirection:210},
  danger:{inputTemp:96,inputHumidity:65,inputWind:5,inputGust:11,inputMaxGust:18,inputDirection:225},
  extreme:{inputTemp:105,inputHumidity:70,inputWind:5,inputGust:12,inputMaxGust:20,inputDirection:240},
  cold:{inputTemp:10,inputHumidity:50,inputWind:22,inputGust:31,inputMaxGust:39,inputDirection:315}
};

document.querySelectorAll("input").forEach(el=>el.addEventListener("input",()=>{lastUpdated=new Date();render();}));
document.querySelectorAll("[data-preset]").forEach(btn=>btn.addEventListener("click",()=>{Object.entries(presets[btn.dataset.preset]).forEach(([id,val])=>document.getElementById(id).value=val);lastUpdated=new Date();render();}));
setInterval(()=>{forecastTomorrow=!forecastTomorrow;render();},FORECAST_SWITCH_MS);
render();

// Expose pure functions for the sync verifier / browser console.
window.Concept1Emulator={DISPLAY_CONTRACT,dewPointF,heatIndexF,windChillF,apparentTemperature,riskLabel,direction16,paletteFor};
