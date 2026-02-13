"""Player models for CFC report builder."""

# Copyright (C) 2024 Nicolas Vaagen
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

"""This is from my unfinished CFC report builder software. Will need some modification, but gives a starting point"""
from gambitpairing import logger
from gambitpairing.tournament import Tournament


class Player(self):
    """A player with a CFC id, associated with tournaments.
    The base model for CFC API.

    Attributes
    ----------
    Identification:
        cfc_id : CfcIdField
            Canadian Federation of Chess ID (primary key)
        fide_id : IntegerField
            International Chess Federation ID
        cfc_expiry : DateField
            Expiration date of CFC membership

    Personal Info:
        name_first : CharField
            Player's first name
        name_last : CharField
            Player's last name
        addr_city : CharField
            City of residence
        addr_province : CharField
            Province of residence (2-letter code)

    Ratings:
        regular_rating : IntegerField
            Standard chess rating
        regular_indicator : IntegerField
            Indicator for regular rating confidence
        quick_rating : IntegerField
            Quick chess rating
        quick_indicator : IntegerField
            Indicator for quick rating confidence

    Relations:
        tournaments : ManyToManyField
            Tournaments this player participated in
        slug : SlugField
            URL-friendly unique identifier

    Notes
    -----
    player is the base model used in the CFC API.
    Players can be both organizers and directors.
    """

    def __init__(self):
        # Identification
        self.cfc_id = None
        self.fide_id = None

        # Personal Information
        self.name_first = None
        self.name_last = None
        self.addr_city = None
        self.addr_province = None

        # Ratings
        self.regular_rating = None
        self.regular_indicator = None
        self.quick_rating = None
        self.quick_indicator = None
        self.slug = None

    def save(self, *args, **kwargs):
        """
        Save the current instance to the database, ensuring a unique slug. overrides
        save behavior by automatically generating a slug and add `force_update` flag and logs the action
        to **kwargs.

        Parameters
        ----------
        args : tuple
            Positional arguments passed to the parent save method.
        kwargs : dict
            Keyword arguments passed to the parent save method. Includes a default
        """

        self.slug = self._generate_slug()
        logger.info("(%s) saved. slug (%s) created for it", self, self.slug)
        super().save(*args, **kwargs)

    def _generate_slug(self) -> str:
        return f"{type(self).__name__}|{self.cfc_id}"

    def get_absolute_url(self):
        pass

    def __str__(self):
        return f"{self.name_first} {self.name_last} ({self.cfc_id})"

    @classmethod
    def create(cls, player_info: dict) -> "Player":
        """
        Factory method to create a new instance of Player.


        Parameters
        ----------
        player_info : dict - JSON response from the API.
            example:
            {
                'cfc_id': 123123,
                'cfc_expiry': '2020-01-02',
                'fide_id': 0,
                'name_first': 'Michael',
                'name_last': 'Williams',
                'addr_city': "St.John's",
                'addr_province': 'NL',
                'regular_rating': 200,
                'regular_indicator': 11,
                'quick_rating': 200,
                'quick_indicator': 11,
                'events': [{'id': 199806005,
                    'name': 'MacDonald Dr RR',
                    'date_end': '1998-05-14',
                    'rating_type': 'R',
                    'games_played': 11,
                    'score': 0.0,
                    'rating_pre': 0,
                    'rating_perf': 0,
                    'rating_post': 200,
                    'rating_indicator': 11}],
                'orgarb': [],
                'is_organizer': False,
                'is_arbiter': False
            },

        Returns
        -------
        Player
            New instance of Player with the basic information set

        Raises
        ------
        ValueError
            if the player_info is incomplete
        """

        player = Player(
            cfc_id=player_info["cfc_id"],
            fide_id=player_info["fide_id"],
            name_first=player_info["name_first"],
            name_last=player_info["name_last"],
            addr_city=player_info["addr_city"],
            addr_province=player_info["addr_province"],
            regular_rating=player_info["regular_rating"],
            regular_indicator=player_info["regular_indicator"],
            quick_rating=player_info["quick_rating"],
            quick_indicator=player_info["quick_indicator"],
        )

        logger.debug("Created: %s with CFC ID: %s", player, player.cfc_id)

        return player

    @classmethod
    def create_player_if_not_exists(cls, player_info: dict) -> "Player":
        if not Player.objects.filter(cfc_id=player_info["cfc_id"]).exists():
            player = Player.create(player_info)
            return player, True  # Created new player
        return (
            Player.objects.get(cfc_id=player_info["cfc_id"]),
            False,
        )  # Player already existed
