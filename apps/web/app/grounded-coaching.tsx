"use client";

import { useEffect, useRef, useState } from "react";
import type { components } from "../generated/api";
import SessionThumbnail from "./components/SessionThumbnail";

type Rep = components["schemas"]["Rep"];
type CoachingResult = components["schemas"]["CoachingResult"];

type State =
  | { kind: "idle" }
  | { kind: "busy" }
  | { kind: "ok"; result: CoachingResult }
  | { kind: "error"; message: string };

async function readError(res: Response): Promise<string> {
  try {
    const data: unknown = await res.json();
    if (typeof data === "object" && data !== null) {
      const d = data as { message?: unknown; detail?: unknown };
      if (typeof d.message === "string" && d.message) return d.message;
      if (typeof d.detail === "string" && d.detail) return d.detail;
    }
  } catch { /* keep status message */ }
  if (res.status === 429) return "Daily coaching quota reached (429). Please try again tomorrow — no automatic retry is attempted.";
  return `Request failed (${res.status})`;
}

function isCoaching(data: unknown): data is CoachingResult {
  if (typeof data !== "object" || data === null) return false;
  const d = data as { status?: unknown };
  return d.status === "ok" || d.status === "unavailable";
}

function seekTo(seconds: number): void {
  window.dispatchEvent(new CustomEvent("mxr:seek-source", { detail: { seconds } }));
}

// Strict validated prefix: 'Segment N (' where N must match an ACTUAL
// Rep.ordinal. No match → no replay association, never an invented one.
const SEGMENT_PREFIX = /^Segment (\d+) \(/;

function matchRep(text: string, reps: Rep[]): Rep | undefined {
  const m = SEGMENT_PREFIX.exec(text);
  if (!m) return undefined;
  const ordinal = Number(m[1]);
  if (!Number.isInteger(ordinal)) return undefined;
  return reps.find((r) => r.ordinal === ordinal);
}

function ReplayButton({ rep }: { rep: Rep }) {
  return (
    <button
      type="button"
      className="btn ghost sm"
      onClick={() => seekTo(rep.start_s)}
      aria-label={`Replay segment ${rep.ordinal} from ${rep.start_s.toFixed(2)} seconds`}
    >
      ▶ Replay this moment
    </button>
  );
}

const URL_RE = /(https:\/\/[^\s)]+)/g;

// Source URLs come ONLY from actual limitations strings supplied by the
// response; never constructed from narrative text or invented identifiers.
function Limitation({ text }: { text: string }) {
  const parts = text.split(URL_RE);
  return (
    <li style={{ margin: ".3rem 0" }}>
      {parts.map((p, i) =>
        p.startsWith("https://") ? (
          <a key={i} href={p} target="_blank" rel="noopener noreferrer">{p}</a>
        ) : (
          <span key={i}>{p}</span>
        ),
      )}
    </li>
  );
}

const highlightCardStyle: React.CSSProperties = {
  display: "flex",
  gap: "0.85rem",
  alignItems: "flex-start",
  flexWrap: "wrap",
  marginTop: ".5rem",
  padding: "0.85rem",
  border: "1px solid #e2e8f4",
  borderRadius: 14,
  background: "#f7f9fd",
};

const highlightBodyStyle: React.CSSProperties = {
  flex: "1 1 220px",
  minWidth: 0,
};

export default function GroundedCoaching({ analysisId, reps }: { analysisId: string; reps: Rep[] }) {
  const [state, setState] = useState<State>({ kind: "idle" });
  const ctrlRef = useRef<AbortController | null>(null);

  useEffect(() => {
    setState({ kind: "idle" });
    ctrlRef.current?.abort();
    ctrlRef.current = null;
    return () => ctrlRef.current?.abort();
  }, [analysisId]);

  // Explicit paid POST only: fired solely from the user-initiated button.
  const generate = async () => {
    if (state.kind === "busy") return;
    const ctrl = new AbortController();
    ctrlRef.current = ctrl;
    setState({ kind: "busy" });
    try {
      const sessionRes = await fetch("/api/session", { credentials: "include", signal: ctrl.signal });
      if (!sessionRes.ok) throw new Error(await readError(sessionRes));
      const session = (await sessionRes.json()) as { csrf_token?: unknown };
      if (typeof session.csrf_token !== "string" || !session.csrf_token) {
        throw new Error("Session did not return a CSRF token.");
      }
      const res = await fetch(`/api/analyses/${analysisId}/coaching`, {
        method: "POST",
        credentials: "include",
        headers: { "X-CSRF-Token": session.csrf_token },
        signal: ctrl.signal,
      });
      if (!res.ok) throw new Error(await readError(res));
      const data: unknown = await res.json();
      if (!isCoaching(data)) throw new Error("The server returned an unexpected coaching format.");
      if (ctrl.signal.aborted) return;
      setState({ kind: "ok", result: data });
    } catch (e) {
      if ((e as Error).name === "AbortError" || ctrl.signal.aborted) return;
      setState({ kind: "error", message: (e as Error).message });
    }
  };

  const busy = state.kind === "busy";
  const okResult = state.kind === "ok" && state.result.status === "ok" ? state.result : null;
  // Exactly one highlight: the first ACTUAL observation, plus the optional
  // ACTUAL next-set cue. No fabricated second cue, no fabricated observation.
  const highlightObservation = okResult && okResult.observations.length > 0 ? okResult.observations[0] : null;
  const highlightRep = highlightObservation !== null ? matchRep(highlightObservation, reps) : undefined;
  const restObservations = okResult ? okResult.observations.slice(1) : [];

  return (
    <div className="card" style={{ marginBottom: "1rem" }} aria-label="Grounded coaching">
      <div className="row" style={{ justifyContent: "space-between", alignItems: "baseline" }}>
        <h3 style={{ margin: 0 }}>Coaching highlight</h3>
      </div>
      <p className="muted" style={{ margin: ".3rem 0 .6rem" }}>
        Turn this set’s measured observations into feedback, with replay links and a sourced cue for your next set.
      </p>
      {state.kind === "idle" && (
        <button type="button" className="btn" onClick={() => void generate()}>
          Generate coaching
        </button>
      )}
      {busy && (
        <button type="button" className="btn" disabled aria-busy="true">
          Generating…
        </button>
      )}
      {state.kind === "error" && (
        <div className="state bad" role="alert" style={{ marginTop: ".5rem" }}>
          <p style={{ margin: ".2rem 0 .5rem" }}>{state.message}</p>
          <button type="button" className="btn ghost sm" onClick={() => void generate()}>
            Generate coaching
          </button>
        </div>
      )}
      {state.kind === "ok" && state.result.status === "unavailable" && (
        <div className="state warn" role="status" style={{ marginTop: ".5rem" }}>
          <strong>Coaching model unavailable.</strong> The language model could not produce coaching for this report. Your deterministic measurements above are unaffected and remain available.
          {state.result.limitations.length > 0 && (
            <ul style={{ margin: ".4rem 0 0", paddingLeft: "1.2rem" }}>
              {state.result.limitations.map((l, i) => <Limitation key={i} text={l} />)}
            </ul>
          )}
        </div>
      )}
      {okResult && (
        <div style={{ marginTop: ".5rem" }}>
          {highlightObservation !== null ? (
            <div style={highlightCardStyle} aria-label="Coaching highlight">
              {highlightRep && (
                <SessionThumbnail
                  analysisId={analysisId}
                  sourceS={highlightRep.start_s}
                  label={`Segment ${highlightRep.ordinal}`}
                />
              )}
              <div style={highlightBodyStyle}>
                <p style={{ margin: 0, fontSize: "1rem", fontWeight: 600, lineHeight: 1.4, color: "#142039" }}>
                  {highlightObservation}
                </p>
                {okResult.next_set_cue && (
                  <p className="muted" style={{ margin: ".35rem 0 0" }}>
                    <strong>Next set cue:</strong> {okResult.next_set_cue}
                  </p>
                )}
                {highlightRep && (
                  <p style={{ margin: ".5rem 0 0" }}>
                    <ReplayButton rep={highlightRep} />
                  </p>
                )}
              </div>
            </div>
          ) : (
            <p className="muted" style={{ margin: ".2rem 0 .5rem" }}>
              {okResult.summary ?? "No specific observation was produced for this set. Your measured values above remain available."}
            </p>
          )}
          {okResult.summary && highlightObservation !== null && !okResult.observations.includes(okResult.summary) && (
            <p className="muted" style={{ margin: ".4rem 0 0" }}>{okResult.summary}</p>
          )}
          {restObservations.length > 0 && (
            <details style={{ marginTop: ".5rem" }}>
              <summary className="muted" style={{ cursor: "pointer", minHeight: 44 }}>
                All observations ({okResult.observations.length})
              </summary>
              <ul style={{ margin: ".3rem 0 0", paddingLeft: "1.2rem" }}>
                {restObservations.map((o, i) => {
                  const rep = matchRep(o, reps);
                  return (
                    <li key={i} style={{ margin: ".3rem 0" }}>
                      {o}
                      {rep && (
                        <span style={{ marginLeft: ".5rem" }}>
                          <ReplayButton rep={rep} />
                        </span>
                      )}
                    </li>
                  );
                })}
              </ul>
            </details>
          )}
          {okResult.limitations.length > 0 && (
            <details style={{ marginTop: ".5rem" }}>
              <summary className="muted" style={{ cursor: "pointer", minHeight: 44 }}>Limitations &amp; sources</summary>
              <ul className="muted" style={{ margin: ".4rem 0 0", paddingLeft: "1.2rem" }}>
                {okResult.limitations.map((l, i) => <Limitation key={i} text={l} />)}
              </ul>
            </details>
          )}
        </div>
      )}
    </div>
  );
}
