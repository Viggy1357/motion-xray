"use client";

import React from "react";
import styles from "./ExperienceExtras.module.css";
import SessionThumbnail from "./SessionThumbnail";
import { useSessionCoaching } from "../lib/coaching-session";

export interface HomeLastFocusProps {
  analysisId: string;
  exerciseLabel: string;
  createdAt: string;
  onOpen: () => void;
}

function formatDate(iso: string): string {
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso;
  return d.toLocaleDateString(undefined, { year: "numeric", month: "short", day: "numeric" });
}

// Shows the ACTUAL cached coaching cue for the most recent session when one
// exists in memory; otherwise a neutral "last review" line. No replay seek
// from Home — the user opens the report first. Parent validates ownership.
export default function HomeLastFocus({ analysisId, exerciseLabel, createdAt, onOpen }: HomeLastFocusProps) {
  const coaching = useSessionCoaching(analysisId);
  const hasCue = coaching !== null && (coaching.observation !== null || coaching.nextSetCue !== null);
  const showThumb =
    coaching !== null && coaching.sourceS !== null && Number.isFinite(coaching.sourceS);

  return (
    <section className={styles.card} aria-label="Last focus">
      <div className={styles.focusRow}>
        {showThumb && coaching && coaching.sourceS !== null && (
          <SessionThumbnail
            analysisId={analysisId}
            sourceS={coaching.sourceS}
            label={
              coaching.segmentOrdinal !== null
                ? `Segment ${coaching.segmentOrdinal}`
                : "Session preview"
            }
          />
        )}
        <div className={styles.focusBody}>
          <p className={styles.muted} style={{ margin: 0 }}>
            {exerciseLabel} · {formatDate(createdAt)}
          </p>
          {hasCue && coaching ? (
            <>
              {coaching.observation !== null && (
                <p className={styles.focusText}>{coaching.observation}</p>
              )}
              {coaching.nextSetCue !== null && (
                <p className={styles.muted} style={{ margin: ".3rem 0 0" }}>
                  <strong>Next set cue:</strong> {coaching.nextSetCue}
                </p>
              )}
            </>
          ) : (
            <p className={styles.muted} style={{ margin: ".3rem 0 0" }}>
              Last review: open the report to see your measured results.
            </p>
          )}
          <div className={styles.actions}>
            <button type="button" className={styles.primaryBtn} onClick={onOpen}>
              Open report
            </button>
          </div>
        </div>
      </div>
    </section>
  );
}
