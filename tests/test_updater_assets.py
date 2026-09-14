import hashlib

import httpx

from gambitpairing.update.updater import Updater


def release():
    return {
        "assets": [
            {"name": name, "browser_download_url": "https://example.test/" + name}
            for name in [
                "gambit-windows-x64.zip",
                "gambit-windows-x64.zip.sha256",
                "gambit-linux-x64.zip",
                "gambit-linux-x64.zip.sha256",
            ]
        ]
    }


def test_update_selects_matching_platform_checksum(monkeypatch):
    monkeypatch.setattr("gambitpairing.update.updater.sys.platform", "win32")
    monkeypatch.setattr(
        "gambitpairing.update.updater.platform.machine", lambda: "AMD64"
    )
    updater = Updater("0.1")
    updater.latest_version_info = release()
    archive, checksum = updater._get_asset_urls()
    assert archive is not None
    assert archive.endswith("windows-x64.zip")
    assert checksum == archive + ".sha256"


def test_download_follows_redirects_and_resets_checksum(monkeypatch, tmp_path):
    monkeypatch.setattr("gambitpairing.update.updater.sys.platform", "win32")
    monkeypatch.setattr(
        "gambitpairing.update.updater.platform.machine", lambda: "AMD64"
    )
    monkeypatch.setattr(
        "gambitpairing.update.updater.tempfile.mkdtemp", lambda **_: str(tmp_path)
    )
    payload = b"archive test bytes"
    digest = hashlib.sha256(payload).hexdigest()
    requests = []

    def handler(request):
        requests.append(str(request.url))
        if request.url.path.endswith(".sha256"):
            return httpx.Response(200, text=digest)
        if request.url.path.endswith(".zip"):
            return httpx.Response(302, headers={"location": "/download"})
        return httpx.Response(200, content=payload)

    client = httpx.Client
    monkeypatch.setattr(
        "gambitpairing.update.updater.httpx.Client",
        lambda **kwargs: client(transport=httpx.MockTransport(handler), **kwargs),
    )
    updater = Updater("0.1")
    updater.latest_version_info = release()
    path = updater.download_update()
    assert path is not None
    assert updater.verify_checksum(path)
    assert any(url.endswith("/download") for url in requests)
    updater.latest_version_info = {"assets": []}
    assert updater.download_update() is None
    assert updater.expected_checksum is None
    assert not updater.verify_checksum(path)
