#!/usr/bin/env python3
"""Check for emojis in staged files."""

import re
import subprocess
import sys


def has_emoji(text):
    """Check if text contains emoji characters."""
    # Common emoji ranges
    emoji_pattern = re.compile(
        "["
        "\U0001F600-\U0001F64F"  # emoticons
        "\U0001F300-\U0001F5FF"  # symbols & pictographs
        "\U0001F680-\U0001F6FF"  # transport & map symbols
        "\U0001F1E0-\U0001F1FF"  # flags (iOS)
        "\U00002702-\U000027B0"
        "\U000024C2-\U0001F251"
        "\U0001F900-\U0001F9FF"  # Supplemental Symbols and Pictographs
        "\U00002600-\U000026FF"  # Miscellaneous Symbols
        "\U00002700-\U000027BF"  # Dingbats
        "]+",
        flags=re.UNICODE,
    )
    return emoji_pattern.search(text) is not None


def check_staged_files():
    """Check staged files for emojis."""
    # Get list of staged files
    result = subprocess.run(
        ["git", "diff", "--cached", "--name-only"],
        capture_output=True,
        text=True,
    )

    if result.returncode != 0:
        print("Error getting staged files")
        return False

    staged_files = result.stdout.strip().split("\n")
    if not staged_files or staged_files == [""]:
        return True

    found_emojis = False

    for filepath in staged_files:
        if not filepath:
            continue

        # Skip binary files
        if filepath.endswith(
            (
                ".png",
                ".jpg",
                ".jpeg",
                ".gif",
                ".ico",
                ".pdf",
                ".zip",
                ".tar",
                ".gz",
            )
        ):
            continue

        # Get staged content
        result = subprocess.run(
            ["git", "show", f":{filepath}"], capture_output=True, text=True
        )

        if result.returncode != 0:
            continue

        content = result.stdout
        if has_emoji(content):
            print(f"[ERROR] Found emoji in {filepath}")
            found_emojis = True

            # Show lines with emojis
            lines = content.split("\n")
            for i, line in enumerate(lines, 1):
                if has_emoji(line):
                    print(f"  Line {i}: {line.strip()}")

    return not found_emojis


if __name__ == "__main__":
    if not check_staged_files():
        print("\n[WARNING] Emojis detected in staged files!")
        print("Please remove emojis before committing.")
        print("(Per project guidelines: ASCII characters only)")
        sys.exit(1)
