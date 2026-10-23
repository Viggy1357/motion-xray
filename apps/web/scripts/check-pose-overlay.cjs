#!/usr/bin/env node
/* Offline unit checks for apps/web/app/pose-overlay.ts.
 * Transpiles the TS helper to CommonJS via the repo's existing `typescript`
 * package and evaluates it in a vm sandbox. No React, DOM, or network.
 *
 * Proposed command: docker exec web node scripts/check-pose-overlay.cjs
 */
"use strict";

const fs = require("fs");
const path = require("path");
const vm = require("vm");

const repoRoot = path.resolve(__dirname, "..");
const tsPath = path.join(repoRoot, "app/pose-overlay.ts");
const source = fs.readFileSync(tsPath, "utf8");

const ts = require(path.join(repoRoot, "node_modules/typescript"));
const js = ts.transpileModule(source, {
  compilerOptions: {
    module: ts.ModuleKind.CommonJS,
    target: ts.ScriptTarget.ES2020,
    strict: true,
  },
  fileName: "pose-overlay.ts",
}).outputText;

const moduleObj = { exports: {} };
const sandbox = {
  module: moduleObj,
  exports: moduleObj.exports,
  require,
  console,
  Number,
  Math,
  JSON,
  Error,
  Array,
  Object,
  String,
  Set,
};
vm.createContext(sandbox);
vm.runInContext(js, sandbox, { filename: "pose-overlay.js" });
const H = moduleObj.exports;

let passed = 0;
let failed = 0;
function check(name, fn) {
  try {
    fn();
    passed++;
    console.log(`ok   ${name}`);
  } catch (err) {
    failed++;
    console.error(`FAIL ${name}: ${err && err.message}`);
  }
}
function assert(cond, msg) {
  if (!cond) throw new Error(msg || "assertion failed");
}
function assertThrows(fn, msg) {
  let threw = false;
  try {
    fn();
  } catch {
    threw = true;
  }
  assert(threw, msg || "expected throw");
}

function joint(x, y, extra) {
  return Object.assign({ xy: [x, y], valid: true, interpolated: false }, extra);
}
function frameLine(index, t, joints) {
  return JSON.stringify({ frame_index: index, timestamp_s: t, joints });
}

const baseMap = {
  transform_version: "ffmpeg-proxy-v1",
  source_sha256: "a".repeat(64),
  proxy_sha256: "b".repeat(64),
  source_width: 719,
  source_height: 1279,
  source_rotation: 90,
  proxy_width: 720,
  proxy_height: 1280,
  padding_right: 1,
  padding_bottom: 1,
  frames: [
    { source_index: 0, source_s: 1.25, proxy_s: 0.0 },
    { source_index: 1, source_s: 1.2917, proxy_s: 0.0417 },
    { source_index: 2, source_s: 1.3333, proxy_s: 0.0833 },
    { source_index: 3, source_s: 1.375, proxy_s: 0.125 },
  ],
};

check("parsePoseText parses valid monotonic NDJSON", () => {
  const text = [
    frameLine(0, 1.25, { left_shoulder: joint(0.4, 0.4) }),
    frameLine(1, 1.2917, { left_shoulder: joint(0.5, 0.5) }),
  ].join("\n");
  const frames = H.parsePoseText(text);
  assert(frames.length === 2, "expected 2 frames");
  assert(frames[0].timestamp_s === 1.25, "order preserved");
  assert(frames[0].joints.left_shoulder.xy[0] === 0.4, "xy preserved");
});

check("parsePoseText rejects out-of-order and duplicate frame indices", () => {
  const ooo = [
    frameLine(1, 1.2917, {}),
    frameLine(0, 1.25, {}),
  ].join("\n");
  assertThrows(() => H.parsePoseText(ooo), "out-of-order indices must throw, not be sorted");
  const dup = [frameLine(0, 1.25, {}), frameLine(0, 1.2917, {})].join("\n");
  assertThrows(() => H.parsePoseText(dup), "duplicate indices must throw");
});

check("parsePoseText rejects malformed JSON and non-finite values", () => {
  assertThrows(() => H.parsePoseText("not json"), "bad JSON must throw");
  assertThrows(
    () => H.parsePoseText(frameLine(0, NaN, {})),
    "NaN timestamp must throw"
  );
  assertThrows(
    () =>
      H.parsePoseText(
        frameLine(0, 1.0, { a: { xy: [Infinity, 0], valid: true, interpolated: false } })
      ),
    "non-finite xy must throw"
  );
  assertThrows(
    () =>
      H.parsePoseText(
        frameLine(0, 1.0, { a: { xy: [0, 0], valid: "yes", interpolated: false } })
      ),
    "non-boolean valid must throw"
  );
});

check("parsePoseText rejects duplicate/unsorted-equal timestamps", () => {
  const text = [frameLine(0, 1.0, {}), frameLine(1, 1.0, {})].join("\n");
  assertThrows(() => H.parsePoseText(text), "equal timestamps must throw");
});

check("parseTimestampMap accepts odd padding and validates monotonic frames", () => {
  const map = H.parseTimestampMap(JSON.stringify(baseMap));
  assert(map.proxy_width === 720 && map.padding_right === 1, "padding kept");
  const bad = JSON.parse(JSON.stringify(baseMap));
  bad.frames[2].proxy_s = bad.frames[1].proxy_s; // break monotonicity
  assertThrows(
    () => H.parseTimestampMap(JSON.stringify(bad)),
    "non-increasing proxy_s must throw"
  );
  const badDims = JSON.parse(JSON.stringify(baseMap));
  badDims.proxy_width = 721;
  assertThrows(
    () => H.parseTimestampMap(JSON.stringify(badDims)),
    "proxy_width mismatch must throw"
  );
});

check("sourceTimeAt handles nonzero source offset (no zero-start assumption)", () => {
  const map = H.parseTimestampMap(JSON.stringify(baseMap));
  const t0 = H.sourceTimeAt(map, 0.0);
  assert(Math.abs(t0 - 1.25) < 1e-9, "proxy 0 must map to source 1.25");
  const t2 = H.sourceTimeAt(map, 0.0833);
  assert(Math.abs(t2 - 1.3333) < 1e-6, "nearest pair mapping");
  assert(H.sourceTimeAt(map, -1) === null, "negative time rejected");
  assert(H.sourceTimeAt(map, 0.5) === null, "beyond map end -> null, no edge hold");
});

check("proxyTimeAt inverts the map with nonzero source offset", () => {
  const map = H.parseTimestampMap(JSON.stringify(baseMap));
  const p = H.proxyTimeAt(map, 1.3333);
  assert(Math.abs(p - 0.0833) < 1e-6, "source 1.3333 must map to proxy 0.0833");
  assert(Math.abs(H.proxyTimeAt(map, 1.25) - 0.0) < 1e-9, "first pair maps to proxy 0");
  assert(H.proxyTimeAt(map, 0.5) === null, "before source range -> null");
  assert(H.proxyTimeAt(map, 9.9) === null, "after source range -> null");
  assert(H.proxyTimeAt(map, NaN) === null, "NaN rejected");
});

check("nearestObservedFrame respects 0.06s tolerance and long gaps stay empty", () => {
  const frames = H.parsePoseText(
    [frameLine(0, 1.0, {}), frameLine(1, 2.0, {}), frameLine(2, 5.0, {})].join("\n")
  );
  assert(H.nearestObservedFrame(frames, 1.05).timestamp_s === 1.0, "within tol");
  assert(H.nearestObservedFrame(frames, 1.07) === null, "beyond tol -> null");
  assert(H.nearestObservedFrame(frames, 3.5) === null, "long gap -> null, no hold");
  assert(H.nearestObservedFrame(frames, 5.05).timestamp_s === 5.0, "edge frame");
  assert(H.nearestObservedFrame([], 1.0) === null, "empty list -> null");
});

check("projectPoint maps odd padding + letterbox correctly", () => {
  const map = H.parseTimestampMap(JSON.stringify(baseMap));
  // Element 360x640 exactly matches 720x1280 aspect -> no letterbox.
  const rect = H.containRect(360, 640, map.proxy_width, map.proxy_height);
  assert(rect && rect.x === 0 && rect.y === 0, "no letterbox expected");
  // Canonical (1,1) is source bottom-right; padding strips the extra pixel.
  const p = H.projectPoint(1, 1, map, rect);
  assert(Math.abs(p.x - (719 / 720) * 360) < 1e-6, "x scaled by source/proxy");
  assert(Math.abs(p.y - (1279 / 1280) * 640) < 1e-6, "y scaled by source/proxy");
  // Wide element -> pillarbox letterbox on x.
  const rect2 = H.containRect(720, 640, map.proxy_width, map.proxy_height);
  assert(rect2 && rect2.x > 0 && rect2.y === 0, "pillarbox offset expected");
  const p2 = H.projectPoint(0, 0, map, rect2);
  assert(Math.abs(p2.x - rect2.x) < 1e-6 && Math.abs(p2.y) < 1e-6, "origin in rect");
});

check("projectPoint skips out-of-range/clipped and non-finite points", () => {
  const map = H.parseTimestampMap(JSON.stringify(baseMap));
  const rect = H.containRect(360, 640, 720, 1280);
  assert(H.projectPoint(-0.1, 0.5, map, rect) === null, "negative x clipped");
  assert(H.projectPoint(0.5, 1.2, map, rect) === null, "y>1 clipped");
  assert(H.projectPoint(NaN, 0.5, map, rect) === null, "NaN rejected");
});

check("drawablePoint masks missing, invalid, and interpolated joints", () => {
  const map = H.parseTimestampMap(JSON.stringify(baseMap));
  const rect = H.containRect(360, 640, 720, 1280);
  const frames = H.parsePoseText(
    frameLine(0, 1.0, {
      good: joint(0.5, 0.5),
      interp: { xy: [0.5, 0.5], valid: true, interpolated: true },
      invalid: { xy: [0.5, 0.5], valid: false, interpolated: false },
      noxy: { xy: null, valid: false, interpolated: false },
    })
  );
  const f = frames[0];
  assert(H.drawablePoint(f, "good", map, rect) !== null, "good joint drawn");
  assert(H.drawablePoint(f, "interp", map, rect) === null, "interpolated masked");
  assert(H.drawablePoint(f, "invalid", map, rect) === null, "invalid masked");
  assert(H.drawablePoint(f, "noxy", map, rect) === null, "null xy masked");
  assert(H.drawablePoint(f, "missing", map, rect) === null, "absent joint masked");
});

check("containRect rejects degenerate geometry", () => {
  assert(H.containRect(0, 100, 100, 100) === null, "zero element width");
  assert(H.containRect(100, 100, 0, 100) === null, "zero content width");
  assert(H.containRect(NaN, 100, 100, 100) === null, "NaN rejected");
});

console.log(`\n${passed} passed, ${failed} failed`);
process.exit(failed === 0 ? 0 : 1);
