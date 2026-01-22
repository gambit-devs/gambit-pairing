"""Validation utilities for Gambit Pairing.

This module provides reusable validation functions with consistent error handling.
"""

import re
from typing import Optional

from gambitpairing.exceptions import (
    EmailValidationException,
    PhoneValidationException,
    RatingValidationException,
)


class ValidationResult:
    """Result of a validation operation.

    Attributes:
        is_valid: Whether the validation passed
        error_message: Human-readable error message if invalid
        sanitized_value: Cleaned/normalized value if valid
    """

    def __init__(
        self,
        is_valid: bool,
        error_message: Optional[str] = None,
        sanitized_value: Optional[str] = None,
    ):
        self.is_valid = is_valid
        self.error_message = error_message
        self.sanitized_value = sanitized_value

    def __bool__(self) -> bool:
        """Allow using result in boolean context: if result: ..."""
        return self.is_valid

    def __repr__(self) -> str:
        if self.is_valid:
            return f"ValidationResult(VALID, {self.sanitized_value!r})"
        return f"ValidationResult(INVALID, {self.error_message!r})"


# ========== Email Validation ==========


def validate_email(email: Optional[str], required: bool = False) -> ValidationResult:
    """Validate an email address.

    Args:
        email: Email address to validate
        required: Whether email is required (empty = invalid)

    Returns:
        ValidationResult with validation status

    Example:
        >>> result = validate_email("user@example.com")
        >>> if result:
        ...     print(f"Valid email: {result.sanitized_value}")
    """
    if not email or not email.strip():
        if required:
            return ValidationResult(
                is_valid=False,
                error_message="Email address is required",
            )
        return ValidationResult(is_valid=True, sanitized_value=None)

    email = email.strip()

    # RFC 5322 simplified email regex
    pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"

    if re.match(pattern, email):
        return ValidationResult(is_valid=True, sanitized_value=email)

    return ValidationResult(
        is_valid=False,
        error_message=f"Invalid email format: {email}",
    )


def validate_email_strict(email: str) -> None:
    """Validate email and raise exception if invalid.

    Args:
        email: Email address to validate

    Raises:
        EmailValidationException: If email is invalid
    """
    result = validate_email(email, required=True)
    if not result.is_valid:
        raise EmailValidationException(result.error_message)


# ========== Phone Validation ==========


def validate_phone(phone: Optional[str], required: bool = False) -> ValidationResult:
    """Validate a phone number.

    Accepts various formats:
    - (123) 456-7890
    - 123-456-7890
    - 123.456.7890
    - 1234567890
    - +1 123 456 7890

    Args:
        phone: Phone number to validate
        required: Whether phone is required

    Returns:
        ValidationResult with validation status and sanitized number
    """
    if not phone or not phone.strip():
        if required:
            return ValidationResult(
                is_valid=False,
                error_message="Phone number is required",
            )
        return ValidationResult(is_valid=True, sanitized_value=None)

    phone = phone.strip()

    # Remove common formatting characters
    digits_only = re.sub(r"[\s\-\.\(\)\+]", "", phone)

    # Check if it's all digits (possibly with country code)
    if not digits_only.isdigit():
        return ValidationResult(
            is_valid=False,
            error_message=f"Phone number contains invalid characters: {phone}",
        )

    # Check length (US: 10 digits, International: 10-15 digits)
    if len(digits_only) < 10 or len(digits_only) > 15:
        return ValidationResult(
            is_valid=False,
            error_message=f"Phone number must be 10-15 digits: {phone}",
        )

    return ValidationResult(is_valid=True, sanitized_value=digits_only)


def validate_phone_strict(phone: str) -> str:
    """Validate phone and return sanitized number or raise exception.

    Args:
        phone: Phone number to validate

    Returns:
        Sanitized phone number (digits only)

    Raises:
        PhoneValidationException: If phone is invalid
    """
    result = validate_phone(phone, required=True)
    if not result.is_valid:
        raise PhoneValidationException(result.error_message)
    return result.sanitized_value or ""


# ========== Rating Validation ==========


def validate_rating(
    rating: Optional[int], min_rating: int = 0, max_rating: int = 3000
) -> ValidationResult:
    """Validate a chess rating.

    Args:
        rating: Rating value to validate
        min_rating: Minimum allowed rating
        max_rating: Maximum allowed rating

    Returns:
        ValidationResult with validation status
    """
    if rating is None:
        return ValidationResult(is_valid=True, sanitized_value=None)

    try:
        rating_int = int(rating)
    except (ValueError, TypeError):
        return ValidationResult(
            is_valid=False,
            error_message=f"Rating must be a number: {rating}",
        )

    if rating_int < min_rating or rating_int > max_rating:
        return ValidationResult(
            is_valid=False,
            error_message=f"Rating must be between {min_rating} and {max_rating}: {rating_int}",
        )

    return ValidationResult(is_valid=True, sanitized_value=str(rating_int))


def validate_rating_strict(
    rating: int, min_rating: int = 0, max_rating: int = 3000
) -> int:
    """Validate rating and return integer or raise exception.

    Args:
        rating: Rating value to validate
        min_rating: Minimum allowed rating
        max_rating: Maximum allowed rating

    Returns:
        Validated rating as integer

    Raises:
        RatingValidationException: If rating is invalid
    """
    result = validate_rating(rating, min_rating, max_rating)
    if not result.is_valid:
        raise RatingValidationException(result.error_message)
    return int(result.sanitized_value or "0")


# ========== FIDE ID Validation ==========


def validate_fide_id(
    fide_id: Optional[str], required: bool = False
) -> ValidationResult:
    """Validate a FIDE ID.

    FIDE IDs are positive integers, typically 6-8 digits.

    Args:
        fide_id: FIDE ID to validate
        required: Whether FIDE ID is required

    Returns:
        ValidationResult with validation status
    """
    if not fide_id or not str(fide_id).strip():
        if required:
            return ValidationResult(
                is_valid=False,
                error_message="FIDE ID is required",
            )
        return ValidationResult(is_valid=True, sanitized_value=None)

    fide_id_str = str(fide_id).strip()

    try:
        fide_id_int = int(fide_id_str)
        if fide_id_int <= 0:
            return ValidationResult(
                is_valid=False,
                error_message="FIDE ID must be a positive number",
            )
        return ValidationResult(is_valid=True, sanitized_value=str(fide_id_int))
    except ValueError:
        return ValidationResult(
            is_valid=False,
            error_message=f"FIDE ID must be a number: {fide_id_str}",
        )


# ========== Name Validation ==========


def validate_name(name: Optional[str], required: bool = True) -> ValidationResult:
    """Validate a person's name.

    Args:
        name: Name to validate
        required: Whether name is required

    Returns:
        ValidationResult with validation status
    """
    if not name or not name.strip():
        if required:
            return ValidationResult(
                is_valid=False,
                error_message="Name is required",
            )
        return ValidationResult(is_valid=True, sanitized_value=None)

    name = name.strip()

    if len(name) < 2:
        return ValidationResult(
            is_valid=False,
            error_message="Name must be at least 2 characters",
        )

    # Check for reasonable characters (letters, spaces, hyphens, apostrophes)
    if not re.match(r"^[a-zA-Z\s\-'\.]+$", name):
        return ValidationResult(
            is_valid=False,
            error_message="Name contains invalid characters",
        )

    return ValidationResult(is_valid=True, sanitized_value=name)


# ========== Generic Validation ==========


def validate_non_empty(
    value: Optional[str], field_name: str = "Field"
) -> ValidationResult:
    """Validate that a field is not empty.

    Args:
        value: Value to validate
        field_name: Name of the field for error messages

    Returns:
        ValidationResult with validation status
    """
    if not value or not str(value).strip():
        return ValidationResult(
            is_valid=False,
            error_message=f"{field_name} cannot be empty",
        )
    return ValidationResult(is_valid=True, sanitized_value=str(value).strip())


def validate_positive_integer(
    value: Optional[int], field_name: str = "Value"
) -> ValidationResult:
    """Validate that a value is a positive integer.

    Args:
        value: Value to validate
        field_name: Name of the field for error messages

    Returns:
        ValidationResult with validation status
    """
    if value is None:
        return ValidationResult(
            is_valid=False,
            error_message=f"{field_name} is required",
        )

    try:
        int_value = int(value)
        if int_value <= 0:
            return ValidationResult(
                is_valid=False,
                error_message=f"{field_name} must be positive",
            )
        return ValidationResult(is_valid=True, sanitized_value=str(int_value))
    except (ValueError, TypeError):
        return ValidationResult(
            is_valid=False,
            error_message=f"{field_name} must be a number",
        )


def validate_score(score: float) -> ValidationResult:
    """Validate a game score (must be 0.0, 0.5, or 1.0).

    Args:
        score: Score to validate

    Returns:
        ValidationResult with validation status
    """
    valid_scores = [0.0, 0.5, 1.0]

    try:
        float_score = float(score)
        if float_score not in valid_scores:
            return ValidationResult(
                is_valid=False,
                error_message=f"Score must be 0.0, 0.5, or 1.0: {score}",
            )
        return ValidationResult(is_valid=True, sanitized_value=str(float_score))
    except (ValueError, TypeError):
        return ValidationResult(
            is_valid=False,
            error_message=f"Score must be a number: {score}",
        )
