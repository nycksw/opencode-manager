# Test Resources

This directory contains resources needed for integration testing.

## [!] Cost Warning

**Integration tests use REAL API calls and will cost money!**

When you run integration tests with these configurations:
- Real requests are sent to your configured AI provider (OpenAI, Anthropic, etc.)
- API credits are consumed based on your provider's pricing
- Requests count against your rate limits
- Testing will use the "small" models, e.g. Anthropic's Haiku.

**Recommendations:**
- Use a separate test API key with spending limits
- Monitor your API usage dashboard
- Run integration tests sparingly

## Quick Setup

Run the setup script to copy your opencode configuration:

```bash
./test_resources/setup.sh
```

This will safely copy your configuration files from their standard locations.

## Manual Setup

If you prefer to set up manually, you need:

1. **auth.json** - Your authentication configuration
   ```bash
   cp ~/.local/share/opencode/auth.json test_resources/
   chmod 600 test_resources/auth.json
   ```

2. **opencode.json** - Your model/provider configuration (optional)
   ```bash
   # From your home config
   cp ~/.config/opencode/opencode.json test_resources/

   # OR from a project
   cp ../opencode.json test_resources/
   ```

3. **opencode** - The opencode binary (symlink or copy)
   ```bash
   # Create symlink (preferred)
   ln -s $(which opencode) test_resources/opencode

   # OR copy if symlinks don't work
   cp $(which opencode) test_resources/opencode
   chmod +x test_resources/opencode
   ```

## Files in this Directory

| File | Tracked in Git | Description |
|------|---------------|-------------|
| `README.md` | Yes | This file |
| `setup.sh` | Yes | Setup helper script |
| `opencode` | No | Symlink/copy of opencode binary (git-ignored) |
| `auth.json` | No | Your auth config (git-ignored) |
| `opencode.json` | No | Your model config (git-ignored) |
| `.opencode/` | No | opencode directory (git-ignored) |

## Running Tests

After setup, run integration tests:

```bash
uv run pytest tests/test_integration.py
```

## Safety Notes

- **NEVER commit `auth.json` or `opencode.json`** - they're in `.gitignore` for safety
- The setup script only copies files, never modifies originals
- Integration tests run in isolated temp directories
- Your real configuration is never modified by tests
- Tests use pytest's `tmp_path` which is automatically cleaned up

## Troubleshooting

If tests fail with authentication errors:
1. Ensure your `auth.json` has valid API keys
2. Check that your `opencode.json` specifies an available model
3. Verify the opencode binary is executable

If you need to test with different configurations:
1. Copy different config files to this directory
2. Or temporarily rename this directory to force real config usage
