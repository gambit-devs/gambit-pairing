"""Player lists the app can keep locally."""

# Gambit Pairing
# Copyright (C) 2025  Gambit Pairing developers
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

SOURCE_FIDE = "FIDE"
SOURCE_CFC = "CFC"

FORMAT_FIDE_XML_ZIP = "fide_xml_zip"
FORMAT_CFC_TDLIST = "cfc_tdlist"

RATING_STANDARD = "standard"
RATING_RAPID = "rapid"
RATING_BLITZ = "blitz"

FIDE_DOWNLOAD_URL = "https://ratings.fide.com/download/"
CFC_TDLIST_URL = "https://storage.googleapis.com/cfc-public/data/tdlist.txt"

FIDE_ATTRIBUTION = (
    "FIDE rating lists are published by FIDE (the International Chess "
    "Federation) at ratings.fide.com."
)
CFC_ATTRIBUTION = (
    "The CFC member list (tdlist.txt) is published by the Chess Federation "
    "of Canada at chess.ca."
)


@dataclass(frozen=True)
class PlayerListSpec:
    """One downloadable player list."""

    key: str
    name: str
    source: str
    url: str
    file_name: str
    format: str
    description: str
    # The rating type a single-type FIDE list holds in its <rating> element.
    # None for lists that carry every rating type in separate elements.
    rating_kind: Optional[str] = None

    @property
    def is_zip(self) -> bool:
        return self.file_name.lower().endswith(".zip")


PLAYER_LISTS: tuple[PlayerListSpec, ...] = (
    PlayerListSpec(
        key="fide_combined",
        name="FIDE combined",
        source=SOURCE_FIDE,
        url=FIDE_DOWNLOAD_URL + "players_list_xml.zip",
        file_name="players_list_xml.zip",
        format=FORMAT_FIDE_XML_ZIP,
        description=(
            "Standard, rapid and blitz ratings for every FIDE-registered "
            "player in one XML zip file (about 50 MB)."
        ),
    ),
    PlayerListSpec(
        key="fide_standard",
        name="FIDE standard",
        source=SOURCE_FIDE,
        url=FIDE_DOWNLOAD_URL + "standard_rating_list_xml.zip",
        file_name="standard_rating_list_xml.zip",
        format=FORMAT_FIDE_XML_ZIP,
        description="FIDE standard ratings (XML zip file, about 15 MB).",
        rating_kind=RATING_STANDARD,
    ),
    PlayerListSpec(
        key="fide_rapid",
        name="FIDE rapid",
        source=SOURCE_FIDE,
        url=FIDE_DOWNLOAD_URL + "rapid_rating_list_xml.zip",
        file_name="rapid_rating_list_xml.zip",
        format=FORMAT_FIDE_XML_ZIP,
        description="FIDE rapid ratings (XML zip file, about 12 MB).",
        rating_kind=RATING_RAPID,
    ),
    PlayerListSpec(
        key="fide_blitz",
        name="FIDE blitz",
        source=SOURCE_FIDE,
        url=FIDE_DOWNLOAD_URL + "blitz_rating_list_xml.zip",
        file_name="blitz_rating_list_xml.zip",
        format=FORMAT_FIDE_XML_ZIP,
        description="FIDE blitz ratings (XML zip file, about 8 MB).",
        rating_kind=RATING_BLITZ,
    ),
    PlayerListSpec(
        key="cfc_members",
        name="CFC member list",
        source=SOURCE_CFC,
        url=CFC_TDLIST_URL,
        file_name="tdlist.txt",
        format=FORMAT_CFC_TDLIST,
        description=(
            "The CFC tournament director list (tdlist.txt, about 5 MB). It "
            "contains members' names, cities and CFC IDs, with their CFC "
            "ratings and FIDE numbers."
        ),
    ),
)

PLAYER_LISTS_BY_KEY: dict[str, PlayerListSpec] = {
    spec.key: spec for spec in PLAYER_LISTS
}


def get_player_list(key: str) -> PlayerListSpec:
    """Return the list with ``key``; raise ``KeyError`` for unknown keys."""
    return PLAYER_LISTS_BY_KEY[key]


def player_lists_for_source(source: str) -> tuple[PlayerListSpec, ...]:
    return tuple(spec for spec in PLAYER_LISTS if spec.source == source)
