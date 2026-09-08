#include <math.h>
#include "app_state.h"
#include "weather_math.h"

float dewPointFromTempHumidityF(float tF, float rh) {
  if (!isfinite(tF) || !isfinite(rh) || rh <= 0.0f || rh > 100.0f) return NAN;
  float tC = (tF - 32.0f) * 5.0f / 9.0f;
  const float a = 17.625f;
  const float b = 243.04f;
  float gamma = logf(rh / 100.0f) + (a * tC) / (b + tC);
  float dpC = (b * gamma) / (a - gamma);
  return dpC * 9.0f / 5.0f + 32.0f;
}

float nwsHeatIndexF(float t, float rh) {
  float simple = 0.5f * (t + 61.0f + ((t - 68.0f) * 1.2f) + (rh * 0.094f));
  simple = (simple + t) * 0.5f;
  if (simple < 80.0f) return simple;

  float hi =
      -42.379f
      + 2.04901523f * t
      + 10.14333127f * rh
      - 0.22475541f * t * rh
      - 0.00683783f * t * t
      - 0.05481717f * rh * rh
      + 0.00122874f * t * t * rh
      + 0.00085282f * t * rh * rh
      - 0.00000199f * t * t * rh * rh;

  if (rh < 13.0f && t >= 80.0f && t <= 112.0f) {
    float inside = (17.0f - fabsf(t - 95.0f)) / 17.0f;
    if (inside > 0.0f) hi -= ((13.0f - rh) / 4.0f) * sqrtf(inside);
  } else if (rh > 85.0f && t >= 80.0f && t <= 87.0f) {
    hi += ((rh - 85.0f) / 10.0f) * ((87.0f - t) / 5.0f);
  }
  return hi;
}

float nwsWindChillF(float t, float windMph) {
  if (!isfinite(t) || !isfinite(windMph)) return t;
  if (t > 50.0f || windMph <= 3.0f) return t;
  float v16 = powf(windMph, 0.16f);
  return 35.74f + 0.6215f * t - 35.75f * v16 + 0.4275f * t * v16;
}

bool windChillApplies() {
  return wx.valid && isfinite(wx.tempF) && isfinite(wx.windMph) &&
         wx.tempF <= 50.0f && wx.windMph > 3.0f;
}

float apparentOutdoorF() {
  return windChillApplies() ? wx.windChillF : wx.heatIndexF;
}

const char* apparentTitle() {
  return windChillApplies() ? "WIND CHILL" : "HEAT INDEX";
}

const char* riskLabel(float hi) {
  if (hi >= 125.0f) return "EXTREME DANGER";
  if (hi >= 103.0f) return "DANGER";
  if (hi >= 90.0f)  return "EXTREME CAUTION";
  if (hi >= 80.0f)  return "CAUTION";
  return "NORMAL";
}

const char* coldRiskLabel(float wc) {
  if (wc <= -35.0f) return "EXTREME DANGER";
  if (wc <= -20.0f) return "DANGER";
  if (wc <= 0.0f) return "VERY COLD";
  if (wc <= 20.0f) return "COLD";
  return "CHILLY";
}

const char* apparentRiskLabel() {
  return windChillApplies() ? coldRiskLabel(wx.windChillF) : riskLabel(wx.heatIndexF);
}

String directionText(float deg) {
  if (!isfinite(deg)) return "--";
  static const char* dirs[] = {"N","NNE","NE","ENE","E","ESE","SE","SSE",
                               "S","SSW","SW","WSW","W","WNW","NW","NNW"};
  int idx = (int)floorf((deg + 11.25f) / 22.5f) % 16;
  return String(dirs[idx]);
}
