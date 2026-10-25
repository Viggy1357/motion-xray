export type MiloVisualState = "idle" | "attentive" | "cheer" | "static";

export type MiloAssetStatus = "provisional" | "ready" | "failed";

export interface MiloLayerAnchor {
  src: string;
  left: number;
  top: number;
  width: number;
  originX: number;
  originY: number;
}

export interface MiloLayerManifest {
  version: 1;
  base: string;
  head?: MiloLayerAnchor;
  paw?: MiloLayerAnchor;
  fallback: string;
  status: MiloAssetStatus;
}

export const DEFAULT_MANIFEST: MiloLayerManifest = {
  version: 1,
  base: "/companion/milo-pip/body.webp",
  head: {
    src: "/companion/milo-pip/head.webp",
    left: 14,
    top: 0,
    width: 66,
    originX: 50,
    originY: 75,
  },
  fallback: "/companion/milo-pip/neutral.webp",
  status: "ready",
};

export const ASSET_VERSION = "1.0.0";

export function resolveAssetStatus(manifest: MiloLayerManifest): MiloAssetStatus {
  if (!manifest || typeof manifest !== "object") return "failed";
  if (manifest.status === "failed") return "failed";
  if (!manifest.base || typeof manifest.base !== "string") return "failed";
  if (!manifest.fallback || typeof manifest.fallback !== "string") return "failed";
  return manifest.status === "ready" ? "ready" : "provisional";
}

export function isManifestReady(manifest: MiloLayerManifest): boolean {
  return resolveAssetStatus(manifest) === "ready";
}
