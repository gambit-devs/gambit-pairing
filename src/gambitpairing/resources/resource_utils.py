# gambitpairing/resources/resource_utils.py
"""Utility functions for accessing package resources at runtime."""

# Gambit Pairing
# Copyright (C) year nrv
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
# along with this program.  If not, see <https://www.gnu.org/licenses/>.
# gambitpairing/resources/resource_utils.py

import sys
from pathlib import Path

# Use importlib.resources for Python 3.9+ or importlib_resources backport
if sys.version_info >= (3, 9):
    from importlib import resources
else:
    import importlib_resources as resources


def get_resource_path(resource_name: str, subpackage: str = "") -> Path:
    """
    Get the path to a resource file.

    Parameters
    ----------
    resource_name : str
        Name of the resource file (e.g., 'icon.png')
    subpackage : str, optional
        Subpackage name (e.g., 'icons' for icons subdirectory), by default ""

    Returns
    -------
    Path
        Path to the resource file

    Raises
    ------
    FileNotFoundError
        If the resource file is not found in the specified package
    """
    if subpackage:
        package_path = f"gambitpairing.resources.{subpackage}"
    else:
        package_path = "gambitpairing.resources"

    try:
        with resources.path(package_path, resource_name) as resource_path:
            return resource_path

    except (ModuleNotFoundError, FileNotFoundError) as e:
        raise FileNotFoundError(
            f"Resource '{resource_name}' not found in package '{package_path}'"
        ) from e


def read_resource_text(
    resource_name: str, subpackage: str = "", encoding: str = "utf-8"
) -> str:
    """
    Read a text resource file.

    Parameters
    ----------
    resource_name : str
        Name of the resource file
    subpackage : str, optional
        Subpackage name, by default ""
    encoding : str, optional
        Text encoding, by default "UTF-8"

    Returns
    -------
    str
        Content of the resource file as string

    Raises
    ------
    FileNotFoundError
        If the resource file is not found in the specified package
    """
    if subpackage:
        package_path = f"gambitpairing.resources.{subpackage}"
    else:
        package_path = "gambitpairing.resources"

    try:
        return resources.read_text(package_path, resource_name, encoding=encoding)
    except (ModuleNotFoundError, FileNotFoundError) as e:
        raise FileNotFoundError(
            f"Resource '{resource_name}' not found in package '{package_path}'"
        ) from e


def read_resource_binary(resource_name: str, subpackage: str = "") -> bytes:
    """
    Read a binary resource file.

    Parameters
    ----------
    resource_name : str
        Name of the resource file
    subpackage : str, optional
        Subpackage name, by default ""

    Returns
    -------
    bytes
        Content of the resource file as bytes

    Raises
    ------
    FileNotFoundError
        If the resource file is not found in the specified package
    """
    if subpackage:
        package_path = f"gambitpairing.resources.{subpackage}"
    else:
        package_path = "gambitpairing.resources"

    try:
        return resources.read_binary(package_path, resource_name)
    except (ModuleNotFoundError, FileNotFoundError) as e:
        raise FileNotFoundError(
            f"Resource '{resource_name}' not found in package '{package_path}'"
        ) from e


# Convenience functions for your specific use case
def get_style_sheet() -> str:
    """
    Get the QSS stylesheet content.

    Returns
    -------
    str
        Content of the styles.qss file
    """
    return read_resource_text("styles.qss")


def get_icon_path(icon_type: str = "png"):
    """
    Get path to the application icon.

    Parameters
    ----------
    icon_type : str, optional
        Icon file type ('png', 'ico', 'webp', 'svg'), by default "png"

    Returns
    -------
    context manager
        Context manager that yields the path to the icon file
    """
    filename = f"icon.{icon_type}"
    return get_resource_path(filename, "icons")


def get_icon_binary(icon_type: str = "png") -> bytes:
    """
    Get the icon as binary data.

    Parameters
    ----------
    icon_type : str, optional
        Icon file type ('png', 'ico', 'webp', 'svg'), by default "png"

    Returns
    -------
    bytes
        Binary content of the icon file
    """
    filename = f"icon.{icon_type}"
    return read_resource_binary(filename, "icons")


def get_ui_icon_binary(icon_name: str) -> bytes:
    """
    Get a UI icon as binary data.

    Parameters
    ----------
    icon_name : str
        Name of the icon file (e.g., 'arrow-up.svg', 'checkmark-white.svg')

    Returns
    -------
    bytes
        Binary content of the icon file
    """
    return read_resource_binary(icon_name, "icons")


#  LocalWords:  importlib
