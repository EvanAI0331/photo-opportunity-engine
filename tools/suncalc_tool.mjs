import SunCalc from "suncalc";

const [timeArg, latArg, lngArg] = process.argv.slice(2);

if (!timeArg || !latArg || !lngArg) {
  console.error("usage: node tools/suncalc_tool.mjs <iso-time> <lat> <lng>");
  process.exit(2);
}

const time = new Date(timeArg);
const lat = Number(latArg);
const lng = Number(lngArg);

if (Number.isNaN(time.getTime()) || Number.isNaN(lat) || Number.isNaN(lng)) {
  console.error("invalid time, lat, or lng");
  process.exit(2);
}

const times = SunCalc.getTimes(time, lat, lng);
const sun = SunCalc.getPosition(time, lat, lng);
const moon = SunCalc.getMoonPosition(time, lat, lng);
const illumination = SunCalc.getMoonIllumination(time);

const toIso = (value) => value instanceof Date && !Number.isNaN(value.getTime()) ? value.toISOString() : null;
const azimuthDegrees = (azimuth) => (azimuth * 180 / Math.PI + 180 + 360) % 360;
const altitudeDegrees = (altitude) => altitude * 180 / Math.PI;

const payload = {
  times: Object.fromEntries(Object.entries(times).map(([key, value]) => [key, toIso(value)])),
  sun: {
    azimuth: azimuthDegrees(sun.azimuth),
    altitude: altitudeDegrees(sun.altitude)
  },
  moon: {
    azimuth: azimuthDegrees(moon.azimuth),
    altitude: altitudeDegrees(moon.altitude),
    distance_km: moon.distance
  },
  moon_illumination: {
    fraction: illumination.fraction,
    phase: illumination.phase,
    angle: illumination.angle
  }
};

console.log(JSON.stringify(payload));
