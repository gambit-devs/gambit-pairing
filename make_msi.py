#!/usr/bin/env python3
"""
Simplified MSI creation script for Gambit Pairing

This script:
1. Builds a onedir executable with PyInstaller
2. Compresses it into an archive
3. Creates a professional MSI installer with branding

Requirements:
- PyInstaller with onedir spec file
- WiX Toolset (auto-downloads if not found)
- PIL (optional, for custom installer graphics)
"""

import os
import shutil
import subprocess
import sys
import tempfile
import urllib.request
import uuid
import zipfile
from pathlib import Path
from typing import Optional, Tuple


def run_command(cmd, description, check=True, cwd=None):
    """Run a command with better error handling"""
    print(f"Running: {description}")
    print(f"Command: {' '.join(cmd) if isinstance(cmd, list) else cmd}")

    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True, check=check, cwd=cwd
        )

        if result.stdout.strip():
            print(f"stdout: {result.stdout}")
        if result.stderr.strip():
            print(f"stderr: {result.stderr}")

        return result

    except subprocess.CalledProcessError as e:
        print(f"Command failed with return code {e.returncode}")
        print(f"stdout: {e.stdout}")
        print(f"stderr: {e.stderr}")
        if check:
            sys.exit(1)
        return e
    except FileNotFoundError as e:
        print(f"Command not found: {e}")
        if check:
            sys.exit(1)
        return None


def get_version():
    """Get the version from __init__.py"""
    try:
        init_file = Path(__file__).parent / "src" / "gambitpairing" / "__init__.py"
        with open(init_file, "r", encoding="utf-8") as f:
            content = f.read()

        for line in content.split("\n"):
            if "APP_VERSION" in line and "=" in line:
                version = line.split("=")[1].strip().strip('"').strip("'")
                # Remove (alpha) or (beta) suffixes for MSI version
                version = version.split("(")[0].strip()
                return version

        return "1.0.0"
    except Exception as e:
        print(f"Warning: Could not read version from __init__.py: {e}")
        return "1.0.0"


def validate_executable_for_msi(exe_path: Path) -> bool:
    """Validate that the executable is suitable for MSI creation"""
    if not exe_path.exists():
        print(f"[ERROR] Executable not found: {exe_path}")
        return False

    exe_parent = exe_path.parent
    looks_onedir = False

    # Check if it's a onedir build (directory structure with supporting files)
    # Look for PyInstaller-generated files like _internal or supporting DLLs
    support_files = (
        list(exe_parent.glob("*.dll"))
        + list(exe_parent.glob("*.pyd"))
        + list(exe_parent.glob("_internal"))  # PyInstaller 5.0+ uses _internal
        + list(exe_parent.glob("base_library.zip"))  # PyInstaller base library
    )

    if support_files:
        looks_onedir = True
        print(f"[+] Detected onedir build with {len(support_files)} supporting files")

    if not looks_onedir:
        print("\n[ERROR] MSI creation requires the onedir build (not --onefile).")
        print("The executable you provided appears to be a single-file build.")
        print("To generate the required onedir build:")
        print("  python make_executable.py --onedir")
        print("  OR use the --pyinstaller flag with this script")
        print("\nThen point to dist/gambit-pairing/gambit-pairing.exe")
        return False

    return True


# Removed create_compressed_archive function - using direct file harvesting instead


def build_executable():
    """Build the executable using PyInstaller"""
    print("\n=== Building Executable with PyInstaller ===")

    script_dir = Path(__file__).parent.absolute()

    # Run dependency script first
    print("Ensuring dependencies...")
    dependency_script = script_dir / "ensure_all_dependencies.py"
    if dependency_script.exists():
        run_command([sys.executable, str(dependency_script)], "Installing dependencies")
    else:
        print(
            "Warning: Dependency script not found, skipping dependency installation..."
        )

    # Use the onedir spec file for MSI creation (we need a directory structure)
    print("Building onedir executable with PyInstaller...")

    # Clean dist directory to avoid PyInstaller conflicts
    dist_dir = script_dir / "dist"
    if dist_dir.exists():
        print(f"Cleaning existing dist directory: {dist_dir}")
        shutil.rmtree(dist_dir)

    spec_file = script_dir / "gambit-pairing-onedir.spec"
    if not spec_file.exists():
        print(f"Error: PyInstaller onedir spec file not found: {spec_file}")
        print("Expected to find gambit-pairing-onedir.spec in project root")
        sys.exit(1)

    run_command(
        ["pyinstaller", "--clean", str(spec_file)], "Running PyInstaller (onedir)"
    )

    # Verify executable was created
    exe_path = script_dir / "dist" / "gambit-pairing" / "gambit-pairing.exe"
    if exe_path.exists():
        if validate_executable_for_msi(exe_path):
            size_mb = exe_path.stat().st_size / (1024 * 1024)
            print(f"[+] Executable created: {exe_path} ({size_mb:.1f} MB)")
            return exe_path
        else:
            sys.exit(1)
    else:
        print("[!] Executable not found after build!")
        print("Expected location:", exe_path)
        print("Available files in dist:")
        dist_dir = script_dir / "dist"
        if dist_dir.exists():
            for item in dist_dir.iterdir():
                print(f"  {item}")
        sys.exit(1)


def find_wix_tools():
    """Locate candle.exe and light.exe in system"""
    import shutil

    def candidate_in_path(name):
        p = shutil.which(name)
        return Path(p) if p else None

    # Check PATH first
    candle = candidate_in_path("candle") or candidate_in_path("candle.exe")
    light = candidate_in_path("light") or candidate_in_path("light.exe")
    if candle and light:
        return (candle, light)

    # Common install locations
    common_bins = [
        r"C:\Program Files (x86)\WiX Toolset v3.11\bin",
        r"C:\Program Files\WiX Toolset v3.11\bin",
        r"C:\Program Files (x86)\WiX Toolset v4\bin",
        r"C:\Program Files\WiX Toolset v4\bin",
        r"C:\Program Files\Windows Kits\10\bin",
    ]

    for b in common_bins:
        bpath = Path(b)
        if bpath.exists():
            c = bpath / "candle.exe"
            l = bpath / "light.exe"
            if c.exists() and l.exists():
                return (c, l)

    # Search Program Files for WiX installations
    prog_roots = [os.environ.get("ProgramFiles"), os.environ.get("ProgramFiles(x86)")]
    for root in filter(None, prog_roots):
        root_path = Path(root)
        try:
            for sub in root_path.iterdir():
                if "wix" in sub.name.lower():
                    candidate = sub / "bin" / "candle.exe"
                    if candidate.exists():
                        light_candidate = candidate.parent / "light.exe"
                        if light_candidate.exists():
                            return (candidate, light_candidate)
        except Exception:
            continue

    return None


def download_wix_tools():
    """Download WiX tools if not found locally"""
    print("WiX tools not found locally. Downloading...")

    # WiX 3.11.2 binaries URL
    wix_url = "https://github.com/wixtoolset/wix3/releases/download/wix3112rtm/wix311-binaries.zip"

    temp_dir = Path(tempfile.mkdtemp(prefix="wix_tools_"))
    zip_file = temp_dir / "wix-binaries.zip"

    try:
        print(f"Downloading WiX binaries to: {temp_dir}")
        urllib.request.urlretrieve(wix_url, zip_file)
        print("Download completed!")

        # Extract ZIP
        print("Extracting WiX binaries...")
        with zipfile.ZipFile(zip_file, "r") as zip_ref:
            zip_ref.extractall(temp_dir)

        zip_file.unlink()  # Remove ZIP file

        # Verify tools exist
        candle_exe = temp_dir / "candle.exe"
        light_exe = temp_dir / "light.exe"

        if candle_exe.exists() and light_exe.exists():
            print(f"[+] WiX tools ready at: {temp_dir}")
            return (candle_exe, light_exe, temp_dir)
        else:
            print("[!] WiX tools not found after extraction")
            return None

    except Exception as e:
        print(f"Error downloading WiX: {e}")
        return None


def find_icon_file():
    """Locate a suitable icon file for the MSI"""
    roots = [Path(__file__).parent / "src" / "gambitpairing" / "resources" / "icons"]
    for root in roots:
        if not root.exists():
            continue
        ico = root / "icon.ico"
        if ico.exists():
            return ico
        png = root / "icon.png"
        if png.exists():
            return png
        # fallback: first ico or png
        for ext in ["*.ico", "*.png"]:
            for cand in root.glob(ext):
                return cand
    return None


def generate_branding_bitmaps(
    output_dir: Path, version: str
) -> Tuple[Optional[Path], Optional[Path]]:
    """Generate WiX UI banner & dialog bitmaps with professional design"""
    try:
        from PIL import (  # type: ignore
            Image,
            ImageDraw,
            ImageFilter,
            ImageFont,
            ImageStat,
        )
    except ImportError:
        print("Warning: PIL not available, skipping branding bitmap generation")
        return (None, None)

    root_dir = Path(__file__).parent
    icons_dir = root_dir / "src" / "gambitpairing" / "resources" / "icons"
    about_img = icons_dir / "about.webp"
    main_icon_path = find_icon_file()

    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    banner_path = output_dir / "wix_banner.bmp"
    dialog_path = output_dir / "wix_dialog.bmp"

    accent = (20, 120, 160)
    base_im = None

    # Derive accent color from about image if available
    try:
        if about_img.exists():
            with Image.open(about_img) as im:
                im = im.convert("RGBA")
                small = im.resize((16, 16))  # type: ignore[call-arg]
                stat = ImageStat.Stat(small)
                r, g, b, *_ = stat.mean
                raw_accent = (int(r), int(g), int(b))

                def ensure_contrast(c):
                    r2, g2, b2 = c
                    if (0.299 * r2 + 0.587 * g2 + 0.114 * b2) < 60:
                        return (min(r2 + 60, 255), min(g2 + 60, 255), min(b2 + 60, 255))
                    return c

                accent = ensure_contrast(raw_accent)
                base_im = im.copy()
    except Exception:
        pass

    # Load fonts
    font_large = font_small = None
    for fc in ["segoeui.ttf", "SegoeUI.ttf", "arial.ttf", "Arial.ttf"]:
        try:
            font_large = ImageFont.truetype(fc, 24)
            font_small = ImageFont.truetype(fc, 12)
            break
        except Exception:
            continue
    if font_large is None:
        font_large = ImageFont.load_default()
    if font_small is None:
        font_small = ImageFont.load_default()

    # Create banner (493x58)
    banner = Image.new("RGB", (493, 58), (255, 255, 255))
    draw = ImageDraw.Draw(banner)

    # Chessboard pattern background
    square_size = 10
    light_tint = (
        min(accent[0] + 70, 255),
        min(accent[1] + 70, 255),
        min(accent[2] + 70, 255),
    )
    dark_tint = (
        min(accent[0] + 20, 255),
        min(accent[1] + 20, 255),
        min(accent[2] + 20, 255),
    )

    for y in range(0, 58, square_size):
        for x in range(0, 493, square_size):
            col = (
                light_tint
                if ((x // square_size) + (y // square_size)) % 2 == 0
                else dark_tint
            )
            draw.rectangle([x, y, x + square_size - 1, y + square_size - 1], fill=col)

    # White overlay for readability
    overlay = Image.new("RGBA", (493, 58), (255, 255, 255, 90))
    banner = Image.alpha_composite(banner.convert("RGBA"), overlay).convert("RGB")

    # Add version text
    if version:
        draw = ImageDraw.Draw(banner)
        draw.text((10, 58 - 16 - 4), f"v{version}", font=font_small, fill=(35, 35, 35))

    # Add main icon with shadow
    try:
        if main_icon_path and main_icon_path.exists():
            with Image.open(main_icon_path) as ic:
                ic = ic.convert("RGBA").resize((48, 48))  # type: ignore[call-arg]

                # Create shadow
                shadow = Image.new("RGBA", (48, 48), (0, 0, 0, 0))
                sh_draw = ImageDraw.Draw(shadow)
                sh_draw.ellipse([2, 2, 46, 46], fill=(0, 0, 0, 60))
                shadow_blur = shadow.filter(ImageFilter.GaussianBlur(radius=2))

                banner.paste(shadow_blur, (493 - 48 - 10, 7), shadow_blur)
                banner.paste(ic, (493 - 48 - 8, 5), ic)
    except Exception:
        pass

    try:
        banner.save(banner_path, format="BMP")
    except Exception:
        return (None, None)

    # Create dialog image (493x312)
    if base_im is not None:
        try:
            dialog_base = base_im.resize((493, 312)).convert("RGBA")  # type: ignore[call-arg]
            dialog_blur = dialog_base.filter(ImageFilter.GaussianBlur(radius=4))
            white_layer = Image.new("RGBA", (493, 312), (255, 255, 255, 200))
            dialog = Image.alpha_composite(dialog_blur, white_layer)
        except Exception:
            dialog = Image.new("RGBA", (493, 312), (255, 255, 255, 255))
    else:
        dialog = Image.new("RGBA", (493, 312), (255, 255, 255, 255))

    ddraw = ImageDraw.Draw(dialog)
    ddraw.line([(0, 0), (493, 0)], fill=(210, 210, 210), width=1)

    # Add corner icons
    try:
        icon2_path = icons_dir / "icon2.webp"
        if icon2_path.exists():
            with Image.open(icon2_path) as i2:
                i2 = i2.convert("RGBA").resize((64, 64))  # type: ignore[call-arg]
                dialog.paste(i2, (12, 312 - 64 - 12), i2)
    except Exception:
        pass

    try:
        if main_icon_path and main_icon_path.exists():
            with Image.open(main_icon_path) as mi:
                mi = mi.convert("RGBA").resize((64, 64))  # type: ignore[call-arg]
                dialog.paste(mi, (493 - 64 - 12, 312 - 64 - 12), mi)
    except Exception:
        pass

    # Footer tagline
    tagline = "Fast • Fair • Modern"
    footer = f"{tagline}  v{version}".strip() if version else tagline
    try:
        fb = ddraw.textbbox((0, 0), footer, font=font_small)  # type: ignore[attr-defined]
        fw = fb[2] - fb[0]
    except Exception:
        fw = len(footer) * 6
    footer_y = 312 - 64 - 24
    ddraw.text(
        ((493 - fw) // 2, footer_y), footer, font=font_small, fill=(110, 110, 110)
    )

    try:
        dialog.convert("RGB").save(dialog_path, format="BMP")
    except Exception:
        return (banner_path, None)

    return (banner_path, dialog_path)


def generate_guid():
    """Generate a new GUID for WiX"""
    return str(uuid.uuid4()).upper()


def create_wix_file(exe_path, version, output_dir):
    """Create the WiX XML file for onedir executable using directory harvesting approach"""
    exe_path = Path(exe_path).resolve()
    exe_dir = exe_path.parent  # The onedir directory containing all files
    output_dir = Path(output_dir)

    # Generate GUIDs
    product_guid = generate_guid()
    upgrade_code = "12345678-1234-5678-9012-123456789012"  # Keep constant for upgrades

    # Generate branding assets
    banner_bmp, dialog_bmp = generate_branding_bitmaps(output_dir, version)
    icon_path = find_icon_file()

    banner_var = (
        f'<WixVariable Id="WixUIBannerBmp" Value="{banner_bmp}" />'
        if banner_bmp
        else ""
    )
    dialog_var = (
        f'<WixVariable Id="WixUIDialogBmp" Value="{dialog_bmp}" />'
        if dialog_bmp
        else ""
    )

    wix_content = f"""<?xml version="1.0" encoding="UTF-8"?>
<Wix xmlns="http://schemas.microsoft.com/wix/2006/wi">
  <Product Id="{product_guid}"
           Name="Gambit Pairing"
           Language="1033"
           Version="{version}"
           Manufacturer="Gambit Pairing Developers"
           UpgradeCode="{upgrade_code}">

    <Package InstallerVersion="200"
             Compressed="yes"
             InstallScope="perMachine"
             Description="Fast, fair, and modern tournament management"
             Comments="Open source chess tournament pairing software" />

    <!-- Upgrade logic -->
    <MajorUpgrade DowngradeErrorMessage="A newer version of [ProductName] is already installed." />

    <!-- Media -->
    <MediaTemplate EmbedCab="yes" />

    <!-- Properties for UI customization -->
    <Property Id="DESKTOP_SHORTCUT" Value="1" />

    <!-- Features with desktop shortcut option -->
    <Feature Id="ProductFeature" Title="Gambit Pairing" Level="1" Description="The main application files.">
      <ComponentGroupRef Id="ApplicationFiles" />
      <ComponentRef Id="ApplicationShortcut" />
    </Feature>

    <Feature Id="DesktopShortcutFeature"
             Title="Desktop Shortcut"
             Level="1"
             Description="Add a shortcut to the desktop."
             Display="expand"
             Absent="allow">
      <ComponentRef Id="DesktopShortcut" />
      <Condition Level="1">DESKTOP_SHORTCUT="1"</Condition>
    </Feature>

    <!-- Directory structure -->
    <Directory Id="TARGETDIR" Name="SourceDir">
      <Directory Id="ProgramFiles64Folder">
        <Directory Id="INSTALLFOLDER" Name="Gambit Pairing" />
      </Directory>
      <Directory Id="ProgramMenuFolder">
        <Directory Id="ApplicationProgramsFolder" Name="Gambit Pairing"/>
      </Directory>
      <Directory Id="DesktopFolder" Name="Desktop"/>
    </Directory>

    <!-- Start Menu Shortcut -->
    <Component Id="ApplicationShortcut" Directory="ApplicationProgramsFolder" Guid="{generate_guid()}">
      <Shortcut Id="ApplicationStartMenuShortcut"
                Name="Gambit Pairing"
                Description="Fast, fair, and modern tournament management"
                Target="[INSTALLFOLDER]gambit-pairing.exe"
                WorkingDirectory="INSTALLFOLDER" />
      <RemoveFolder Id="ApplicationProgramsFolder" On="uninstall"/>
      <RegistryValue Root="HKCU" Key="Software\\GambitPairing" Name="installed" Type="integer" Value="1" KeyPath="yes"/>
    </Component>

    <!-- Desktop Shortcut (optional) -->
    <Component Id="DesktopShortcut" Directory="DesktopFolder" Guid="{generate_guid()}">
      <Shortcut Id="ApplicationDesktopShortcut"
                Name="Gambit Pairing"
                Description="Fast, fair, and modern tournament management"
                Target="[INSTALLFOLDER]gambit-pairing.exe"
                WorkingDirectory="INSTALLFOLDER" />
      <RegistryValue Root="HKCU" Key="Software\\GambitPairing" Name="desktop" Type="integer" Value="1" KeyPath="yes"/>
    </Component>

    <!-- Custom UI with desktop shortcut checkbox -->
    <UI>
      <UIRef Id="WixUI_FeatureTree" />
      <Publish Dialog="CustomizeDlg" Control="Tree" Property="_BrowseProperty" Value="[WIXUI_INSTALLDIR]" Order="1">1</Publish>
      <Publish Dialog="CustomizeDlg" Control="Tree" Property="_BrowseProperty" Value="[WIXUI_INSTALLDIR]" Order="2">WixUI_InstallMode = "InstallCustom"</Publish>
    </UI>

    <Property Id="WIXUI_INSTALLDIR" Value="INSTALLFOLDER" />

    <!-- Custom license & branding -->
    <WixVariable Id="WixUILicenseRtf" Value="licenses\\license.rtf" />
    {banner_var}
    {dialog_var}

    <!-- Icon -->
    <Property Id="ARPPRODUCTICON" Value="GambitPairingIcon" />
    <Icon Id="GambitPairingIcon" SourceFile="{icon_path if icon_path else exe_path}" />

    <!-- Add/Remove Programs entries -->
    <Property Id="ARPHELPLINK" Value="https://www.chickaboo.net/gambit-pairing/" />
    <Property Id="ARPURLINFOABOUT" Value="https://www.chickaboo.net/gambit-pairing/" />
    <Property Id="ARPCONTACT" Value="support@chickaboo.net" />
    <Property Id="ARPCOMMENTS" Value="Open source chess tournament pairing software" />

  </Product>

  <!-- Fragment to be populated by heat.exe -->
  <Fragment>
    <ComponentGroup Id="ApplicationFiles">
      <!-- This will be populated by WiX Heat tool -->
    </ComponentGroup>
  </Fragment>

</Wix>"""

    wix_file = output_dir / "gambit-pairing.wxs"
    with open(wix_file, "w", encoding="utf-8") as f:
        f.write(wix_content)

    return wix_file


def build_msi(wix_file, version, output_dir, wix_tools=None, cleanup_wix=True):
    """Build the MSI using WiX tools with Heat for directory harvesting"""
    output_dir = Path(output_dir)
    wix_file = Path(wix_file)

    # Get WiX tools
    if wix_tools is None:
        tools = find_wix_tools()
        if tools is None:
            # Try to download WiX tools
            download_result = download_wix_tools()
            if download_result is None:
                print("Error: Could not find or download WiX tools")
                return None
            candle_path, light_path, temp_dir = download_result
        else:
            candle_path, light_path = tools
            temp_dir = None
    else:
        candle_path, light_path, temp_dir = wix_tools

    # Find heat.exe in the same directory as candle.exe
    heat_path = Path(str(candle_path)).parent / "heat.exe"
    if not heat_path.exists() and temp_dir:
        heat_path = temp_dir / "heat.exe"

    try:
        # Determine source directory (look for existing onedir build)
        source_dir = None
        possible_dirs = [
            Path("dist/gambit-pairing"),
            Path("build/gambit-pairing-onedir"),
        ]

        for dir_path in possible_dirs:
            if dir_path.exists() and (dir_path / "gambit-pairing.exe").exists():
                source_dir = dir_path.resolve()
                break

        if not source_dir:
            print("Error: Could not find onedir build directory")
            return None

        print(f"Using source directory: {source_dir}")

        # Step 1: Use Heat to harvest the directory structure
        harvest_file = output_dir / "harvest.wxs"
        heat_cmd = [
            str(heat_path),
            "dir",
            str(source_dir),
            "-cg",
            "ApplicationFiles",
            "-gg",  # Generate GUIDs
            "-scom",  # Suppress COM registration
            "-sreg",  # Suppress registry entries
            "-sfrag",  # Suppress fragments
            "-srd",  # Suppress root directory
            "-dr",
            "INSTALLFOLDER",  # Directory reference
            "-var",
            f"var.SourceDir",
            "-out",
            str(harvest_file),
        ]

        print("Harvesting directory structure with Heat...")
        result = subprocess.run(heat_cmd, capture_output=True, text=True)

        if result.returncode != 0:
            print(f"Heat harvesting failed:")
            print(f"stdout: {result.stdout}")
            print(f"stderr: {result.stderr}")
            return None

        print("Directory harvesting successful")

        # Step 2: Combine the main WiX file with the harvested components
        combined_wix_file = output_dir / "gambit-pairing-combined.wxs"

        # Read the main WiX content
        with open(wix_file, "r", encoding="utf-8") as f:
            main_content = f.read()

        # Read the harvested components
        with open(harvest_file, "r", encoding="utf-8") as f:
            harvest_content = f.read()

        # Extract both Fragment sections from harvest file
        import re

        # Find all Fragment sections
        fragment_matches = re.findall(
            r"<Fragment>.*?</Fragment>", harvest_content, re.DOTALL
        )

        if len(fragment_matches) >= 2:
            # Combine both fragments into one
            combined_fragments = f"""<Fragment>
{fragment_matches[0][10:-11]}
{fragment_matches[1][10:-11]}
  </Fragment>"""

            # Replace the placeholder Fragment with the combined Fragment
            placeholder = """  <Fragment>
    <ComponentGroup Id="ApplicationFiles">
      <!-- This will be populated by WiX Heat tool -->
    </ComponentGroup>
  </Fragment>"""

            print(
                f"Debug: Placeholder found in template: {placeholder in main_content}"
            )
            print(f"Debug: Found {len(fragment_matches)} fragments in harvest file")

            main_content = main_content.replace(placeholder, f"  {combined_fragments}")

            # Verify the replacement worked
            if 'ComponentGroup Id="ApplicationFiles"' in main_content:
                print("[+] ComponentGroup 'ApplicationFiles' found in merged file")
            else:
                print("[x] ComponentGroup 'ApplicationFiles' NOT found in merged file")
        else:
            print(f"Warning: Expected 2 fragments, found {len(fragment_matches)}")

        # Write the combined file
        with open(combined_wix_file, "w", encoding="utf-8") as f:
            f.write(main_content)

        # Step 3: Compile with candle
        wixobj_file = output_dir / "gambit-pairing.wixobj"
        candle_cmd = [
            str(candle_path),
            str(combined_wix_file),
            "-out",
            str(wixobj_file),
            "-arch",
            "x64",
            f"-dSourceDir={source_dir}",  # Define the variable for heat
        ]

        print("Compiling WiX file...")
        result = subprocess.run(candle_cmd, capture_output=True, text=True)

        if result.returncode != 0:
            print(f"Candle compilation failed:")
            print(f"stdout: {result.stdout}")
            print(f"stderr: {result.stderr}")
            return None

        print("WiX compilation successful")

        # Step 4: Link with light
        msi_file = output_dir / f"GambitPairing-{version}-x64.msi"

        # Find WixUIExtension
        extension_path = None
        if temp_dir:
            extension_path = temp_dir / "WixUIExtension.dll"
        else:
            parent_dir = Path(str(candle_path)).parent
            extension_path = parent_dir / "WixUIExtension.dll"

        light_cmd = [str(light_path), str(wixobj_file), "-out", str(msi_file)]

        if extension_path and Path(extension_path).exists():
            light_cmd.extend(["-ext", str(extension_path)])
        else:
            light_cmd.extend(["-ext", "WixUIExtension"])

        print("Linking MSI...")
        result = subprocess.run(light_cmd, capture_output=True, text=True)

        if result.returncode != 0:
            print(f"Light linking failed:")
            print(f"stdout: {result.stdout}")
            print(f"stderr: {result.stderr}")
            return None

        print("MSI linking successful")
        return msi_file

    finally:
        # Cleanup downloaded WiX tools if requested
        if cleanup_wix and temp_dir and Path(temp_dir).exists():
            try:
                shutil.rmtree(temp_dir)
                print("Cleaned up temporary WiX tools")
            except Exception as e:
                print(f"Warning: Could not cleanup WiX tools: {e}")


def main():
    print("Gambit Pairing - Simplified MSI Creation Script")
    print("=" * 50)

    # Get version from __init__.py
    version = get_version()
    print(f"Version: {version}")

    # Set output directory absolute path
    script_dir = Path(__file__).parent.absolute()
    output_dir = script_dir / "build" / "gambit-pairing-msi"
    output_dir.mkdir(parents=True, exist_ok=True)

    # Step 1: Build onedir executable with PyInstaller
    print("\n=== Building Onedir Executable ===")
    exe_path = build_executable()
    exe_dir = exe_path.parent

    # Validate executable is suitable for MSI creation
    if not validate_executable_for_msi(exe_path):
        sys.exit(1)

    print(f"Built onedir executable: {exe_path}")
    print(f"Onedir directory: {exe_dir}")
    print(f"Output directory: {output_dir}")

    # Step 2: Generate WiX file with branding (using direct harvesting)
    print("\n=== Generating WiX XML with Branding ===")
    wix_file = create_wix_file(exe_path, version, output_dir)
    print(f"[+] Created WiX file: {wix_file}")

    # Step 3: Build MSI with direct file harvesting
    print("\n=== Building MSI with WiX (Direct File Harvesting) ===")
    msi_file = build_msi(wix_file, version, output_dir, cleanup_wix=True)

    if msi_file and msi_file.exists():
        size_mb = msi_file.stat().st_size / (1024 * 1024)
        print(f"\n[SUCCESS] MSI created successfully!")
        print(f"File: {msi_file}")
        print(f"Size: {size_mb:.1f} MB")

        print(f"\nMSI Features:")
        print(f"- Professional installer with branding")
        print(f"- Direct file installation (no intermediate archives)")
        print(f"- Installs to Program Files")
        print(f"- Start Menu shortcut")
        print(f"- Optional desktop shortcut")
        print(f"- Proper uninstall support")
        print(f"- Windows transactional installation")
        print(f"- MSI repair capability")

        # Cleanup intermediate files
        wixobj_file = output_dir / "gambit-pairing.wixobj"
        harvest_file = output_dir / "harvest.wxs"
        combined_file = output_dir / "gambit-pairing-combined.wxs"

        for cleanup_file in [wixobj_file, harvest_file, combined_file]:
            if cleanup_file.exists():
                cleanup_file.unlink()

        print("Cleaned up intermediate files")

    else:
        print("\n[ERROR] MSI creation failed!")
        sys.exit(1)


if __name__ == "__main__":
    main()
