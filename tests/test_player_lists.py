"""Qt-free tests for player list parsing, storage, updates and search."""

import ast
from datetime import datetime, timedelta, timezone
import hashlib
import json
from pathlib import Path
import zipfile

import httpx
import pytest

from gambitpairing.constants import (
    DEFAULT_PLAYER_LISTS,
    PLAYER_LIST_CHECK_INTERVAL_SECONDS,
)
from gambitpairing.player_lists.catalog import (
    PLAYER_LISTS,
    SOURCE_CFC,
    SOURCE_FIDE,
    get_player_list,
)
from gambitpairing.player_lists.parsers import (
    SKIP_ANONYMOUS,
    SKIP_BAD_ID,
    SKIP_BAD_NUMBER,
    SKIP_DUPLICATE_ID,
    SKIP_NO_NAME,
    SKIP_TOO_FEW_FIELDS,
    ParseReport,
    PlayerListFormatError,
    iter_cfc_members,
    iter_cfc_members_from_text,
    iter_fide_players,
)
from gambitpairing.player_lists.search import (
    SOURCE_LABEL_BOTH,
    LiveLookups,
    SearchMode,
    SearchRequest,
    SourceState,
    SourceStatus,
    cfc_hit,
    fide_hit,
    format_search_status,
    merge_search_hits,
    search_source,
    selected_sources,
)
from gambitpairing.player_lists.store import (
    ListMetadata,
    ListState,
    PlayerListStore,
    PlayerListValidationError,
    atomic_write_text,
    is_check_due,
    md5_from_etag,
    name_key,
)
from gambitpairing.player_lists.updates import (
    CheckStatus,
    check_and_update,
    conditional_headers,
)

FIXTURES = Path(__file__).parent / "fixtures" / "player_lists"
CFC_SAMPLE = FIXTURES / "tdlist_sample.txt"
FIDE_SAMPLE = FIXTURES / "fide_players_list_sample.xml"
FIDE_RAPID_SAMPLE = FIXTURES / "fide_rapid_list_sample.xml"

FIDE = get_player_list("fide_combined")
FIDE_RAPID = get_player_list("fide_rapid")
CFC = get_player_list("cfc_members")
NOW = datetime(2026, 10, 18, 12, 0, tzinfo=timezone.utc)


def fide_zip(path: Path, member: str = "players_list_xml_foa.xml", xml=FIDE_SAMPLE):
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr(member, Path(xml).read_bytes())
    return path


def make_store(tmp_path: Path, selected=()) -> PlayerListStore:
    store = PlayerListStore(tmp_path / "data", min_rows=1)
    store.save_selection(selected)
    return store


def install_fixture(store: PlayerListStore, spec, source: Path, headers=None):
    temp = store.new_temp_path(spec)
    temp.write_bytes(source.read_bytes())
    return store.install(spec, temp, headers or {}, NOW)


@pytest.fixture
def fide_zip_bytes(tmp_path):
    return fide_zip(tmp_path / "sample.zip").read_bytes()


# --- parsers -----------------------------------------------------------------


def test_cfc_parser_tolerates_quoting_and_placeholders_and_counts_skips():
    report = ParseReport()
    members = {m["cfc_id"]: m for m in iter_cfc_members(CFC_SAMPLE, report)}

    assert report.rows == 9 == len(members)
    assert dict(report.skipped) == {
        SKIP_NO_NAME: 1,
        SKIP_ANONYMOUS: 1,
        SKIP_BAD_NUMBER: 1,
        SKIP_TOO_FEW_FIELDS: 1,
        SKIP_BAD_ID: 1,
        SKIP_DUPLICATE_ID: 1,
    }
    assert report.skipped_total == 6
    assert "9 rows read, 6 skipped" in report.summary()

    marc = members[171117]
    assert (marc["last"], marc["first"], marc["city"]) == (
        "Tremblay",
        "Marc",
        "Montréal",
    )
    assert (marc["rating"], marc["active_rating"], marc["fide_id"]) == (
        1991,
        1898,
        2600001,
    )
    assert members[144493]["last"] == "" and members[144493]["first"] == "Joey"
    assert members[112292]["city"] == "Marseille, FRANCE"
    assert members[126469]["city"] == "" and members[126469]["province"] == ""
    assert members[174892]["active_high"] is None  # -1 in the High column
    assert members[182731]["city"] == ""  # "x" placeholder
    assert members[165306]["fide_id"] is None and members[165306]["rating"] is None
    assert members[100301]["last"] == "Côté"  # Windows-1252 decoding


def test_cfc_parser_rejects_a_file_without_the_cfc_header():
    with pytest.raises(PlayerListFormatError):
        list(iter_cfc_members_from_text("a,b,c\n1,2,3\n", ParseReport()))


def test_fide_parser_reads_member_name_from_archive_and_counts_skips(tmp_path):
    path = fide_zip(tmp_path / "list.zip", member="renamed_by_fide.xml")
    report = ParseReport()
    players = {p["fide_id"]: p for p in iter_fide_players(path, report)}

    assert report.rows == 4
    assert dict(report.skipped) == {
        SKIP_BAD_ID: 1,
        SKIP_NO_NAME: 1,
        SKIP_DUPLICATE_ID: 1,
    }
    carlsen = players[1503014]
    assert carlsen["name"] == "Carlsen, Magnus"
    assert (carlsen["standard"], carlsen["rapid"], carlsen["blitz"]) == (
        2823,
        2801,
        2860,
    )
    assert carlsen["title"] == "GM" and carlsen["birth_year"] == 1990
    sophie = players[2600002]
    assert sophie["title"] == "WFM" and sophie["sex"] == "F" and sophie["inactive"]
    assert sophie["standard"] is None


def test_fide_parser_maps_rating_element_for_single_type_lists(tmp_path):
    path = fide_zip(tmp_path / "rapid.zip", member="rapid.xml", xml=FIDE_RAPID_SAMPLE)
    players = list(iter_fide_players(path, ParseReport(), rating_kind="rapid"))

    assert players[0]["rapid"] == 2801
    assert players[0]["standard"] is None and players[0]["blitz"] is None


def test_fide_parser_rejects_archive_without_xml(tmp_path):
    path = tmp_path / "empty.zip"
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr("readme.txt", "no players")
    with pytest.raises(PlayerListFormatError):
        list(iter_fide_players(path, ParseReport()))


# --- store: selection, throttle, metadata ------------------------------------------


def test_default_selection_is_the_constant_and_cfc_is_off(tmp_path):
    store = PlayerListStore(tmp_path)
    assert store.selected_keys() == DEFAULT_PLAYER_LISTS == ("fide_combined",)
    assert "cfc_members" not in store.selected_keys()
    assert [spec.key for spec in PLAYER_LISTS] == [
        "fide_combined",
        "fide_standard",
        "fide_rapid",
        "fide_blitz",
        "cfc_members",
    ]
    assert "names, cities and CFC IDs" in CFC.description


def test_throttle_checks_each_list_at_most_once_per_interval(tmp_path):
    assert PLAYER_LIST_CHECK_INTERVAL_SECONDS == 24 * 60 * 60
    assert is_check_due(ListMetadata(), NOW)
    recent = ListMetadata(checked_at=(NOW - timedelta(hours=23)).isoformat())
    assert not is_check_due(recent, NOW)
    old = ListMetadata(checked_at=(NOW - timedelta(hours=24)).isoformat())
    assert is_check_due(old, NOW)

    store = make_store(tmp_path, ["fide_combined", "cfc_members"])
    store.write_metadata(CFC, recent)
    assert [spec.key for spec in store.due_for_check(NOW)] == ["fide_combined"]


def test_no_lists_are_due_when_none_are_selected(tmp_path):
    store = make_store(tmp_path, [])
    assert store.due_for_check(NOW) == ()


def test_deselecting_a_list_deletes_its_local_copy(tmp_path):
    store = make_store(tmp_path, ["cfc_members"])
    install_fixture(store, CFC, CFC_SAMPLE)
    assert store.is_downloaded(CFC)

    store.save_selection(["fide_combined"])

    assert not store.list_dir(CFC).exists()
    assert store.selected_keys() == ("fide_combined",)


def test_atomic_write_leaves_no_temporary_files(tmp_path):
    target = tmp_path / "meta.json"
    atomic_write_text(target, "one")
    atomic_write_text(target, "two")
    assert target.read_text() == "two"
    assert list(tmp_path.iterdir()) == [target]


def test_md5_is_read_only_from_bare_md5_etags():
    assert md5_from_etag('"6d973a2b445d14d1a1f606fdb7dc5252"') == (
        "6d973a2b445d14d1a1f606fdb7dc5252"
    )
    assert md5_from_etag('"6ad3e3e3-3049e0d"') is None


def test_name_key_ignores_case_accents_and_punctuation():
    assert name_key("Côté, Félix") == " cote felix"


# --- store: validation and atomic replace -----------------------------------------


def test_install_validates_and_replaces_atomically(tmp_path):
    store = make_store(tmp_path, ["cfc_members"])
    data = CFC_SAMPLE.read_bytes()
    headers = {
        "content-length": str(len(data)),
        "etag": '"' + hashlib.md5(data).hexdigest() + '"',
        "last-modified": "Thu, 08 Oct 2026 18:36:01 GMT",
    }
    metadata = install_fixture(store, CFC, CFC_SAMPLE, headers)

    assert store.state(CFC) is ListState.DOWNLOADED
    assert store.data_path(CFC).read_bytes() == data
    assert metadata.row_count == 9 and metadata.skipped_total == 6
    assert metadata.etag == headers["etag"]
    assert metadata.content_length == len(data)
    assert metadata.source_url == CFC.url
    assert metadata.schema_version == 1
    assert metadata.downloaded_at == NOW.isoformat()
    saved = json.loads(store.metadata_path(CFC).read_text())
    assert saved["last_modified"] == headers["last-modified"]
    assert sorted(p.name for p in store.list_dir(CFC).iterdir()) == [
        "index.sqlite3",
        "metadata.json",
        "tdlist.txt",
    ]
    assert "Downloaded 2026-10-1" in store.describe_state(CFC)
    assert "9 players" in store.describe_state(CFC)


@pytest.mark.parametrize(
    "case",
    ["size", "md5", "row_drop", "not_a_list"],
)
def test_failed_validation_keeps_the_old_copy(tmp_path, case):
    store = make_store(tmp_path, ["cfc_members"])
    install_fixture(store, CFC, CFC_SAMPLE)
    original = store.data_path(CFC).read_bytes()

    new_data = CFC_SAMPLE.read_bytes()
    headers = {}
    if case == "size":
        headers = {"content-length": str(len(new_data) + 10)}
    elif case == "md5":
        headers = {"etag": '"' + "0" * 32 + '"'}
    elif case == "row_drop":
        new_data = b"\r\n".join(new_data.splitlines()[:4])  # 2 rows, was 9
    else:
        new_data = b"<html>Service unavailable</html>"

    temp = store.new_temp_path(CFC)
    temp.write_bytes(new_data)
    with pytest.raises(PlayerListValidationError):
        store.install(CFC, temp, headers, NOW)

    assert store.data_path(CFC).read_bytes() == original
    assert not temp.exists()
    assert sorted(p.name for p in store.list_dir(CFC).iterdir()) == [
        "index.sqlite3",
        "metadata.json",
        "tdlist.txt",
    ]
    assert store.read_metadata(CFC).row_count == 9


def test_zip_crc_failure_fails_validation(tmp_path, fide_zip_bytes):
    store = make_store(tmp_path, ["fide_combined"])
    corrupt = bytearray(fide_zip_bytes)
    # Flip a byte inside the compressed member data.
    corrupt[60] ^= 0xFF
    temp = store.new_temp_path(FIDE)
    temp.write_bytes(bytes(corrupt))

    with pytest.raises(PlayerListValidationError):
        store.install(FIDE, temp, {"content-length": str(len(corrupt))}, NOW)
    assert not store.has_data_file(FIDE)
    assert not temp.exists()


def test_minimum_row_count_fails_validation(tmp_path):
    store = PlayerListStore(tmp_path, min_rows=1000)
    with pytest.raises(PlayerListValidationError, match="at least"):
        install_fixture(store, CFC, CFC_SAMPLE)
    assert not store.is_downloaded(CFC)


# --- updates (mocked HTTP) ----------------------------------------------------


class FakeServer:
    """Answer list requests like the FIDE and CFC servers do."""

    def __init__(self, body: bytes, etag: str = '"v1"', fail: bool = False):
        self.body = body
        self.etag = etag
        self.fail = fail
        self.requests: list[httpx.Request] = []
        self.last_modified = "Sat, 17 Oct 2026 21:08:51 GMT"

    def handler(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        if self.fail:
            raise httpx.ConnectError("offline", request=request)
        headers = {
            "etag": self.etag,
            "last-modified": self.last_modified,
            "content-length": str(len(self.body)),
            "accept-ranges": "bytes",
        }
        if request.headers.get("if-none-match") == self.etag:
            return httpx.Response(304, headers={"etag": self.etag})
        if request.method == "HEAD":
            return httpx.Response(200, headers=headers)
        return httpx.Response(200, headers=headers, content=self.body)

    def client(self) -> httpx.Client:
        return httpx.Client(transport=httpx.MockTransport(self.handler))

    @property
    def methods(self) -> list[str]:
        return [request.method for request in self.requests]


def test_missing_list_is_downloaded_without_a_check(tmp_path, fide_zip_bytes):
    store = make_store(tmp_path, ["fide_combined"])
    server = FakeServer(fide_zip_bytes)
    progress = []

    with server.client() as client:
        outcome = check_and_update(
            store, FIDE, client, now=NOW, progress=lambda d, t: progress.append(d)
        )

    assert outcome.status is CheckStatus.UPDATED
    assert server.methods == ["GET"]
    assert progress and progress[-1] == len(fide_zip_bytes)
    metadata = store.read_metadata(FIDE)
    assert metadata.etag == '"v1"' and metadata.row_count == 4
    assert metadata.checked_at == NOW.isoformat()


def test_unchanged_list_is_checked_with_a_conditional_head_only(
    tmp_path, fide_zip_bytes
):
    store = make_store(tmp_path, ["fide_combined"])
    server = FakeServer(fide_zip_bytes)
    with server.client() as client:
        check_and_update(store, FIDE, client, now=NOW)
        server.requests.clear()
        later = NOW + timedelta(days=1)
        outcome = check_and_update(store, FIDE, client, now=later)

    assert outcome.status is CheckStatus.UNCHANGED
    assert server.methods == ["HEAD"]
    sent = server.requests[0].headers
    assert sent["if-none-match"] == '"v1"'
    assert sent["if-modified-since"] == server.last_modified
    assert store.read_metadata(FIDE).checked_at == later.isoformat()


def test_changed_list_is_downloaded_again(tmp_path, fide_zip_bytes):
    store = make_store(tmp_path, ["fide_combined"])
    server = FakeServer(fide_zip_bytes)
    with server.client() as client:
        check_and_update(store, FIDE, client, now=NOW)
        server.etag = '"v2"'
        server.requests.clear()
        outcome = check_and_update(store, FIDE, client, now=NOW)

    assert outcome.status is CheckStatus.UPDATED
    assert server.methods == ["HEAD", "GET"]
    assert store.read_metadata(FIDE).etag == '"v2"'
    assert store.state(FIDE) is ListState.DOWNLOADED


def test_server_ignoring_conditional_headers_is_still_unchanged(
    tmp_path, fide_zip_bytes
):
    store = make_store(tmp_path, ["fide_combined"])
    server = FakeServer(fide_zip_bytes)
    with server.client() as client:
        check_and_update(store, FIDE, client, now=NOW)
    metadata = store.read_metadata(FIDE)
    assert conditional_headers(metadata) == {
        "If-None-Match": '"v1"',
        "If-Modified-Since": server.last_modified,
    }

    def ignore_validators(request):
        server.requests.append(request)
        return httpx.Response(
            200,
            headers={
                "etag": '"v1"',
                "last-modified": server.last_modified,
                "content-length": str(len(fide_zip_bytes)),
            },
        )

    server.requests.clear()
    with httpx.Client(transport=httpx.MockTransport(ignore_validators)) as client:
        outcome = check_and_update(store, FIDE, client, now=NOW)
    assert outcome.status is CheckStatus.UNCHANGED
    assert server.methods == ["HEAD"]


def test_network_failure_keeps_old_copy_and_records_error(tmp_path, fide_zip_bytes):
    store = make_store(tmp_path, ["fide_combined"])
    server = FakeServer(fide_zip_bytes)
    with server.client() as client:
        check_and_update(store, FIDE, client, now=NOW)
        server.fail = True
        outcome = check_and_update(store, FIDE, client, now=NOW)

    assert outcome.status is CheckStatus.FAILED
    assert "offline" in outcome.message
    assert store.state(FIDE) is ListState.ERROR
    assert store.is_downloaded(FIDE)
    assert "keeping the copy" in store.describe_state(FIDE)


def test_cancelled_download_removes_the_temporary_file(tmp_path, fide_zip_bytes):
    store = make_store(tmp_path, ["fide_combined"])
    server = FakeServer(fide_zip_bytes)
    with server.client() as client:
        outcome = check_and_update(
            store, FIDE, client, now=NOW, progress=None, cancelled=lambda: True
        )

    assert outcome.status is CheckStatus.CANCELLED
    assert not store.has_data_file(FIDE)
    assert not list(store.list_dir(FIDE).glob("*.part"))


# --- search: sources and requests ----------------------------------------------


def test_source_checkboxes_choose_the_sources():
    assert selected_sources(True, True) == (SOURCE_FIDE, SOURCE_CFC)
    assert selected_sources(True, False) == (SOURCE_FIDE,)
    assert selected_sources(False, True) == (SOURCE_CFC,)
    assert selected_sources(False, False) == ()

    none = SearchRequest.from_inputs(SearchMode.NAME, "Carlsen", False, False)
    assert "at least one source" in (none.validation_error() or "")


def test_search_request_never_guesses_the_mode_from_digits():
    by_name = SearchRequest.from_inputs(SearchMode.NAME, "1503014", True, True)
    assert by_name.validation_error() is None
    assert by_name.player_id is None

    assert SearchRequest.from_inputs(
        SearchMode.NAME, "C", True, True
    ).validation_error()
    assert SearchRequest.from_inputs(
        SearchMode.NAME, " ", True, True
    ).validation_error()
    bad_id = SearchRequest.from_inputs(SearchMode.FIDE_ID, "Carlsen", True, True)
    assert "positive whole number" in (bad_id.validation_error() or "")
    assert SearchRequest.from_inputs(
        SearchMode.CFC_ID, "0", True, True
    ).validation_error()
    good = SearchRequest.from_inputs(SearchMode.CFC_ID, " 100300 ", False, True)
    assert good.validation_error() is None and good.player_id == 100300


# --- search: merge and dedupe ----------------------------------------------------


def _fide(fide_id, name, std=None, rapid=None):
    return fide_hit(
        {
            "fide_id": str(fide_id),
            "name": name,
            "standard_rating": std,
            "rapid_rating": rapid,
            "federation": "CAN",
        }
    )


def _cfc(cfc_id, first, last, rating, fide_id=None):
    record = {
        "cfc_id": cfc_id,
        "name_first": first,
        "name_last": last,
        "regular_rating": rating,
        "addr_city": "Montréal",
        "addr_province": "QC",
    }
    if fide_id:
        record["fide_id"] = fide_id
    return cfc_hit(record)


def test_merge_joins_rows_on_fide_number_and_keeps_ratings_apart():
    rows = merge_search_hits(
        [
            _fide(2600001, "Tremblay, Marc", std=1950),
            _fide(2600002, "Tremblay, Sophie", rapid=1875),
        ],
        [
            _cfc(171117, "Marc", "Tremblay", 1991, fide_id=2600001),
            _cfc(165306, "Ethan", "Ngo", 208),
        ],
    )

    by_name = {row.name: row for row in rows}
    assert [row.name for row in rows] == [
        "Ethan Ngo",
        "Tremblay, Marc",
        "Tremblay, Sophie",
    ]
    marc = by_name["Tremblay, Marc"]
    assert marc.source_label == SOURCE_LABEL_BOTH == "FIDE + CFC"
    assert (marc.fide_id, marc.cfc_id) == (2600001, 171117)
    assert (marc.fide_rating_text, marc.cfc_rating_text) == ("1950", "1991")
    assert by_name["Tremblay, Sophie"].source_label == "FIDE"
    assert by_name["Tremblay, Sophie"].fide_rating_text == "1875 (rapid)"
    assert by_name["Tremblay, Sophie"].cfc_rating_text == ""
    ethan = by_name["Ethan Ngo"]
    assert ethan.source_label == "CFC" and ethan.fide_id is None
    assert ethan.fide_rating_text == ""


def test_merge_drops_duplicates_and_keeps_unmatched_cfc_rows():
    rows = merge_search_hits(
        [
            _fide(2600001, "Tremblay, Marc", std=1950),
            _fide(2600001, "Tremblay, Marc", std=1950),
        ],
        [
            _cfc(171117, "Marc", "Tremblay", 1991, fide_id=2600001),
            _cfc(171117, "Marc", "Tremblay", 1991, fide_id=2600001),
            _cfc(171118, "Marc", "Tremblay", 1500, fide_id=2600001),
            _cfc(100300, "Magnus", "Carlsen", 2800, fide_id=1503014),
        ],
    )

    assert len(rows) == 3
    labels = sorted((row.source_label, row.cfc_id) for row in rows)
    assert labels == [("CFC", 100300), ("CFC", 171118), ("FIDE + CFC", 171117)]
    carlsen = next(row for row in rows if row.cfc_id == 100300)
    assert carlsen.fide_id == 1503014  # shown from the CFC record


def test_merged_player_data_fills_both_ids_and_fide_fields():
    row = merge_search_hits(
        [_fide(2600001, "Tremblay, Marc", std=1950)],
        [_cfc(171117, "Marc", "Tremblay", 1991, fide_id=2600001)],
    )[0]
    data = row.player_data()

    assert data["fide_id"] == 2600001 and data["cfc_id"] == 171117
    assert data["name"] == "Tremblay, Marc"
    assert data["rating"] == 1950 and data["fide_standard"] == 1950
    assert data["federation"] == "CAN"

    cfc_only = merge_search_hits([], [_cfc(165306, "Ethan", "Ngo", 208)])[0]
    assert cfc_only.player_data()["cfc_id"] == 165306
    assert "fide_id" not in cfc_only.player_data()


def test_merged_rows_rank_surname_matches_first():
    rows = merge_search_hits(
        [
            _fide(10081160, "Abaho Allan Smith"),
            _fide(48764272, "Agrima Smitha Shiju"),
            _fide(2600010, "Smith, John"),
        ],
        [_cfc(100400, "Anna", "Smithers", 1400)],
        term="smith",
    )
    assert [row.name for row in rows] == [
        "Smith, John",
        "Abaho Allan Smith",
        "Agrima Smitha Shiju",
        "Anna Smithers",
    ]


def test_status_line_reports_each_source():
    text = format_search_status(
        [
            SourceStatus(SOURCE_FIDE, SourceState.DONE, count=20, origin="local list"),
            SourceStatus(SOURCE_CFC, SourceState.SEARCHING),
        ]
    )
    assert text == "FIDE: 20 results (local list) · CFC: searching…"
    failed = SourceStatus(SOURCE_CFC, SourceState.FAILED, message="timed out")
    assert failed.text() == "CFC: error: timed out"
    assert (
        SourceStatus(SOURCE_FIDE, SourceState.DONE, count=1).text() == "FIDE: 1 result"
    )


# --- search: local lists and live fallback -----------------------------------------


class RecordingLive:
    def __init__(self):
        self.calls = []

    def lookups(self) -> LiveLookups:
        def cfc_by_id(cfc_id):
            self.calls.append(("cfc_id", cfc_id))
            return {
                "cfc_id": cfc_id,
                "name_first": "Magnus",
                "name_last": "Carlsen",
                "fide_id": 1503014,
            }

        return LiveLookups(cfc_by_id)


@pytest.fixture
def local_store(tmp_path):
    store = make_store(tmp_path, ["fide_combined", "cfc_members"])
    install_fixture(store, FIDE, fide_zip(tmp_path / "fide.zip"))
    install_fixture(store, CFC, CFC_SAMPLE)
    return store


def test_local_lists_are_searched_without_live_lookups(local_store):
    live = RecordingLive()
    request = SearchRequest(SearchMode.NAME, "tremblay", (SOURCE_FIDE, SOURCE_CFC))

    fide = search_source(SOURCE_FIDE, request, local_store, live.lookups())
    cfc = search_source(SOURCE_CFC, request, local_store, live.lookups())

    assert live.calls == []
    assert fide.origin == cfc.origin == "local list"
    assert sorted(hit.name for hit in fide.hits) == [
        "Tremblay, Marc",
        "Tremblay, Sophie",
    ]
    assert [hit.cfc_id for hit in cfc.hits] == [171117]
    rows = merge_search_hits(fide.hits, cfc.hits)
    assert [row.source_label for row in rows] == ["FIDE + CFC", "FIDE"]


def test_local_id_searches_and_cross_source_lookups(local_store):
    live = RecordingLive().lookups()
    by_fide = SearchRequest(SearchMode.FIDE_ID, "1503014", (SOURCE_FIDE, SOURCE_CFC))
    assert [
        h.name for h in search_source(SOURCE_FIDE, by_fide, local_store, live).hits
    ] == ["Carlsen, Magnus"]
    # CFC members carry FIDE numbers, so a FIDE ID search finds them too.
    assert [
        h.cfc_id for h in search_source(SOURCE_CFC, by_fide, local_store, live).hits
    ] == [100300]

    by_cfc = SearchRequest(SearchMode.CFC_ID, "100300", (SOURCE_FIDE, SOURCE_CFC))
    fide = search_source(SOURCE_FIDE, by_cfc, local_store, live)
    assert [h.fide_id for h in fide.hits] == [1503014]
    assert "via FIDE number 1503014" in fide.status().text()

    no_fide = SearchRequest(SearchMode.CFC_ID, "165306", (SOURCE_FIDE,))
    result = search_source(SOURCE_FIDE, no_fide, local_store, live)
    assert result.hits == () and "no FIDE number" in result.message


def test_without_downloaded_lists_only_cfc_id_searches_go_online(tmp_path):
    store = make_store(tmp_path, [])
    live = RecordingLive()
    name = SearchRequest(SearchMode.NAME, "Tremblay", (SOURCE_FIDE, SOURCE_CFC))

    fide = search_source(SOURCE_FIDE, name, store, live.lookups())
    cfc = search_source(SOURCE_CFC, name, store, live.lookups())
    assert fide.status().state is SourceState.UNAVAILABLE
    assert cfc.status().state is SourceState.UNAVAILABLE
    assert "Player lists" in fide.message and "Player lists" in cfc.message
    assert live.calls == []

    by_cfc = SearchRequest(SearchMode.CFC_ID, "100300", (SOURCE_CFC,))
    online = search_source(SOURCE_CFC, by_cfc, store, live.lookups())
    assert live.calls == [("cfc_id", 100300)]
    assert online.origin == "online"
    assert [hit.cfc_id for hit in online.hits] == [100300]

    by_fide = SearchRequest(SearchMode.FIDE_ID, "1503014", (SOURCE_CFC,))
    unavailable = search_source(SOURCE_CFC, by_fide, store, live.lookups())
    assert not unavailable.available
    assert unavailable.status().state is SourceState.UNAVAILABLE
    assert live.calls == [("cfc_id", 100300)]


def test_single_type_fide_lists_combine_their_ratings(tmp_path):
    store = make_store(tmp_path, ["fide_standard", "fide_rapid"])
    install_fixture(
        store, get_player_list("fide_standard"), fide_zip(tmp_path / "std.zip")
    )
    install_fixture(
        store, FIDE_RAPID, fide_zip(tmp_path / "rapid.zip", xml=FIDE_RAPID_SAMPLE)
    )
    request = SearchRequest(SearchMode.FIDE_ID, "1503014", (SOURCE_FIDE,))

    hit = search_source(SOURCE_FIDE, request, store, RecordingLive().lookups()).hits[0]

    assert (hit.fide_standard, hit.fide_rapid, hit.fide_blitz) == (2823, 2801, None)


# --- boundaries -----------------------------------------------------------------


def test_player_lists_package_does_not_import_qt_or_gui():
    package = Path(__file__).parents[1] / "src" / "gambitpairing" / "player_lists"
    for source_file in package.rglob("*.py"):
        tree = ast.parse(source_file.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            names = []
            if isinstance(node, ast.Import):
                names = [alias.name for alias in node.names]
            elif isinstance(node, ast.ImportFrom) and node.module:
                names = [node.module]
            for name in names:
                assert not name.startswith(("PyQt", "PySide", "gambitpairing.gui")), (
                    source_file,
                    name,
                )
