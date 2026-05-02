"""Tool Registry module for managing MCP tool definitions and metadata."""

import asyncio
import json
import logging
from pathlib import Path
from typing import Dict, Any, Iterator, List, Optional

from . import constants
from .platform_abstraction import platform_info
from .vault import manager

logger = logging.getLogger("mcpv-router")

# Configuration
CONFIG_DIR = platform_info.get_config_dir()
TOOL_INDEX_FILE = CONFIG_DIR / "tool_index.json"
REGISTRY_INIT_TIMEOUT = constants.REGISTRY_INIT_TIMEOUT
GATHER_TIMEOUT = constants.GATHER_TIMEOUT
TOOL_LIST_TIMEOUT = constants.TOOL_LIST_TIMEOUT


class ToolRegistry:
    """Encapsulates tool registry logic, providing async initialization and dict-like access."""

    def __init__(self) -> None:
        self.TOOL_REGISTRY: Dict[str, Any] = {}
        self._initialized: bool = False
        self._registry_lock = asyncio.Lock()

    async def _build_registry(self) -> None:
        """Builds tool map by scanning upstream servers. Uses local cache if available.
        
        This function is idempotent and thread-safe. Multiple concurrent calls will
        only trigger one actual registry build. Subsequent calls will wait for the
        first call to complete or return immediately if already initialized.
        """
        # Fast path: if already initialized, return immediately (idempotency)
        if self._initialized and self.TOOL_REGISTRY:
            logger.debug("Registry already initialized, skipping rebuild")
            return
        
        # Acquire lock to prevent concurrent builds (thread safety)
        async with self._registry_lock:
            # Double-check after acquiring lock (another thread might have initialized)
            if self._initialized and self.TOOL_REGISTRY:
                logger.debug("Registry initialized while waiting for lock, skipping rebuild")
                return
            
            from .vault import BACKUP_FILE
            
            # 1. Try local cache first
            if not self.TOOL_REGISTRY and TOOL_INDEX_FILE.exists():
                try:
                    with open(TOOL_INDEX_FILE, "r", encoding="utf-8") as f:
                        self.TOOL_REGISTRY = json.load(f)
                    logger.info("⚡ Tool Registry loaded from local cache.")
                except (json.JSONDecodeError, OSError) as e:
                    logger.warning(f"Failed to load tool cache: {e}")

            if not BACKUP_FILE.exists(): return
            
            with open(BACKUP_FILE, "r", encoding="utf-8") as f:
                config = json.load(f)
            
            active_servers = [k for k, v in config.get("mcpServers", {}).items() if not v.get("disabled")]
            
            # Parallel connection attempts (REQ-01: timeout wrapper)
            tasks = [manager.get_session(name) for name in active_servers]
            try:
                sessions = await asyncio.wait_for(
                    asyncio.gather(*tasks, return_exceptions=True),
                    timeout=GATHER_TIMEOUT
                )
            except asyncio.TimeoutError:
                logger.warning(f"Timeout ({GATHER_TIMEOUT}s) connecting to servers")
                return  # Exit early, use cached registry if available
            
            new_registry = {}
            
            for name, session in zip(active_servers, sessions):
                if not session or isinstance(session, Exception):
                    if isinstance(session, Exception):
                        logger.warning(f"Failed to connect to {name}: {session}")
                    continue
                try:
                    tools = await asyncio.wait_for(session.list_tools(), timeout=TOOL_LIST_TIMEOUT)
                    for t in tools.tools:
                        key = t.name
                        if key in new_registry:
                            key = f"{name}_{t.name}"
                        
                        args = list(t.inputSchema.get("properties", {}).keys())
                        new_registry[key] = {
                            "server": name,
                            "real_name": t.name,
                            "desc": t.description[:150] if t.description else "No description",
                            "args": ", ".join(args)
                        }
                except asyncio.TimeoutError:
                    logger.warning(f"Timeout listing tools from {name}")
                    continue
                except Exception as e:
                    logger.warning(f"Error listing tools from {name}: {e}")
                    continue
                
            if new_registry:
                self.TOOL_REGISTRY = new_registry
                self._initialized = True
                # Save to local file cache
                try:
                    with open(TOOL_INDEX_FILE, "w", encoding="utf-8") as f:
                        json.dump(self.TOOL_REGISTRY, f, indent=2)
                except OSError as e:
                    logger.warning(f"Failed to save tool cache: {e}")
                logger.info(f"🗺️ Tool Registry Rebuilt and Cached: {len(self.TOOL_REGISTRY)} tools found.")

    async def initialize(self) -> None:
        """Initialize the registry by calling _build_registry if not already done."""
        if not self._initialized:
            try:
                await asyncio.wait_for(self._build_registry(), timeout=REGISTRY_INIT_TIMEOUT)
                self._initialized = True
                logger.info("✅ [MCPV] Tool registry initialized successfully at startup")
            except asyncio.TimeoutError:
                logger.warning("⏱️ [MCPV] Timeout occurred while building registry at startup - will initialize on first call")
            except Exception as e:
                logger.error(f"❌ [MCPV] Failed to initialize registry at startup: {e}")
                # Continue even if registry fails - graceful degradation
                pass

    def get_registry(self) -> Dict[str, Any]:
        """Return the underlying registry dictionary."""
        return self.TOOL_REGISTRY

    # List/iterable interface for backward compatibility
    def __iter__(self) -> Iterator[str]:
        return iter(self.TOOL_REGISTRY)

    def __len__(self) -> int:
        return len(self.TOOL_REGISTRY)

    def __getitem__(self, key: str) -> Any:
        return self.TOOL_REGISTRY[key]

    def __contains__(self, key: str) -> bool:
        return key in self.TOOL_REGISTRY

    def keys(self) -> Iterator[str]:
        return self.TOOL_REGISTRY.keys()

    def values(self) -> Iterator[Any]:
        return self.TOOL_REGISTRY.values()

    def items(self) -> Iterator[tuple]:
        return self.TOOL_REGISTRY.items()
