Full license texts for the KDE Breeze style bundled in release builds
=====================================================================

Release builds ship the Breeze Qt widget style together with some KDE
Frameworks and helper libraries (see BREEZE-NOTICE.txt in the bundle, next to
the copied licenses/ directory). Each directory here holds the license files
from that project's own source release, copied unmodified:

  breeze/                LICENSES/ of breeze-6.7.5.tar.xz (download.kde.org)
  breeze-icons/          COPYING-ICONS and COPYING.LIB of breeze-icons-6.31.0.tar.xz;
                         the icons are LGPL-3.0-or-later, so the GNU LGPL v3
                         (LGPL-3.0.txt) and the GNU GPL v3 it supplements
                         (GPL-3.0.txt) are added from kiconthemes-6.31.0's
                         LICENSES/LGPL-3.0-only.txt and GPL-3.0-only.txt
  frameworkintegration/, karchive/, kcolorscheme/, kconfig/, kcoreaddons/,
  kguiaddons/, ki18n/, kiconthemes/, kwidgetsaddons/, kwindowsystem/
                         LICENSES/ of the matching 6.31.0 tarball (download.kde.org)
  gettext/               gettext-runtime/intl/COPYING.LIB of gettext-0.22.3.tar.xz (libintl)
  libiconv/              COPYING.LIB of libiconv-1.18.tar.gz (Linux builds)
  win-iconv/             readme.txt of win-iconv v0.0.10 (Windows builds; public domain)
  libbzip2/              LICENSE of bzip2 1.0.8
  liblzma/               COPYING of xz 5.2.3 (liblzma is in the public domain)
  libzstd/               LICENSE and COPYING of zstd v1.5.7 (BSD-3-Clause OR GPL-2.0-only)
  openssl/               LICENSE.txt of OpenSSL 3.6.4 (Apache-2.0)
  zlib/                  LICENSE of zlib 1.3.1

scripts/stage_breeze.py copies the directories named by each shipped package's
"license_dir" in scripts/breeze_craft_pins.json into the staged bundle. When a
pinned version changes, refresh the matching directory from the new release.
