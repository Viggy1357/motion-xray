"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { usePathname } from "next/navigation";
import type { ReactElement } from "react";
import type { components } from "../generated/api";
import MovementReport from "./movement-report";
import AthleteCompanion from "./athlete-companion";
import PoseReplay from "./pose-replay";
import CameraRecorder from "./components/CameraRecorder";
import SettingsPanel from "./components/SettingsPanel";
import RegionActivity from "./components/RegionActivity";
import SessionThumbnail from "./components/SessionThumbnail";
import {
  applyUxSettings,
  defaultUxMetadata,
  loadUxMetadata,
  persistUxMetadata,
  withViewed,
} from "./lib/ux-metadata";
import type { UxMetadata, UxSettings } from "./lib/ux-metadata";

type PrototypeReport = components["schemas"]["PrototypeAnalysisResult"];
type SessionInfo = components["schemas"]["SessionInfo"];
type VideoAsset = components["schemas"]["VideoAsset"];
type AnalysisStatus = components["schemas"]["AnalysisStatus"];
type AnalysisResult = components["schemas"]["AnalysisResult"];
type ExerciseId = components["schemas"]["AnalysisCreateRequest"]["exercise_id"];

type RouteName = "home" | "analyse" | "results" | "progress" | "settings";
type Route = { name: RouteName; analysis?: string | null; exercise?: string | null; view?: string | null };

type LogEntry = {
  logId: string;
  analysisId: string | null;
  exercise: string;
  createdAt: string;
  detectedReps: number | null;
  loggedReps: number;
  load: string;
  notes: string;
  recognitionVersion?: "analysed-set-v1";
  recognition?: { analysisId: string; exercise: string };
};

type ActiveJob = { analysisId: string; exercise: string; createdAt: string };
type PendingCreate = { assetId: string; requestKey: string; exercise: ExerciseId };

const MAX_BYTES = 100 * 1024 * 1024;
const MAX_SECONDS = 60;
const LOG_KEY = "mxr.logs.v1";
const JOB_KEY = "mxr.activeJob.v1";
const NAME_KEY = "mxr.displayName.v1"; // legacy read-only fallback; new writes go into mxr.ux.v1
const UUID = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;

const EXERCISES: {
  id: ExerciseId;
  name: string;
  guidance: string;
  regions: string[];
  art: "pull" | "curl" | "squat" | "press";
}[] = [
  { id: "lat_pulldown", name: "Lat pulldown", guidance: "Diagonal side view, full arms and the bar visible", regions: ["Lats", "Biceps", "Upper back"], art: "pull" },
  { id: "dumbbell_curl", name: "Dumbbell curl", guidance: "Standing, both arms visible from the side", regions: ["Biceps", "Forearms"], art: "curl" },
  { id: "squat", name: "Squat (bodyweight)", guidance: "Side view, hips and knees visible through the full rep", regions: ["Quads", "Glutes", "Core"], art: "squat" },
  { id: "incline_chest_press", name: "Incline dumbbell press", guidance: "Side view, bench and both arms visible in frame", regions: ["Chest", "Shoulders", "Triceps"], art: "press" },
];

function Logo() {
  return (
    <svg width="26" height="26" viewBox="0 0 26 26" role="img" aria-label="Motion X Ray" style={{ flexShrink: 0 }}>
      <rect x="1" y="1" width="24" height="24" rx="7" fill="#3158e8" />
      <path d="M6 17 C9 9 11 15 13 12 C15 9 17 14 20 8" fill="none" stroke="#fff" strokeWidth="2.2" strokeLinecap="round" />
      <circle cx="20" cy="8" r="2" fill="#fff" />
    </svg>
  );
}

function SettingsIcon() {
  return (
    <svg width="20" height="20" viewBox="0 0 20 20" aria-hidden="true">
      <circle cx="10" cy="7" r="3.2" fill="none" stroke="currentColor" strokeWidth="1.6" />
      <path d="M3.5 17 C4.5 13.5 7 12 10 12 C13 12 15.5 13.5 16.5 17" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" />
    </svg>
  );
}

function ExerciseArt({ kind }: { kind: "pull" | "curl" | "squat" | "press" }) {
  const common = { fill: "none", stroke: "#142039", strokeWidth: 5, strokeLinecap: "round" as const };
  return (
    <svg viewBox="0 0 120 90" role="img" aria-hidden="true" className="exart">
      {kind === "pull" && (
        <g {...common}>
          <line x1="20" y1="12" x2="100" y2="12" stroke="#3158e8" />
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
          <path d="M52 30 L70 38 L64 20" stroke="#3158e8" />
          <circle cx="64" cy="16" r="5" stroke="#3158e8" />
          <path d="M52 56 L40 84 M52 56 L64 84" />
        </g>
      )}
      {kind === "squat" && (
        <g {...common}>
          <circle cx="46" cy="18" r="7" />
          <path d="M46 25 L58 48" />
          <path d="M58 48 L40 58 L46 80" stroke="#3158e8" />
          <path d="M58 48 L74 60 L70 82" />
          <path d="M46 32 L66 40" />
        </g>
      )}
      {kind === "press" && (
        <g {...common}>
          <path d="M20 74 L92 58" stroke="#3158e8" />
          <circle cx="40" cy="52" r="7" />
          <path d="M46 55 L66 60" />
          <path d="M56 58 L62 34 M62 34 L70 34" stroke="#3158e8" />
          <circle cx="66" cy="30" r="5" stroke="#3158e8" />
          <path d="M66 60 L84 66" />
        </g>
      )}
    </svg>
  );
}

function loadLogs(): LogEntry[] {
  try {
    const raw = localStorage.getItem(LOG_KEY);
    if (!raw) return [];
    const parsed: unknown = JSON.parse(raw);
    if (!Array.isArray(parsed)) return [];
    const bounded = (v: unknown, max: number) => typeof v === "string" && v.length <= max;
    return parsed.filter((e): e is LogEntry => {
      if (typeof e !== "object" || e === null) return false;
      const l = e as LogEntry;
      const base =
        bounded(l.logId, 64) &&
        (l.analysisId === null || (typeof l.analysisId === "string" && UUID.test(l.analysisId))) &&
        EXERCISES.some((x) => x.id === l.exercise) &&
        typeof l.createdAt === "string" && !Number.isNaN(Date.parse(l.createdAt)) &&
        Number.isInteger(l.loggedReps) && l.loggedReps >= 0 && l.loggedReps <= 10000 &&
        (l.detectedReps === null || (Number.isInteger(l.detectedReps) && l.detectedReps >= 0)) &&
        bounded(l.load, 200) && bounded(l.notes, 2000);
      if (!base) return false;
      if (l.recognitionVersion !== undefined) {
        const r = l.recognition;
        return (
          l.recognitionVersion === "analysed-set-v1" &&
          typeof r === "object" && r !== null &&
          typeof r.analysisId === "string" && UUID.test(r.analysisId) &&
          r.analysisId === l.analysisId &&
          r.exercise === l.exercise
        );
      }
      return true; // legacy logs preserved, never retroactively awarded recognition
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

function parseRoute(): Route {
  const p = window.location.pathname;
  const q = new URLSearchParams(window.location.search);
  if (p.startsWith("/analyse/results")) return { name: "results", analysis: q.get("analysis"), exercise: q.get("exercise") };
  if (p.startsWith("/analyse")) return { name: "analyse" };
  if (p.startsWith("/progress")) return { name: "progress", view: q.get("view") };
  if (p.startsWith("/settings")) return { name: "settings" };
  if (q.get("analysis") && q.get("exercise")) return { name: "results", analysis: q.get("analysis"), exercise: q.get("exercise") };
  return { name: "home" };
}

function routeUrl(r: Route): string {
  if (r.name === "analyse") return "/analyse";
  if (r.name === "progress") return r.view === "all" ? "/progress?view=all" : "/progress";
  if (r.name === "settings") return "/settings";
  if (r.name === "results") {
    const q = new URLSearchParams();
    if (r.analysis) q.set("analysis", r.analysis);
    if (r.exercise) q.set("exercise", r.exercise);
    return `/analyse/results?${q.toString()}`;
  }
  return "/";
}

function fmtElapsed(since: string, now: number): string {
  const s = Math.max(0, Math.floor((now - Date.parse(since)) / 1000));
  const m = Math.floor(s / 60);
  return m > 0 ? `${m}m ${s % 60}s` : `${s}s`;
}

export default function Page() {
  const [route, setRoute] = useState<Route>({ name: "home" });
  const [session, setSession] = useState<SessionInfo | null>(null);
  const [sessionErr, setSessionErr] = useState<string | null>(null);
  const [name, setName] = useState("");
  const [logs, setLogs] = useState<LogEntry[]>([]);
  const [job, setJob] = useState<ActiveJob | null>(null);
  const [status, setStatus] = useState<AnalysisStatus | null>(null);
  const [result, setResult] = useState<AnalysisResult | null>(null);
  const [resultErr, setResultErr] = useState<string | null>(null);
  const [movement, setMovement] = useState<PrototypeReport | null>(null);
  const [movementSettled, setMovementSettled] = useState(false);
  const [videoErr, setVideoErr] = useState(false);
  const [cancelBusy, setCancelBusy] = useState(false);
  const [now, setNow] = useState(() => Date.now());

  // UX metadata (mxr.ux.v1): goal settings, week mode, display name, Viewed markers.
  const [uxMeta, setUxMeta] = useState<UxMetadata>(() => defaultUxMetadata());
  const [uxMetaErr, setUxMetaErr] = useState<string | null>(null);

  // Analyse form
  const [exercise, setExercise] = useState<ExerciseId>("lat_pulldown");
  const [file, setFile] = useState<File | null>(null);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const [fileNote, setFileNote] = useState<string | null>(null);
  const [consent, setConsent] = useState(false);
  const [load, setLoad] = useState("");
  const [notes, setNotes] = useState("");
  const [uploadPct, setUploadPct] = useState<number | null>(null);
  const [uploadErr, setUploadErr] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [pendingCreate, setPendingCreate] = useState<PendingCreate | null>(null);
  const [exercisePickerOpen, setExercisePickerOpen] = useState(false); // presentation only: exercise selector disclosure
  const [recorderOpen, setRecorderOpen] = useState(false);

  // Save form
  const [rate, setRate] = useState(1);
  const [editReps, setEditReps] = useState("");
  const [toast, setToast] = useState<string | null>(null);
  const [storageErr, setStorageErr] = useState<string | null>(null);

  // Bumped on visibilitychange so the Viewed effect re-evaluates when the
  // user returns to a report that finished loading in the background.
  const [visibilityTick, setVisibilityTick] = useState(0);

  const xhrRef = useRef<XMLHttpRequest | null>(null);
  const uploadingRef = useRef(false);
  const pickTokenRef = useRef(0);
  const h1Ref = useRef<HTMLHeadingElement | null>(null);
  const fileInputRef = useRef<HTMLInputElement | null>(null);
  const expiredRef = useRef(false);
  const prefillRef = useRef<{ reps: string; load: string; notes: string } | null>(null);

  // Next.js App Router patches window.history.pushState, so native
  // pushes are picked up by the router and reflected in usePathname.
  // Route state is derived from the URL in the sync effect below — there
  // is no independent React-side route that can drift or be reverted.
  const pathname = usePathname();

  const navigate = useCallback((r: Route) => {
    window.history.pushState(null, "", routeUrl(r));
    setRoute(parseRoute()); // Also reconcile query-only pushes on the same pathname.
  }, []);

  const initSession = useCallback(() => {
    setSessionErr(null);
    fetch("/api/session", { credentials: "include" })
      .then(async (r) => {
        if (!r.ok) throw new Error(await readError(r));
        return (await r.json()) as SessionInfo;
      })
      .then(setSession)
      .catch((e: Error) => setSessionErr(e.message));
  }, []);

  // Initial load: local state and session only. The route itself is
  // derived from the URL by the sync effect below (single source of truth).
  useEffect(() => {
    setLogs(loadLogs());
    const { metadata, error } = loadUxMetadata();
    setUxMeta(metadata);
    setUxMetaErr(error);
    // Display name: prefer a valid name persisted inside mxr.ux.v1; fall
    // back to the legacy standalone key for back-compat. No writes here.
    let legacyName = "";
    try {
      legacyName = localStorage.getItem(NAME_KEY) ?? "";
      const raw = localStorage.getItem(JOB_KEY);
      if (raw) {
        const j: unknown = JSON.parse(raw);
        const a = j as ActiveJob;
        if (
          typeof j === "object" && j !== null &&
          typeof a.analysisId === "string" && UUID.test(a.analysisId) &&
          EXERCISES.some((x) => x.id === a.exercise) &&
          typeof a.createdAt === "string" && !Number.isNaN(Date.parse(a.createdAt))
        ) {
          setJob(a); // restored, but does not force navigation
        }
      }
    } catch { /* ignore corrupt local data */ }
    const metaName = metadata.displayName;
    setName(typeof metaName === "string" && metaName.length <= 60 ? metaName : legacyName);
    initSession();
  }, [initSession]);

  // URL -> route sync, the single source of truth for navigation.
  useEffect(() => {
    const sync = () => {
      const r = parseRoute();
      setRoute(r);
      // Reconcile the active job with the URL so a previously viewed
      // report can never be displayed under a different analysis id.
      if (r.name === "results" && r.analysis && r.exercise && UUID.test(r.analysis) && EXERCISES.some((x) => x.id === r.exercise)) {
        const analysisId = r.analysis;
        const ex = r.exercise;
        setJob((prev) =>
          prev && prev.analysisId === analysisId
            ? prev
            : { analysisId, exercise: ex, createdAt: new Date().toISOString() }
        );
      }
    };
    sync();
    window.addEventListener("popstate", sync);
    return () => window.removeEventListener("popstate", sync);
  }, [pathname]);

  // Focus heading on navigation.
  useEffect(() => {
    h1Ref.current?.focus({ preventScroll: true });
    window.scrollTo(0, 0);
  }, [route.name]);

  // Clear stale per-job results immediately when the job identity changes.
  useEffect(() => {
    setMovement(null);
    setMovementSettled(false);
    setResult(null);
    setStatus(null);
    if (expiredRef.current) expiredRef.current = false;
    else setResultErr(null);
    setVideoErr(false);
    setEditReps("");
    const p = prefillRef.current;
    if (p) {
      prefillRef.current = null;
      setEditReps(p.reps);
      setLoad(p.load);
      setNotes(p.notes);
    }
  }, [job?.analysisId]);

  // Stable identity; settled flag distinguishes 'fetch in flight' from
  // 'fetch finished with no report' so a late save can never downgrade an
  // existing recognised record while the movement GET is still loading.
  const onReport = useCallback((r: PrototypeReport | null, settled: boolean) => {
    setMovement(r);
    setMovementSettled(settled);
  }, []);

  const jobActive =
    job !== null &&
    (status === null || (status.state !== "succeeded" && status.state !== "failed" && status.state !== "cancelled"));

  // Poll active job every 2s; stop on terminal state. Never forces navigation.
  useEffect(() => {
    if (!job || !session) return;
    const jobId = job.analysisId;
    const ctrl = new AbortController();
    let timer = 0;
    const tick = async () => {
      try {
        const r = await fetch(`/api/analyses/${jobId}`, { credentials: "include", signal: ctrl.signal });
        if (!r.ok) {
          if (r.status === 404) {
            try { localStorage.removeItem(JOB_KEY); } catch { /* ignore */ }
            expiredRef.current = true;
            setJob(null);
            setResultErr("This analysis is no longer available on the server (expired or revoked). You can start a new upload; your local history is unchanged.");
            return;
          }
          throw new Error(await readError(r));
        }
        const s = (await r.json()) as AnalysisStatus;
        if (ctrl.signal.aborted) return;
        setStatus(s);
        if (typeof s.created_at === "string" && s.created_at !== job.createdAt) {
          setJob({ ...job, createdAt: s.created_at });
        }
        if (s.state === "succeeded") {
          const rr = await fetch(`/api/analyses/${jobId}/result`, { credentials: "include", signal: ctrl.signal });
          if (ctrl.signal.aborted) return;
          if (rr.ok) {
            const parsed = (await rr.json()) as AnalysisResult;
            if (ctrl.signal.aborted || parsed.analysis_id !== jobId) return;
            setResult(parsed);
          } else if (!ctrl.signal.aborted) {
            setResultErr(await readError(rr));
          }
          return; // keep job metadata so a refresh can reattach
        }
        if (s.state === "failed" || s.state === "cancelled") {
          try { localStorage.removeItem(JOB_KEY); } catch { /* ignore */ }
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

  // Elapsed clock for the queued/processing banner.
  useEffect(() => {
    if (!jobActive || !job) return;
    const t = window.setInterval(() => setNow(Date.now()), 1000);
    return () => window.clearInterval(t);
  }, [jobActive, job]);

  useEffect(() => {
    if (!toast) return;
    const t = window.setTimeout(() => setToast(null), 3000);
    return () => window.clearTimeout(t);
  }, [toast]);

  // Abort any in-flight upload XHR if the component unmounts so no stale
  // state updates (or late analysis creation) can occur afterwards.
  useEffect(() => {
    return () => {
      xhrRef.current?.abort();
      xhrRef.current = null;
      uploadingRef.current = false;
    };
  }, []);

  // Preview object URL lifecycle.
  useEffect(() => {
    if (!file) { setPreviewUrl(null); return; }
    const url = URL.createObjectURL(file);
    setPreviewUrl(url);
    return () => URL.revokeObjectURL(url);
  }, [file]);

  // Track tab visibility so a report that finished loading in the
  // background is only marked Viewed once the user actually returns to it.
  useEffect(() => {
    const onVis = () => setVisibilityTick((t) => t + 1);
    document.addEventListener("visibilitychange", onVis);
    return () => document.removeEventListener("visibilitychange", onVis);
  }, []);

  // Viewed marker: recorded only when the owned report has settled with an
  // actual non-null movement report matching this analysis (a failed or
  // missing movement report never counts) and the Results view is actually
  // visible. Persisted atomically to mxr.ux.v1 BEFORE state updates; a
  // storage failure records nothing. "Viewed" means the report finished
  // loading while visible — never watched/reviewed.
  useEffect(() => {
    if (route.name !== "results" || !result || !movementSettled || !movement) return;
    const moveId = (movement as unknown as { analysis_id?: unknown }).analysis_id;
    if (typeof moveId !== "string" || moveId !== result.analysis_id) return;
    if (typeof document !== "undefined" && document.visibilityState !== "visible") return;
    const id = result.analysis_id;
    if (uxMeta.viewed[id]) return;
    const next = withViewed(uxMeta, id, new Date().toISOString());
    if (persistUxMetadata(next)) {
      setUxMeta(next);
    }
  }, [route.name, result, movement, movementSettled, uxMeta, visibilityTick]);

  // Name state updates only; storage is committed atomically with settings
  // in saveSettings (single mxr.ux.v1 write). No second store write here.
  const saveName = (v: string) => {
    setName(v);
  };

  // Settings save: atomic. The full merged mxr.ux.v1 record — settings plus
  // the display name carried in the preserved extra metadata field — is
  // serialized and written once. On failure nothing is committed (name
  // included — the panel only calls onNameChange after this returns true).
  const saveSettings = useCallback((s: UxSettings, displayName?: string): boolean => {
    const next = applyUxSettings(uxMeta, s);
    if (typeof displayName === "string") next.displayName = displayName;
    if (!persistUxMetadata(next)) {
      setUxMetaErr("Could not write to this browser's storage — settings were not saved. Previous values are unchanged.");
      return false;
    }
    setUxMeta(next);
    setUxMetaErr(null);
    return true;
  }, [uxMeta]);

  const onPick = async (f: File | null) => {
    const token = ++pickTokenRef.current;
    setFile(null); setFileNote(null); setUploadErr(null);
    if (!f) return;
    if (f.size > MAX_BYTES) { setFileNote("This file is over the 100 MiB limit."); return; }
    if (!guessMime(f)) { setFileNote("Unsupported file type. Use MP4, MOV or WebM."); return; }
    const dur = await probeDuration(f);
    if (token !== pickTokenRef.current) return; // a newer pick superseded this validation
    if (dur === null) {
      setFileNote("We could not preview this codec in your browser. You can still upload — the server will validate it.");
    } else if (dur > MAX_SECONDS) {
      setFileNote(`This clip is ${Math.round(dur)}s. The current limit is ${MAX_SECONDS}s per set — trim it and try again.`);
      return;
    }
    setFile(f);
  };

  // Clear the chosen file and its local preview without uploading.
  const clearFile = () => {
    if (busy) return;
    pickTokenRef.current++; // invalidate any in-flight async validation
    setFile(null);
    setFileNote(null);
    setUploadErr(null);
    if (fileInputRef.current) fileInputRef.current.value = ""; // allow re-selecting the same file
  };

  const createAnalysis = useCallback(async (assetId: string, requestKey: string, ex: ExerciseId) => {
    if (!session) return;
    const r = await fetch("/api/analyses", {
      method: "POST", credentials: "include",
      headers: { "Content-Type": "application/json", "X-CSRF-Token": session.csrf_token },
      body: JSON.stringify({ video_id: assetId, exercise_id: ex, request_key: requestKey }),
    });
    if (!r.ok) throw new Error(await readError(r));
    const s = (await r.json()) as AnalysisStatus;
    const j = { analysisId: s.id, exercise: ex, createdAt: s.created_at };
    setJob(j); setStatus(s); setPendingCreate(null);
    try { localStorage.setItem(JOB_KEY, JSON.stringify(j)); } catch { /* ignore */ }
    navigate({ name: "results", analysis: s.id, exercise: ex });
  }, [session, navigate]);

  const startUpload = () => {
    if (jobActive) {
      setUploadErr("An analysis is already in progress — wait for it to finish or cancel it before uploading again.");
      return;
    }
    if (!file || !session || !consent || uploadingRef.current) return;
    const frozen = exercise; // exercise is frozen for the submitted request
    uploadingRef.current = true;
    setBusy(true); setUploadErr(null); setUploadPct(0); setPendingCreate(null);
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
          setBusy(false); setUploadPct(null); uploadingRef.current = false; xhrRef.current = null;
          setUploadErr(`Upload failed: ${xhr.responseText ? String(xhr.responseText).slice(0, 300) : xhr.status}. Nothing was re-sent automatically.`);
          return;
        }
        try {
          const asset = JSON.parse(String(xhr.responseText)) as VideoAsset;
          const requestKey = crypto.randomUUID();
          try {
            await createAnalysis(asset.id, requestKey, frozen);
          } catch (e) {
            // Upload succeeded but analysis creation failed: retain asset id + request key, offer retry without re-upload.
            setPendingCreate({ assetId: asset.id, requestKey, exercise: frozen });
            setUploadErr(`Your video uploaded, but starting the analysis failed: ${(e as Error).message}. You can retry without uploading again.`);
          }
        } catch {
          setUploadErr("The upload response was unreadable. Upload status is unknown — nothing was re-sent automatically. Check Results before retrying.");
        }
        setBusy(false); setUploadPct(null); uploadingRef.current = false; xhrRef.current = null;
      })();
    };
    xhr.onerror = () => {
      setBusy(false); setUploadPct(null); uploadingRef.current = false; xhrRef.current = null;
      setUploadErr("Network error during upload. Upload status is unknown — nothing was re-sent automatically. Check Results before retrying.");
    };
    xhr.onabort = () => {
      setBusy(false); setUploadPct(null); uploadingRef.current = false; xhrRef.current = null;
      setUploadErr("Upload cancelled. The file was not fully sent.");
    };
    xhr.send(file);
  };

  const retryCreate = async () => {
    if (!pendingCreate || !session || busy) return;
    setBusy(true); setUploadErr(null);
    try {
      await createAnalysis(pendingCreate.assetId, pendingCreate.requestKey, pendingCreate.exercise);
    } catch (e) {
      setUploadErr(`Retry failed: ${(e as Error).message}. Your uploaded video is still retained — you can retry again.`);
    }
    setBusy(false);
  };

  const cancelJob = async () => {
    if (!job || !session || cancelBusy) return;
    setCancelBusy(true); setResultErr(null);
    try {
      const r = await fetch(`/api/analyses/${job.analysisId}/cancel`, {
        method: "POST", credentials: "include", headers: { "X-CSRF-Token": session.csrf_token },
      });
      if (!r.ok) setResultErr(`Cancel failed: ${await readError(r)}`);
    } catch (e) {
      setResultErr(`Cancel request failed: ${(e as Error).message}`);
    }
    setCancelBusy(false);
  };

  const movementMeta = movement as unknown as { analysis_id?: string; detected_rep_count?: number | null } | null;
  const detectedReps =
    movement !== null
      ? (movementMeta?.detected_rep_count ?? null)
      : result
        ? result.warnings.includes("POSE_ONLY")
          ? null
          : result.reps.filter((r) => r.completion_status === "completed").length
        : null;

  const movementProof = movement as unknown as {
    analysis_id?: string;
    exercise?: string;
    reps?: { completion_status?: string }[];
    metrics?: { value: number | null }[];
  } | null;
  const recognitionEligible =
    !!result && !!movementProof &&
    typeof movementProof.analysis_id === "string" &&
    movementProof.analysis_id === result.analysis_id &&
    movementProof.exercise === result.exercise &&
    Array.isArray(movementProof.reps) &&
    movementProof.reps.some((r) => r.completion_status === "completed") &&
    Array.isArray(movementProof.metrics) &&
    movementProof.metrics.some((m) => m.value !== null);

  const saveLog = () => {
    if (result && !movementSettled) {
      setResultErr("The movement report is still loading — wait for it to finish (or fail) before saving, so detected reps and analysis recognition are not lost.");
      return;
    }
    const reps = Number(editReps);
    if (editReps.trim() === "" || !Number.isInteger(reps) || reps < 0 || reps > 10000) {
      setResultErr("Enter a whole rep count between 0 and 10000.");
      return;
    }
    if (load.length > 200 || notes.length > 2000) {
      setResultErr("Load must be 200 characters or fewer and notes 2000 or fewer.");
      return;
    }
    const analysisId = job?.analysisId ?? result?.analysis_id ?? null;
    const ex = result?.exercise ?? job?.exercise ?? exercise;
    const prior = analysisId ? logs.find((l) => l.analysisId === analysisId) : undefined;
    const preservePrior =
      !!prior &&
      movement === null &&
      movementSettled &&
      !!result &&
      prior.exercise === ex &&
      (prior.detectedReps !== null || prior.recognitionVersion === "analysed-set-v1");
    const entry: LogEntry = {
      logId: prior?.logId ?? crypto.randomUUID(),
      analysisId,
      exercise: ex,
      createdAt: prior?.createdAt ?? new Date().toISOString(),
      detectedReps: preservePrior ? (prior?.detectedReps ?? null) : detectedReps,
      loggedReps: reps, load, notes,
      ...(recognitionEligible && analysisId
        ? { recognitionVersion: "analysed-set-v1" as const, recognition: { analysisId, exercise: ex } }
        : preservePrior && prior?.recognitionVersion === "analysed-set-v1" && prior.recognition && analysisId
          ? { recognitionVersion: "analysed-set-v1" as const, recognition: { analysisId, exercise: ex } }
          : {}),
    };
    const next = entry.analysisId
      ? [...logs.filter((l) => l.analysisId !== entry.analysisId), entry]
      : [...logs, entry];
    // Atomic: persist to localStorage before any React state or navigation.
    try {
      localStorage.setItem(LOG_KEY, JSON.stringify(next));
    } catch {
      setStorageErr("Could not write to this browser's storage — your set was not saved.");
      return;
    }
    setStorageErr(null);
    setLogs(next);
    setToast("Set saved to this browser's history.");
    navigate({ name: "progress" });
  };

  const deleteLocal = (logId: string) => {
    const next = logs.filter((l) => l.logId !== logId);
    try {
      localStorage.setItem(LOG_KEY, JSON.stringify(next));
    } catch {
      setStorageErr("Could not write to this browser's storage — the change was not saved.");
      return;
    }
    setLogs(next);
  };

  const deleteRemote = async (analysisId: string) => {
    if (!session || !window.confirm("Revoke access to this analysis and its video on the server now? This does not guarantee physical erasure of stored video, and it cannot be undone. Your local history entry is kept.")) return;
    try {
      const r = await fetch(`/api/analyses/${analysisId}`, {
        method: "DELETE", credentials: "include", headers: { "X-CSRF-Token": session.csrf_token },
      });
      if (!r.ok && r.status !== 204) { window.alert(await readError(r)); return; }
      if (job?.analysisId === analysisId) {
        setJob(null);
        try { localStorage.removeItem(JOB_KEY); } catch { /* ignore */ }
      }
    } catch (e) {
      window.alert(`Delete request failed: ${(e as Error).message}`);
    }
  };

  const resume = (l: LogEntry) => {
    if (!l.analysisId) return;
    const prefill = { reps: String(l.loggedReps), load: l.load, notes: l.notes };
    if (job?.analysisId === l.analysisId) {
      setEditReps(prefill.reps);
      setLoad(prefill.load);
      setNotes(prefill.notes);
    } else {
      prefillRef.current = prefill;
    }
    const j = { analysisId: l.analysisId, exercise: l.exercise, createdAt: l.createdAt };
    setJob(j);
    try { localStorage.setItem(JOB_KEY, JSON.stringify(j)); } catch { /* ignore */ }
    navigate({ name: "results", analysis: l.analysisId, exercise: l.exercise });
  };

  // Week window: rolling 7 days by default; opt-in local calendar week (Mon–Sun).
  const inWeek = (iso: string): boolean => {
    const t = Date.parse(iso);
    if (Number.isNaN(t)) return false;
    if (uxMeta.weekMode === "calendar") {
      const start = new Date();
      start.setHours(0, 0, 0, 0);
      start.setDate(start.getDate() - ((start.getDay() + 6) % 7)); // Monday
      return t >= start.getTime();
    }
    const start = new Date();
    start.setDate(start.getDate() - 6);
    return t >= start.getTime();
  };
  const weekLogs = logs.filter((l) => inWeek(l.createdAt));
  const lastLog = logs.length > 0 ? logs[logs.length - 1] : null;
  const recognised = logs.filter((l) => l.recognitionVersion === "analysed-set-v1" && l.recognition);
  const recognisedDedup = new Map<string, LogEntry>();
  for (const l of recognised) if (l.recognition) recognisedDedup.set(l.recognition.analysisId, l);
  const analysedSets = [...recognisedDedup.values()];
  const weekAnalysed = analysedSets.filter((l) => inWeek(l.createdAt)).length;
  const recentLogs = [...logs].reverse();
  const recent3 = recentLogs.slice(0, 3);
  const progressLogs = route.view === "all" ? recentLogs : recent3;

  const viewedPill = (l: LogEntry) =>
    l.analysisId && uxMeta.viewed[l.analysisId] ? <span className="pill dim">Viewed</span> : null;

  const navItems: { name: RouteName; label: string; icon: ReactElement }[] = [
    {
      name: "home", label: "Home",
      icon: <svg width="20" height="20" viewBox="0 0 20 20" aria-hidden="true"><path d="M3 9 L10 3 L17 9 V16 H12 V12 H8 V16 H3 Z" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinejoin="round" /></svg>,
    },
    {
      name: "analyse", label: "Analyse",
      icon: <svg width="22" height="22" viewBox="0 0 22 22" aria-hidden="true"><rect x="3" y="6" width="12" height="11" rx="2.5" fill="none" stroke="currentColor" strokeWidth="1.8" /><path d="M15 10 L19 7.5 V15.5 L15 13" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinejoin="round" /></svg>,
    },
    {
      name: "progress", label: "Progress",
      icon: <svg width="20" height="20" viewBox="0 0 20 20" aria-hidden="true"><path d="M4 16 V10 M10 16 V5 M16 16 V8" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" /></svg>,
    },
  ];

  const navBtn = (name: RouteName, label: string, icon: ReactElement, elevated: boolean) => (
    <button
      key={name}
      type="button"
      className={elevated ? "navbtn centre" : "navbtn"}
      aria-current={route.name === name || (name === "analyse" && route.name === "results") ? "page" : undefined}
      onClick={() => navigate({ name })}
    >
      <span className="navicon" aria-hidden="true">{icon}</span>
      <span>{label}</span>
    </button>
  );

  const settingsBtn = (
    <button
      type="button"
      className="iconbtn"
      aria-label="Settings and profile"
      aria-current={route.name === "settings" ? "page" : undefined}
      onClick={() => navigate({ name: "settings" })}
    >
      <SettingsIcon />
    </button>
  );

  const activeBanner = jobActive && job && (
    <div className="state" role="status">
      <div className="spread">
        <div>
          <strong>An analysis is {status?.state === "running" ? "processing" : "queued"}</strong>
          {" · "}{EXERCISES.find((e) => e.id === job.exercise)?.name ?? job.exercise}
          <p className="muted" style={{ margin: ".3rem 0 0" }}>Since submitted: {fmtElapsed(job.createdAt, now)}. You can keep browsing — nothing is interrupted.</p>
        </div>
        <div className="row">
          <button className="btn sm" onClick={() => navigate({ name: "results", analysis: job.analysisId, exercise: job.exercise })}>Resume</button>
          <button className="btn ghost sm" disabled={cancelBusy} onClick={() => void cancelJob()}>{cancelBusy ? "Requesting…" : "Cancel"}</button>
        </div>
      </div>
    </div>
  );

  const currentExercise = EXERCISES.find((e) => e.id === exercise);

  return (
    <div className="shell">
      <a className="skip" href="#main">Skip to content</a>

      <aside className="rail">
        <a className="brand" href="/" onClick={(e) => { e.preventDefault(); navigate({ name: "home" }); }}>
          <Logo />
          <span>Motion X&nbsp;Ray</span>
        </a>
        <nav className="railnav" aria-label="Primary">
          {navItems.map((n) => navBtn(n.name, n.label, n.icon, false))}
        </nav>
        <div className="railsettings">{settingsBtn}</div>
        <p className="railfoot">Movement insights · personal prototype</p>
      </aside>

      <main className="main" id="main">
        <header className="brandbar">
          <a className="brand" href="/" onClick={(e) => { e.preventDefault(); navigate({ name: "home" }); }}>
            <Logo />
            <span>Motion X-Ray</span>
          </a>
          {settingsBtn}
        </header>
        {sessionErr && (
          <div className="state bad" role="alert">
            Could not start a session: {sessionErr}. Uploads are disabled until this succeeds.{" "}
            <button className="btn ghost sm" onClick={initSession}>Retry session</button>
          </div>
        )}
        {toast && <div className="toast" role="status">{toast}</div>}

        {route.name === "home" && (
          <section className="view homeview" aria-labelledby="home-h">
            <div className="heroscene">
              <div className="herocopy">
                <h1 className="h-hero" id="home-h" tabIndex={-1} ref={h1Ref}>Make your<br />next set count.</h1>
                <p className="herosub">Movement insights for your next set.</p>
              </div>
              <div className="heroart">
                <AthleteCompanion exercise={exercise} variant="poster" />
              </div>
            </div>
            <p className="illabel">Illustration — generic athlete artwork, rendered front and back views (not a 360° model)</p>
            <button className="btn herocta" onClick={() => navigate({ name: "analyse" })}>Analyse a set</button>
            {activeBanner}
            {uxMeta.goalEnabled && uxMeta.goalTarget !== null && (
              <div className="card goalwidget" aria-label="Weekly analysed-set target">
                <div className="spread">
                  <p style={{ margin: 0 }}><strong>{weekAnalysed}</strong> of <strong>{uxMeta.goalTarget}</strong> analysed sets this week</p>
                  <button className="textlink" onClick={() => navigate({ name: "settings" })}>Adjust</button>
                </div>
                <div className="goaltrack" role="progressbar" aria-valuenow={Math.min(weekAnalysed, uxMeta.goalTarget)} aria-valuemin={0} aria-valuemax={uxMeta.goalTarget} aria-label="Weekly analysed-set target progress">
                  <span className="goalfill" style={{ width: `${Math.min(100, (weekAnalysed / uxMeta.goalTarget) * 100)}%` }} />
                </div>
                <p className="muted" style={{ margin: ".5rem 0 0" }}>A local consistency target you set — not a measure of muscle growth or strength.</p>
              </div>
            )}
            {logs.length > 0 && (
              <div className="homeactivity">
                <div>
                  <p className="muted">This week</p>
                  <p><strong>{weekLogs.length}</strong> saved {weekLogs.length === 1 ? "set" : "sets"}</p>
                </div>
                <button className="textlink" onClick={() => navigate({ name: "progress" })}>View progress →</button>
              </div>
            )}
            {recent3.length > 0 && (
              <div className="card recents" aria-label="Recent sessions">
                <div className="spread" style={{ alignItems: "baseline" }}>
                  <h3 style={{ margin: 0 }}>Recent sessions</h3>
                  <button className="textlink" onClick={() => navigate({ name: "progress", view: "all" })}>View all</button>
                </div>
                {recent3.map((l) => (
                  <div className="recentrow" key={l.logId}>
                    <span className="recentthumb">
                      {l.analysisId ? (
                        <SessionThumbnail analysisId={l.analysisId} label={`${EXERCISES.find((e) => e.id === l.exercise)?.name ?? l.exercise} video frame`} />
                      ) : (
                        <svg width="22" height="22" viewBox="0 0 24 24" aria-hidden="true"><rect x="3" y="5" width="18" height="14" rx="2" fill="none" stroke="currentColor" strokeWidth="1.5" /></svg>
                      )}
                    </span>
                    <div className="recentmain">
                      <strong>{EXERCISES.find((e) => e.id === l.exercise)?.name ?? l.exercise}</strong>
                      <p className="muted" style={{ margin: 0 }}>{new Date(l.createdAt).toLocaleDateString()}</p>
                    </div>
                    {viewedPill(l)}
                    {l.analysisId && <button className="textlink" onClick={() => resume(l)}>Reopen</button>}
                  </div>
                ))}
              </div>
            )}
            {lastLog && lastLog.analysisId && (
              <p className="muted lastreview">Last review: {EXERCISES.find((e) => e.id === lastLog.exercise)?.name ?? lastLog.exercise} · <button type="button" className="textlink" onClick={() => resume(lastLog)}>Reopen report</button></p>
            )}
            <AthleteCompanion exercise={exercise} variant="map" />
            {logs.length === 0 && (
              <div className="empty">
                <h2 style={{ fontSize: "1.3rem", marginBottom: ".5rem" }}>No sets yet</h2>
                <p>Your home screen fills in once you save your first analysed set.</p>
                <p style={{ marginTop: "1.25rem" }}><button className="btn" onClick={() => navigate({ name: "analyse" })}>Begin analysis</button></p>
              </div>
            )}
          </section>
        )}

        {route.name === "analyse" && (
          <section className="view" aria-labelledby="an-h">
            <h1 className="h-page" id="an-h" tabIndex={-1} ref={h1Ref}>Let’s get a clear view.</h1>
            <p className="lede">Record a set or choose a video. One set per clip, up to {MAX_SECONDS} seconds and 100 MiB. MP4, MOV or WebM.</p>
            {activeBanner}
            {jobActive ? (
              <div className="state warn" role="status">
                An analysis is already in progress. You can review it or check your progress while it runs — start a new upload once it finishes.
              </div>
            ) : (
              <>
                <div className="exrow">
                  <div className="excurrent">
                    <span className="exlabel">Exercise</span>
                    <span className="exname">{currentExercise?.name}</span>
                  </div>
                  <button type="button" className="btn ghost sm" aria-expanded={exercisePickerOpen} aria-controls="exercise-picker" onClick={() => setExercisePickerOpen((v) => !v)} disabled={busy}>
                    {exercisePickerOpen ? "Done" : "Change"}
                  </button>
                </div>
                {exercisePickerOpen && (
                  <div className="exselect" id="exercise-picker" role="group" aria-label="Choose exercise">
                    {EXERCISES.map((e) => (
                      <button key={e.id} type="button" className="exoption" aria-pressed={exercise === e.id} disabled={busy} onClick={() => { setExercise(e.id); setExercisePickerOpen(false); }}>
                        <ExerciseArt kind={e.art} />
                        <span className="exoptiontext"><strong>{e.name}</strong><span className="muted">{e.guidance}</span></span>
                      </button>
                    ))}
                  </div>
                )}
                <p className="framing">{currentExercise?.guidance}.<br />Keep your whole body in frame with steady lighting.</p>
                {previewUrl ? (
                  <div className="previewwrap">
                    <video className="preview" controls preload="metadata" src={previewUrl} aria-label="Local preview — not uploaded yet" />
                    <p className="muted">Local preview only — nothing is uploaded until you choose “Upload &amp; analyse”.</p>
                  </div>
                ) : (
                  <div className="pickarea">
                    <svg width="34" height="34" viewBox="0 0 34 34" aria-hidden="true"><rect x="4" y="9" width="19" height="17" rx="4" fill="none" stroke="currentColor" strokeWidth="2" /><path d="M23 15 L30 10.5 V24.5 L23 20" fill="none" stroke="currentColor" strokeWidth="2" strokeLinejoin="round" /></svg>
                    <p>Record a set or choose a video.</p>
                  </div>
                )}
                <div className="row fileactions">
                  <button type="button" className="btn" onClick={() => setRecorderOpen(true)} disabled={busy}>
                    <svg width="19" height="19" viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="1.6" aria-hidden="true"><rect x="2" y="5" width="12" height="11" rx="2.5" /><path d="M14 9 L18 6.8 V14.2 L14 12" strokeLinejoin="round" /></svg>
                    Record a set
                  </button>
                  <label className="btn ghost filebtn">
                    <svg width="19" height="19" viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="1.5" aria-hidden="true"><rect x="2" y="3" width="16" height="14" rx="2"/><path d="m3 14 4-4 4 4 3-3 4 4"/><circle cx="13" cy="7" r="1"/></svg>
                    Choose video
                    <input
                      ref={fileInputRef}
                      className="visuallyhidden"
                      type="file" accept="video/mp4,video/quicktime,video/webm" aria-label="Choose a set video"
                      onChange={(e) => void onPick(e.target.files?.[0] ?? null)} disabled={busy}
                    />
                  </label>
                  {file && <button type="button" className="btn ghost sm" onClick={clearFile} disabled={busy}>Clear file</button>}
                </div>
                {file && <p className="muted filemeta">{file.name} · {(file.size / (1024 * 1024)).toFixed(1)} MiB · limit {MAX_SECONDS}s / 100 MiB</p>}
                {fileNote && <div className="state warn" role="status">{fileNote}</div>}
                <label className="consent">
                  <input type="checkbox" checked={consent} onChange={(e) => setConsent(e.target.checked)} disabled={busy} />
                  <span>I consent to uploading this video to the server for processing. Video access lasts up to 24 hours; my workout history stays in this browser.</span>
                </label>
                <details className="details">
                  <summary>Details (optional)</summary>
                  <div className="grid" style={{ marginTop: ".8rem" }}>
                    <div className="field"><label htmlFor="load">Load</label><input id="load" value={load} maxLength={200} onChange={(e) => setLoad(e.target.value)} placeholder="e.g. 40 kg stack" /></div>
                    <div className="field"><label htmlFor="notes">Notes</label><input id="notes" value={notes} maxLength={2000} onChange={(e) => setNotes(e.target.value)} placeholder="e.g. last reps felt grindy" /></div>
                  </div>
                </details>
                {uploadPct !== null && (
                  <div>
                    <div className="progress" role="progressbar" aria-valuenow={uploadPct} aria-valuemin={0} aria-valuemax={100} aria-label="Upload progress"><div style={{ width: `${uploadPct}%` }} /></div>
                    <p className="muted">Uploading — {uploadPct}% of bytes sent.</p>
                  </div>
                )}
                {uploadErr && (
                  <div className="state bad" role="alert">
                    {uploadErr}
                    {pendingCreate && (
                      <button className="btn sm" style={{ marginLeft: ".6rem" }} disabled={busy} onClick={() => void retryCreate()}>
                        {busy ? "Working…" : "Retry analysis (no re-upload)"}
                      </button>
                    )}
                  </div>
                )}
                <div className="row" style={{ marginTop: "1rem" }}>
                  <button className="btn" disabled={!file || !consent || !session || busy} onClick={startUpload}>
                    {busy ? "Working…" : "Upload & analyse"}
                  </button>
                  {busy && uploadPct !== null && <button className="btn ghost" onClick={() => xhrRef.current?.abort()}>Cancel upload</button>}
                </div>
              </>
            )}
            {recorderOpen && (
              <div className="recorderoverlay">
                <CameraRecorder
                  exerciseLabel={currentExercise?.name ?? exercise}
                  guidance={currentExercise?.guidance ?? ""}
                  disabled={busy}
                  onUse={(f) => { setRecorderOpen(false); void onPick(f); }}
                  onClose={() => setRecorderOpen(false)}
                />
              </div>
            )}
          </section>
        )}

        {route.name === "results" && (
          <section className="view" aria-labelledby="res-h">
            <h1 className="h-page" id="res-h" tabIndex={-1} ref={h1Ref}>Your set, explained.</h1>
            {!job && !result && (
              <div className="empty">
                <p>No analysis selected.</p>
                <p style={{ marginTop: "1rem" }}><button className="btn" onClick={() => navigate({ name: "analyse" })}>Begin analysis</button></p>
              </div>
            )}
            {job && status && status.state !== "succeeded" && status.state !== "failed" && status.state !== "cancelled" && (
              <div className="state" role="status">
                <div className="spread">
                  <div>
                    <strong>{status.state === "queued" ? "Queued" : "Processing"}</strong> — stage: {status.stage}.
                    <p className="muted" style={{ margin: ".3rem 0 0" }}>
                      Since submitted: {fmtElapsed(job.createdAt, now)}. This page updates automatically; we report the real pipeline stage rather than an estimate.
                    </p>
                  </div>
                  <button className="btn ghost sm" disabled={cancelBusy} onClick={() => void cancelJob()}>
                    {cancelBusy ? "Requesting…" : "Cancel analysis"}
                  </button>
                </div>
              </div>
            )}
            {status?.state === "failed" && (
              <div className="state bad" role="alert">
                Analysis failed{status.error ? `: ${status.error}` : "."} Your video may have expired or been unreadable.{" "}
                <button className="btn sm" onClick={() => navigate({ name: "analyse" })}>Start a new set</button>
              </div>
            )}
            {status?.state === "cancelled" && (
              <div className="state warn">
                This analysis was cancelled.{" "}
                <button className="btn sm" onClick={() => navigate({ name: "analyse" })}>Start a new set</button>
              </div>
            )}
            {resultErr && (
              <div className="state bad" role="alert">
                {resultErr}
                {job && (
                  <button className="btn ghost sm" style={{ marginLeft: ".6rem" }} onClick={() => { setResultErr(null); setJob({ ...job }); }}>Retry</button>
                )}
              </div>
            )}
            {result && result.analysis_id === job?.analysisId && (
              <>
                {movementSettled && movement === null && result.warnings.length > 0 && (
                  <div className="state warn" role="status">
                    {result.warnings.map((w) => (
                      <p key={w} style={{ margin: ".2rem 0" }}>
                        {w === "POSE_ONLY"
                          ? "Your video and pose data are ready, but a movement report is not available for this clip — repetitions and metrics have not been calculated."
                          : w.replaceAll("_", " ").toLowerCase()}
                      </p>
                    ))}
                  </div>
                )}
                {videoErr && (
                  <div className="state warn" role="status">
                    The video for this report is unavailable — it may have expired or been removed from the server. The report data below is still available.
                  </div>
                )}
                <div className="resultgrid">
                  <div>
                    <PoseReplay analysisId={result.analysis_id} playbackRate={rate} onVideoError={() => setVideoErr(true)} />
                    <div className="row" style={{ margin: ".6rem 0 0" }}>
                      <label htmlFor="rate" className="muted">Playback speed</label>
                      <select id="rate" value={rate} onChange={(e) => setRate(Number(e.target.value))}>
                        {[0.25, 0.5, 1, 1.5, 2].map((r) => <option key={r} value={r}>{r}×</option>)}
                      </select>
                    </div>
                  </div>
                  <div className="reportcol">
                    <MovementReport analysisId={result.analysis_id} onReport={onReport} />
                  </div>
                </div>
                <div className="card savecard">
                  <h3>Save this set</h3>
                  <p className="muted">Saved only in this browser. Enter the reps you actually count — it can differ from what was detected.</p>
                  {detectedReps !== null && <p className="muted">Detected reps for this report: <strong>{detectedReps}</strong></p>}
                  {!movementSettled && <p className="muted" role="status">Loading movement report before saving…</p>}
                  {movementSettled && movement === null && logs.some((l) => l.analysisId === result.analysis_id && l.exercise === result.exercise && l.detectedReps !== null) && (
                    <p className="muted">The movement report could not be reloaded. Saving keeps the detection metadata already stored with this set.</p>
                  )}
                  <div className="row" style={{ marginTop: ".6rem" }}>
                    <div className="field" style={{ margin: 0, width: 140 }}>
                      <label htmlFor="reps">Your rep count</label>
                      <input
                        id="reps" inputMode="numeric" value={editReps}
                        onChange={(e) => setEditReps(e.target.value)}
                        placeholder={detectedReps !== null ? String(detectedReps) : ""}
                      />
                    </div>
                    <button className="btn" disabled={editReps.trim() === "" || !movementSettled} title={!movementSettled ? "Loading movement report before saving…" : undefined} onClick={saveLog}>Save set</button>
                  </div>
                  {storageErr && <div className="state bad" role="alert">{storageErr}</div>}
                </div>
              </>
            )}
          </section>
        )}

        {route.name === "progress" && (
          <section className="view" aria-labelledby="pr-h">
            <h1 className="h-page" id="pr-h" tabIndex={-1} ref={h1Ref}>Small steps.<br />Real consistency.</h1>
            <p className="lede">
              {name ? `${name}, here’s your training so far.` : "A little consistency, one set at a time."}
            </p>
            {activeBanner}
            {storageErr && <div className="state bad" role="alert">{storageErr}</div>}
            {logs.length === 0 ? (
              <div className="empty">
                <h2 style={{ fontSize: "1.3rem", marginBottom: ".5rem" }}>Nothing logged yet</h2>
                <p>Your saved sets and analysed reports will appear here.</p>
                <p style={{ marginTop: "1.25rem" }}><button className="btn" onClick={() => navigate({ name: "analyse" })}>Begin analysis</button></p>
              </div>
            ) : (
              <>
                {analysedSets.length >= 3 && (
                  <div className="milestone" role="status">
                    <svg width="26" height="26" viewBox="0 0 26 26" aria-hidden="true" style={{ flexShrink: 0 }}>
                      <circle cx="13" cy="13" r="12" fill="#3158e8" />
                      <path d="M8 13.5 L11.5 17 L18 9.5" fill="none" stroke="#fff" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round" />
                    </svg>
                    <div>
                      <strong>3 analysed sets saved</strong>
                      <p className="muted" style={{ margin: ".2rem 0 0" }}>A great start — keep it up. Companion progress is illustrative; this reflects your current browser history only and updates if entries are removed.</p>
                    </div>
                  </div>
                )}
                <div className="card weekstrip" aria-label="Saved sets over the last seven days">
                  <h3>{uxMeta.weekMode === "calendar" ? "This week (Mon–Sun)" : "Last 7 days"}</h3>
                  <div className="weekdays">
                    {Array.from({ length: 7 }, (_, i) => {
                      const day = new Date();
                      day.setHours(0, 0, 0, 0);
                      if (uxMeta.weekMode === "calendar") {
                        day.setDate(day.getDate() - ((day.getDay() + 6) % 7) + i); // Monday + i
                      } else {
                        day.setDate(day.getDate() - (6 - i));
                      }
                      const nextDay = new Date(day);
                      nextDay.setDate(nextDay.getDate() + 1);
                      const next = nextDay.getTime();
                      const count = logs.filter((l) => {
                        const t = new Date(l.createdAt).getTime();
                        return t >= day.getTime() && t < next;
                      }).length;
                      return (
                        <div className="weekday" key={day.toISOString()}>
                          <span className={count > 0 ? "weekdot has" : "weekdot"} aria-hidden="true">{count > 0 ? count : ""}</span>
                          <span className="weeklabel">{day.toLocaleDateString(undefined, { weekday: "short" })}</span>
                          <span className="weekdate">{day.toLocaleDateString(undefined, { day: "numeric", month: "short" })}</span>
                          <span className="visuallyhidden">{count} saved {count === 1 ? "set" : "sets"}</span>
                        </div>
                      );
                    })}
                  </div>
                </div>
                <RegionActivity sets={logs} />
                {analysedSets.length > 0 && (
                  <div className="card exbars">
                    <h3>Analysed sets by exercise</h3>
                    <p className="muted">Counts of analysed sets per exercise — illustrative history, not measured progress.</p>
                    {EXERCISES.map((e) => {
                      const n = analysedSets.filter((l) => l.exercise === e.id).length;
                      if (n === 0) return null;
                      const max = Math.max(...EXERCISES.map((x) => analysedSets.filter((l) => l.exercise === x.id).length));
                      return (
                        <div className="exbar" key={e.id}>
                          <span className="exbarlabel">{e.name}</span>
                          <span className="exbartrack" aria-hidden="true"><span className="exbarfill" style={{ width: `${(n / max) * 100}%` }} /></span>
                          <span className="exbarcount">{n}</span>
                        </div>
                      );
                    })}
                  </div>
                )}
                <div className="card sessions">
                  <div className="spread" style={{ alignItems: "baseline" }}>
                    <h3>{route.view === "all" ? "All sessions" : "Recent sessions"}</h3>
                    {route.view === "all" ? (
                      <button className="textlink" onClick={() => navigate({ name: "progress" })}>Show recent</button>
                    ) : recentLogs.length > 3 ? (
                      <button className="textlink" onClick={() => navigate({ name: "progress", view: "all" })}>View all</button>
                    ) : null}
                  </div>
                  {progressLogs.map((l) => (
                    <div className="session" key={l.logId}>
                      <span className="recentthumb">
                        {l.analysisId ? (
                          <SessionThumbnail analysisId={l.analysisId} label={`${EXERCISES.find((e) => e.id === l.exercise)?.name ?? l.exercise} video frame`} />
                        ) : (
                          <svg width="22" height="22" viewBox="0 0 24 24" aria-hidden="true"><rect x="3" y="5" width="18" height="14" rx="2" fill="none" stroke="currentColor" strokeWidth="1.5" /></svg>
                        )}
                      </span>
                      <div className="sessionmain">
                        <div className="sessionhead">
                          <strong>{EXERCISES.find((e) => e.id === l.exercise)?.name ?? l.exercise}</strong>
                          {l.recognitionVersion === "analysed-set-v1"
                            ? <span className="pill ok">Analysed set</span>
                            : l.analysisId
                              ? <span className="pill dim">Linked analysis</span>
                              : <span className="pill dim">Manual entry</span>}
                          {viewedPill(l)}
                        </div>
                        <p className="muted">{new Date(l.createdAt).toLocaleString()}</p>
                        <p className="sessionmeta">
                          Logged reps: <strong>{l.loggedReps}</strong>
                          {l.detectedReps !== null && <> · Detected: <strong>{l.detectedReps}</strong></>}
                          {l.load && <> · Load: {l.load}</>}
                        </p>
                        {l.notes && <p className="sessionnotes">“{l.notes}”</p>}
                      </div>
                      <div className="sessionactions">
                        {l.analysisId && <button className="btn sm" onClick={() => resume(l)}>Reopen report</button>}
                        <details className="manage">
                          <summary className="btn ghost sm">Manage</summary>
                          <div className="managebody">
                            {l.analysisId && <button className="btn danger sm" onClick={() => void deleteRemote(l.analysisId!)}>Revoke server analysis</button>}
                            <button className="btn ghost sm" onClick={() => { if (window.confirm("Remove this set from your history? The server analysis is kept.")) deleteLocal(l.logId); }}>Remove from history</button>
                          </div>
                        </details>
                      </div>
                    </div>
                  ))}
                </div>
              </>
            )}
            <p className="muted" style={{ marginTop: "1.25rem" }}>
              History stays in this browser. Clearing site data or changing browsers loses it.
              {" "}Removing a log keeps its server analysis; revoke server access separately under Manage.
            </p>
          </section>
        )}

        {route.name === "settings" && (
          <section className="view" aria-labelledby="set-h">
            <h1 className="h-page" id="set-h" tabIndex={-1} ref={h1Ref}>Settings</h1>
            <p className="lede">Guest profile and local preferences. No account — everything stays in this browser.</p>
            <SettingsPanel
              displayName={name}
              onNameChange={saveName}
              metadata={uxMeta}
              onSave={saveSettings}
              onBack={() => navigate({ name: "home" })}
              error={uxMetaErr}
            />
          </section>
        )}
      </main>

      <nav className="bottomnav" aria-label="Primary">
        {navBtn("home", "Home", navItems[0].icon, false)}
        {navBtn("analyse", "Analyse", navItems[1].icon, true)}
        {navBtn("progress", "Progress", navItems[2].icon, false)}
      </nav>
    </div>
  );
}
