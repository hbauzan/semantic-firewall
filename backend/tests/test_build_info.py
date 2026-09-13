"""Tests for startup version/build resolution."""
from app.core.build_info import resolve_version, startup_banner


def test_resolve_version_from_manifest():
    assert resolve_version() == "2.34.0"


def test_startup_banner_includes_version_and_build():
    banner = startup_banner()
    assert "Three-Headed Semantic Firewall" in banner
    assert "version=2.34.0" in banner
    assert "build=" in banner
