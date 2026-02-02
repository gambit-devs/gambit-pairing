"""work with and produce ctr cfc file."""

# horizon_pair
# Copyright (C) 2024  Nicolas Vaagen
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
# Copyright (C) 2024  Nicolas Vaagen
from typing import List

from models import Match, Player

from . import logger


class CtrCreationException(Exception):
    """Something went wrong with ctr creation."""

    pass


def make_match_report(m: Match, player: Player) -> List[str]:
    """Make a match part of ctr report file for a given player

    returns: a list of strings to be written to ctr_report one per line
    """

    logger.info("make_match_report entered with match: %s, and player: %s", m, player)
    match_result = m.result
    if match_result == player.cfc_id:
        res = "W"
        points = "1.0"
    elif match_result is None:
        res = "D"
        points = "0.5"
    else:
        res = "L"
        points = "0.0"

    # match report
    match_report: List[str] = []

    # line 1
    match_report.append(f'"{player.cfc_id}"')

    # line 2
    match_report.append(f'"{res}","0"')

    # line 3
    match_report.append(f'"{points}"')

    return match_report


def CTR_builder(
    session,
    name=None,
    rounds=None,
    pairing_system=None,
    to_cfc_id=None,
    td_cfc_id=None,
    province=None,
    date=None,
) -> CTR:
    """Build a CTR model

    Parameters
    ----------
    session : the active Django session_services
        used to get player and match info
    name : str
        Tournament Name
    rounds : int
        the number of rounds in the tournament
    pairing_system : str
        Pairing System used. ie: Swiss, Round Robin
    to_cfc_id : CfdId
        Tournament Organizer CFC ID
    td_cfc_id : CfdId
        Tournament Director CFC ID
    province : str
        Province abreviation tournament is in
    date : str
        Date of the tournament

    Returns
    -------
    CTR : cfc_report.models.ctr.CTR
        A CTR model
    """
    logger.info(
        "CTR_builder entered w -- session_services: %s, name: %s,  \
        rounds: %s, pairing_system: %s, TO CFC: %s, TD CFC: %s, \
        date: %s",
        session,
        name,
        rounds,
        pairing_system,
        to_cfc_id,
        td_cfc_id,
        date,
    )

    player_ids = session.get_player_ids()
    num_players = len(player_ids)
    # make sure the tournament has requisite data
    try:
        assert name is not None
        assert pairing_system is not None
        assert td_cfc_id is not None
        assert province is not None
        assert date is not None
        assert num_players > 0
    except AssertionError:
        print(f"make_ctr_report: missing tournament data in {name}")
        raise CtrCreationException("missing tournament data.")

    # get the pairing abbreviation
    if pairing_system == "Swiss":
        pairing_abbreviation = "S"
    else:
        # Round Robin is the default;
        # I think this works ie: I think there are only 2 options
        pairing_abbreviation = "R"

    """List with one index per CTR line"""
    ctr: List[str] = [f""""{name}","{province}","0","{pairing_abbreviation}","{
    date}","{num_players}","{td_cfc_id}","{to_cfc_id}"\n"""]

    # start by building the 1st line of the ctr

    logger.info("CTR_builder(...) made: ctr: %s", ctr)

    # add all matches to report
    for rnd in range(rounds):
        # get matches in round
        matches = Match.objects.filter(round_number=rnd)

        logger.info("building round: %s \nw: Matches: %s", rnd, matches)
        for match in matches:
            match_report = make_match_report(match, match.white)
            match_report += make_match_report(match, match.black)
            # append both players match reports to main report
            for line in match_report:
                ctr.append(line)


def ctr_to_str(ctr) -> str:
    """Take a ctr prototype and return a ctr report as a string."""
    ctr_str = ""
    for line in ctr:
        ctr_str += line + "\n"
    return ctr_str


if __name__ == "__main__":
    # test
    T = {
        "name": "my test tournament",
        "rounds": 4,
        "pairing_system": "Swiss",
        "td_cfc": "111111",
        "to_cfc": "222222",
        "date_year": "1",
        "date_month": "1",
        "date_day": "1",
    }
    ctr_test = CTR_builder(T)

    print(ctr_test)
    ctr_test.write_to_file()
