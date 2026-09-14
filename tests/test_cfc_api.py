from gambitpairing.utils import api
from gambitpairing.utils.api_adapters import (
    cfc_api_to_player_dict,
    cfc_api_to_search_result,
)


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


def test_cfc_name_search_parses_search_page(monkeypatch):
    calls = []

    class Response:
        text = """
        <table>
          <tr><th>Name</th><th>City</th><th>CFC id</th><th>CFC Expiry</th>
              <th>Regular Rating</th><th>FIDE id</th></tr>
          <tr><td>Lovelace, Ada</td><td>Toronto, ON</td><td>100123</td>
              <td>2027-01-01</td><td>1800</td><td>1234567</td></tr>
        </table>
        """

        def raise_for_status(self):
            return None

    def fake_get(url, params, timeout):
        calls.append((url, params, timeout))
        return Response()

    monkeypatch.setattr(api.httpx, "get", fake_get)

    results = api.search_cfc_players("Ada Lovelace")

    assert results == [
        {
            "cfc_id": 100123,
            "name": "Lovelace, Ada",
            "rating": 1800,
            "province": "ON",
            "city": "Toronto",
            "expiry_date": "2027-01-01",
            "status": "",
            "fide_id": 1234567,
        }
    ]
    assert calls == [
        (
            "https://www.chess.ca/en/ratings/p/sr/",
            {"fn": "Ada", "ln": "Lovelace"},
            10.0,
        )
    ]
    assert cfc_api_to_player_dict(results[0])["name"] == "Lovelace, Ada"
