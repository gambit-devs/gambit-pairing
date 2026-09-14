"""Qt-free identifiers for domain entities."""

from uuid import uuid4


def generate_id(prefix: str = "item_") -> str:
    return f"{prefix}{uuid4().hex}"
