"use client";

import React from "react";
import styles from "./ExperienceExtras.module.css";

export interface ProgressCompanionProps {
  eligibleSets: number;
}

// Compact companion strip: neutral count of ACTUAL eligible saved sets.
// No measured muscle-growth claims, no rotating mesh, no fabricated rewards.
export default function ProgressCompanion({ eligibleSets }: ProgressCompanionProps) {
  const count =
    typeof eligibleSets === "number" && Number.isFinite(eligibleSets) && eligibleSets > 0
      ? Math.floor(eligibleSets)
      : 0;
  return (
    <div className={styles.companion} aria-label="Progress companion">
      {/* eslint-disable-next-line @next/next/no-img-element */}
      <img
        className={styles.companionArt}
        src="/companion/athlete.png"
        alt=""
        aria-hidden="true"
        onError={(e) => {
          // Resilient fallback: hide artwork if the asset is unavailable.
          (e.currentTarget as HTMLImageElement).style.display = "none";
        }}
      />
      <p className={styles.companionText}>
        {count === 0
          ? "No eligible saved sets yet."
          : `${count} eligible saved ${count === 1 ? "set" : "sets"} so far.`}
      </p>
    </div>
  );
}
