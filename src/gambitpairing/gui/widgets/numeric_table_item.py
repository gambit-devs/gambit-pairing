"""Custom QTableWidgetItem for numerical sorting."""

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


from PyQt6 import QtWidgets


class NumericTableWidgetItem(QtWidgets.QTableWidgetItem):
    """Custom QTableWidgetItem for numerical sorting."""

    def __lt__(self, other):
        """Less than via converting text to a float with string comp. as backup."""
        try:
            # Handle empty strings or non-numeric data gracefully
            self_val = float(self.text())
            other_val = float(other.text())
            return self_val < other_val
        except (ValueError, TypeError):
            # Fallback to string comparison if conversion fails
            return super().__lt__(other)
