"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import {
  containRect,
  drawablePoint,
  nearestObservedFrame,
  parsePoseText,
  parseTimestampMap,
  proxyTimeAt,
  sourceTimeAt,
  SKELETON_EDGES,
  type PoseFrame,
  type ProxyTimestampMap,
} from "./pose-overlay";

export interface PoseReplayProps {
  analysisId: string;
  playbackRate: number;
  onVideoError: () => void;
}

type OverlayStatus =
  | { kind: "loading" }
  | { kind: "ready"; frames: PoseFrame[]; map: ProxyTimestampMap }
  | { kind: "unavailable"; reason: string };

type RVFCVideo = HTMLVideoElement & {
  requestVideoFrameCallback?: (callback: () => void) => number;
  cancelVideoFrameCallback?: (handle: number) => void;
};

const MAX_POSE_BYTES = 32 * 1024 * 1024;
const MAX_MAP_BYTES = 8 * 1024 * 1024;
// Source-time broadcast throttle: max 5 Hz.
const SOURCE_TIME_MIN_INTERVAL_MS = 200;

// Bound by actually-read bytes, not by Content-Length alone: stream the
// body, cancel the reader and abort past the cap so an untrusted artifact
// can never be buffered unbounded into memory.
async function readBoundedText(
  res: Response,
  maxBytes: number,
  signal: AbortSignal
): Promise<string> {
  const reader = res.body?.getReader();
  if (!reader) {
    throw new Error("artifact body unreadable");
  }
  const chunks: Uint8Array[] = [];
  let total = 0;
  try {
    for (;;) {
      if (signal.aborted) {
        throw new DOMException("aborted", "AbortError");
      }
      const { done, value } = await reader.read();
      if (done) {
        break;
      }
      total += value.byteLength;
      if (total > maxBytes) {
        await reader.cancel();
        throw new Error(`artifact exceeds ${Math.round(maxBytes / (1024 * 1024))} MiB limit`);
      }
      chunks.push(value);
    }
  } finally {
    reader.releaseLock();
  }
  const buf = new Uint8Array(total);
  let off = 0;
  for (const c of chunks) {
    buf.set(c, off);
    off += c.byteLength;
  }
  return new TextDecoder().decode(buf);
}

const COBALT = "#1f4fd8";
const WHITE = "#ffffff";

export default function PoseReplay({
  analysisId,
  playbackRate,
  onVideoError,
}: PoseReplayProps) {
  const videoRef = useRef<HTMLVideoElement | null>(null);
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const [status, setStatus] = useState<OverlayStatus>({ kind: "loading" });
  const [overlayOn, setOverlayOn] = useState(true);

  // Preserve the caller's callback across inline-identity changes without
  // retriggering fetches or effect loops.
  const onVideoErrorRef = useRef(onVideoError);
  useEffect(() => {
    onVideoErrorRef.current = onVideoError;
  }, [onVideoError]);

  const analysisIdRef = useRef(analysisId);
  useEffect(() => {
    analysisIdRef.current = analysisId;
  }, [analysisId]);

  const statusRef = useRef<OverlayStatus>(status);
  useEffect(() => {
    statusRef.current = status;
  }, [status]);
  const overlayOnRef = useRef(overlayOn);
  useEffect(() => {
    overlayOnRef.current = overlayOn;
  }, [overlayOn]);

  const lastSourceTimeEmitRef = useRef(0);

  // Broadcast the player's current ORIGINAL source PTS (from the canonical
  // measured timestamp map, never zero-assumed) so listeners can follow
  // actual playback. Throttled to max 5 Hz; emits nothing outside the map.
  const emitSourceTime = useCallback(() => {
    const video = videoRef.current;
    const st = statusRef.current;
    if (!video || st.kind !== "ready" || video.error) {
      return;
    }
    const now = performance.now();
    if (now - lastSourceTimeEmitRef.current < SOURCE_TIME_MIN_INTERVAL_MS) {
      return;
    }
    const sourceS = sourceTimeAt(st.map, video.currentTime);
    if (sourceS === null) {
      return;
    }
    lastSourceTimeEmitRef.current = now;
    window.dispatchEvent(
      new CustomEvent("mxr:source-time", {
        detail: { analysisId: analysisIdRef.current, sourceS },
      })
    );
  }, []);

  const clearCanvas = useCallback(() => {
    const canvas = canvasRef.current;
    const ctx = canvas?.getContext("2d");
    if (canvas && ctx) {
      ctx.clearRect(0, 0, canvas.width, canvas.height);
    }
  }, []);

  const drawFrame = useCallback(() => {
    const video = videoRef.current;
    const canvas = canvasRef.current;
    if (!video || !canvas) {
      return;
    }
    const ctx = canvas.getContext("2d");
    if (!ctx) {
      return;
    }
    const dpr = window.devicePixelRatio || 1;
    const cssW = canvas.clientWidth;
    const cssH = canvas.clientHeight;
    if (cssW <= 0 || cssH <= 0) {
      return;
    }
    const pxW = Math.round(cssW * dpr);
    const pxH = Math.round(cssH * dpr);
    if (canvas.width !== pxW || canvas.height !== pxH) {
      canvas.width = pxW;
      canvas.height = pxH;
    }
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    ctx.clearRect(0, 0, cssW, cssH);
    if (video.error) {
      return; // after a video error the overlay stays clear, even on later seeks
    }

    const st = statusRef.current;
    if (st.kind === "ready") {
      emitSourceTime();
    }
    if (!overlayOnRef.current || st.kind !== "ready") {
      return;
    }
    const rect = containRect(cssW, cssH, st.map.proxy_width, st.map.proxy_height);
    if (!rect) {
      return;
    }
    const sourceS = sourceTimeAt(st.map, video.currentTime);
    if (sourceS === null) {
      return;
    }
    const frame = nearestObservedFrame(st.frames, sourceS);
    if (!frame) {
      return; // gap: draw nothing, never hold or interpolate
    }

    ctx.lineWidth = 2;
    ctx.strokeStyle = COBALT;
    ctx.lineCap = "round";
    for (const [a, b] of SKELETON_EDGES) {
      const pa = drawablePoint(frame, a, st.map, rect);
      const pb = drawablePoint(frame, b, st.map, rect);
      if (!pa || !pb) {
        continue; // invalid point breaks the limb; no interpolation
      }
      ctx.beginPath();
      ctx.moveTo(pa.x, pa.y);
      ctx.lineTo(pb.x, pb.y);
      ctx.stroke();
    }
    const drawn = new Set<string>();
    for (const [a, b] of SKELETON_EDGES) {
      drawn.add(a);
      drawn.add(b);
    }
    for (const name of drawn) {
      const p = drawablePoint(frame, name, st.map, rect);
      if (!p) {
        continue;
      }
      ctx.beginPath();
      ctx.arc(p.x, p.y, 3.5, 0, Math.PI * 2);
      ctx.fillStyle = COBALT;
      ctx.fill();
      ctx.lineWidth = 1.5;
      ctx.strokeStyle = WHITE;
      ctx.stroke();
    }
  }, [emitSourceTime]);

  // Draw once refs are current: toggling the overlay on, or data becoming
  // ready while paused, must render immediately rather than showing a stale
  // frame until the next timeupdate (previously draw ran before ref effects).
  useEffect(() => {
    if (status.kind === "ready" && overlayOn) {
      drawFrame();
    }
  }, [status, overlayOn, drawFrame]);

  // Fetch pose + timestamp artifacts once per analysisId, with abort/reset.
  useEffect(() => {
    const controller = new AbortController();
    setStatus({ kind: "loading" });
    setOverlayOn(true);
    clearCanvas();

    const base = `/api/analyses/${encodeURIComponent(analysisId)}/artifacts`;
    const init: RequestInit = {
      credentials: "include",
      signal: controller.signal,
      headers: { Accept: "application/octet-stream, application/json" },
    };

    (async () => {
      try {
        const [poseRes, tsRes] = await Promise.all([
          fetch(`${base}/pose`, init),
          fetch(`${base}/timestamps`, init),
        ]);
        if (!poseRes.ok) {
          throw new Error(`pose artifact unavailable (HTTP ${poseRes.status})`);
        }
        if (!tsRes.ok) {
          throw new Error(`timestamp map unavailable (HTTP ${tsRes.status})`);
        }
        const [poseText, tsText] = await Promise.all([
          readBoundedText(poseRes, MAX_POSE_BYTES, controller.signal),
          readBoundedText(tsRes, MAX_MAP_BYTES, controller.signal),
        ]);
        if (controller.signal.aborted) {
          return;
        }
        const frames = parsePoseText(poseText);
        const map = parseTimestampMap(tsText);
        if (controller.signal.aborted) {
          return;
        }
        setStatus({ kind: "ready", frames, map });
      } catch (err) {
        if (controller.signal.aborted) {
          return;
        }
        const reason =
          err instanceof Error ? err.message : "pose data unavailable";
        setStatus({ kind: "unavailable", reason });
      }
    })();

    return () => {
      controller.abort();
      clearCanvas();
    };
  }, [analysisId, clearCanvas]);

  // External seek requests carry ORIGINAL source PTS seconds; convert to
  // proxy currentTime via the measured timestamp map (never zero-assumed).
  useEffect(() => {
    const onSeek = (ev: Event) => {
      const detail = (ev as CustomEvent<unknown>).detail;
      const sourceS =
        typeof detail === "number"
          ? detail
          : (detail as { seconds?: unknown } | null)?.seconds;
      if (typeof sourceS !== "number" || !Number.isFinite(sourceS)) {
        return;
      }
      const st = statusRef.current;
      const video = videoRef.current;
      if (st.kind !== "ready" || !video) {
        return;
      }
      const proxyS = proxyTimeAt(st.map, sourceS);
      if (proxyS === null) {
        return;
      }
      video.currentTime = proxyS;
      void video.play().catch(() => undefined);
    };
    window.addEventListener("mxr:seek-source", onSeek);
    return () => window.removeEventListener("mxr:seek-source", onSeek);
  }, []);

  // Playback rate is owned by the parent; assign on prop change.
  useEffect(() => {
    const video = videoRef.current;
    if (video && Number.isFinite(playbackRate) && playbackRate > 0) {
      video.playbackRate = playbackRate;
    }
  }, [playbackRate]);

  // Frame scheduling: rVFC while playing when available, RAF fallback while
  // playing, plus discrete events. No RAF while paused/hidden/offscreen.
  useEffect(() => {
    const video = videoRef.current as RVFCVideo | null;
    if (!video) {
      return;
    }
    let rafId: number | null = null;
    let rvfcId: number | null = null;
    let disposed = false;

    const cancelLoops = () => {
      if (rafId !== null) {
        cancelAnimationFrame(rafId);
        rafId = null;
      }
      if (rvfcId !== null && video.cancelVideoFrameCallback) {
        video.cancelVideoFrameCallback(rvfcId);
        rvfcId = null;
      }
    };

    const tick = () => {
      if (disposed) {
        return;
      }
      drawFrame();
      schedule();
    };

    const schedule = () => {
      if (disposed || video.paused || video.ended || document.hidden) {
        return;
      }
      if (typeof video.requestVideoFrameCallback === "function") {
        rvfcId = video.requestVideoFrameCallback(tick);
      } else {
        rafId = requestAnimationFrame(tick);
      }
    };

    const onPlay = () => {
      cancelLoops();
      drawFrame();
      schedule();
    };
    const onStill = () => {
      cancelLoops();
      drawFrame(); // paused seek: draw the single nearest observed frame
    };
    const onEndOrError = () => {
      cancelLoops();
      clearCanvas();
    };
    const onResize = () => {
      drawFrame();
    };
    const onVisibility = () => {
      if (document.hidden) {
        cancelLoops();
      } else {
        onStill();
        schedule();
      }
    };
    const handleError = () => {
      onEndOrError();
      onVideoErrorRef.current();
    };

    video.addEventListener("play", onPlay);
    video.addEventListener("playing", onPlay);
    video.addEventListener("pause", onStill);
    video.addEventListener("seeked", onStill);
    video.addEventListener("timeupdate", drawFrame);
    video.addEventListener("ended", onEndOrError);
    video.addEventListener("error", handleError);
    video.addEventListener("emptied", onEndOrError);
    document.addEventListener("visibilitychange", onVisibility);

    let observer: ResizeObserver | null = null;
    if (typeof ResizeObserver !== "undefined") {
      observer = new ResizeObserver(onResize);
      observer.observe(video);
    }

    return () => {
      disposed = true;
      cancelLoops();
      video.removeEventListener("play", onPlay);
      video.removeEventListener("playing", onPlay);
      video.removeEventListener("pause", onStill);
      video.removeEventListener("seeked", onStill);
      video.removeEventListener("timeupdate", drawFrame);
      video.removeEventListener("ended", onEndOrError);
      video.removeEventListener("error", handleError);
      video.removeEventListener("emptied", onEndOrError);
      document.removeEventListener("visibilitychange", onVisibility);
      if (observer) {
        observer.disconnect();
      }
    };
  }, [analysisId, drawFrame, clearCanvas]);

  const ready = status.kind === "ready";

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
      <figure style={{ margin: 0 }}>
        <div
          style={{
            position: "relative",
            width: "100%",
            background: "#0a0a0a",
            borderRadius: 8,
            overflow: "hidden",
          }}
        >
          <video
            id="mxr-analysis-video"
            data-analysis-video
            ref={videoRef}
            src={`/api/analyses/${encodeURIComponent(analysisId)}/artifacts/proxy`}
            controls
            playsInline
            preload="metadata"
            style={{
              display: "block",
              width: "100%",
              maxHeight: 480,
              objectFit: "contain",
              background: "#0a0a0a",
            }}
          />
          <canvas
            ref={canvasRef}
            aria-hidden="true"
            style={{
              position: "absolute",
              inset: 0,
              width: "100%",
              height: "100%",
              pointerEvents: "none",
            }}
          />
        </div>
        <figcaption
          style={{
            marginTop: 6,
            fontSize: 12,
            lineHeight: 1.4,
            color: "#5b657d",
          }}
        >
          Your actual uploaded video. Tap a segment below to jump to it.
        </figcaption>
      </figure>
      <div
        style={{
          display: "flex",
          alignItems: "center",
          gap: 12,
          flexWrap: "wrap",
          fontSize: 13,
          color: "#334155",
        }}
      >
        <label style={{ display: "inline-flex", alignItems: "center", gap: 6 }}>
          <input
            type="checkbox"
            checked={overlayOn && ready}
            disabled={!ready}
            onChange={(e) => {
              setOverlayOn(e.target.checked);
              if (!e.target.checked) {
                clearCanvas();
              } else {
                drawFrame();
              }
            }}
          />
          Pose overlay
        </label>
        {ready && overlayOn && (
          <span
            style={{
              padding: "2px 8px",
              borderRadius: 9999,
              background: "#e8eefc",
              color: COBALT,
              border: "1px solid #c3d2f5",
              fontWeight: 600,
            }}
          >
            Estimated pose
          </span>
        )}
        {status.kind === "loading" && <span>Loading pose data…</span>}
        {status.kind === "unavailable" && (
          <span role="status">Pose overlay unavailable: {status.reason}</span>
        )}
      </div>
    </div>
  );
}
