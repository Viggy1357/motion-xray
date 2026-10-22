"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import type { components } from "../generated/api";
import MovementReport from "./movement-report";

type PrototypeReport = components["schemas"]["PrototypeAnalysisResult"];

type SessionInfo = components["schemas"]["SessionInfo"];
type VideoAsset = components["schemas"]["VideoAsset"];
type AnalysisStatus = components["schemas"]["AnalysisStatus"];
type AnalysisResult = components["schemas"]["AnalysisResult"];
type ExerciseId = components["schemas"]["AnalysisCreateRequest"]["exercise_id"];

type View = "dashboard" | "new" | "results" | "history";

type LogEntry = {
  logId: string;
  analysisId: string | null;
  exercise: string;
  createdAt: string;
  detectedReps: number | null;
  loggedReps: number;
  load: string;
  notes: string;
};

type ActiveJob = { analysisId: string; exercise: string; createdAt: string };

const MAX_BYTES = 100 * 1024 * 1024;
const MAX_SECONDS = 60;
const LOG_KEY = "mxr.logs.v1";
const JOB_KEY = "mxr.activeJob.v1";
const NAME_KEY = "mxr.displayName.v1";

const EXERCISES: {
  id: ExerciseId;
  name: string;
  guidance: string;
  muscles: string[];
  art: "pull" | "curl" | "squat";
}[] = [
  { id: "lat_pulldown", name: "Lat pulldown", guidance: "Front view, full arms visible", muscles: ["Lats", "Biceps", "Upper back"], art: "pull" },
  { id: "dumbbell_curl", name: "Dumbbell curl", guidance: "Side or front, elbow in frame", muscles: ["Biceps", "Forearms"], art: "curl" },
  { id: "squat", name: "Squat", guidance: "Side view, hips and knees visible", muscles: ["Quads", "Glutes", "Core"], art: "squat" },
  { id: "incline_chest_press", name: "Incline dumbbell press", guidance: "Side view, bench and full arms visible in frame", muscles: ["Chest", "Shoulders", "Triceps"], art: "pull" },
];

function ExerciseArt({ kind }: { kind: "pull" | "curl" | "squat" }) {
  const stroke = "#0b1220";
  const common = { fill: "none", stroke, strokeWidth: 5, strokeLinecap: "round" as const };
  return (
    <svg viewBox="0 0 120 90" role="img" aria-hidden="true">
      {kind === "pull" && (
        <g {...common}>
          <line x1="20" y1="12" x2="100" y2="12" stroke="#9fc92c" />
          <circle cx="60" cy="26" r="7" />
          <line x1="60" y1="33" x2="60" y2="62" />
          <path d="M34 14 L46 40 M86 14 L74 40" />
          <path d="M60 62 L46 84 M60 62 L74 84" />
        </g>
      )}
      {kind === "curl" && (
        <g {...common}>
          <circle cx="52" cy="16" r="7" />
          <line x1="52" y1="23" x2="52" y2="56" />
          <path d="M52 30 L70 38 L64 20" stroke="#9fc92c" />
          <circle cx="64" cy="16" r="5" stroke="#9fc92c" />
          <path d="M52 56 L40 84 M52 56 L64 84" />
        </g>
      )}
      {kind === "squat" && (
        <g {...common}>
          <circle cx="46" cy="18" r="7" />
          <path d="M46 25 L58 48" />
          <path d="M58 48 L40 58 L46 80" stroke="#9fc92c" />
          <path d="M58 48 L74 60 L70 82" />
          <path d="M46 32 L66 40" />
        </g>
      )}
    </svg>
  );
}

function Silhouette({ active }: { active: string[] }) {
  const on = (g: string) => active.some((a) => a.toLowerCase().includes(g));
  const c = (g: string) => (on(g) ? "#c8f542" : "#2a3854");
  return (
    <svg className="sil" viewBox="0 0 120 200" role="img" aria-label="Illustrative silhouette highlighting muscle groups you have logged">
      <circle cx="60" cy="18" r="11" fill="#2a3854" />
      <path d="M60 30 C40 34 34 52 36 74 L44 76 C42 58 46 46 60 44 C74 46 78 58 76 76 L84 74 C86 52 80 34 60 30 Z" fill={c("lat") || c("back") ? c("x") : "#2a3854"} />
      <path d="M38 78 L34 118 L42 120 L48 82 Z" fill={on("biceps") ? "#c8f542" : "#2a3854"} />
      <path d="M82 78 L86 118 L78 120 L72 82 Z" fill={on("biceps") ? "#c8f542" : "#2a3854"} />
      <path d="M34 120 L32 146 L40 148 L42 122 Z" fill={on("forearm") ? "#c8f542" : "#2a3854"} />
      <path d="M86 120 L88 146 L80 148 L78 122 Z" fill={on("forearm") ? "#c8f542" : "#2a3854"} />
      <path d="M48 78 L72 78 L70 108 L50 108 Z" fill={on("core") ? "#c8f542" : "#2a3854"} />
      <path d="M50 110 L46 150 L54 152 L58 112 Z" fill={on("quad") || on("glute") ? "#c8f542" : "#2a3854"} />
      <path d="M70 110 L74 150 L66 152 L62 112 Z" fill={on("quad") || on("glute") ? "#c8f542" : "#2a3854"} />
      <path d="M46 152 L44 190 L52 190 L54 154 Z M74 152 L76 190 L68 190 L66 154 Z" fill="#2a3854" />
    </svg>
  );
}

function loadLogs(): LogEntry[] {
  try {
    const raw = localStorage.getItem(LOG_KEY);
    if (!raw) return [];
    const parsed: unknown = JSON.parse(raw);
    if (!Array.isArray(parsed)) return [];
    const uuid = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;
    const bounded = (v: unknown, max: number) => typeof v === "string" && v.length <= max;
    return parsed.filter((e): e is LogEntry => {
      if (typeof e !== "object" || e === null) return false;
      const l = e as LogEntry;
      return (
        bounded(l.logId, 64) &&
        (l.analysisId === null || (typeof l.analysisId === "string" && uuid.test(l.analysisId))) &&
        EXERCISES.some((x) => x.id === l.exercise) &&
        typeof l.createdAt === "string" && !Number.isNaN(Date.parse(l.createdAt)) &&
        Number.isInteger(l.loggedReps) && l.loggedReps >= 0 && l.loggedReps <= 10000 &&
        (l.detectedReps === null || (Number.isInteger(l.detectedReps) && l.detectedReps >= 0)) &&
        bounded(l.load, 200) &&
        bounded(l.notes, 2000)
      );
    });
  } catch {
    return [];
  }
}

function guessMime(file: File): string | null {
  if (["video/mp4", "video/quicktime", "video/webm"].includes(file.type)) return file.type;
  const ext = file.name.toLowerCase().split(".").pop();
  if (ext === "mp4" || ext === "m4v") return "video/mp4";
  if (ext === "mov") return "video/quicktime";
  if (ext === "webm") return "video/webm";
  return null;
}

function probeDuration(file: File): Promise<number | null> {
  return new Promise((resolve) => {
    const url = URL.createObjectURL(file);
    const v = document.createElement("video");
    const done = (d: number | null) => { URL.revokeObjectURL(url); resolve(d); };
    const timer = window.setTimeout(() => done(null), 5000);
    v.preload = "metadata";
    v.onloadedmetadata = () => { window.clearTimeout(timer); done(Number.isFinite(v.duration) ? v.duration : null); };
    v.onerror = () => { window.clearTimeout(timer); done(null); };
    v.src = url;
  });
}

async function readError(res: Response): Promise<string> {
  try {
    const data: unknown = await res.json();
    if (typeof data === "object" && data !== null) {
      const d = data as { detail?: unknown };
      if (typeof d.detail === "string") return d.detail;
      if (Array.isArray(d.detail)) return d.detail.map((x) => (x as { msg?: string }).msg ?? "Invalid value").join("; ");
    }
  } catch { /* fall through */ }
  return `Request failed (${res.status})`;
}

export default function Page() {
  const [view, setView] = useState<View>("dashboard");
  const [session, setSession] = useState<SessionInfo | null>(null);
  const [sessionErr, setSessionErr] = useState<string | null>(null);
  const [name, setName] = useState("");
  const [logs, setLogs] = useState<LogEntry[]>([]);
  const [job, setJob] = useState<ActiveJob | null>(null);
  const [status, setStatus] = useState<AnalysisStatus | null>(null);
  const [result, setResult] = useState<AnalysisResult | null>(null);
  const [resultErr, setResultErr] = useState<string | null>(null);
  const [movement, setMovement] = useState<PrototypeReport | null>(null);

  // New-set form state
  const [exercise, setExercise] = useState<ExerciseId>("lat_pulldown");
  const [file, setFile] = useState<File | null>(null);
  const [fileNote, setFileNote] = useState<string | null>(null);
  const [consent, setConsent] = useState(false);
  const [load, setLoad] = useState("");
  const [notes, setNotes] = useState("");
  const [uploadPct, setUploadPct] = useState<number | null>(null);
  const [uploadErr, setUploadErr] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [rate, setRate] = useState(1);
  const [editReps, setEditReps] = useState("");
  const [videoErr, setVideoErr] = useState(false);
  const [storageErr, setStorageErr] = useState<string | null>(null);
  const xhrRef = useRef<XMLHttpRequest | null>(null);
  const pollRef = useRef<AbortController | null>(null);
  const videoRef = useRef<HTMLVideoElement | null>(null);

  useEffect(() => {
    setLogs(loadLogs());
    try {
      setName(localStorage.getItem(NAME_KEY) ?? "");
      const raw = localStorage.getItem(JOB_KEY);
      if (raw) {
        const j: unknown = JSON.parse(raw);
        const a = j as ActiveJob;
        if (
          typeof j === "object" && j !== null &&
          typeof a.analysisId === "string" &&
          /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(a.analysisId) &&
          EXERCISES.some((x) => x.id === a.exercise) &&
          typeof a.createdAt === "string" && !Number.isNaN(Date.parse(a.createdAt))
        ) {
          setJob(a);
        }
      }
      const params = new URLSearchParams(window.location.search);
      const linkedId = params.get("analysis");
      const linkedExercise = params.get("exercise");
      if (linkedId && /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(linkedId)
          && linkedExercise && EXERCISES.some((x) => x.id === linkedExercise)) {
        setJob({ analysisId: linkedId, exercise: linkedExercise, createdAt: new Date().toISOString() });
        setView("results");
      }
    } catch { /* ignore corrupt local data */ }
    fetch("/api/session", { credentials: "include" })
      .then(async (r) => {
        if (!r.ok) throw new Error(await readError(r));
        return (await r.json()) as SessionInfo;
      })
      .then(setSession)
      .catch((e: Error) => setSessionErr(e.message));
  }, []);

  const persistLogs = (next: LogEntry[]) => {
    setLogs(next);
    try {
      localStorage.setItem(LOG_KEY, JSON.stringify(next));
      setStorageErr(null);
    } catch {
      setStorageErr("Could not write to this browser's storage — your history change was not saved.");
    }
  };

  const saveName = (v: string) => {
    setName(v);
    try { localStorage.setItem(NAME_KEY, v); } catch { /* ignore */ }
  };

  useEffect(() => { setMovement(null); }, [job?.analysisId]);

  // Poll active job every 2s; stop on terminal state.
  useEffect(() => {
    if (!job || !session) return;
    const ctrl = new AbortController();
    pollRef.current = ctrl;
    let timer = 0;
    const tick = async () => {
      try {
        const r = await fetch(`/api/analyses/${job.analysisId}`, { credentials: "include", signal: ctrl.signal });
        if (!r.ok) throw new Error(await readError(r));
        const s = (await r.json()) as AnalysisStatus;
        setStatus(s);
        if (s.state === "succeeded") {
          const rr = await fetch(`/api/analyses/${job.analysisId}/result`, { credentials: "include", signal: ctrl.signal });
          if (rr.ok) setResult((await rr.json()) as AnalysisResult);
          else setResultErr(await readError(rr));
          setView("results");
          return;
        }
        if (s.state === "failed" || s.state === "cancelled") {
          try { localStorage.removeItem(JOB_KEY); } catch { /* ignore */ }
          setView("results");
          return;
        }
        timer = window.setTimeout(tick, 2000);
      } catch (e) {
        if ((e as Error).name === "AbortError") return;
        setResultErr(`Lost connection while checking analysis status: ${(e as Error).message}. The analysis continues on the server — use Retry to resume updates.`);
      }
    };
    void tick();
    return () => { ctrl.abort(); window.clearTimeout(timer); };
  }, [job, session]);

  useEffect(() => {
    if (videoRef.current) videoRef.current.playbackRate = rate;
  }, [rate, result]);

  const onPick = async (f: File | null) => {
    setFile(null); setFileNote(null); setUploadErr(null);
    if (!f) return;
    if (f.size > MAX_BYTES) { setFileNote("This file is over the 100 MiB limit."); return; }
    if (!guessMime(f)) { setFileNote("Unsupported file type. Use MP4, MOV or WebM."); return; }
    const dur = await probeDuration(f);
    if (dur === null) {
      setFileNote("We could not preview this codec in your browser. You can still upload — the server will validate it.");
    } else if (dur > MAX_SECONDS) {
      setFileNote(`This clip is ${Math.round(dur)}s. The current limit is ${MAX_SECONDS}s per set — trim it and try again.`);
      return;
    }
    setFile(f);
  };

  const startUpload = () => {
    if (!file || !session || !consent) return;
    setBusy(true); setUploadErr(null); setUploadPct(0);
    const xhr = new XMLHttpRequest();
    xhrRef.current = xhr;
    xhr.open("POST", "/api/videos");
    xhr.withCredentials = true;
    xhr.setRequestHeader("Content-Type", guessMime(file) ?? "video/mp4");
    xhr.setRequestHeader("X-CSRF-Token", session.csrf_token);
    xhr.setRequestHeader("X-Upload-Consent", "true");
    xhr.upload.onprogress = (ev) => { if (ev.lengthComputable) setUploadPct(Math.round((ev.loaded / ev.total) * 100)); };
    xhr.onload = () => {
      void (async () => {
        if (xhr.status !== 201) {
          setBusy(false); setUploadPct(null);
          setUploadErr(`Upload failed: ${xhr.responseText ? String(xhr.responseText).slice(0, 300) : xhr.status}`);
          return;
        }
        try {
          const asset = JSON.parse(String(xhr.responseText)) as VideoAsset;
          const r = await fetch("/api/analyses", {
            method: "POST", credentials: "include",
            headers: { "Content-Type": "application/json", "X-CSRF-Token": session.csrf_token },
            body: JSON.stringify({ video_id: asset.id, exercise_id: exercise, request_key: crypto.randomUUID() }),
          });
          if (!r.ok) throw new Error(await readError(r));
          const s = (await r.json()) as AnalysisStatus;
          const j = { analysisId: s.id, exercise, createdAt: s.created_at };
          setJob(j); setStatus(s); setResult(null); setResultErr(null); setVideoErr(false);
          try { localStorage.setItem(JOB_KEY, JSON.stringify(j)); } catch { /* ignore */ }
          setBusy(false); setUploadPct(null);
          setView("results");
        } catch (e) {
          setBusy(false); setUploadPct(null);
          setUploadErr((e as Error).message);
        }
      })();
    };
    xhr.onerror = () => { setBusy(false); setUploadPct(null); setUploadErr("Network error during upload. Nothing was re-sent automatically — retry when ready."); };
    xhr.onabort = () => { setBusy(false); setUploadPct(null); setUploadErr("Upload cancelled. The file was not fully sent."); };
    xhr.send(file);
  };

  const cancelJob = async () => {
    if (!job || !session) return;
    try {
      const r = await fetch(`/api/analyses/${job.analysisId}/cancel`, {
        method: "POST", credentials: "include", headers: { "X-CSRF-Token": session.csrf_token },
      });
      if (!r.ok) setResultErr(`Cancel failed: ${await readError(r)}`);
    } catch (e) {
      setResultErr(`Cancel request failed: ${(e as Error).message}`);
    }
  };

  const saveLog = () => {
    const reps = Number(editReps);
    if (editReps.trim() === "" || !Number.isInteger(reps) || reps < 0 || reps > 10000) {
      setResultErr("Enter a whole rep count between 0 and 10000.");
      return;
    }
    const legacyDetected = result
      ? result.warnings.includes("POSE_ONLY")
        ? null
        : result.reps.filter((r) => r.completion_status === "completed").length
      : null;
    const detected = movement !== null ? (movement.detected_rep_count ?? null) : legacyDetected;
    const entry: LogEntry = {
      logId: crypto.randomUUID(),
      analysisId: job?.analysisId ?? result?.analysis_id ?? null,
      exercise: result?.exercise ?? job?.exercise ?? exercise,
      createdAt: new Date().toISOString(),
      detectedReps: detected, loggedReps: reps, load, notes,
    };
    // Idempotent: one saved log per analysis.
    const next = entry.analysisId
      ? [...logs.filter((l) => l.analysisId !== entry.analysisId), entry]
      : [...logs, entry];
    persistLogs(next);
    setView("history");
  };

  const deleteLocal = (logId: string) => persistLogs(logs.filter((l) => l.logId !== logId));

  const deleteRemote = async (analysisId: string) => {
    if (!session || !window.confirm("Revoke access to this analysis and its video on the server now? This does not guarantee physical erasure of stored video, and it cannot be undone. Your local history entry is kept.")) return;
    try {
      const r = await fetch(`/api/analyses/${analysisId}`, {
        method: "DELETE", credentials: "include", headers: { "X-CSRF-Token": session.csrf_token },
      });
      if (!r.ok && r.status !== 204) { window.alert(await readError(r)); return; }
      if (job?.analysisId === analysisId) {
        setJob(null); setStatus(null); setResult(null); setResultErr(null);
        try { localStorage.removeItem(JOB_KEY); } catch { /* ignore */ }
      }
    } catch (e) {
      window.alert(`Delete request failed: ${(e as Error).message}`);
    }
  };

  const resume = (l: LogEntry) => {
    if (!l.analysisId) return;
    setJob({ analysisId: l.analysisId, exercise: l.exercise, createdAt: l.createdAt });
    setStatus(null); setResult(null); setResultErr(null); setVideoErr(false);
    setView("results");
  };

  const muscleSet = [...new Set(logs.flatMap((l) => EXERCISES.find((e) => e.id === l.exercise)?.muscles ?? []))];
  const today = new Date().toDateString();
  const repsToday = logs.filter((l) => new Date(l.createdAt).toDateString() === today).reduce((a, l) => a + l.loggedReps, 0);

  const navBtn = (v: View, label: string, icon: string) => (
    <button key={v} aria-current={view === v ? "page" : undefined} onClick={() => setView(v)}>
      <span aria-hidden="true">{icon}</span>{label}
    </button>
  );

  return (
    <div className="shell">
      <a className="skip" href="#main">Skip to content</a>
      <aside className="side">
        <a className="brand" href="#" onClick={(e) => { e.preventDefault(); setView("dashboard"); }}>
          Motion <em>X&nbsp;Ray</em>
        </a>
        <span className="badge">Prototype</span>
        <nav className="nav" aria-label="Primary">
          {navBtn("dashboard", "Dashboard", "◧")}
          {navBtn("new", "New set", "＋")}
          {navBtn("results", "Results", "◉")}
          {navBtn("history", "History", "≡")}
        </nav>
        <p className="sidefoot">
          Movement insights · personal prototype
        </p>
      </aside>

      <main className="main" id="main">
        {sessionErr && <div className="state bad" role="alert">Could not start a session: {sessionErr}. Uploads are disabled until this succeeds — reload to retry.</div>}

        {view === "dashboard" && (
          <section className="view" aria-labelledby="dash-h">
            <p className="kicker">Overview</p>
            <h1 className="h-xl" id="dash-h">{name ? `Good to see you, ${name}.` : "Make every set count."}</h1>
            <p className="lede">Upload a set, review your movement and keep your training in one place.</p>
            <button className="btn" style={{ marginBottom: "1.5rem" }} onClick={() => setView("new")}>Analyse a new set ↗</button>
            <div className="field" style={{ maxWidth: 320 }}>
              <label htmlFor="name">Display name (optional, stored only in this browser)</label>
              <input id="name" value={name} onChange={(e) => saveName(e.target.value)} placeholder="e.g. Alex" autoComplete="off" />
            </div>
            {logs.length === 0 ? (
              <div className="empty">
                <h2 style={{ fontSize: "1.4rem", marginBottom: ".5rem" }}>No sets yet</h2>
                <p>Your dashboard fills in once you log your first set.</p>
                <p style={{ marginTop: "1.25rem" }}><button className="btn" onClick={() => setView("new")}>Start a new set</button></p>
              </div>
            ) : (
              <>
                <div className="grid" style={{ marginBottom: "1.5rem" }}>
                  <div className="card"><p className="muted">Sets logged</p><p className="big">{logs.length}</p></div>
                  <div className="card"><p className="muted">Reps logged today</p><p className="big">{repsToday}</p></div>
                  <div className="card"><p className="muted">Latest exercise</p><p className="big" style={{ fontSize: "1.4rem" }}>{EXERCISES.find((e) => e.id === logs[logs.length - 1]?.exercise)?.name ?? logs[logs.length - 1]?.exercise}</p></div>
                </div>
                <div className="card" style={{ background: "var(--ink)", color: "var(--paper)" }}>
                  <div className="spread">
                    <div style={{ minWidth: 0 }}>
                      <h3 style={{ color: "var(--paper)" }}>Muscle focus</h3>
                      <p style={{ color: "#aeb8cc" }}>Illustrative only — based on the exercises you logged, not measured activation.</p>
                      <div className="muscles">{muscleSet.map((m) => <span className="tag" key={m} style={{ background: "#1c2942", color: "var(--lime)" }}>{m}</span>)}</div>
                    </div>
                    <Silhouette active={muscleSet} />
                  </div>
                </div>
              </>
            )}
          </section>
        )}

        {view === "new" && (
          <section className="view" aria-labelledby="new-h">
            <p className="kicker">Capture</p>
            <h1 className="h-xl" id="new-h">New set</h1>
            <p className="lede">One set per clip, up to {MAX_SECONDS} seconds and 100 MiB. MP4, MOV or WebM.</p>
            <h2 style={{ fontSize: "1.2rem", margin: "0 0 .8rem" }}>1 · Choose exercise</h2>
            <div className="grid" role="group" aria-label="Exercise">
              {EXERCISES.map((e) => (
                <button key={e.id} className="excard" aria-pressed={exercise === e.id} onClick={() => setExercise(e.id)}>
                  <ExerciseArt kind={e.art} />
                  <h3>{e.name}</h3>
                  <p>{e.guidance}</p>
                  <span className="muscles">{e.muscles.map((m) => <span className="tag" key={m}>{m}</span>)}</span>
                </button>
              ))}

            </div>
            <h2 style={{ fontSize: "1.2rem", margin: "1.6rem 0 .8rem" }}>2 · Add your clip</h2>
            <div className="drop">
              <input
                type="file" accept="video/mp4,video/quicktime,video/webm" aria-label="Choose a set video"
                onChange={(e) => void onPick(e.target.files?.[0] ?? null)} disabled={busy}
              />
              {file && <p className="muted" style={{ marginTop: ".5rem" }}>{file.name} · {(file.size / (1024 * 1024)).toFixed(1)} MiB</p>}
              {fileNote && <div className="state warn" role="status">{fileNote}</div>}
            </div>
            <div style={{ margin: "1rem 0" }}>
              <label className="consent">
                <input type="checkbox" checked={consent} onChange={(e) => setConsent(e.target.checked)} disabled={busy} />
                <span>I consent to uploading this video for analysis. Video access lasts up to 24 hours; my workout history stays in this browser.</span>
              </label>
            </div>
            <h2 style={{ fontSize: "1.2rem", margin: "1.6rem 0 .8rem" }}>3 · Details (optional)</h2>
            <div className="grid">
              <div className="field"><label htmlFor="load">Load</label><input id="load" value={load} onChange={(e) => setLoad(e.target.value)} placeholder="e.g. 40 kg stack" /></div>
              <div className="field"><label htmlFor="notes">Notes</label><input id="notes" value={notes} onChange={(e) => setNotes(e.target.value)} placeholder="e.g. last reps felt grindy" /></div>
            </div>
            {uploadPct !== null && (
              <div>
                <div className="progress" role="progressbar" aria-valuenow={uploadPct} aria-valuemin={0} aria-valuemax={100} aria-label="Upload progress"><div style={{ width: `${uploadPct}%` }} /></div>
                <p className="muted">Uploading — {uploadPct}% of bytes sent.</p>
              </div>
            )}
            {uploadErr && <div className="state bad" role="alert">{uploadErr}</div>}
            <div className="row" style={{ marginTop: "1rem" }}>
              <button className="btn" disabled={!file || !consent || !session || busy} onClick={startUpload}>
                {busy ? "Working…" : "Upload & analyse"}
              </button>
              {busy && uploadPct !== null && <button className="btn ghost" onClick={() => xhrRef.current?.abort()}>Cancel upload</button>}
            </div>
          </section>
        )}

        {view === "results" && (
          <section className="view" aria-labelledby="res-h">
            <p className="kicker">Report</p>
            <h1 className="h-xl" id="res-h">Results</h1>
            {!job && !result && <div className="empty"><p>No analysis selected. Start a new set or reopen one from History.</p></div>}
            {status && status.state !== "succeeded" && status.state !== "failed" && status.state !== "cancelled" && (
              <div className="state" role="status">
                <div className="spread">
                  <div>
                    <strong>{status.state === "queued" ? "Queued" : "Processing"}</strong> — stage: {status.stage}.
                    <p className="muted" style={{ margin: ".3rem 0 0" }}>This page updates automatically. No estimated percentage — we report the real pipeline stage.</p>
                  </div>
                  <button className="btn ghost sm" onClick={() => void cancelJob()}>Cancel analysis</button>
                </div>
              </div>
            )}
            {status?.state === "failed" && <div className="state bad" role="alert">Analysis failed{status.error ? `: ${status.error}` : "."} Your video may have expired or been unreadable. Start a new set to try again.</div>}
            {status?.state === "cancelled" && <div className="state warn">This analysis was cancelled.</div>}
            {resultErr && (
              <div className="state bad" role="alert">
                {resultErr}
                {job && (
                  <button className="btn ghost sm" style={{ marginLeft: ".6rem" }} onClick={() => { setResultErr(null); setJob({ ...job }); }}>Retry</button>
                )}
              </div>
            )}
            {result && (
              <>
                {movement === null && result.warnings.length > 0 && (
                  <div className="state warn" role="status">
                    {result.warnings.map((w) => (
                      <p key={w} style={{ margin: ".2rem 0" }}>
                        {w === "POSE_ONLY"
                          ? "Your video and pose data are ready, but a movement report is not yet available for this clip — repetitions and metrics have not yet been calculated."
                          : w.replaceAll("_", " ").toLowerCase()}
                      </p>
                    ))}
                  </div>
                )}
                {movement === null && (
                <div className="grid" style={{ marginBottom: "1.25rem" }}>
                  <div className="card"><p className="muted">Detected reps</p><p className="big">{result.warnings.includes("POSE_ONLY") ? "—" : result.reps.filter((r) => r.completion_status === "completed").length}</p>{result.warnings.includes("POSE_ONLY") && <p className="muted">Unavailable for this report</p>}</div>
                  <div className="card"><p className="muted">Score</p><p className="big">{result.score ?? "—"}</p>{result.score == null && <p className="muted">Unavailable for this report</p>}</div>
                  <div className="card"><p className="muted">Coaching</p><p>{result.coaching?.status === "ok" ? result.coaching.summary : "Coaching is unavailable for this report."}</p></div>
                </div>
                )}
                {videoErr && <div className="state warn" role="status">The video for this report is unavailable — it may have expired or been removed from the server. The report data above is still valid.</div>}
                <video ref={videoRef} controls src={`/api/analyses/${result.analysis_id}/artifacts/proxy`} aria-label="Analysed set video" onError={() => setVideoErr(true)} />
                <div className="row" style={{ margin: ".6rem 0 1.25rem" }}>
                  <label htmlFor="rate" className="muted">Playback speed</label>
                  <select id="rate" value={rate} onChange={(e) => setRate(Number(e.target.value))}>
                    {[0.25, 0.5, 1, 1.5, 2].map((r) => <option key={r} value={r}>{r}×</option>)}
                  </select>
                </div>
                <MovementReport analysisId={result.analysis_id} onReport={setMovement} />
                {movement === null && result.reps.length > 0 && (
                  <div className="card" style={{ overflowX: "auto", marginBottom: "1.25rem" }}>
                    <h3>Repetitions</h3>
                    <table>
                      <thead><tr><th>#</th><th>Start</th><th>End</th><th>Completion</th><th>Scorable</th></tr></thead>
                      <tbody>
                        {result.reps.map((r) => (
                          <tr key={r.id}>
                            <td>{r.ordinal}</td><td>{r.start_s.toFixed(2)}s</td><td>{r.end_s.toFixed(2)}s</td>
                            <td><span className={`pill ${r.completion_status === "completed" ? "ok" : "warn"}`}>{r.completion_status}</span></td>
                            <td>{r.scorable ? "Yes" : "No"}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )}
                {movement === null && (
                <div className="card" style={{ overflowX: "auto", marginBottom: "1.25rem" }}>
                  <h3>Metrics</h3>
                  {result.metrics.length === 0 ? <p className="muted">No metrics were produced for this report.</p> : (
                    <table>
                      <thead><tr><th>Metric</th><th>Rep</th><th>Value</th><th>Reference band</th><th>Status</th></tr></thead>
                      <tbody>
                        {result.metrics.map((m, i) => (
                          <tr key={`${m.id}-${m.rep_id}-${i}`}>
                            <td>{m.id.replaceAll("_", " ")}</td><td>{m.rep_id}</td>
                            <td>{m.value == null ? `Unavailable${m.reason ? ` — ${m.reason.replaceAll("_", " ")}` : ""}` : `${m.value.toFixed(1)} ${m.unit}`}</td>
                            <td>{m.reference_interval ? `${m.reference_interval[0]}–${m.reference_interval[1]} ${m.unit}` : "—"}</td>
                            <td><span className={`pill ${m.status === "ok" ? "ok" : "dim"}`}>{m.status}</span></td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  )}
                </div>
                )}
                <div className="card">
                  <h3>Save this set to your history</h3>
                  <p className="muted">Saved only in this browser. Enter the reps you actually count — it can differ from what was detected.</p>
                  <div className="row" style={{ marginTop: ".6rem" }}>
                    <div className="field" style={{ margin: 0, width: 140 }}>
                      <label htmlFor="reps">Your rep count</label>
                      <input id="reps" inputMode="numeric" value={editReps} onChange={(e) => setEditReps(e.target.value)} placeholder={movement !== null ? (movement.detected_rep_count !== null && movement.detected_rep_count !== undefined ? String(movement.detected_rep_count) : "") : result.warnings.includes("POSE_ONLY") ? "" : String(result.reps.filter((r) => r.completion_status === "completed").length)} />
                    </div>
                    <button className="btn" disabled={editReps.trim() === ""} onClick={saveLog}>Save set</button>
                  </div>
                </div>
              </>
            )}
          </section>
        )}

        {view === "history" && (
          <section className="view" aria-labelledby="his-h">
            <p className="kicker">Log</p>
            <h1 className="h-xl" id="his-h">History</h1>
            <p className="lede">Saved in this browser. Removing a log keeps the server analysis; revoke analysis access separately. Video access expires under the retention policy.</p>
            {storageErr && <div className="state bad" role="alert">{storageErr}</div>}
            {logs.length === 0 ? (
              <div className="empty"><p>Nothing logged yet.</p><p style={{ marginTop: "1rem" }}><button className="btn" onClick={() => setView("new")}>Start a new set</button></p></div>
            ) : (
              <div className="grid" style={{ gridTemplateColumns: "1fr" }}>
                {[...logs].reverse().map((l) => (
                  <div className="card" key={l.logId}>
                    <div className="spread">
                      <div style={{ minWidth: 0 }}>
                        <h3>{EXERCISES.find((e) => e.id === l.exercise)?.name ?? l.exercise}</h3>
                        <p>{new Date(l.createdAt).toLocaleString()}</p>
                        <p>
                          Logged reps: <strong>{l.loggedReps}</strong>
                          {l.detectedReps !== null && <> · Detected: <strong>{l.detectedReps}</strong></>}
                          {l.load && <> · Load: {l.load}</>}
                        </p>
                        {l.notes && <p>“{l.notes}”</p>}
                        <p>{l.analysisId ? <span className="pill ok">Analysed</span> : <span className="pill dim">Manual entry</span>}</p>
                      </div>
                      <div className="row">
                        {l.analysisId && <button className="btn ghost sm" onClick={() => resume(l)}>Reopen report</button>}
                        {l.analysisId && <button className="btn danger sm" onClick={() => void deleteRemote(l.analysisId!)}>Revoke server analysis</button>}
                        <button className="btn ghost sm" onClick={() => deleteLocal(l.logId)}>Remove from history</button>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </section>
        )}
      </main>

      <nav className="bottomnav" aria-label="Primary">
        {navBtn("dashboard", "Dashboard", "◧")}
        {navBtn("new", "New set", "＋")}
        {navBtn("results", "Results", "◉")}
        {navBtn("history", "History", "≡")}
      </nav>
    </div>
  );
}
