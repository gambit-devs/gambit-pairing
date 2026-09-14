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
    result = invoke("validate", "--file", sample, "--round", 1)
    assert result.returncode == 2
    assert "not_verified" in result.stdout
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


def test_reference_missing_explicit_engine_does_not_claim_a_passing_run(tmp_path):
    assert (
        invoke("bbp-reference", "--path", tmp_path / "missing-engine").returncode == 2
    )


def test_generate_seed_zero_and_ranges_are_reproducible(tmp_path):
    for label in ("first", "second"):
        result = invoke(
            "generate",
            "--players",
            "4-6",
            "--rounds",
            "1-2",
            "--tournaments",
            3,
            "--seed",
            0,
            "--output",
            tmp_path / f"{label}.json",
        )
        assert result.returncode == 0, result.stdout + result.stderr
    for index in range(1, 4):
        assert json.loads((tmp_path / f"first_{index}.json").read_text()) == json.loads(
            (tmp_path / f"second_{index}.json").read_text()
        )


def test_generate_validate_reports_incomplete_verification(tmp_path):
    path = tmp_path / "generated.json"
    result = invoke(
        "generate",
        "--players",
        4,
        "--rounds",
        1,
        "--seed",
        0,
        "--validate",
        "--output",
        path,
    )
    assert result.returncode == 2, result.stdout + result.stderr
    report = json.loads(path.read_text())["fpc_report"]
    assert report["verification_status"] == "not_verified"
    assert report["limitations"]


def test_trf_export_contains_final_round_results(tmp_path):
    path = tmp_path / "generated.trf"
    result = invoke(
        "generate",
        "--players",
        4,
        "--rounds",
        2,
        "--seed",
        0,
        "--format",
        "trf",
        "--output",
        path,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    records = [
        line for line in path.read_text().splitlines() if line.startswith("001 ")
    ]
    assert len(records) == 4
    assert all(len(line) == 109 and int(line[101:105]) > 0 for line in records)


def test_benchmark_rejects_empty_iterations():
    result = invoke("benchmark", "--iterations", 0)
    assert result.returncode == 2
    assert "Traceback" not in result.stderr
