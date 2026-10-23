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

type ViewSide = 'front' | 'back';

// Approximate illustrative overlay anchor points (percent of the poster box)
// per region and rendered view. Purely decorative target hints — never
// measured activation or growth claims.
const REGION_DOT: Record<string, Record<ViewSide, { top: string; left: string } | null>> = {
  back: { front: { top: '30%', left: '58%' }, back: { top: '30%', left: '42%' } },
  arms: { front: { top: '38%', left: '30%' }, back: { top: '38%', left: '62%' } },
  legs: { front: { top: '66%', left: '48%' }, back: { top: '66%', left: '50%' } },
  chest: { front: { top: '28%', left: '46%' }, back: null },
};

const VIEW_SRC: Record<ViewSide, string> = {
  front: '/companion/athlete.png',
  back: '/companion/athlete-back.png',
};

/**
 * Illustrative athlete companion. Purely visual — no activation, growth,
 * or health claims.
 *
 * variant="poster": borderless transparent PNG artwork for the hero scene,
 *   with an explicit Front / Back rendered-view toggle of the same character.
 *   These are two static rendered views, not a 360° or rotatable model.
 *   Asset failures degrade gracefully to the available view or text.
 * variant="map": secondary disclosure with an on-demand interactive body map.
 *   This separate object is not the model depicted in the poster.
 */
export default function AthleteCompanion({ exercise, variant = 'map' }: AthleteCompanionProps) {
  const region = EXERCISE_REGION[exercise] ?? 'back';
  const src = useMemo(() => `/companion/index.html?region=${encodeURIComponent(region)}`, [region]);
  const [exploreOpen, setExploreOpen] = useState(false);
  const [view, setView] = useState<ViewSide>('front');
  const [failed, setFailed] = useState<Partial<Record<ViewSide, boolean>>>({});

  if (variant === 'poster') {
    const markFailed = (v: ViewSide) => setFailed((f) => ({ ...f, [v]: true }));
    // Effective view: fall back to whichever asset still loads.
    const effective: ViewSide | null = !failed[view]
      ? view
      : !failed.front
        ? 'front'
        : !failed.back
          ? 'back'
          : null;
    const dot = effective ? REGION_DOT[region]?.[effective] ?? null : null;
    return (
      <div className="athwrap">
        {effective === null ? (
          <p className="artfallback">Your next set starts here.</p>
        ) : (
          <div className="athstage">
            <div className="viewtoggle" role="group" aria-label="Artwork view">
              <button type="button" aria-pressed={view === 'front'} onClick={() => setView('front')}>
                Front
              </button>
              <button type="button" aria-pressed={view === 'back'} onClick={() => setView('back')}>
                Back
              </button>
            </div>
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img
              key={effective}
              src={VIEW_SRC[effective]}
              alt={`Illustrative athlete artwork, ${effective} view, ${REGION_LABEL[region].toLowerCase()}`}
              className="athimg"
              loading="eager"
              decoding="async"
              onError={() => markFailed(effective)}
            />
            {dot && (
              <span
                className="regiondot"
                style={{ top: dot.top, left: dot.left }}
                aria-hidden="true"
              />
            )}
            <p className="illabel">Illustrative targets.</p>
          </div>
        )}
        <span className="visuallyhidden">
          Rendered front and back views of the same illustrated athlete. Target highlights are
          illustrative only, not measured muscle activation.
        </span>
      </div>
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
