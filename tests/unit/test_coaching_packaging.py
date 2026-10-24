from __future__ import annotations

import importlib.resources
import json
import sys
import types

import app.coaching as coaching


def _install_fake_providers_pkg(monkeypatch, *, json_text=None, raise_on_read=False,
                                missing=False, malformed=False):
    """Install a fake ``providers.llm`` package exposing a controllable
    ``coaching-claims-v1.json`` resource.

    The fake package mirrors the layout used by the real wheel so that
    ``importlib.resources.files("providers.llm").joinpath(...).is_file()``
    behaves the same way the production code expects.
    """
    pkg = types.ModuleType("providers")
    pkg.__path__ = []  # mark as package
    llm = types.ModuleType("providers.llm")
    llm.__path__ = []
    monkeypatch.setitem(sys.modules, "providers", pkg)
    monkeypatch.setitem(sys.modules, "providers.llm", llm)

    class _Resource:
        def __init__(self, text):
            self._text = text

        def is_file(self):
            if missing:
                return False
            if raise_on_read:
                raise OSError("simulated missing resource")
            return True

        def read_text(self, encoding="utf-8"):
            if raise_on_read:
                raise OSError("simulated read failure")
            if malformed:
                raise UnicodeDecodeError("utf-8", b"", 0, 1, "bad")
            return self._text

    payload = json_text if json_text is not None else json.dumps({
        "version": "coaching-claims-v1",
        "claims": [
            {
                "id": "lat_control",
                "exercise": "lat_pulldown",
                "text": "Keep the upper body controlled while pulling.",
                "url": "https://www.ifafitness.com/wttrain/latpulldown.htm",
            },
        ],
    })
    llm._fake_resource = _Resource(payload)
    llm.joinpath = lambda name: llm._fake_resource

    real_files = importlib.resources.files

    def _fake_files(name):
        if name == "providers.llm":
            return llm
        return real_files(name)

    monkeypatch.setattr(importlib.resources, "files", _fake_files)
    return llm


def test_load_claims_uses_packaged_resource_when_path_missing(monkeypatch):
    """Installed wheel: ``_claims_path()`` returns ``None`` but the bundled
    resource must still load the real lat_pulldown cue with its source URL.
    """
    monkeypatch.setattr(coaching, "_claims_path", lambda: None)

    version, claims = coaching._load_claims("lat_pulldown")
    assert version == "coaching-claims-v1"
    assert len(claims) == 1
    cue = claims[0]
    assert cue["id"] == "lat_control"
    assert cue["exercise"] == "lat_pulldown"
    assert cue["text"]
    assert cue["url"] == "https://www.ifafitness.com/wttrain/latpulldown.htm"


def test_load_claims_missing_resource_returns_safe_empty(monkeypatch):
    """No source path and no bundled resource: fail closed with the default
    version and an empty claim list. No invented cue.
    """
    monkeypatch.setattr(coaching, "_claims_path", lambda: None)
    _install_fake_providers_pkg(monkeypatch, missing=True)

    version, claims = coaching._load_claims("lat_pulldown")
    assert version == "coaching-claims-v1"
    assert claims == []


def test_load_claims_source_path_still_works(monkeypatch, tmp_path):
    """Source-tree path resolution must keep working unchanged."""
    claims_file = tmp_path / "coaching-claims-v1.json"
    claims_file.write_text(json.dumps({
        "version": "coaching-claims-v1",
        "claims": [
            {
                "id": "curl_control",
                "exercise": "dumbbell_curl",
                "text": "Use a controlled curl and lowering phase.",
                "url": "https://example.test/curl",
            },
        ],
    }))
    monkeypatch.setattr(coaching, "_claims_path", lambda: claims_file)

    version, claims = coaching._load_claims("dumbbell_curl")
    assert version == "coaching-claims-v1"
    assert len(claims) == 1
    assert claims[0]["id"] == "curl_control"
    assert claims[0]["url"] == "https://example.test/curl"


def test_load_claims_malformed_json_returns_safe_empty(monkeypatch, tmp_path):
    """Malformed JSON on disk must not raise and must not invent a cue."""
    bad = tmp_path / "coaching-claims-v1.json"
    bad.write_text("{not valid json")
    monkeypatch.setattr(coaching, "_claims_path", lambda: bad)

    version, claims = coaching._load_claims("lat_pulldown")
    assert version == "coaching-claims-v1"
    assert claims == []


def test_load_claims_filters_by_exercise(monkeypatch):
    """Bundled resource: only the requested exercise is returned."""
    monkeypatch.setattr(coaching, "_claims_path", lambda: None)
    _install_fake_providers_pkg(monkeypatch, json_text=json.dumps({
        "version": "coaching-claims-v1",
        "claims": [
            {"id": "lat_control", "exercise": "lat_pulldown",
             "text": "lat cue", "url": "https://example.test/lat"},
            {"id": "curl_control", "exercise": "dumbbell_curl",
             "text": "curl cue", "url": "https://example.test/curl"},
        ],
    }))

    version, claims = coaching._load_claims("dumbbell_curl")
    assert version == "coaching-claims-v1"
    assert len(claims) == 1
    assert claims[0]["id"] == "curl_control"


def test_load_claims_resource_read_failure_returns_safe_empty(monkeypatch):
    """Resource present but unreadable: fail closed, no invented cue."""
    monkeypatch.setattr(coaching, "_claims_path", lambda: None)
    _install_fake_providers_pkg(monkeypatch, raise_on_read=True)

    version, claims = coaching._load_claims("lat_pulldown")
    assert version == "coaching-claims-v1"
    assert claims == []


def test_load_claims_resource_malformed_bytes_returns_safe_empty(monkeypatch):
    """Resource present but bytes are not valid UTF-8 JSON: fail closed."""
    monkeypatch.setattr(coaching, "_claims_path", lambda: None)
    _install_fake_providers_pkg(monkeypatch, malformed=True)

    version, claims = coaching._load_claims("lat_pulldown")
    assert version == "coaching-claims-v1"
    assert claims == []
