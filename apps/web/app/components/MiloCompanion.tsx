"use client";

import {
  CSSProperties,
  ReactElement,
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
} from "react";
import styles from "./MiloCompanion.module.css";
import {
  DEFAULT_MANIFEST,
  MiloLayerManifest,
  MiloVisualState,
  resolveAssetStatus,
} from "../lib/milo-assets";

type MiloSize = "hero" | "compact";

export interface MiloCompanionProps {
  state: MiloVisualState;
  eventKey: string;
  size?: MiloSize;
  hidden?: boolean;
  reducedMotion?: boolean;
  fallbackSrc?: string;
  layers?: MiloLayerManifest;
  onAssetStatusChange?: (status: "provisional" | "ready" | "failed") => void;
}

interface SeenKeyEntry {
  ts: number;
}

const SEEN_KEY_LIMIT = 128;
const CHEER_AUTO_RETURN_MS = 1600;
const SEEN_STORAGE_KEY = "milo.seenEventKeys";

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function readSeenKeys(): Map<string, SeenKeyEntry> {
  if (typeof window === "undefined") return new Map();
  try {
    const raw = window.sessionStorage.getItem(SEEN_STORAGE_KEY);
    if (!raw) return new Map();
    const parsed: unknown = JSON.parse(raw);
    if (!isRecord(parsed)) return new Map();
    const map = new Map<string, SeenKeyEntry>();
    let added = 0;
    for (const [k, v] of Object.entries(parsed)) {
      if (added >= SEEN_KEY_LIMIT) break;
      if (typeof v === "number" && Number.isFinite(v)) {
        map.set(k, { ts: v });
        added += 1;
      }
    }
    return map;
  } catch {
    return new Map();
  }
}

function writeSeenKeys(map: Map<string, SeenKeyEntry>): void {
  if (typeof window === "undefined") return;
  try {
    const obj: Record<string, number> = {};
    let i = 0;
    for (const [k, v] of map.entries()) {
      if (i >= SEEN_KEY_LIMIT) break;
      obj[k] = v.ts;
      i += 1;
    }
    window.sessionStorage.setItem(SEEN_STORAGE_KEY, JSON.stringify(obj));
  } catch {
    /* ignore quota / privacy errors */
  }
}

function tryMarkSeen(
  map: Map<string, SeenKeyEntry>,
  key: string,
): boolean {
  if (!key) return false;
  if (map.has(key)) return false;
  map.set(key, { ts: Date.now() });
  while (map.size > SEEN_KEY_LIMIT) {
    const oldest = map.keys().next().value;
    if (!oldest) break;
    map.delete(oldest);
  }
  writeSeenKeys(map);
  return true;
}

interface Decision {
  visual: MiloVisualState;
  cheer: boolean;
}

function decideVisual(input: {
  state: MiloVisualState;
  eventKey: string;
  hidden: boolean;
  reducedMotion: boolean;
  assetStatus: "provisional" | "ready" | "failed";
  lastEventKey: string;
  lastReactionAt: number;
  now: number;
}): Decision {
  const {
    state,
    eventKey,
    hidden,
    reducedMotion,
    assetStatus,
    lastEventKey,
    lastReactionAt,
    now,
  } = input;

  if (hidden || reducedMotion) {
    return { visual: "static", cheer: false };
  }
  if (assetStatus === "failed") {
    return { visual: "static", cheer: false };
  }
  if (state === "static") {
    return { visual: "static", cheer: false };
  }
  if (state === "attentive") {
    return { visual: "attentive", cheer: false };
  }
  if (state === "cheer") {
    const isNewKey = !!eventKey && eventKey !== lastEventKey;
    return {
      visual: isNewKey ? "cheer" : "idle",
      cheer: isNewKey,
    };
  }
  return { visual: "idle", cheer: false };
}

interface RequiredAsset {
  src: string;
  key: string;
}

function collectRequiredAssets(
  manifest: MiloLayerManifest,
  fallback: string,
  showFallback: boolean,
): RequiredAsset[] {
  const list: RequiredAsset[] = [];
  if (showFallback) {
    if (fallback) list.push({ src: fallback, key: "fallback" });
    return list;
  }
  if (manifest.base) list.push({ src: manifest.base, key: "base" });
  if (manifest.head?.src) list.push({ src: manifest.head.src, key: "head" });
  if (manifest.paw?.src) list.push({ src: manifest.paw.src, key: "paw" });
  return list;
}

export function MiloCompanion({
  state,
  eventKey,
  size = "compact",
  hidden = false,
  reducedMotion = false,
  fallbackSrc,
  layers,
  onAssetStatusChange,
}: MiloCompanionProps): ReactElement | null {
  const manifest = layers ?? DEFAULT_MANIFEST;
  const fallback = fallbackSrc ?? manifest.fallback;

  const [assetStatus, setAssetStatus] = useState<"provisional" | "ready" | "failed">(
    resolveAssetStatus(manifest),
  );
  const [failedSrc, setFailedSrc] = useState<string | null>(null);
  const [visual, setVisual] = useState<MiloVisualState>("idle");
  const [cheerNonce, setCheerNonce] = useState(0);
  const [systemReduced, setSystemReduced] = useState<boolean>(false);
  const [pageVisible, setPageVisible] = useState<boolean>(
    typeof document === "undefined" ? true : document.visibilityState !== "hidden",
  );

  const seenKeysRef = useRef<Map<string, SeenKeyEntry>>(readSeenKeys());
  const cheerTimerRef = useRef<number | null>(null);
  const lastReactionAtRef = useRef<number>(0);
  const lastEventKeyRef = useRef<string>("");
  const lastDecisionRef = useRef<Decision | null>(null);
  const rafRef = useRef<number | null>(null);
  const mountedRef = useRef(true);
  const loadedRef = useRef<Set<string>>(new Set());
  const failedRef = useRef<Set<string>>(new Set());
  const stageRef = useRef<HTMLDivElement | null>(null);

  const effectiveReduced = !!reducedMotion || systemReduced || !pageVisible;

  const showFallback = assetStatus === "failed" || !manifest.base;
  const requiredAssets = useMemo(
    () => collectRequiredAssets(manifest, fallback, showFallback),
    [manifest, fallback, showFallback],
  );

  // Reset asset tracking whenever the manifest or fallback changes intentionally.
  // Single bounded effect: resets refs, sets provisional/failed, then on next rAF
  // inspects actual <img> elements in the stage to populate loadedRef (catches
  // cached loads that fired before this effect ran). No polling, no new Image().
  useEffect(() => {
    loadedRef.current = new Set();
    failedRef.current = new Set();
    setFailedSrc(null);
    const initial = resolveAssetStatus(manifest);
    setAssetStatus(initial === "ready" ? "provisional" : initial);

    if (typeof window === "undefined") return;
    const assetFrame = requestAnimationFrame(() => {
      if (!mountedRef.current) return;
      const stage = stageRef.current;
      if (!stage) return;
      const imgs = stage.querySelectorAll<HTMLImageElement>("img");
      imgs.forEach((img) => {
        if (img.complete && img.naturalWidth > 0) {
          const source = img.getAttribute("src");
          if (source) loadedRef.current.add(source);
        }
      });
      const showFallbackNow = (resolveAssetStatus(manifest) === "failed") || !manifest.base;
      const requiredSrcs: string[] = [];
      if (showFallbackNow) {
        if (fallback) requiredSrcs.push(fallback);
      } else {
        if (manifest.base) requiredSrcs.push(manifest.base);
        if (manifest.head?.src) requiredSrcs.push(manifest.head.src);
        if (manifest.paw?.src) requiredSrcs.push(manifest.paw.src);
      }
      const allLoaded = requiredSrcs.length > 0 && requiredSrcs.every((s) => loadedRef.current.has(s));
      const manifestReady = resolveAssetStatus(manifest) === "ready";
      if (allLoaded && manifestReady) {
        setAssetStatus((prev) => (prev === "failed" ? prev : "ready"));
      }
    });

    return () => {
      cancelAnimationFrame(assetFrame);
    };
  }, [manifest, fallback]);

  useEffect(() => {
    onAssetStatusChange?.(assetStatus);
  }, [assetStatus, onAssetStatusChange]);

  useEffect(() => {
    mountedRef.current = true;
    return () => {
      mountedRef.current = false;
      if (rafRef.current !== null) {
        cancelAnimationFrame(rafRef.current);
        rafRef.current = null;
      }
      if (cheerTimerRef.current !== null) {
        window.clearTimeout(cheerTimerRef.current);
        cheerTimerRef.current = null;
      }
    };
  }, []);

  useEffect(() => {
    if (typeof window === "undefined") return;
    const mq = window.matchMedia("(prefers-reduced-motion: reduce)");
    const apply = () => {
      setSystemReduced(mq.matches);
    };
    apply();
    mq.addEventListener("change", apply);
    return () => mq.removeEventListener("change", apply);
  }, []);

  useEffect(() => {
    if (typeof document === "undefined") return;
    const apply = () => {
      setPageVisible(document.visibilityState !== "hidden");
    };
    apply();
    document.addEventListener("visibilitychange", apply);
    return () => {
      document.removeEventListener("visibilitychange", apply);
    };
  }, []);

  const handleAssetError = useCallback(
    (src: string) => {
      if (failedRef.current.has(src)) return;
      failedRef.current.add(src);
      if (failedSrc !== src) setFailedSrc(src);
      setAssetStatus("failed");
    },
    [failedSrc],
  );

  const handleAssetLoad = useCallback(
    (src: string) => {
      if (failedRef.current.has(src)) return;
      if (assetStatus === "failed") return;
      loadedRef.current.add(src);
      // Only mark ready when every required asset has loaded successfully.
      const allLoaded = requiredAssets.every((a) => loadedRef.current.has(a.src));
      if (allLoaded) {
        setAssetStatus((prev) => (prev === "failed" ? prev : "ready"));
      }
    },
    [requiredAssets, assetStatus],
  );

  // Guard: if a load fires after we already failed (e.g. fallback loaded but
  // manifest is still failed), do not flip back to ready.
  const handleAssetLoadGuarded = useCallback(
    (src: string) => {
      if (assetStatus === "failed") return;
      if (failedRef.current.has(src)) return;
      handleAssetLoad(src);
    },
    [assetStatus, handleAssetLoad],
  );

  useEffect(() => {
    if (typeof window === "undefined") return;
    if (rafRef.current !== null) {
      cancelAnimationFrame(rafRef.current);
      rafRef.current = null;
    }
    rafRef.current = requestAnimationFrame(() => {
      rafRef.current = null;
      if (!mountedRef.current) return;
      const now = Date.now();
      const decision = decideVisual({
        state,
        eventKey,
        hidden,
        reducedMotion: effectiveReduced,
        assetStatus,
        lastEventKey: lastEventKeyRef.current,
        lastReactionAt: lastReactionAtRef.current,
        now,
      });

      const prev = lastDecisionRef.current;
      const sameVisual = prev?.visual === decision.visual;
      const sameCheer = prev?.cheer === decision.cheer;
      const sameEventKey = prev && lastEventKeyRef.current === eventKey;
      lastDecisionRef.current = decision;

      if (sameVisual && sameCheer && sameEventKey) return;

      setVisual(decision.visual);

      if (decision.cheer) {
        if (effectiveReduced || hidden) {
          setVisual("idle");
          lastDecisionRef.current = { visual: "idle", cheer: false };
          return;
        }
        const firstTime = tryMarkSeen(seenKeysRef.current, eventKey);
        if (!firstTime) {
          setVisual("idle");
          lastDecisionRef.current = { visual: "idle", cheer: false };
          return;
        }
        lastReactionAtRef.current = now;
        lastEventKeyRef.current = eventKey;
        setCheerNonce((n) => n + 1);
        if (cheerTimerRef.current !== null) {
          window.clearTimeout(cheerTimerRef.current);
        }
        cheerTimerRef.current = window.setTimeout(() => {
          cheerTimerRef.current = null;
          if (!mountedRef.current) return;
          setVisual("idle");
          lastDecisionRef.current = { visual: "idle", cheer: false };
        }, CHEER_AUTO_RETURN_MS);
      } else if (cheerTimerRef.current !== null && decision.visual !== "cheer") {
        window.clearTimeout(cheerTimerRef.current);
        cheerTimerRef.current = null;
      }
    });
  }, [state, eventKey, hidden, effectiveReduced, assetStatus]);

  if (hidden) return null;

  const sizeClass = size === "hero" ? styles.hero : styles.compact;
  const visualClass =
    visual === "idle"
      ? styles.idle
      : visual === "attentive"
        ? styles.attentive
        : visual === "cheer"
          ? styles.cheer
          : styles.static;

  const motionClass = effectiveReduced ? styles.reducedMotion : "";

  const containerStyle: CSSProperties = {
    width: size === "hero" ? "min(280px, 100%)" : "min(96px, 100%)",
    aspectRatio: "1 / 1",
  };

  const baseSrc = showFallback ? fallback : manifest.base;
  const baseBroken = showFallback && !!failedSrc && failedSrc === baseSrc;

  const headSrc = manifest.head?.src;
  const pawSrc = manifest.paw?.src;

  const headStyle: CSSProperties | undefined = manifest.head
    ? {
        left: `${manifest.head.left}%`,
        top: `${manifest.head.top}%`,
        width: `${manifest.head.width}%`,
        height: "auto",
        transformOrigin: `${manifest.head.originX}% ${manifest.head.originY}%`,
      }
    : undefined;

  const pawStyle: CSSProperties | undefined = manifest.paw
    ? {
        left: `${manifest.paw.left}%`,
        top: `${manifest.paw.top}%`,
        width: `${manifest.paw.width}%`,
        height: "auto",
        transformOrigin: `${manifest.paw.originX}% ${manifest.paw.originY}%`,
      }
    : undefined;

  const showHead = !!headSrc && !showFallback;
  const showPaw = !!pawSrc && !showFallback;

  return (
    <div
      className={`${styles.root} ${sizeClass} ${visualClass} ${motionClass}`}
      style={containerStyle}
      data-state={effectiveReduced ? "static" : visual}
      data-asset-status={assetStatus}
      data-cheer-nonce={cheerNonce}
      aria-hidden="true"
    >
      <div className={styles.stage} ref={stageRef}>
        {baseSrc && !baseBroken ? (
          <img
            className={styles.layer}
            src={baseSrc}
            alt=""
            role="presentation"
            draggable={false}
            onError={() => handleAssetError(baseSrc)}
            onLoad={() => handleAssetLoadGuarded(baseSrc)}
          />
        ) : (
          <span data-milo-fallback="true">
            Milo
          </span>
        )}
        {showHead && headSrc ? (
          <img
            className={`${styles.layer} ${styles.head}`}
            style={headStyle}
            src={headSrc}
            alt=""
            role="presentation"
            draggable={false}
            onError={() => handleAssetError(headSrc)}
            onLoad={() => handleAssetLoadGuarded(headSrc)}
          />
        ) : null}
        {showPaw && pawSrc ? (
          <img
            className={`${styles.layer} ${styles.paw}`}
            style={pawStyle}
            src={pawSrc}
            alt=""
            role="presentation"
            draggable={false}
            onError={() => handleAssetError(pawSrc)}
            onLoad={() => handleAssetLoad(pawSrc)}
          />
        ) : null}
      </div>
    </div>
  );
}

export default MiloCompanion;
