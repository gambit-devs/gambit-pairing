"""Exit-code contracts for automation using the public testing CLI."""

import json
from pathlib import Path
import subprocess
import sys

from gambitpairing.models.player import Player


def invoke(*args):
    return subprocess.run(
        [sys.executable, "-m", "gambitpairing.testing", *map(str, args)],
        capture_output=True,
        text=True,
        check=False,
    )


def test_validation_cli_success_and_round_selection():
    sample = (
        Path(__file__).parents[1] / "src/gambitpairing/testing/test_tournament.json"
    )
    assert invoke("validate", "--file", sample, "--round", 1).returncode == 0
    assert invoke("validate", "--file", sample, "--round", 999).returncode == 2


def test_validation_cli_reports_violations(tmp_path):
    players = [Player(str(index), 1800) for index in range(4)]
    document = {
        "players": [player.to_dict() for player in players],
        "config": {"num_rounds": 2},
        "rounds": [
            {
                "round_number": 1,
                "pairings": [[players[0].id, players[1].id]],
                "results": [[players[0].id, players[1].id, 1.0]],
            },
            {
                "round_number": 2,
                "pairings": [[players[0].id, players[1].id]],
                "active_player_ids": [player.id for player in players],
            },
        ],
    }
    path = tmp_path / "missing-players.json"
    path.write_text(json.dumps(document))
    result = invoke("validate", "--file", path, "--round", 2)
    assert result.returncode == 1, result.stdout + result.stderr


def test_validation_cli_invalid_input_is_not_success(tmp_path):
    path = tmp_path / "invalid.json"
    path.write_text("not json")
    result = invoke("validate", "--file", path)
    assert result.returncode == 2
    assert "Traceback" not in result.stderr


def test_reference_instructions_do_not_claim_a_passing_run():
    assert invoke("bbp-reference").returncode == 2
