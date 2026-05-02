# Changelog

## SOS Sync - 2026-05-02 20:44:47

## [2026-04-08 11:17:21] 8ca1ce87-8404-466a-80ff-fb781bf499f5

**Task**: Audit Fix: Fix race condition in vault.py get_session() with asyncio.Lock

**Advice**: Implement double-checked locking pattern with asyncio.Lock for thread-safe session creation. Add _global_lock and _session_locks dict to VaultManager.__init__(), then wrap session creation in get_session() with async with locks. Critical security fix from audit.

---

## [2026-04-08 11:17:21] 6b99d42b-05ea-4628-8430-d655b2a6c6a8

**Task**: Audit Fix: Fix AsyncExitStack resource management in vault.py

**Advice**: Refactor get_session() to avoid private _exit_callbacks access. Store temp_stack reference in _session_stacks dict to keep it alive instead of manipulating private attributes. High priority bug fix from audit.

---

## [2026-04-08 11:17:21] d30e515b-8990-48a5-b413-6719256ae1e7

**Task**: Audit Fix: Add shell command validation in platform_abstraction.py run_shell_command()

**Advice**: Implement allowlist validation or use subprocess with shell=False. Add security check to prevent arbitrary command execution via shell metacharacters. High priority security fix from audit.

---

## [2026-05-02 09:29:36] d4c5603e-250f-4540-beb4-4cca077354c2

**Task**: Uncomment @mcp.on_startup() decorator and implement eager registry initialization

**Advice**: Locate the commented @mcp.on_startup() decorator in src/mcpv/server.py (lines 347-353). Uncomment it and ensure it properly awaits _build_registry(). Wrap the call in try/except block with logging for failed upstream connections but allow server to continue. Add timeout handling (10-15 seconds) to prevent blocking. Ensure TOOL_REGISTRY is async-safe during population.

---

## [2026-05-02 09:29:36] 3d718e0d-480c-4124-9ad5-e65140718e7e

**Task**: Add instructions parameter to FastMCP constructor for automatic agent onboarding

**Advice**: Modify the FastMCP instantiation to include an instructions parameter. Dynamically generate the instructions string after registry population with: server names and connection status, total tool count per server, and directive to use get_initial_context for detailed schemas. Keep payload under ~300 tokens. This provides deterministic baseline context without requiring explicit discovery calls.

---

## [2026-05-02 09:29:36] cc2554f5-5415-4a32-b8ab-dbcb8330f6f4

**Task**: Optimize get_initial_context() to return compact summary by default

**Advice**: Refactor get_initial_context() in src/mcpv/server.py to return compact summary (server names, statuses, tool counts) by default. Add optional parameter detailed=False that returns full schemas when true. Ensure response structure remains backward compatible. Include brief usage note about on-demand schema retrieval. This reduces token overhead by ~60-80%.

---

## [2026-05-02 09:29:36] f525e4d6-80fc-4827-90b4-253bd085c41f

**Task**: Add readiness state check for tool routing

**Advice**: Add a readiness flag or state check so tool routing gracefully handles requests that arrive before startup completes. Verify that existing tool execution paths remain unchanged. The proxy routing logic should continue to resolve tools from the registry without modification. Test flow: start server → verify agent receives instructions → confirm tool discovery works without explicit initial call.

---

## [2026-05-02 09:29:36] 741eb166-a7c6-4e43-9d91-8d5d18cfa001

**Task**: Test and validate auto-initialization implementation

**Advice**: Test the complete flow: start server and verify pre-populated registry, confirm agent receives clear instructions on connection, verify get_initial_context() returns compact summary, test tool routing without explicit initial call, verify compact summary reduces token usage. Ensure startup failures in individual upstream servers do not crash the vault. Verify backward compatibility with existing clients.

---

All notable changes to MCP Vault (`mcpv`) will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [2.1.0] - 2026-04-08

### 🎉 Major Changes

#### Cross-Platform Support (Windows, macOS, Linux)

This release introduces full cross-platform support, transforming MCP Vault from a Windows-only tool to a universal solution for AI agent acceleration.

**New Platform Abstraction Layer:**
- Added [`src/mcpv/platform_abstraction.py`](src/mcpv/platform_abstraction.py) - Core module for OS detection and platform-specific operations
- `PlatformInfo` class provides unified interface for:
  - Platform detection (Windows/macOS/Linux)
  - Path resolution (AppData, Library, XDG directories)
  - Executable naming (`.exe` on Windows, none on Unix)
  - Script extensions (`.bat` vs `.sh`)
  - Shell command generation (`cmd.exe` vs `bash`)
  - Process management (window hiding flags)

**Path Handling Improvements:**
- Windows: OneDrive Desktop redirect detection via registry
- macOS: `~/Library/Application Support` paths
- Linux: XDG specification compliance (`~/.local/share`)
- Unified config directory: `~/.gemini/antigravity` (all platforms)

**New Shell Scripts:**
- [`scripts/init.sh`](scripts/init.sh) - Development initialization for macOS/Linux
- [`scripts/uninstall.sh`](scripts/uninstall.sh) - Cross-platform uninstaller
- [`scripts/reinstall.sh`](scripts/reinstall.sh) - Cross-platform reinstaller

**Desktop/Launcher Support:**
- Windows: `.lnk` shortcuts with OneDrive Desktop support
- macOS: `.command` files in Applications folder
- Linux: `.desktop` files (XDG standard)

### 📦 Updated Files

| File | Change Type | Description |
|------|-------------|-------------|
| `src/mcpv/platform_abstraction.py` | NEW | Core platform abstraction module |
| `src/mcpv/platform_utils.py` | MODIFIED | Enhanced with cross-platform desktop detection |
| `src/mcpv/vault.py` | MODIFIED | Uses platform_info for paths and executables |
| `src/mcpv/server.py` | MODIFIED | Uses platform_info for config directory |
| `scripts/init.sh` | NEW | macOS/Linux init script |
| `scripts/uninstall.sh` | NEW | macOS/Linux uninstall script |
| `scripts/reinstall.sh` | NEW | macOS/Linux reinstall script |
| `tests/test_platform_abstraction.py` | NEW | 31 unit tests for platform abstraction |
| `README.md` | MODIFIED | Updated with multi-platform documentation |
| `pyproject.toml` | MODIFIED | Version bump to 0.4.0, added classifiers |

### 🧪 Testing

- Added 31 unit tests for `platform_abstraction` module
- All tests pass on Windows (mocked tests for macOS/Linux)
- Integration tests verify actual system behavior

### 📝 Documentation

- Updated README.md with platform support matrix
- Added installation instructions for Windows, macOS, and Linux
- Documented platform-specific features and limitations

### 🔧 Technical Changes

- **Breaking Changes:** None - backward compatible with existing Windows installations
- **Dependencies:** No new external dependencies (stdlib only)
- **Python Version:** Still requires Python 3.10+

### 🐛 Bug Fixes

- Fixed OneDrive Desktop redirect detection on Windows (issue reported via GitHub)
- Fixed hardcoded `LOCALAPPDATA` path assumptions
- Fixed `.bat` extension hardcoded references

### 📈 Metrics

- **Lines Added:** ~600
- **Lines Modified:** ~50
- **Files Created:** 6
- **Files Modified:** 5
- **Tests Added:** 31
- **Platforms Supported:** 1 → 3

---

## [0.3.5] - Previous Version

- Windows-only release
- Initial MCP Vault implementation
- Basic booster injection and config hijacking
