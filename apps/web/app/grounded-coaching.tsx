"use client";

import { useEffect, useRef, useState } from "react";
import type { components } from "../generated/api";

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

const SEGMENT_PREFIX = /^Segment (\d+) \(/;

function Observation({ text, reps }: { text: string; reps: Rep[] }) {
  const m = SEGMENT_PREFIX.exec(text);
  const rep = m ? reps.find((r) => r.ordinal === Number(m[1])) : undefined;
  return (
    <li style={{ margin: ".3rem 0" }}>
      {text}
      {rep && (
        <button
          type="button"
          className="btn ghost sm"
          style={{ marginLeft: ".5rem" }}
          onClick={() => seekTo(rep.start_s)}
          aria-label={`Replay segment ${rep.ordinal} from ${rep.start_s.toFixed(2)} seconds`}
        >
          ▶ Replay
        </button>
      )}
    </li>
  );
}

const URL_RE = /(https:\/\/[^\s)]+)/g;

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

export default function GroundedCoaching({ analysisId, reps }: { analysisId: string; reps: Rep[] }) {
  const [state, setState] = useState<State>({ kind: "idle" });
  const ctrlRef = useRef<AbortController | null>(null);

  useEffect(() => {
    setState({ kind: "idle" });
    ctrlRef.current?.abort();
    ctrlRef.current = null;
    return () => ctrlRef.current?.abort();
  }, [analysisId]);

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

  return (
    <div className="card" style={{ marginBottom: "1rem" }} aria-label="Grounded coaching">
      <div className="row" style={{ justifyContent: "space-between", alignItems: "baseline" }}>
        <h3 style={{ margin: 0 }}>Grounded coaching</h3>
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
      {state.kind === "ok" && state.result.status === "ok" && (
        <div style={{ marginTop: ".5rem" }}>
          {state.result.summary && !state.result.observations.includes(state.result.summary) && <p style={{ margin: ".2rem 0 .5rem" }}>{state.result.summary}</p>}
          {state.result.observations.length > 0 && (
            <ul style={{ margin: ".2rem 0 .5rem", paddingLeft: "1.2rem" }}>
              {state.result.observations.map((o, i) => <Observation key={i} text={o} reps={reps} />)}
            </ul>
          )}
          {state.result.next_set_cue && (
            <p style={{ margin: ".2rem 0 .5rem" }}><strong>Next set cue:</strong> {state.result.next_set_cue}</p>
          )}
          {state.result.limitations.length > 0 && (
            <details>
              <summary className="muted" style={{ cursor: "pointer" }}>Limitations &amp; sources</summary>
              <ul className="muted" style={{ margin: ".4rem 0 0", paddingLeft: "1.2rem" }}>
                {state.result.limitations.map((l, i) => <Limitation key={i} text={l} />)}
              </ul>
            </details>
          )}
        </div>
      )}
    </div>
  );
}
