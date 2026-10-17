"""Release version comparison, GitHub fetch and Velopack platform gating."""

from types import SimpleNamespace

import httpx
import pytest

from gambitpairing._version import __version__
from gambitpairing.update import (
    IN_APP_UPDATE_PLATFORMS,
    ReleaseInfo,
    UpdateCheckError,
    VelopackUpdateError,
    VelopackUpdater,
    fetch_latest_release,
    find_newer_release,
    in_app_update_supported,
    is_newer_version,
    parse_version,
)


@pytest.mark.parametrize(
    ("candidate", "current", "expected"),
    [
        ("v0.8.1", "0.8.0", True),
        ("0.9.0", "0.8.0", True),
        ("v1.0.0", "0.10.0", True),
        ("v0.10.0", "0.9.0", True),  # numeric, not string, comparison
        ("v0.8.0", "0.8.0", False),
        ("v0.7.9", "0.8.0", False),
        ("v0.9.0rc1", "0.8.0", True),
        ("v0.9.0rc1", "0.9.0", False),
        ("v0.9.0-rc.1", "0.9.0rc1", False),  # SemVer spelling of the same version
        ("not-a-version", "0.8.0", False),
        ("v0.9.0", "garbage", False),
    ],
)
def test_is_newer_version(candidate, current, expected):
    assert is_newer_version(candidate, current) is expected


def test_parse_version_accepts_tags_and_rejects_garbage():
    assert str(parse_version("v0.8.0")) == "0.8.0"
    assert str(parse_version("V1.2")) == "1.2"
    assert parse_version("latest") is None


def test_current_version_is_parseable():
    assert parse_version(__version__) is not None


def _client_factory(handler):
    real_client = httpx.Client

    def factory(**kwargs):
        return real_client(transport=httpx.MockTransport(handler), **kwargs)

    return factory


def test_fetch_latest_release_reads_github_payload():
    seen = []

    def handler(request):
        seen.append(request)
        return httpx.Response(
            200,
            json={
                "tag_name": "v9.9.9",
                "body": "notes",
                "html_url": "https://example.test/release",
                "draft": False,
                "prerelease": False,
            },
        )

    release = fetch_latest_release(
        "https://api.example.test/latest", client_factory=_client_factory(handler)
    )

    assert (release.version, release.tag, release.notes) == ("9.9.9", "v9.9.9", "notes")
    assert release.page_url == "https://example.test/release"
    assert seen[0].headers["accept"] == "application/vnd.github+json"


@pytest.mark.parametrize(
    "response",
    [
        httpx.Response(500),
        httpx.Response(200, text="not json"),
        httpx.Response(200, json=["unexpected"]),
        httpx.Response(200, json={"tag_name": "nightly"}),
        httpx.Response(200, json={"tag_name": "v2.0.0", "prerelease": True}),
    ],
)
def test_fetch_latest_release_errors(response):
    with pytest.raises(UpdateCheckError):
        fetch_latest_release(
            "https://api.example.test/latest",
            client_factory=_client_factory(lambda request: response),
        )


def test_fetch_latest_release_network_error():
    def handler(request):
        raise httpx.ConnectError("offline", request=request)

    with pytest.raises(UpdateCheckError):
        fetch_latest_release(
            "https://api.example.test/latest", client_factory=_client_factory(handler)
        )


def test_find_newer_release_compares_with_current_version():
    newer = ReleaseInfo("0.9.0", "v0.9.0", "", "https://example.test")
    same = ReleaseInfo("0.8.0", "v0.8.0", "", "https://example.test")
    assert find_newer_release("0.8.0", fetch=lambda: newer) is newer
    assert find_newer_release("0.8.0", fetch=lambda: same) is None


@pytest.mark.parametrize(
    ("platform", "frozen", "expected"),
    [
        ("win32", True, True),
        ("win32", False, False),
        ("darwin", True, False),
        ("linux", True, False),
    ],
)
def test_in_app_update_platform_gating(platform, frozen, expected):
    assert in_app_update_supported(platform, frozen) is expected


def test_in_app_update_platforms_is_windows_only_for_now():
    assert IN_APP_UPDATE_PLATFORMS == frozenset({"win32"})


class _FakeManager:
    def __init__(self, source, offered_version: str | None = "2.0.0"):
        self.source = source
        self.offered = offered_version
        self.downloaded = []
        self.applied = []

    def check_for_updates(self):
        if self.offered is None:
            return None
        return SimpleNamespace(TargetFullRelease=SimpleNamespace(Version=self.offered))

    def download_updates(self, info, progress_callback=None):
        if progress_callback:
            progress_callback(100)
        self.downloaded.append(info)

    def wait_exit_then_apply_updates(self, info, silent=False, restart=True):
        self.applied.append((info, silent, restart))


def _fake_velopack(offered: str | None = "2.0.0", fail: bool = False):
    managers = []

    def github_source(url, token, prerelease):
        return ("github", url, token, prerelease)

    def update_manager(source):
        if fail:
            raise RuntimeError("This application is not properly installed")
        managers.append(_FakeManager(source, offered))
        return managers[-1]

    module = SimpleNamespace(GithubSource=github_source, UpdateManager=update_manager)
    return module, managers


def test_velopack_updater_uses_github_stable_releases():
    module, managers = _fake_velopack()
    updater = VelopackUpdater("https://github.com/o/r", velopack_loader=lambda: module)

    assert updater.is_available()
    progress = []
    assert updater.download("2.0.0", progress.append) == "2.0.0"
    updater.apply_and_restart()

    manager = managers[0]
    assert manager.source == ("github", "https://github.com/o/r", None, False)
    assert progress == [100]
    assert manager.applied[0][1:] == (False, True)


def test_velopack_updater_refuses_a_different_version():
    module, _ = _fake_velopack(offered="2.0.1")
    updater = VelopackUpdater(velopack_loader=lambda: module)
    with pytest.raises(VelopackUpdateError):
        updater.download("2.0.0")
    with pytest.raises(VelopackUpdateError):
        updater.apply_and_restart()


def test_velopack_updater_reports_missing_package():
    module, _ = _fake_velopack(offered=None)
    with pytest.raises(VelopackUpdateError):
        VelopackUpdater(velopack_loader=lambda: module).download("2.0.0")


def test_velopack_updater_unavailable_outside_a_velopack_install():
    module, _ = _fake_velopack(fail=True)
    assert not VelopackUpdater(velopack_loader=lambda: module).is_available()

    def missing():
        raise ImportError("no velopack")

    assert not VelopackUpdater(velopack_loader=missing).is_available()
