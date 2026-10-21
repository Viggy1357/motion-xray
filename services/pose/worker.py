from __future__ import annotations

import logging
import os
import signal
import sys
import threading

from app.processing_config import WorkerConfig, load_worker_config
from app.pose_jobs import run_pose_once
from app.store import Store

_LOG = logging.getLogger("motion_xray.pose.worker")

WORKER_FAILED = "WORKER_FAILED"
WORKER_CONFIG_INVALID = "WORKER_CONFIG_INVALID"


class WorkerShutdown(BaseException):
    pass


def _install_shutdown_handlers(stop: threading.Event) -> tuple:
    saved_term = signal.getsignal(signal.SIGTERM)
    saved_int = signal.getsignal(signal.SIGINT)

    def handler(signum: int, frame: object) -> None:
        stop.set()
        raise WorkerShutdown()

    signal.signal(signal.SIGTERM, handler)
    signal.signal(signal.SIGINT, handler)
    return saved_term, saved_int


def _restore_handlers(saved: tuple) -> None:
    signal.signal(signal.SIGTERM, saved[0])
    signal.signal(signal.SIGINT, saved[1])


def run_loop(
    store: Store,
    config: WorkerConfig,
    stop: threading.Event,
    *,
    once: bool = False,
) -> None:
    while not stop.is_set():
        claimed = run_pose_once(
            store,
            config.source_root,
            config.artifact_root,
            config.checkpoint_path,
            config.checkpoint_sha256,
            lease_s=config.lease_s,
            poll_s=config.poll_s,
            timeout_s=config.timeout_s,
        )
        if once:
            return
        if not claimed:
            stop.wait(config.idle_s)


def main(argv: list[str] | None = None) -> int:
    import argparse

    parser = argparse.ArgumentParser(description="Pose-only worker daemon")
    parser.add_argument("--once", action="store_true", help="process one job or empty queue then exit")
    args = parser.parse_args(argv)

    os.umask(0o077)

    try:
        config = load_worker_config()
    except Exception:
        _LOG.error(WORKER_CONFIG_INVALID)
        return 2

    logging.basicConfig(level=logging.INFO)
    _LOG.info("pose-only worker started")

    try:
        for root in (config.source_root, config.artifact_root):
            root.mkdir(parents=True, exist_ok=True, mode=0o700)
            root.chmod(0o700)
        store = Store(config.db_path)
    except Exception:
        _LOG.error(WORKER_CONFIG_INVALID)
        return 1

    stop = threading.Event()
    saved = _install_shutdown_handlers(stop)

    try:
        run_loop(store, config, stop, once=args.once)
    except WorkerShutdown:
        return 0
    except KeyboardInterrupt:
        return 0
    except Exception:
        _LOG.error(WORKER_FAILED)
        return 1
    finally:
        _restore_handlers(saved)

    return 0


if __name__ == "__main__":
    sys.exit(main())
