'use client';

import React, { useState } from 'react';
import type { UxMetadata, UxSettings, WeekMode } from '../lib/ux-metadata';
import styles from './ProgressWidgets.module.css';

export interface SettingsPanelProps {
  displayName: string;
  onNameChange: (v: string) => void;
  metadata: UxMetadata;
  onSave: (settings: UxSettings, displayName?: string) => boolean;
  onBack: () => void;
  error?: string | null;
}

export default function SettingsPanel({
  displayName,
  onNameChange,
  metadata,
  onSave,
  onBack,
  error,
}: SettingsPanelProps) {
  const [name, setName] = useState(displayName);
  const [goalEnabled, setGoalEnabled] = useState(metadata.goalEnabled);
  const [goalTarget, setGoalTarget] = useState<string>(
    metadata.goalTarget != null ? String(metadata.goalTarget) : ''
  );
  const [weekMode, setWeekMode] = useState<WeekMode>(metadata.weekMode);
  const [fieldError, setFieldError] = useState<string | null>(null);
  const [saved, setSaved] = useState(false);

  const handleSave = () => {
    setFieldError(null);
    setSaved(false);
    let target: number | null = null;
    if (goalEnabled) {
      const n = Number(goalTarget);
      if (!Number.isInteger(n) || n <= 0) {
        setFieldError('Enter a positive whole number for the weekly target.');
        return;
      }
      target = n;
    }
    // Single atomic commit: settings and display name are written together
    // in one mxr.ux.v1 record by the parent. If the write fails, onSave
    // returns false and nothing — name included — is committed.
    const ok = onSave({ goalEnabled, goalTarget: target, weekMode }, name);
    if (ok) {
      // Reflect the name in app state only after storage succeeded.
      onNameChange(name);
      setSaved(true);
    }
  };

  const handleCancel = () => {
    // Discard edits: reset all drafts back to the persisted values and
    // never call onNameChange.
    setName(displayName);
    setGoalEnabled(metadata.goalEnabled);
    setGoalTarget(metadata.goalTarget != null ? String(metadata.goalTarget) : '');
    setWeekMode(metadata.weekMode);
    setFieldError(null);
    setSaved(false);
    onBack();
  };

  return (
    <section className={styles.panel} aria-label="Settings">
      <h2 className={styles.heading}>Settings</h2>
      {error ? (
        <p role="alert" className={styles.error}>
          {error}
        </p>
      ) : null}
      <div className={styles.field}>
        <label htmlFor="settings-display-name">Display name (this browser only)</label>
        <input
          id="settings-display-name"
          type="text"
          value={name}
          onChange={(e) => {
            setName(e.target.value);
            setSaved(false);
          }}
          maxLength={60}
        />
      </div>
      <div className={styles.field}>
        <label>
          <input
            type="checkbox"
            checked={goalEnabled}
            onChange={(e) => {
              setGoalEnabled(e.target.checked);
              setSaved(false);
            }}
          />{' '}
          Enable a weekly analysed-set target
        </label>
      </div>
      {goalEnabled ? (
        <div className={styles.field}>
          <label htmlFor="settings-goal-target">Weekly target (sets)</label>
          <input
            id="settings-goal-target"
            type="number"
            min={1}
            step={1}
            value={goalTarget}
            onChange={(e) => {
              setGoalTarget(e.target.value);
              setSaved(false);
            }}
            aria-describedby={fieldError ? 'settings-goal-error' : undefined}
          />
          {fieldError ? (
            <p id="settings-goal-error" role="alert" className={styles.error}>
              {fieldError}
            </p>
          ) : null}
        </div>
      ) : null}
      <fieldset className={styles.field}>
        <legend>Week counting</legend>
        <label>
          <input
            type="radio"
            name="week-mode"
            checked={weekMode === 'rolling7'}
            onChange={() => setWeekMode('rolling7')}
          />{' '}
          Rolling 7 days
        </label>
        <label>
          <input
            type="radio"
            name="week-mode"
            checked={weekMode === 'calendar'}
            onChange={() => setWeekMode('calendar')}
          />{' '}
          Calendar week (Mon–Sun)
        </label>
      </fieldset>
      <p className={styles.note}>
        History and settings stay in this browser. Server media access expires after a limited
        period; removing a local entry does not delete a server analysis.
      </p>
      {saved ? (
        <p role="status" className={styles.note}>
          Settings saved.
        </p>
      ) : null}
      <div className={styles.actions}>
        <button type="button" className={styles.primaryButton} onClick={handleSave}>
          Save
        </button>
        <button type="button" className={styles.secondaryButton} onClick={handleCancel}>
          Cancel
        </button>
      </div>
    </section>
  );
}
