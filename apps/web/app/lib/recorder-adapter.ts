/**
 * Browser-safe MediaRecorder adapter.
 *
 * Async Blob -> Uint8Array conversions are serialized and awaited before
 * invoking onChunk, and the final dataavailable is awaited before onStop.
 * This guarantees the controller never sees a partial final chunk and that
 * chunk ordering matches MediaRecorder emission order.
 *
 * Callbacks are race-free: after destroy() any in-flight conversion is
 * discarded and subsequent onChunk/onStop invocations are no-ops.
 *
 * Conservative defaults: 4 Mbps video bitrate, 1s timeslice. These leave
 * headroom under the 60s / 100MiB hard limits for typical webm/mp4 outputs.
 *
 * NOTE: Some browsers can emit a final dataavailable whose size exceeds the
 * configured bitrate budget by a small margin because the muxer trailer is
 * appended after the last timeslice. This is an unavoidable platform quirk;
 * the controller's finalize() guard rejects any clip at or over MAX_BYTES
 * rather than truncating mux chunks.
 */

import type { RecordedChunk, RecorderAdapter } from './capture-controller';

export interface RecorderAdapterOptions {
  stream: MediaStream;
  mimeType: string;
  timesliceMs: number;
  videoBitsPerSecond: number;
}

export function createRecorderAdapter(opts: RecorderAdapterOptions): RecorderAdapter {
  const { stream, mimeType, timesliceMs, videoBitsPerSecond } = opts;
  const inner = new MediaRecorder(stream, {
    mimeType,
    videoBitsPerSecond,
  });

  let destroyed = false;
  let stopped = false;
  // Serialized conversion queue: each dataavailable's arrayBuffer() is awaited
  // in order before the next is processed, so onChunk fires in emission order.
  let conversionChain: Promise<void> = Promise.resolve();
  // Tracks whether onStop has already been delivered to the controller. The
  // adapter must fire onStop exactly once across all stop paths (explicit
  // stop(), MediaRecorder onstop, and any catch-all flush) so the controller's
  // finalize() guard is not bypassed.
  let stopDelivered = false;

  const deliverStop = (): void => {
    if (destroyed) return;
    if (stopDelivered) return;
    stopDelivered = true;
    adapter.onStop?.();
  };

  const adapter: RecorderAdapter = {
    mimeType: inner.mimeType || mimeType,
    onChunk: null,
    onStop: null,
    onError: null,
    start() {
      inner.ondataavailable = (e: BlobEvent): void => {
        if (destroyed) return;
        const blob = e.data;
        if (!blob || blob.size <= 0) return;
        const mime = adapter.mimeType;
        conversionChain = conversionChain.then(async () => {
          if (destroyed) return;
          try {
            const buf = await blob.arrayBuffer();
            if (destroyed) return;
            const u8 = new Uint8Array(buf);
            adapter.onChunk?.({ data: u8, mimeType: mime });
          } catch (err) {
            if (destroyed) return;
            destroyed = true;
            adapter.onChunk = null;
            adapter.onStop = null;
            adapter.onError?.(err instanceof Error ? err : new Error('conversion failed'));
            adapter.onError = null;
            try { inner.stop(); } catch { /* best effort */ }
          }
        });
      };
      inner.onstop = (): void => {
        if (destroyed) return;
        stopped = true;
        // Wait for the final dataavailable conversion (if any) to land before
        // signalling onStop, so the controller's finalize() sees every chunk.
        // The chain itself is the single source of truth for ordering; we
        // never shortcut past it, so a stop() that races with a pending
        // conversion cannot deliver onStop before the final chunk.
        conversionChain = conversionChain.then(() => {
          deliverStop();
        });
      };
      inner.onerror = (): void => {
        if (destroyed) return;
        adapter.onError?.(new Error('recorder error'));
      };
      inner.start(timesliceMs);
    },
    stop() {
      if (destroyed) {
        return;
      }
      if (stopped) {
        // MediaRecorder already fired onstop; the conversion chain will
        // deliver onStop in order. Do not shortcut past the queue.
        return;
      }
      if (inner.state !== 'inactive') {
        try {
          inner.stop();
        } catch {
          // If stop throws, still flush onStop so the controller can finalize.
          conversionChain = conversionChain.then(() => {
            deliverStop();
          });
        }
      } else {
        conversionChain = conversionChain.then(() => {
          deliverStop();
        });
      }
    },
  };

  // Expose a teardown hook so the controller can detach callbacks and discard
  // any in-flight conversion. The controller calls stop() then nulls callbacks;
  // we additionally guard here against late callbacks.
  (adapter as unknown as { __destroy?: () => void }).__destroy = (): void => {
    destroyed = true;
    adapter.onChunk = null;
    adapter.onStop = null;
    adapter.onError = null;
  };

  return adapter;
}
