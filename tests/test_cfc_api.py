from gambitpairing.utils import api
from gambitpairing.utils.api_adapters import cfc_api_to_search_result


def test_cfc_search_result_adapter_handles_api_player_shape():
    result = cfc_api_to_search_result(
        {
            "cfc_id": 123456,
            "name_first": "Ada",
            "name_last": "Lovelace",
            "regular_rating": 1800,
            "addr_province": "ON",
            "addr_city": "Toronto",
            "cfc_expiry": "2027-01-01",
        }
    )

    assert result == {
        "cfc_id": 123456,
        "name": "Ada Lovelace",
        "rating": 1800,
        "province": "ON",
        "city": "Toronto",
        "expiry_date": "2027-01-01",
        "status": "",
    }


def test_cfc_player_lookup_uses_timeout_and_returns_player(monkeypatch):
    calls = []

    class Response:
        def raise_for_status(self):
            return None

        def json(self):
            return {"player": {"cfc_id": 123456, "name_last": "Lovelace"}}

    def fake_get(url, timeout):
        calls.append((url, timeout))
        return Response()

    monkeypatch.setattr(api.httpx, "get", fake_get)

    player = api.get_cfc_player_info(" 123456 ")

    assert player["cfc_id"] == 123456
    assert calls == [("https://server.chess.ca/api/player/v1/123456", 10.0)]
