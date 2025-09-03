#!/bin/bash
# Check for incorrect capitalization of "opencode" in comments and docs
# Note: OpencodeServer (class names) are OK, but "Opencode server" in text is not

FILES=$(git diff --cached --name-only | grep -E '\.(py|md|txt|rst)$' | grep -v AGENTS.md)

if [ -z "$FILES" ]; then
    exit 0
fi

for file in $FILES; do
    if [ -f "$file" ]; then
        # For Python files, check comments and docstrings
        if [[ "$file" == *.py ]]; then
            # Look for "Opencode " or "OpenCode " (with space after) in comments/strings
            # This avoids matching OpencodeServer class names
            if grep -E '(#.*\bOpencode\s|#.*\bOpenCode\s|""".*\bOpencode\s|""".*\bOpenCode\s|'"'"'.*\bOpencode\s|'"'"'.*\bOpenCode\s)' "$file" > /dev/null; then
                echo "Error in $file: Use lowercase 'opencode' not 'Opencode' or 'OpenCode' in comments/docs"
                grep -n -E '(#.*\bOpencode\s|#.*\bOpenCode\s|""".*\bOpencode\s|""".*\bOpenCode\s)' "$file" | head -3
                exit 1
            fi
        # For Markdown/text files, check all occurrences except class names
        elif [[ "$file" == *.md ]] || [[ "$file" == *.txt ]] || [[ "$file" == *.rst ]]; then
            # Look for standalone "Opencode" or "OpenCode" (not part of OpencodeServer)
            if grep -E '\b(Opencode|OpenCode)\b' "$file" | grep -v 'OpencodeServer' > /dev/null; then
                echo "Error in $file: Use lowercase 'opencode' not 'Opencode' or 'OpenCode'"
                grep -n -E '\b(Opencode|OpenCode)\b' "$file" | grep -v 'OpencodeServer' | head -3
                exit 1
            fi
        fi
    fi
done

exit 0