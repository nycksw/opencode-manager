#!/usr/bin/env python3
"""Download specific opencode version based on compatibility configuration."""

import json
import platform
import subprocess
import sys
import zipfile
from pathlib import Path
from urllib.request import urlretrieve


def get_platform_key():
    """Get platform key for download selection."""
    system = platform.system().lower()
    machine = platform.machine().lower()

    if system == "linux":
        if machine in ["x86_64", "amd64"]:
            return "linux-x64"
        elif machine in ["aarch64", "arm64"]:
            return "linux-arm64"
    elif system == "darwin":
        if machine in ["x86_64", "amd64"]:
            return "darwin-x64"
        elif machine in ["arm64"]:
            return "darwin-arm64"

    raise ValueError(f"Unsupported platform: {system} {machine}")


def download_opencode(version: str = None, output_dir: Path = None):
    """Download specific opencode version.

    Args:
        version: opencode version to download (default: from config)
        output_dir: Directory to download to (default: ./bin)
    """
    # Load version configuration
    config_path = Path(__file__).parent.parent / "opencode_versions.json"
    with open(config_path) as f:
        config = json.load(f)

    # Determine version
    if version is None:
        version = config["recommended_opencode_version"]

    # Check if version info exists
    if version not in config["opencode_releases"]:
        print(f"Error: No download info for opencode v{version}")
        return False

    release_info = config["opencode_releases"][version]

    # Check for breaking changes
    if "compatibility" in release_info:
        if "INCOMPATIBLE" in release_info["compatibility"]:
            print(f"Warning: {release_info['compatibility']}")
            response = input("Continue anyway? (y/N): ")
            if response.lower() != 'y':
                return False

    # Get platform-specific download info
    platform_key = get_platform_key()
    if "downloads" not in release_info:
        print(f"Error: No downloads available for v{version}")
        return False

    if platform_key not in release_info["downloads"]:
        print(f"Error: No download for {platform_key} platform")
        return False

    download_info = release_info["downloads"][platform_key]

    # Setup output directory
    if output_dir is None:
        output_dir = Path("./bin")
    output_dir.mkdir(exist_ok=True)

    # Download file
    zip_path = output_dir / download_info["filename"]
    # Use versioned binary name
    versioned_binary = output_dir / f"opencode-v{version}"
    symlink_path = output_dir / "opencode"
    temp_binary = output_dir / download_info["extract"]

    print(f"Downloading opencode v{version} for {platform_key}...")
    print(f"URL: {download_info['url']}")

    try:
        urlretrieve(download_info["url"], zip_path)
        print(f"Downloaded to {zip_path}")
    except Exception as e:
        print(f"Download failed: {e}")
        return False

    # Extract
    print(f"Extracting {zip_path}...")
    try:
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(output_dir)
        print(f"Extracted to {output_dir}")
    except Exception as e:
        print(f"Extraction failed: {e}")
        return False

    # Rename to versioned binary
    if temp_binary.exists():
        # Remove old versioned binary if exists
        if versioned_binary.exists():
            versioned_binary.unlink()
        temp_binary.rename(versioned_binary)
        versioned_binary.chmod(0o755)
        print(f"Installed as {versioned_binary}")
    else:
        print(f"Warning: Binary not found at {temp_binary}")
        # List extracted files
        print("Extracted files:")
        for f in output_dir.iterdir():
            print(f"  - {f.name}")
        return False

    # Update symlink
    if symlink_path.exists() or symlink_path.is_symlink():
        symlink_path.unlink()
    symlink_path.symlink_to(versioned_binary.name)
    print(f"Created symlink: {symlink_path} -> {versioned_binary.name}")

    # Clean up zip file
    zip_path.unlink()
    print(f"Cleaned up {zip_path}")

    # Verify version
    if versioned_binary.exists():
        result = subprocess.run(
            [str(versioned_binary), "--version"],
            capture_output=True,
            text=True
        )
        installed_version = result.stdout.strip()
        print(f"\nInstalled opencode version: {installed_version}")
        if installed_version != version:
            print(
                f"Warning: Version mismatch! "
                f"Expected {version}, got {installed_version}"
            )

    print(f"\nSuccess! opencode v{version} installed")
    print(f"  Binary: {versioned_binary}")
    print(f"  Symlink: {symlink_path} -> {versioned_binary.name}")
    return True


def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Download specific opencode version"
    )
    parser.add_argument(
        "--version",
        help="opencode version to download (default: from config)"
    )
    parser.add_argument(
        "--output-dir",
        help="Output directory (default: ./bin)",
        type=Path
    )

    args = parser.parse_args()

    success = download_opencode(args.version, args.output_dir)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
