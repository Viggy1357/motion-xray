"use client";

import { useEffect, useState } from "react";
import type { components } from "../generated/api";
import GroundedCoaching from "./grounded-coaching";
import styles from "./movement-report.module.css";

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
  "knee_angle/estimated_3d/bottom": "Knee angle at bottom (estimated 3D)",
  "knee_angle/estimated_3d/excursion": "Knee range of motion (estimated 3D)",
  "knee_angle/projected_2d/bottom": "Knee angle at bottom (camera plane)",
  "knee_angle/projected_2d/excursion": "Knee range of motion (camera plane)",
  "hip_angle/estimated_3d/bottom": "Hip angle at bottom (estimated 3D)",
  "hip_angle/estimated_3d/excursion": "Hip range of motion (estimated 3D)",
  "hip_angle/projected_2d/bottom": "Hip angle at bottom (camera plane)",
  "hip_angle/projected_2d/excursion": "Hip range of motion (camera plane)",
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

function fmtDeviation(m: Metric): string | null {
  if (m.deviation == null) return null;
  const d = m.deviation;
  const sign = d > 0 ? "+" : "";
  return `${sign}${d.toFixed(1)} ${m.unit}`;
}

function fmtInterval(m: Metric): string | null {
  if (!m.reference_interval) return null;
  const [lo, hi] = m.reference_interval;
  return `${lo.toFixed(1)} – ${hi.toFixed(1)} ${m.unit}`;
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
  window.dispatchEvent(new CustomEvent("mxr:seek-source", { detail: { seconds } }));
}

function MetricLine({ m, showReference }: { m: Metric; showReference: boolean }) {
  const v = fmtValue(m);
  const interval = showReference ? fmtInterval(m) : null;
  const deviation = showReference ? fmtDeviation(m) : null;
  return (
    <tr>
      <td>{humanize(m.id)}</td>
      <td>
        {v !== null ? v : <span className="muted">Unavailable{m.reason ? ` — ${m.reason.replaceAll("_", " ")}` : ""}</span>}
      </td>
      {showReference && (
        <>
          <td>{interval !== null ? <span className="muted">{interval}</span> : <span className="muted">—</span>}</td>
          <td>{deviation !== null ? <span className="muted">{deviation}</span> : <span className="muted">—</span>}</td>
        </>
      )}
    </tr>
  );
}

function RepMetrics({ rep, metrics, showReference }: { rep: Rep; metrics: Metric[]; showReference: boolean }) {
  const preferred = metrics.some((m) => m.id.startsWith("knee_angle/"))
    ? ["knee_angle/estimated_3d/bottom", "knee_angle/estimated_3d/excursion", "hip_angle/estimated_3d/bottom", "torso_axis_angle/projected_2d/excursion"]
    : TOP_METRIC_IDS;
  const top = metrics.filter((m) => preferred.includes(m.id));
  const rest = metrics.filter((m) => !preferred.includes(m.id));
  const shown = top.length > 0 ? top : metrics.slice(0, 4);
  // TOP_METRIC_IDS is lat-pulldown-specific; other exercises fall back to the
  // first four metrics with generic humanized labels (no big rewrite).
  const header = showReference ? (
    <thead>
      <tr><th>Metric</th><th>Measured</th><th>Reference band</th><th>Signed deviation</th></tr>
    </thead>
  ) : null;
  return (
    <div className={styles.repBlock}>
      <h4 className={styles.repHeading}>
        Segment {rep.ordinal} <span className={styles.repTimes}>· {rep.start_s.toFixed(2)}s – {rep.end_s.toFixed(2)}s</span>{" "}
        <button type="button" className={styles.playButton} onClick={() => seekTo(rep.start_s)} aria-label={`Play video from segment ${rep.ordinal} start`}>
          Play
        </button>
      </h4>
      {metrics.length === 0 ? (
        <p className="muted" style={{ margin: ".2rem 0" }}>No measurements for this rep.</p>
      ) : (
        <>
          <div className={styles.tableWrap}>
            <table>
              {header}
              <tbody>{shown.map((m, i) => <MetricLine key={`${m.id}-${i}`} m={m} showReference={showReference} />)}</tbody>
            </table>
          </div>
          {rest.length > 0 && (
            <details className={styles.inlineDetails}>
              <summary className="muted">All measurements for this rep ({metrics.length})</summary>
              <div className={styles.tableWrap}>
                <table>
                  {header}
                  <tbody>{metrics.map((m, i) => <MetricLine key={`${m.id}-all-${i}`} m={m} showReference={showReference} />)}</tbody>
                </table>
              </div>
            </details>
          )}
        </>
      )}
    </div>
  );
}

function ExperimentalMatch({ report }: { report: Report }) {
  const pa = report.prototype_assessment;
  const prov = report.provenance;
  if (pa.estimated_match == null) return null;
  const policyVersion = prov.experimental_policy_version ?? pa.policy_version ?? "unknown";
  const referenceId = prov.reference_id;
  const referenceName = prov.reference_name ?? (referenceId === "qmotion_roi" ? "QMotion" : (referenceId ?? "not reported"));
  const referenceView = prov.reference_view_id;
  const reviewStatus = prov.reference_review_status;
  const matchedCycles = prov.matched_cycles;
  const omittedCycles = prov.omitted_cycle_count;
  const normDeg = prov.match_normalization_degrees != null ? String(prov.match_normalization_degrees) : "not reported";
  const coverageThreshold = prov.match_coverage_threshold != null
    ? `${Math.round(Number(prov.match_coverage_threshold) * 100)}%`
    : null;
  const calibration = prov.calibration_status;
  const referenceRepCount = prov.reference_rep_count;
  return (
    <div className={styles.innerPanel} aria-label="Experimental reference match">
      <div className="row" style={{ justifyContent: "space-between", alignItems: "baseline" }}>
        <h3 style={{ margin: 0 }}>Experimental reference match</h3>
        <span className="pill warn">Partial comparison · unreviewed calibration</span>
      </div>
      <p className="big" style={{ margin: ".3rem 0" }}>{pa.estimated_match.toFixed(1)}<span className="muted" style={{ fontSize: "1rem" }}> / 100</span></p>
      <p className="muted" style={{ margin: ".2rem 0" }}>
        Experimental resemblance index: a low-confidence resemblance to the {referenceName} reference{referenceView ? ` (view: ${referenceView})` : ""}, the primary reference source for this profile.
        This is not a technique score, not a numerical accuracy percentage, and it has not been owner-reviewed or validated.
      </p>
      <p className="muted" style={{ margin: ".2rem 0" }}>
        This compares only the listed measured features, not overall technique quality. The camera geometry and normalization remain unreviewed; omitted features are listed below.
      </p>
      <details style={{ marginTop: ".4rem" }}>
        <summary className="muted" style={{ cursor: "pointer" }}>How this estimate is computed</summary>
        <ul className="muted" style={{ margin: ".4rem 0 0", paddingLeft: "1.2rem" }}>
          <li>For each measured value x and reference band [L, U]: distance = max(L − x, 0, x − U) — the distance outside the band (0 when inside).</li>
          <li>Resemblance per metric = 100 × max(0, 1 − distance / {normDeg}). The {normDeg}-degree normalization is an explicit, unreviewed engineering hypothesis — not a validated threshold.</li>
          {prov.match_aggregation === "equal_metric_mean_per_cycle_then_cycle_mean" ? (
            <li>Each of the four compared metrics contributes equally: per cycle the mean of the four per-metric resemblance values is taken, then averaged across complete eligible cycles.</li>
          ) : (
            <li>Three families weighted equally per cycle: torso dynamic, arm range of motion (two components averaged), shoulder drive; then averaged across complete eligible cycles.</li>
          )}
          {coverageThreshold !== null ? (
            <li>Each cycle needs all four metrics observed with ≥ {coverageThreshold} supporting coverage. This is a data-completeness requirement — it does not mean {coverageThreshold} accuracy.</li>
          ) : (
            <li>Each cycle needs all four metrics observed with sufficient supporting coverage. This is a data-completeness requirement — it does not describe accuracy.</li>
          )}
          {matchedCycles !== undefined && <li>Matched cycles: {matchedCycles}{omittedCycles !== undefined && omittedCycles !== "0" ? ` · omitted cycles: ${omittedCycles}` : ""}.</li>}
          <li>Policy: {policyVersion}{calibration ? ` · calibration: ${calibration.replaceAll("_", " ")}` : ""}{reviewStatus ? ` · reference review: ${reviewStatus.replaceAll("_", " ")}` : ""}.</li>
        </ul>
      </details>
      {pa.omitted_components.length > 0 && (
        <p className="muted" style={{ margin: ".4rem 0 0" }}>
          Omitted from comparison: {pa.omitted_components.map((c) => c.replaceAll("_", " ")).join(", ")}.
        </p>
      )}
      {pa.missing_reasons.length > 0 && (
        <p className="muted" style={{ margin: ".2rem 0 0" }}>{pa.missing_reasons.join("; ").replaceAll("_", " ")}</p>
      )}
    </div>
  );
}

export default function MovementReport({ analysisId, exercise, onReport }: { analysisId: string; exercise?: string; onReport: (report: Report | null, settled: boolean) => void }) {
  const [report, setReport] = useState<Report | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [retry, setRetry] = useState(0);
  const [activeSeg, setActiveSeg] = useState<string | null>(null);

  useEffect(() => {
    const ctrl = new AbortController();
    setReport(null);
    setError(null);
    setLoading(true);
    setActiveSeg(null);
    onReport(null, false); // fetch in flight: parent must not treat null as 'no report'
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
        if (ctrl.signal.aborted) return; // never leak a settled callback into a superseded job
        setReport(data);
        onReport(data, true);
      } catch (e) {
        if ((e as Error).name === "AbortError") return;
        if (ctrl.signal.aborted) return;
        setError((e as Error).message);
        onReport(null, true); // settled with failure: honest null, no pending state
      } finally {
        if (!ctrl.signal.aborted) setLoading(false);
      }
    })();
    return () => ctrl.abort();
  }, [analysisId, retry, onReport]);

  // Active segment follows ACTUAL playback: the player broadcasts the
  // original source PTS (mxr:source-time). A completed interval wins; an
  // excluded fragment is the fallback; outside every interval select none.
  // Never fabricate boundaries or rep events.
  useEffect(() => {
    if (!report) return;
    const completed = report.reps.filter((r) => r.completion_status === "completed");
    const excluded = report.reps.filter((r) => r.completion_status !== "completed");
    const onSourceTime = (ev: Event) => {
      const detail = (ev as CustomEvent<unknown>).detail as
        | { analysisId?: unknown; sourceS?: unknown }
        | null;
      if (!detail || detail.analysisId !== analysisId) return;
      const sourceS = detail.sourceS;
      if (typeof sourceS !== "number" || !Number.isFinite(sourceS)) return;
      const inInterval = (r: Rep) => sourceS >= r.start_s && sourceS <= r.end_s;
      const hit = completed.find(inInterval) ?? excluded.find(inInterval) ?? null;
      setActiveSeg(hit ? hit.id : null);
    };
    window.addEventListener("mxr:source-time", onSourceTime);
    return () => window.removeEventListener("mxr:source-time", onSourceTime);
  }, [report, analysisId]);

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
  const completed = [...report.reps]
    .filter((r) => r.completion_status === "completed")
    .sort((a, b) => a.start_s - b.start_s || a.ordinal - b.ordinal);
  const fragments = [...report.reps]
    .filter((r) => r.completion_status !== "completed")
    .sort((a, b) => a.start_s - b.start_s || a.ordinal - b.ordinal);
  // Primary timeline shows ONLY actual completed cycles. Excluded/partial
  // fragments live exclusively in the disclosure below (single list, no
  // duplicates) so a zero-completed result does not flood the timeline.
  const coverageEntries = Object.entries(q.per_metric_coverage);
  const byRep = new Map<string, Metric[]>();
  for (const m of report.metrics) {
    const list = byRep.get(m.rep_id) ?? [];
    list.push(m);
    byRep.set(m.rep_id, list);
  }
  const pa = report.prototype_assessment;
  const prov = report.provenance;
  const hasEstimate = pa.estimated_match != null;
  const showReference = report.metrics.some((m) => m.reference_interval != null || m.deviation != null);
  const profileUnavailable = pa.missing_reasons.some((r) => r.includes("exercise_profile_unavailable"));
  const referenceCalibrationPending = pa.missing_reasons.some((r) => r.includes("reference_calibration_pending"));
  const noEligibleCycles = pa.missing_reasons.some((r) => r.includes("no_eligible_cycles"));
  const referenceRepCount = prov.reference_rep_count;

  return (
    <section aria-labelledby="movement-h" className={styles.report}>
      <div className={styles.headingRow}>
        <h2 id="movement-h" className={styles.heading}>Movement insights</h2>
        <span className="pill dim">Experimental</span>
      </div>

      {completed.length > 0 ? (
        <nav className={styles.chipStrip} aria-label="Completed cycles">
          {completed.map((r) => (
            <button
              key={r.id}
              type="button"
              className={styles.chip}
              data-active={activeSeg === r.id || undefined}
              aria-pressed={activeSeg === r.id}
              title={`Segment ${r.ordinal} · ${r.start_s.toFixed(2)}s – ${r.end_s.toFixed(2)}s`}
              aria-label={`Play video from segment ${r.ordinal}`}
              onClick={() => { setActiveSeg(r.id); seekTo(r.start_s); }}
            >
              <span className={styles.chipLabel}>Segment {r.ordinal}</span>
              <span className={styles.chipTime}>{r.start_s.toFixed(2)}s – {r.end_s.toFixed(2)}s</span>
            </button>
          ))}
        </nav>
      ) : (
        <p className={styles.emptyNote} role="status">
          Analysis finished, but no full repetitions were identified in this video.
          {fragments.length > 0
            ? ` ${fragments.length} partial or excluded fragment${fragments.length === 1 ? " was" : "s were"} detected — see “Partial / excluded fragments” below for exact timestamps and playback.`
            : ""}{" "}
          Signal visibility below reflects pose-signal visibility, not accuracy.
        </p>
      )}

      <div className={styles.panel} aria-label="Session summary">
        <div className={styles.summaryGrid}>
          <div className={styles.summaryCell}>
            <p className={styles.summaryLabel}>Completed cycles</p>
            <p className={styles.summaryValue}>{report.detected_rep_count ?? "—"}</p>
          </div>
          <div className={styles.summaryCell}>
            <p className={styles.summaryLabel}>Partial fragments</p>
            <p className={styles.summaryValue}>{fragments.length}</p>
          </div>
          <div className={styles.summaryCell}>
            <p className={styles.summaryLabel}>Signal visibility</p>
            <p className={styles.summaryValue}>{visibility !== null ? `${visibility}%` : "—"}</p>
          </div>
        </div>
        {report.detected_rep_count == null && (
          <p className={styles.note}>Completed cycles unavailable{report.detected_rep_count_unavailable_reason ? ` — ${report.detected_rep_count_unavailable_reason.replaceAll("_", " ")}` : ""}.</p>
        )}
        <p className={styles.note}>Visibility reflects pose-signal visibility, not accuracy.</p>
        <details className={styles.inlineDetails}>
          <summary className={styles.noteSummary}>Visibility details</summary>
          <p className={styles.note}>
            {visibility !== null
              ? `${q.valid_observed_samples} of ${q.expected_supporting_samples} supporting samples observed.`
              : "No supporting samples expected for this profile."}
            {fragments.length > 0 ? " Partial fragments are not counted as completed cycles." : ""}
          </p>
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
        </details>
      </div>

      {completed.length > 0 && report.metrics.some((m) => m.value != null) && (
        <GroundedCoaching analysisId={analysisId} exercise={exercise} reps={completed} />
      )}

      {hasEstimate && (
        <details className={styles.disclosure}>
          <summary><strong>Reference comparison · experimental</strong>{" "}<span className="pill warn">always partial</span></summary>
          <ExperimentalMatch report={report} />
        </details>
      )}

      {pa.status === "unavailable" && (
        <div className="state warn" role="status">
          <strong>Reference match unavailable.</strong>{" "}
          {profileUnavailable
            ? "The exercise profile for this movement is still pending, so no reference comparison can run yet — this is not a segmentation failure."
            : referenceCalibrationPending
              ? "The reference videos for this exercise have not been calibrated yet, so no reference comparison can run — this is a pending-calibration state, not a measurement failure and not an unsupported profile."
              : noEligibleCycles
              ? "There are insufficient compatible observed measurements to compare against the reference, so no match estimate is shown."
              : pa.policy_version
                ? `The reference comparison policy (${pa.policy_version}) is pending and not yet approved, so no match estimate is shown.`
                : "No approved reference comparison policy is available for this exercise profile, so no match estimate is shown."}{" "}
          Your measured values below are still reported as-is.
          {pa.missing_reasons.length > 0 && (
            <p className="muted" style={{ margin: ".3rem 0 0" }}>{pa.missing_reasons.join("; ").replaceAll("_", " ")}</p>
          )}
        </div>
      )}

      {fragments.length > 0 && (
        <details className={styles.disclosure}>
          <summary>
            <strong>Partial / excluded fragments ({fragments.length})</strong>{" "}
            <span className="muted">— not counted as completed cycles</span>
          </summary>
          <div className={styles.tableWrap}>
            <table>
              <thead><tr><th>Segment</th><th>Start</th><th>End</th><th>Status</th><th></th></tr></thead>
              <tbody>
                {fragments.map((r) => (
                  <tr key={r.id} data-active={activeSeg === r.id || undefined}>
                    <td>{r.ordinal}</td>
                    <td>{r.start_s.toFixed(2)}s</td>
                    <td>{r.end_s.toFixed(2)}s</td>
                    <td><span className="pill warn">{r.completion_status.replaceAll("_", " ")}</span></td>
                    <td><button type="button" className={styles.playButton} onClick={() => { setActiveSeg(r.id); seekTo(r.start_s); }} aria-label={`Play video from segment ${r.ordinal}`}>Play</button></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </details>
      )}

      <details className={styles.disclosure}>
        <summary><strong>Measurements and reference details</strong>{" "}<span className="muted">— full measured values, provenance and missing reasons</span></summary>
        <p className="muted" style={{ maxWidth: "68ch" }}>
          Angles are in degrees, times in seconds. 3D values come from an uncalibrated estimated-3D pose model; the torso axis is measured in the camera plane (image-up), not against gravity. Coverage reflects how much of the supporting pose signal was visible — it is not an accuracy score, and no technique judgement is made without an approved reference.
        </p>
        {showReference && (
          <p className="muted" style={{ margin: ".2rem 0 .6rem" }}>
            Reference bands are observed min/max ranges from {referenceRepCount != null ? `n=${referenceRepCount} reference windows` : "the reference windows"} (unreviewed camera) — not acceptable technique tolerances. Signed deviation is negative below the band, positive above it, and 0 inside. Labels indicate camera-plane (projected 2D) or estimated-3D measurements; these are descriptive only.
          </p>
        )}
        {completed.length === 0 ? (
          <p className="muted">
            {profileUnavailable
              ? "No completed cycles are shown because the exercise profile is still pending — this is not a segmentation failure."
              : "No completed cycles were segmented, so no per-rep measurements are available."}
          </p>
        ) : (
          completed.map((r) => <RepMetrics key={r.id} rep={r} metrics={byRep.get(r.id) ?? []} showReference={showReference} />)
        )}
      </details>

      <p className={styles.note}>
        3D values come from an uncalibrated estimated-3D pose model; the torso axis is measured in the camera plane, not against gravity. Full measurement notes are in “Measurements and reference details”.
      </p>
    </section>
  );
}
