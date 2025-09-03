#!/usr/bin/env python3
"""Setup script for opencode-manager development and testing."""

import json
import shutil
import subprocess
import sys
from pathlib import Path

# Terminal colors
RED = "\033[0;31m"
GREEN = "\033[0;32m"
YELLOW = "\033[0;33m"
BLUE = "\033[0;34m"
NC = "\033[0m"  # No Color


def setup_configs(target_dir: Path):
    """Copy configuration files for testing.

    Args:
        target_dir: Directory to copy configs to
    """
    print("\nCopying configuration files...")

    # Auth file
    auth_source = Path.home() / ".local/share/opencode/auth.json"
    if not auth_source.exists():
        print(f"{RED}[!] Error: auth.json not found at {auth_source}{NC}")
        print("    Please run 'opencode auth' first")
        return False

    auth_dest = target_dir / "auth.json"
    shutil.copy2(auth_source, auth_dest)
    auth_dest.chmod(0o600)
    print(f"{GREEN}  [OK] Copied auth.json (permissions: 600){NC}")

    # Config file
    config_sources = [
        Path.home() / ".config/opencode/opencode.json",
        Path.cwd() / "opencode.json",
        Path.cwd().parent / "opencode.json",
    ]

    config_source = None
    for path in config_sources:
        if path.exists():
            config_source = path
            break

    if config_source:
        config_dest = target_dir / "opencode.json"
        shutil.copy2(config_source, config_dest)
        config_dest.chmod(0o600)
        print(f"{GREEN}  [OK] Copied opencode.json (permissions: 600){NC}")
    else:
        print(f"{YELLOW}  ! No opencode.json found (will use defaults){NC}")

    # Create .opencode directory structure if it exists
    opencode_dir_source = Path.home() / ".opencode"
    if opencode_dir_source.exists():
        opencode_dir_dest = target_dir / ".opencode"
        if opencode_dir_dest.exists():
            shutil.rmtree(opencode_dir_dest)
        shutil.copytree(opencode_dir_source, opencode_dir_dest)
        print(f"{GREEN}  [OK] Copied .opencode directory{NC}")

    return True


def setup_binary(target_dir: Path, version: str = None):
    """Setup opencode binary - either symlink to bin/ or download.

    Args:
        target_dir: Directory to install binary to
        version: Specific version to download (default: from config)
    """
    print(f"\n{BLUE}Setting up opencode binary...{NC}")

    # Load version configuration
    config_path = Path(__file__).parent.parent / "opencode_versions.json"
    with open(config_path) as f:
        config = json.load(f)

    if version is None:
        version = config["recommended_opencode_version"]

    binary_path = target_dir / "opencode"

    # For test_resources, try to symlink to bin/opencode first
    if target_dir.name == "test_resources":
        bin_opencode = Path.cwd() / "bin" / "opencode"
        if bin_opencode.exists():
            # Check version of bin/opencode
            result = subprocess.run(
                [str(bin_opencode), "--version"], capture_output=True, text=True
            )
            bin_version = result.stdout.strip()

            if bin_version == version:
                # Create symlink
                if binary_path.exists() or binary_path.is_symlink():
                    binary_path.unlink()
                binary_path.symlink_to("../bin/opencode")
                print(
                    f"{GREEN}  [OK] Created symlink to "
                    f"bin/opencode (v{bin_version}){NC}"
                )
                return True
            else:
                print(
                    f"{YELLOW}  ! bin/opencode is v{bin_version}, "
                    f"need v{version}{NC}"
                )

    # Check if binary already exists in target dir
    if binary_path.exists():
        if binary_path.is_symlink():
            target = binary_path.readlink()
            print(f"  Existing symlink: opencode -> {target}")
            # Verify symlink target exists and has right version
            if (target_dir / target).exists():
                return True
        else:
            # Check version
            result = subprocess.run(
                [str(binary_path), "--version"], capture_output=True, text=True
            )
            existing_version = result.stdout.strip()

            if existing_version == version:
                print(
                    f"{GREEN}  [OK] Already have correct version "
                    f"(v{existing_version}){NC}"
                )
                return True
            else:
                print(
                    f"{YELLOW}  ! Version mismatch: "
                    f"have v{existing_version}, need v{version}{NC}"
                )
                response = input("    Replace with correct version? (y/N): ")
                if response.lower() != "y":
                    return True
                binary_path.unlink()

    # Download the specific version
    print(f"  Downloading opencode v{version}...")

    # Use the download script
    download_script = Path(__file__).parent / "download_opencode.py"
    result = subprocess.run(
        [
            sys.executable,
            str(download_script),
            "--version",
            version,
            "--output-dir",
            str(target_dir),
        ],
        capture_output=True,
        text=True,
    )

    if result.returncode != 0:
        print(f"{RED}  [FAIL] Download failed: {result.stderr}{NC}")
        return False

    print(f"{GREEN}  [OK] Downloaded opencode v{version}{NC}")
    return True


def main():
    """Main setup function."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Setup opencode-manager for development and testing"
    )
    parser.add_argument(
        "--test-resources",
        action="store_true",
        help="Setup test_resources directory",
    )
    parser.add_argument(
        "--bin-dir",
        action="store_true",
        help="Setup bin directory with recommended opencode version",
    )
    parser.add_argument("--version", help="Specific opencode version to install")

    args = parser.parse_args()

    # Default to setting up both if no specific option given
    if not args.test_resources and not args.bin_dir:
        args.test_resources = True
        args.bin_dir = True

    print(f"\n{BLUE}opencode-manager Setup{NC}")
    print("=" * 60)

    # Check version compatibility
    config_path = Path(__file__).parent.parent / "opencode_versions.json"
    with open(config_path) as f:
        config = json.load(f)

    print(f"SDK Version: {config['current_sdk_version']}")
    print(f"Recommended opencode: v{config['recommended_opencode_version']}")

    success = True

    # Setup bin directory
    if args.bin_dir:
        bin_dir = Path.cwd() / "bin"
        bin_dir.mkdir(exist_ok=True)

        if not setup_binary(bin_dir, args.version):
            success = False

    # Setup test resources
    if args.test_resources:
        test_dir = Path.cwd() / "test_resources"
        test_dir.mkdir(exist_ok=True)

        print(f"\n{YELLOW}{'='*60}")
        print("[!] WARNING: Integration tests use REAL API calls")
        print("=" * 60 + NC)
        print("\nIntegration tests will:")
        print("  • Make real requests to your configured AI provider")
        print("  • Consume API credits (costs money)")
        print("  • Count against your rate limits")
        print("\nConsider using a test API key with spending limits.")
        print("")

        response = input("Continue with test setup? (y/N) ")
        if response.lower() != "y":
            print("Cancelled.")
        else:
            if not setup_configs(test_dir):
                success = False

            if not setup_binary(test_dir, args.version):
                success = False

    if success:
        print(f"\n{GREEN}[SUCCESS] Setup complete!{NC}")

        if args.bin_dir:
            bin_path = Path.cwd() / "bin" / "opencode"
            if bin_path.exists():
                print("\nBinary ready at: ./bin/opencode")

        if args.test_resources:
            print(f"\n{YELLOW}[!] Remember:{NC}")
            print("  • auth.json and opencode.json are in .gitignore")
            print("  • These files should NEVER be committed")
            print("  • Integration tests will make REAL API calls")
            print("\nYou can now run integration tests:")
            print(f"  {BLUE}make test-integration{NC}")
            print(f"  {BLUE}uv run pytest tests/test_integration.py{NC}")
    else:
        print(f"\n{RED}[ERROR] Setup had errors{NC}")
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
