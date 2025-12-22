"""Exceptions for use in Gambit-Pairing"""

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


# ========== Base Application Exception ==========


class GambitPairingException(Exception):
    """Base exception for all Gambit Pairing errors.

    All custom exceptions in the application should inherit from this class.
    This enables catching all application-specific errors with a single except clause.
    """

    pass


# ========== Pairing Exceptions ==========


class PairingException(GambitPairingException):
    """Base exception for pairing-related errors."""

    pass


class InvalidPairingException(PairingException):
    """Raised when a pairing configuration is invalid."""

    pass


class RepeatPairingException(PairingException):
    """Raised when attempting to pair players who have already played."""

    pass


class NoPairingAvailableException(PairingException):
    """Raised when no valid pairing can be generated."""

    pass


# ========== Tournament Exceptions ==========


class TournamentException(GambitPairingException):
    """Base exception for tournament-related errors."""

    pass


class TournamentStateException(TournamentException):
    """Raised when tournament is in an invalid state for the requested operation."""

    pass


class RoundNotFoundException(TournamentException):
    """Raised when a requested round does not exist."""

    pass


class DuplicatePlayerException(TournamentException):
    """Raised when attempting to add a player that already exists."""

    pass


# ========== Player Exceptions ==========


class PlayerException(GambitPairingException):
    """Base exception for player-related errors."""

    pass


class PlayerNotFoundException(PlayerException):
    """Raised when a requested player cannot be found."""

    pass


class InvalidPlayerDataException(PlayerException):
    """Raised when player data is invalid or incomplete."""

    pass


# ========== Result Exceptions ==========


class ResultException(GambitPairingException):
    """Base exception for result recording errors."""

    pass


class InvalidResultException(ResultException):
    """Raised when a result is invalid (e.g., score out of range)."""

    pass


class DuplicateResultException(ResultException):
    """Raised when attempting to record a result that already exists."""

    pass


class ResultNotFoundException(ResultException):
    """Raised when a requested result cannot be found."""

    pass


# ========== Validation Exceptions ==========


class ValidationException(GambitPairingException):
    """Base exception for validation errors."""

    pass


class EmailValidationException(ValidationException):
    """Raised when an email address is invalid."""

    pass


class PhoneValidationException(ValidationException):
    """Raised when a phone number is invalid."""

    pass


class RatingValidationException(ValidationException):
    """Raised when a rating value is invalid."""

    pass


# ========== File/Resource Exceptions ==========


class ResourceException(GambitPairingException):
    """Base exception for resource-related errors."""

    pass


class IconException(ResourceException):
    """Raised when there's an error loading or using the app icon."""

    pass


class StyleException(ResourceException):
    """Raised when there's an error loading or applying the app style."""

    pass


class FileLoadException(ResourceException):
    """Raised when a file cannot be loaded."""

    pass


class FileSaveException(ResourceException):
    """Raised when a file cannot be saved."""

    pass


# ========== API Exceptions ==========


class APIException(GambitPairingException):
    """Base exception for API-related errors."""

    pass


class FIDEAPIException(APIException):
    """Raised when there's an error communicating with the FIDE API."""

    pass


class NetworkException(APIException):
    """Raised when there's a network connectivity error."""

    pass


# ========== Configuration Exceptions ==========


class ConfigurationException(GambitPairingException):
    """Base exception for configuration errors."""

    pass


class InvalidConfigurationException(ConfigurationException):
    """Raised when configuration data is invalid."""

    pass


class MissingConfigurationException(ConfigurationException):
    """Raised when required configuration is missing."""

    pass
