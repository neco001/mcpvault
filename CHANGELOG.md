# Changelog

## SOS Sync - 2026-05-02 23:57:02

## [2026-05-02 21:34:59] f78b320c-9321-4148-b98a-f06af3006d8d

**Task**: Baseline Modernization & Constants Extraction

**Advice**: Create src/mcpv/constants.py with all hardcoded strings (MCPV_INSTRUCTIONS, UI_MESSAGES), timeout constants (GATHER_TIMEOUT, TOOL_LIST_TIMEOUT, REGISTRY_INIT_TIMEOUT), and display limits (MAX_TOOLS_DISPLAY). Fix mutable default arguments (params: dict = {} → None, args: dict = {} → None). Replace bare except:pass on lines 14-15 and 25-26 with specific exception types + logger.warning. Add type hints to all functions. Translate/remove Korean comments to English. This task is the foundation for all subsequent extraction work.

---

## [2026-05-02 21:35:00] 6777990b-f74f-4c6d-bfeb-70222711bfaa

**Task**: Registry Encapsulation - ToolRegistry class

**Advice**: Create src/mcpv/registry.py implementing a ToolRegistry class that encapsulates: tool dictionary, _registry_initialized flag, _registry_lock (asyncio.Lock), TOOL_INDEX_FILE path, and all registry lifecycle methods. Migrate _build_registry() logic into async method ToolRegistry.initialize() — must remain idempotent and thread-safe with double-check locking. Add methods: get_tools(), search(query), get_tools_by_server(server_name), toggle_server(name, enabled), toggle_tool(server, tool, enabled). The class must accept dependencies (manager, BACKUP_FILE path, config_dir) via constructor injection. Keep TOOL_REGISTRY backward-compatible as module-level alias initially.

---

## [2026-05-02 21:35:00] dc83928b-0e46-469b-8997-6e34ebfa6b08

**Task**: Context Builders & Admin Dispatch extraction

**Advice**: Create src/mcpv/context.py with: build_initial_context(registry, valve, force, detailed), build_compact_context(servers, total_tools), build_detailed_context(servers, total_tools). Registry injected as parameter. Create src/mcpv/admin.py with AdminDispatcher class: use dict-based dispatch mapping action names to async handler functions (list_servers, list_tools, search, toggle_server, toggle_tool). Each handler receives registry instance + params dict. Replace the 5-branch if/elif in mcpv_admin with AdminDispatcher.dispatch(action, params).

---

## [2026-05-02 21:35:00] 1121d0ef-9b24-42df-b78e-50a05f310dec

**Task**: Smart Routing & File Utilities extraction

**Advice**: Create src/mcpv/routing.py implementing: route_tool_call(tool_name, args, registry, manager) — migrate run_tool logic including vault: prefix stripping, mcp_ prefix correction, server-name confusion detection, and typo suggestion. Create src/mcpv/file_utils.py with: validate_path(path, root_dir) → Path (single DRY containment check), safe_read_file(path, root_dir) → str, safe_list_directory(path, root_dir) → str. Both file functions must call validate_path() before I/O. All functions need full type hints.

---

## [2026-05-02 21:35:00] a505fa0b-269a-43cb-be8a-4c8dc68f3479

**Task**: Facade Assembly & Compatibility Verification

**Advice**: Refactor server.py into thin orchestrator/facade: import and instantiate ToolRegistry, configure FastMCP lifespan to call registry.initialize(), register all @mcp.tool() functions delegating to new modules (get_initial_context → context, mcpv_admin → admin.dispatch, run_tool → routing, read_file/list_directory → file_utils). Re-export mcp, TOOL_REGISTRY (alias), and all tool functions at module level for backward compat. Run pytest on test_timeout_protection.py and test_auto_initialization.py. Update internal test imports only where tests reference module internals directly.

---

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
