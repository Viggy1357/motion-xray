"""Proxy timestamp map contracts for private audio-free video proxy."""

from __future__ import annotations

import re
from typing import Literal

from .base import FiniteFloat, MXRModel


class TimestampPair(MXRModel):
    """A single frame's source-to-proxy timestamp mapping."""

    source_index: int
    source_s: FiniteFloat
    proxy_s: FiniteFloat

    def model_post_init(self, __context: object) -> None:
        if self.source_index < 0:
            raise ValueError("source_index must be >= 0")
        if self.source_s < 0:
            raise ValueError("source_s must be >= 0")
        if self.proxy_s < 0:
            raise ValueError("proxy_s must be >= 0")


class ProxyTimestampMap(MXRModel):
    """Complete mapping from source PTS to proxy PTS for a transcoded video."""

    schema_version: Literal["0.2.0"] = "0.2.0"
    transform_version: Literal["ffmpeg-proxy-v1"] = "ffmpeg-proxy-v1"
    source_sha256: str
    proxy_sha256: str
    source_width: int
    source_height: int
    source_rotation: int
    proxy_width: int
    proxy_height: int
    padding_right: int
    padding_bottom: int
    frames: list[TimestampPair]

    def model_post_init(self, __context: object) -> None:
        if not re.fullmatch(r"[0-9a-f]{64}", self.source_sha256):
            raise ValueError("source_sha256 must be 64 lowercase hex characters")
        if not re.fullmatch(r"[0-9a-f]{64}", self.proxy_sha256):
            raise ValueError("proxy_sha256 must be 64 lowercase hex characters")
        if not (0 < self.source_width <= 1920):
            raise ValueError("source_width out of bounds")
        if not (0 < self.source_height <= 1920):
            raise ValueError("source_height out of bounds")
        if not (0 < self.proxy_width <= 1920):
            raise ValueError("proxy_width out of bounds")
        if not (0 < self.proxy_height <= 1920):
            raise ValueError("proxy_height out of bounds")
        if self.source_rotation not in (0, 90, -90, 180, -180):
            raise ValueError("source_rotation must be 0, +-90, or +-180")
        if self.padding_right not in (0, 1):
            raise ValueError("padding_right must be 0 or 1")
        if self.padding_bottom not in (0, 1):
            raise ValueError("padding_bottom must be 0 or 1")
        if self.proxy_width != self.source_width + self.padding_right:
            raise ValueError("proxy_width must equal source_width + padding_right")
        if self.proxy_height != self.source_height + self.padding_bottom:
            raise ValueError("proxy_height must equal source_height + padding_bottom")
        if len(self.frames) < 2 or len(self.frames) > 7200:
            raise ValueError(f"frame count out of range: {len(self.frames)}")
        last_si = -1
        last_ss = -1.0
        last_ps = -1.0
        for f in self.frames:
            if f.source_index <= last_si:
                raise ValueError("source_index must be strictly increasing")
            if f.source_s <= last_ss:
                raise ValueError("source_s must be strictly increasing")
            if f.proxy_s <= last_ps:
                raise ValueError("proxy_s must be strictly increasing")
            last_si = f.source_index
            last_ss = f.source_s
            last_ps = f.proxy_s
