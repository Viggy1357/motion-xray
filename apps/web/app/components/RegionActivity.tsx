'use client';

import React, { useMemo } from 'react';
import styles from './ProgressWidgets.module.css';

export interface RegionActivitySet {
  analysisId: string | null;
  exercise: string;
  recognitionVersion?: string;
  recognition?: { analysisId: string; exercise: string };
}

export interface RegionActivityProps {
  sets: RegionActivitySet[];
}

type Region = 'back' | 'arms' | 'legs' | 'chest';

const REGIONS: Region[] = ['back', 'arms', 'legs', 'chest'];

/** One primary region per exercise; no secondary inference. */
export function primaryRegionForExercise(exercise: string): Region | null {
  switch (exercise) {
    case 'lat_pulldown':
      return 'back';
    case 'dumbbell_curl':
      return 'arms';
    case 'squat':
      return 'legs';
    case 'incline_chest_press':
      return 'chest';
    default:
      return null;
  }
}

/**
 * Eligibility: unique analysisId with exact recognition proof matching the
 * record's own analysisId and exercise. Legacy/manual records without proof
 * earn no retrospective credit.
 */
export function isEligibleSet(set: RegionActivitySet): boolean {
  if (!set.analysisId) return false;
  const rec = set.recognition;
  if (!rec) return false;
  return rec.analysisId === set.analysisId && rec.exercise === set.exercise;
}

export function countByRegion(sets: RegionActivitySet[]): Record<Region, number> {
  const counts: Record<Region, number> = { back: 0, arms: 0, legs: 0, chest: 0 };
  const seen = new Set<string>();
  for (const set of sets) {
    if (!isEligibleSet(set)) continue;
    const id = set.analysisId as string;
    if (seen.has(id)) continue;
    seen.add(id);
    const region = primaryRegionForExercise(set.exercise);
    if (region) counts[region] += 1;
  }
  return counts;
}

export default function RegionActivity({ sets }: RegionActivityProps) {
  const counts = useMemo(() => countByRegion(sets), [sets]);
  const max = Math.max(0, ...REGIONS.map((r) => counts[r]));
  const total = REGIONS.reduce((n, r) => n + counts[r], 0);

  if (total === 0) {
    return (
      <section className={styles.panel} aria-label="Body region activity">
        <h3 className={styles.heading}>Body regions</h3>
        <p className={styles.note}>No eligible analysed sets yet.</p>
      </section>
    );
  }

  return (
    <section className={styles.panel} aria-label="Body region activity">
      <h3 className={styles.heading}>Body regions</h3>
      <p className={styles.note}>Activity by primary region, not measured muscle development.</p>
      <ul className={styles.regionList}>
        {REGIONS.map((region) => {
          const n = counts[region];
          const widthPct = max > 0 ? (n / max) * 100 : 0;
          return (
            <li key={region} className={styles.regionRow}>
              <span className={styles.regionLabel}>{region}</span>
              <span className={styles.barTrack}>
                <span className={styles.barFill} style={{ width: `${widthPct}%` }} />
              </span>
              <span className={styles.regionCount}>{n}</span>
            </li>
          );
        })}
      </ul>
    </section>
  );
}
