"use client";

import {
  CSSProperties,
  ReactElement,
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
} from "react";
import styles from "./MiloMoments.module.css";
import MiloCompanion from "./MiloCompanion";

const BUBBLE_INTERVAL_MS = 6000;

const BUBBLE_MESSAGES: readonly string[] = [
  "One set at a time.",
  "You showed up. That counts.",
  "A little consistency goes a long way.",
];

const PIP_SLEEPING_SRC = "/companion/milo-pip/sleeping.webp";
const PIP_NEUTRAL_SRC = "/companion/milo-pip/neutral.webp";

export interface MiloHomeRestProps {
  reducedMotion?: boolean;
}

export function MiloHomeRest({
  reducedMotion = false,
}: MiloHomeRestProps): ReactElement {
  const [src, setSrc] = useState<string>(PIP_SLEEPING_SRC);
  const [failed, setFailed] = useState<boolean>(false);

  const handleError = useCallback(() => {
    setFailed(true);
    setSrc(PIP_NEUTRAL_SRC);
  }, []);

  const containerStyle: CSSProperties = useMemo(() => {
    return {
      transformOrigin: "50% 100%",
      animation: reducedMotion ? "none" : `${styles.breath} 4.2s ease-in-out infinite`,
    };
  }, [reducedMotion]);

  return (
    <div
      className={styles.homePet}
      data-rest="true"
      aria-label="Milo resting"
      role="img"
    >
      <div className={styles.homePetInner} style={containerStyle}>
        {!failed ? (
          <img
            className={styles.homePetImg}
            src={PIP_SLEEPING_SRC}
            alt=""
            draggable={false}
            onError={handleError}
          />
        ) : (
          <img
            className={styles.homePetImg}
            src={src}
            alt=""
            draggable={false}
          />
        )}
      </div>
    </div>
  );
}

export interface MiloProcessingBuddyProps {
  active: boolean;
  reducedMotion?: boolean;
}

export function MiloProcessingBuddy({
  active,
  reducedMotion = false,
}: MiloProcessingBuddyProps): ReactElement | null {
  const [bubbleIndex, setBubbleIndex] = useState<number>(0);
  const [pageVisible, setPageVisible] = useState<boolean>(true);
  const [systemReduced, setSystemReduced] = useState<boolean>(false);
  const intervalRef = useRef<number | null>(null);
  const mountedRef = useRef<boolean>(true);

  useEffect(() => {
    mountedRef.current = true;
    return () => {
      mountedRef.current = false;
      if (intervalRef.current !== null) {
        window.clearInterval(intervalRef.current);
        intervalRef.current = null;
      }
    };
  }, []);

  useEffect(() => {
    if (typeof document === "undefined") return;
    const apply = () => setPageVisible(document.visibilityState !== "hidden");
    apply();
    document.addEventListener("visibilitychange", apply);
    return () => {
      document.removeEventListener("visibilitychange", apply);
    };
  }, []);

  useEffect(() => {
    if (typeof window === "undefined") return;
    const mq = window.matchMedia("(prefers-reduced-motion: reduce)");
    const apply = () => setSystemReduced(mq.matches);
    apply();
    mq.addEventListener("change", apply);
    return () => mq.removeEventListener("change", apply);
  }, []);

  const effectiveReduced = !!reducedMotion || systemReduced;

  useEffect(() => {
    if (intervalRef.current !== null) {
      window.clearInterval(intervalRef.current);
      intervalRef.current = null;
    }
    if (!active || effectiveReduced || !pageVisible) {
      return;
    }
    intervalRef.current = window.setInterval(() => {
      if (!mountedRef.current) return;
      setBubbleIndex((i) => (i + 1) % BUBBLE_MESSAGES.length);
    }, BUBBLE_INTERVAL_MS);
    return () => {
      if (intervalRef.current !== null) {
        window.clearInterval(intervalRef.current);
        intervalRef.current = null;
      }
    };
  }, [active, effectiveReduced, pageVisible]);

  if (!active) return null;

  const message = BUBBLE_MESSAGES[bubbleIndex] ?? BUBBLE_MESSAGES[0];

  return (
    <div className={styles.buddy} data-active={active ? "true" : "false"}>
      <div className={styles.buddyAvatar} data-still={effectiveReduced || !pageVisible} aria-hidden="true">
        <MiloCompanion state="attentive" eventKey="milo-processing" size="compact" reducedMotion={effectiveReduced} hidden={!pageVisible} />
      </div>
      <div
        className={styles.bubble}
        aria-hidden="true"
        aria-live="off"
        data-bubble-index={bubbleIndex}
      >
        <span className={styles.bubbleText}>{message}</span>
      </div>
    </div>
  );
}

export default MiloHomeRest;
