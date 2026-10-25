"use client";

import {
  ChangeEvent,
  ReactElement,
  useCallback,
  useEffect,
  useRef,
  useState,
} from "react";
import MiloCompanion from "../components/MiloCompanion";
import {
  DEFAULT_MANIFEST,
  MiloLayerManifest,
  MiloVisualState,
  resolveAssetStatus,
} from "../lib/milo-assets";

type SizeChoice = "hero" | "compact";
type AssetStatus = "provisional" | "ready" | "failed";

interface PreviewState {
  visual: MiloVisualState;
  eventKey: string;
  size: SizeChoice;
  hidden: boolean;
  reducedMotion: boolean;
  failedAsset: boolean;
  stopped: boolean;
  assetStatus: AssetStatus;
}

const INITIAL: PreviewState = {
  visual: "idle",
  eventKey: "preview-init",
  size: "hero",
  hidden: false,
  reducedMotion: false,
  failedAsset: false,
  stopped: false,
  assetStatus: resolveAssetStatus(DEFAULT_MANIFEST),
};

function nextKey(prev: string): string {
  return `preview-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;
}

export default function MiloPreviewPage(): ReactElement {
  const [state, setState] = useState<PreviewState>(INITIAL);
  const [layers, setLayers] = useState<MiloLayerManifest>(DEFAULT_MANIFEST);
  const [fallbackSrc, setFallbackSrc] = useState<string>(DEFAULT_MANIFEST.fallback);
  const eventCounterRef = useRef(0);

  useEffect(() => {
    if (typeof window === "undefined") return;
    const mq = window.matchMedia("(prefers-reduced-motion: reduce)");
    const apply = () => {
      setState((s) => ({ ...s, reducedMotion: mq.matches }));
    };
    apply();
    mq.addEventListener("change", apply);
    return () => mq.removeEventListener("change", apply);
  }, []);

  const trigger = useCallback((visual: MiloVisualState) => {
    eventCounterRef.current += 1;
    setState((s) => ({
      ...s,
      visual,
      stopped: false,
      eventKey: nextKey(`${visual}-${eventCounterRef.current}`),
    }));
  }, []);

  const onSize = useCallback((e: ChangeEvent<HTMLSelectElement>) => {
    setState((s) => ({ ...s, size: e.target.value as SizeChoice }));
  }, []);

  const onReducedMotion = useCallback((e: ChangeEvent<HTMLInputElement>) => {
    setState((s) => ({ ...s, reducedMotion: e.target.checked }));
  }, []);

  const onHidden = useCallback((e: ChangeEvent<HTMLInputElement>) => {
    setState((s) => ({ ...s, hidden: e.target.checked }));
  }, []);

  const onFailedAsset = useCallback((e: ChangeEvent<HTMLInputElement>) => {
    const failed = e.target.checked;
    setState((s) => ({
      ...s,
      failedAsset: failed,
      assetStatus: failed ? "failed" : resolveAssetStatus(layers),
    }));
  }, [layers]);

  const onStop = useCallback(() => {
    setState((s) => ({ ...s, visual: "static", stopped: true }));
  }, []);

  const onRetry = useCallback(() => {
    setState((s) => ({
      ...s,
      visual: "cheer",
      stopped: false,
      failedAsset: false,
      assetStatus: resolveAssetStatus(layers),
      eventKey: s.eventKey,
    }));
  }, [layers]);

  const onAssetStatus = useCallback((status: AssetStatus) => {
    setState((s) => (s.assetStatus === status ? s : { ...s, assetStatus: status }));
  }, []);

  const onLayersChange = useCallback((e: ChangeEvent<HTMLTextAreaElement>) => {
    const raw = e.target.value.trim();
    if (!raw) {
      setLayers(DEFAULT_MANIFEST);
      return;
    }
    try {
      const parsed = JSON.parse(raw) as MiloLayerManifest;
      if (
        parsed &&
        typeof parsed === "object" &&
        typeof parsed.version === "number"
      ) {
        setLayers(parsed);
      }
    } catch {
      /* keep previous manifest on parse error */
    }
  }, []);

  const onFallbackChange = useCallback((e: ChangeEvent<HTMLInputElement>) => {
    setFallbackSrc(e.target.value);
  }, []);

  const statusLabel =
    state.assetStatus === "ready"
      ? "Asset status: ready"
      : state.assetStatus === "failed"
        ? "Asset status: failed — using fallback"
        : "Asset status: provisional (placeholder layers)";

  return (
    <main
      style={{
        padding: "24px",
        fontFamily:
          "system-ui, -apple-system, Segoe UI, Roboto, sans-serif",
        maxWidth: 960,
        margin: "0 auto",
        color: "#1f2937",
      }}
    >
      <h1 style={{ fontSize: 20, marginBottom: 4 }}>Milo Pip — isolated preview</h1>
      <p style={{ marginTop: 0, color: "#4b5563", fontSize: 13 }}>
        Standalone renderer harness. No upload, no API, no recording. Status and
        copy live in this parent; the companion itself is decorative.
      </p>

      <section
        aria-label="Preview"
        style={{
          display: "flex",
          gap: 24,
          alignItems: "flex-start",
          flexWrap: "wrap",
          marginTop: 16,
        }}
      >
        <div
          style={{
            width: 320,
            minHeight: 320,
            border: "1px dashed #cbd5e1",
            borderRadius: 12,
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            background: "#f8fafc",
            padding: 12,
          }}
        >
          {state.hidden ? (
            <span style={{ color: "#64748b", fontSize: 13 }}>
              Companion hidden
            </span>
          ) : (
            <MiloCompanion
              state={state.visual}
              eventKey={state.eventKey}
              size={state.size}
              hidden={state.hidden}
              reducedMotion={state.reducedMotion}
              fallbackSrc={fallbackSrc}
              layers={state.failedAsset ? { ...layers, status: "failed" } : layers}
              onAssetStatusChange={onAssetStatus}
            />
          )}
        </div>

        <div style={{ flex: 1, minWidth: 280 }}>
          <div
            role="status"
            aria-live="polite"
            style={{
              fontSize: 13,
              padding: "8px 10px",
              borderRadius: 8,
              background:
                state.assetStatus === "failed"
                  ? "#fef2f2"
                  : state.assetStatus === "ready"
                    ? "#ecfdf5"
                    : "#fffbeb",
              color:
                state.assetStatus === "failed"
                  ? "#991b1b"
                  : state.assetStatus === "ready"
                    ? "#065f46"
                    : "#92400e",
              marginBottom: 12,
            }}
          >
            {statusLabel}
          </div>

          <div style={{ display: "flex", flexWrap: "wrap", gap: 8 }}>
            <button
              type="button"
              onClick={() => trigger("idle")}
              style={btnStyle}
            >
              Idle
            </button>
            <button
              type="button"
              onClick={() => trigger("attentive")}
              style={btnStyle}
            >
              Attentive
            </button>
            <button
              type="button"
              onClick={() => trigger("cheer")}
              style={btnStyle}
            >
              Cheer
            </button>
            <button
              type="button"
              onClick={onStop}
              style={{ ...btnStyle, background: "#e2e8f0" }}
            >
              Stop
            </button>
            <button
              type="button"
              onClick={onRetry}
              style={{ ...btnStyle, background: "#fde68a" }}
            >
              Retry (same key)
            </button>
          </div>

          <fieldset
            style={{
              marginTop: 16,
              border: "1px solid #e2e8f0",
              borderRadius: 8,
              padding: 12,
            }}
          >
            <legend style={{ fontSize: 12, color: "#475569" }}>Display</legend>
            <label style={fieldStyle}>
              Size{" "}
              <select value={state.size} onChange={onSize}>
                <option value="hero">hero (280px)</option>
                <option value="compact">compact (96px)</option>
              </select>
            </label>
            <label style={fieldStyle}>
              <input
                type="checkbox"
                checked={state.reducedMotion}
                onChange={onReducedMotion}
              />{" "}
              Reduced motion
            </label>
            <label style={fieldStyle}>
              <input
                type="checkbox"
                checked={state.hidden}
                onChange={onHidden}
              />{" "}
              Hidden
            </label>
            <label style={fieldStyle}>
              <input
                type="checkbox"
                checked={state.failedAsset}
                onChange={onFailedAsset}
              />{" "}
              Failed asset (force fallback)
            </label>
            <label style={{ ...fieldStyle, display: "block" }}>
              Fallback src{" "}
              <input
                type="text"
                value={fallbackSrc}
                onChange={onFallbackChange}
                style={{ width: "100%", marginTop: 4 }}
              />
            </label>
          </fieldset>

          <details style={{ marginTop: 16 }}>
            <summary style={{ cursor: "pointer", fontSize: 13 }}>
              Layer manifest (JSON)
            </summary>
            <textarea
              defaultValue={JSON.stringify(DEFAULT_MANIFEST, null, 2)}
              onChange={onLayersChange}
              style={{
                width: "100%",
                height: 180,
                marginTop: 8,
                fontFamily: "ui-monospace, SFMono-Regular, Menlo, monospace",
                fontSize: 12,
              }}
            />
          </details>

          <p style={{ marginTop: 16, fontSize: 12, color: "#64748b" }}>
            Current visual: <strong>{state.visual}</strong>. Event key:{" "}
            <code style={{ fontSize: 11 }}>{state.eventKey}</code>.
          </p>
        </div>
      </section>
    </main>
  );
}

const btnStyle: React.CSSProperties = {
  padding: "6px 12px",
  borderRadius: 6,
  border: "1px solid #cbd5e1",
  background: "#f1f5f9",
  cursor: "pointer",
  fontSize: 13,
};

const fieldStyle: React.CSSProperties = {
  display: "flex",
  alignItems: "center",
  gap: 6,
  fontSize: 13,
  marginRight: 12,
  marginBottom: 6,
};
