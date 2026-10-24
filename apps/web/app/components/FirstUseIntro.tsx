"use client";

import React from "react";
import styles from "./ExperienceExtras.module.css";

export interface FirstUseIntroProps {
  onContinue: () => void;
  onSkip: () => void;
}

// Restrained first-visit explanation. Neither button grants camera or upload
// consent; those are requested separately at the point of use. "Seen"
// persistence is owned by the parent.
export default function FirstUseIntro({ onContinue, onSkip }: FirstUseIntroProps) {
  return (
    <section className={styles.card} aria-labelledby="first-use-title">
      <h2 id="first-use-title" className={styles.title}>
        How Motion X-Ray works
      </h2>
      <ul className={styles.introList}>
        <li>Four supported exercises: squat, lat pulldown, dumbbell curl, and incline chest press.</li>
        <li>Record a set in the app or upload an existing video of one.</li>
        <li>Pose estimates are provisional measurements, not medical or diagnostic judgments.</li>
        <li>Your history stays on this device; you can review or delete it at any time.</li>
      </ul>
      <div className={styles.actions}>
        <button type="button" className={styles.primaryBtn} onClick={onContinue}>
          Continue
        </button>
        <button type="button" className={styles.ghostBtn} onClick={onSkip}>
          Skip intro
        </button>
      </div>
      <p className={styles.muted}>
        Continuing or skipping does not grant camera or upload access — those are asked for separately, only when you use them.
      </p>
    </section>
  );
}
