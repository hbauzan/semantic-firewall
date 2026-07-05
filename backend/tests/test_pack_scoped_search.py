"""Tests for pack-scoped firewall search."""
from app.core.models import ConfigState
from app.modules.storage import storage


def test_resolve_active_pack_explicit():
    packs = storage.get_summary()
    if not packs:
        return
    fname = packs[0]["filename"]
    assert storage.resolve_active_pack(fname) == fname


def test_resolve_active_pack_single_pack_fallback():
    packs = storage.get_summary()
    if len(packs) != 1:
        return
    assert storage.resolve_active_pack(None) == packs[0]["filename"]


def test_search_for_firewall_uses_pack_scope(monkeypatch):
    packs = storage.get_summary()
    if not packs:
        return
    fname = packs[0]["filename"]
    calls: list[str] = []

    def fake_pack_search(vec, filename, k=1):
        calls.append(filename)
        return []

    monkeypatch.setattr(storage, "search_nearest_for_pack", fake_pack_search)
    storage.search_for_firewall([0.1] * 8, k=3, active_corpus_file=fname)
    assert calls == [fname]
