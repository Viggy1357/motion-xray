// Pose overlay helpers for PoseReplay. Pure, framework-free, strictly typed.
// Canonical pose xy are normalized to [0,1] relative to source_width/source_height
// (rotation already baked by the backend proxy transform ffmpeg-proxy-v1).
// The proxy may carry 1px odd padding on right/bottom; we scale source dims to
// proxy dims before letterboxing into the object-fit:contain displayed area.

export const MAX_POSE_FRAMES = 15000;
export const MAX_MAP_FRAMES = 7200;
// Viewer-only displayed-frame tolerance. NOT a scoring threshold.
export const VIEWER_FRAME_TOLERANCE_S = 0.06;

export interface JointObservation {
  xy: [number, number] | null;
  valid: boolean;
  interpolated: boolean;
}

export interface PoseFrame {
  frame_index: number;
  timestamp_s: number; // ORIGINAL source PTS, seconds
  joints: Record<string, JointObservation>;
}

export interface TimestampPair {
  source_index: number;
  source_s: number;
  proxy_s: number;
}

export interface ProxyTimestampMap {
  transform_version: "ffmpeg-proxy-v1";
  source_width: number;
  source_height: number;
  source_rotation: number;
  proxy_width: number;
  proxy_height: number;
  padding_right: number;
  padding_bottom: number;
  frames: TimestampPair[];
}

export interface ContainRect {
  x: number; // CSS px offset of the displayed video image inside the element
  y: number;
  width: number;
  height: number;
}

function isFiniteNumber(v: unknown): v is number {
  return typeof v === "number" && Number.isFinite(v);
}

function isRecord(v: unknown): v is Record<string, unknown> {
  return typeof v === "object" && v !== null && !Array.isArray(v);
}

function parseJoint(name: string, raw: unknown): JointObservation {
  if (!isRecord(raw)) {
    throw new Error(`pose: joint ${name} is not an object`);
  }
  if (typeof raw.valid !== "boolean" || typeof raw.interpolated !== "boolean") {
    throw new Error(`pose: joint ${name} missing boolean valid/interpolated`);
  }
  let xy: [number, number] | null = null;
  if (raw.xy !== null && raw.xy !== undefined) {
    if (
      !Array.isArray(raw.xy) ||
      raw.xy.length !== 2 ||
      !isFiniteNumber(raw.xy[0]) ||
      !isFiniteNumber(raw.xy[1])
    ) {
      throw new Error(`pose: joint ${name} has non-finite xy`);
    }
    xy = [raw.xy[0], raw.xy[1]];
  }
  return { xy, valid: raw.valid, interpolated: raw.interpolated };
}

/** Parse canonical pose NDJSON (one PoseFrame per line). Throws on malformed input. */
export function parsePoseText(text: string): PoseFrame[] {
  if (typeof text !== "string") {
    throw new Error("pose: input must be text");
  }
  const lines = text.split(/\r?\n/).filter((l) => l.trim().length > 0);
  if (lines.length === 0) {
    throw new Error("pose: no frames");
  }
  if (lines.length > MAX_POSE_FRAMES) {
    throw new Error(`pose: frame count ${lines.length} exceeds ${MAX_POSE_FRAMES}`);
  }
  const frames: PoseFrame[] = lines.map((line, i) => {
    let raw: unknown;
    try {
      raw = JSON.parse(line);
    } catch {
      throw new Error(`pose: line ${i + 1} is not valid JSON`);
    }
    if (!isRecord(raw)) {
      throw new Error(`pose: line ${i + 1} is not an object`);
    }
    if (!Number.isInteger(raw.frame_index) || (raw.frame_index as number) < 0) {
      throw new Error(`pose: line ${i + 1} bad frame_index`);
    }
    if (!isFiniteNumber(raw.timestamp_s) || raw.timestamp_s < 0) {
      throw new Error(`pose: line ${i + 1} bad timestamp_s`);
    }
    if (!isRecord(raw.joints)) {
      throw new Error(`pose: line ${i + 1} missing joints`);
    }
    const joints: Record<string, JointObservation> = {};
    for (const [name, j] of Object.entries(raw.joints)) {
      joints[name] = parseJoint(name, j);
    }
    return {
      frame_index: raw.frame_index as number,
      timestamp_s: raw.timestamp_s,
      joints,
    };
  });
  // Contract requires monotonic capture order: reject out-of-order or
  // duplicate frame indices/timestamps instead of silently re-sorting.
  for (let i = 1; i < frames.length; i++) {
    if (frames[i].frame_index <= frames[i - 1].frame_index) {
      throw new Error("pose: frame_index must be strictly increasing (input order)");
    }
    if (frames[i].timestamp_s <= frames[i - 1].timestamp_s) {
      throw new Error("pose: timestamps must be strictly increasing");
    }
  }
  return frames;
}

/** Parse and validate a ProxyTimestampMap JSON string. Throws on malformed input. */
export function parseTimestampMap(text: string): ProxyTimestampMap {
  let raw: unknown;
  try {
    raw = JSON.parse(text);
  } catch {
    throw new Error("timestamps: not valid JSON");
  }
  if (!isRecord(raw)) {
    throw new Error("timestamps: not an object");
  }
  if (raw.transform_version !== "ffmpeg-proxy-v1") {
    throw new Error("timestamps: unsupported transform_version");
  }
  const dims: Array<[string, number, number]> = [
    ["source_width", 1, 1920],
    ["source_height", 1, 1920],
    ["proxy_width", 1, 1920],
    ["proxy_height", 1, 1920],
  ];
  for (const [key, lo, hi] of dims) {
    const v = raw[key];
    if (!Number.isInteger(v) || (v as number) < lo || (v as number) > hi) {
      throw new Error(`timestamps: ${key} out of bounds`);
    }
  }
  const source_width = raw.source_width as number;
  const source_height = raw.source_height as number;
  const proxy_width = raw.proxy_width as number;
  const proxy_height = raw.proxy_height as number;
  const padding_right = raw.padding_right;
  const padding_bottom = raw.padding_bottom;
  if (padding_right !== 0 && padding_right !== 1) {
    throw new Error("timestamps: padding_right must be 0 or 1");
  }
  if (padding_bottom !== 0 && padding_bottom !== 1) {
    throw new Error("timestamps: padding_bottom must be 0 or 1");
  }
  if (proxy_width !== source_width + padding_right) {
    throw new Error("timestamps: proxy_width must equal source_width + padding_right");
  }
  if (proxy_height !== source_height + padding_bottom) {
    throw new Error("timestamps: proxy_height must equal source_height + padding_bottom");
  }
  const rotation = raw.source_rotation;
  if (
    typeof rotation !== "number" ||
    ![0, 90, -90, 180, -180].includes(rotation)
  ) {
    throw new Error("timestamps: bad source_rotation");
  }
  if (!Array.isArray(raw.frames)) {
    throw new Error("timestamps: frames must be an array");
  }
  if (raw.frames.length < 2 || raw.frames.length > MAX_MAP_FRAMES) {
    throw new Error(`timestamps: frame count out of range: ${raw.frames.length}`);
  }
  const frames: TimestampPair[] = raw.frames.map((f: unknown, i: number) => {
    if (!isRecord(f)) {
      throw new Error(`timestamps: frame ${i} not an object`);
    }
    if (!Number.isInteger(f.source_index) || (f.source_index as number) < 0) {
      throw new Error(`timestamps: frame ${i} bad source_index`);
    }
    if (!isFiniteNumber(f.source_s) || f.source_s < 0) {
      throw new Error(`timestamps: frame ${i} bad source_s`);
    }
    if (!isFiniteNumber(f.proxy_s) || f.proxy_s < 0) {
      throw new Error(`timestamps: frame ${i} bad proxy_s`);
    }
    return {
      source_index: f.source_index as number,
      source_s: f.source_s,
      proxy_s: f.proxy_s,
    };
  });
  for (let i = 1; i < frames.length; i++) {
    if (
      frames[i].source_index <= frames[i - 1].source_index ||
      frames[i].source_s <= frames[i - 1].source_s ||
      frames[i].proxy_s <= frames[i - 1].proxy_s
    ) {
      throw new Error("timestamps: frames must be strictly increasing");
    }
  }
  return {
    transform_version: "ffmpeg-proxy-v1",
    source_width,
    source_height,
    source_rotation: rotation,
    proxy_width,
    proxy_height,
    padding_right,
    padding_bottom,
    frames,
  };
}

/** Map a proxy currentTime (s) to the ORIGINAL source PTS via the nearest pair. */
export function sourceTimeAt(map: ProxyTimestampMap, proxyS: number): number | null {
  if (!isFiniteNumber(proxyS) || proxyS < 0) {
    return null;
  }
  const frames = map.frames;
  if (proxyS < frames[0].proxy_s || proxyS > frames[frames.length - 1].proxy_s) {
    return null; // outside the measured map range: never hold the edge pose
  }
  let lo = 0;
  let hi = frames.length - 1;
  while (lo < hi) {
    const mid = (lo + hi) >> 1;
    if (frames[mid].proxy_s < proxyS) {
      lo = mid + 1;
    } else {
      hi = mid;
    }
  }
  let best = frames[lo];
  if (lo > 0) {
    const prev = frames[lo - 1];
    if (Math.abs(prev.proxy_s - proxyS) <= Math.abs(best.proxy_s - proxyS)) {
      best = prev;
    }
  }
  return best.source_s;
}

/** Inverse of sourceTimeAt: map an ORIGINAL source PTS to proxy currentTime. */
export function proxyTimeAt(map: ProxyTimestampMap, sourceS: number): number | null {
  if (!isFiniteNumber(sourceS) || sourceS < 0) {
    return null;
  }
  const frames = map.frames;
  if (sourceS < frames[0].source_s || sourceS > frames[frames.length - 1].source_s) {
    return null;
  }
  let lo = 0;
  let hi = frames.length - 1;
  while (lo < hi) {
    const mid = (lo + hi) >> 1;
    if (frames[mid].source_s < sourceS) {
      lo = mid + 1;
    } else {
      hi = mid;
    }
  }
  let best = frames[lo];
  if (lo > 0) {
    const prev = frames[lo - 1];
    if (Math.abs(prev.source_s - sourceS) <= Math.abs(best.source_s - sourceS)) {
      best = prev;
    }
  }
  return best.proxy_s;
}

/**
 * Nearest observed pose frame to a source PTS, only when within tolerance.
 * No interpolation, no holding through gaps: returns null outside tolerance.
 */
export function nearestObservedFrame(
  frames: PoseFrame[],
  sourceS: number,
  toleranceS: number = VIEWER_FRAME_TOLERANCE_S
): PoseFrame | null {
  if (!isFiniteNumber(sourceS) || frames.length === 0) {
    return null;
  }
  let lo = 0;
  let hi = frames.length - 1;
  while (lo < hi) {
    const mid = (lo + hi) >> 1;
    if (frames[mid].timestamp_s < sourceS) {
      lo = mid + 1;
    } else {
      hi = mid;
    }
  }
  let best = frames[lo];
  if (lo > 0) {
    const prev = frames[lo - 1];
    if (Math.abs(prev.timestamp_s - sourceS) <= Math.abs(best.timestamp_s - sourceS)) {
      best = prev;
    }
  }
  if (Math.abs(best.timestamp_s - sourceS) <= toleranceS) {
    return best;
  }
  return null;
}

/**
 * Project a canonical normalized xy into CSS px inside the displayed video
 * image rect. Canonical xy are relative to source_width/source_height; the
 * proxy adds odd padding right/bottom, so scale by source/proxy dims first.
 * Returns null for non-finite or out-of-range (clipped) points; never invents.
 */
export function projectPoint(
  x: number,
  y: number,
  map: ProxyTimestampMap,
  rect: ContainRect
): { x: number; y: number } | null {
  if (!isFiniteNumber(x) || !isFiniteNumber(y)) {
    return null;
  }
  if (x < 0 || x > 1 || y < 0 || y > 1) {
    return null; // clipped by provider; skip, do not clamp/invent
  }
  const px = (x * map.source_width) / map.proxy_width;
  const py = (y * map.source_height) / map.proxy_height;
  return {
    x: rect.x + px * rect.width,
    y: rect.y + py * rect.height,
  };
}

/** Compute the object-fit:contain image rect for proxy dims inside an element. */
export function containRect(
  elementWidth: number,
  elementHeight: number,
  contentWidth: number,
  contentHeight: number
): ContainRect | null {
  if (
    !isFiniteNumber(elementWidth) ||
    !isFiniteNumber(elementHeight) ||
    !isFiniteNumber(contentWidth) ||
    !isFiniteNumber(contentHeight) ||
    elementWidth <= 0 ||
    elementHeight <= 0 ||
    contentWidth <= 0 ||
    contentHeight <= 0
  ) {
    return null;
  }
  const scale = Math.min(elementWidth / contentWidth, elementHeight / contentHeight);
  const width = contentWidth * scale;
  const height = contentHeight * scale;
  return {
    x: (elementWidth - width) / 2,
    y: (elementHeight - height) / 2,
    width,
    height,
  };
}

/** Skeleton edges drawn only between observed, valid, non-interpolated joints. */
export const SKELETON_EDGES: ReadonlyArray<readonly [string, string]> = [
  ["left_shoulder", "right_shoulder"],
  ["left_shoulder", "left_elbow"],
  ["left_elbow", "left_wrist"],
  ["right_shoulder", "right_elbow"],
  ["right_elbow", "right_wrist"],
  ["left_shoulder", "left_hip"],
  ["right_shoulder", "right_hip"],
  ["left_hip", "right_hip"],
  ["left_hip", "left_knee"],
  ["left_knee", "left_ankle"],
  ["right_hip", "right_knee"],
  ["right_knee", "right_ankle"],
];

/** A joint is drawable only when observed: valid AND not interpolated AND finite xy. */
export function drawablePoint(
  frame: PoseFrame,
  name: string,
  map: ProxyTimestampMap,
  rect: ContainRect
): { x: number; y: number } | null {
  const joint = frame.joints[name];
  if (!joint || !joint.valid || joint.interpolated || joint.xy === null) {
    return null;
  }
  return projectPoint(joint.xy[0], joint.xy[1], map, rect);
}
