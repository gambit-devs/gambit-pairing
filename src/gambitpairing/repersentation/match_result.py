"""Data transformation/serialization/to-from dict for MatchResult."""


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
def match_result_to_dict(match_result: MatchResult) -> Dict[str, Any]:
    """Project a MatchResult into a dictionary representation.

    This function converts a :class:`~gambitpairing.models.tournament.match_result.MatchResult`
    aggregate into a plain dictionary composed only of Python primitives.
    The resulting representation is suitable for storage, logging,
    undo/redo snapshots, and export.

    Parameters
    ----------
    match_result: MatchResult
        MatchResult stored in the dict.

    Returns
    -------
    dict
        Dictionary representation of the MatchResult.

    Notes
    -----
    This function performs no I/O and has no side effects. It is intended
    to be a pure projection of domain state.

    The representation is *lossless*: reconstructed via
    :func:`match_result_from_dict` will be semantically equivalent.

    See Also
    --------
    match_result_from_dict : Reconstruct a Tournament from its dictionary
        representation.
    """
    return {
        "white_id": match_result.white_id,
        "black_id": match_result.black_id,
        "white_score": match_result.white_score,
    }


def match_result_from_dict(data: Dict[str, Any]) -> MatchResult:
    """Retrieve a MatchResult from the dictionary representation.

    This function converts a  dictionary reperesentation into
    :class:`~gambitpairing.models.tournament.match_result.MatchResult`

    Parameters
    ----------
    dict
        Dictionary representation of the MatchResult.

    Returns
    -------
    match_result: MatchResult
        MatchResult stored in the dict.

    Notes
    -----
    This function performs no I/O and has no side effects. It is intended
    to be a pure projection of domain state.

    The representation is *lossless*: reconstructed via
    :func:`match_result_from_dict` will be semantically equivalent.

    See Also
    --------
    match_result_to_dict : Create a Tournament dictionary representation.
    """
    return cls(
        white_id=data["white_id"],
        black_id=data["black_id"],
        white_score=data["white_score"],
    )


#  LocalWords:  MatchResult
