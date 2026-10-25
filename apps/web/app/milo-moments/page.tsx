"use client";

import {
  ReactElement,
  useCallback,
  useEffect,
  useState,
} from "react";
import AthleteCompanion from "../athlete-companion";
import {
  MiloHomeRest,
  MiloProcessingBuddy,
} from "../components/MiloMoments";
import styles from "../components/MiloMoments.module.css";

export default function MiloMomentsPage(): ReactElement {
  const [active, setActive] = useState<boolean>(true);
  const [reducedMotion, setReducedMotion] = useState<boolean>(false);

  useEffect(() => {
    if (typeof window === "undefined") return;
    const mq = window.matchMedia("(prefers-reduced-motion: reduce)");
    const apply = () => setReducedMotion(mq.matches);
    apply();
    mq.addEventListener("change", apply);
    return () => mq.removeEventListener("change", apply);
  }, []);

  const handleStart = useCallback(() => setActive(true), []);
  const handlePause = useCallback(() => setActive(false), []);

  return (
    <main className={styles.previewRoot} aria-label="Milo moments preview">
      <h1 className={styles.previewTitle}>Milo moments preview</h1>
      <p className={styles.previewLede}>
        Review the Home resting pet and the processing buddy. This page is for
        design review only and is not part of the main app navigation.
      </p>

      <section className={styles.previewSection} aria-label="Home resting">
        <h2 className={styles.previewH2}>Home — lady athlete + resting Pip</h2>
        <div className={styles.previewHero}>
          <div className={styles.previewHeroArt}>
            <AthleteCompanion exercise="squat" variant="poster" />
          </div>
          <MiloHomeRest reducedMotion={reducedMotion} />
        </div>
      </section>

      <section className={styles.previewSection} aria-label="Processing buddy">
        <h2 className={styles.previewH2}>Processing buddy</h2>
        <div className={styles.previewBuddyRow}>
          <MiloProcessingBuddy active={active} reducedMotion={reducedMotion} />
        </div>
        <div className={styles.previewControls}>
          <button
            type="button"
            className={styles.previewBtn}
            onClick={handleStart}
            aria-pressed={active}
          >
            Start
          </button>
          <button
            type="button"
            className={styles.previewBtn}
            onClick={handlePause}
            aria-pressed={!active}
          >
            Pause
          </button>
        </div>
      </section>
    </main>
  );
}
