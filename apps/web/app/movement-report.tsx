"use client";

import { useEffect, useState } from "react";
import type { components } from "../generated/api";

type Report = components["schemas"]["PrototypeAnalysisResult"];
type Metric = components["schemas"]["Metric"];
type Rep = components["schemas"]["Rep"];

const METRIC_LABELS: Record<string, string> = {
  "elbow_angle/estimated_3d/excursion": "Elbow range of motion (estimated 3D)",
  "elbow_angle/estimated_3d/end": "Return elbow angle (estimated 3D)",
  "torso_axis_angle/projected_2d/excursion": "Torso axis excursion (camera plane)",
  "upper_arm_torso_angle/estimated_3d/bottom": "Upper-arm to torso angle (estimated 3D)",
  "elbow_angle/projected_2d": "Elbow angle (camera plane)",
  "elbow_angle/estimated_3d": "Elbow angle (estimated 3D)",
  "upper_arm_torso_angle/projected_2d": "Upper-arm to torso angle (camera plane)",
  "upper_arm_torso_angle/estimated_3d": "Upper-arm to torso angle (estimated 3D)",
  "torso_axis_angle/projected_2d": "Torso axis angle (camera plane)",
};
const TOP_METRIC_IDS = [
  "elbow_angle/estimated_3d/excursion",
  "elbow_angle/estimated_3d/end",
  "torso_axis_angle/projected_2d/excursion",
  "upper_arm_torso_angle/estimated_3d/bottom",
];

function humanize(id: string): string {
  return METRIC_LABELS[id] ?? id.replaceAll("_", " ").replaceAll("/", " · ");
}

function fmtValue(m: Metric): string | null {
  if (m.value == null) return null;
  const unit = m.unit.toLowerCase();
  const digits = unit === "s" || unit === "sec" || unit === "seconds" ? 2 : 1;
  return `${m.value.toFixed(digits)} ${m.unit}`;
}

function isReport(data: unknown): data is Report {
  if (typeof data !== "object" || data === null) return false;
  const d = data as { schema_version?: unknown; quality?: unknown; reps?: unknown; metrics?: unknown };
  return (
    d.schema_version === "0.3.0" &&
    typeof d.quality === "object" && d.quality !== null &&
    Array.isArray(d.reps) &&
    Array.isArray(d.metrics)
  );
}

function seekTo(seconds: number): void {
  const v = document.querySelector("video");
  if (!v) return;
  v.currentTime = seconds;
  void v.play().catch(() => undefined);
}

function MetricLine({ m }: { m: Metric }) {
  const v = fmtValue(m);
  return (
    <tr>
      <td>{humanize(m.id)}</td>
      <td>
        {v !== null ? v : <span className="muted">Unavailable{m.reason ? ` — ${m.reason.replaceAll("_", " ")}` : ""}</span>}
      </td>
    </tr>
  );
}

function RepMetrics({ rep, metrics }: { rep: Rep; metrics: Metric[] }) {
  const top = metrics.filter((m) => TOP_METRIC_IDS.includes(m.id));
  const rest = metrics.filter((m) => !TOP_METRIC_IDS.includes(m.id));
  const shown = top.length > 0 ? top : metrics.slice(0, 4);
  return (
    <div style={{ marginBottom: ".9rem" }}>
      <h4 style={{ margin: "0 0 .3rem", fontSize: ".95rem" }}>
        Segment {rep.ordinal} <span className="muted" style={{ fontWeight: 400 }}>· {rep.start_s.toFixed(2)}s – {rep.end_s.toFixed(2)}s</span>{" "}
        <button type="button" className="btn ghost sm" style={{ marginLeft: ".4rem" }} onClick={() => seekTo(rep.start_s)} aria-label={`Play video from segment ${rep.ordinal} start`}>
          ▶ Play
        </button>
      </h4>
      {metrics.length === 0 ? (
        <p className="muted" style={{ margin: ".2rem 0" }}>No measurements for this rep.</p>
      ) : (
        <>
          <table>
            <tbody>{shown.map((m, i) => <MetricLine key={`${m.id}-${i}`} m={m} />)}</tbody>
          </table>
          {rest.length > 0 && (
            <details style={{ marginTop: ".3rem" }}>
              <summary className="muted" style={{ cursor: "pointer" }}>All measurements for this rep ({metrics.length})</summary>
              <table>
                <tbody>{metrics.map((m, i) => <MetricLine key={`${m.id}-all-${i}`} m={m} />)}</tbody>
              </table>
            </details>
          )}
        </>
      )}
    </div>
  );
}

export default function MovementReport({ analysisId, onReport }: { analysisId: string; onReport: (report: Report | null) => void }) {
  const [report, setReport] = useState<Report | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [retry, setRetry] = useState(0);

  useEffect(() => {
    const ctrl = new AbortController();
    setReport(null);
    setError(null);
    setLoading(true);
    onReport(null);
    void (async () => {
      try {
        const res = await fetch(`/api/analyses/${analysisId}/movement-report`, {
          credentials: "include",
          signal: ctrl.signal,
        });
        if (!res.ok) {
          let msg = `Request failed (${res.status})`;
          try {
            const body: unknown = await res.json();
            const b = body as { message?: unknown; detail?: unknown };
            if (typeof b.message === "string" && b.message) msg = b.message;
            else if (typeof b.detail === "string" && b.detail) msg = b.detail;
          } catch { /* keep status message */ }
          throw new Error(msg);
        }
        const data: unknown = await res.json();
        if (!isReport(data)) throw new Error("The server returned an unexpected movement report format.");
        setReport(data);
        onReport(data);
      } catch (e) {
        if ((e as Error).name === "AbortError") return;
        setError((e as Error).message);
      } finally {
        if (!ctrl.signal.aborted) setLoading(false);
      }
    })();
    return () => ctrl.abort();
  }, [analysisId, retry, onReport]);

  if (loading) {
    return (
      <div className="state" role="status" aria-live="polite">
        <strong>Movement insights</strong> — loading your movement report…
      </div>
    );
  }

  if (error || !report) {
    return (
      <div className="state bad" role="alert">
        <strong>Movement insights</strong>
        <p style={{ margin: ".3rem 0 .6rem" }}>{error ?? "Movement report is unavailable."}</p>
        <button type="button" className="btn ghost sm" onClick={() => setRetry((n) => n + 1)}>Retry</button>
      </div>
    );
  }

  const q = report.quality;
  const visibility = q.expected_supporting_samples > 0
    ? Math.round((q.valid_observed_samples / q.expected_supporting_samples) * 100)
    : null;
  const completed = report.reps.filter((r) => r.completion_status === "completed");
  const fragments = report.reps.filter((r) => r.completion_status !== "completed");
  const coverageEntries = Object.entries(q.per_metric_coverage);
  const byRep = new Map<string, Metric[]>();
  for (const m of report.metrics) {
    const list = byRep.get(m.rep_id) ?? [];
    list.push(m);
    byRep.set(m.rep_id, list);
  }
  const pa = report.prototype_assessment;

  return (
    <section aria-labelledby="movement-h" style={{ marginBottom: "1.25rem" }}>
      <div className="row" style={{ justifyContent: "space-between", marginBottom: ".6rem" }}>
        <h2 id="movement-h" style={{ fontSize: "1.5rem", margin: 0 }}>Movement insights</h2>
        <span className="pill dim">Experimental</span>
      </div>

      <div className="grid" style={{ marginBottom: "1rem" }}>
        <div className="card">
          <p className="muted">Estimated completed cycles</p>
          {report.detected_rep_count !== null && report.detected_rep_count !== undefined ? (
            <p className="big">{report.detected_rep_count}</p>
          ) : (
            <>
              <p className="big">—</p>
              <p className="muted">Unavailable{report.detected_rep_count_unavailable_reason ? ` — ${report.detected_rep_count_unavailable_reason.replaceAll("_", " ")}` : ""}</p>
            </>
          )}
        </div>
        <div className="card">
          <p className="muted">Partial / excluded motion fragments</p>
          <p className="big">{fragments.length}</p>
          {fragments.length > 0 && <p className="muted">Not counted as completed cycles.</p>}
        </div>
        <div className="card">
          <p className="muted">Signal visibility</p>
          {visibility !== null ? (
            <>
              <p className="big">{visibility}%</p>
              <p className="muted">{q.valid_observed_samples} of {q.expected_supporting_samples} supporting samples observed. This describes pose-signal visibility, not accuracy.</p>
            </>
          ) : (
            <>
              <p className="big">—</p>
              <p className="muted">No supporting samples expected for this profile.</p>
            </>
          )}
        </div>
      </div>

      {coverageEntries.length > 0 && (
        <div className="card" style={{ marginBottom: "1rem" }}>
          <h3>Per-metric signal visibility</h3>
          {coverageEntries.map(([id, cov]) => {
            const pct = Math.round(cov * 100);
            return (
              <div key={id} style={{ margin: ".45rem 0" }}>
                <div className="spread" style={{ alignItems: "baseline" }}>
                  <span style={{ fontSize: ".88rem" }}>{humanize(id)}</span>
                  <span className="muted">{pct}%</span>
                </div>
                <div className="progress" role="progressbar" aria-valuenow={pct} aria-valuemin={0} aria-valuemax={100} aria-label={`${humanize(id)} signal visibility`} style={{ margin: ".2rem 0 0" }}>
                  <div style={{ width: `${pct}%` }} />
                </div>
              </div>
            );
          })}
        </div>
      )}

      {pa.status === "unavailable" && (
        <div className="state warn" role="status">
          <strong>Reference match unavailable.</strong>{" "}
          {pa.policy_version
            ? `The reference comparison policy (${pa.policy_version}) is pending and not yet approved, so no match estimate or technique grade is shown.`
            : "No approved reference comparison policy is available for this exercise profile, so no match estimate or technique grade is shown."}{" "}
          Your measured values below are still reported as-is.
          {pa.missing_reasons.length > 0 && (
            <p className="muted" style={{ margin: ".3rem 0 0" }}>{pa.missing_reasons.join("; ").replaceAll("_", " ")}</p>
          )}
        </div>
      )}

      {completed.length > 0 && (
        <div className="card" style={{ marginBottom: "1rem" }}>
          <h3>Rep times</h3>
          <p className="muted">Detected segments from the pose signal — completed cycles, not manually confirmed reps.</p>
          <table>
            <thead><tr><th>#</th><th>Start</th><th>End</th><th>Status</th><th></th></tr></thead>
            <tbody>
              {completed.map((r) => (
                <tr key={r.id}>
                  <td>{r.ordinal}</td>
                  <td>{r.start_s.toFixed(2)}s</td>
                  <td>{r.end_s.toFixed(2)}s</td>
                  <td><span className="pill ok">completed</span></td>
                  <td><button type="button" className="btn ghost sm" onClick={() => seekTo(r.start_s)} aria-label={`Play video from segment ${r.ordinal}`}>▶</button></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {fragments.length > 0 && (
        <details className="card" style={{ marginBottom: "1rem" }}>
          <summary style={{ cursor: "pointer" }}>
            <strong>Partial / excluded fragments ({fragments.length})</strong>{" "}
            <span className="muted">— not counted as completed cycles</span>
          </summary>
          <table style={{ marginTop: ".5rem" }}>
            <thead><tr><th>Segment</th><th>Start</th><th>End</th><th>Status</th><th></th></tr></thead>
            <tbody>
              {fragments.map((r) => (
                <tr key={r.id}>
                  <td>{r.ordinal}</td>
                  <td>{r.start_s.toFixed(2)}s</td>
                  <td>{r.end_s.toFixed(2)}s</td>
                  <td><span className="pill warn">{r.completion_status.replaceAll("_", " ")}</span></td>
                  <td><button type="button" className="btn ghost sm" onClick={() => seekTo(r.start_s)} aria-label={`Play video from segment ${r.ordinal}`}>▶</button></td>
                </tr>
              ))}
            </tbody>
          </table>
        </details>
      )}

      <div className="card" style={{ marginBottom: "1rem" }}>
        <h3>Measured values</h3>
        {completed.length === 0 ? (
          <p className="muted">No completed cycles were segmented, so no per-rep measurements are available.</p>
        ) : (
          completed.map((r) => <RepMetrics key={r.id} rep={r} metrics={byRep.get(r.id) ?? []} />)
        )}
      </div>

      <p className="muted" style={{ maxWidth: "68ch" }}>
        Angles are in degrees, times in seconds. 3D values come from an uncalibrated estimated-3D pose model; the torso axis is measured in the camera plane (image-up), not against gravity. Coverage reflects how much of the supporting pose signal was visible — it is not an accuracy score, and no technique judgement is made without an approved reference.
      </p>
    </section>
  );
}
