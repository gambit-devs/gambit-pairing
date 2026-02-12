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


import hashlib
import os
from pathlib import Path
import shutil
import sys
import tempfile
from typing import Any, Dict, Optional, Tuple
import zipfile

import httpx
from packaging.version import parse as parse_version

from gambitpairing.constants import UPDATE_URL
from gambitpairing.utils import setup_logger

logger = setup_logger(__name__)

# Fallback update URL if not defined elsewhere


class Updater:
    """Handles checking for and applying application updates from GitHub Releases."""

    def __init__(self, current_version: str):
        self.current_version = current_version
        self.latest_version_info: Optional[Dict[str, Any]] = None
        self.update_zip_path: Optional[str] = None
        self.expected_checksum: Optional[str] = None

    def check_for_updates(self) -> bool:
        logger.info("Checking for updates...")
        try:
            with httpx.Client(timeout=10.0) as client:
                response = client.get(UPDATE_URL)
                response.raise_for_status()
                self.latest_version_info = response.json()
                latest_version_str = self.latest_version_info.get(
                    "tag_name", "0.0.0"
                ).lstrip("v")
                is_newer = parse_version(latest_version_str) > parse_version(
                    self.current_version
                )
                logger.info(
                    f"Latest version: {latest_version_str}, Current version: {self.current_version}, Newer available: {is_newer}"
                )
                return is_newer
        except httpx.RequestError as e:
            logger.error(f"Update check failed: Network error - {e}")
            return False
        except Exception as e:
            logger.error(f"An unexpected error occurred during update check: {e}")
            return False

    def get_latest_version(self) -> Optional[str]:
        return (
            self.latest_version_info.get("tag_name", "N/A").lstrip("v")
            if self.latest_version_info
            else None
        )

    def get_release_notes(self) -> Optional[str]:
        return (
            self.latest_version_info.get("body", "No description available.")
            if self.latest_version_info
            else None
        )

    def _get_asset_urls(self) -> Tuple[Optional[str], Optional[str]]:
        if not self.latest_version_info:
            return None, None
        assets = self.latest_version_info.get("assets", [])
        zip_url, checksum_url = None, None
        for asset in assets:
            if asset.get("name", "").endswith(".zip"):
                zip_url = asset.get("browser_download_url")
            if asset.get("name", "").endswith(".sha256"):
                checksum_url = asset.get("browser_download_url")
        return zip_url, checksum_url

    def download_update(self, progress_callback=None) -> Optional[str]:
        zip_url, checksum_url = self._get_asset_urls()
        if not zip_url:
            return None

        if checksum_url:
            try:
                with httpx.Client(timeout=10.0) as client:
                    checksum_response = client.get(checksum_url)
                    self.expected_checksum = checksum_response.text.split()[0].strip()
                    logger.info(f"Expected checksum: {self.expected_checksum}")
            except Exception as e:
                logger.warning(f"Could not download checksum: {e}")

        try:
            with httpx.Client(timeout=60.0) as client:
                with client.stream("GET", zip_url) as response:
                    response.raise_for_status()
                    total_size = int(response.headers.get("content-length", 0))
                    temp_dir = tempfile.gettempdir()
                    self.update_zip_path = os.path.join(temp_dir, "gambit_update.zip")
                    bytes_downloaded = 0
                    with open(self.update_zip_path, "wb") as f:
                        for chunk in response.iter_bytes(chunk_size=8192):
                            f.write(chunk)
                            bytes_downloaded += len(chunk)
                            if progress_callback and total_size > 0:
                                progress_callback(
                                    int((bytes_downloaded / total_size) * 100)
                                )
            return self.update_zip_path
        except httpx.RequestError as e:
            logger.error(f"Failed to download update: {e}")
            return None

    def verify_checksum(self, file_path: str) -> bool:
        if not self.expected_checksum:
            return True
        sha256_hash = hashlib.sha256()
        with open(file_path, "rb") as f:
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)
        calculated_checksum = sha256_hash.hexdigest()
        logger.info(f"Calculated checksum: {calculated_checksum}")
        return calculated_checksum.lower() == self.expected_checksum.lower()

    def extract_update(self) -> Optional[str]:
        if not self.update_zip_path:
            return None
        extract_dir = Path(tempfile.gettempdir()) / "gambit_update_extracted"
        if extract_dir.exists():
            shutil.rmtree(extract_dir)
        try:
            with zipfile.ZipFile(self.update_zip_path, "r") as zip_ref:
                zip_ref.extractall(extract_dir)
            os.remove(self.update_zip_path)

            extracted_items = list(extract_dir.iterdir())
            if len(extracted_items) == 1 and extracted_items[0].is_dir():
                final_path = Path(tempfile.gettempdir()) / "gambit_update_final"
                if final_path.exists():
                    shutil.rmtree(final_path)
                shutil.move(str(extracted_items[0]), str(final_path))
                shutil.rmtree(extract_dir)
                logger.info(f"Update contents moved to {final_path}")
                return str(final_path)
            return str(extract_dir)
        except Exception as e:
            logger.error(f"Failed to extract update: {e}")
            return None

    def get_pending_update_path(self) -> Optional[str]:
        path = Path(tempfile.gettempdir()) / "gambit_update_final"
        return str(path) if path.is_dir() else None

    def cleanup_pending_update(self):
        path = self.get_pending_update_path()
        if path:
            shutil.rmtree(path, ignore_errors=True)

    def apply_update(self, extracted_path: str) -> None:
        """
        Apply the update by copying files from the extracted update directory to the app directory,
        skipping the running executable. No admin rights or external scripts required.
        """
        if not getattr(sys, "frozen", False):
            logger.warning("Skipping update: not running from a frozen executable.")
            return

        app_path = Path(sys.executable)
        app_dir = app_path.parent
        extracted_dir = Path(extracted_path)
        errors = []

        def copytree_overwrite(src, dst):
            for item in src.iterdir():
                s = src / item.name
                d = dst / item.name
                if s.is_dir():
                    d.mkdir(exist_ok=True)
                    copytree_overwrite(s, d)
                else:
                    # Skip the running executable
                    if d.resolve() == app_path.resolve():
                        continue
                    try:
                        shutil.copy2(s, d)
                    except Exception as e:
                        errors.append(f"Failed to copy {s} to {d}: {e}")

        try:
            copytree_overwrite(extracted_dir, app_dir)
            logger.info(f"Update files copied from {extracted_dir} to {app_dir}")
            # Optionally, cleanup extracted_dir
            try:
                shutil.rmtree(extracted_dir)
            except Exception as e:
                logger.warning(f"Could not remove temp update dir: {e}")
            if errors:
                logger.error("Some files could not be updated:\n" + "\n".join(errors))
            else:
                logger.info(
                    "Update applied successfully. Please restart the application."
                )
        except Exception as e:
            logger.error(f"Failed to apply update: {e}")
