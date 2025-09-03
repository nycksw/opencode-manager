# opencode Version Management Strategy

## Current Situation (September 2025)

### The Problem
- opencode releases extremely aggressively (4 releases in one day on Sept 1st)
- The SDK (opencode-ai) lags significantly behind server releases
- Breaking API changes are frequent and often undocumented
- Current SDK version: 0.1.0a36 (released August 27, 2025)
- Latest opencode version: 0.6.3+ (multiple breaking changes from SDK's target)

### Version Compatibility Analysis

For current recommended version, see [`opencode_versions.json`](opencode_versions.json).

| opencode Version | SDK Version | Compatibility | Notes |
|-----------------|-------------|---------------|-------|
| v0.5.28 | 0.1.0a36 | FULL | SDK was built for this version (Aug 26-27) |
| v0.6.0 | 0.1.0a36 | BROKEN | Major breaking changes introduced |
| v0.6.3 | 0.1.0a36 | PARTIAL | Works by accident, not design |

### Breaking Changes in v0.6.0

Released September 1, 2025, v0.6.0 introduced:

1. **Removed `/app` concept entirely**
   - Replaced with `/project` endpoints
   - Breaks health checks using `/app`

2. **API Operation Changes**
   - `session.chat` → `session.prompt`
   - SDK still calls `session.chat()`

3. **Request Structure Changes**
   - Model parameter changed from flat fields to nested object
   - Old: `{model_id: "x", provider_id: "y"}`
   - New: `{model: {modelID: "x", providerID: "y"}}`

4. **Universal Directory Parameter**
   - All endpoints now accept `directory` query parameter
   - For multi-project support
   - Currently optional but may become required

5. **Response Structure Changes**
   - Parts array often empty, content in info field
   - JavaScript errors appearing in responses
   - Event stream format changed to `text/event-stream`

## Recommended Strategy

### Pin to Recommended Version
The recommended version is maintained in `opencode_versions.json`:
- Currently v0.5.28 (released August 26, 2025)
- SDK 0.1.0a36 released August 27, 2025
- Full compatibility, no workarounds needed

### Version Management System

1. **Version Configuration File** (`opencode_versions.json`)
   - Maps SDK versions to compatible opencode versions
   - Specifies download URLs for each platform
   - Tracks tested combinations

2. **Automatic Binary Management**
   - Download specific version from GitHub releases
   - Store in project directory (not test_resources)
   - Verify checksum/signature

3. **Compatibility Enforcement**
   - Check version on OpencodeServer startup
   - Warn or fail if version mismatch
   - Allow override with explicit flag

4. **Documentation**
   - Clear version requirements in README
   - Compatibility matrix
   - Migration guides for version updates

### Implementation Plan

1. Create `opencode_versions.json` configuration
2. Update setup scripts to download specific versions
3. Add version checking to OpencodeServer
4. Update all documentation
5. Test thoroughly with recommended version
6. Create migration plan for future updates

## Current Workarounds (v0.6.3)

While the system "works" with v0.6.3, it's fragile:
- Relies on server's backwards compatibility (undocumented)
- Response parsing uses string conversion fallback
- JavaScript errors in responses ignored
- May break at any time

## Future Considerations

1. **Track SDK Updates**
   - Monitor for new SDK releases
   - Test compatibility when SDK updates
   - Update version mappings accordingly

2. **Support Multiple Versions**
   - Allow users to specify version
   - Maintain compatibility layers
   - Automated testing against multiple versions

3. **Direct API Client**
   - Consider bypassing SDK for stability
   - Implement own HTTP client with version handling
   - More control over compatibility
