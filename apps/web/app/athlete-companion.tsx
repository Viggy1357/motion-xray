'use client';

import React, { useMemo, useState } from 'react';

export interface AthleteCompanionProps {
  exercise: string;
  variant?: 'poster' | 'map';
}

const EXERCISE_REGION: Record<string, string> = {
  lat_pulldown: 'back',
  dumbbell_curl: 'arms',
  squat: 'legs',
  incline_chest_press: 'chest',
};

const REGION_LABEL: Record<string, string> = {
  back: 'Back focus',
  arms: 'Arms focus',
  legs: 'Legs focus',
  chest: 'Chest focus',
};

/**
 * Illustrative athlete companion. Purely visual — no activation, growth,
 * or health claims.
 *
 * variant="poster": borderless transparent PNG artwork for the hero scene.
 *   Sizing is controlled by CSS; a text fallback handles image-load failure.
 * variant="map": secondary disclosure with an on-demand interactive body map.
 *   This separate object is not the model depicted in the poster.
 */
export default function AthleteCompanion({ exercise, variant = 'map' }: AthleteCompanionProps) {
  const region = EXERCISE_REGION[exercise] ?? 'back';
  const src = useMemo(() => `/companion/index.html?region=${encodeURIComponent(region)}`, [region]);
  const [exploreOpen, setExploreOpen] = useState(false);
  const [imageFailed, setImageFailed] = useState(false);

  if (variant === 'poster') {
    if (imageFailed) return <p className="artfallback">Your next set starts here.</p>;
    return (
      <img
        src="/companion/athlete.png"
        alt={`Illustrative athlete artwork, ${REGION_LABEL[region].toLowerCase()}`}
        className="athimg"
        loading="eager"
        decoding="async"
        onError={() => setImageFailed(true)}
      />
    );
  }

  return (
    <section className="companionmap" aria-label="Illustrative athlete body map">
      <details className="details companionmap-explore" onToggle={(e) => setExploreOpen((e.target as HTMLDetailsElement).open)}>
        <summary>Explore body map</summary>
        <p className="muted" style={{ margin: '0 0 .6rem' }}>
          {REGION_LABEL[region]} · generic exercise targets, not measured activation.
          {' '}This separate illustrative map rotates; the artwork above is static.
        </p>
        {exploreOpen && (
          <iframe
            key={src}
            src={src}
            title="Interactive 3D athlete body map"
            loading="lazy"
            frameBorder={0}
            className="companionmap-frame"
          />
        )}
      </details>
    </section>
  );
}
