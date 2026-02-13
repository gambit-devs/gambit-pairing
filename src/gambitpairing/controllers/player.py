"""Player controler for managing player creation."""

from gambitpairing.models.player.fide_player import FidePlayer


def create_fide_player(player_data):
    """Create a FidePlayer data class.

    Parameters
    ----------
    player_data : dict {
        name: str,
        rating: Optional[int] = None,
        phone: Optional[str] = None,
        email: Optional[str] = None,
        club: Optional[Club] = None,
        gender: Optional[str] = None,
        date_of_birth: Optional[date] = None,
        federation: Optional[str] = None,
        }
    """
    return FidePlayer.from_dict(player_data)
